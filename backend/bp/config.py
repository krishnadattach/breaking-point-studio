"""Settings. Reads the .env file once and exposes paths + switches.

Why: every other file imports from here, so there is ONE place that knows
where things live and which keys exist.
"""
import os
import shutil
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]          # the project folder
load_dotenv(ROOT / ".env")

OUTPUT_DIR = ROOT / "output"                        # generated audio/video (git-ignored)
KIT_DIR = ROOT / "blender" / "kit"
BLENDER_SCRIPT = ROOT / "blender" / "render_level.py"
TTS_SCRIPT = Path(__file__).with_name("tts.ps1")

BLENDER_PATH = os.getenv("BLENDER_PATH", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
FFMPEG = os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg") or "ffmpeg"

MODEL_CHEAP = os.getenv("MODEL_CHEAP", "claude-haiku-5-5")
MODEL_WRITER = os.getenv("MODEL_WRITER", "claude-sonnet-5-5")

# --- skeleton render quality (raise later; see PROGRESS.md roadmap) ---
RENDER_FPS = 15          # frames per second inside Blender (ffmpeg makes it 30)
RENDER_SAMPLES = 8       # Eevee quality; kit preview uses 32, final 128

MAX_FACT_LOOPS = 2       # fact_check may send the script back this many times


def has_anthropic_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def has_tavily_key() -> bool:
    return bool(os.getenv("TAVILY_API_KEY", "").strip())


def mock_llm() -> bool:
    """True = use fake script/fact-check (free). Force with MOCK_LLM=1/0."""
    forced = os.getenv("MOCK_LLM", "").strip()
    return forced == "1" if forced else not has_anthropic_key()


def mock_search() -> bool:
    forced = os.getenv("MOCK_SEARCH", "").strip()
    return forced == "1" if forced else not has_tavily_key()


def mysql_conn_string() -> str:
    """Connection string for the LangGraph checkpointer (user bp_app, not root)."""
    u = quote(os.getenv("MYSQL_USER", "bp_app"), safe="")
    p = quote(os.getenv("MYSQL_PASSWORD", ""), safe="")
    h = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3307")
    db = os.getenv("MYSQL_DATABASE", "breaking_point")
    return f"mysql://{u}:{p}@{h}:{port}/{db}"


def episode_dir(episode_id: str) -> Path:
    d = OUTPUT_DIR / episode_id
    d.mkdir(parents=True, exist_ok=True)
    return d
