"""NODE 7 - assemble: FFmpeg joins shots + voice + burned-in captions into one 1080x1920 MP4.

Steps: (1) per shot: scale video to 1080x1920, add its voice track;
(2) join all shots; (3) burn in text (caption, level header, big verdict word)
using an .ass subtitle file that we generate.
"""
import subprocess

from .. import config
from ..state import State
from .render import VERDICT_AT

CYAN, ORANGE, GREEN, RED = "&H00FFC200", "&H002C6BFF", "&H008AFF3C", "&H003030FF"   # ASS colours are BGR


def _ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def build_ass(script: dict, audio: list[dict], shots: list[dict]) -> str:
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,62,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,2,2,80,80,330,1
Style: Header,Arial,70,{CYAN},&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,2,8,60,60,300,1
Style: Verdict,Arial,130,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,8,3,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev, t = [], 0.0
    levels = {lv["n"]: lv for lv in script["levels"]}
    for a, s in zip(audio, shots):
        dur, n = s["seconds"], a["level"]
        end = t + dur
        ev.append(f"Dialogue: 0,{_ts(t)},{_ts(end)},Caption,,0,0,0,,{a['text']}")
        if n:
            lv = levels[n]
            twist = "  \\N{\\c" + ORANGE + "}TWIST LEVEL" if n == script["twist_level"] else ""
            ev.append(f"Dialogue: 0,{_ts(t)},{_ts(end)},Header,,0,0,0,,LEVEL {n}  |  {lv['value']}{twist}")
            colour = GREEN if lv["verdict"] == "SURVIVES" else RED
            ev.append(f"Dialogue: 1,{_ts(t + dur * VERDICT_AT)},{_ts(end)},Verdict,,0,0,0,,{{\\c{colour}}}{lv['verdict']}")
        else:
            ev.append(f"Dialogue: 0,{_ts(t)},{_ts(end)},Header,,0,0,0,,THE BREAKING POINT")
        t = end
    return head + "\n".join(ev) + "\n"


def _ffmpeg(args: list[str], cwd=None):
    r = subprocess.run([config.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *args],
                       capture_output=True, text=True, cwd=cwd, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr}")


def assemble(state: State) -> dict:
    ep = config.episode_dir(state["episode_id"])
    seg_dir = ep / "segments"
    seg_dir.mkdir(exist_ok=True)

    # (1) one segment per shot: video scaled to 1080x1920 + its voice
    segs = []
    for a, s in zip(state["audio"], state["shots"]):
        seg = seg_dir / f"{a['label']}.mp4"
        _ffmpeg(["-i", s["path"], "-i", a["path"], "-filter_complex",
                 "[0:v]scale=1080:1920:flags=lanczos,fps=30,tpad=stop_mode=clone:stop_duration=2,format=yuv420p[v];"
                 "[1:a]apad,aresample=44100[a]",
                 "-map", "[v]", "-map", "[a]", "-t", str(s["seconds"]),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-ac", "2", str(seg)])
        segs.append(seg)

    # (2) join
    (ep / "segments.txt").write_text("".join(f"file 'segments/{p.name}'\n" for p in segs), encoding="utf-8")
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", "segments.txt", "-c", "copy", "joined.mp4"], cwd=ep)

    # (3) burn in captions
    (ep / "captions.ass").write_text(build_ass(state["script"], state["audio"], state["shots"]), encoding="utf-8")
    _ffmpeg(["-i", "joined.mp4", "-vf", "ass=captions.ass", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "20", "-c:a", "copy", "-movflags", "+faststart", "final.mp4"], cwd=ep)
    return {"stage": "assemble", "final_video": str(ep / "final.mp4")}
