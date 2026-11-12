"""NODE 5 - voiceover: free offline Windows text-to-speech, one audio file per line.

One line = the hook, then one per level (11 files). We also measure each
file's length, because every video shot must last as long as its audio.
"""
import json
import subprocess
import wave

from .. import config, db
from ..state import State


def lines_of(script: dict) -> list[dict]:
    """The spoken lines in order: hook first, then levels 1-10."""
    items = [{"label": "hook", "level": 0, "text": script["hook"]}]
    for lv in script["levels"]:
        items.append({"label": f"level_{lv['n']:02d}", "level": lv["n"], "text": lv["narration"]})
    return items


def voiceover(state: State) -> dict:
    out = config.episode_dir(state["episode_id"]) / "audio"
    out.mkdir(exist_ok=True)
    items = lines_of(state["script"])
    for it in items:
        it["path"] = str(out / f"{it['label']}.wav")

    job = out / "tts_job.json"
    job.write_text(json.dumps([{"path": i["path"], "text": i["text"]} for i in items]), encoding="utf-8")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(config.TTS_SCRIPT),
                        "-JsonPath", str(job)], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"Text-to-speech failed: {r.stderr or r.stdout}")

    for it in items:
        with wave.open(it["path"]) as w:
            it["seconds"] = round(w.getnframes() / w.getframerate(), 2)
    for it in items:
        db.save_asset(state["episode_id"], "audio", it["label"], it["path"], it["seconds"])
    return {"stage": "voiceover", "audio": items}
