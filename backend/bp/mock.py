"""Fake data for free testing (no API keys needed).

Why: the walking skeleton must work end to end without spending money. Mock
facts are clearly labelled MOCK and must never be published as real.
"""
import re

# hazard -> (unit, ten escalating values)
HAZARDS = {
    "speed": ("m/s", [1, 5, 20, 50, 100, 340, 700, 1500, 3000, 7800]),
    "heat": ("°C", [100, 300, 600, 1000, 1400, 1700, 2000, 3000, 4500, 5500]),
    "cold": ("°C", [0, -40, -80, -120, -160, -196, -230, -250, -265, -272]),
    "pressure": ("atm", [2, 10, 50, 100, 500, 1100, 3000, 10000, 100000, 1000000]),
    "lightning": ("kA", [1, 5, 10, 20, 30, 50, 100, 150, 200, 300]),
    "spin": ("rpm", [60, 600, 3000, 10000, 30000, 60000, 100000, 300000, 1000000, 5000000]),
}


def parse_topic(topic: str) -> tuple[str, str]:
    """'A grain of sand vs 10 levels of speed' -> ('a grain of sand', 'speed')."""
    m = re.match(r"(.+?)\s+vs\.?\s+10 levels of\s+(.+)", topic.strip(), re.I)
    obj, hazard = (m.group(1), m.group(2)) if m else (topic, "speed")
    hazard = hazard.lower().replace("impact ", "").strip()
    for key in HAZARDS:
        if key in hazard:
            return obj.strip(), key
    return obj.strip(), "speed"


def search(topic: str) -> list[dict]:
    return [
        {"url": "https://example.com/mock-source-1", "title": "MOCK source 1", "snippet": f"MOCK facts about {topic}."},
        {"url": "https://example.com/mock-source-2", "title": "MOCK source 2", "snippet": f"MOCK ladder values for {topic}."},
    ]


def script(topic: str) -> dict:
    obj, hazard = parse_topic(topic)
    unit, values = HAZARDS[hazard]
    twist = 7
    levels = []
    for i, v in enumerate(values, start=1):
        # mock rule: survives early levels, is destroyed from level 8, and the
        # twist level (7) is a surprising SURVIVES
        verdict = "SURVIVES" if i < 8 else "DESTROYED"
        levels.append({
            "n": i,
            "narration": f"Level {i}: {v} {unit}. {obj.capitalize()} {'survives' if verdict == 'SURVIVES' else 'is destroyed'}.",
            "value": f"{v} {unit}",
            "verdict": verdict,
            "claim": f"MOCK claim: {obj} faces {v} {unit} at level {i}.",
            "source_url": "https://example.com/mock-source-1",
        })
    return {
        "hook": f"Can {obj.lower()} survive 10 levels of {hazard}? Watch until level {twist}.",
        "shape": "sphere",
        "hazard": hazard,
        "twist_level": twist,
        "levels": levels,
    }
