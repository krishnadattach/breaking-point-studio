# Progress

The full build plan and rules are in [PLAN.md](PLAN.md). Last updated: 2026-11-12.

| Stage | Status |
|---|---|
| 1 - Setup | DONE |
| 2 - LangGraph workflow | DONE (mock-tested) |
| 3 - MySQL tables | DONE (mock-tested) |
| 4 - FastAPI | DONE (mock-tested) |
| 5 - React dashboard | DONE (builds; owner to click through) |
| 6 - Finish (start.bat, README, GitHub) | IN PROGRESS |

## Stage 1 - Setup (DONE)
- git repo, .gitignore (ignores .env, .venv, output/, mysql-data/), .env / .env.example, .venv
- Grid kit copied to blender/kit and cleaned: tests/ removed, ib_kit.py renamed grid_kit.py
  (kept: grid_kit.py, STYLE.md, compare.py, 2 reference images)
- MySQL 8.4 installed beside the old 5.1: port 3307, data in mysql-data/, started by scripts/start_mysql.bat
- Database `breaking_point`; app user `bp_app` (rights on that database only, random password stored only in .env)
- CLAUDE.md with the project rules

## Stage 2 - LangGraph workflow (DONE)
- 8 nodes in backend/bp/nodes: research, write_script, fact_check (max 2 loops), review_script (interrupt),
  voiceover (Windows SAPI, one wav per line), render (Blender + grid kit via blender/render_level.py),
  assemble (FFmpeg -> 1080x1920 MP4 with burned-in captions, level header, verdict word), review_video (interrupt)
- Durable MySQL checkpointer (PyMySQLSaver). Tested: a crashed run resumed from MySQL in a new process.
- Mock mode (free) is automatic when a key is missing, or forced with MOCK_LLM=1 / MOCK_SEARCH=1.
- Test run: `cd backend; ..\.venv\Scripts\python -m bp.cli "topic" --auto`
- Tested in MOCK mode only: full run, notes loop, durable resume, 67 s final video. Render takes about 5 min.
- Fixed along the way: newest Claude models reject a custom `temperature` (removed); PowerShell 5.1 JSON list
  quirk in tts.ps1.

## Open items / things to remember
- ANTHROPIC_API_KEY and TAVILY_API_KEY are filled in .env, so the pipeline uses REAL Claude/search unless mock is
  forced. Real runs cost money: ask the owner before the first real run (planned for Stage 6).
- NOT yet tested with real Claude or Tavily (fact_check's source-text check in particular).
- Skeleton limits: object is a plain sphere; the verdict flash is at 60% of each shot, not synced to the spoken word.
- Stages 1-2 committed; from now on commit after each finished stage. GitHub push happens in Stage 6.
- The old MySQL 5.1 on port 3306 is untouched and unused.

## Stage 3 - MySQL tables (DONE)
- backend/bp/db.py: 6 readable tables beside LangGraph's own checkpoint tables, created automatically on start:
  episodes (topic, stage, status, error), sources, scripts (new version per draft), claims (per level, pass/fail),
  approvals (every approve/notes decision), assets (audio, render, final_video paths; re-runs replace rows).
- Nodes write to them: research->sources, fact_check->scripts+claims, review nodes->approvals + status
  (waiting_script_review / waiting_video_review / done), voiceover/render/assemble->assets. A wrapper in graph.py
  updates `episodes.stage` as each node starts. cli.py creates the episode row and marks `failed` on errors.
- Read helpers for Stage 4: db.list_episodes(), db.get_episode(id).
- Tested in mock mode: full run with one notes loop -> 2 script versions, 10 claims, 3 approvals, 23 assets.

## Stage 4 - FastAPI (DONE)
- backend/bp/runner.py: runs the graph in a background thread per episode (starts, or resumes after a review). A
  set of running ids stops double-resumes. On server start, episodes left 'running' are marked failed (-> Retry).
- backend/bp/api.py: POST /episodes, GET /episodes, GET /episodes/{id}, POST /episodes/{id}/approve,
  POST /episodes/{id}/reject {notes}, POST /episodes/{id}/retry, GET /episodes/{id}/video. CORS allows the Vite
  dashboard on port 5173. Clickable test page at /docs.
- Start: `cd backend; ..\.venv\Scripts\python -m uvicorn bp.api:app --port 8000`
  (add MOCK_LLM=1 MOCK_SEARCH=1 to the environment for free test runs).
- Tested in mock mode over HTTP: start -> script review -> notes -> script review -> approve -> render ->
  video review -> download (18 MB mp4) -> approve -> done. Also: empty notes (422), double approve (409), unknown id (404).

## Stage 5 - React dashboard (DONE)
- frontend/ = Vite + React (plain JS, no router/UI library). Dark theme, cyan #00C2FF + orange #FF6B2C accents
  (cyan = normal/go, orange = needs your attention / twist level).
- src/api.js (all backend calls), src/usePolling.js (asks the backend again every 3 s while working, 6 s while waiting),
  src/stages.js (8 stage names), src/components.jsx (badge, 8-dot stage track), src/styles.css.
- pages/EpisodeList.jsx: new-episode form + episode list (stage, status, rows needing you are marked orange).
- pages/EpisodePage.jsx: one episode; stage track, progress, error box + Retry, Script / Video tabs.
- pages/ScriptReview.jsx: hook, 10 levels (value, verdict, twist highlighted), each claim with Checked/Failed
  and its source link, Approve / Send notes (notes required), earlier decisions.
- pages/VideoPage.jsx: 9:16 player, Download MP4, final Approve / Send notes.
- Tested: `npm run build` OK; dev server + backend (mock) up; a mock episode reached script review and the API data
  matches what the pages read. Not yet clicked through in a browser by the owner.
- Start: backend as in Stage 4, then `cd frontend; npm run dev` -> http://localhost:5173

## Stage 6 - Finish (IN PROGRESS)
Done so far:
- Dashboard fix: Stage column shows "Done" (was lowercase `done`); stages.js `stageLabel`.
- Git identity set for this repo to Krishna Datta + GitHub noreply email; all 4 old commits rewritten, old refs/reflog
  purged (no trace of the old email). History scanned: the real API keys / DB password appear in no commit.
- start.bat written (MySQL + backend + dashboard + browser; `start.bat mock` = free mode). Not yet run: the
  Stage 4-5 test servers are still running on ports 8000/5173/3307 and must be stopped first.

Next:
1. OWNER APPROVAL for the first real (paid) run, then delete the 3 old mock episodes (DB rows + checkpoints + output/ folders).
2. Test start.bat, run "A grain of sand vs 10 levels of speed" for real, end to end.
3. README (what it does, Mermaid diagram, how to run, roadmap).
4. Commit; create the PUBLIC GitHub repo (gh CLI not installed yet) and push.
