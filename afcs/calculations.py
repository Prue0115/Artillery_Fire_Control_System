import csv
from bisect import bisect_left
from typing import TypedDict

from .config import RANGE_TABLE_DIR

SYSTEM_FILE_PREFIX = {
    "M109A6": "M109A6",
    "M1129": "M1129",
    "M119": "M119",
    "RM-70": "RM70",
    "siala": "siala",
}

SYSTEM_TRAJECTORY_CHARGES: dict[str, dict[str, list[int]]] = {
    "M1129": {"low": [], "high": [0, 1, 2]}
}


class RangeRow(TypedDict):
    range: float
    mill: float
    diff100m: float
    eta: float


class Solution(TypedDict):
    mill: float
    eta: float
    charge: int
    base_mill: float
    diff100m: float


class RangeTable:
    def __init__(self, system: str, trajectory: str, charge: int):
        self.system = system
        self.trajectory = trajectory
        self.charge = charge
        prefix = SYSTEM_FILE_PREFIX.get(system, system)
        self.path = RANGE_TABLE_DIR / f"{prefix}_rangeTable_{trajectory}_{charge}.csv"
        self.rows: list[RangeRow] = self._load_rows()

    def _load_rows(self) -> list[RangeRow]:
        with self.path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows: list[RangeRow] = []
            for _, row in enumerate(reader, start=1):
                cleaned = {
                    (key.strip() if key else ""): (value.strip() if value is not None else "")
                    for key, value in row.items()
                }
                try:
                    r = float(cleaned.get("range", ""))
                    mill = float(cleaned.get("mill", ""))
                    diff100m = float(cleaned.get("diff100m", ""))
                    eta = float(cleaned.get("eta", ""))
                except (ValueError, TypeError):
                    continue
                rows.append({"range": r, "mill": mill, "diff100m": diff100m, "eta": eta})
        return rows

    def supports_range(self, distance: float) -> bool:
        if not self.rows:
            return False
        distances: list[float] = [row["range"] for row in self.rows]
        return min(distances) <= distance <= max(distances)

    def calculate(self, distance: float, altitude_delta: float) -> Solution:
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

    def _neighbor_rows(self, distance: float) -> list[RangeRow]:
        ranges = [row["range"] for row in self.rows]
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

        remaining.sort(key=lambda r: abs(r["range"] - distance))
        for row in remaining:
            if row not in neighbors:
                neighbors.append(row)
            if len(neighbors) >= 3:
                break

        neighbors.sort(key=lambda r: r["range"])
        return neighbors

    def _interpolate(self, key: str, distance: float) -> float:
        neighbors = self._neighbor_rows(distance)
        if not neighbors:
            raise ValueError("적절한 범위를 찾을 수 없습니다")

        if len(neighbors) == 1:
            return neighbors[0][key]
        if len(neighbors) == 2 or neighbors[0]["range"] == neighbors[1]["range"]:
            lower, upper = neighbors[0], neighbors[1]
            if upper["range"] == lower["range"]:
                return lower[key]
            ratio = (distance - lower["range"]) / (upper["range"] - lower["range"])
            return lower[key] + ratio * (upper[key] - lower[key])

        x0, x1, x2 = (row["range"] for row in neighbors[:3])
        y0, y1, y2 = (row[key] for row in neighbors[:3])

        def basis(x: float, a: float, b: float) -> float:
            return (x - a) / (b - a) if b != a else 0.0

        t0 = basis(distance, x1, x0) * basis(distance, x2, x0)
        t1 = basis(distance, x0, x1) * basis(distance, x2, x1)
        t2 = basis(distance, x0, x2) * basis(distance, x1, x2)
        return y0 * t0 + y1 * t1 + y2 * t2


def available_charges(system: str, trajectory: str) -> list[int]:
    prefix = SYSTEM_FILE_PREFIX.get(system, system)
    pattern = f"{prefix}_rangeTable_{trajectory}_"
    charges: list[int] = []
    for csv_path in RANGE_TABLE_DIR.glob(f"{pattern}*.csv"):
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
    system: str = "M109A6",
    limit: int = 3,
    charges: list[int] | None = None,
) -> list[Solution]:
    solutions: list[Solution] = []
    if charges is None:
        charges = available_charges(system, trajectory)
    if not charges:
        return solutions
    for charge in charges:
        try:
            table = RangeTable(system, trajectory, charge)
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


def find_solution(
    distance: float, altitude_delta: float, trajectory: str, system: str = "M109A6"
) -> Solution | None:
    solutions = find_solutions(distance, altitude_delta, trajectory, system=system, limit=1)
    return solutions[0] if solutions else None


def format_solution_list(title: str, solutions: list[Solution]) -> str:
    if not solutions:
        return f"{title}: 지원 범위 밖입니다"

    header = f"{'CH':>2} | {'MILL':>10} | {'ETA':>5}"
    lines = [f"{title}:", header]
    for solution in solutions:
        lines.append(f"{solution['charge']:>2} | {solution['mill']:>10.2f} | {solution['eta']:>5.1f}")
    return "\n".join(lines)
