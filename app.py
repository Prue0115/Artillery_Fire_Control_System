import csv
import math
from bisect import bisect_left
from datetime import datetime
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

MIL_PER_DEG = 6400 / 360.0
BASE_DIR = Path(__file__).parent
RANGE_TABLE_DIR = BASE_DIR / "rangeTables"
SYSTEM_FILE_PREFIX = {
    "M109A6": "M109A6",
    "M1129": "M1129",
    "M119": "M119",
    "RH-70": "RM70",
    "siala": "siala",
}

# 장비별로 고정된 궤적으로만 사격해야 하는 경우를 명시한다.
# 지정되지 않은 장비는 존재하는 CSV 파일을 기준으로 자동 감지한다.
SYSTEM_TRAJECTORY_CHARGES = {"M1129": {"low": [], "high": [0, 1, 2]}}


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
            for line_no, row in enumerate(reader, start=1):
                # 키 공백 제거 및 None 처리
                cleaned = { (key.strip() if key else ""): (value.strip() if value is not None else "") for key, value in row.items() }
                try:
                    r = float(cleaned.get("range", ""))
                    mill = float(cleaned.get("mill", ""))
                    diff100m = float(cleaned.get("diff100m", ""))
                    eta = float(cleaned.get("eta", ""))
                except (ValueError, TypeError):
                    # 숫자 변환 불가(빈값 포함)하면 해당 행은 건너뜀
                    continue
                rows.append({"range": r, "mill": mill, "diff100m": diff100m, "eta": eta})
        return rows

    def supports_range(self, distance: float) -> bool:
        if not self.rows:
            return False
        distances = [row["range"] for row in self.rows]
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

    def _neighbor_rows(self, distance: float):
        ranges = [row["range"] for row in self.rows]
        idx = bisect_left(ranges, distance)

        neighbors = []
        if idx > 0:
            neighbors.append(self.rows[idx - 1])
        if idx < len(self.rows):
            neighbors.append(self.rows[idx])

        remaining = []
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

        def basis(x, a, b):
            return (x - a) / (b - a) if b != a else 0.0

        t0 = basis(distance, x1, x0) * basis(distance, x2, x0)
        t1 = basis(distance, x0, x1) * basis(distance, x2, x1)
        t2 = basis(distance, x0, x2) * basis(distance, x1, x2)
        return y0 * t0 + y1 * t1 + y2 * t2


def available_charges(system: str, trajectory: str):
    prefix = SYSTEM_FILE_PREFIX.get(system, system)
    pattern = f"{prefix}_rangeTable_{trajectory}_"
    charges = []
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
):
    solutions = []
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


def update_solution_table(rows, status_label, solutions, message: str | None = None):
    if message:
        status_label.config(text=message)
    elif not solutions:
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


def _format_log_entry(entry):
    timestamp = entry["timestamp"].strftime("%H:%M")

    header_line = f"시간 {timestamp} · 장비 {entry['system']}"
    meta_line = (
        f"My ALT {entry['my_alt']:>5g}m  |  "
        f"Target ALT {entry['target_alt']:>5g}m  |  "
        f"Distance {entry['distance']:>6g}m"
    )

    lines = [
        (f"{header_line}\n", "time"),
        (f"{meta_line}\n", "meta"),
        ("┄" * 62 + "\n", "divider"),
        (f"{'LOW':<28}{'HIGH'}\n", "header"),
        (f"{'CH':>3}   {'MILL':>8}   {'ETA':>5}    {'CH':>3}   {'MILL':>8}   {'ETA':>5}\n", "subheader"),
    ]

    row_count = max(len(entry["low"]), len(entry["high"]), 1)
    for idx in range(row_count):
        low = entry["low"][idx] if idx < len(entry["low"]) else None
        high = entry["high"][idx] if idx < len(entry["high"]) else None

        def fmt(solution):
            if solution:
                return f"{solution['charge']:>3}   {solution['mill']:>8.2f}   {solution['eta']:>5.1f}"
            return f"{'—':>3}   {'—':>8}   {'—':>5}"

        lines.append((f"{fmt(low):<28}{fmt(high)}\n", "row"))

    lines.append(("\n", None))
    return lines


def render_log(log_text: tk.Text, entries, equipment_filter: str):
    log_text.configure(state="normal")
    log_text.delete("1.0", "end")

    filtered_entries = entries
    if equipment_filter and equipment_filter != "전체":
        filtered_entries = [e for e in entries if e["system"] == equipment_filter]

    if not filtered_entries:
        empty_msg = "선택한 조건에 맞는 기록이 없습니다."
        log_text.insert("end", empty_msg, ("meta",))
        log_text.configure(state="disabled")
        return

    for idx, entry in enumerate(filtered_entries):
        if idx > 0:
            log_text.insert("end", "\n", ("divider",))
            log_text.insert("end", "─" * 66 + "\n", ("divider",))
        for chunk, tag in _format_log_entry(entry):
            log_text.insert("end", chunk, (tag,) if tag else ())

    log_text.see("end")
    log_text.configure(state="disabled")


def log_calculation(
    log_text: tk.Text,
    log_entries: list,
    equipment_filter: tk.StringVar,
    my_alt: float,
    target_alt: float,
    distance: float,
    system: str,
    low_solutions,
    high_solutions,
):
    log_entries.append(
        {
            "timestamp": datetime.now(),
            "my_alt": my_alt,
            "target_alt": target_alt,
            "distance": distance,
            "system": system,
            "low": low_solutions,
            "high": high_solutions,
        }
    )
    render_log(log_text, log_entries, equipment_filter.get())


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
    log_entries,
    log_equipment_filter,
    log_text,
):
    try:
        my_alt = float(my_altitude_entry.get())
        target_alt = float(target_altitude_entry.get())
        distance = float(distance_entry.get())
    except ValueError:
        messagebox.showerror("입력 오류", "숫자만 입력하세요.")
        return

    # 고도 차이는 사수 고도에서 목표 고도를 뺀 값으로 계산한다
    # (목표가 더 높으면 음수, 더 낮으면 양수)
    altitude_delta = my_alt - target_alt
    system = system_var.get()
    system_charges = SYSTEM_TRAJECTORY_CHARGES.get(system, {})

    low_override = system_charges.get("low")
    high_override = system_charges.get("high")

    low_charges = low_override if low_override is not None else available_charges(system, "low")
    high_charges = high_override if high_override is not None else available_charges(system, "high")

    if low_charges:
        low_solutions = find_solutions(
            distance, altitude_delta, "low", system=system, limit=3, charges=low_charges
        )
        low_message = None
    else:
        low_solutions = []
        low_message = (
            "해당 장비는 저각 사격을 지원하지 않습니다"
            if low_override == []
            else "저각 데이터가 없습니다. rangeTables를 확인하세요"
        )

    if high_charges:
        high_solutions = find_solutions(
            distance, altitude_delta, "high", system=system, limit=3, charges=high_charges
        )
        high_message = None
    else:
        high_solutions = []
        high_message = (
            "해당 장비는 고각 사격을 지원하지 않습니다"
            if high_override == []
            else "고각 데이터가 없습니다. rangeTables를 확인하세요"
        )

    update_solution_table(low_rows, low_status, low_solutions, message=low_message)
    update_solution_table(high_rows, high_status, high_solutions, message=high_message)
    delta_label.config(text=f"고도 차이(사수-목표): {altitude_delta:+.1f} m")

    log_calculation(
        log_text,
        log_entries,
        log_equipment_filter,
        my_alt,
        target_alt,
        distance,
        system,
        low_solutions,
        high_solutions,
    )


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
        text="Made by Prue\nDiscord - prue._.0115",
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
        values=["M109A6", "M1129", "M119", "RH-70", "siala"],
        state="readonly",
        width=8,
        font=BODY_FONT,
    )
    system_select.grid(row=0, column=1, sticky="w", padx=(6, 0))

    input_card = ttk.Frame(main, style="Card.TFrame", padding=(16, 16, 16, 12))
    input_card.grid(row=1, column=0, sticky="ew")
    input_card.columnconfigure(1, weight=1)

    ttk.Label(input_card, text="my ALT (m)", style="CardBody.TLabel").grid(
        row=0, column=0, sticky="e", padx=(0, 10), pady=4
    )
    my_altitude_entry = ttk.Entry(input_card)
    my_altitude_entry.grid(row=0, column=1, sticky="ew", pady=4)

    ttk.Label(input_card, text="Target ALT (m)", style="CardBody.TLabel").grid(
        row=1, column=0, sticky="e", padx=(0, 10), pady=4
    )
    target_altitude_entry = ttk.Entry(input_card)
    target_altitude_entry.grid(row=1, column=1, sticky="ew", pady=4)

    ttk.Label(input_card, text="Distance (m)", style="CardBody.TLabel").grid(
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

    low_frame = ttk.Labelframe(results_card, text="LOW", style="Card.TLabelframe")
    low_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    high_frame = ttk.Labelframe(results_card, text="HIGH", style="Card.TLabelframe")
    high_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
    results_card.rowconfigure(0, weight=1)
    results_card.columnconfigure(0, weight=1)
    results_card.columnconfigure(1, weight=1)

    low_rows, low_status = build_solution_table(low_frame)
    high_rows, high_status = build_solution_table(high_frame)

    delta_label = ttk.Label(main, text="고도 차이: 계산 필요", style="Muted.TLabel")
    delta_label.grid(row=4, column=0, sticky="w", pady=(10, 0))

    bottom_bar = ttk.Frame(main, style="Main.TFrame")
    bottom_bar.grid(row=5, column=0, sticky="ew", pady=(8, 0))
    bottom_bar.columnconfigure(0, weight=1)
    log_toggle_button = ttk.Button(bottom_bar, text="기록", style="Secondary.TButton")
    log_toggle_button.grid(row=0, column=1, sticky="e")

    log_frame = ttk.Labelframe(root, text="기록", style="Card.TLabelframe", padding=14)
    log_frame.grid(row=0, column=1, sticky="nsw", padx=(0, 12), pady=12)
    log_frame.grid_remove()

    log_header = ttk.Frame(log_frame, style="Main.TFrame", padding=(0, 0, 0, 6))
    log_header.grid(row=0, column=0, columnspan=2, sticky="ew")
    log_header.columnconfigure(0, weight=1)
    log_header.columnconfigure(1, weight=0)

    ttk.Label(
        log_header,
        text="장비별 기록을 선택해 보세요",
        style="Muted.TLabel",
    ).grid(row=0, column=0, sticky="w")

    equipment_wrap = ttk.Frame(log_header, style="Card.TFrame")
    equipment_wrap.grid(row=0, column=1, sticky="e")
    ttk.Label(equipment_wrap, text="장비", style="Muted.TLabel").grid(row=0, column=0, sticky="e", padx=(0, 6))
    log_equipment_filter = tk.StringVar(value="전체")
    equipment_select = ttk.Combobox(
        equipment_wrap,
        textvariable=log_equipment_filter,
        values=["전체", "M109A6", "M1129", "M119", "RH-70", "siala"],
        state="readonly",
        width=8,
        font=BODY_FONT,
    )
    equipment_select.grid(row=0, column=1, sticky="e")
    log_text = tk.Text(
        log_frame,
        width=66,
        height=22,
        bg=CARD_BG,
        fg=TEXT_COLOR,
        font=MONO_FONT,
        relief="flat",
        borderwidth=1,
        highlightthickness=1,
        highlightbackground="#e5e5ea",
        highlightcolor="#e5e5ea",
        wrap="none",
        padx=14,
        pady=10,
    )
    log_text.configure(spacing1=2, spacing3=6)
    log_text.grid(row=1, column=0, sticky="nsew")
    log_text.configure(state="disabled")
    log_text.tag_configure("time", foreground=ACCENT_COLOR, font=(MONO_FONT[0], 12, "bold"))
    log_text.tag_configure("meta", foreground=MUTED_COLOR)
    log_text.tag_configure("header", font=(MONO_FONT[0], 11, "bold"))
    log_text.tag_configure("subheader", font=(MONO_FONT[0], 10, "bold"), foreground=MUTED_COLOR)
    log_text.tag_configure("row", spacing1=1, spacing3=1)
    log_text.tag_configure("divider", foreground="#d2d2d7")
    y_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    y_scroll.grid(row=1, column=1, sticky="nsw", padx=(8, 0))
    log_text.configure(yscrollcommand=y_scroll.set)

    def _on_mousewheel(event):
        log_text.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _on_linux_scroll(event):
        direction = -1 if event.num == 4 else 1
        log_text.yview_scroll(direction, "units")
        return "break"

    log_text.bind("<MouseWheel>", _on_mousewheel)
    log_text.bind("<Button-4>", _on_linux_scroll)
    log_text.bind("<Button-5>", _on_linux_scroll)
    log_frame.columnconfigure(0, weight=1)
    log_frame.columnconfigure(1, weight=0)
    log_frame.rowconfigure(1, weight=1)

    log_entries = []

    def _refresh_log(event=None):
        render_log(log_text, log_entries, log_equipment_filter.get())

    equipment_select.bind("<<ComboboxSelected>>", _refresh_log)

    log_visible = {"value": False}

    def toggle_log():
        log_visible["value"] = not log_visible["value"]
        if log_visible["value"]:
            log_frame.grid()
            log_toggle_button.configure(text="기록 닫기")
        else:
            log_frame.grid_remove()
            log_toggle_button.configure(text="기록")

    log_toggle_button.configure(command=toggle_log)

    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=0)
    root.rowconfigure(0, weight=1)
    main.columnconfigure(0, weight=1)
    main.rowconfigure(3, weight=1)

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
            log_entries,
            log_equipment_filter,
            log_text,
        )
    )

    return root


def main():
    root = build_gui()
    root.mainloop()


if __name__ == "__main__":
    main()
