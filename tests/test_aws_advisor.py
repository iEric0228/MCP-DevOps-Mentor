from reviewers.aws_advisor import review_aws_infrastructure, _detect_aws_services


def test_service_detection():
    resources = ["aws_instance", "aws_s3_bucket", "aws_lambda_function"]
    services = _detect_aws_services(resources)
    assert services["ec2"] is True
    assert services["s3"] is True
    assert services["lambda"] is True
    assert services["rds"] is False


def test_nat_gateway_cost_warning():
    terraform_result = {
        "detected_resources": ["aws_vpc", "aws_nat_gateway", "aws_instance"],
        "detailed_findings": [],
    }
    repo_analysis = {"stack": ["python"], "maturity_level": "developing"}
    result = review_aws_infrastructure(terraform_result, repo_analysis)
    assert any("NAT Gateway" in f["message"] for f in result["cost_findings"])


def test_missing_auto_scaling():
    terraform_result = {
        "detected_resources": ["aws_instance"],
        "detailed_findings": [],
    }
    repo_analysis = {"stack": ["python"], "maturity_level": "developing"}
    result = review_aws_infrastructure(terraform_result, repo_analysis)
    assert any("Auto Scaling" in f["message"] for f in result["cost_findings"])


def test_missing_cloudtrail():
    terraform_result = {
        "detected_resources": ["aws_instance"],
        "detailed_findings": [],
    }
    repo_analysis = {"stack": [], "maturity_level": "early"}
    result = review_aws_infrastructure(terraform_result, repo_analysis)
    assert any("CloudTrail" in f["message"] for f in result["security_findings"])


def test_missing_vpc_flow_logs():
    terraform_result = {
        "detected_resources": ["aws_vpc", "aws_subnet"],
        "detailed_findings": [],
    }
    repo_analysis = {"stack": [], "maturity_level": "early"}
    result = review_aws_infrastructure(terraform_result, repo_analysis)
    assert any("flow log" in f["message"].lower() for f in result["security_findings"])


def test_s3_without_public_access_block():
    terraform_result = {
        "detected_resources": ["aws_s3_bucket"],
        "detailed_findings": [],
    }
    repo_analysis = {"stack": [], "maturity_level": "early"}
    result = review_aws_infrastructure(terraform_result, repo_analysis)
    assert any("public access block" in f["message"].lower() for f in result["security_findings"])


def test_iam_user_warning():
    terraform_result = {
        "detected_resources": ["aws_iam_user", "aws_iam_role"],
        "detailed_findings": [],
    }
    repo_analysis = {"stack": [], "maturity_level": "early"}
    result = review_aws_infrastructure(terraform_result, repo_analysis)
    assert any("IAM users" in f["message"] for f in result["security_findings"])


def test_maturity_assessment():
    terraform_result = {
        "detected_resources": ["aws_cloudtrail", "aws_s3_bucket", "aws_s3_bucket_public_access_block"],
        "detailed_findings": [],
    }
    repo_analysis = {"stack": [], "maturity_level": "developing"}
    result = review_aws_infrastructure(terraform_result, repo_analysis)
    assert result["maturity_level"] in ("developing", "production-leaning")


def test_empty_resources():
    terraform_result = {
        "detected_resources": [],
        "detailed_findings": [],
    }
    repo_analysis = {"stack": [], "maturity_level": "early"}
    result = review_aws_infrastructure(terraform_result, repo_analysis)
    assert result["aws_services_detected"] == []
    # Should still have CloudTrail finding
    assert any("CloudTrail" in f["message"] for f in result["security_findings"])


def test_output_structure():
    terraform_result = {
        "detected_resources": ["aws_instance"],
        "detailed_findings": [],
    }
    repo_analysis = {"stack": [], "maturity_level": "early"}
    result = review_aws_infrastructure(terraform_result, repo_analysis)
    assert "aws_services_detected" in result
    assert "maturity_level" in result
    assert "cost_findings" in result
    assert "security_findings" in result
    assert "risks" in result
    assert "recommended_improvements" in result
    assert "severity_summary" in result


def test_container_orchestration_advice():
    terraform_result = {
        "detected_resources": ["aws_ecs_cluster", "aws_ecs_service", "aws_cloudtrail"],
        "detailed_findings": [],
    }
    repo_analysis = {"stack": [], "maturity_level": "developing"}
    result = review_aws_infrastructure(terraform_result, repo_analysis)
    assert any("Container" in f["message"] or "Fargate" in f.get("recommendation", "") for f in result["cost_findings"])
