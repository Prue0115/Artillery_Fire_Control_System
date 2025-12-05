from __future__ import annotations

"""Device profile helpers for desktop/mobile 레이아웃을 구분 관리합니다."""

from dataclasses import dataclass
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


def resolve_device_profile() -> DeviceProfile:
    """플랫폼에 따라 알맞은 디바이스 프로필을 반환합니다."""

    if sys.platform.startswith("android"):
        return _PROFILES["mobile"]
    return _PROFILES["desktop"]


__all__ = ["DeviceProfile", "resolve_device_profile"]
