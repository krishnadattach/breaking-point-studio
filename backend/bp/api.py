"""The web API (FastAPI). The React dashboard (stage 5) talks only to this.

Run:  cd backend; ..\.venv\Scripts\python -m uvicorn bp.api:app --port 8000
Docs: http://127.0.0.1:8000/docs  (FastAPI makes a clickable test page for free)

Endpoints
  POST /episodes                  start an episode  {"topic": "..."}
  GET  /episodes                  list all (id, topic, stage, status)
  GET  /episodes/{id}             everything about one (script, claims, sources, approvals, assets)
  POST /episodes/{id}/approve     approve the script or the video (whichever is waiting)
  POST /episodes/{id}/reject      send notes back  {"notes": "..."}  (needs notes)
  POST /episodes/{id}/retry       continue a failed episode
  GET  /episodes/{id}/video       the final MP4 (for the player / download)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import config, db, runner

WAITING = {"waiting_script_review", "waiting_video_review"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    runner.mark_orphans()
    yield


app = FastAPI(title="Breaking Point Studio", lifespan=lifespan)
# The dashboard runs on another port (Vite, 5173), so the browser needs permission to call us.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


class NewEpisode(BaseModel):
    topic: str = Field(min_length=3, max_length=300)


class Notes(BaseModel):
    notes: str = Field(min_length=1, max_length=4000)


def _episode_or_404(episode_id: str) -> dict:
    ep = db.get_episode(episode_id)
    if not ep:
        raise HTTPException(404, "No such episode")
    return ep


def _answer(episode_id: str, answer: dict) -> dict:
    ep = _episode_or_404(episode_id)
    if ep["status"] not in WAITING:
        raise HTTPException(409, f"Episode is not waiting for a review (status: {ep['status']})")
    if not runner.resume_with_answer(episode_id, answer):
        raise HTTPException(409, "Episode is already busy")
    return {"id": episode_id, "status": "running"}


@app.post("/episodes", status_code=201)
def create_episode(body: NewEpisode):
    return {"id": runner.start_episode(body.topic.strip()), "status": "running"}


@app.get("/episodes")
def list_episodes():
    return db.list_episodes()


@app.get("/episodes/{episode_id}")
def get_episode(episode_id: str):
    return _episode_or_404(episode_id)


@app.post("/episodes/{episode_id}/approve")
def approve(episode_id: str):
    return _answer(episode_id, {"action": "approve"})


@app.post("/episodes/{episode_id}/reject")
def reject(episode_id: str, body: Notes):
    return _answer(episode_id, {"action": "notes", "notes": body.notes.strip()})


@app.post("/episodes/{episode_id}/retry")
def retry(episode_id: str):
    ep = _episode_or_404(episode_id)
    if ep["status"] != "failed":
        raise HTTPException(409, "Only failed episodes can be retried")
    if not runner.retry(episode_id):
        raise HTTPException(409, "Episode is already busy")
    return {"id": episode_id, "status": "running"}


@app.get("/episodes/{episode_id}/video")
def video(episode_id: str):
    ep = _episode_or_404(episode_id)
    final = next((a for a in ep["assets"] if a["kind"] == "final_video"), None)
    if not final:
        raise HTTPException(404, "No video yet")
    path = config.ROOT / final["path"]          # absolute paths stay as they are
    if not path.is_file():
        raise HTTPException(404, "Video file is missing")
    return FileResponse(path, media_type="video/mp4", filename=f"{episode_id}.mp4")
