"""NODE 3 - fact_check: every claim must link to a source.

Claims checked: the 10 level claims AND the hook (stored as level 0), so a false opening line is caught too.
Two checks per claim:
 1. (free, plain Python) the claim's URL must be one of the research sources
    and the script must have exactly 10 levels.
 2. (cheap Haiku model) does the source text actually support the claim?
Failed claims are sent back to write_script - at most MAX_FACT_LOOPS times.
After that the script goes to the human reviewer with the failures marked.
"""
from .. import config, db, llm
from ..state import ClaimChecks, State


FACT_CHECK_SYSTEM = """You are a strict fact checker. For each ITEM say whether the SOURCE TEXT supports the CLAIM
(numbers and meaning). Be strict but fair; unsupported or contradicted = not supported.
For every item, write your reasoning FIRST, and only then give the verdict. Your verdict must agree with the conclusion
of your reasoning (if you conclude 'the source supports the claim', the verdict is supported = true).
ITEM 0 is the episode's opening HOOK: check every factual statement in it against the source text (and against basic
common knowledge: an overclaim such as 'the smallest rock on Earth' is NOT supported). If the hook is only a question or
a teaser with no factual statement, it is supported."""


def fact_check(state: State) -> dict:
    script = state["script"]
    sources = {s["url"]: s for s in state.get("sources", [])}
    levels = script["levels"]
    hook_url = script.get("hook_source_url", "")
    claims = [{"level": 0, "claim": script["hook"], "source_url": hook_url, "status": "pass", "reason": ""}]
    claims += [{"level": lv["n"], "claim": lv["claim"], "source_url": lv["source_url"],
                "status": "pass", "reason": ""} for lv in levels]

    problems = []
    if len(levels) != 10:
        problems.append(f"Script has {len(levels)} levels; it must have exactly 10.")

    # check 1: source link exists
    for c in claims:
        if c["level"] == 0 and not c["source_url"]:
            continue    # a hook with no source is allowed ONLY if it states no facts; the AI check below decides
        if c["source_url"] not in sources:
            c["status"], c["reason"] = "fail", "source_url is not one of the researched sources"

    # check 2: does the source text support the claim? (skipped in mock mode)
    if not config.mock_llm():
        to_check = [c for c in claims if c["status"] == "pass"]
        if to_check:
            block = "\n\n".join(
                (f"ITEM {c['level']}" + (" (THE HOOK)" if c["level"] == 0 else "") + f"\nCLAIM: {c['claim']}\n"
                 f"SOURCE TEXT: {sources[c['source_url']]['snippet'] if c['source_url'] in sources else '(no source given)'}")
                for c in to_check)
            result: ClaimChecks = llm.cheap().with_structured_output(ClaimChecks).invoke([
                ("system", FACT_CHECK_SYSTEM), ("human", block)])
            by_level = {r.level: r for r in result.checks}
            for c in to_check:
                r = by_level.get(c["level"])
                if r is None or not r.supported:
                    c["status"], c["reason"] = "fail", (r.reason if r else "not checked")

    failed = [c for c in claims if c["status"] == "fail"]
    problems += [f"{'The HOOK' if c['level'] == 0 else 'Level ' + str(c['level'])}: {c['reason']} (claim: {c['claim']})"
                 for c in failed]

    db.save_script_with_claims(state["episode_id"], script, claims)   # one script version per pass

    loops = state.get("fact_loops", 0)
    if problems and loops < config.MAX_FACT_LOOPS:
        return {"stage": "fact_check", "claims": claims, "fact_loops": loops + 1,
                "fact_feedback": "\n".join(problems)}
    # all good, or out of retries: continue; failures stay visible to the human reviewer
    return {"stage": "fact_check", "claims": claims, "fact_feedback": ""}


def route_after_fact_check(state: State) -> str:
    """Back to write_script if there is feedback to fix, otherwise on to the human."""
    return "write_script" if state.get("fact_feedback") else "review_script"
