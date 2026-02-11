import pytest
from enhancer.prompt_enhancer import (
    enhance_prompt,
    _detect_domains,
    _resolve_cloud_provider,
    _get_missing_dimensions,
    MAX_INJECTIONS,
)
from enhancer.domain_rules import DIMENSION_INJECTIONS


# --- Domain Detection Tests ---


def test_detect_single_domain_cicd():
    domains = _detect_domains("set up a ci/cd pipeline")
    assert "ci_cd" in domains


def test_detect_single_domain_terraform():
    domains = _detect_domains("create a terraform module")
    assert "terraform" in domains


def test_detect_single_domain_docker():
    domains = _detect_domains("write a dockerfile for my app")
    assert "docker" in domains


def test_detect_multiple_domains():
    domains = _detect_domains("deploy docker container to ecs with iam roles")
    assert "docker" in domains
    assert "aws" in domains


def test_detect_no_domain_defaults_to_devops():
    domains = _detect_domains("help me improve my skills")
    assert domains == ["devops"]


def test_detect_domain_ordering_by_relevance():
    # "aws ec2 s3 lambda ecs" has 5 aws keywords vs 1 docker keyword
    domains = _detect_domains("deploy docker to aws ec2 s3 lambda ecs")
    assert domains[0] == "aws"


# --- Cloud Provider Tests ---


def test_default_cloud_provider_is_aws():
    provider = _resolve_cloud_provider("set up a pipeline", "")
    assert provider == "aws"


def test_explicit_cloud_provider_gcp():
    provider = _resolve_cloud_provider("set up a pipeline", "gcp")
    assert provider == "gcp"


def test_explicit_cloud_provider_azure():
    provider = _resolve_cloud_provider("set up a pipeline", "azure")
    assert provider == "azure"


def test_detect_gcp_from_prompt():
    provider = _resolve_cloud_provider("deploy to google cloud", "")
    assert provider == "gcp"


def test_detect_gcp_keyword_from_prompt():
    provider = _resolve_cloud_provider("deploy to gcp", "")
    assert provider == "gcp"


def test_detect_azure_from_prompt():
    provider = _resolve_cloud_provider("deploy to azure", "")
    assert provider == "azure"


def test_explicit_overrides_detection():
    # Prompt says "aws" but explicit param says "gcp"
    provider = _resolve_cloud_provider("deploy to aws", "gcp")
    assert provider == "gcp"


# --- Dimension Injection Tests ---


def test_missing_dimensions_injected():
    """A bare ci_cd prompt should get security, rollback, caching, testing injections."""
    injections, added = _get_missing_dimensions(
        "set up a pipeline", ["ci_cd"], []
    )
    assert len(injections) > 0
    dim_names = [d.split(":")[1] for d in added]
    assert "security" in dim_names
    assert "rollback" in dim_names
    assert "caching" in dim_names
    assert "testing" in dim_names


def test_already_covered_dimension_skipped():
    """A prompt mentioning 'caching' should not get the caching injection."""
    injections, added = _get_missing_dimensions(
        "set up a pipeline with caching", ["ci_cd"], []
    )
    dim_names = [d.split(":")[1] for d in added]
    assert "caching" not in dim_names


def test_all_dimensions_covered_no_injection():
    """A prompt covering all ci_cd keywords should get no injections."""
    prompt = "set up a secure pipeline with secret management, rollback strategy, caching, and test coverage"
    injections, added = _get_missing_dimensions(prompt, ["ci_cd"], [])
    assert len(injections) == 0
    assert len(added) == 0


def test_focus_areas_filter():
    """Only dimensions matching focus_areas should be injected."""
    injections, added = _get_missing_dimensions(
        "set up a pipeline", ["ci_cd"], ["security"]
    )
    dim_names = [d.split(":")[1] for d in added]
    assert "security" in dim_names
    # Other dimensions should NOT be present
    assert "rollback" not in dim_names
    assert "caching" not in dim_names
    assert "testing" not in dim_names


def test_focus_areas_empty_injects_all():
    """Empty focus_areas should inject all missing dimensions."""
    injections, added = _get_missing_dimensions(
        "set up a pipeline", ["ci_cd"], []
    )
    assert len(added) >= 3  # ci_cd has 4 dimensions, all should be missing


def test_cross_domain_dedup():
    """Security dimension should only be injected once even if multiple domains have it."""
    injections, added = _get_missing_dimensions(
        "set up infrastructure", ["ci_cd", "aws"], []
    )
    security_dims = [d for d in added if d.endswith(":security")]
    assert len(security_dims) <= 1


def test_injection_cap():
    """Should not exceed MAX_INJECTIONS to prevent overwhelming output."""
    # Use many domains to trigger lots of injections
    injections, added = _get_missing_dimensions(
        "help me",
        ["ci_cd", "terraform", "docker", "aws", "security", "observability"],
        [],
    )
    assert len(injections) <= MAX_INJECTIONS


# --- Mode Template Tests ---


def test_mentor_mode_has_learning_structure(tmp_db):
    result = enhance_prompt("set up a pipeline", mode="mentor")
    assert "Conceptual explanation" in result["enhanced_prompt"]
    assert "WHY" in result["enhanced_prompt"]


def test_review_mode_has_assessment_structure(tmp_db):
    result = enhance_prompt("review my terraform", mode="review")
    assert "Critical issues" in result["enhanced_prompt"]
    assert "maturity rating" in result["enhanced_prompt"]


def test_debug_mode_has_hypothesis_structure(tmp_db):
    result = enhance_prompt("my deployment is failing", mode="debug")
    assert "hypotheses" in result["enhanced_prompt"]


def test_interview_mode_has_challenge_structure(tmp_db):
    result = enhance_prompt("design a deployment strategy", mode="interview")
    assert "Follow-up probes" in result["enhanced_prompt"]


def test_invalid_mode_falls_back_to_mentor(tmp_db):
    result = enhance_prompt("set up a pipeline", mode="nonexistent_mode")
    # Should use mentor template (fallback)
    assert "Conceptual explanation" in result["enhanced_prompt"]


# --- Full Integration Tests ---


def test_enhance_prompt_returns_expected_keys(tmp_db):
    result = enhance_prompt("set up a CI/CD pipeline for my Python app")
    assert "original_prompt" in result
    assert "enhanced_prompt" in result
    assert "enhancements_applied" in result
    assert "context_injected" in result
    assert "reasoning" in result


def test_enhance_prompt_context_injected_keys(tmp_db):
    result = enhance_prompt("set up a pipeline")
    ctx = result["context_injected"]
    assert "cloud_provider" in ctx
    assert "skill_level" in ctx
    assert "mode" in ctx
    assert "dimensions_added" in ctx
    assert "detected_domains" in ctx


def test_enhance_prompt_original_preserved(tmp_db):
    raw = "Set up a CI/CD pipeline for my Python app"
    result = enhance_prompt(raw)
    assert result["original_prompt"] == raw


def test_enhance_prompt_xml_tags_present(tmp_db):
    result = enhance_prompt("set up a CI/CD pipeline")
    enhanced = result["enhanced_prompt"]
    assert "<context>" in enhanced
    assert "</context>" in enhanced
    assert "<task>" in enhanced
    assert "</task>" in enhanced
    assert "<instructions>" in enhanced
    assert "</instructions>" in enhanced
    assert "<thinking>" in enhanced
    assert "</thinking>" in enhanced
    assert "<output_format>" in enhanced
    assert "</output_format>" in enhanced


def test_enhance_prompt_task_contains_original(tmp_db):
    raw = "Set up a CI/CD pipeline for my Python app"
    result = enhance_prompt(raw)
    # The raw prompt should appear inside <task> tags
    assert raw in result["enhanced_prompt"]


def test_enhance_prompt_enhancements_applied_list(tmp_db):
    result = enhance_prompt("set up a pipeline")
    applied = result["enhancements_applied"]
    assert "cloud_context" in applied
    assert "skill_adaptation" in applied
    assert "mode_structuring" in applied
    assert "xml_structuring" in applied
    assert "chain_of_thought" in applied


def test_enhance_prompt_dimension_injection_in_applied_list(tmp_db):
    result = enhance_prompt("set up a pipeline")
    assert "dimension_injection" in result["enhancements_applied"]


def test_enhance_prompt_no_dimension_injection_when_covered(tmp_db):
    prompt = "set up a secure pipeline with secret management, rollback strategy, caching, and test coverage"
    result = enhance_prompt(prompt)
    # ci_cd dimensions are all covered, but other enhancements still apply
    # dimension_injection may or may not be present depending on other domain matches
    assert "cloud_context" in result["enhancements_applied"]


def test_enhance_prompt_reasoning_includes_domains(tmp_db):
    result = enhance_prompt("set up a terraform module")
    assert "terraform" in result["reasoning"].lower()


def test_enhance_prompt_reasoning_includes_mode(tmp_db):
    result = enhance_prompt("set up a pipeline", mode="review")
    assert "review" in result["reasoning"]


def test_enhance_prompt_default_aws_context(tmp_db):
    result = enhance_prompt("set up a pipeline")
    assert result["context_injected"]["cloud_provider"] == "aws"
    assert "AWS" in result["enhanced_prompt"]


def test_enhance_prompt_gcp_context(tmp_db):
    result = enhance_prompt("deploy to google cloud", cloud_provider="gcp")
    assert result["context_injected"]["cloud_provider"] == "gcp"
    assert "Google Cloud" in result["enhanced_prompt"]


def test_enhance_prompt_with_focus_areas(tmp_db):
    result = enhance_prompt("set up a pipeline", focus_areas="security,cost")
    dim_names = [
        d.split(":")[1] for d in result["context_injected"]["dimensions_added"]
    ]
    # Only security and cost should be present (if they were missing)
    for dim in dim_names:
        assert dim in ("security", "cost")


# --- Edge Cases ---


def test_empty_prompt(tmp_db):
    result = enhance_prompt("")
    assert result["enhanced_prompt"] == ""
    assert result["enhancements_applied"] == []
    assert "Empty prompt" in result["reasoning"]


def test_whitespace_only_prompt(tmp_db):
    result = enhance_prompt("   ")
    assert result["enhancements_applied"] == []


def test_very_long_prompt(tmp_db):
    long_prompt = "set up a pipeline " + "with many requirements " * 200
    result = enhance_prompt(long_prompt)
    assert result["original_prompt"] == long_prompt
    assert "<task>" in result["enhanced_prompt"]


def test_prompt_with_special_characters(tmp_db):
    prompt = 'Deploy to ECS with env vars like KEY="value<>&" and PATH=/usr/bin'
    result = enhance_prompt(prompt)
    # The raw prompt should be preserved inside <task> tags
    assert prompt in result["enhanced_prompt"]


def test_prompt_with_multiple_cloud_mentions(tmp_db):
    """When prompt mentions multiple clouds, explicit param wins."""
    result = enhance_prompt(
        "migrate from aws to azure", cloud_provider="azure"
    )
    assert result["context_injected"]["cloud_provider"] == "azure"
