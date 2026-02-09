from typing import List, Dict


def analyze_repo(file_paths: List[str]) -> Dict:
    findings = []
    stack = set()

    has_docker = "Dockerfile" in file_paths
    has_compose = "docker-compose.yml" in file_paths
    has_ci = any(p.startswith(".github/workflows/") for p in file_paths)
    has_terraform = any(
        p.endswith(".tf") or p.startswith("terraform/") for p in file_paths
    )

    if "package.json" in file_paths:
        stack.add("nodejs")

    if "requirements.txt" in file_paths or "pyproject.toml" in file_paths:
        stack.add("python")

    if "go.mod" in file_paths:
        stack.add("golang")

    if has_docker:
        findings.append("Dockerfile present")

    if has_ci:
        findings.append("CI/CD pipeline detected")

    if has_terraform:
        findings.append("Infrastructure as Code detected (Terraform)")

    if not has_ci:
        findings.append("No CI/CD pipeline detected")

    if not has_terraform:
        findings.append("No Infrastructure as Code detected")

    # DevOps maturity heuristic
    maturity = "early"
    if has_ci and has_docker:
        maturity = "developing"
    if has_ci and has_docker and has_terraform:
        maturity = "production-leaning"

    return {
        "stack": list(stack),
        "ci_cd": "present" if has_ci else "absent",
        "iac": "terraform" if has_terraform else "none",
        "containerization": has_docker,
        "maturity_level": maturity,
        "key_findings": findings,
    }
