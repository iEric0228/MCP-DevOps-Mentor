"""
Core prompt enhancement pipeline.

Takes a raw DevOps-related prompt and improves it through a 6-stage
deterministic pipeline:
  1. Domain Detection
  2. Dimension Injection
  3. Cloud Provider Context
  4. Skill-Level Adaptation
  5. Mode-Aware Structuring
  6. XML Assembly

Inspired by Claude's Prompt Improver pattern but implemented as
pure Python template logic (no LLM API calls).
"""

from enhancer.domain_rules import (
    DOMAIN_KEYWORDS,
    DIMENSION_INJECTIONS,
    CLOUD_PROVIDER_CONTEXT,
    MODE_TEMPLATES,
)
from enhancer.skill_adapter import get_skill_adaptation

MAX_INJECTIONS = 6


def enhance_prompt(
    raw_prompt: str,
    mode: str = "mentor",
    cloud_provider: str = "",
    focus_areas: str = "",
) -> dict:
    """
    Enhance a raw DevOps prompt with structure, context, and best-practice
    considerations.

    Args:
        raw_prompt: The user's original prompt text.
        mode: Review mode (mentor/review/debug/interview).
        cloud_provider: Explicit cloud provider (aws/gcp/azure). Defaults to aws.
        focus_areas: Comma-separated dimension filter (e.g. "security,cost").

    Returns:
        Dict with original_prompt, enhanced_prompt, enhancements_applied,
        context_injected, and reasoning.
    """
    if not raw_prompt or not raw_prompt.strip():
        return {
            "original_prompt": raw_prompt,
            "enhanced_prompt": raw_prompt or "",
            "enhancements_applied": [],
            "context_injected": {
                "cloud_provider": "",
                "skill_level": "",
                "mode": mode,
                "dimensions_added": [],
                "detected_domains": [],
            },
            "reasoning": "Empty prompt provided. No enhancements applied.",
        }

    prompt_lower = raw_prompt.lower()

    # Stage 1: Domain detection
    detected_domains = _detect_domains(prompt_lower)

    # Stage 2: Dimension injection
    focus_list = (
        [f.strip() for f in focus_areas.split(",") if f.strip()]
        if focus_areas
        else []
    )
    injections, dimensions_added = _get_missing_dimensions(
        prompt_lower, detected_domains, focus_list
    )

    # Stage 3: Cloud provider context
    resolved_provider = _resolve_cloud_provider(prompt_lower, cloud_provider)
    cloud_context = CLOUD_PROVIDER_CONTEXT.get(
        resolved_provider, CLOUD_PROVIDER_CONTEXT["aws"]
    )

    # Stage 4: Skill-level adaptation
    skill_adaptation = get_skill_adaptation(detected_domains)

    # Stage 5: Mode template
    mode_template = MODE_TEMPLATES.get(mode, MODE_TEMPLATES["mentor"])

    # Stage 6: Assembly
    enhanced = _assemble_enhanced_prompt(
        raw_prompt=raw_prompt,
        cloud_context=cloud_context,
        skill_adaptation=skill_adaptation,
        mode_template=mode_template,
        dimension_injections=injections,
        detected_domains=detected_domains,
    )

    enhancements_applied = []
    if dimensions_added:
        enhancements_applied.append("dimension_injection")
    enhancements_applied.append("cloud_context")
    enhancements_applied.append("skill_adaptation")
    enhancements_applied.append("mode_structuring")
    enhancements_applied.append("xml_structuring")
    enhancements_applied.append("chain_of_thought")

    return {
        "original_prompt": raw_prompt,
        "enhanced_prompt": enhanced,
        "enhancements_applied": enhancements_applied,
        "context_injected": {
            "cloud_provider": resolved_provider,
            "skill_level": skill_adaptation["effective_level"],
            "mode": mode,
            "dimensions_added": dimensions_added,
            "detected_domains": detected_domains,
        },
        "reasoning": _build_reasoning(
            detected_domains, dimensions_added, skill_adaptation, mode
        ),
    }


def _detect_domains(prompt_lower: str) -> list:
    """Score each domain by keyword matches and return sorted by relevance."""
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in prompt_lower)
        if count > 0:
            scores[domain] = count

    if not scores:
        return ["devops"]

    return sorted(scores.keys(), key=lambda d: scores[d], reverse=True)


def _resolve_cloud_provider(prompt_lower: str, explicit_provider: str) -> str:
    """Determine cloud provider from explicit param or prompt content."""
    if explicit_provider:
        return explicit_provider.lower()
    if "gcp" in prompt_lower or "google cloud" in prompt_lower:
        return "gcp"
    if "azure" in prompt_lower:
        return "azure"
    return "aws"


def _get_missing_dimensions(
    prompt_lower: str,
    detected_domains: list,
    focus_list: list,
) -> tuple:
    """
    Find dimensions not already covered in the prompt and return injections.

    Returns:
        Tuple of (injection_texts: list[str], dimension_names: list[str])
    """
    injections = []
    dimensions_added = []
    seen_dimensions = set()

    for domain in detected_domains:
        domain_dimensions = DIMENSION_INJECTIONS.get(domain, {})
        for dim_name, dim_config in domain_dimensions.items():
            if dim_name in seen_dimensions:
                continue

            # If focus_areas specified, only inject matching dimensions
            if focus_list and dim_name not in focus_list:
                continue

            # Check if prompt already covers this dimension
            already_covered = any(
                kw in prompt_lower for kw in dim_config["check_keywords"]
            )

            if not already_covered:
                injections.append(dim_config["injection"])
                dimensions_added.append(f"{domain}:{dim_name}")
                seen_dimensions.add(dim_name)

            # Cap total injections to avoid overwhelming output
            if len(injections) >= MAX_INJECTIONS:
                return injections, dimensions_added

    return injections, dimensions_added


def _assemble_enhanced_prompt(
    raw_prompt: str,
    cloud_context: str,
    skill_adaptation: dict,
    mode_template: dict,
    dimension_injections: list,
    detected_domains: list,
) -> str:
    """Assemble the final enhanced prompt using XML-structured sections."""
    sections = []

    # 1. Context block
    sections.append("<context>")
    sections.append(cloud_context)
    sections.append(f"Domains: {', '.join(detected_domains)}")
    sections.append(f"User experience level: {skill_adaptation['effective_level']}")
    sections.append(f"Response detail: {skill_adaptation['detail_level']}")
    sections.append("</context>")

    # 2. Instructions block
    sections.append("")
    sections.append("<instructions>")
    sections.append(mode_template["preamble"])
    sections.append("")
    sections.append(skill_adaptation["tone"])
    sections.append("</instructions>")

    # 3. The actual task/question
    sections.append("")
    sections.append("<task>")
    sections.append(raw_prompt)
    sections.append("</task>")

    # 4. Additional considerations (injected dimensions)
    if dimension_injections:
        sections.append("")
        sections.append("<additional_considerations>")
        for injection in dimension_injections:
            sections.append(f"- {injection}")
        sections.append("</additional_considerations>")

    # 5. Chain of thought instruction
    sections.append("")
    sections.append("<thinking>")
    sections.append(mode_template["chain_of_thought"])
    sections.append("</thinking>")

    # 6. Output format
    sections.append("")
    sections.append("<output_format>")
    sections.append(mode_template["structure_hint"])
    sections.append("")
    sections.append(skill_adaptation["output_hint"])
    sections.append("</output_format>")

    return "\n".join(sections)


def _build_reasoning(
    detected_domains: list,
    dimensions_added: list,
    skill_adaptation: dict,
    mode: str,
) -> str:
    """Generate a human-readable explanation of the enhancement decisions."""
    parts = []
    parts.append(f"Detected domains: {', '.join(detected_domains)}.")

    if dimensions_added:
        parts.append(
            f"Added {len(dimensions_added)} missing consideration(s): "
            f"{', '.join(dimensions_added)}."
        )
    else:
        parts.append(
            "The prompt already covers the key dimensions for the detected domains."
        )

    parts.append(
        f"Adapted for {skill_adaptation['effective_level']}-level user "
        f"({skill_adaptation['detail_level']} detail)."
    )
    parts.append(f"Structured for {mode} mode.")

    return " ".join(parts)
