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
    hook: str = Field(description="Opening line, max ~20 words, makes people stay")
    shape: Literal["sphere", "cube", "cone"] = Field(description="Simple 3D stand-in for the object")
    hazard: str = Field(description="heat, cold, pressure, impact speed, lightning or spin")
    twist_level: int = Field(description="The one surprising level (1-10): result opposite to expectation")
    levels: list[Level] = Field(description="Exactly 10 levels")


# ---- fact-check result for one claim ----
class ClaimCheck(BaseModel):
    level: int
    supported: bool
    reason: str


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
