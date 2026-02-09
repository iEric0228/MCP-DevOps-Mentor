import os
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def list_repo_files(owner: str, repo: str):
    if not GITHUB_TOKEN:
        return "GitHub token not configured."

    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return f"Failed to list repo files: {response.text}"

    tree = response.json().get("tree", [])
    return [item["path"] for item in tree if item["type"] == "blob"]


def read_github_file(owner: str, repo: str, path: str):
    if not GITHUB_TOKEN:
        return "GitHub token not configured."

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return f"Failed to read file: {response.text}"

    data = response.json()
    if data.get("encoding") == "base64":
        import base64

        return base64.b64decode(data["content"]).decode("utf-8")

    return data.get("content", "")


def read_github_workflows(owner: str, repo: str):
    workflows_path = ".github/workflows"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{workflows_path}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return {}

    workflows = {}
    for file in response.json():
        if file["type"] == "file":
            file_content = requests.get(file["download_url"]).text
            workflows[file["name"]] = file_content

    return workflows


def read_terraform_files(owner: str, repo: str):
    all_files = list_repo_files(owner, repo)
    if isinstance(all_files, str):
        return {}

    tf_paths = [p for p in all_files if p.endswith(".tf")]
    tf_files = {}
    for path in tf_paths:
        content = read_github_file(owner, repo, path)
        if isinstance(content, str) and not content.startswith("Failed"):
            tf_files[path] = content
    return tf_files


def read_terraform_all_files(owner: str, repo: str):
    """Read all .tf and .tfvars files from a repository."""
    all_files = list_repo_files(owner, repo)
    if isinstance(all_files, str):
        return {}

    tf_paths = [p for p in all_files if p.endswith(".tf") or p.endswith(".tfvars")]
    tf_files = {}
    for path in tf_paths:
        content = read_github_file(owner, repo, path)
        if isinstance(content, str) and not content.startswith("Failed"):
            tf_files[path] = content
    return tf_files
