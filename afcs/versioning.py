"""버전 문자열을 파일과 동기화하며 업데이트 확인을 지원하는 헬퍼.

이 모듈은 두 가지 경로로 버전을 결정합니다.

1. 배포물과 함께 제공되는 `afcs/VERSION` 파일
2. 코드 안에 정의된 기본 상수 `DEFAULT_VERSION`

`DEFAULT_VERSION`만 있으면 코드 차원에서는 동작할 수 있지만, 실행 환경
에서 버전을 갱신하거나 배포 아티팩트가 버전 문자열을 유지하려면 파일이
필수입니다. `afcs/VERSION`은 GUI 타이틀, 빌드 산출물, 타입 검증 과정에서
일관된 버전을 노출하기 위한 단일 진실 공급원(single source of truth)으로
동작합니다.
"""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
VERSION_FILE = BASE_DIR / "VERSION"
DEFAULT_VERSION = "1.25.4"
DEFAULT_GITHUB_REPO = "prue0115/Artillery_Fire_Control_System"


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
