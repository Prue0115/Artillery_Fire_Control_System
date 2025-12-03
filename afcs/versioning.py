import json
import os
from pathlib import Path
from urllib import error, request

BASE_DIR = Path(__file__).resolve().parent
VERSION_FILE = BASE_DIR / "VERSION"
DEFAULT_VERSION = "1.25.3"
DEFAULT_REPO_SLUG = os.environ.get(
    "AFCS_GITHUB_REPO", "prue63/Artillery_Fire_Control_System"
)


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


def get_latest_release_version(repo_slug: str | None = None, timeout: float = 5.0) -> str | None:
    slug = repo_slug or DEFAULT_REPO_SLUG
    if not slug:
        return None

    url = f"https://api.github.com/repos/{slug}/releases/latest"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "afcs-version-checker",
    }

    try:
        with request.urlopen(request.Request(url, headers=headers), timeout=timeout) as resp:
            payload = resp.read().decode("utf-8")
    except error.URLError as exc:
        raise ConnectionError(f"Failed to fetch latest release: {exc}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Unexpected response from GitHub API") from exc

    return data.get("tag_name") or data.get("name")
