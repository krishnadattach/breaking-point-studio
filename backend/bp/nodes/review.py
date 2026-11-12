"""NODES 4 and 8 - the two human checkpoints (LangGraph interrupts).

How interrupt() works: the graph STOPS here and its whole state is saved in
MySQL. Later (even after a restart) someone resumes it with a value, e.g.
{"action": "approve"} or {"action": "notes", "notes": "make level 3 funnier"}.
That value becomes the return value of interrupt().
"""
from langgraph.types import interrupt

from .. import db
from ..state import State


def review_script(state: State) -> dict:
    db.set_stage(state["episode_id"], "review_script", "waiting_script_review")
    answer = interrupt({"kind": "script_review", "script": state["script"], "claims": state.get("claims", [])})
    db.add_approval(state["episode_id"], "script", answer.get("action", "notes"), answer.get("notes", ""))
    if answer.get("action") == "approve":
        return {"stage": "review_script", "script_decision": "approve", "notes": ""}
    return {"stage": "review_script", "script_decision": "notes", "notes": answer.get("notes", ""),
            "fact_loops": 0}


def route_after_review_script(state: State) -> str:
    return "voiceover" if state.get("script_decision") == "approve" else "write_script"


def review_video(state: State) -> dict:
    db.set_stage(state["episode_id"], "review_video", "waiting_video_review")
    answer = interrupt({"kind": "video_review", "video": state["final_video"]})
    db.add_approval(state["episode_id"], "video", answer.get("action", "notes"), answer.get("notes", ""))
    if answer.get("action") == "approve":
        db.set_stage(state["episode_id"], "done", "done")
        return {"stage": "done", "video_decision": "approve", "done": True}
    return {"stage": "review_video", "video_decision": "notes", "notes": answer.get("notes", ""),
            "fact_loops": 0}


def route_after_review_video(state: State) -> str:
    return "__end__" if state.get("video_decision") == "approve" else "write_script"
