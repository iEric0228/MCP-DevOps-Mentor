from reviewers.cicd_reviewer import review_github_actions


def test_valid_yaml_parsed(sample_workflow_secure):
    result = review_github_actions(sample_workflow_secure)
    assert result["ci_cd_type"] == "github-actions"
    assert "ci.yml" in result["pipeline_files"]
    assert "severity_summary" in result


def test_invalid_yaml():
    files = {"bad.yml": "name: test\n  invalid: [yaml: {broken"}
    result = review_github_actions(files)
    assert any("failed to parse YAML" in f["message"] for f in result["detailed_findings"])
    assert result["severity_summary"]["critical"] >= 1


def test_missing_permissions(sample_workflow_insecure):
    result = review_github_actions(sample_workflow_insecure)
    assert any("permissions" in r for r in result["risks"])


def test_permissions_present(sample_workflow_secure):
    result = review_github_actions(sample_workflow_secure)
    assert not any("permissions" in r for r in result["risks"])


def test_action_pinning_sha():
    files = {
        "ci.yml": """
name: CI
on: push
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675
"""
    }
    result = review_github_actions(files)
    pinning_warnings = [
        f for f in result["detailed_findings"]
        if "tag reference" in f.get("message", "")
    ]
    assert len(pinning_warnings) == 0


def test_action_pinning_tag_warns():
    files = {
        "ci.yml": """
name: CI
on: push
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
"""
    }
    result = review_github_actions(files)
    pinning_warnings = [
        f for f in result["detailed_findings"]
        if "tag reference" in f.get("message", "")
    ]
    assert len(pinning_warnings) >= 1


def test_timeout_check(sample_workflow_insecure):
    result = review_github_actions(sample_workflow_insecure)
    assert any("timeout" in r.lower() for r in result["risks"])


def test_self_hosted_runner(sample_workflow_insecure):
    result = review_github_actions(sample_workflow_insecure)
    assert any("self-hosted" in r for r in result["risks"])


def test_aws_oidc_missing(sample_workflow_insecure):
    result = review_github_actions(sample_workflow_insecure)
    assert any("OIDC" in r or "oidc" in r.lower() for r in result["risks"])


def test_terraform_apply_unguarded(sample_workflow_insecure):
    result = review_github_actions(sample_workflow_insecure)
    assert any("terraform apply" in r for r in result["risks"])


def test_concurrency_check():
    files = {
        "ci.yml": """
name: CI
on: push
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675
"""
    }
    result = review_github_actions(files)
    assert any("concurrency" in f["message"] for f in result["detailed_findings"])


def test_caching_check():
    files = {
        "ci.yml": """
name: CI
on: push
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675
      - run: npm install
"""
    }
    result = review_github_actions(files)
    assert any("caching" in r.lower() for r in result["risks"])


def test_maturity_production_leaning(sample_workflow_secure):
    result = review_github_actions(sample_workflow_secure)
    # Secure workflow should have few/no critical or warning issues
    assert result["maturity_level"] in ("developing", "production-leaning")


def test_backward_compatible_output(sample_workflow_secure):
    result = review_github_actions(sample_workflow_secure)
    assert "findings" in result
    assert "risks" in result
    assert "recommended_improvements" in result
    assert "maturity_level" in result
    assert "detailed_findings" in result
    assert "severity_summary" in result


def test_non_yaml_files_ignored():
    files = {
        "readme.md": "# Hello",
        "ci.yml": """
name: CI
on: push
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675
""",
    }
    result = review_github_actions(files)
    assert "readme.md" not in result["pipeline_files"]
    assert "ci.yml" in result["pipeline_files"]
