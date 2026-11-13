"""Free test of write_script's validation + retry (no API calls).
Run from the backend folder:  ..\\.venv\\Scripts\\python -m tests.test_write_script
"""
from bp import mock
from bp.nodes.write_script import generate_script, validate_script
from bp.state import Script


def good() -> Script:
    return Script(**mock.script("A grain of sand vs 10 levels of speed"))


def bad_same_verdict_twist() -> Script:
    s = good()
    s.levels[6].verdict = "DESTROYED"          # twist level 7 is now just another DESTROYED
    return s


class FakeInvoke:
    """Plays the model: returns the given answers one by one and remembers the messages it was sent."""
    def __init__(self, answers):
        self.answers, self.sent = list(answers), []

    def __call__(self, messages):
        self.sent.append(messages)
        return self.answers.pop(0)


def main():
    assert validate_script(good()) == [], validate_script(good())
    print("OK: the mock script passes validation")

    probs = validate_script(bad_same_verdict_twist())
    assert any("not a real surprise" in p for p in probs), probs
    print("OK: a DESTROYED-after-DESTROYED twist is rejected:", probs[0][:60], "...")

    s = good(); s.levels = s.levels[:9]
    assert any("exactly 10" in p for p in validate_script(s))
    s = good(); s.levels[0].verdict = "DESTROYED"
    assert any("Level 1" in p for p in validate_script(s))
    print("OK: wrong level count and a non-harmless level 1 are rejected")

    # 1. valid on the first try -> no retry
    f = FakeInvoke([{"parsed": good()}])
    generate_script(f, [("system", "s"), ("human", "h")])
    assert len(f.sent) == 1
    print("OK: valid answer, 1 call")

    # 2. invalid first, valid second -> exactly one retry, and the retry message contains the validation error
    f = FakeInvoke([{"parsed": bad_same_verdict_twist()}, {"parsed": good()}])
    generate_script(f, [("system", "s"), ("human", "h")])
    assert len(f.sent) == 2
    retry_msg = f.sent[1][-1][1]
    assert "not a real surprise" in retry_msg and "REJECTED" in retry_msg, retry_msg
    print("OK: retried once with the validation error in the prompt")

    # 3. the model's answer did not even parse (pydantic error) -> retry with that error
    f = FakeInvoke([{"parsed": None, "parsing_error": ValueError("field 'levels' is required")}, {"parsed": good()}])
    generate_script(f, [("system", "s"), ("human", "h")])
    assert "field 'levels' is required" in f.sent[1][-1][1]
    print("OK: parse error is passed to the retry")

    # 4. invalid twice -> clear error, only 2 calls (no endless loop = no runaway cost)
    f = FakeInvoke([{"parsed": bad_same_verdict_twist()}, {"parsed": bad_same_verdict_twist()}])
    try:
        generate_script(f, [("system", "s"), ("human", "h")])
        raise SystemExit("should have raised")
    except RuntimeError as e:
        assert len(f.sent) == 2 and "failed validation twice" in str(e)
    print("OK: gives up after one retry with a clear error")


if __name__ == "__main__":
    main()
