# Progress

The full build plan and rules are in [PLAN.md](PLAN.md). Last updated: 2026-11-12.

| Stage | Status |
|---|---|
| 1 - Setup | DONE |
| 2 - LangGraph workflow | DONE (mock-tested) |
| 3 - MySQL tables | DONE (mock-tested) |
| 4 - FastAPI | next |
| 5 - React dashboard | not started |
| 6 - Finish (start.bat, README, GitHub) | not started |

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

## Next
Stage 4 - FastAPI: start episode, list, view one, approve / send notes (resumes the graph), graph runs in the
background and the dashboard polls status. Plan: reuse the graph; one background thread per running episode.
