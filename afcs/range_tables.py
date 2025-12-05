"""사격 제원 계산을 위한 사거리표 로딩 및 보간 로직."""
from __future__ import annotations

import csv
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from afcs.equipment import Equipment


@dataclass(frozen=True)
class RangeRow:
    range: float
    mill: float
    diff100m: float
    eta: float


class RangeTable:
    def __init__(self, equipment: Equipment, trajectory: str, charge: int):
        self.equipment = equipment
        self.trajectory = trajectory
        self.charge = charge
        prefix = equipment.prefix
        self.path = equipment.range_table_dir / f"{prefix}_rangeTable_{trajectory}_{charge}.csv"
        self.rows = self._load_rows()

    def _load_rows(self) -> list[RangeRow]:
        return list(self._read_rows(self.path))

    @staticmethod
    @lru_cache(maxsize=64)
    def _read_rows(path: Path) -> Iterable[RangeRow]:
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                try:
                    yield RangeRow(
                        range=float(row.get("range", "")),
                        mill=float(row.get("mill", "")),
                        diff100m=float(row.get("diff100m", "")),
                        eta=float(row.get("eta", "")),
                    )
                except (ValueError, TypeError):
                    continue

    def supports_range(self, distance: float) -> bool:
        if not self.rows:
            return False
        distances = [row.range for row in self.rows]
        return min(distances) <= distance <= max(distances)

    def calculate(self, distance: float, altitude_delta: float):
        if not self.supports_range(distance):
            raise ValueError("거리 밖입니다")

        base_mill = self._interpolate("mill", distance)
        diff100m = self._interpolate("diff100m", distance)
        eta = self._interpolate("eta", distance)

        mill_adjust = (altitude_delta / 100.0) * diff100m
        final_mill = base_mill + mill_adjust

        return {
            "mill": final_mill,
            "eta": eta,
            "charge": self.charge,
            "base_mill": base_mill,
            "diff100m": diff100m,
        }

    def _neighbor_rows(self, distance: float) -> Sequence[RangeRow]:
        ranges = [row.range for row in self.rows]
        idx = bisect_left(ranges, distance)

        neighbors: list[RangeRow] = []
        if idx > 0:
            neighbors.append(self.rows[idx - 1])
        if idx < len(self.rows):
            neighbors.append(self.rows[idx])

        remaining: list[RangeRow] = []
        if idx - 2 >= 0:
            remaining.append(self.rows[idx - 2])
        if idx + 1 < len(self.rows):
            remaining.append(self.rows[idx + 1])

        remaining.sort(key=lambda r: abs(r.range - distance))
        for row in remaining:
            if row not in neighbors:
                neighbors.append(row)
            if len(neighbors) >= 3:
                break

        neighbors.sort(key=lambda r: r.range)
        return neighbors

    def _interpolate(self, key: str, distance: float) -> float:
        neighbors = self._neighbor_rows(distance)
        if not neighbors:
            raise ValueError("적절한 범위를 찾을 수 없습니다")

        if len(neighbors) == 1:
            return getattr(neighbors[0], key)
        if len(neighbors) == 2 or neighbors[0].range == neighbors[1].range:
            lower, upper = neighbors[0], neighbors[1]
            if upper.range == lower.range:
                return getattr(lower, key)
            ratio = (distance - lower.range) / (upper.range - lower.range)
            return getattr(lower, key) + ratio * (getattr(upper, key) - getattr(lower, key))

        x0, x1, x2 = (row.range for row in neighbors[:3])
        y0, y1, y2 = (getattr(row, key) for row in neighbors[:3])

        def basis(x, a, b):
            return (x - a) / (b - a) if b != a else 0.0

        t0 = basis(distance, x1, x0) * basis(distance, x2, x0)
        t1 = basis(distance, x0, x1) * basis(distance, x2, x1)
        t2 = basis(distance, x0, x2) * basis(distance, x1, x2)
        return y0 * t0 + y1 * t1 + y2 * t2


def available_charges(equipment: Equipment, trajectory: str) -> List[int]:
    equipment.ensure_range_table_dir()
    pattern = f"{equipment.prefix}_rangeTable_{trajectory}_"
    charges = []
    for csv_path in equipment.range_table_dir.glob(f"{pattern}*.csv"):
        name = csv_path.stem
        if not name.startswith(pattern):
            continue
        suffix = name.replace(pattern, "", 1)
        if suffix.isdigit():
            charges.append(int(suffix))
    return sorted(set(charges))


def find_solutions(
    distance: float,
    altitude_delta: float,
    trajectory: str,
    equipment: Equipment,
    limit: int = 3,
    charges: Optional[List[int]] = None,
):
    solutions = []
    if charges is None:
        charges = available_charges(equipment, trajectory)
    if not charges:
        return solutions
    for charge in charges:
        try:
            table = RangeTable(equipment, trajectory, charge)
        except FileNotFoundError:
            continue
        if not table.supports_range(distance):
            continue
        try:
            solution = table.calculate(distance, altitude_delta)
        except ValueError:
            continue
        solutions.append(solution)
        if len(solutions) >= limit:
            break
    return solutions


def find_solution(distance: float, altitude_delta: float, trajectory: str, equipment: Equipment):
    solutions = find_solutions(distance, altitude_delta, trajectory, equipment=equipment, limit=1)
    return solutions[0] if solutions else None
