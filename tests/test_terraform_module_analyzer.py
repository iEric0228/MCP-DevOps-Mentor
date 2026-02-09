import pytest
from reviewers.terraform_module_analyzer import (
    analyze_terraform_modules,
    _check_module_sources,
    _check_module_required_variables,
    _check_variable_usage,
    _check_output_references,
    _check_sensitive_variables,
    _check_sensitive_outputs,
    _check_tfvars_secrets,
    _check_untrusted_module_sources,
    _generate_cost_summary,
)
from reviewers.terraform_reviewer import _parse_tf_content


# ---------------------------------------------------------------------------
# Module Source Validation
# ---------------------------------------------------------------------------


def test_module_missing_source():
    files = {"main.tf": 'module "vpc" {\n}\n'}
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_module_sources(parsed, list(files.keys()))
    assert any("no source" in f["message"] for f in findings)
    assert all(f["severity"] == "critical" for f in findings if "no source" in f["message"])


def test_module_local_path_not_found():
    files = {
        "main.tf": '''
module "vpc" {
  source = "./modules/vpc"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_module_sources(parsed, list(files.keys()))
    assert any("no .tf files found" in f["message"] for f in findings)


def test_module_local_path_found():
    files = {
        "main.tf": '''
module "vpc" {
  source = "./modules/vpc"
}
''',
        "modules/vpc/main.tf": 'resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n',
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_module_sources(parsed, list(files.keys()))
    path_findings = [f for f in findings if "no .tf files found" in f["message"]]
    assert len(path_findings) == 0


def test_module_untrusted_source():
    files = {
        "main.tf": '''
module "shady" {
  source = "some-random-registry.io/org/module"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_module_sources(parsed, list(files.keys()))
    assert any("untrusted" in f["message"] for f in findings)


# ---------------------------------------------------------------------------
# Module Required Variables
# ---------------------------------------------------------------------------


def test_module_missing_required_variable():
    files = {
        "main.tf": '''
module "db" {
  source = "./modules/db"
  engine = "postgres"
}
''',
        "modules/db/variables.tf": '''
variable "engine" {
  type = string
}
variable "instance_class" {
  type = string
}
''',
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_module_required_variables(parsed)
    assert any("instance_class" in f["message"] for f in findings)
    assert all(f["severity"] == "critical" for f in findings if "instance_class" in f["message"])


def test_module_all_required_variables_passed():
    files = {
        "main.tf": '''
module "db" {
  source         = "./modules/db"
  engine         = "postgres"
  instance_class = "db.t3.micro"
}
''',
        "modules/db/variables.tf": '''
variable "engine" {
  type = string
}
variable "instance_class" {
  type = string
}
''',
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_module_required_variables(parsed)
    assert len(findings) == 0


def test_module_variable_with_default_not_required():
    files = {
        "main.tf": '''
module "db" {
  source = "./modules/db"
  engine = "postgres"
}
''',
        "modules/db/variables.tf": '''
variable "engine" {
  type = string
}
variable "instance_class" {
  type    = string
  default = "db.t3.micro"
}
''',
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_module_required_variables(parsed)
    # instance_class has a default, so it should not be flagged
    assert not any("instance_class" in f["message"] for f in findings)


# ---------------------------------------------------------------------------
# Variable Usage Cross-Validation
# ---------------------------------------------------------------------------


def test_unused_variable_detected():
    files = {
        "variables.tf": '''
variable "region" {
  type = string
}
variable "unused_var" {
  type = string
}
''',
        "main.tf": '''
provider "aws" {
  region = var.region
}
''',
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_variable_usage(parsed, files)
    assert any(
        "unused_var" in f["message"] and "never referenced" in f["message"]
        for f in findings
    )


def test_undeclared_variable_detected():
    files = {
        "main.tf": '''
resource "aws_instance" "web" {
  ami           = var.ami_id
  instance_type = var.instance_type
}
''',
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_variable_usage(parsed, files)
    assert any("ami_id" in f["message"] and "never declared" in f["message"] for f in findings)
    assert any(
        "instance_type" in f["message"] and "never declared" in f["message"]
        for f in findings
    )


def test_all_variables_used_and_declared():
    files = {
        "variables.tf": '''
variable "ami_id" {
  type = string
}
''',
        "main.tf": '''
resource "aws_instance" "web" {
  ami = var.ami_id
}
''',
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_variable_usage(parsed, files)
    assert len(findings) == 0


# ---------------------------------------------------------------------------
# Output Reference Validation
# ---------------------------------------------------------------------------


def test_output_referencing_nonexistent_resource():
    files = {
        "outputs.tf": '''
output "web_ip" {
  value = aws_instance.web.public_ip
}
''',
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_output_references(parsed)
    assert any("aws_instance.web" in f["message"] for f in findings)


def test_output_referencing_existing_resource():
    files = {
        "main.tf": '''
resource "aws_instance" "web" {
  ami           = "ami-123"
  instance_type = "t3.micro"
}
''',
        "outputs.tf": '''
output "web_ip" {
  value = aws_instance.web.public_ip
}
''',
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_output_references(parsed)
    ref_findings = [f for f in findings if "aws_instance.web" in f["message"]]
    assert len(ref_findings) == 0


def test_output_referencing_nonexistent_module():
    files = {
        "outputs.tf": '''
output "vpc_id" {
  value = module.ghost_vpc.vpc_id
}
''',
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_output_references(parsed)
    assert any("module.ghost_vpc" in f["message"] for f in findings)


# ---------------------------------------------------------------------------
# Sensitive Variable Checks
# ---------------------------------------------------------------------------


def test_sensitive_var_missing_flag():
    files = {
        "variables.tf": '''
variable "db_password" {
  type = string
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_sensitive_variables(parsed)
    assert len(findings) >= 1
    assert findings[0]["severity"] == "critical"
    assert "sensitive = true" in findings[0]["message"]


def test_sensitive_var_with_flag():
    files = {
        "variables.tf": '''
variable "db_password" {
  type      = string
  sensitive = true
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_sensitive_variables(parsed)
    # Should not flag missing sensitive = true
    assert not any("lacks sensitive = true" in f["message"] for f in findings)


def test_sensitive_var_hardcoded_default():
    files = {
        "variables.tf": '''
variable "api_key" {
  type      = string
  sensitive = true
  default   = "sk-12345abc"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_sensitive_variables(parsed)
    assert any("hardcoded default" in f["message"] for f in findings)


def test_non_sensitive_var_not_flagged():
    files = {
        "variables.tf": '''
variable "region" {
  type    = string
  default = "us-east-1"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_sensitive_variables(parsed)
    assert len(findings) == 0


# ---------------------------------------------------------------------------
# Sensitive Output Checks
# ---------------------------------------------------------------------------


def test_sensitive_output_not_marked():
    files = {
        "outputs.tf": '''
output "db_password" {
  value = var.db_password
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_sensitive_outputs(parsed)
    assert len(findings) >= 1
    assert findings[0]["severity"] == "critical"


def test_sensitive_output_properly_marked():
    files = {
        "outputs.tf": '''
output "db_password" {
  value     = var.db_password
  sensitive = true
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_sensitive_outputs(parsed)
    assert len(findings) == 0


def test_non_sensitive_output_not_flagged():
    files = {
        "outputs.tf": '''
output "instance_id" {
  value = aws_instance.web.id
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_sensitive_outputs(parsed)
    assert len(findings) == 0


# ---------------------------------------------------------------------------
# .tfvars Secret Scanning
# ---------------------------------------------------------------------------


def test_tfvars_secret_detected():
    files = {
        "prod.tfvars": 'db_password = "super-secret-123"\nregion = "us-east-1"',
    }
    findings = _check_tfvars_secrets(files)
    assert len(findings) >= 1
    assert findings[0]["severity"] == "critical"


def test_tfvars_aws_key_detected():
    files = {
        "prod.tfvars": 'access_key = "AKIAIOSFODNN7EXAMPLE"',
    }
    findings = _check_tfvars_secrets(files)
    assert len(findings) >= 1


def test_tfvars_no_false_positive():
    files = {
        "prod.tfvars": 'region = "us-east-1"\ninstance_type = "t3.micro"',
    }
    findings = _check_tfvars_secrets(files)
    assert len(findings) == 0


def test_tf_file_not_scanned_as_tfvars():
    files = {
        "main.tf": 'password = "secret-123"',
    }
    findings = _check_tfvars_secrets(files)
    assert len(findings) == 0  # Only .tfvars files are scanned


# ---------------------------------------------------------------------------
# Module Version Pinning
# ---------------------------------------------------------------------------


def test_git_module_no_version():
    files = {
        "main.tf": '''
module "vpc" {
  source = "git::https://github.com/org/terraform-vpc.git"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_untrusted_module_sources(parsed)
    assert any("version pinning" in f["message"] for f in findings)


def test_git_module_with_ref():
    files = {
        "main.tf": '''
module "vpc" {
  source = "git::https://github.com/org/terraform-vpc.git?ref=v1.0.0"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_untrusted_module_sources(parsed)
    version_findings = [f for f in findings if "version pinning" in f["message"]]
    assert len(version_findings) == 0


def test_registry_module_no_version():
    files = {
        "main.tf": '''
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_untrusted_module_sources(parsed)
    assert any("no version constraint" in f["message"] for f in findings)


def test_registry_module_with_version():
    files = {
        "main.tf": '''
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    findings = _check_untrusted_module_sources(parsed)
    version_findings = [f for f in findings if "no version constraint" in f["message"]]
    assert len(version_findings) == 0


# ---------------------------------------------------------------------------
# Cost Summary
# ---------------------------------------------------------------------------


def test_cost_summary_detects_expensive_resources():
    files = {
        "main.tf": '''
resource "aws_nat_gateway" "main" {
  allocation_id = "eip-123"
  subnet_id     = "subnet-123"
}
resource "aws_eks_cluster" "main" {
  name = "my-cluster"
}
resource "aws_s3_bucket" "data" {
  bucket = "my-bucket"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    cost = _generate_cost_summary(parsed)
    assert cost["tier_summary"]["high"] >= 1
    assert cost["tier_summary"]["very_high"] >= 1
    assert len(cost["cost_findings"]) >= 2


def test_cost_summary_low_cost_only():
    files = {
        "main.tf": '''
resource "aws_s3_bucket" "data" {
  bucket = "my-bucket"
}
resource "aws_sqs_queue" "main" {
  name = "my-queue"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    cost = _generate_cost_summary(parsed)
    assert cost["tier_summary"]["high"] == 0
    assert cost["tier_summary"]["very_high"] == 0
    assert len(cost["cost_findings"]) == 0


def test_cost_summary_total_estimate():
    files = {
        "main.tf": '''
resource "aws_nat_gateway" "main" {
  allocation_id = "eip-123"
  subnet_id     = "subnet-123"
}
'''
    }
    parsed = {k: v for k, v in ((k, _parse_tf_content(v)) for k, v in files.items()) if v}
    cost = _generate_cost_summary(parsed)
    assert cost["estimated_monthly_total_usd"].startswith("$")
    assert len(cost["resource_costs"]) >= 1
    assert cost["resource_costs"][0]["cost_tier"] == "high"


# ---------------------------------------------------------------------------
# Integration Tests — Public Entry Point
# ---------------------------------------------------------------------------


def test_full_analysis_output_structure():
    files = {
        "main.tf": '''
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
}
resource "aws_instance" "web" {
  ami           = var.ami_id
  instance_type = "t3.micro"
}
''',
        "variables.tf": '''
variable "ami_id" {
  type = string
}
variable "db_password" {
  type = string
}
''',
        "outputs.tf": '''
output "instance_id" {
  value = aws_instance.web.id
}
''',
    }
    result = analyze_terraform_modules(files)
    assert result["analysis_type"] == "terraform-module-analysis"
    assert "maturity_level" in result
    assert "module_findings" in result
    assert "security_findings" in result
    assert "cost_summary" in result
    assert "risks" in result
    assert "recommended_improvements" in result
    assert "detailed_findings" in result
    assert "severity_summary" in result
    assert "critical" in result["severity_summary"]
    assert "warning" in result["severity_summary"]
    assert "info" in result["severity_summary"]
    assert "resource_costs" in result["cost_summary"]
    assert "tier_summary" in result["cost_summary"]
    assert "estimated_monthly_total_usd" in result["cost_summary"]


def test_empty_files():
    result = analyze_terraform_modules({})
    assert result["files_analyzed"] == []
    assert result["maturity_level"] == "production-leaning"
    assert result["severity_summary"]["critical"] == 0


def test_maturity_level_basic_with_critical():
    files = {
        "main.tf": '''
variable "password" {
  type    = string
  default = "hardcoded123"
}
''',
    }
    result = analyze_terraform_modules(files)
    assert result["maturity_level"] == "basic"


def test_parse_failure_graceful():
    files = {"broken.tf": "this is {{{{ not valid hcl"}
    result = analyze_terraform_modules(files)
    assert "broken.tf" in result["files_analyzed"]
    assert any("could not parse" in f for f in result["findings"])


def test_fixture_secure_modules(sample_terraform_with_modules):
    result = analyze_terraform_modules(sample_terraform_with_modules)
    assert result["analysis_type"] == "terraform-module-analysis"
    # Should find db_password missing sensitive = true
    assert any("db_password" in f["message"] for f in result["security_findings"])


def test_fixture_insecure_modules(sample_terraform_modules_insecure):
    result = analyze_terraform_modules(sample_terraform_modules_insecure)
    assert result["maturity_level"] == "basic"
    # Should find multiple issues: tfvars secret, api_key sensitive, git unpinned
    assert result["severity_summary"]["critical"] >= 1
    assert len(result["risks"]) >= 1
    # Should detect cost of nat_gateway and db_instance
    assert result["cost_summary"]["tier_summary"]["high"] >= 1
