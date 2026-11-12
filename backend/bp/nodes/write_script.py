"""NODE 2 - write_script: Claude writes the structured episode script.

Why structured output: instead of free text we force Claude to fill in a form
(hook, 10 levels, twist level, a source per claim). That makes later steps
(fact-check, voice, render) reliable.
It also receives human notes and fact-check feedback when the graph loops back here.
"""
from .. import config, llm, mock
from ..state import Script, State

SYSTEM = """You write scripts for the YouTube Shorts channel "The Breaking Point".
One object faces 10 escalating levels of one hazard (heat, cold, pressure, impact speed, lightning or spin) until it fails.
Rules:
- Exactly 10 levels, strictly escalating, each with a REAL value and unit taken from the sources.
- Each level has one SURVIVES or DESTROYED verdict. The object fails somewhere sensible, but there is exactly ONE
  twist level where the result is the opposite of what viewers expect.
- Each narration line is short (max 25 words), spoken, and ends by naming the verdict.
- Every level's claim must be supported by one of the provided source URLs. Use ONLY those URLs. Do not invent facts."""


def write_script(state: State) -> dict:
    topic = state["topic"]
    if config.mock_llm():
        return {"stage": "write_script", "script": mock.script(topic), "notes": "", "fact_feedback": ""}

    sources = "\n\n".join(f"URL: {s['url']}\nTITLE: {s['title']}\nTEXT: {s['snippet']}" for s in state.get("sources", []))
    extra = ""
    if state.get("fact_feedback"):
        extra += f"\n\nFIX THESE FACT-CHECK PROBLEMS from your previous draft:\n{state['fact_feedback']}"
    if state.get("notes"):
        extra += f"\n\nREVIEWER NOTES to apply to your previous draft:\n{state['notes']}"
    if extra and state.get("script"):
        extra += f"\n\nPrevious draft (JSON):\n{state['script']}"

    model = llm.writer().with_structured_output(Script)
    script: Script = model.invoke([
        ("system", SYSTEM),
        ("human", f"Episode: {topic}\n\nSOURCES:\n{sources}{extra}"),
    ])
    return {"stage": "write_script", "script": script.model_dump(), "notes": "", "fact_feedback": ""}
