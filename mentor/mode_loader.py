from pathlib import Path

BASE_PATH = Path("mentor")
MODE_PATH = BASE_PATH / "modes"


def load_mode_prompt(mode: str) -> str:
    file = MODE_PATH / f"{mode}.txt"
    if not file.exists():
        return ""
    return file.read_text()


def get_system_prompt(mode: str = "mentor") -> str:
    """Compose the full system prompt from base + active mode."""
    base_file = BASE_PATH / "system_prompt.txt"
    base_prompt = base_file.read_text() if base_file.exists() else ""
    mode_prompt = load_mode_prompt(mode)
    return f"{base_prompt}\n\n{mode_prompt}".strip()
