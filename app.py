import csv
import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

BASE_DIR = Path(__file__).parent
RANGE_TABLE_DIR = BASE_DIR / "rangeTables"
VERSION_FILE = BASE_DIR / "version.txt"
UPDATE_MANIFEST = BASE_DIR / "update_manifest.json"


class RangeTable:
    def __init__(self, trajectory: str, charge: int):
        self.trajectory = trajectory
        self.charge = charge
        self.path = RANGE_TABLE_DIR / f"M109A6_rangeTable_{trajectory}_{charge}.csv"
        self.rows = self._load_rows()

    def _load_rows(self):
        with self.path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                cleaned = {key.strip(): value for key, value in row.items()}
                rows.append(
                    {
                        "range": float(cleaned["range"]),
                        "mill": float(cleaned["mill"]),
                        "diff100m": float(cleaned["diff100m"]),
                        "eta": float(cleaned["eta"]),
                    }
                )
        return rows

    def supports_range(self, distance: float) -> bool:
        distances = [row["range"] for row in self.rows]
        return min(distances) <= distance <= max(distances)

    def calculate(self, distance: float, altitude_delta: float):
        if not self.supports_range(distance):
            raise ValueError("거리 밖입니다")

        lower_row, upper_row = self._find_bounds(distance)
        if lower_row["range"] == upper_row["range"]:
            base_mill = lower_row["mill"]
            diff100m = lower_row["diff100m"]
            eta = lower_row["eta"]
        else:
            ratio = (distance - lower_row["range"]) / (upper_row["range"] - lower_row["range"])
            base_mill = lower_row["mill"] + ratio * (upper_row["mill"] - lower_row["mill"])
            diff100m = lower_row["diff100m"] + ratio * (upper_row["diff100m"] - lower_row["diff100m"])
            eta = lower_row["eta"] + ratio * (upper_row["eta"] - lower_row["eta"])

        mill_adjust = (altitude_delta / 100.0) * diff100m
        final_mill = base_mill + mill_adjust

        return {
            "mill": final_mill,
            "eta": eta,
            "charge": self.charge,
            "base_mill": base_mill,
            "diff100m": diff100m,
        }

    def _find_bounds(self, distance: float):
        lower = None
        upper = None
        for row in self.rows:
            if row["range"] <= distance:
                lower = row
            if row["range"] >= distance:
                upper = row
                break
        if lower is None or upper is None:
            raise ValueError("적절한 범위를 찾을 수 없습니다")
        return lower, upper


def find_solutions(distance: float, altitude_delta: float, trajectory: str, limit: int = 3):
    solutions = []
    charges = [0, 1, 2, 3, 4]
    for charge in charges:
        table = RangeTable(trajectory, charge)
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


def find_solution(distance: float, altitude_delta: float, trajectory: str):
    solutions = find_solutions(distance, altitude_delta, trajectory, limit=1)
    return solutions[0] if solutions else None


def load_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return "0.0.0"


def check_updates():
    current_version = load_version()
    if not UPDATE_MANIFEST.exists():
        messagebox.showinfo("업데이트", "업데이트 정보가 없습니다. 최신 버전을 확인할 수 없습니다.")
        return

    try:
        manifest = json.loads(UPDATE_MANIFEST.read_text(encoding="utf-8"))
        latest = manifest.get("latest_version", current_version)
    except (json.JSONDecodeError, OSError):
        messagebox.showerror("업데이트", "업데이트 정보를 읽을 수 없습니다.")
        return

    if latest == current_version:
        messagebox.showinfo("업데이트", f"현재 버전 ({current_version}) 이 최신입니다.")
    else:
        notes = manifest.get("notes", "")
        url = manifest.get("download_url", "")
        message = [f"새 버전 {latest} 이(가) 있습니다!", f"현재 버전: {current_version}"]
        if notes:
            message.append(f"변경점: {notes}")
        if url:
            message.append(f"다운로드: {url}")
        messagebox.showinfo("업데이트", "\n".join(message))


def format_solution_list(title: str, solutions):
    if not solutions:
        return f"{title}: 지원 범위 밖입니다"

    header = f"{'CH':>2} | {'MILL':>10} | {'ETA':>5}"
    lines = [f"{title}:", header]
    for solution in solutions:
        lines.append(f"{solution['charge']:>2} | {solution['mill']:>10.2f} | {solution['eta']:>5.1f}")
    return "\n".join(lines)


def calculate_and_display(low_label, high_label, delta_label, my_altitude_entry, target_altitude_entry, distance_entry):
    try:
        my_alt = float(my_altitude_entry.get())
        target_alt = float(target_altitude_entry.get())
        distance = float(distance_entry.get())
    except ValueError:
        messagebox.showerror("입력 오류", "숫자만 입력하세요.")
        return

    altitude_delta = target_alt - my_alt
    low_solutions = find_solutions(distance, altitude_delta, "low", limit=3)
    high_solutions = find_solutions(distance, altitude_delta, "high", limit=3)

    low_message = format_solution_list("저각", low_solutions)
    high_message = format_solution_list("고각", high_solutions)

    low_label.config(text=low_message)
    high_label.config(text=high_message)
    delta_label.config(text=f"고도 차이: {altitude_delta:+.1f} m")


def build_gui():
    root = tk.Tk()
    root.title("M109A6 포병 계산기")

    tk.Label(root, text="나의 고도 (m)").grid(row=0, column=0, sticky="e", padx=5, pady=5)
    my_altitude_entry = tk.Entry(root)
    my_altitude_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(root, text="타격 지점 고도 (m)").grid(row=1, column=0, sticky="e", padx=5, pady=5)
    target_altitude_entry = tk.Entry(root)
    target_altitude_entry.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(root, text="거리 (m)").grid(row=2, column=0, sticky="e", padx=5, pady=5)
    distance_entry = tk.Entry(root)
    distance_entry.grid(row=2, column=1, padx=5, pady=5)

    version = load_version()
    tk.Label(root, text=f"버전: {version}").grid(row=3, column=0, columnspan=2, pady=(0, 5))

    results_frame = tk.Frame(root)
    results_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=10)

    low_label = tk.Label(results_frame, text="저각:", justify="left", anchor="nw")
    low_label.grid(row=0, column=0, sticky="nw")

    high_label = tk.Label(results_frame, text="고각:", justify="left", anchor="nw")
    high_label.grid(row=0, column=1, sticky="nw", padx=(10, 0))

    results_frame.columnconfigure(0, weight=1)
    results_frame.columnconfigure(1, weight=1)

    delta_label = tk.Label(root, text="고도 차이: 계산 필요", anchor="w", justify="left")
    delta_label.grid(row=6, column=0, columnspan=2, sticky="w", padx=5)

    calculate_button = tk.Button(
        root,
        text="계산",
        command=lambda: calculate_and_display(
            low_label,
            high_label,
            delta_label,
            my_altitude_entry,
            target_altitude_entry,
            distance_entry,
        ),
    )
    calculate_button.grid(row=4, column=0, padx=5, pady=5, sticky="ew")

    update_button = tk.Button(root, text="업데이트 확인", command=check_updates)
    update_button.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

    for i in range(2):
        root.columnconfigure(i, weight=1)

    return root


def main():
    root = build_gui()
    root.mainloop()


if __name__ == "__main__":
    main()
