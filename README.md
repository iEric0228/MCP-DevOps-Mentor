# MCP DevOps Mentor

A Dockerized MCP (Model Context Protocol) server that acts as a senior DevOps and Cloud engineering mentor. It reviews GitHub repositories, analyzes CI/CD pipelines, audits Terraform infrastructure, advises on AWS cost and security, and tracks your skill progression over time.

Built to teach **how to think like a DevOps engineer**, not just what to do.

## Architecture

```
MCP Client (IDE / Claude)
        |
        | MCP Protocol
        v
+-------------------------------+
|   MCP DevOps Mentor Server    |
|                               |
|   Mentor Brain                |
|   - System Prompt + Modes     |
|                               |
|   Repo Analyzer               |
|   - Tech Stack Detection      |
|   - DevOps Maturity Scoring   |
|                               |
|   CI/CD Review Engine         |
|   - GitHub Actions (YAML)     |
|   - Security + Best Practices |
|                               |
|   Terraform Review Engine     |
|   - HCL2 Parsing              |
|   - Security + State Mgmt     |
|                               |
|   AWS Advisor                 |
|   - Cost Optimization         |
|   - Security Posture          |
|                               |
|   Prompt Enhancer             |
|   - Domain Detection          |
|   - Dimension Injection       |
|   - Skill-Aware Adaptation    |
|                               |
|   Skill Tracker               |
|   - Weighted Scoring          |
|   - Learning Path Engine      |
|   - SQLite Persistence        |
+-------------------------------+
        |
     Docker
```

## Features

### 11 MCP Tools

| Tool | Description |
|------|-------------|
| `set_review_mode` | Switch between mentor, review, debug, and interview modes |
| `analyze_github_repo` | Analyze a repo for tech stack and DevOps maturity |
| `review_cicd_pipeline` | Review GitHub Actions workflows with YAML parsing |
| `review_terraform` | Audit Terraform files for security, state management, and best practices |
| `review_aws_infrastructure` | AWS cost optimization and security posture analysis |
| `analyze_terraform_modules` | Analyze Terraform modules for structure, security, and cost estimation |
| `enhance_prompt` | Improve raw DevOps prompts with structure, context, and best-practice considerations |
| `get_skill_profile` | View your current skill levels and evidence counts |
| `get_learning_path` | Get a personalized learning roadmap based on skill gaps |
| `read_github_file` | Read a single file from a GitHub repository |
| `read_github_workflows` | Read all GitHub Actions workflow files |
| `read_terraform_files` | Read all Terraform files from a repository |

### Review Modes

- **Mentor** -- Teaching mode. Explains concepts, asks guiding questions, assumes junior level.
- **Review** -- PR-style review. Direct, production-focused, flags risks.
- **Debug** -- Troubleshooting mode. Forms hypotheses, narrows scope, asks for logs.
- **Interview** -- Challenge mode. Questions your design decisions, exposes tradeoffs.

### CI/CD Review Engine

Parses GitHub Actions YAML and checks for:

- Missing `permissions` block (least-privilege)
- Action pinning (SHA vs tag references)
- Job timeouts
- Dependency caching
- AWS OIDC vs long-lived credentials
- Terraform apply without environment guards
- Self-hosted runner security
- Matrix strategy `fail-fast` settings
- Concurrency groups
- Workflow dispatch input validation

### Terraform Review Engine

Parses HCL2 with `python-hcl2` and checks for:

- Hardcoded credentials and AWS access keys
- Missing remote backend (local state risk)
- S3 backend without DynamoDB state locking
- Missing provider version constraints
- Resources without tags
- Overly permissive security groups (0.0.0.0/0)
- S3 buckets without encryption or versioning
- IAM policies with wildcard actions
- Missing lifecycle rules on stateful resources

### AWS Cost + Security Advisor

Analyzes detected Terraform resources and recommends:

**Cost:**
- NAT Gateway alternatives for dev/staging
- Auto Scaling for EC2 instances
- Spot instances for fault-tolerant workloads
- EIP audit
- RDS Reserved Instances / Aurora Serverless
- Fargate Spot / Karpenter for containers

**Security:**
- CloudTrail for API audit logging
- VPC Flow Logs
- S3 public access blocks
- IAM roles over IAM users
- RDS encryption at rest
- Lambda VPC placement

### Prompt Enhancer

Inspired by [Claude's Prompt Improver](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompt-improver), the prompt enhancer automatically improves raw DevOps prompts through a **6-stage deterministic pipeline** (no LLM API calls -- pure template logic):

| Stage | What it Does |
|-------|-------------|
| 1. Domain Detection | Keyword-matches against 8 DevOps domains (CI/CD, Docker, Terraform, AWS, Security, Observability, Networking, Cost) |
| 2. Dimension Injection | Checks if key considerations (security, cost, rollback, scalability, etc.) are already in the prompt -- injects missing ones |
| 3. Cloud Provider Context | Detects or defaults to AWS, prepends provider-specific context |
| 4. Skill-Level Adaptation | Reads your tracked skill profile and adapts tone/detail (beginner=detailed, advanced=concise) |
| 5. Mode-Aware Structuring | Applies the active review mode template (mentor/review/debug/interview) |
| 6. XML Assembly | Wraps everything in structured XML tags (`<context>`, `<task>`, `<thinking>`, `<output_format>`) |

**Parameters:**

```
enhance_prompt(
    prompt="Set up a CI/CD pipeline for my Python app",
    mode="mentor",           # optional, defaults to current mode
    cloud_provider="aws",    # optional, auto-detected or defaults to AWS
    focus_areas="security"   # optional, comma-separated dimension filter
)
```

**Example output structure:**

```xml
<context>
Cloud provider context: AWS. ...
Domains: ci_cd
User experience level: beginner
Response detail: detailed
</context>

<instructions>
You are helping a DevOps learner understand and implement the following. ...
</instructions>

<task>
Set up a CI/CD pipeline for my Python app
</task>

<additional_considerations>
- Consider security implications: action pinning, least-privilege permissions...
- Include a rollback strategy: how to revert a failed deployment safely.
- Address build performance: dependency caching, artifact reuse...
- Include testing requirements: what tests to run, coverage thresholds...
</additional_considerations>

<thinking>
Think through this step by step, explaining your reasoning at each stage.
</thinking>

<output_format>
Structure your response as:
1. Conceptual explanation (the WHY)
2. Implementation approach (the HOW)
3. Common pitfalls to avoid
4. Next steps for learning
</output_format>
```

### Skill Tracking

Tracks 7 skill domains with weighted keyword scoring:

| Domain | Example Keywords |
|--------|-----------------|
| CI/CD | github actions, pipeline, workflow, deploy |
| Docker | dockerfile, docker-compose, container, multi-stage |
| Terraform | terraform, hcl, tfstate, remote backend |
| AWS | iam, s3, ec2, eks, security group, vpc |
| Security | secrets, oidc, rbac, encryption, least-privilege |
| Observability | prometheus, grafana, cloudwatch, tracing |
| Testing | pytest, jest, coverage, integration test, e2e |

**5-level progression:** unknown -> beginner -> developing -> solid -> advanced

Levels are based on accumulated weighted scores with maturity multipliers. The learning path engine identifies weak areas, finds prerequisite gaps (e.g., "security" depends on "aws"), and generates actionable next steps.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- A GitHub personal access token (read-only scope is sufficient)

### Run with Docker

```bash
export GITHUB_TOKEN=ghp_your_token_here
docker-compose up --build
```

The server starts on `http://localhost:3333`.

### Run Locally (Development)

```bash
pip install -r requirements.txt
export GITHUB_TOKEN=ghp_your_token_here
uvicorn main:app --host 0.0.0.0 --port 3333
```

### Run Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Project Structure

```
MCP-DevOps-Mentor/
  main.py                           # FastAPI + MCP server, tool registration
  requirements.txt                  # Dependencies
  Dockerfile                        # Python 3.11-slim container
  docker-compose.yml                # Single-service deployment
  analyzer/
    repo_analyzer.py                # Tech stack detection and maturity scoring
  reviewers/
    cicd_reviewer.py                # GitHub Actions review (YAML parsing)
    terraform_reviewer.py           # Terraform review (HCL2 parsing)
    aws_advisor.py                  # AWS cost + security advisor
  tools/
    github.py                       # GitHub REST API integration
  enhancer/
    prompt_enhancer.py              # 6-stage prompt enhancement pipeline
    domain_rules.py                 # Domain keywords, dimension injections, templates
    skill_adapter.py                # Skill-level to enhancement behavior bridge
  memory/
    models.py                       # SkillState, UserProfile dataclasses
    store.py                        # SQLite persistence
    tracker.py                      # Weighted skill tracking + learning path
  mentor/
    system_prompt.txt               # Base mentor persona
    mode_loader.py                  # Dynamic prompt composition
    modes/
      mentor.txt                    # Teaching mode prompt
      review.txt                    # PR review mode prompt
      debug.txt                     # Troubleshooting mode prompt
      interview.txt                 # Challenge mode prompt
  tests/
    conftest.py                     # Shared fixtures (tmp_db, sample data)
    test_repo_analyzer.py           # 10 tests
    test_cicd_reviewer.py           # 15 tests
    test_terraform_reviewer.py      # 15 tests
    test_aws_advisor.py             # 11 tests
    test_tracker.py                 # 17 tests
    test_store.py                   # 5 tests
    test_mode_loader.py             # 8 tests
    test_prompt_enhancer.py         # 38 tests
    test_domain_rules.py            # 10 tests
    test_skill_adapter.py           # 10 tests
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| Framework | FastAPI |
| Protocol | MCP (Model Context Protocol) |
| CI/CD Parsing | PyYAML |
| Terraform Parsing | python-hcl2 |
| Persistence | SQLite |
| Testing | pytest (182 tests) |
| Containerization | Docker |
| External API | GitHub REST API v3 |

## Example Usage

Once connected via an MCP client:

```
> "Analyze my repo and tell me its DevOps maturity."

> "Switch to review mode and review my CI/CD pipeline."

> "Review the Terraform files in my infrastructure repo."

> "What are my weakest DevOps skills? Give me a learning path."

> "Switch to interview mode. Challenge my system design."

> "Enhance my prompt: Set up a CI/CD pipeline for my Python app"

> "Enhance this prompt with a focus on security: Deploy containers to ECS with Terraform"
```

## Design Decisions

**Signal-based heuristics, not magic.** Analysis uses structured parsing (YAML, HCL2) with deterministic check functions. Every finding has a severity level, a message, and a recommendation.

**Severity-driven output.** All reviewers categorize findings as `critical`, `warning`, or `info`. Maturity levels are derived from severity counts, not arbitrary rules.

**Weighted skill tracking.** Domain-specific keywords score higher than generic ones. A maturity multiplier rewards engagement with production-grade repositories. Skills progress through evidence accumulation, not one-off matches.

**Backward-compatible persistence.** New SkillState fields (`weighted_score`, `history`) have defaults. Old database records load without migration.

**Thin orchestration, deep modules.** Tool functions in `main.py` are 5-10 line wrappers. All analysis logic lives in dedicated modules that are independently testable.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub personal access token for API access |

## Security

- Read-only GitHub API access (no write operations)
- No credentials stored in code or database
- Terraform reviewer detects hardcoded secrets in user code
- All data stays local (SQLite file, no external telemetry)


