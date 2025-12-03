from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VERSION_FILE = BASE_DIR / "VERSION"
DEFAULT_VERSION = "1.25.3"


def get_version() -> str:
    if VERSION_FILE.exists():
        content = VERSION_FILE.read_text(encoding="utf-8").strip()
        if content:
            return content
    set_version(DEFAULT_VERSION)
    return DEFAULT_VERSION


def set_version(version: str):
    VERSION_FILE.write_text(version.strip(), encoding="utf-8")


def update_version(new_version: str) -> str:
    normalized = new_version.strip()
    if not normalized:
        raise ValueError("Version cannot be empty")

    set_version(normalized)
    return normalized
