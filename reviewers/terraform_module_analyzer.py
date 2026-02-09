import re
from typing import Dict, List

from reviewers.terraform_reviewer import _parse_tf_content, _iter_blocks

CRITICAL = "critical"
WARNING = "warning"
INFO = "info"

SENSITIVE_VARIABLE_PATTERNS = [
    "password",
    "secret",
    "token",
    "api_key",
    "access_key",
    "private_key",
    "credentials",
    "connection_string",
    "auth",
    "db_pass",
    "master_password",
    "admin_password",
]

TRUSTED_REGISTRY_PREFIXES = [
    "hashicorp/",
    "registry.terraform.io/",
    "./",
    "../",
]

RESOURCE_COST_MAP = {
    # resource_type: (cost_tier, label, est_monthly_low_usd, est_monthly_high_usd)
    "aws_nat_gateway": ("high", "NAT Gateway", 32, 100),
    "aws_instance": ("medium", "EC2 Instance", 10, 500),
    "aws_db_instance": ("high", "RDS Instance", 25, 1000),
    "aws_db_cluster": ("very_high", "RDS Aurora Cluster", 50, 2000),
    "aws_eks_cluster": ("very_high", "EKS Cluster", 73, 500),
    "aws_eks_node_group": ("high", "EKS Node Group", 50, 2000),
    "aws_elasticache_cluster": ("high", "ElastiCache Cluster", 25, 500),
    "aws_cloudfront_distribution": ("medium", "CloudFront Distribution", 1, 500),
    "aws_lambda_function": ("low", "Lambda Function", 0, 50),
    "aws_s3_bucket": ("low", "S3 Bucket", 0, 100),
    "aws_sqs_queue": ("low", "SQS Queue", 0, 10),
    "aws_sns_topic": ("low", "SNS Topic", 0, 10),
    "aws_eip": ("low", "Elastic IP", 4, 4),
    "aws_ecs_cluster": ("medium", "ECS Cluster", 0, 200),
    "aws_ecs_service": ("medium", "ECS Service (Fargate)", 10, 500),
    "aws_vpc": ("low", "VPC", 0, 0),
    "aws_subnet": ("low", "Subnet", 0, 0),
    "aws_iam_role": ("low", "IAM Role", 0, 0),
}


# ---------------------------------------------------------------------------
# Module Structure Checks
# ---------------------------------------------------------------------------


def _check_module_sources(
    parsed_files: Dict[str, Dict], all_tf_paths: List[str]
) -> List[Dict]:
    """Check that module source paths are valid and from trusted origins."""
    findings: List[Dict] = []
    for filename, parsed in parsed_files.items():
        for module_block in _iter_blocks(parsed, "module"):
            if not isinstance(module_block, dict):
                continue
            for module_name, configs in module_block.items():
                if not isinstance(configs, list):
                    configs = [configs]
                for config in configs:
                    if not isinstance(config, dict):
                        continue
                    source = config.get("source", "")
                    if isinstance(source, list):
                        source = source[0] if source else ""
                    if not source:
                        findings.append(
                            {
                                "severity": CRITICAL,
                                "message": f"{filename}: module '{module_name}' has no source attribute",
                                "recommendation": "Every module block must specify a source path or registry address",
                            }
                        )
                        continue

                    # Local module – check that the target directory has .tf files
                    if source.startswith("./") or source.startswith("../"):
                        normalized = source.rstrip("/")
                        # Strip leading ./ or ../ to get a relative dir prefix
                        module_dir_prefix = normalized.lstrip("./").lstrip("../")
                        has_files = any(
                            p.startswith(module_dir_prefix + "/")
                            or p.startswith(source.rstrip("/") + "/")
                            for p in all_tf_paths
                        )
                        if not has_files:
                            findings.append(
                                {
                                    "severity": WARNING,
                                    "message": (
                                        f"{filename}: module '{module_name}' references "
                                        f"local path '{source}' but no .tf files found there"
                                    ),
                                    "recommendation": "Verify the module source path exists and contains .tf files",
                                }
                            )
                    # Remote source – warn if not from a well-known origin
                    elif not any(
                        source.startswith(prefix)
                        for prefix in TRUSTED_REGISTRY_PREFIXES
                    ):
                        if (
                            "github.com" not in source
                            and "terraform.io" not in source
                        ):
                            findings.append(
                                {
                                    "severity": WARNING,
                                    "message": (
                                        f"{filename}: module '{module_name}' uses "
                                        f"potentially untrusted source '{source}'"
                                    ),
                                    "recommendation": "Prefer modules from the official Terraform Registry or verified sources",
                                }
                            )
    return findings


def _check_module_required_variables(
    parsed_files: Dict[str, Dict],
) -> List[Dict]:
    """For local modules, check that all required variables are passed."""
    findings: List[Dict] = []

    # Build map: directory_prefix -> {var_name: has_default}
    module_vars: Dict[str, Dict[str, bool]] = {}
    for filename, parsed in parsed_files.items():
        dir_prefix = "/".join(filename.split("/")[:-1]) if "/" in filename else ""
        for var_block in _iter_blocks(parsed, "variable"):
            if not isinstance(var_block, dict):
                continue
            for var_name, var_config_list in var_block.items():
                configs = (
                    var_config_list
                    if isinstance(var_config_list, list)
                    else [var_config_list]
                )
                for var_config in configs:
                    has_default = isinstance(var_config, dict) and "default" in var_config
                    module_vars.setdefault(dir_prefix, {})[var_name] = has_default

    # Check each module call against its child module's required variables
    for filename, parsed in parsed_files.items():
        for module_block in _iter_blocks(parsed, "module"):
            if not isinstance(module_block, dict):
                continue
            for module_name, configs in module_block.items():
                if not isinstance(configs, list):
                    configs = [configs]
                for config in configs:
                    if not isinstance(config, dict):
                        continue
                    source = config.get("source", "")
                    if isinstance(source, list):
                        source = source[0] if source else ""
                    if not (source.startswith("./") or source.startswith("../")):
                        continue  # Only validate local modules

                    # Resolve relative path
                    caller_dir = (
                        "/".join(filename.split("/")[:-1]) if "/" in filename else ""
                    )
                    resolved_dir = (
                        source.replace("./", "").replace("../", "").rstrip("/")
                    )
                    if caller_dir:
                        resolved_dir = caller_dir + "/" + resolved_dir

                    if resolved_dir not in module_vars:
                        continue  # Module dir not parsed

                    meta_keys = {
                        "source",
                        "version",
                        "providers",
                        "depends_on",
                        "count",
                        "for_each",
                    }
                    passed_args = set(config.keys()) - meta_keys
                    required_vars = {
                        name
                        for name, has_default in module_vars[resolved_dir].items()
                        if not has_default
                    }
                    missing = required_vars - passed_args
                    for var in sorted(missing):
                        findings.append(
                            {
                                "severity": CRITICAL,
                                "message": (
                                    f"{filename}: module '{module_name}' missing "
                                    f"required variable '{var}'"
                                ),
                                "recommendation": (
                                    f"Pass variable '{var}' to module '{module_name}' "
                                    f"-- it has no default value"
                                ),
                            }
                        )
    return findings


def _check_variable_usage(
    parsed_files: Dict[str, Dict], raw_files: Dict[str, str]
) -> List[Dict]:
    """Cross-validate variable declarations against usage."""
    findings: List[Dict] = []

    # Collect all declared variables
    declared_vars: Dict[str, str] = {}  # var_name -> declaring_filename
    for filename, parsed in parsed_files.items():
        for var_block in _iter_blocks(parsed, "variable"):
            if not isinstance(var_block, dict):
                continue
            for var_name in var_block:
                declared_vars[var_name] = filename

    # Collect all var.X references across raw file content
    all_content = " ".join(raw_files.values())
    used_var_names = set(re.findall(r"var\.(\w+)", all_content))

    # Declared but unused
    for var_name, declaring_file in declared_vars.items():
        if var_name not in used_var_names:
            findings.append(
                {
                    "severity": INFO,
                    "message": (
                        f"{declaring_file}: variable '{var_name}' is declared "
                        f"but never referenced"
                    ),
                    "recommendation": (
                        f"Remove unused variable '{var_name}' or confirm "
                        f"it is passed to a module"
                    ),
                }
            )

    # Used but undeclared
    for var_name in used_var_names:
        if var_name not in declared_vars:
            findings.append(
                {
                    "severity": WARNING,
                    "message": (
                        f"variable '{var_name}' is referenced (var.{var_name}) "
                        f"but never declared in any variables file"
                    ),
                    "recommendation": f'Add a variable "{var_name}" block in variables.tf',
                }
            )

    return findings


def _check_output_references(
    parsed_files: Dict[str, Dict],
) -> List[Dict]:
    """Check that outputs reference resources/modules/data/locals that exist."""
    findings: List[Dict] = []

    # Collect all declared identifiers
    declared_resources: set = set()
    declared_data_sources: set = set()
    declared_locals: set = set()
    declared_modules: set = set()

    for _filename, parsed in parsed_files.items():
        for resource_block in _iter_blocks(parsed, "resource"):
            if isinstance(resource_block, dict):
                for res_type, instances in resource_block.items():
                    if not isinstance(instances, list):
                        instances = [instances]
                    for inst in instances:
                        if isinstance(inst, dict):
                            for name in inst:
                                declared_resources.add(f"{res_type}.{name}")

        for data_block in _iter_blocks(parsed, "data"):
            if isinstance(data_block, dict):
                for data_type, instances in data_block.items():
                    if not isinstance(instances, list):
                        instances = [instances]
                    for inst in instances:
                        if isinstance(inst, dict):
                            for name in inst:
                                declared_data_sources.add(f"data.{data_type}.{name}")

        for module_block in _iter_blocks(parsed, "module"):
            if isinstance(module_block, dict):
                for mod_name in module_block:
                    declared_modules.add(f"module.{mod_name}")

        for locals_block in _iter_blocks(parsed, "locals"):
            if isinstance(locals_block, dict):
                for local_name in locals_block:
                    declared_locals.add(f"local.{local_name}")

    # Check output value references
    for filename, parsed in parsed_files.items():
        for output_block in _iter_blocks(parsed, "output"):
            if not isinstance(output_block, dict):
                continue
            for output_name, output_config_list in output_block.items():
                configs = (
                    output_config_list
                    if isinstance(output_config_list, list)
                    else [output_config_list]
                )
                for output_config in configs:
                    if not isinstance(output_config, dict):
                        continue
                    value_str = str(output_config.get("value", ""))
                    refs = re.findall(
                        r"(?:module|data|local|aws_\w+)\.\w+", value_str
                    )
                    for ref in refs:
                        if ref.startswith("module.") and ref not in declared_modules:
                            findings.append(
                                {
                                    "severity": WARNING,
                                    "message": (
                                        f"{filename}: output '{output_name}' references "
                                        f"'{ref}' which is not declared"
                                    ),
                                    "recommendation": f"Verify that {ref} exists or fix the output value reference",
                                }
                            )
                        elif (
                            ref.startswith("data.") and ref not in declared_data_sources
                        ):
                            findings.append(
                                {
                                    "severity": WARNING,
                                    "message": (
                                        f"{filename}: output '{output_name}' references "
                                        f"'{ref}' which is not declared"
                                    ),
                                    "recommendation": f"Verify that {ref} exists or fix the output value reference",
                                }
                            )
                        elif (
                            ref.startswith("local.") and ref not in declared_locals
                        ):
                            findings.append(
                                {
                                    "severity": WARNING,
                                    "message": (
                                        f"{filename}: output '{output_name}' references "
                                        f"'{ref}' which is not declared"
                                    ),
                                    "recommendation": f"Verify that {ref} exists or fix the output value reference",
                                }
                            )
                        elif not ref.startswith(("module.", "data.", "local.")):
                            # Resource reference like aws_instance.web
                            if ref not in declared_resources:
                                findings.append(
                                    {
                                        "severity": WARNING,
                                        "message": (
                                            f"{filename}: output '{output_name}' references "
                                            f"'{ref}' which is not declared"
                                        ),
                                        "recommendation": f"Verify that {ref} exists or fix the output value reference",
                                    }
                                )

    return findings


# ---------------------------------------------------------------------------
# Security Checks — Sensitive Data Leak Prevention
# ---------------------------------------------------------------------------


def _check_sensitive_variables(parsed_files: Dict[str, Dict]) -> List[Dict]:
    """Flag variables holding secrets that lack sensitive = true."""
    findings: List[Dict] = []
    for filename, parsed in parsed_files.items():
        for var_block in _iter_blocks(parsed, "variable"):
            if not isinstance(var_block, dict):
                continue
            for var_name, var_config_list in var_block.items():
                name_lower = var_name.lower()
                is_sensitive_name = any(
                    pat in name_lower for pat in SENSITIVE_VARIABLE_PATTERNS
                )
                if not is_sensitive_name:
                    continue
                configs = (
                    var_config_list
                    if isinstance(var_config_list, list)
                    else [var_config_list]
                )
                for var_config in configs:
                    if not isinstance(var_config, dict):
                        continue
                    sensitive_flag = var_config.get("sensitive", [False])
                    if isinstance(sensitive_flag, list):
                        sensitive_flag = sensitive_flag[0] if sensitive_flag else False

                    if not sensitive_flag:
                        findings.append(
                            {
                                "severity": CRITICAL,
                                "message": (
                                    f"{filename}: variable '{var_name}' appears to hold "
                                    f"sensitive data but lacks sensitive = true"
                                ),
                                "recommendation": (
                                    f"Add 'sensitive = true' to variable '{var_name}' to "
                                    f"prevent it from appearing in plan/apply output"
                                ),
                            }
                        )

                    # Check for hardcoded default on sensitive vars
                    default_val = var_config.get("default", None)
                    if isinstance(default_val, list):
                        default_val = default_val[0] if default_val else None
                    if (
                        default_val is not None
                        and default_val != ""
                        and default_val != []
                    ):
                        findings.append(
                            {
                                "severity": CRITICAL,
                                "message": (
                                    f"{filename}: variable '{var_name}' has a hardcoded "
                                    f"default for a sensitive value"
                                ),
                                "recommendation": (
                                    f"Remove the default from '{var_name}' -- sensitive "
                                    f"values should come from .tfvars or environment variables"
                                ),
                            }
                        )
    return findings


def _check_sensitive_outputs(
    parsed_files: Dict[str, Dict],
) -> List[Dict]:
    """Flag outputs exposing sensitive data without sensitive = true."""
    findings: List[Dict] = []
    for filename, parsed in parsed_files.items():
        for output_block in _iter_blocks(parsed, "output"):
            if not isinstance(output_block, dict):
                continue
            for output_name, output_config_list in output_block.items():
                configs = (
                    output_config_list
                    if isinstance(output_config_list, list)
                    else [output_config_list]
                )
                for output_config in configs:
                    if not isinstance(output_config, dict):
                        continue
                    value_str = str(output_config.get("value", "")).lower()
                    is_sensitive = any(
                        pat in value_str for pat in SENSITIVE_VARIABLE_PATTERNS
                    )
                    if not is_sensitive:
                        is_sensitive = any(
                            pat in output_name.lower()
                            for pat in SENSITIVE_VARIABLE_PATTERNS
                        )
                    if not is_sensitive:
                        continue

                    sensitive_flag = output_config.get("sensitive", [False])
                    if isinstance(sensitive_flag, list):
                        sensitive_flag = sensitive_flag[0] if sensitive_flag else False
                    if not sensitive_flag:
                        findings.append(
                            {
                                "severity": CRITICAL,
                                "message": (
                                    f"{filename}: output '{output_name}' may expose "
                                    f"sensitive data without sensitive = true"
                                ),
                                "recommendation": (
                                    f"Add 'sensitive = true' to output '{output_name}' "
                                    f"or remove the sensitive reference"
                                ),
                            }
                        )
    return findings


def _check_tfvars_secrets(raw_files: Dict[str, str]) -> List[Dict]:
    """Scan .tfvars files for hardcoded secrets."""
    findings: List[Dict] = []
    secret_patterns = [
        (
            r'(?i)(password|secret|api_key|access_key|token)\s*=\s*"[^${}][^"]{3,}"',
            "Hardcoded secret in tfvars",
        ),
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID in tfvars"),
    ]
    for filename, content in raw_files.items():
        if not filename.endswith(".tfvars"):
            continue
        for pattern, message in secret_patterns:
            if re.search(pattern, content):
                findings.append(
                    {
                        "severity": CRITICAL,
                        "message": f"{filename}: {message}",
                        "recommendation": (
                            "Never store secrets in .tfvars files. Use environment "
                            "variables, AWS Secrets Manager, or a secrets management tool"
                        ),
                    }
                )
    return findings


def _check_untrusted_module_sources(parsed_files: Dict[str, Dict]) -> List[Dict]:
    """Flag modules from git URLs without version pinning."""
    findings: List[Dict] = []
    for filename, parsed in parsed_files.items():
        for module_block in _iter_blocks(parsed, "module"):
            if not isinstance(module_block, dict):
                continue
            for module_name, configs in module_block.items():
                if not isinstance(configs, list):
                    configs = [configs]
                for config in configs:
                    if not isinstance(config, dict):
                        continue
                    source = config.get("source", "")
                    if isinstance(source, list):
                        source = source[0] if source else ""
                    version = config.get("version", "")
                    if isinstance(version, list):
                        version = version[0] if version else ""

                    # Git URL without ref pinning
                    if "git::" in source or (
                        "github.com" in source and "git" in source
                    ):
                        if "?ref=" not in source and not version:
                            findings.append(
                                {
                                    "severity": WARNING,
                                    "message": (
                                        f"{filename}: module '{module_name}' uses git "
                                        f"source without version pinning"
                                    ),
                                    "recommendation": (
                                        "Pin module to a specific git tag or commit hash "
                                        "using ?ref=v1.0.0"
                                    ),
                                }
                            )

                    # Registry module without version constraint
                    if (
                        not source.startswith("./")
                        and not source.startswith("../")
                        and "git::" not in source
                        and "github.com" not in source
                    ):
                        if source and not version:
                            findings.append(
                                {
                                    "severity": WARNING,
                                    "message": (
                                        f"{filename}: module '{module_name}' has no "
                                        f"version constraint"
                                    ),
                                    "recommendation": (
                                        "Pin registry modules with a version constraint "
                                        '(e.g., version = "~> 3.0")'
                                    ),
                                }
                            )
    return findings


# ---------------------------------------------------------------------------
# Cost Summary
# ---------------------------------------------------------------------------


def _generate_cost_summary(parsed_files: Dict[str, Dict]) -> Dict:
    """Detect resources and generate a cost tier summary."""
    resource_costs: List[Dict] = []

    for filename, parsed in parsed_files.items():
        for resource_block in _iter_blocks(parsed, "resource"):
            if not isinstance(resource_block, dict):
                continue
            for resource_type, instances in resource_block.items():
                if resource_type not in RESOURCE_COST_MAP:
                    continue
                tier, label, est_low, est_high = RESOURCE_COST_MAP[resource_type]
                if not isinstance(instances, list):
                    instances = [instances]
                for instance in instances:
                    if not isinstance(instance, dict):
                        continue
                    for name in instance:
                        resource_costs.append(
                            {
                                "resource_type": resource_type,
                                "resource_name": name,
                                "cost_tier": tier,
                                "label": label,
                                "estimated_monthly_range_usd": f"${est_low}-${est_high}",
                                "filename": filename,
                            }
                        )

    # Aggregate by tier
    tier_counts = {"low": 0, "medium": 0, "high": 0, "very_high": 0}
    total_low = 0
    total_high = 0
    for rc in resource_costs:
        tier_counts[rc["cost_tier"]] += 1
        _tier, _label, est_low, est_high = RESOURCE_COST_MAP[rc["resource_type"]]
        total_low += est_low
        total_high += est_high

    # Generate cost findings for expensive resources
    cost_findings: List[Dict] = []
    for rc in resource_costs:
        if rc["cost_tier"] in ("high", "very_high"):
            sev = WARNING if rc["cost_tier"] == "high" else CRITICAL
            cost_findings.append(
                {
                    "severity": sev,
                    "message": (
                        f"{rc['filename']}: {rc['label']} "
                        f"({rc['resource_type']}.{rc['resource_name']}) is a "
                        f"{rc['cost_tier']}-cost resource "
                        f"({rc['estimated_monthly_range_usd']}/mo)"
                    ),
                    "recommendation": (
                        f"Review if {rc['resource_type']}.{rc['resource_name']} is "
                        f"right-sized. Consider reserved capacity or smaller instance "
                        f"types for non-production use"
                    ),
                }
            )

    return {
        "resource_costs": resource_costs,
        "tier_summary": tier_counts,
        "estimated_monthly_total_usd": f"${total_low}-${total_high}",
        "cost_findings": cost_findings,
    }


# ---------------------------------------------------------------------------
# Public Entry Point
# ---------------------------------------------------------------------------


def analyze_terraform_modules(files: Dict[str, str]) -> Dict:
    """Analyze Terraform modules for structure, security, and cost.

    Args:
        files: dict mapping filename to file content (.tf and .tfvars files)

    Returns:
        Dict with module_findings, security_findings, cost_summary,
        maturity_level, severity_summary, risks, recommended_improvements
    """
    all_findings: List[Dict] = []
    tf_files = {name: content for name, content in files.items() if name.endswith(".tf")}
    all_tf_paths = list(tf_files.keys())

    # Parse all .tf files
    parsed_files: Dict[str, Dict] = {}
    for name, content in tf_files.items():
        parsed = _parse_tf_content(content)
        if parsed:
            parsed_files[name] = parsed
        else:
            all_findings.append(
                {
                    "severity": INFO,
                    "message": (
                        f"{name}: could not parse HCL2 "
                        f"(syntax issue or python-hcl2 unavailable)"
                    ),
                    "recommendation": "Validate Terraform syntax with 'terraform validate'",
                }
            )

    # --- Module structure checks ---
    module_findings: List[Dict] = []
    module_findings.extend(_check_module_sources(parsed_files, all_tf_paths))
    module_findings.extend(_check_module_required_variables(parsed_files))
    module_findings.extend(_check_variable_usage(parsed_files, files))
    module_findings.extend(_check_output_references(parsed_files))
    all_findings.extend(module_findings)

    # --- Security checks ---
    security_findings: List[Dict] = []
    security_findings.extend(_check_sensitive_variables(parsed_files))
    security_findings.extend(_check_sensitive_outputs(parsed_files))
    security_findings.extend(_check_tfvars_secrets(files))
    security_findings.extend(_check_untrusted_module_sources(parsed_files))
    all_findings.extend(security_findings)

    # --- Cost summary ---
    cost_summary = _generate_cost_summary(parsed_files)
    all_findings.extend(cost_summary["cost_findings"])

    # --- Categorize by severity ---
    critical = [f for f in all_findings if f["severity"] == CRITICAL]
    warnings = [f for f in all_findings if f["severity"] == WARNING]
    info = [f for f in all_findings if f["severity"] == INFO]

    risks = [f["message"] for f in critical + warnings]
    improvements = list(dict.fromkeys(f["recommendation"] for f in all_findings))

    if len(critical) == 0 and len(warnings) == 0:
        maturity = "production-leaning"
    elif len(critical) == 0 and len(warnings) <= 3:
        maturity = "developing"
    else:
        maturity = "basic"

    return {
        "analysis_type": "terraform-module-analysis",
        "files_analyzed": list(files.keys()),
        "maturity_level": maturity,
        "module_findings": module_findings,
        "security_findings": security_findings,
        "cost_summary": {
            "resource_costs": cost_summary["resource_costs"],
            "tier_summary": cost_summary["tier_summary"],
            "estimated_monthly_total_usd": cost_summary["estimated_monthly_total_usd"],
        },
        "findings": [f["message"] for f in info],
        "risks": risks,
        "recommended_improvements": improvements,
        "detailed_findings": all_findings,
        "severity_summary": {
            "critical": len(critical),
            "warning": len(warnings),
            "info": len(info),
        },
    }
