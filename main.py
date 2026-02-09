from fastapi import FastAPI
from mcp.server.fastapi import MCPServer
from mcp.server import tool
from pathlib import Path

from mentor.mode_loader import get_system_prompt, load_mode_prompt
from analyzer.repo_analyzer import analyze_repo
from reviewers.cicd_reviewer import review_github_actions
from reviewers.terraform_reviewer import review_terraform
from reviewers.aws_advisor import review_aws_infrastructure
from tools.github import (
    list_repo_files,
    read_github_file,
    read_github_workflows,
    read_terraform_files,
)
from memory.tracker import update_skills, get_learning_recommendations

app = FastAPI()

CURRENT_MODE = "mentor"


@tool(
    name="set_review_mode",
    description="Set the review mode: mentor, review, debug, interview",
)
def set_review_mode(mode: str):
    global CURRENT_MODE
    if mode not in ["mentor", "review", "debug", "interview"]:
        return "Invalid mode. Choose from: mentor, review, debug, interview"

    CURRENT_MODE = mode
    return f"Review mode set to '{mode}'"


@tool(
    name="analyze_github_repo",
    description="Analyze a GitHub repository for tech stack and DevOps maturity",
)
def analyze_github_repo(owner: str, repo: str):
    files = list_repo_files(owner, repo)
    if isinstance(files, str):
        return files

    result = analyze_repo(files)
    update_skills(
        str(result.get("key_findings", [])), result.get("maturity_level", "early")
    )
    return result


@tool(
    name="review_cicd_pipeline",
    description="Review GitHub Actions CI/CD workflows for a repository",
)
def review_cicd_pipeline(owner: str, repo: str):
    workflows = read_github_workflows(owner, repo)
    if not workflows:
        return {"error": "No workflow files found or failed to read workflows."}

    result = review_github_actions(workflows)
    update_skills(str(result.get("risks", [])), result.get("maturity_level", "basic"))
    return result


@tool(
    name="get_skill_profile",
    description="View current skill profile and identify weak areas",
)
def get_skill_profile():
    from memory.store import load_profile

    profile = load_profile()
    skills_summary = {
        k: {
            "level": v.level,
            "evidence_count": v.evidence_count,
            "last_feedback": v.last_feedback,
            "weighted_score": v.weighted_score,
        }
        for k, v in profile.skills.items()
    }
    return {
        "user_level": profile.user_level,
        "skills": skills_summary,
    }


@tool(
    name="review_terraform",
    description="Review Terraform files in a GitHub repository for security, cost, and best practice issues",
)
def review_terraform_tool(owner: str, repo: str):
    tf_files = read_terraform_files(owner, repo)
    if not tf_files:
        return {"error": "No Terraform files found or failed to read them."}

    result = review_terraform(tf_files)
    update_skills(str(result.get("risks", [])), result.get("maturity_level", "basic"))
    return result


@tool(
    name="review_aws_infrastructure",
    description="Review AWS infrastructure for cost optimization and security issues based on Terraform and repo analysis",
)
def review_aws_infra_tool(owner: str, repo: str):
    files = list_repo_files(owner, repo)
    if isinstance(files, str):
        return {"error": files}

    repo_analysis = analyze_repo(files)

    tf_files = read_terraform_files(owner, repo)
    if not tf_files:
        return {"error": "No Terraform files found. AWS review requires Terraform files."}

    terraform_result = review_terraform(tf_files)
    result = review_aws_infrastructure(terraform_result, repo_analysis)

    update_skills(
        str(result.get("risks", [])) + " " + str(result.get("aws_services_detected", [])),
        result.get("maturity_level", "basic"),
    )
    return result


@tool(
    name="get_learning_path",
    description="Get a personalized learning path based on current skill gaps and dependencies",
)
def get_learning_path():
    from memory.store import load_profile

    profile = load_profile()
    return get_learning_recommendations(profile)


mcp = MCPServer(
    name="DevOps Mentor MCP",
    description="A senior DevOps mentor that reviews code and infrastructure",
    system_prompt=get_system_prompt(CURRENT_MODE),
)

mcp.add_tool(set_review_mode)
mcp.add_tool(analyze_github_repo)
mcp.add_tool(review_cicd_pipeline)
mcp.add_tool(get_skill_profile)
mcp.add_tool(read_github_file)
mcp.add_tool(read_github_workflows)
mcp.add_tool(read_terraform_files)
mcp.add_tool(review_terraform_tool)
mcp.add_tool(review_aws_infra_tool)
mcp.add_tool(get_learning_path)

app.mount("/", mcp.app)
