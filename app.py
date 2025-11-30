import csv
import math
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


APP_BG = "#f5f5f7"
CARD_BG = "#ffffff"
TEXT_COLOR = "#1d1d1f"
MUTED_COLOR = "#6e6e73"
ACCENT_COLOR = "#007aff"
TITLE_FONT = ("SF Pro Display", 18, "bold")
BODY_FONT = ("SF Pro Text", 12)
MONO_FONT = ("SF Mono", 12)

BASE_DIR = Path(__file__).parent
RANGE_TABLE_DIR = BASE_DIR / "rangeTables"
SYSTEM_FILE_PREFIX = {"M109A6": "M109A6", "M119": "M1129"}


class RangeTable:
    def __init__(self, system: str, trajectory: str, charge: int):
        self.system = system
        self.trajectory = trajectory
        self.charge = charge
        prefix = SYSTEM_FILE_PREFIX.get(system, system)
        self.path = RANGE_TABLE_DIR / f"{prefix}_rangeTable_{trajectory}_{charge}.csv"
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
        if not self.rows:
            return False
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


def find_solutions(
    distance: float, altitude_delta: float, trajectory: str, system: str = "M109A6", limit: int = 3
):
    solutions = []
    charges = [0, 1, 2, 3, 4]
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


def find_solution(distance: float, altitude_delta: float, trajectory: str, system: str = "M109A6"):
    solutions = find_solutions(distance, altitude_delta, trajectory, system=system, limit=1)
    return solutions[0] if solutions else None


def format_solution_list(title: str, solutions):
    if not solutions:
        return f"{title}: 지원 범위 밖입니다"

    header = f"{'CH':>2} | {'MILL':>10} | {'ETA':>5}"
    lines = [f"{title}:", header]
    for solution in solutions:
        lines.append(f"{solution['charge']:>2} | {solution['mill']:>10.2f} | {solution['eta']:>5.1f}")
    return "\n".join(lines)


def update_solution_table(rows, status_label, solutions):
    if not solutions:
        status_label.config(text="지원 범위 밖입니다")
    else:
        status_label.config(text="")

    for idx, row in enumerate(rows):
        if idx < len(solutions):
            solution = solutions[idx]
            row["ch"].config(text=f"{solution['charge']}", fg=TEXT_COLOR)
            row["mill"].config(text=f"{solution['mill']:.2f}", fg=TEXT_COLOR)
            row["eta"].config(text=f"{solution['eta']:.1f}", fg=TEXT_COLOR)
        else:
            row["ch"].config(text="—", fg=MUTED_COLOR)
            row["mill"].config(text="—", fg=MUTED_COLOR)
            row["eta"].config(text="—", fg=MUTED_COLOR)


def calculate_and_display(
    system_var,
    low_rows,
    high_rows,
    low_status,
    high_status,
    delta_label,
    my_altitude_entry,
    target_altitude_entry,
    distance_entry,
):
    try:
        my_alt = float(my_altitude_entry.get())
        target_alt = float(target_altitude_entry.get())
        distance = float(distance_entry.get())
    except ValueError:
        messagebox.showerror("입력 오류", "숫자만 입력하세요.")
        return

    altitude_delta = target_alt - my_alt
    system = system_var.get()
    low_solutions = find_solutions(distance, altitude_delta, "low", system=system, limit=3)
    high_solutions = find_solutions(distance, altitude_delta, "high", system=system, limit=3)

    update_solution_table(low_rows, low_status, low_solutions)
    update_solution_table(high_rows, high_status, high_solutions)
    delta_label.config(text=f"고도 차이: {altitude_delta:+.1f} m")


def apply_styles(root: tk.Tk):
    style = ttk.Style()
    style.theme_use("clam")

    # Global colors
    style.configure("TFrame", background=APP_BG)
    style.configure("Main.TFrame", background=APP_BG)
    style.configure("Card.TFrame", background=CARD_BG, relief="flat", borderwidth=0)

    style.configure("Body.TLabel", background=APP_BG, foreground=TEXT_COLOR, font=BODY_FONT)
    style.configure("Muted.TLabel", background=APP_BG, foreground=MUTED_COLOR, font=BODY_FONT)
    style.configure("CardBody.TLabel", background=CARD_BG, foreground=TEXT_COLOR, font=BODY_FONT, anchor="w")
    style.configure("TableHeader.TLabel", background=CARD_BG, foreground=MUTED_COLOR, font=(BODY_FONT[0], 11, "bold"))
    style.configure("TableStatus.TLabel", background=CARD_BG, foreground=MUTED_COLOR, font=BODY_FONT)

    style.configure(
        "Primary.TButton",
        font=(BODY_FONT[0], 12, "bold"),
        foreground="#ffffff",
        background=ACCENT_COLOR,
        borderwidth=0,
        padding=(14, 10),
    )
    style.map(
        "Primary.TButton",
        background=[("active", "#0a84ff"), ("pressed", "#0060df")],
        foreground=[("disabled", "#d1d1d6")],
    )

    style.configure(
        "Secondary.TButton",
        font=(BODY_FONT[0], 12, "bold"),
        foreground=ACCENT_COLOR,
        background=CARD_BG,
        borderwidth=1,
        padding=(14, 10),
        relief="solid",
    )
    style.map(
        "Secondary.TButton",
        background=[("active", "#f0f4ff")],
        foreground=[("disabled", "#c7c7cc")],
    )

    style.configure(
        "Card.TLabelframe",
        background=CARD_BG,
        borderwidth=0,
        relief="flat",
        padding=(12, 12, 12, 10),
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=CARD_BG,
        foreground=TEXT_COLOR,
        font=(BODY_FONT[0], 12, "bold"),
    )


def build_solution_table(parent):
    table = ttk.Frame(parent, style="Card.TFrame")
    table.columnconfigure(0, weight=1)
    table.columnconfigure(1, weight=3)
    table.columnconfigure(2, weight=2)

    headers = ["CH", "MILL", "ETA"]
    for col, text in enumerate(headers):
        ttk.Label(table, text=text, style="TableHeader.TLabel").grid(row=0, column=col, sticky="w", padx=(0, 8))

    rows = []
    for i in range(3):
        ch = tk.Label(table, text="—", bg=CARD_BG, fg=MUTED_COLOR, font=MONO_FONT, anchor="w", width=4)
        mill = tk.Label(table, text="—", bg=CARD_BG, fg=MUTED_COLOR, font=MONO_FONT, anchor="w", width=12)
        eta = tk.Label(table, text="—", bg=CARD_BG, fg=MUTED_COLOR, font=MONO_FONT, anchor="w", width=6)

        ch.grid(row=i + 1, column=0, sticky="w", pady=3)
        mill.grid(row=i + 1, column=1, sticky="w", pady=3)
        eta.grid(row=i + 1, column=2, sticky="w", pady=3)

        rows.append({"ch": ch, "mill": mill, "eta": eta})

    status = ttk.Label(parent, text="계산 결과가 여기에 표시됩니다", style="TableStatus.TLabel")
    status.grid(row=1, column=0, sticky="w", pady=(8, 0))

    table.grid(row=0, column=0, sticky="nsew")
    parent.columnconfigure(0, weight=1)
    return rows, status


def build_gui():
    root = tk.Tk()
    root.title("포병 계산기")
    root.configure(bg=APP_BG)
    root.option_add("*Font", BODY_FONT)
    apply_styles(root)

    main = ttk.Frame(root, style="Main.TFrame", padding=20)
    main.grid(row=0, column=0, sticky="nsew")

    header = ttk.Frame(main, style="Main.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    header.columnconfigure(0, weight=1)
    title = ttk.Label(header, text="포병 계산기", font=TITLE_FONT, foreground=TEXT_COLOR, background=APP_BG)
    title.grid(row=0, column=0, sticky="w")
    subtitle = ttk.Label(
        header,
        text="M109A6 · M119 저각·고각 해법을 깔끔한 표로 확인하세요.",
        style="Muted.TLabel",
    )
    subtitle.grid(row=1, column=0, sticky="w")

    system_var = tk.StringVar(value="M109A6")
    system_picker = ttk.Frame(header, style="Main.TFrame")
    system_picker.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))
    ttk.Label(system_picker, text="장비", style="Body.TLabel").grid(row=0, column=0, sticky="e")
    system_select = ttk.Combobox(
        system_picker,
        textvariable=system_var,
        values=["M109A6", "M119"],
        state="readonly",
        width=8,
        font=BODY_FONT,
    )
    system_select.grid(row=0, column=1, sticky="w", padx=(6, 0))

    input_card = ttk.Frame(main, style="Card.TFrame", padding=(16, 16, 16, 12))
    input_card.grid(row=1, column=0, sticky="ew")
    input_card.columnconfigure(1, weight=1)

    ttk.Label(input_card, text="나의 고도 (m)", style="CardBody.TLabel").grid(
        row=0, column=0, sticky="e", padx=(0, 10), pady=4
    )
    my_altitude_entry = ttk.Entry(input_card)
    my_altitude_entry.grid(row=0, column=1, sticky="ew", pady=4)

    ttk.Label(input_card, text="타격 지점 고도 (m)", style="CardBody.TLabel").grid(
        row=1, column=0, sticky="e", padx=(0, 10), pady=4
    )
    target_altitude_entry = ttk.Entry(input_card)
    target_altitude_entry.grid(row=1, column=1, sticky="ew", pady=4)

    ttk.Label(input_card, text="거리 (m)", style="CardBody.TLabel").grid(
        row=2, column=0, sticky="e", padx=(0, 10), pady=4
    )
    distance_entry = ttk.Entry(input_card)
    distance_entry.grid(row=2, column=1, sticky="ew", pady=4)

    button_row = ttk.Frame(main, style="Main.TFrame")
    button_row.grid(row=2, column=0, sticky="ew", pady=(12, 0))
    button_row.columnconfigure(0, weight=1)

    calculate_button = ttk.Button(
        button_row,
        text="계산",
        style="Primary.TButton",
        command=lambda: None,
    )
    calculate_button.grid(row=0, column=0, sticky="ew")

    results_card = ttk.Frame(main, style="Card.TFrame", padding=16)
    results_card.grid(row=3, column=0, sticky="ew", pady=(16, 0))
    results_card.columnconfigure(0, weight=1)
    results_card.columnconfigure(1, weight=1)

    low_frame = ttk.Labelframe(results_card, text="저각", style="Card.TLabelframe")
    low_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    high_frame = ttk.Labelframe(results_card, text="고각", style="Card.TLabelframe")
    high_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
    results_card.rowconfigure(0, weight=1)
    results_card.columnconfigure(0, weight=1)
    results_card.columnconfigure(1, weight=1)

    low_rows, low_status = build_solution_table(low_frame)
    high_rows, high_status = build_solution_table(high_frame)

    delta_label = ttk.Label(main, text="고도 차이: 계산 필요", style="Muted.TLabel")
    delta_label.grid(row=4, column=0, sticky="w", pady=(10, 0))

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    main.columnconfigure(0, weight=1)

    calculate_button.configure(
        command=lambda: calculate_and_display(
            system_var,
            low_rows,
            high_rows,
            low_status,
            high_status,
            delta_label,
            my_altitude_entry,
            target_altitude_entry,
            distance_entry,
        )
    )

    return root


def main():
    root = build_gui()
    root.mainloop()


if __name__ == "__main__":
    main()
