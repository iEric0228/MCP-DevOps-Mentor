import io
import re
from typing import Dict, List

try:
    import hcl2
    HCL2_AVAILABLE = True
except ImportError:
    HCL2_AVAILABLE = False

CRITICAL = "critical"
WARNING = "warning"
INFO = "info"


def _parse_tf_content(content: str) -> Dict:
    if not HCL2_AVAILABLE:
        return {}
    try:
        return hcl2.load(io.StringIO(content))
    except Exception:
        return {}


def _iter_blocks(data, key: str):
    blocks = data.get(key, [])
    if isinstance(blocks, list):
        return blocks
    return [blocks]


def _check_hardcoded_secrets(content: str, filename: str) -> List[Dict]:
    findings = []
    secret_patterns = [
        (r'(?i)(password|secret|api_key|access_key|token)\s*=\s*"[^${}][^"]*"',
         "Possible hardcoded credential"),
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID detected"),
        (r'(?i)secret_key\s*=\s*"[^${}]', "Hardcoded AWS secret key"),
    ]
    for pattern, message in secret_patterns:
        if re.search(pattern, content):
            findings.append({
                "severity": CRITICAL,
                "message": f"{filename}: {message}",
                "recommendation": "Use variables with sensitive=true or reference AWS Secrets Manager/SSM Parameter Store",
            })
    return findings


def _check_backend_config(parsed: Dict, filename: str) -> List[Dict]:
    findings = []
    has_backend = False

    for block in _iter_blocks(parsed, "terraform"):
        if not isinstance(block, dict):
            continue
        if "backend" not in block:
            continue
        has_backend = True
        backends = block["backend"]
        if isinstance(backends, list):
            for b in backends:
                if isinstance(b, dict) and "s3" in b:
                    s3_config = b["s3"]
                    if isinstance(s3_config, list):
                        s3_config = s3_config[0] if s3_config else {}
                    if isinstance(s3_config, dict) and "dynamodb_table" not in s3_config:
                        findings.append({
                            "severity": WARNING,
                            "message": f"{filename}: S3 backend without DynamoDB state locking",
                            "recommendation": "Add dynamodb_table for state locking to prevent concurrent modifications",
                        })

    if not has_backend:
        findings.append({
            "severity": CRITICAL,
            "message": f"{filename}: no remote backend configured (using local state)",
            "recommendation": "Configure a remote backend (S3 + DynamoDB) for team collaboration and state safety",
        })
    return findings


def _check_provider_versions(parsed: Dict, filename: str) -> List[Dict]:
    findings = []
    has_version_constraint = False

    for block in _iter_blocks(parsed, "terraform"):
        if not isinstance(block, dict):
            continue
        required_providers = block.get("required_providers", [])
        if required_providers:
            has_version_constraint = True

    if not has_version_constraint:
        findings.append({
            "severity": WARNING,
            "message": f"{filename}: no required_providers with version constraints",
            "recommendation": "Pin provider versions to prevent unexpected upgrades",
        })
    return findings


def _check_resource_tags(parsed: Dict, filename: str) -> List[Dict]:
    findings = []
    for resource_block in _iter_blocks(parsed, "resource"):
        if not isinstance(resource_block, dict):
            continue
        for resource_type, instances in resource_block.items():
            if not isinstance(instances, list):
                instances = [instances]
            for instance in instances:
                if not isinstance(instance, dict):
                    continue
                for name, config in instance.items():
                    if isinstance(config, dict) and "tags" not in config:
                        findings.append({
                            "severity": INFO,
                            "message": f"{filename}: {resource_type}.{name} has no tags",
                            "recommendation": "Add tags for cost allocation and resource management",
                        })
    return findings


def _check_security_groups(parsed: Dict, filename: str) -> List[Dict]:
    findings = []
    for resource_block in _iter_blocks(parsed, "resource"):
        if not isinstance(resource_block, dict):
            continue
        for resource_type in ["aws_security_group", "aws_security_group_rule"]:
            instances = resource_block.get(resource_type, [])
            if not isinstance(instances, list):
                instances = [instances]
            for instance in instances:
                if not isinstance(instance, dict):
                    continue
                for name, config in instance.items():
                    if "0.0.0.0/0" in str(config):
                        findings.append({
                            "severity": CRITICAL,
                            "message": f"{filename}: {resource_type}.{name} allows 0.0.0.0/0",
                            "recommendation": "Restrict CIDR blocks to known IP ranges",
                        })
    return findings


def _check_s3_security(parsed: Dict, filename: str) -> List[Dict]:
    findings = []
    for resource_block in _iter_blocks(parsed, "resource"):
        if not isinstance(resource_block, dict):
            continue
        buckets = resource_block.get("aws_s3_bucket", [])
        if not isinstance(buckets, list):
            buckets = [buckets]
        for bucket in buckets:
            if not isinstance(bucket, dict):
                continue
            for name, config in bucket.items():
                config_str = str(config)
                if "server_side_encryption_configuration" not in config_str:
                    findings.append({
                        "severity": WARNING,
                        "message": f"{filename}: aws_s3_bucket.{name} may lack encryption",
                        "recommendation": "Enable server-side encryption (SSE-S3 or SSE-KMS)",
                    })
                if "versioning" not in config_str:
                    findings.append({
                        "severity": WARNING,
                        "message": f"{filename}: aws_s3_bucket.{name} may lack versioning",
                        "recommendation": "Enable versioning for data protection and recovery",
                    })
    return findings


def _check_iam_policies(parsed: Dict, filename: str) -> List[Dict]:
    findings = []
    content_str = str(parsed)
    if '"*"' in content_str and ("Action" in content_str or "action" in content_str):
        findings.append({
            "severity": CRITICAL,
            "message": f"{filename}: IAM policy may contain wildcard (*) actions",
            "recommendation": "Follow least-privilege: specify exact actions needed instead of '*'",
        })
    return findings


def _check_lifecycle_rules(parsed: Dict, filename: str) -> List[Dict]:
    findings = []
    stateful_types = ["aws_instance", "aws_db_instance", "aws_ecs_service"]
    for resource_block in _iter_blocks(parsed, "resource"):
        if not isinstance(resource_block, dict):
            continue
        for resource_type in stateful_types:
            instances = resource_block.get(resource_type, [])
            if not isinstance(instances, list):
                instances = [instances]
            for instance in instances:
                if not isinstance(instance, dict):
                    continue
                for name, config in instance.items():
                    if isinstance(config, dict) and "lifecycle" not in config:
                        findings.append({
                            "severity": INFO,
                            "message": f"{filename}: {resource_type}.{name} has no lifecycle block",
                            "recommendation": "Consider adding lifecycle { prevent_destroy = true } for stateful resources",
                        })
    return findings


def review_terraform(files: Dict[str, str]) -> Dict:
    """Review Terraform files using HCL2 parsing.

    Args:
        files: dict mapping filename to file content (only .tf files)

    Returns:
        Dict with findings, risks, improvements, maturity_level, severity_summary,
        and detected_resources for downstream use by AWS advisor
    """
    all_findings = []
    tf_files = [name for name in files if name.endswith(".tf")]
    detected_resources = set()

    for name in tf_files:
        content = files[name]
        all_findings.extend(_check_hardcoded_secrets(content, name))

        parsed = _parse_tf_content(content)
        if not parsed:
            all_findings.append({
                "severity": INFO,
                "message": f"{name}: could not parse HCL2 (syntax issue or pyhcl2 unavailable)",
                "recommendation": "Validate Terraform syntax with 'terraform validate'",
            })
            continue

        for resource_block in _iter_blocks(parsed, "resource"):
            if isinstance(resource_block, dict):
                detected_resources.update(resource_block.keys())

        all_findings.extend(_check_backend_config(parsed, name))
        all_findings.extend(_check_provider_versions(parsed, name))
        all_findings.extend(_check_resource_tags(parsed, name))
        all_findings.extend(_check_security_groups(parsed, name))
        all_findings.extend(_check_s3_security(parsed, name))
        all_findings.extend(_check_iam_policies(parsed, name))
        all_findings.extend(_check_lifecycle_rules(parsed, name))

    critical = [f for f in all_findings if f["severity"] == CRITICAL]
    warnings = [f for f in all_findings if f["severity"] == WARNING]
    info = [f for f in all_findings if f["severity"] == INFO]

    risks = [f["message"] for f in critical + warnings]
    improvements = list(dict.fromkeys(f["recommendation"] for f in all_findings))

    maturity = "basic"
    if len(critical) == 0 and len(warnings) <= 3:
        maturity = "developing"
    if len(critical) == 0 and len(warnings) == 0:
        maturity = "production-leaning"

    return {
        "iac_type": "terraform",
        "files_reviewed": tf_files,
        "maturity_level": maturity,
        "findings": [f["message"] for f in info],
        "risks": risks,
        "recommended_improvements": improvements,
        "detailed_findings": all_findings,
        "severity_summary": {
            "critical": len(critical),
            "warning": len(warnings),
            "info": len(info),
        },
        "detected_resources": list(detected_resources),
    }
