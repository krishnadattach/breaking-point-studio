# Progress

The full build plan and rules are in [PLAN.md](PLAN.md). Last updated: 2026-11-12 (Stage 7).

| Stage | Status |
|---|---|
| 1 - Setup | DONE |
| 2 - LangGraph workflow | DONE (one real run completed) |
| 3 - MySQL tables | DONE (mock-tested) |
| 4 - FastAPI | DONE (mock-tested) |
| 5 - React dashboard | DONE (builds; owner to click through) |
| 6 - Finish (start.bat, README, GitHub) | DONE |
| 7 - Upgrades (research agent, robust writer, approve safeguard) | DONE (mock/fake-tested; real run pending) |

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

## Stage 6 - Finish (DONE)
- Dashboard fix: Stage column shows "Done" (`stageLabel` in frontend/src/stages.js).
- start.bat (MySQL + backend + dashboard + browser) and start_mock.bat (same, free mock mode). From a terminal use
  `.\start.bat` (plain `start.bat` is read by cmd as its built-in `start`).
- Personal paths removed: scripts/my8.ini is generic (start_mysql.bat passes basedir/datadir); the path comment in
  grid_kit.py is generic; both scrubbed from old commits too.
- Git identity for this repo: Krishna Datta + GitHub noreply email. All commits rewritten, old refs/reflog purged.
  History scanned: no API key, DB password, old email or personal path in any commit. `.env` was never tracked.
- Mock data deleted (3 episodes, orphan checkpoints, output folders) before the real run.
- FIRST REAL RUN (Claude + Tavily) of "A grain of sand vs 10 levels of speed": completed end to end (episode
  ep-eac294e0, script approved, 25 MB final.mp4, video approved). Bug found by the real run and fixed: Sonnet 5.5
  "thinks" and used up max_tokens=4000, truncating the structured script (missing `levels`). Now writer 16000 /
  cheap 8000 (a ceiling only; billed per token used).
- README.md written (what it does, Mermaid architecture diagram, setup, how to run, roadmap).
- gh CLI installed; owner signs in with `gh auth login`.

## Stage 7 - Upgrades (DONE, tested in mock/fake mode only)
- **Research is a real tool-using agent** (backend/bp/nodes/research.py): LangChain `create_agent` + the cheap model + one
  tool `web_search` (Tavily). It chooses its own queries, reads results, fills gaps, decides when to stop. Hard limit 5
  searches (counted inside the tool, thread-safe; a 6th call just gets "limit reached"). Ends with a FINDINGS / TWIST FACT
  / GAPS summary, passed to the writer as `research_notes`. Safety: one fallback search if it never searched; step limit.
- DB: new table `research_queries` (every query, result count, URLs, in order, written live) + `episodes.research_notes`
  (added automatically by `init_db` on older databases). `GET /episodes/{id}` now has `research: {queries, notes}`.
- Dashboard: new "Research" tab / live panel on the episode page: "N of 5 searches used", each query, results, summary.
- Mock mode unchanged for the owner: with either key missing (or MOCK_LLM/MOCK_SEARCH=1) research records 3 labelled MOCK
  queries and fake sources, free.
- **write_script is robust**: structured output is requested with `include_raw`, then `validate_script` checks 10 levels
  numbered 1-10, distinct values, level 1 SURVIVES, at least one DESTROYED, narration length, twist level 3-9 whose
  verdict differs from the level before it. Invalid -> ONE retry that includes the validation error; still invalid ->
  clear error (episode shows Retry). At most 2 Sonnet calls per attempt.
- **Writer prompt**: level 1 harmless, level 10 extreme, steady spread, no single threshold table; the twist must be a real
  surprise (best: SURVIVES where viewers expect failure, not just another DESTROYED). The mock script follows the same rules.
- **Dashboard safeguard**: ScriptReview shows an orange warning listing failed levels; Approve then needs a second
  "Yes, approve with N failed claims" click (or Cancel). This is a dashboard check only; the API itself still accepts approve.
- Tests (free, no API calls): `cd backend; ..\.venv\Scripts\python -m tests.test_research_agent` (scripted fake model:
  proves the 5-search limit, early stop, fallback, DB rows) and `... -m tests.test_write_script` (validator + retry).
  Also: a full mock episode over HTTP reached script review with 3 queries saved; `npm run build` OK; the review
  component was rendered with fake failed claims (warning shows only when claims failed).
- NOT yet tested with real Claude/Tavily: how well Haiku drives the agent, and whether the new writer prompt gives a
  better spread and twist. Needs one real run (ask the owner first; it adds <= 5 Tavily searches and a few cheap Haiku
  calls on top of the usual Sonnet script). The Approve confirmation click flow was not clicked in a browser.
- Incident: while testing, a start request went to an OLDER backend still running on port 8000 in real mode, which began
  a real run (one Tavily research pass and the start of a Sonnet call, a few cents at most). It was stopped at once and
  its episode deleted. Before mock tests, check nothing else is listening on the port.

## Known quality issues (for the roadmap)
- Seen in the real run before Stage 7 (should improve now, not re-checked): levels 1-6 were all tiny speeds from one
  threshold table; the "twist" was also DESTROYED; 3 claims still failed after the 2-loop maximum.
- fact_check only sees each source's search excerpt (<= 1200 chars), so correct claims can still fail.
- Skeleton visuals/voice as listed above.

## GitHub
- PUBLIC repo: https://github.com/krishnadattach/breaking-point-studio (branch main, remote `origin`).
- Verified from a fresh clone of GitHub: all commits by Krishna Datta (noreply email); no .env, output/, mysql-data/;
  the real API keys / DB password appear in no commit; no personal path or old email.
- README and CLAUDE.md say "agentic workflow" (not multi-agent); research is now the one tool-using agent.

## Next (roadmap, see README)
1. One REAL run (ask the owner first) to judge the agent's queries and the new script quality.
2. Page-reader tool for the research agent; better voice and visuals; visual QA; evals; analytics.
