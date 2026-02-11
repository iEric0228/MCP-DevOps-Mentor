import pytest
from enhancer.skill_adapter import (
    get_skill_adaptation,
    LEVEL_ADAPTATION,
    DOMAIN_TO_SKILL,
    USER_LEVEL_MAP,
)
from memory.models import SkillState, UserProfile
from memory.store import save_profile


def test_unknown_profile_gets_detailed(tmp_db):
    """A fresh profile with no skills should get detailed adaptation."""
    result = get_skill_adaptation(["ci_cd"])
    assert result["detail_level"] == "detailed"
    assert result["effective_level"] in ("unknown", "beginner")


def test_beginner_gets_detailed_adaptation(tmp_db):
    """A user with beginner-level skill should get detailed output."""
    profile = UserProfile(
        user_level="junior",
        skills={"ci_cd": SkillState(level="beginner", weighted_score=3.0)},
    )
    save_profile(profile)
    result = get_skill_adaptation(["ci_cd"])
    assert result["detail_level"] == "detailed"
    assert result["effective_level"] == "beginner"


def test_developing_gets_moderate_adaptation(tmp_db):
    """A developing user should get moderate detail level."""
    profile = UserProfile(
        user_level="mid",
        skills={"terraform": SkillState(level="developing", weighted_score=8.0)},
    )
    save_profile(profile)
    result = get_skill_adaptation(["terraform"])
    assert result["detail_level"] == "moderate"
    assert result["effective_level"] == "developing"


def test_advanced_gets_concise_adaptation(tmp_db):
    """An advanced user should get concise output."""
    profile = UserProfile(
        user_level="senior",
        skills={"aws": SkillState(level="advanced", weighted_score=35.0)},
    )
    save_profile(profile)
    result = get_skill_adaptation(["aws"])
    assert result["detail_level"] == "concise"
    assert result["effective_level"] == "advanced"


def test_weakest_relevant_skill_used(tmp_db):
    """When multiple domains detected, use the weakest to avoid overwhelming."""
    profile = UserProfile(
        user_level="mid",
        skills={
            "docker": SkillState(level="advanced", weighted_score=35.0),
            "aws": SkillState(level="beginner", weighted_score=3.0),
        },
    )
    save_profile(profile)
    result = get_skill_adaptation(["docker", "aws"])
    assert result["effective_level"] == "beginner"
    assert result["detail_level"] == "detailed"


def test_unrelated_skills_ignored(tmp_db):
    """High skill in unrelated domain should not affect a different domain prompt."""
    profile = UserProfile(
        user_level="junior",
        skills={
            "terraform": SkillState(level="advanced", weighted_score=35.0),
        },
    )
    save_profile(profile)
    # Prompt is about ci_cd, terraform skill is irrelevant
    result = get_skill_adaptation(["ci_cd"])
    # Falls back to user_level mapping since no ci_cd skill tracked
    assert result["effective_level"] == USER_LEVEL_MAP["junior"]


def test_fallback_to_user_level_when_no_skills_match(tmp_db):
    """When no detected domains match tracked skills, use user_level."""
    profile = UserProfile(user_level="mid", skills={})
    save_profile(profile)
    result = get_skill_adaptation(["networking"])
    assert result["effective_level"] == "developing"


def test_networking_maps_to_aws_skill(tmp_db):
    """Networking domain should use the aws skill level."""
    profile = UserProfile(
        user_level="junior",
        skills={"aws": SkillState(level="solid", weighted_score=20.0)},
    )
    save_profile(profile)
    result = get_skill_adaptation(["networking"])
    assert result["effective_level"] == "solid"


def test_all_adaptation_levels_have_required_keys():
    """Every level adaptation should have detail_level, tone, and output_hint."""
    for level_name, adaptation in LEVEL_ADAPTATION.items():
        assert "detail_level" in adaptation, f"'{level_name}' missing detail_level"
        assert "tone" in adaptation, f"'{level_name}' missing tone"
        assert "output_hint" in adaptation, f"'{level_name}' missing output_hint"


def test_domain_to_skill_mapping_coverage():
    """All enhancer domains should map to a tracked skill."""
    expected_domains = {
        "ci_cd", "docker", "terraform", "aws",
        "security", "observability", "networking", "cost",
    }
    assert set(DOMAIN_TO_SKILL.keys()) == expected_domains
