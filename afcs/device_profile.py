from __future__ import annotations

"""Device profile helpers for desktop/mobile 레이아웃을 구분 관리합니다."""

from dataclasses import dataclass
import os
import sys
from typing import Dict


@dataclass(frozen=True)
class DeviceProfile:
    name: str
    font_scale: float = 1.0
    padding_scale: float = 1.0
    base_geometry: str | None = None
    narrow_layout: bool = False


_PROFILES: Dict[str, DeviceProfile] = {
    "desktop": DeviceProfile(
        name="desktop",
        font_scale=1.0,
        padding_scale=1.0,
        base_geometry="1200x720",
        narrow_layout=False,
    ),
    "mobile": DeviceProfile(
        name="mobile",
        font_scale=1.15,
        padding_scale=1.2,
        base_geometry="960x1280",
        narrow_layout=True,
    ),
}


def _default_profile_name() -> str:
    if sys.platform.startswith("android"):
        return "mobile"
    return "desktop"


def resolve_device_profile(name: str | None = None) -> DeviceProfile:
    """환경 변수와 인자로 주어진 이름을 바탕으로 디바이스 프로필을 결정합니다."""

    # Android 실행 시에는 별도 선택 없이 모바일 프로필을 강제합니다.
    if sys.platform.startswith("android"):
        return _PROFILES["mobile"]

    explicit = (name or "").strip().lower()
    env_value = os.environ.get("AFCS_DEVICE_PROFILE", "").strip().lower()
    profile_name = explicit or env_value or _default_profile_name()
    return _PROFILES.get(profile_name, _PROFILES["desktop"])


__all__ = ["DeviceProfile", "resolve_device_profile"]
