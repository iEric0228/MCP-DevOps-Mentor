import pytest
from memory.tracker import (
    compute_level,
    update_skills,
    get_learning_recommendations,
    WEIGHTED_SKILL_MAP,
    LEVEL_THRESHOLDS,
    MAX_HISTORY,
)
from memory.models import SkillState, UserProfile, SKILL_LEVELS


def test_compute_level_unknown():
    assert compute_level(0.0) == "unknown"
    assert compute_level(1.9) == "unknown"


def test_compute_level_beginner():
    assert compute_level(2.0) == "beginner"
    assert compute_level(5.9) == "beginner"


def test_compute_level_developing():
    assert compute_level(6.0) == "developing"
    assert compute_level(14.9) == "developing"


def test_compute_level_solid():
    assert compute_level(15.0) == "solid"
    assert compute_level(29.9) == "solid"


def test_compute_level_advanced():
    assert compute_level(30.0) == "advanced"
    assert compute_level(100.0) == "advanced"


def test_compute_level_monotonic():
    prev_idx = 0
    for score in [0, 1, 2, 5, 6, 10, 15, 20, 30, 50]:
        level = compute_level(score)
        idx = SKILL_LEVELS.index(level)
        assert idx >= prev_idx
        prev_idx = idx


def test_update_skills_weighted_scoring(tmp_db):
    profile = update_skills("terraform hcl remote backend", "developing")
    tf_state = profile.skills.get("terraform")
    assert tf_state is not None
    assert tf_state.weighted_score > 0
    # "terraform" (2.0) + "hcl" (2.0) + "remote backend" (2.0) = 6.0
    # multiplier for "developing" = 1.0 -> 6.0
    assert tf_state.weighted_score == 6.0
    assert tf_state.level == "developing"


def test_update_skills_maturity_multiplier(tmp_db):
    profile = update_skills("docker container", "production-leaning")
    docker_state = profile.skills.get("docker")
    assert docker_state is not None
    # "docker" (1.0) + "container" (1.0) = 2.0
    # multiplier for "production-leaning" = 1.5 -> 3.0
    assert docker_state.weighted_score == 3.0


def test_update_skills_low_maturity_multiplier(tmp_db):
    profile = update_skills("docker container", "early")
    docker_state = profile.skills.get("docker")
    assert docker_state is not None
    # multiplier for "early" = 0.5 -> 1.0
    assert docker_state.weighted_score == 1.0


def test_update_skills_history_capped(tmp_db):
    for i in range(MAX_HISTORY + 3):
        profile = update_skills(f"docker feedback #{i}", "developing")

    docker_state = profile.skills["docker"]
    assert len(docker_state.history) == MAX_HISTORY


def test_update_skills_feedback_truncated(tmp_db):
    long_feedback = "terraform " + "x" * 300
    profile = update_skills(long_feedback, "developing")
    tf_state = profile.skills["terraform"]
    assert len(tf_state.last_feedback) <= 200


def test_update_skills_user_level(tmp_db):
    # Give multiple skills developing-level scores
    update_skills("terraform hcl remote backend state locking tfstate tfvars", "production-leaning")
    profile = update_skills("docker dockerfile docker-compose container multi-stage", "production-leaning")
    # At least some skills should be tracked
    assert len(profile.skills) >= 2
    assert profile.user_level != "junior"  # should be updated from default


def test_update_skills_no_match(tmp_db):
    profile = update_skills("nothing relevant here", "basic")
    assert len(profile.skills) == 0


def test_get_learning_recommendations_empty_profile():
    profile = UserProfile()
    recs = get_learning_recommendations(profile)
    assert len(recs["weak_skills"]) > 0  # all skills are untracked = weak
    assert len(recs["next_steps"]) > 0


def test_get_learning_recommendations_weak_skills():
    profile = UserProfile(skills={
        "docker": SkillState(level="beginner", evidence_count=1, weighted_score=2.0),
        "aws": SkillState(level="solid", evidence_count=10, weighted_score=20.0),
    })
    recs = get_learning_recommendations(profile)
    assert "docker" in recs["weak_skills"]
    assert "aws" in recs["strong_skills"]


def test_get_learning_recommendations_prerequisites():
    profile = UserProfile(skills={
        "security": SkillState(level="unknown", evidence_count=0, weighted_score=0.0),
        # aws is a prerequisite for security but is missing
    })
    recs = get_learning_recommendations(profile)
    assert "aws" in recs["prerequisite_gaps"]


def test_get_learning_recommendations_focus_order():
    profile = UserProfile(skills={
        "terraform": SkillState(level="beginner", evidence_count=1, weighted_score=2.0),
        # aws is a prereq for terraform and is missing
    })
    recs = get_learning_recommendations(profile)
    # Prerequisites should come before the dependent skill
    if "aws" in recs["recommended_focus"] and "terraform" in recs["recommended_focus"]:
        aws_idx = recs["recommended_focus"].index("aws")
        tf_idx = recs["recommended_focus"].index("terraform")
        assert aws_idx < tf_idx


def test_get_learning_recommendations_untracked_skills():
    profile = UserProfile(skills={
        "docker": SkillState(level="solid", evidence_count=10, weighted_score=20.0),
    })
    recs = get_learning_recommendations(profile)
    all_skills = set(WEIGHTED_SKILL_MAP.keys())
    # All untracked skills should appear as weak
    for skill in all_skills - {"docker"}:
        assert skill in recs["weak_skills"]
