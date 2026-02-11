from enhancer.domain_rules import (
    DOMAIN_KEYWORDS,
    DIMENSION_INJECTIONS,
    CLOUD_PROVIDER_CONTEXT,
    MODE_TEMPLATES,
)


def test_all_domains_have_keywords():
    expected_domains = {
        "ci_cd", "docker", "terraform", "aws",
        "security", "observability", "networking", "cost",
    }
    assert set(DOMAIN_KEYWORDS.keys()) == expected_domains


def test_no_empty_keyword_lists():
    for domain, keywords in DOMAIN_KEYWORDS.items():
        assert len(keywords) > 0, f"Domain '{domain}' has empty keyword list"


def test_all_injection_domains_exist_in_keywords():
    for domain in DIMENSION_INJECTIONS:
        assert domain in DOMAIN_KEYWORDS, (
            f"Injection domain '{domain}' not in DOMAIN_KEYWORDS"
        )


def test_dimension_configs_have_required_keys():
    for domain, dimensions in DIMENSION_INJECTIONS.items():
        for dim_name, dim_config in dimensions.items():
            assert "check_keywords" in dim_config, (
                f"{domain}:{dim_name} missing check_keywords"
            )
            assert "injection" in dim_config, (
                f"{domain}:{dim_name} missing injection"
            )


def test_no_empty_check_keywords():
    for domain, dimensions in DIMENSION_INJECTIONS.items():
        for dim_name, dim_config in dimensions.items():
            assert len(dim_config["check_keywords"]) > 0, (
                f"{domain}:{dim_name} has empty check_keywords"
            )


def test_no_empty_injection_texts():
    for domain, dimensions in DIMENSION_INJECTIONS.items():
        for dim_name, dim_config in dimensions.items():
            assert len(dim_config["injection"].strip()) > 0, (
                f"{domain}:{dim_name} has empty injection text"
            )


def test_cloud_providers_all_present():
    assert "aws" in CLOUD_PROVIDER_CONTEXT
    assert "gcp" in CLOUD_PROVIDER_CONTEXT
    assert "azure" in CLOUD_PROVIDER_CONTEXT


def test_mode_templates_all_present():
    expected_modes = {"mentor", "review", "debug", "interview"}
    assert set(MODE_TEMPLATES.keys()) == expected_modes


def test_mode_templates_have_required_keys():
    required_keys = {"preamble", "structure_hint", "chain_of_thought"}
    for mode_name, template in MODE_TEMPLATES.items():
        assert set(template.keys()) == required_keys, (
            f"Mode '{mode_name}' missing keys: {required_keys - set(template.keys())}"
        )


def test_mode_templates_values_not_empty():
    for mode_name, template in MODE_TEMPLATES.items():
        for key, value in template.items():
            assert len(value.strip()) > 0, (
                f"Mode '{mode_name}' has empty '{key}'"
            )
