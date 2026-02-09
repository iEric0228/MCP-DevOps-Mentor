import pytest
from memory.models import UserProfile, SkillState


def test_save_and_load_roundtrip(tmp_db):
    from memory.store import save_profile, load_profile

    profile = UserProfile(
        user_level="developing",
        skills={
            "docker": SkillState(
                level="developing",
                evidence_count=5,
                last_feedback="Dockerfile present",
                weighted_score=8.5,
                history=["fb1", "fb2"],
            ),
        },
    )
    save_profile(profile)
    loaded = load_profile()

    assert loaded.user_level == "developing"
    assert "docker" in loaded.skills
    docker = loaded.skills["docker"]
    assert docker.level == "developing"
    assert docker.evidence_count == 5
    assert docker.last_feedback == "Dockerfile present"
    assert docker.weighted_score == 8.5
    assert docker.history == ["fb1", "fb2"]


def test_load_empty_db(tmp_db):
    from memory.store import load_profile

    profile = load_profile()
    assert profile.user_level == "junior"
    assert profile.skills == {}


def test_backward_compat_old_format(tmp_db):
    """Test loading data that was saved without weighted_score/history fields."""
    import sqlite3
    import json

    conn = sqlite3.connect(tmp_db)
    c = conn.cursor()
    old_data = {
        "user_level": "junior",
        "skills": {
            "docker": {
                "level": "developing",
                "evidence_count": 3,
                "last_feedback": "some feedback",
                # Note: no weighted_score or history
            }
        },
    }
    c.execute(
        "REPLACE INTO user_profile (id, data) VALUES (1, ?)",
        (json.dumps(old_data),),
    )
    conn.commit()
    conn.close()

    from memory.store import load_profile

    profile = load_profile()
    docker = profile.skills["docker"]
    assert docker.level == "developing"
    assert docker.evidence_count == 3
    assert docker.weighted_score == 0.0  # default
    assert docker.history == []  # default


def test_overwrite_profile(tmp_db):
    from memory.store import save_profile, load_profile

    profile1 = UserProfile(user_level="junior")
    save_profile(profile1)

    profile2 = UserProfile(user_level="solid")
    save_profile(profile2)

    loaded = load_profile()
    assert loaded.user_level == "solid"


def test_multiple_skills(tmp_db):
    from memory.store import save_profile, load_profile

    profile = UserProfile(
        user_level="developing",
        skills={
            "docker": SkillState(level="developing", evidence_count=3, weighted_score=7.0),
            "aws": SkillState(level="beginner", evidence_count=1, weighted_score=2.5),
            "ci_cd": SkillState(level="solid", evidence_count=8, weighted_score=16.0),
        },
    )
    save_profile(profile)
    loaded = load_profile()

    assert len(loaded.skills) == 3
    assert loaded.skills["docker"].level == "developing"
    assert loaded.skills["aws"].level == "beginner"
    assert loaded.skills["ci_cd"].level == "solid"
