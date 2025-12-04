"""버전 문자열을 파일과 동기화하며 업데이트 확인을 지원하는 헬퍼.

`afcs/VERSION` 파일을 단일 진실 공급원(single source of truth)으로 사용해
버전을 관리한다. 코드 내부의 기본값은 파일이 존재하지 않을 때 초기값을
기록하는 부트스트랩 용도로만 사용한다.
"""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
VERSION_FILE = BASE_DIR / "VERSION"
INITIAL_VERSION = "1.25.4"
DEFAULT_GITHUB_REPO = "prue0115/Artillery_Fire_Control_System"


def get_version() -> str:
    if VERSION_FILE.exists():
        content = VERSION_FILE.read_text(encoding="utf-8").strip()
        if content:
            return content
    set_version(INITIAL_VERSION)
    return INITIAL_VERSION


def set_version(version: str):
    VERSION_FILE.write_text(version.strip(), encoding="utf-8")


def update_version(new_version: str) -> str:
    normalized = new_version.strip()
    if not normalized:
        raise ValueError("Version cannot be empty")

    set_version(normalized)
    return normalized


def fetch_latest_release(repo: str | None = None, timeout: float = 5.0):
    repo_slug = repo or os.environ.get("AFCS_GITHUB_REPO", DEFAULT_GITHUB_REPO)
    if not repo_slug:
        return None

    url = f"https://api.github.com/repos/{repo_slug}/releases/latest"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "AFCS-Version-Checker",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    latest_version = payload.get("tag_name") or payload.get("name")
    if not latest_version:
        return None

    return {"version": latest_version, "url": payload.get("html_url")}
