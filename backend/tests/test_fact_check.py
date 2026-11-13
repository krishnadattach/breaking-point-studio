"""Free test of fact_check (no API calls): a fake 'cheap model' plays the checker.
Proves: reasoning comes BEFORE the verdict in the format, the hook is checked as item 0, a failed hook goes back to
the writer, and a hook that only asks a question needs no source.
Run from the backend folder:  ..\\.venv\\Scripts\\python -m tests.test_fact_check
"""
import uuid

from bp import db, llm, mock
from bp.nodes import fact_check as fc
from bp.state import ClaimCheck, ClaimChecks


class FakeCheaper:
    """Replaces llm.cheap(): remembers what it was asked and answers with a scripted verdict per item."""
    def __init__(self, verdicts):      # {item number: (reason, supported)}
        self.verdicts, self.asked = verdicts, ""

    def with_structured_output(self, schema):
        assert schema is ClaimChecks
        return self

    def invoke(self, messages):
        self.asked = messages[-1][1]
        items = [int(line.split()[1]) for line in self.asked.splitlines() if line.startswith("ITEM ")]
        return ClaimChecks(checks=[ClaimCheck(level=i, reason=self.verdicts.get(i, ("Source matches.", True))[0],
                                              supported=self.verdicts.get(i, ("", True))[1]) for i in items])


def run(script, verdicts):
    ep = "test-" + uuid.uuid4().hex[:8]
    db.init_db()
    db.create_episode(ep, "A grain of sand vs 10 levels of speed")
    sources = [{"url": "https://example.com/mock-source-1", "title": "t", "snippet": "sand is a granular material"}]
    fake = FakeCheaper(verdicts)
    real_cheap, real_mock = llm.cheap, fc.config.mock_llm
    llm.cheap, fc.config.mock_llm = (lambda: fake), (lambda: False)     # pretend we are in real mode, with a fake model
    try:
        out = fc.fact_check({"episode_id": ep, "script": script, "sources": sources, "fact_loops": 0})
        saved = db.get_episode(ep)["script"]["claims"]
    finally:
        llm.cheap, fc.config.mock_llm = real_cheap, real_mock
        with db.connect() as c, c.cursor() as cur:
            cur.execute("DELETE FROM episodes WHERE id=%s", (ep,))
    return out, fake, saved


def main():
    # 1. the answer format puts the reasoning before the verdict
    fields = list(ClaimCheck.model_json_schema()["properties"])
    assert fields.index("reason") < fields.index("supported"), fields
    print("OK: schema order is", fields, "(reason before supported)")

    script = mock.script("A grain of sand vs 10 levels of speed")

    # 2. everything fine -> hook (item 0) was sent to the checker, no loop
    out, fake, saved = run(script, {})
    assert "ITEM 0 (THE HOOK)" in fake.asked, fake.asked[:200]
    assert out["fact_feedback"] == "" and len(saved) == 11 and saved[0]["level"] == 0
    print("OK: hook is checked as item 0; 11 claims saved (hook + 10 levels)")

    # 3. a false hook (the real run's 'tiniest rock on Earth') fails and goes back to the writer
    bad = dict(script, hook="One grain of sand: the tiniest rock on Earth. Where does it break?",
               hook_source_url="https://example.com/mock-source-1")
    out, _, saved = run(bad, {0: ("Silt and clay are smaller, so this overclaims.", False)})
    assert saved[0]["status"] == "fail" and "overclaims" in saved[0]["reason"]
    assert out["fact_feedback"].startswith("The HOOK:") and out["fact_loops"] == 1, out
    print("OK: a false hook fails and is sent back with feedback:", out["fact_feedback"][:60], "...")

    # 4. a hook with a source URL that is not in the research list fails without even asking the model
    bad2 = dict(script, hook_source_url="https://not-researched.example/x")
    out, _, saved = run(bad2, {})
    assert saved[0]["status"] == "fail" and "not one of the researched sources" in saved[0]["reason"]
    print("OK: hook with an unknown source URL fails")


if __name__ == "__main__":
    main()
