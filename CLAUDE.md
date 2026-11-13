# Breaking Point Studio

A human-in-the-loop agentic workflow (LangGraph; LLM steps in a graph, not autonomous agents) that makes YouTube Shorts for "The Breaking Point":
one object faces 10 escalating levels of heat, cold, pressure, impact speed, lightning or spin until it fails.
Each episode has one surprising twist level and a SURVIVES/DESTROYED verdict per level.

## Rules
(The full original build plan is in `PLAN.md`; current status in `PROGRESS.md`.)
- **Explain every new file and design decision in simple terms.** The owner is a beginner.
- Build in stages; after each stage run it, test it, say what to check, and wait for "continue".
- Walking skeleton first: simplest working version end to end, improve later.
- Self-contained: never link to or modify `~/impossible-builds`. The grid kit lives in `blender/kit` (a copy).
- Never ask for API keys in chat. Tell the owner which `.env` line to fill in. Never commit `.env`.
- Keep API costs low: cheap model (`MODEL_CHEAP`) for simple steps. Ask before anything that costs money.
- After each stage update `PROGRESS.md` (done / next).

## Stack
Python + LangGraph + LangChain + Claude API, FastAPI, MySQL 8+, React (Vite), Blender (Eevee), FFmpeg.

## Layout
- `backend/` Python: graph, API, DB
- `frontend/` React dashboard
- `blender/kit/` copied grid kit; `blender/` render scripts
- `output/` generated audio/renders/videos (git-ignored)
- Python env: `.venv` (use `.venv\Scripts\python`)

## Database
Project-local MySQL 8.4 on port 3307 (data in `mysql-data/`, start with `scripts/start_mysql.bat`).
The old system MySQL 5.1 on port 3306 is not used. Root has an empty password, bound to localhost only (dev only).
