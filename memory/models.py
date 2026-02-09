from dataclasses import dataclass, field
from typing import Dict, List


SKILL_LEVELS = ["unknown", "beginner", "developing", "solid", "advanced"]

SKILL_DEPENDENCIES = {
    "security": ["aws"],
    "terraform": ["aws"],
    "observability": ["docker"],
}


@dataclass
class SkillState:
    level: str = "unknown"
    evidence_count: int = 0
    last_feedback: str = ""
    weighted_score: float = 0.0
    history: List[str] = field(default_factory=list)


@dataclass
class UserProfile:
    user_level: str = "junior"
    skills: Dict[str, SkillState] = field(default_factory=dict)
