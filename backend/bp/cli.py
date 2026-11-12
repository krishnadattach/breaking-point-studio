"""Run the graph from the terminal (for testing; the dashboard comes in stage 5).

  python -m bp.cli "A grain of sand vs 10 levels of speed"          # asks you at each review
  python -m bp.cli "..." --auto                                     # approves both reviews automatically
  python -m bp.cli --resume ep-1a2b3c4d                             # continue a stopped episode
"""
import argparse
import sys
import time
import uuid

from langgraph.types import Command

from . import db
from .graph import build_graph, mysql_checkpointer


def pending_interrupt(graph, cfg):
    """Return the payload the graph is waiting on, or None if it is not stopped."""
    for task in graph.get_state(cfg).tasks:
        for it in task.interrupts:
            return it.value
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("topic", nargs="?")
    ap.add_argument("--auto", action="store_true", help="auto-approve both review steps")
    ap.add_argument("--resume", help="episode id to continue")
    ap.add_argument("--notes-once", help="auto mode: send these notes at the first script review, then approve")
    args = ap.parse_args()

    with mysql_checkpointer() as saver:
        graph = build_graph(saver)
        ep = args.resume or f"ep-{uuid.uuid4().hex[:8]}"
        cfg = {"configurable": {"thread_id": ep}}
        payload = None if args.resume else {"episode_id": ep, "topic": args.topic, "fact_loops": 0}
        if not args.resume:
            db.create_episode(ep, args.topic)
        print(f"Episode {ep}")
        notes_pending = args.notes_once
        while True:
            t0 = time.time()
            try:
                for update in graph.stream(payload, cfg, stream_mode="updates"):
                    for node in update:
                        if node != "__interrupt__":
                            print(f"  [{time.time() - t0:6.1f}s] finished node: {node}")
            except Exception as e:                      # show the failure in the episodes table, then re-raise
                db.set_stage(ep, graph.get_state(cfg).values.get("stage", "unknown"), "failed", str(e)[:2000])
                raise
            wait = pending_interrupt(graph, cfg)
            if wait is None:
                print("Graph finished.")
                print("Final state:", {k: v for k, v in graph.get_state(cfg).values.items()
                                       if k in ("stage", "done", "final_video")})
                return
            kind = wait["kind"]
            print(f"\n*** PAUSED for human: {kind}")
            if kind == "script_review":
                bad = [c for c in wait["claims"] if c["status"] == "fail"]
                print(f"    hook: {wait['script']['hook']}\n    twist level: {wait['script']['twist_level']}"
                      f"   failed claims: {len(bad)}")
            else:
                print(f"    video: {wait['video']}")
            if args.auto:
                if kind == "script_review" and notes_pending:
                    answer, notes_pending = {"action": "notes", "notes": notes_pending}, None
                else:
                    answer = {"action": "approve"}
                print(f"    auto answer: {answer}")
            else:
                choice = input("    type 'a' to approve, or type notes to send back: ").strip()
                answer = {"action": "approve"} if choice.lower() in ("a", "approve") else {"action": "notes", "notes": choice}
            payload = Command(resume=answer)


if __name__ == "__main__":
    main()
