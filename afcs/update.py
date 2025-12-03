from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from .version import LATEST_RELEASE_API, LATEST_RELEASE_PAGE, __version__


class UpdateCheckError(Exception):
    """Raised when update information cannot be retrieved."""


@dataclass
class UpdateResult:
    latest_version: str
    download_url: str | None
    is_newer: bool


_VERSION_PATTERN = re.compile(r"^v?(?P<num>[0-9]+(\.[0-9]+)*)")


def _normalize_version(version: str) -> tuple[int, ...]:
    match = _VERSION_PATTERN.match(version.strip())
    if not match:
        return tuple()
    parts = match.group("num").split(".")
    normalized = []
    for part in parts:
        try:
            normalized.append(int(part))
        except ValueError:
            normalized.append(0)
    return tuple(normalized)


def _is_newer(latest: str, current: str) -> bool:
    return _normalize_version(latest) > _normalize_version(current)


def check_for_updates(timeout: float = 5.0) -> UpdateResult:
    request = urllib.request.Request(LATEST_RELEASE_API, headers={"User-Agent": "AFCS Update Checker"})

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise UpdateCheckError(f"업데이트 정보를 불러올 수 없습니다. (HTTP {response.status})")
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:  # pragma: no cover - network dependency
        raise UpdateCheckError("업데이트 서버와 통신할 수 없습니다. 인터넷 연결을 확인하세요.") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise UpdateCheckError("업데이트 정보를 해석할 수 없습니다.") from exc

    tag_name = data.get("tag_name")
    html_url = data.get("html_url", LATEST_RELEASE_PAGE)

    if not tag_name:
        raise UpdateCheckError("최신 버전을 찾을 수 없습니다.")

    is_newer = _is_newer(tag_name, __version__)
    return UpdateResult(latest_version=tag_name, download_url=html_url, is_newer=is_newer)
