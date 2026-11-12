"""The episode database (MySQL): the dashboard's source of truth for "what exists".

Two kinds of data live in MySQL, in the same database:
  * LangGraph's own checkpoint tables (created by the checkpointer) - the graph's
    private memory so it can pause/resume. We never read those directly.
  * OUR tables below - plain, readable records that the API and dashboard use.

Tables:
  episodes   one row per episode (topic, current stage, status)
  sources    web pages found by research
  scripts    every script draft (a new version each time write_script runs)
  claims     one row per level's factual claim + whether fact_check passed it
  approvals  every human decision (approve / send notes) on a script or video
  assets     files we generated: audio lines, rendered shots, the final video
"""
import json
import os
from contextlib import contextmanager

import pymysql
import pymysql.cursors

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS episodes (
        id VARCHAR(32) PRIMARY KEY,
        topic VARCHAR(300) NOT NULL,
        stage VARCHAR(40) NOT NULL DEFAULT 'created',
        status VARCHAR(40) NOT NULL DEFAULT 'running',
        error TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS sources (
        id INT AUTO_INCREMENT PRIMARY KEY,
        episode_id VARCHAR(32) NOT NULL,
        url VARCHAR(1000) NOT NULL,
        title VARCHAR(500) NULL,
        snippet TEXT NULL,
        FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS scripts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        episode_id VARCHAR(32) NOT NULL,
        version INT NOT NULL,
        hook TEXT NOT NULL,
        shape VARCHAR(20) NOT NULL,
        hazard VARCHAR(60) NOT NULL,
        twist_level INT NOT NULL,
        levels_json JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_script_version (episode_id, version),
        FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS claims (
        id INT AUTO_INCREMENT PRIMARY KEY,
        script_id INT NOT NULL,
        level INT NOT NULL,
        claim TEXT NOT NULL,
        source_url VARCHAR(1000) NULL,
        status VARCHAR(10) NOT NULL,
        reason TEXT NULL,
        FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS approvals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        episode_id VARCHAR(32) NOT NULL,
        kind VARCHAR(10) NOT NULL,
        action VARCHAR(10) NOT NULL,
        notes TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS assets (
        id INT AUTO_INCREMENT PRIMARY KEY,
        episode_id VARCHAR(32) NOT NULL,
        kind VARCHAR(20) NOT NULL,
        label VARCHAR(40) NOT NULL,
        path VARCHAR(500) NOT NULL,
        seconds FLOAT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_asset (episode_id, kind, label),
        FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
    )""",
]
# episodes.status values: running | waiting_script_review | waiting_video_review | done | failed
# approvals.kind: script | video      approvals.action: approve | notes
# assets.kind: audio | render | final_video   (UNIQUE key: re-running a step replaces the row)


@contextmanager
def connect():
    from . import config  # imported here so .env is loaded first
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"), port=int(os.getenv("MYSQL_PORT", "3307")),
        user=os.getenv("MYSQL_USER", "bp_app"), password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "breaking_point"), charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with connect() as c, c.cursor() as cur:
        for stmt in SCHEMA:
            cur.execute(stmt)


# ---------------- writes (called by the graph nodes) ----------------
def create_episode(episode_id: str, topic: str):
    with connect() as c, c.cursor() as cur:
        cur.execute("INSERT IGNORE INTO episodes (id, topic) VALUES (%s, %s)", (episode_id, topic))


def set_stage(episode_id: str, stage: str, status: str = "running", error: str | None = None):
    with connect() as c, c.cursor() as cur:
        cur.execute("UPDATE episodes SET stage=%s, status=%s, error=%s WHERE id=%s",
                    (stage, status, error, episode_id))


def save_sources(episode_id: str, sources: list[dict]):
    with connect() as c, c.cursor() as cur:
        cur.execute("DELETE FROM sources WHERE episode_id=%s", (episode_id,))
        cur.executemany("INSERT INTO sources (episode_id, url, title, snippet) VALUES (%s,%s,%s,%s)",
                        [(episode_id, s["url"], s.get("title", ""), s.get("snippet", "")) for s in sources])


def save_script_with_claims(episode_id: str, script: dict, claims: list[dict]):
    """One new script version + its claim rows (called after each fact_check pass)."""
    with connect() as c, c.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(version),0)+1 AS v FROM scripts WHERE episode_id=%s", (episode_id,))
        version = cur.fetchone()["v"]
        cur.execute("INSERT INTO scripts (episode_id, version, hook, shape, hazard, twist_level, levels_json) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (episode_id, version, script["hook"], script["shape"], script["hazard"],
                     script["twist_level"], json.dumps(script["levels"])))
        script_id = cur.lastrowid
        cur.executemany("INSERT INTO claims (script_id, level, claim, source_url, status, reason) "
                        "VALUES (%s,%s,%s,%s,%s,%s)",
                        [(script_id, k["level"], k["claim"], k["source_url"], k["status"], k["reason"]) for k in claims])


def add_approval(episode_id: str, kind: str, action: str, notes: str = ""):
    with connect() as c, c.cursor() as cur:
        cur.execute("INSERT INTO approvals (episode_id, kind, action, notes) VALUES (%s,%s,%s,%s)",
                    (episode_id, kind, action, notes))


def save_asset(episode_id: str, kind: str, label: str, path: str, seconds: float | None = None):
    with connect() as c, c.cursor() as cur:
        cur.execute("INSERT INTO assets (episode_id, kind, label, path, seconds) VALUES (%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE path=VALUES(path), seconds=VALUES(seconds), created_at=CURRENT_TIMESTAMP",
                    (episode_id, kind, label, path, seconds))


# ---------------- reads (used by the API in stage 4) ----------------
def list_episodes() -> list[dict]:
    with connect() as c, c.cursor() as cur:
        cur.execute("SELECT * FROM episodes ORDER BY created_at DESC")
        return cur.fetchall()


def get_episode(episode_id: str) -> dict | None:
    """Everything about one episode: latest script + its claims, sources, approvals, assets."""
    with connect() as c, c.cursor() as cur:
        cur.execute("SELECT * FROM episodes WHERE id=%s", (episode_id,))
        ep = cur.fetchone()
        if not ep:
            return None
        cur.execute("SELECT * FROM scripts WHERE episode_id=%s ORDER BY version DESC LIMIT 1", (episode_id,))
        script = cur.fetchone()
        if script:
            script["levels"] = json.loads(script.pop("levels_json"))
            cur.execute("SELECT level, claim, source_url, status, reason FROM claims WHERE script_id=%s ORDER BY level",
                        (script["id"],))
            script["claims"] = cur.fetchall()
        cur.execute("SELECT url, title, snippet FROM sources WHERE episode_id=%s", (episode_id,))
        sources = cur.fetchall()
        cur.execute("SELECT kind, action, notes, created_at FROM approvals WHERE episode_id=%s ORDER BY id", (episode_id,))
        approvals = cur.fetchall()
        cur.execute("SELECT kind, label, path, seconds FROM assets WHERE episode_id=%s ORDER BY id", (episode_id,))
        assets = cur.fetchall()
        return {**ep, "script": script, "sources": sources, "approvals": approvals, "assets": assets}
