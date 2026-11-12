"""NODE 6 - render: one simple low-res Eevee shot per spoken line, made by Blender.

For each line we start Blender in the background (no window) with
blender/render_level.py, which uses the grid kit. Already-finished shots are
skipped, so if the computer crashes halfway, resuming does not redo them.
"""
import json
import subprocess

from .. import config, db
from ..state import State

TAIL = 0.7            # seconds of calm after the voice stops
VERDICT_AT = 0.6      # the SURVIVES/DESTROYED moment happens at 60% of the shot


def shot_seconds(audio_seconds: float) -> float:
    return round(audio_seconds + TAIL, 2)


def render(state: State) -> dict:
    ep = config.episode_dir(state["episode_id"])
    out = ep / "renders"
    out.mkdir(exist_ok=True)
    script = state["script"]
    levels = {lv["n"]: lv for lv in script["levels"]}

    shots = []
    for a in state["audio"]:
        n = a["level"]
        mp4 = out / f"{a['label']}.mp4"
        shots.append({"label": a["label"], "path": str(mp4), "seconds": shot_seconds(a["seconds"])})
        if mp4.exists() and mp4.stat().st_size > 0:
            continue                                   # resume: already rendered
        params = {
            "out": str(mp4), "level": n, "shape": script["shape"],
            "verdict": levels[n]["verdict"] if n else None,
            "seconds": shot_seconds(a["seconds"]), "fps": config.RENDER_FPS,
            "samples": config.RENDER_SAMPLES, "verdict_at": VERDICT_AT,
        }
        pfile = out / f"{a['label']}.json"
        pfile.write_text(json.dumps(params), encoding="utf-8")
        r = subprocess.run([config.BLENDER_PATH, "-b", "-P", str(config.BLENDER_SCRIPT), "--", str(pfile)],
                           capture_output=True, text=True, timeout=900)
        (out / f"{a['label']}.log").write_text(r.stdout + "\n" + r.stderr, encoding="utf-8")
        if r.returncode != 0 or not mp4.exists():
            raise RuntimeError(f"Blender failed on {a['label']} - see {out / (a['label'] + '.log')}")
    for s in shots:
        db.save_asset(state["episode_id"], "render", s["label"], s["path"], s["seconds"])
    return {"stage": "render", "shots": shots}
