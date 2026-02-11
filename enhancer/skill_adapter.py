"""
Bridges the memory/store skill tracking system to prompt enhancement behavior.

Reads the user profile (read-only) and translates skill levels into
adaptation parameters that control tone, detail level, and output hints.
"""

from memory.store import load_profile
from memory.models import SKILL_LEVELS


# Maps skill levels to enhancement adaptation parameters.
LEVEL_ADAPTATION = {
    "unknown": {
        "detail_level": "detailed",
        "tone": (
            "Explain concepts thoroughly. Define technical terms. "
            "Provide step-by-step guidance."
        ),
        "output_hint": "Include example commands or configuration snippets where helpful.",
    },
    "beginner": {
        "detail_level": "detailed",
        "tone": (
            "Explain the reasoning behind each recommendation. "
            "Avoid assuming prior knowledge of advanced patterns."
        ),
        "output_hint": "Include example commands or configuration snippets where helpful.",
    },
    "developing": {
        "detail_level": "moderate",
        "tone": (
            "Focus on best practices and production considerations. "
            "Brief explanations are acceptable."
        ),
        "output_hint": "Use structured output with clear sections.",
    },
    "solid": {
        "detail_level": "concise",
        "tone": (
            "Be direct and focus on advanced patterns, edge cases, and trade-offs."
        ),
        "output_hint": "Highlight non-obvious considerations and advanced optimizations.",
    },
    "advanced": {
        "detail_level": "concise",
        "tone": (
            "Focus on architecture-level decisions, trade-offs, and cutting-edge practices. "
            "Skip basics."
        ),
        "output_hint": "Prioritize trade-off analysis and production battle scars.",
    },
}

# Maps enhancer domains to tracked skill keys in memory/tracker.py.
DOMAIN_TO_SKILL = {
    "ci_cd": "ci_cd",
    "docker": "docker",
    "terraform": "terraform",
    "aws": "aws",
    "security": "security",
    "observability": "observability",
    "networking": "aws",
    "cost": "aws",
}

# Maps user_level (junior/mid/senior) to skill level names.
USER_LEVEL_MAP = {
    "junior": "beginner",
    "mid": "developing",
    "senior": "solid",
}


def get_skill_adaptation(detected_domains: list) -> dict:
    """
    Load the user profile and determine enhancement adaptation
    based on relevant skill levels for the detected domains.

    Uses the weakest relevant skill to avoid overwhelming the user.
    Falls back to user_level if no domain-specific skills are tracked.
    """
    try:
        profile = load_profile()
    except Exception:
        adaptation = dict(LEVEL_ADAPTATION["unknown"])
        adaptation["effective_level"] = "unknown"
        return adaptation

    # Find skill levels for the detected domains
    relevant_levels = []
    for domain in detected_domains:
        skill_key = DOMAIN_TO_SKILL.get(domain)
        if skill_key and skill_key in profile.skills:
            level = profile.skills[skill_key].level
            relevant_levels.append(SKILL_LEVELS.index(level))

    if not relevant_levels:
        # No tracked skills for these domains, use overall user_level
        effective_level = USER_LEVEL_MAP.get(profile.user_level, "unknown")
    else:
        # Use the minimum (weakest) relevant skill to avoid overwhelming
        min_idx = min(relevant_levels)
        effective_level = SKILL_LEVELS[min_idx]

    adaptation = dict(LEVEL_ADAPTATION.get(effective_level, LEVEL_ADAPTATION["unknown"]))
    adaptation["effective_level"] = effective_level
    return adaptation
