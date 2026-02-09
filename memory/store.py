import sqlite3
import json
from memory.models import UserProfile, SkillState

DB_PATH = "mentor_memory.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY,
            data TEXT
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


def load_profile() -> UserProfile:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT data FROM user_profile WHERE id = 1")
    row = c.fetchone()
    conn.close()

    if not row:
        return UserProfile()

    raw = json.loads(row[0])
    skills = {}
    for k, v in raw["skills"].items():
        v.setdefault("weighted_score", 0.0)
        v.setdefault("history", [])
        skills[k] = SkillState(**v)
    return UserProfile(user_level=raw["user_level"], skills=skills)


def save_profile(profile: UserProfile):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    data = {
        "user_level": profile.user_level,
        "skills": {k: vars(v) for k, v in profile.skills.items()},
    }

    c.execute("REPLACE INTO user_profile (id, data) VALUES (1, ?)", (json.dumps(data),))
    conn.commit()
    conn.close()
