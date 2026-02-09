from memory.store import load_profile, save_profile
from memory.models import SkillState, SKILL_LEVELS, SKILL_DEPENDENCIES

WEIGHTED_SKILL_MAP = {
    "ci_cd": [
        ("github actions", 2.0),
        ("workflow", 1.5),
        ("pipeline", 1.5),
        ("ci", 1.0),
        ("deploy", 1.0),
        ("artifact", 1.5),
        ("matrix strategy", 2.0),
        ("concurrency", 1.5),
    ],
    "docker": [
        ("dockerfile", 2.0),
        ("docker-compose", 2.0),
        ("container", 1.0),
        ("multi-stage", 2.0),
        ("docker", 1.0),
    ],
    "terraform": [
        ("terraform", 2.0),
        ("hcl", 2.0),
        ("tfstate", 2.0),
        ("tfvars", 1.5),
        ("provider", 1.5),
        ("module", 1.5),
        ("remote backend", 2.0),
        ("state locking", 2.0),
    ],
    "aws": [
        ("iam", 2.0),
        ("s3", 1.5),
        ("ec2", 1.5),
        ("lambda", 1.5),
        ("ecs", 1.5),
        ("eks", 2.0),
        ("rds", 1.5),
        ("cloudfront", 1.5),
        ("vpc", 1.5),
        ("security group", 2.0),
        ("auto-scaling", 2.0),
        ("aws", 1.0),
    ],
    "security": [
        ("secrets", 2.0),
        ("iam", 1.5),
        ("oidc", 2.0),
        ("rbac", 2.0),
        ("least-privilege", 2.0),
        ("permissions", 1.0),
        ("encryption", 2.0),
        ("hardcoded credential", 2.0),
    ],
    "observability": [
        ("prometheus", 2.0),
        ("grafana", 2.0),
        ("datadog", 2.0),
        ("cloudwatch", 2.0),
        ("logging", 1.0),
        ("monitoring", 1.0),
        ("alerting", 1.5),
        ("tracing", 2.0),
    ],
    "testing": [
        ("pytest", 2.0),
        ("jest", 2.0),
        ("unittest", 1.5),
        ("coverage", 1.5),
        ("integration test", 2.0),
        ("e2e", 2.0),
        ("test", 1.0),
    ],
}

LEVEL_THRESHOLDS = {
    "beginner": 2.0,
    "developing": 6.0,
    "solid": 15.0,
    "advanced": 30.0,
}

MAX_HISTORY = 5


def compute_level(weighted_score: float) -> str:
    level = "unknown"
    for lvl_name, threshold in LEVEL_THRESHOLDS.items():
        if weighted_score >= threshold:
            level = lvl_name
    return level


def update_skills(feedback: str, maturity: str):
    profile = load_profile()
    lower_feedback = feedback.lower()

    maturity_multiplier = {
        "early": 0.5,
        "basic": 0.75,
        "developing": 1.0,
        "production-leaning": 1.5,
    }.get(maturity, 0.75)

    for skill, keywords_weights in WEIGHTED_SKILL_MAP.items():
        state = profile.skills.get(skill, SkillState())
        matched_score = 0.0

        for keyword, weight in keywords_weights:
            if keyword in lower_feedback:
                matched_score += weight

        if matched_score > 0:
            state.evidence_count += 1
            state.weighted_score += matched_score * maturity_multiplier
            state.last_feedback = feedback[:200]
            state.history = (state.history + [feedback[:100]])[-MAX_HISTORY:]
            state.level = compute_level(state.weighted_score)
            profile.skills[skill] = state

    levels_index = [
        SKILL_LEVELS.index(s.level)
        for s in profile.skills.values()
        if s.level != "unknown"
    ]
    if levels_index:
        avg = sum(levels_index) / len(levels_index)
        profile.user_level = SKILL_LEVELS[min(int(avg), len(SKILL_LEVELS) - 1)]

    save_profile(profile)
    return profile


def get_learning_recommendations(profile):
    weak_skills = []
    strong_skills = []

    for skill_name, state in profile.skills.items():
        idx = SKILL_LEVELS.index(state.level)
        if idx <= 1:
            weak_skills.append(skill_name)
        elif idx >= 3:
            strong_skills.append(skill_name)

    all_skills = set(WEIGHTED_SKILL_MAP.keys())
    untracked = all_skills - set(profile.skills.keys())
    weak_skills.extend(sorted(untracked))

    prerequisite_gaps = []
    for skill in weak_skills:
        deps = SKILL_DEPENDENCIES.get(skill, [])
        for dep in deps:
            dep_state = profile.skills.get(dep, SkillState())
            if SKILL_LEVELS.index(dep_state.level) < 2:
                if dep not in prerequisite_gaps:
                    prerequisite_gaps.append(dep)

    recommended_focus = list(dict.fromkeys(prerequisite_gaps + weak_skills))

    step_map = {
        "ci_cd": "Set up a GitHub Actions workflow with caching, matrix builds, and environment protection",
        "docker": "Write a multi-stage Dockerfile and compose file for a real application",
        "terraform": "Create a Terraform module with remote state, variables, and outputs",
        "aws": "Deploy a VPC with public/private subnets, NAT, and security groups",
        "security": "Implement IAM least-privilege policies and enable encryption at rest",
        "observability": "Set up CloudWatch alarms and structured logging for a service",
        "testing": "Write integration tests with pytest and achieve 80%+ coverage",
    }

    next_steps = []
    for skill in recommended_focus[:5]:
        if skill in step_map:
            next_steps.append({"skill": skill, "action": step_map[skill]})

    return {
        "weak_skills": weak_skills,
        "strong_skills": strong_skills,
        "recommended_focus": recommended_focus,
        "prerequisite_gaps": prerequisite_gaps,
        "next_steps": next_steps,
    }
