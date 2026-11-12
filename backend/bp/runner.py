"""Runs the graph in the background so the API can answer instantly.

Rendering takes minutes, so a web request must never wait for it. Instead each
episode gets its own background THREAD. The thread runs the graph until it either
finishes or stops at a human review (interrupt), then the thread ends. The
dashboard just asks the API "what stage is episode X on?" every few seconds.

The graph's progress lives in MySQL (the checkpointer), not in the thread, so a
thread ending (or the server restarting) loses nothing.
"""
import threading
import uuid

from langgraph.types import Command

from . import db
from .graph import build_graph, mysql_checkpointer

_running: set[str] = set()          # episode ids that currently have a live thread
_lock = threading.Lock()


def is_running(episode_id: str) -> bool:
    with _lock:
        return episode_id in _running


def _work(episode_id: str, payload):
    """Thread body: run the graph from where it stopped until the next pause or the end."""
    cfg = {"configurable": {"thread_id": episode_id}}
    try:
        with mysql_checkpointer() as saver:
            graph = build_graph(saver)
            for _ in graph.stream(payload, cfg, stream_mode="updates"):
                pass
    except Exception as e:                       # show the failure in the episodes table
        stage = "unknown"
        try:
            stage = graph.get_state(cfg).values.get("stage", "unknown")
        except Exception:
            pass
        db.set_stage(episode_id, stage, "failed", str(e)[:2000])
    finally:
        with _lock:
            _running.discard(episode_id)


def _launch(episode_id: str, payload) -> bool:
    """Start a thread unless this episode already has one. Returns False if it was busy."""
    with _lock:
        if episode_id in _running:
            return False
        _running.add(episode_id)
    threading.Thread(target=_work, args=(episode_id, payload), daemon=True, name=episode_id).start()
    return True


def start_episode(topic: str) -> str:
    episode_id = f"ep-{uuid.uuid4().hex[:8]}"
    db.create_episode(episode_id, topic)
    _launch(episode_id, {"episode_id": episode_id, "topic": topic, "fact_loops": 0})
    return episode_id


def resume_with_answer(episode_id: str, answer: dict) -> bool:
    """Wake a paused graph with the human's answer. The status flips right away so the
    dashboard (and a double click) can't send a second answer."""
    with _lock:
        if episode_id in _running:
            return False
    db.set_stage(episode_id, "resuming")
    return _launch(episode_id, Command(resume=answer))


def retry(episode_id: str) -> bool:
    """Continue a failed / interrupted episode from its last saved checkpoint."""
    db.set_stage(episode_id, "resuming")
    return _launch(episode_id, None)


def mark_orphans():
    """On server start: episodes marked 'running' have no thread any more (server was restarted)."""
    for ep in db.list_episodes():
        if ep["status"] == "running":
            db.set_stage(ep["id"], ep["stage"], "failed", "Server restarted while this was running. Use Retry.")
