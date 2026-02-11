import pytest


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_mentor.db")
    monkeypatch.setattr("memory.store.DB_PATH", db_path)
    from memory.store import init_db
    init_db()
    return db_path


@pytest.fixture
def sample_workflow_secure():
    return {
        "ci.yml": """
name: CI
on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r requirements.txt
      - run: pytest
"""
    }


@pytest.fixture
def sample_workflow_insecure():
    return {
        "deploy.yml": """
name: Deploy
on: push

jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_KEY }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET }}
          aws-region: us-east-1
      - run: terraform apply -auto-approve
"""
    }


@pytest.fixture
def sample_terraform_secure():
    return {
        "main.tf": '''
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "my-tf-state"
    key            = "state/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "tf-locks"
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  tags = {
    Name        = "web-server"
    Environment = "production"
  }

  lifecycle {
    prevent_destroy = true
  }
}
'''
    }


@pytest.fixture
def sample_terraform_insecure():
    return {
        "bad.tf": '''
resource "aws_security_group" "open" {
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
}

resource "aws_iam_policy" "admin" {
  policy = jsonencode({
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}
'''
    }


@pytest.fixture
def sample_file_list_full():
    return [
        "README.md",
        "Dockerfile",
        "docker-compose.yml",
        "requirements.txt",
        "main.py",
        ".github/workflows/ci.yml",
        "terraform/main.tf",
        "terraform/variables.tf",
    ]


@pytest.fixture
def sample_file_list_minimal():
    return [
        "README.md",
        "main.py",
        "requirements.txt",
    ]


@pytest.fixture
def sample_terraform_with_modules():
    return {
        "main.tf": '''
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  cidr    = var.vpc_cidr
}

resource "aws_instance" "web" {
  ami           = var.ami_id
  instance_type = "t3.micro"
  subnet_id     = module.vpc.public_subnets[0]
  tags = {
    Name = "web-server"
  }
}
''',
        "variables.tf": '''
variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

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

output "vpc_id" {
  value = module.vpc.vpc_id
}
''',
    }


@pytest.fixture
def sample_terraform_modules_insecure():
    return {
        "main.tf": '''
module "custom" {
  source = "git::https://github.com/random-org/module.git"
}

resource "aws_nat_gateway" "main" {
  allocation_id = "eip-123"
  subnet_id     = "subnet-123"
}

resource "aws_db_instance" "main" {
  engine         = "postgres"
  instance_class = "db.r5.2xlarge"
}
''',
        "variables.tf": '''
variable "api_key" {
  type    = string
  default = "sk-test-12345"
}
''',
        "outputs.tf": '''
output "api_key" {
  value = var.api_key
}
''',
        "prod.tfvars": 'db_password = "real-secret-password"',
    }


@pytest.fixture
def sample_raw_prompt_cicd():
    return "Set up a CI/CD pipeline for my Python app"


@pytest.fixture
def sample_raw_prompt_terraform():
    return "Create a Terraform module for a VPC with public and private subnets"


@pytest.fixture
def sample_raw_prompt_comprehensive():
    return (
        "Set up a CI/CD pipeline that deploys Docker containers to ECS "
        "with Terraform, including security scanning and cost monitoring"
    )
