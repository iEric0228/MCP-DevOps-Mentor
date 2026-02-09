from mentor.mode_loader import load_mode_prompt, get_system_prompt


def test_load_mentor_mode():
    prompt = load_mode_prompt("mentor")
    assert len(prompt) > 0
    assert "MENTOR" in prompt.upper() or "mentor" in prompt.lower()


def test_load_review_mode():
    prompt = load_mode_prompt("review")
    assert len(prompt) > 0


def test_load_debug_mode():
    prompt = load_mode_prompt("debug")
    assert len(prompt) > 0


def test_load_interview_mode():
    prompt = load_mode_prompt("interview")
    assert len(prompt) > 0


def test_load_invalid_mode():
    prompt = load_mode_prompt("nonexistent_mode_xyz")
    assert prompt == ""


def test_get_system_prompt_includes_base():
    prompt = get_system_prompt("mentor")
    assert len(prompt) > 0
    # Base prompt should mention DevOps or mentor
    assert "devops" in prompt.lower() or "mentor" in prompt.lower()


def test_get_system_prompt_includes_mode():
    prompt = get_system_prompt("review")
    assert "review" in prompt.lower()


def test_get_system_prompt_default_mode():
    prompt = get_system_prompt()
    assert len(prompt) > 0
