# Breaking Point Studio - Original Build Plan

(Saved verbatim from the owner's original brief. Progress is tracked in PROGRESS.md.)

Build "Breaking Point Studio", a GenAI resume project. The owner is a beginner: before each step, explain in
simple terms what is being built and why. Build in stages. After each stage, run it, test it, tell the owner
what to check, and wait for them to say "continue".

## Rules
- WALKING SKELETON first: make every stage work in its simplest form so ONE click in the dashboard produces a
  finished MP4. Video quality does not matter. Improve only after it works end to end.
- This project must be completely self-contained. Copy (don't link) the owner's grid kit from
  ~/impossible-builds/blender/kit into this project's blender/kit folder. Never change anything in
  ~/impossible-builds.
- Never ask the owner to paste API keys into the chat. Tell them which line of .env to fill in and they will do it
  themselves.
- After each stage, update PROGRESS.md with what's done and what's next.
- Keep API costs low: use cheaper models for simple steps. Ask before anything that costs money.

## What it does
A human-in-the-loop multi-agent system that creates videos for the YouTube Shorts channel "The Breaking Point".
In each episode, one object faces 10 escalating levels of heat, cold, pressure, impact speed, lightning or spin
until it fails. Each episode has one surprising twist level and a SURVIVES/DESTROYED verdict per level.

## Tech
Python, LangGraph, LangChain, Claude API, FastAPI, MySQL, React (Vite), Blender, FFmpeg.
Blender is at "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe".

## Stage 1 - Setup
git, .gitignore, .env and .env.example (never commit keys), a Python virtual environment, install MySQL if
missing and create the database, copy the grid kit, and write a CLAUDE.md for this project that includes the
rule "Explain every new file and design decision in simple terms."

## Stage 2 - LangGraph workflow with these nodes
- research: web search for real facts about the object and the ladder (tell the owner if the search tool needs a key)
- write_script: structured output with a hook, 10 levels (narration line, real value, verdict) and the twist level
- fact_check: every claim must link to a source; failed claims go back to write_script, max 2 loops
- review_script: LangGraph interrupt that waits for the owner to approve or send notes
- voiceover: free offline Windows text-to-speech, one audio file per line
- render: Blender with the grid kit, one simple low-res Eevee shot per level (the object on the grid, changing
  colour as the level rises, with a SURVIVES or DESTROYED moment)
- assemble: FFmpeg joins the shots, voice and burned-in captions into one 1080x1920 MP4
- review_video: LangGraph interrupt that waits for the owner's final approval
Use a durable MySQL checkpointer.

## Stage 3 - MySQL tables
episodes, scripts, claims, sources, approvals, and assets (audio, renders, final video paths).

## Stage 4 - FastAPI
Endpoints to start an episode, list episodes, view one, approve, or reject with notes (which resumes the graph).
Rendering takes minutes, so run the graph in the background and let the dashboard poll for status.

## Stage 5 - React dashboard
A new-episode form; an episode list showing which stage each episode is on; a script review page with each
claim's source link and Approve / Send Notes buttons; and a video page with a player, a download button and
final approval.

## Stage 6 - Finish
Create a start.bat that launches the backend and the dashboard together. Run "A grain of sand vs 10 levels of
speed" end to end with one click. Write a README with what it does, an architecture diagram in Mermaid, how to
run it, and a roadmap (better voice, better visuals, visual QA, evals, analytics). Commit everything and help
the owner push it to GitHub.

---

## Changes the owner made while building (after the original brief)
- Stage 1 follow-up: the app must not connect to MySQL as root. A dedicated user (`bp_app`) with a strong random
  password, written into .env by Claude, is used from now on.
- Stage 1 follow-up: the grid kit copy was cleaned. The tests folder (previews, old MP4, Dyson test) was removed
  and `ib_kit.py` was renamed to `grid_kit.py`, with all references updated.
