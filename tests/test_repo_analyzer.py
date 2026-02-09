from analyzer.repo_analyzer import analyze_repo


def test_production_leaning_maturity(sample_file_list_full):
    result = analyze_repo(sample_file_list_full)
    assert result["maturity_level"] == "production-leaning"
    assert result["ci_cd"] == "present"
    assert result["iac"] == "terraform"
    assert result["containerization"] is True


def test_early_maturity(sample_file_list_minimal):
    result = analyze_repo(sample_file_list_minimal)
    assert result["maturity_level"] == "early"
    assert result["ci_cd"] == "absent"
    assert result["iac"] == "none"
    assert result["containerization"] is False


def test_developing_maturity():
    files = [
        "Dockerfile",
        ".github/workflows/ci.yml",
        "requirements.txt",
    ]
    result = analyze_repo(files)
    assert result["maturity_level"] == "developing"


def test_python_stack_detected():
    result = analyze_repo(["requirements.txt", "main.py"])
    assert "python" in result["stack"]


def test_nodejs_stack_detected():
    result = analyze_repo(["package.json", "index.js"])
    assert "nodejs" in result["stack"]


def test_golang_stack_detected():
    result = analyze_repo(["go.mod", "main.go"])
    assert "golang" in result["stack"]


def test_empty_file_list():
    result = analyze_repo([])
    assert result["maturity_level"] == "early"
    assert result["stack"] == []
    assert result["ci_cd"] == "absent"


def test_key_findings_populated(sample_file_list_full):
    result = analyze_repo(sample_file_list_full)
    findings = result["key_findings"]
    assert any("Dockerfile" in f for f in findings)
    assert any("CI/CD" in f for f in findings)
    assert any("Terraform" in f for f in findings)


def test_no_ci_finding():
    result = analyze_repo(["main.py"])
    assert any("No CI/CD" in f for f in result["key_findings"])


def test_no_iac_finding():
    result = analyze_repo(["main.py"])
    assert any("No Infrastructure" in f for f in result["key_findings"])
