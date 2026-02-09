import pytest
from reviewers.terraform_reviewer import review_terraform, _check_hardcoded_secrets


def test_hardcoded_secret_detection():
    content = 'password = "my-secret-123"'
    findings = _check_hardcoded_secrets(content, "main.tf")
    assert len(findings) >= 1
    assert findings[0]["severity"] == "critical"


def test_aws_key_detection():
    content = 'access_key = "AKIAIOSFODNN7EXAMPLE"'
    findings = _check_hardcoded_secrets(content, "main.tf")
    assert len(findings) >= 1


def test_no_false_positive_on_variable_ref():
    content = 'password = "${var.db_password}"'
    findings = _check_hardcoded_secrets(content, "main.tf")
    assert len(findings) == 0


def test_secure_terraform(sample_terraform_secure):
    result = review_terraform(sample_terraform_secure)
    assert result["iac_type"] == "terraform"
    assert "main.tf" in result["files_reviewed"]
    assert result["severity_summary"]["critical"] == 0


def test_insecure_security_group(sample_terraform_insecure):
    result = review_terraform(sample_terraform_insecure)
    assert any("0.0.0.0/0" in r for r in result["risks"])


def test_s3_missing_encryption(sample_terraform_insecure):
    result = review_terraform(sample_terraform_insecure)
    assert any("encryption" in r.lower() for r in result["risks"])


def test_s3_missing_versioning(sample_terraform_insecure):
    result = review_terraform(sample_terraform_insecure)
    assert any("versioning" in r.lower() for r in result["risks"])


def test_iam_wildcard_detection(sample_terraform_insecure):
    result = review_terraform(sample_terraform_insecure)
    assert any("wildcard" in r.lower() or "IAM" in r for r in result["risks"])


def test_missing_backend():
    files = {
        "main.tf": '''
resource "aws_instance" "web" {
  ami           = "ami-123"
  instance_type = "t3.micro"
}
'''
    }
    result = review_terraform(files)
    assert any("backend" in r.lower() for r in result["risks"])


def test_detected_resources(sample_terraform_insecure):
    result = review_terraform(sample_terraform_insecure)
    assert "aws_security_group" in result["detected_resources"]
    assert "aws_s3_bucket" in result["detected_resources"]


def test_maturity_assessment(sample_terraform_secure):
    result = review_terraform(sample_terraform_secure)
    # Secure terraform should be developing or better
    assert result["maturity_level"] in ("developing", "production-leaning")


def test_severity_summary_present(sample_terraform_insecure):
    result = review_terraform(sample_terraform_insecure)
    assert "severity_summary" in result
    assert "critical" in result["severity_summary"]
    assert "warning" in result["severity_summary"]
    assert "info" in result["severity_summary"]


def test_empty_tf_files():
    result = review_terraform({})
    assert result["files_reviewed"] == []
    assert result["maturity_level"] == "production-leaning"


def test_non_tf_files_ignored():
    files = {
        "readme.md": "# Hello",
        "main.tf": '''
resource "aws_instance" "web" {
  ami           = "ami-123"
  instance_type = "t3.micro"
}
''',
    }
    result = review_terraform(files)
    assert "readme.md" not in result["files_reviewed"]
    assert "main.tf" in result["files_reviewed"]


def test_fallback_on_parse_failure():
    files = {
        "broken.tf": "this is not valid { hcl content }{{{",
    }
    result = review_terraform(files)
    # Should still run without crashing
    assert "broken.tf" in result["files_reviewed"]
