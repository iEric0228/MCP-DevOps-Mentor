import yaml
from typing import Dict, List, Optional

CRITICAL = "critical"
WARNING = "warning"
INFO = "info"


def _parse_workflow(content: str) -> Optional[Dict]:
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError:
        return None


def _get_triggers(workflow: Dict) -> Dict:
    return workflow.get("on", workflow.get(True, {}))


def _check_action_pinning(steps: List[Dict], filename: str) -> List[Dict]:
    findings = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        uses = step.get("uses", "")
        if uses and "@" in uses:
            ref = uses.split("@")[1]
            if len(ref) < 40 and not ref.startswith("sha"):
                findings.append({
                    "severity": WARNING,
                    "message": f"{filename}: action '{uses}' uses tag reference instead of SHA pin",
                    "recommendation": "Pin actions to a full commit SHA for supply-chain security",
                })
    return findings


def _check_permissions(workflow: Dict, filename: str) -> List[Dict]:
    findings = []
    if "permissions" not in workflow:
        findings.append({
            "severity": CRITICAL,
            "message": f"{filename}: missing top-level permissions block",
            "recommendation": "Add 'permissions: contents: read' at minimum for least-privilege",
        })
    return findings


def _check_timeouts(jobs: Dict, filename: str) -> List[Dict]:
    findings = []
    for job_name, job_config in jobs.items():
        if isinstance(job_config, dict) and "timeout-minutes" not in job_config:
            findings.append({
                "severity": WARNING,
                "message": f"{filename}: job '{job_name}' has no timeout-minutes",
                "recommendation": f"Add timeout-minutes to job '{job_name}' to prevent runaway builds",
            })
    return findings


def _check_matrix_strategy(jobs: Dict, filename: str) -> List[Dict]:
    findings = []
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue
        strategy = job_config.get("strategy", {})
        if isinstance(strategy, dict) and "matrix" in strategy:
            if "fail-fast" not in strategy:
                findings.append({
                    "severity": INFO,
                    "message": f"{filename}: job '{job_name}' matrix has no fail-fast setting",
                    "recommendation": "Consider setting fail-fast: false for comprehensive test results",
                })
    return findings


def _check_self_hosted_runners(jobs: Dict, filename: str) -> List[Dict]:
    findings = []
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue
        runs_on = job_config.get("runs-on", "")
        if "self-hosted" in str(runs_on):
            findings.append({
                "severity": WARNING,
                "message": f"{filename}: job '{job_name}' uses self-hosted runner",
                "recommendation": "Ensure self-hosted runners are ephemeral and isolated",
            })
    return findings


def _check_workflow_dispatch(workflow: Dict, filename: str) -> List[Dict]:
    findings = []
    triggers = _get_triggers(workflow)
    if not isinstance(triggers, dict):
        return findings
    dispatch = triggers.get("workflow_dispatch")
    if isinstance(dispatch, dict) and "inputs" in dispatch:
        for input_name, input_config in dispatch["inputs"].items():
            if isinstance(input_config, dict) and "description" not in input_config:
                findings.append({
                    "severity": INFO,
                    "message": f"{filename}: workflow_dispatch input '{input_name}' lacks description",
                    "recommendation": "Add descriptions to all workflow_dispatch inputs",
                })
    return findings


def _check_concurrency(workflow: Dict, filename: str) -> List[Dict]:
    findings = []
    if "concurrency" not in workflow:
        findings.append({
            "severity": INFO,
            "message": f"{filename}: no concurrency group defined",
            "recommendation": "Add concurrency group to prevent duplicate runs",
        })
    return findings


def _check_caching(jobs: Dict, filename: str) -> List[Dict]:
    findings = []
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue
        steps = job_config.get("steps", [])
        has_cache = any(
            "actions/cache" in str(s.get("uses", "")) or "cache" in str(s.get("with", {}))
            for s in steps if isinstance(s, dict)
        )
        if not has_cache:
            findings.append({
                "severity": WARNING,
                "message": f"{filename}: job '{job_name}' has no dependency caching",
                "recommendation": "Add actions/cache to speed up builds",
            })
    return findings


def _check_aws_oidc(steps: List[Dict], filename: str) -> List[Dict]:
    findings = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        uses = step.get("uses", "")
        if "aws-actions/configure-aws-credentials" in uses:
            with_block = step.get("with", {})
            if isinstance(with_block, dict) and "role-to-assume" not in with_block:
                findings.append({
                    "severity": CRITICAL,
                    "message": f"{filename}: AWS credentials without OIDC role-to-assume",
                    "recommendation": "Use OIDC with role-to-assume instead of long-lived secrets",
                })
    return findings


def _check_terraform_safety(steps: List[Dict], filename: str) -> List[Dict]:
    findings = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        run_cmd = step.get("run", "")
        if "terraform apply" in run_cmd:
            if_cond = step.get("if", "")
            if not if_cond:
                findings.append({
                    "severity": CRITICAL,
                    "message": f"{filename}: terraform apply without if-guard",
                    "recommendation": "Protect terraform apply with environment conditions or manual approval",
                })
    return findings


def _check_artifact_handling(jobs: Dict, filename: str) -> List[Dict]:
    findings = []
    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue
        steps = job_config.get("steps", [])
        has_upload = any(
            "actions/upload-artifact" in str(s.get("uses", ""))
            for s in steps if isinstance(s, dict)
        )
        has_download = any(
            "actions/download-artifact" in str(s.get("uses", ""))
            for s in steps if isinstance(s, dict)
        )
        if has_upload and not has_download:
            findings.append({
                "severity": INFO,
                "message": f"{filename}: job '{job_name}' uploads artifacts but no job downloads them",
                "recommendation": "Ensure uploaded artifacts are consumed by downstream jobs or used for debugging",
            })
    return findings


def _check_secrets_usage(workflow: Dict, content: str, filename: str) -> List[Dict]:
    findings = []
    if "secrets." in content.lower():
        findings.append({
            "severity": INFO,
            "message": f"{filename}: uses GitHub secrets",
            "recommendation": None,
        })
    return findings


def _check_environment_protection(workflow: Dict, content: str, filename: str) -> List[Dict]:
    findings = []
    jobs = workflow.get("jobs", {})
    for job_name, job_config in jobs.items():
        if isinstance(job_config, dict) and "environment" in job_config:
            findings.append({
                "severity": INFO,
                "message": f"{filename}: job '{job_name}' uses environment protection rules",
                "recommendation": None,
            })
    return findings


def review_github_actions(files: Dict[str, str]) -> Dict:
    """Review GitHub Actions workflow files with proper YAML parsing."""
    all_findings = []
    yaml_files = [name for name in files if name.endswith((".yml", ".yaml"))]

    for name in yaml_files:
        content = files[name]
        workflow = _parse_workflow(content)

        if workflow is None:
            all_findings.append({
                "severity": CRITICAL,
                "message": f"{name}: failed to parse YAML -- invalid syntax",
                "recommendation": "Fix YAML syntax errors before proceeding",
            })
            continue

        if not isinstance(workflow, dict):
            continue

        jobs = workflow.get("jobs", {})
        if not isinstance(jobs, dict):
            jobs = {}

        all_findings.extend(_check_permissions(workflow, name))
        all_findings.extend(_check_concurrency(workflow, name))
        all_findings.extend(_check_workflow_dispatch(workflow, name))
        all_findings.extend(_check_timeouts(jobs, name))
        all_findings.extend(_check_matrix_strategy(jobs, name))
        all_findings.extend(_check_self_hosted_runners(jobs, name))
        all_findings.extend(_check_caching(jobs, name))
        all_findings.extend(_check_artifact_handling(jobs, name))
        all_findings.extend(_check_secrets_usage(workflow, content, name))
        all_findings.extend(_check_environment_protection(workflow, content, name))

        for job_name, job_config in jobs.items():
            if isinstance(job_config, dict):
                steps = job_config.get("steps", [])
                if isinstance(steps, list):
                    all_findings.extend(_check_action_pinning(steps, name))
                    all_findings.extend(_check_aws_oidc(steps, name))
                    all_findings.extend(_check_terraform_safety(steps, name))

    critical = [f for f in all_findings if f["severity"] == CRITICAL]
    warnings = [f for f in all_findings if f["severity"] == WARNING]
    info = [f for f in all_findings if f["severity"] == INFO]

    risks = [f["message"] for f in critical + warnings]
    improvements = list(dict.fromkeys(
        f["recommendation"] for f in all_findings if f.get("recommendation")
    ))
    findings_text = [f["message"] for f in info]

    maturity = "basic"
    if len(critical) == 0 and len(warnings) <= 2:
        maturity = "developing"
    if len(critical) == 0 and len(warnings) == 0:
        maturity = "production-leaning"

    return {
        "ci_cd_type": "github-actions",
        "pipeline_files": yaml_files,
        "maturity_level": maturity,
        "findings": findings_text,
        "risks": risks,
        "recommended_improvements": improvements,
        "detailed_findings": all_findings,
        "severity_summary": {
            "critical": len(critical),
            "warning": len(warnings),
            "info": len(info),
        },
    }
