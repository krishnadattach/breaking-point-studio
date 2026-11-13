"""The 'clipboard' every node reads from and writes to, plus the script format.

Why: LangGraph passes one State dict between nodes. Each node returns only
the keys it changed. Keeping the shape in one file keeps things understandable.
"""
from typing import Literal, TypedDict

from pydantic import BaseModel, Field


# ---- the script format Claude must follow (structured output) ----
class Level(BaseModel):
    n: int = Field(description="Level number 1-10, escalating")
    narration: str = Field(description="One spoken line, max ~25 words. Ends by naming the verdict.")
    value: str = Field(description="The real measured value for this level, with unit, e.g. '340 m/s'")
    verdict: Literal["SURVIVES", "DESTROYED"]
    claim: str = Field(description="The single factual claim behind this level, as one checkable sentence")
    source_url: str = Field(description="URL from the research sources that supports the claim")


class Script(BaseModel):
    hook: str = Field(description="Opening line, max ~20 words, makes people stay. Any factual statement in it must be "
                                  "true and supported by a research source; a pure question is safest.")
    hook_source_url: str = Field(default="", description="URL from the research sources that supports any factual "
                                 "statement in the hook. Empty ONLY if the hook states no facts (just a question/teaser).")
    shape: Literal["sphere", "cube", "cone"] = Field(description="Simple 3D stand-in for the object")
    hazard: str = Field(description="heat, cold, pressure, impact speed, lightning or spin")
    twist_expectation: str = Field(default="", description="What most viewers would EXPECT to happen at the twist level "
                                   "(e.g. 'a fragile grain of sand shatters')")
    twist_explanation: str = Field(default="", description="What really happens at the twist level and why it is "
                                   "surprising, based on the research (one or two sentences)")
    twist_level: int = Field(description="The one twist level (3-9): the object SURVIVES where viewers expect it to fail")
    levels: list[Level] = Field(description="Exactly 10 levels")


# ---- fact-check result for one claim ----
# FIELD ORDER MATTERS: the model writes the fields in this order, so it must write its reasoning BEFORE it commits to
# the verdict. (Before, the verdict came first and the explanation sometimes contradicted it.)
class ClaimCheck(BaseModel):
    level: int = Field(description="The item number (0 = the hook)")
    reason: str = Field(description="Reasoning FIRST: compare the claim with the source text, then end with your "
                                    "conclusion in plain words")
    supported: bool = Field(description="The final verdict, decided only after the reasoning above. It MUST agree "
                                        "with the conclusion you just wrote.")


class ClaimChecks(BaseModel):
    checks: list[ClaimCheck]


class State(TypedDict, total=False):
    episode_id: str
    topic: str                 # e.g. "A grain of sand vs 10 levels of speed"
    stage: str                 # which node is active - the dashboard shows this
    sources: list[dict]        # [{url, title, snippet}]
    research_notes: str        # the research agent's findings summary (values harmless -> destructive + twist fact)
    script: dict               # Script as a dict
    claims: list[dict]         # [{level, claim, source_url, status, reason}]
    fact_loops: int
    fact_feedback: str         # why claims failed, fed back to write_script
    notes: str                 # reviewer notes from the human
    script_decision: str       # "approve" | "notes"
    audio: list[dict]          # [{label, text, path, seconds}]
    shots: list[dict]          # [{label, path}]
    final_video: str
    video_decision: str        # "approve" | "notes"
    done: bool
    error: str
