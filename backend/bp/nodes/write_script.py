"""NODE 2 - write_script: Claude writes the structured episode script.

Why structured output: instead of free text we force Claude to fill in a form
(hook, 10 levels, twist level, a source per claim). That makes later steps
(fact-check, voice, render) reliable.
It also receives human notes and fact-check feedback when the graph loops back here.

Robustness: the answer is VALIDATED (form fills in correctly + our own rules). If it fails, we retry ONCE and
tell the model exactly what was wrong. If the retry fails too, the episode stops with a clear error (dashboard: Retry).
"""
from typing import Callable

from .. import config, llm, mock
from ..state import Script, State

SYSTEM = """You write scripts for the YouTube Shorts channel "The Breaking Point".
One object faces 10 escalating levels of one hazard (heat, cold, pressure, impact speed, lightning or spin) until it fails.

RULES
- Exactly 10 levels, numbered 1 to 10, strictly escalating, each with a REAL value and unit taken from the research.
- SPREAD THE FULL RANGE. Level 1 is HARMLESS: an ordinary, everyday value where the object clearly SURVIVES.
  Level 10 is EXTREME: the most extreme documented value, where the object is DESTROYED.
  Levels 2-9 climb steadily between them, each value clearly bigger (for cold: colder) than the one before, roughly
  evenly spaced on a sensible scale (usually multiplying, not adding). Never put several levels inside one narrow
  band or take them all from one threshold table. Check yourself: if levels 1-5 look almost the same, redo them.
- Each level has one SURVIVES or DESTROYED verdict. The object fails somewhere sensible. Every level tests a fresh,
  identical object, so a later level may survive even though an earlier one was destroyed.
- THE TWIST: exactly ONE level (between 3 and 9) is a REAL surprise: the result is the opposite of what viewers
  expect, so its verdict differs from the level just before it. Best: the object SURVIVES at a level where everyone
  expects it to fail (use the surprising fact from the research, e.g. a real physical effect). Just being DESTROYED
  at a higher number is NOT a twist, and the last level cannot be the twist. The narration for the twist level must
  say why it is surprising.
- Each narration line is short (max 25 words), spoken, and ends by naming the verdict.
- Every level's claim must be supported by one of the provided source URLs. Use ONLY those URLs. Do not invent facts."""


def validate_script(script: Script) -> list[str]:
    """Our own rules, beyond 'the form was filled in'. Returns a list of problems (empty = valid)."""
    problems = []
    lv = script.levels
    if len(lv) != 10:
        problems.append(f"There must be exactly 10 levels, but there are {len(lv)}.")
        return problems
    if [x.n for x in lv] != list(range(1, 11)):
        problems.append(f"Levels must be numbered 1 to 10 in order, but the numbers are {[x.n for x in lv]}.")
    if len({x.value.strip().lower() for x in lv}) != 10:
        problems.append("Every level needs a different value; some values are repeated.")
    if lv[0].verdict != "SURVIVES":
        problems.append("Level 1 must be harmless: its verdict must be SURVIVES.")
    if not any(x.verdict == "DESTROYED" for x in lv):
        problems.append("The object must fail somewhere: at least one level must be DESTROYED.")
    for x in lv:
        if len(x.narration.split()) > 30:
            problems.append(f"Level {x.n} narration is too long ({len(x.narration.split())} words; max 25).")
    t = script.twist_level
    if not 3 <= t <= 9:
        problems.append(f"twist_level must be between 3 and 9, but it is {t}.")
    elif lv[t - 1].verdict == lv[t - 2].verdict:
        problems.append(f"The twist (level {t}) is not a real surprise: its verdict ({lv[t - 1].verdict}) is the same as "
                        f"level {t - 1}. The twist must flip the result, e.g. SURVIVES where viewers expect DESTROYED.")
    return problems


def generate_script(invoke: Callable[[list], dict], messages: list) -> Script:
    """Ask for a script; on a failed answer retry ONCE, telling the model what was wrong.
    `invoke(messages)` must return {"parsed": Script|None, "parsing_error": Exception|None} (what
    with_structured_output(include_raw=True) gives). Taking it as a parameter lets tests run this for free."""
    problem = ""
    previous = None
    for attempt in (1, 2):
        msgs = list(messages)
        if problem:
            msgs.append(("human", "Your previous answer was REJECTED by validation. Fix it and answer again.\n"
                                  f"VALIDATION ERROR:\n{problem}"
                                  + (f"\n\nYour rejected answer (JSON):\n{previous}" if previous else "")))
        out = invoke(msgs)
        script = out.get("parsed")
        if script is None:
            problem = f"The answer did not match the required format: {out.get('parsing_error') or 'no structured answer'}"
            previous = None
            continue
        issues = validate_script(script)
        if not issues:
            return script
        problem = "\n".join(f"- {i}" for i in issues)
        previous = script.model_dump_json()
    raise RuntimeError(f"write_script: the model's answer failed validation twice (original + 1 retry). Last error:\n{problem}")


def write_script(state: State) -> dict:
    topic = state["topic"]
    if config.mock_llm():
        script = Script(**mock.script(topic))
        problems = validate_script(script)      # the mock must pass our own rules too
        assert not problems, problems
        return {"stage": "write_script", "script": script.model_dump(), "notes": "", "fact_feedback": ""}

    sources = "\n\n".join(f"URL: {s['url']}\nTITLE: {s['title']}\nTEXT: {s['snippet']}" for s in state.get("sources", []))
    research = state.get("research_notes", "")
    extra = ""
    if state.get("fact_feedback"):
        extra += f"\n\nFIX THESE FACT-CHECK PROBLEMS from your previous draft:\n{state['fact_feedback']}"
    if state.get("notes"):
        extra += f"\n\nREVIEWER NOTES to apply to your previous draft:\n{state['notes']}"
    if extra and state.get("script"):
        extra += f"\n\nPrevious draft (JSON):\n{state['script']}"

    model = llm.writer().with_structured_output(Script, include_raw=True)
    script = generate_script(model.invoke, [
        ("system", SYSTEM),
        ("human", f"Episode: {topic}\n\nRESEARCH NOTES (from the research agent; values harmless -> destructive, "
                  f"plus the twist fact):\n{research}\n\nSOURCES:\n{sources}{extra}"),
    ])
    return {"stage": "write_script", "script": script.model_dump(), "notes": "", "fact_feedback": ""}
