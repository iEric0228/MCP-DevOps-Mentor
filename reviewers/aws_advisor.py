from typing import Dict, List

CRITICAL = "critical"
WARNING = "warning"
INFO = "info"

SERVICE_RESOURCE_MAP = {
    "ec2": ["aws_instance", "aws_launch_template", "aws_launch_configuration"],
    "s3": ["aws_s3_bucket", "aws_s3_bucket_policy"],
    "rds": ["aws_db_instance", "aws_db_cluster"],
    "ecs": ["aws_ecs_cluster", "aws_ecs_service", "aws_ecs_task_definition"],
    "eks": ["aws_eks_cluster", "aws_eks_node_group"],
    "lambda": ["aws_lambda_function"],
    "vpc": ["aws_vpc", "aws_subnet", "aws_nat_gateway", "aws_eip"],
    "iam": ["aws_iam_role", "aws_iam_policy", "aws_iam_user"],
    "cloudfront": ["aws_cloudfront_distribution"],
    "elasticache": ["aws_elasticache_cluster"],
    "sqs": ["aws_sqs_queue"],
    "sns": ["aws_sns_topic"],
}


def _detect_aws_services(detected_resources: List[str]) -> Dict[str, bool]:
    services = {}
    for service, resource_types in SERVICE_RESOURCE_MAP.items():
        services[service] = any(rt in detected_resources for rt in resource_types)
    return services


def _cost_checks(detected_resources: List[str], terraform_findings: List[Dict]) -> List[Dict]:
    findings = []
    services = _detect_aws_services(detected_resources)

    if "aws_nat_gateway" in detected_resources:
        findings.append({
            "severity": WARNING,
            "category": "cost",
            "message": "NAT Gateway detected -- high per-hour + per-GB cost",
            "recommendation": "Consider NAT instances for dev/staging, or VPC endpoints to reduce NAT traffic",
        })

    if services.get("ec2") and "aws_autoscaling_group" not in detected_resources:
        findings.append({
            "severity": WARNING,
            "category": "cost",
            "message": "EC2 instances without Auto Scaling Group detected",
            "recommendation": "Use Auto Scaling to right-size capacity and reduce cost during low demand",
        })

    if services.get("ec2") and "aws_spot_instance_request" not in detected_resources:
        findings.append({
            "severity": INFO,
            "category": "cost",
            "message": "No spot instances detected",
            "recommendation": "Consider spot instances for fault-tolerant workloads (up to 90% savings)",
        })

    if "aws_eip" in detected_resources:
        findings.append({
            "severity": INFO,
            "category": "cost",
            "message": "Elastic IPs detected -- unattached EIPs incur charges",
            "recommendation": "Audit EIPs and release any that are not attached to running instances",
        })

    if services.get("rds"):
        findings.append({
            "severity": INFO,
            "category": "cost",
            "message": "RDS instance detected",
            "recommendation": "Consider Reserved Instances for production RDS, and Aurora Serverless for variable workloads",
        })

    if services.get("ecs") or services.get("eks"):
        findings.append({
            "severity": INFO,
            "category": "cost",
            "message": "Container orchestration detected",
            "recommendation": "Use Fargate Spot for non-critical ECS tasks, or Karpenter for EKS node optimization",
        })

    return findings


def _security_checks(detected_resources: List[str], terraform_findings: List[Dict]) -> List[Dict]:
    findings = []
    services = _detect_aws_services(detected_resources)

    if services.get("vpc") and "aws_flow_log" not in detected_resources:
        findings.append({
            "severity": WARNING,
            "category": "security",
            "message": "VPC detected without flow logs",
            "recommendation": "Enable VPC Flow Logs for network traffic monitoring and security analysis",
        })

    if "aws_cloudtrail" not in detected_resources:
        findings.append({
            "severity": CRITICAL,
            "category": "security",
            "message": "No CloudTrail configuration detected in Terraform",
            "recommendation": "Enable CloudTrail for API audit logging across all regions",
        })

    if services.get("rds"):
        findings.append({
            "severity": WARNING,
            "category": "security",
            "message": "Verify RDS encryption at rest is enabled",
            "recommendation": "Set storage_encrypted = true on all RDS instances",
        })

    if services.get("lambda"):
        findings.append({
            "severity": INFO,
            "category": "security",
            "message": "Lambda functions detected",
            "recommendation": "Ensure Lambda functions run inside VPC for sensitive workloads, use environment variable encryption",
        })

    if "aws_iam_user" in detected_resources:
        findings.append({
            "severity": WARNING,
            "category": "security",
            "message": "IAM users created in Terraform -- prefer IAM roles with federation",
            "recommendation": "Use IAM Identity Center (SSO) with federated roles instead of IAM users",
        })

    if services.get("s3") and "aws_s3_bucket_public_access_block" not in detected_resources:
        findings.append({
            "severity": CRITICAL,
            "category": "security",
            "message": "S3 buckets without public access block",
            "recommendation": "Add aws_s3_bucket_public_access_block to all buckets",
        })

    return findings


def review_aws_infrastructure(terraform_result: Dict, repo_analysis: Dict) -> Dict:
    """Provide AWS-focused cost and security advice.

    Args:
        terraform_result: output from review_terraform()
        repo_analysis: output from analyze_repo()

    Returns:
        Dict with cost_findings, security_findings, maturity_level, summary
    """
    detected_resources = terraform_result.get("detected_resources", [])
    terraform_findings = terraform_result.get("detailed_findings", [])

    cost_findings = _cost_checks(detected_resources, terraform_findings)
    security_findings = _security_checks(detected_resources, terraform_findings)

    all_findings = cost_findings + security_findings
    services = _detect_aws_services(detected_resources)
    active_services = [svc for svc, active in services.items() if active]

    critical = [f for f in all_findings if f["severity"] == CRITICAL]
    warnings = [f for f in all_findings if f["severity"] == WARNING]
    info_items = [f for f in all_findings if f["severity"] == INFO]

    maturity = "basic"
    if len(critical) == 0 and len(warnings) <= 2:
        maturity = "developing"
    if len(critical) == 0 and len(warnings) == 0:
        maturity = "production-leaning"

    risks = [f["message"] for f in critical + warnings]
    improvements = list(dict.fromkeys(f["recommendation"] for f in all_findings))

    return {
        "aws_services_detected": active_services,
        "maturity_level": maturity,
        "cost_findings": cost_findings,
        "security_findings": security_findings,
        "risks": risks,
        "recommended_improvements": improvements,
        "severity_summary": {
            "critical": len(critical),
            "warning": len(warnings),
            "info": len(info_items),
        },
    }
