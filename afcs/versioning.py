import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

INITIAL_VERSION = "1.25.4"
DEFAULT_GITHUB_REPO = "prue0115/Artillery_Fire_Control_System"

_current_version = INITIAL_VERSION


_VERSION_PATTERN = re.compile(r"(\d+(?:\.\d+)+)")


def normalize_version_string(version: str) -> str:
    """릴리스 제목이나 태그에서 버전 숫자만 추출해 비교 가능하게 만든다."""

    if not version:
        return ""

    cleaned = version.strip()
    match = _VERSION_PATTERN.search(cleaned)
    if match:
        return match.group(1)

    return cleaned.lstrip("vV")


def get_version() -> str:
    """현재 메모리에 저장된 버전 문자열을 반환한다."""

    return _current_version


def set_version(version: str):
    """버전 문자열을 정규화해 메모리에 기록한다."""
    global _current_version

    normalized = normalize_version_string(version)
    if normalized:
        _current_version = normalized


# 초기화 시 기본 버전 사용
set_version(INITIAL_VERSION)

def update_version(new_version: str) -> str:
    """버전을 갱신하고 결과 문자열을 반환한다."""

    set_version(new_version)
    return _current_version


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
