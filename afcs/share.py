"""Sharing manager for fire mission results."""

from __future__ import annotations

__all__ = ["FireMissionShare", "format_solution_list", "describe_shared_payload", "share_manager"]

import secrets
import string
from datetime import datetime


class FireMissionShare:
    """Manage one-time room codes and shared calculation payloads."""

    rooms: dict[str, dict] = {}

    def __init__(self):
        self.active_code: str | None = None
        self.mode: str | None = None
        self.current_payload: dict | None = None
        self.root = None
        self._listeners: list = []

    def attach_root(self, root):
        self.root = root

    def _generate_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(6))

    def start_new_room(self) -> str:
        code = self._generate_code()
        self.active_code = code
        self.mode = "host"
        self.current_payload = None
        self._notify_listeners()
        return code

    def join_room(self, code: str):
        normalized = code.strip().upper()
        if not normalized:
            return
        self.active_code = normalized
        self.mode = "guest"
        self.current_payload = self.rooms.get(normalized)
        self._notify_listeners()

    def stop_sharing(self):
        self.active_code = None
        self.mode = None
        self.current_payload = None
        self._notify_listeners()

    def share_results(self, payload: dict):
        if not self.active_code:
            return
        shared_payload = {
            **payload,
            "code": self.active_code,
            "shared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.rooms[self.active_code] = shared_payload
        self.current_payload = shared_payload
        self._notify_listeners()

    def register_listener(self, callback):
        self._listeners.append(callback)
        callback(self.current_payload, self.active_code, self.mode)
        return callback

    def unregister_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        for listener in list(self._listeners):
            listener(self.current_payload, self.active_code, self.mode)


def format_solution_list(title: str, solutions):
    if not solutions:
        return f"{title}: 지원 범위 밖입니다"

    header = f"{'CH':>2} | {'MILL':>10} | {'ETA':>5}"
    lines = [f"{title}:", header]
    for solution in solutions:
        lines.append(
            f"{solution['charge']:>2} | {solution['mill']:>10.2f} | {solution['eta']:>5.1f}"
        )
    return "\n".join(lines)


def describe_shared_payload(payload: dict | None) -> str:
    if not payload:
        return "아직 공유된 제원이 없습니다. 계산 버튼을 눌러 제원을 공유하세요."

    timestamp = payload.get("shared_at", "")
    lines = [
        f"장비: {payload.get('system', 'N/A')}",
        f"거리: {payload.get('distance', 'N/A')} m",
        f"고도 차이: {payload.get('altitude_delta', 'N/A')} m",
    ]
    if timestamp:
        lines.append(f"공유 시각: {timestamp}")

    low_text = format_solution_list("LOW", payload.get("low", []))
    high_text = format_solution_list("HIGH", payload.get("high", []))
    return "\n".join([*lines, "", low_text, "", high_text])


share_manager = FireMissionShare()
