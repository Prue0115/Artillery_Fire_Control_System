import csv
import math
from bisect import bisect_left
from datetime import datetime
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


THEMES = {
    "light": {
        "APP_BG": "#f5f5f7",
        "CARD_BG": "#ffffff",
        "TEXT_COLOR": "#1d1d1f",
        "MUTED_COLOR": "#6e6e73",
        "ACCENT_COLOR": "#007aff",
        "BORDER_COLOR": "#e5e5ea",
        "INPUT_BG": "#ffffff",
        "INPUT_BORDER": "#d1d1d6",
        "HOVER_BG": "#e6f0ff",
        "PRESSED_BG": "#d6e5ff",
        "SECONDARY_ACTIVE": "#f0f4ff",
        "PRIMARY_PRESSED": "#0060df",
    },
    "dark": {
        "APP_BG": "#1c1c1e",
        "CARD_BG": "#2c2c2e",
        "TEXT_COLOR": "#f2f2f7",
        "MUTED_COLOR": "#8e8e93",
        "ACCENT_COLOR": "#0a84ff",
        "BORDER_COLOR": "#3a3a3c",
        "INPUT_BG": "#2c2c2e",
        "INPUT_BORDER": "#4a4a4c",
        "HOVER_BG": "#0f2f55",
        "PRESSED_BG": "#0c2441",
        "SECONDARY_ACTIVE": "#2f2f33",
        "PRIMARY_PRESSED": "#07294d",
    },
}

APP_BG = ""
CARD_BG = ""
TEXT_COLOR = ""
MUTED_COLOR = ""
ACCENT_COLOR = ""
BORDER_COLOR = ""
INPUT_BG = ""
INPUT_BORDER = ""
HOVER_BG = ""
PRESSED_BG = ""
SECONDARY_ACTIVE = ""
PRIMARY_PRESSED = ""


def set_theme(theme_name: str):
    theme = THEMES[theme_name]
    global APP_BG, CARD_BG, TEXT_COLOR, MUTED_COLOR, ACCENT_COLOR, BORDER_COLOR
    global INPUT_BG, INPUT_BORDER, HOVER_BG, PRESSED_BG, SECONDARY_ACTIVE, PRIMARY_PRESSED
    APP_BG = theme["APP_BG"]
    CARD_BG = theme["CARD_BG"]
    TEXT_COLOR = theme["TEXT_COLOR"]
    MUTED_COLOR = theme["MUTED_COLOR"]
    ACCENT_COLOR = theme["ACCENT_COLOR"]
    BORDER_COLOR = theme["BORDER_COLOR"]
    INPUT_BG = theme["INPUT_BG"]
    INPUT_BORDER = theme["INPUT_BORDER"]
    HOVER_BG = theme["HOVER_BG"]
    PRESSED_BG = theme["PRESSED_BG"]
    SECONDARY_ACTIVE = theme["SECONDARY_ACTIVE"]
    PRIMARY_PRESSED = theme["PRIMARY_PRESSED"]


set_theme("light")
TITLE_FONT = ("SF Pro Display", 18, "bold")
BODY_FONT = ("SF Pro Text", 12)
MONO_FONT = ("SF Mono", 12)
CH_WIDTH = 4
MILL_WIDTH = 12
ETA_WIDTH = 6

MIL_PER_DEG = 6400 / 360.0
BASE_DIR = Path(__file__).parent
RANGE_TABLE_DIR = BASE_DIR / "rangeTables"
# 아이콘 폴더 경로 추가
ICONS_DIR = BASE_DIR / "icons"
SYSTEM_FILE_PREFIX = {
    "M109A6": "M109A6",
    "M1129": "M1129",
    "M119": "M119",
    "RM-70": "RM70",
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
def render_log(log_body: ttk.Frame, entries, equipment_filter: str):
    for child in log_body.winfo_children():
        child.destroy()

    filtered_entries = sorted(entries, key=lambda e: e["timestamp"], reverse=True)
    if equipment_filter and equipment_filter != "전체":
        filtered_entries = [
            e for e in filtered_entries if e["system"] == equipment_filter
        ]

    if not filtered_entries:
        tk.Label(
            log_body,
            text="선택한 조건에 맞는 기록이 없습니다.",
            bg=CARD_BG,
            fg=MUTED_COLOR,
            font=MONO_FONT,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=8)
        return

    for idx, entry in enumerate(filtered_entries):
        card = ttk.Frame(log_body, style="Card.TFrame")
        card.grid(row=idx * 2, column=0, sticky="ew", padx=0, pady=(0, 6))
        card.columnconfigure(0, weight=1)

        tk.Label(
            card,
            text=f"시간 {entry['timestamp'].strftime('%H:%M')} · 장비 {entry['system']}",
            bg=CARD_BG,
            fg=ACCENT_COLOR,
            font=(MONO_FONT[0], 12, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 2))

        tk.Label(
            card,
            text=(
                f"My ALT {entry['my_alt']:>5g}m  |  "
                f"Target ALT {entry['target_alt']:>5g}m  |  "
                f"Distance {entry['distance']:>6g}m"
            ),
            bg=CARD_BG,
            fg=MUTED_COLOR,
            font=MONO_FONT,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

        table = ttk.Frame(card, style="Card.TFrame")
        table.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        for col in range(7):
            weight = 0 if col == 3 else 1
            table.grid_columnconfigure(col, weight=weight, minsize=0)
        table.grid_columnconfigure(3, minsize=16)

        def _header(text, column, columnspan=1):
            tk.Label(
                table,
                text=text,
                bg=CARD_BG,
                fg=TEXT_COLOR,
                font=(MONO_FONT[0], 11, "bold"),
                anchor="w",
            ).grid(row=0, column=column, columnspan=columnspan, sticky="w")

        _header("LOW", 0, 3)
        _header("HIGH", 4, 3)

        def _column_header(label_text, column, width):
            tk.Label(
                table,
                text=label_text,
                width=width,
                bg=CARD_BG,
                fg=MUTED_COLOR,
                font=(MONO_FONT[0], 10, "bold"),
                anchor="w",
            ).grid(row=1, column=column, sticky="w")

        for idx_col, (label_text, width) in enumerate(
            (("CH", CH_WIDTH), ("MILL", MILL_WIDTH), ("ETA", ETA_WIDTH))
        ):
            _column_header(label_text, idx_col, width)
            _column_header(label_text, idx_col + 4, width)

        low_sorted = sorted(entry["low"], key=lambda s: s["charge"])
        high_sorted = sorted(entry["high"], key=lambda s: s["charge"])

        low_map = {solution["charge"]: solution for solution in low_sorted}
        high_map = {solution["charge"]: solution for solution in high_sorted}
        charges = sorted(set(low_map.keys()) | set(high_map.keys())) or [None]

        def _row(value, width, row_idx, column):
            tk.Label(
                table,
                text=value,
                width=width,
                bg=CARD_BG,
                fg=MUTED_COLOR if value == "—" else TEXT_COLOR,
                font=MONO_FONT,
                anchor="w",
            ).grid(row=row_idx, column=column, sticky="w", pady=(2, 0))

        for row_idx, charge in enumerate(charges, start=2):
            low = low_map.get(charge)
            high = high_map.get(charge)

            def fmt(solution, key, width):
                if not solution:
                    return "—"
                if key == "mill":
                    return f"{solution[key]:.2f}"
                if key == "eta":
                    return f"{solution[key]:.1f}"
                return str(solution[key])

            for col_offset, key, width in (
                (0, "charge", CH_WIDTH),
                (1, "mill", MILL_WIDTH),
                (2, "eta", ETA_WIDTH),
            ):
                _row(fmt(low, key, width), width, row_idx, col_offset)
                _row(fmt(high, key, width), width, row_idx, col_offset + 4)

        if idx < len(filtered_entries) - 1:
            ttk.Separator(log_body, orient="horizontal").grid(
                row=idx * 2 + 1, column=0, sticky="ew", pady=4
            )


def log_calculation(
    log_body: ttk.Frame,
    log_entries: list,
    equipment_filter: tk.StringVar,
    my_alt: float,
    target_alt: float,
    distance: float,
    system: str,
    low_solutions,
    high_solutions,
    sync_layout=None,
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
    render_log(log_body, log_entries, equipment_filter.get())
    if sync_layout:
        sync_layout()


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
    log_body,
    sync_layout=None,
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
        log_body,
        log_entries,
        log_equipment_filter,
        my_alt,
        target_alt,
        distance,
        system,
        low_solutions,
        high_solutions,
        sync_layout=sync_layout,
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
    style.configure("Title.TLabel", background=APP_BG, foreground=TEXT_COLOR, font=TITLE_FONT)
    style.configure("CardBody.TLabel", background=CARD_BG, foreground=TEXT_COLOR, font=BODY_FONT, anchor="w")
    style.configure("TableHeader.TLabel", background=CARD_BG, foreground=MUTED_COLOR, font=(BODY_FONT[0], 11, "bold"))
    style.configure("TableStatus.TLabel", background=CARD_BG, foreground=MUTED_COLOR, font=BODY_FONT)

    style.configure(
        "TEntry",
        fieldbackground=INPUT_BG,
        background=INPUT_BG,
        foreground=TEXT_COLOR,
        bordercolor=INPUT_BORDER,
        lightcolor=INPUT_BORDER,
        darkcolor=INPUT_BORDER,
        insertcolor=TEXT_COLOR,
        relief="solid",
    )

    style.configure(
        "TCombobox",
        fieldbackground=INPUT_BG,
        background=INPUT_BG,
        foreground=TEXT_COLOR,
        bordercolor=INPUT_BORDER,
        lightcolor=INPUT_BORDER,
        darkcolor=INPUT_BORDER,
        arrowcolor=TEXT_COLOR,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", INPUT_BG), ("!disabled", INPUT_BG)],
        foreground=[("readonly", TEXT_COLOR), ("!disabled", TEXT_COLOR)],
        bordercolor=[("focus", ACCENT_COLOR), ("!focus", INPUT_BORDER)],
        arrowcolor=[("disabled", MUTED_COLOR), ("!disabled", TEXT_COLOR)],
    )
    combobox_popup_options = {
        "background": INPUT_BG,
        "foreground": TEXT_COLOR,
        "selectBackground": ACCENT_COLOR,
        "selectForeground": "#ffffff",
        "borderColor": BORDER_COLOR,
    }
    for key, value in combobox_popup_options.items():
        root.option_add(f"*TCombobox*Listbox.{key}", value)
        root.option_add(f"*Combobox*Listbox.{key}", value)

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
        background=[("active", ACCENT_COLOR), ("pressed", PRIMARY_PRESSED)],
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
        background=[("active", SECONDARY_ACTIVE), ("pressed", HOVER_BG)],
        foreground=[("disabled", "#c7c7cc")],
    )

    style.configure(
        "ThemeToggle.TButton",
        padding=(6, 6),
        relief="solid",
        borderwidth=1,
        background=CARD_BG,
        foreground=ACCENT_COLOR,
    )
    style.map(
        "ThemeToggle.TButton",
        background=[("active", HOVER_BG), ("pressed", PRESSED_BG)],
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


def refresh_solution_rows(rows):
    for row in rows:
        for key in ("ch", "mill", "eta"):
            widget = row[key]
            widget.configure(bg=CARD_BG)
            widget.configure(fg=MUTED_COLOR if widget.cget("text") == "—" else TEXT_COLOR)


def configure_log_canvas(canvas: tk.Canvas):
    canvas.configure(
        bg=CARD_BG,
        highlightbackground=BORDER_COLOR,
        highlightcolor=BORDER_COLOR,
    )


def apply_theme(
    root: tk.Tk,
    theme_name: str,
    *,
    solution_tables,
    log_body: ttk.Frame,
    log_entries,
    log_equipment_filter,
):
    set_theme(theme_name)
    root.configure(bg=APP_BG)
    apply_styles(root)

    for rows in solution_tables:
        refresh_solution_rows(rows)

    configure_log_canvas(log_body.master)
    render_log(log_body, log_entries, log_equipment_filter.get())


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
    root.title("AFCS : Artillery Fire Control System")
    root.configure(bg=APP_BG)
    root.option_add("*Font", BODY_FONT)
    apply_styles(root)

    main = ttk.Frame(root, style="Main.TFrame", padding=20)
    main.grid(row=0, column=0, sticky="nsew")

    header = ttk.Frame(main, style="Main.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    header.columnconfigure(0, weight=1)
    title = ttk.Label(header, text="AFCS v1.1", style="Title.TLabel")
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
        values=["M109A6", "M1129", "M119", "RM-70", "siala"],
        state="readonly",
        width=8,
        font=BODY_FONT,
    )
    system_select.grid(row=0, column=1, sticky="w", padx=(6, 0))

    input_card = ttk.Frame(main, style="Card.TFrame", padding=(16, 16, 16, 12))
    input_card.grid(row=1, column=0, sticky="ew")
    input_card.columnconfigure(1, weight=1)

    ttk.Label(input_card, text="My ALT (m)", style="CardBody.TLabel").grid(
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

    theme_var = tk.StringVar(value="light")

    bottom_bar = ttk.Frame(main, style="Main.TFrame")
    bottom_bar.grid(row=5, column=0, sticky="ew", pady=(8, 0))
    bottom_bar.columnconfigure(0, weight=1)

    # PNG 아이콘 로드
    try:
        root.light_icon_base = tk.PhotoImage(file=str(ICONS_DIR / "Light Mode.png"))
        root.dark_icon_base = tk.PhotoImage(file=str(ICONS_DIR / "Dark Mode.png"))
    except Exception as e:
        messagebox.showerror("아이콘 로드 오류", f"테마 아이콘을 불러오지 못했습니다.\n{e}")
        root.light_icon_base = root.dark_icon_base = None

    theme_toggle = ttk.Button(
        bottom_bar,
        text="" if root.light_icon_base else "🌞",
        style="ThemeToggle.TButton",
        image=root.light_icon_base if root.light_icon_base else None,
        cursor="hand2",
    )
    theme_toggle.grid(row=0, column=1, sticky="e", padx=(0, 8))

    log_toggle_button = ttk.Button(bottom_bar, text="기록", style="Secondary.TButton")
    log_toggle_button.grid(row=0, column=2, sticky="e")

    log_frame = ttk.Labelframe(root, text="기록", style="Card.TLabelframe", padding=14)
    log_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
    log_frame.grid_remove()

    log_header = ttk.Frame(log_frame, style="Main.TFrame", padding=(0, 0, 0, 6))
    log_header.grid(row=0, column=0, columnspan=2, sticky="ew")
    log_header.columnconfigure(0, weight=1)

    equipment_wrap = ttk.Frame(log_header, style="Card.TFrame")
    equipment_wrap.grid(row=0, column=0, sticky="e")
    ttk.Label(equipment_wrap, text="장비", style="Muted.TLabel").grid(row=0, column=0, sticky="e", padx=(0, 6))
    log_equipment_filter = tk.StringVar(value="전체")
    equipment_select = ttk.Combobox(
        equipment_wrap,
        textvariable=log_equipment_filter,
        values=["전체", "M109A6", "M1129", "M119", "RM-70", "siala"],
        state="readonly",
        width=8,
        font=BODY_FONT,
    )
    equipment_select.grid(row=0, column=1, sticky="e")
    log_canvas = tk.Canvas(
        log_frame,
        height=380,
        highlightthickness=1,
        borderwidth=0,
    )
    configure_log_canvas(log_canvas)
    log_canvas.grid(row=1, column=0, sticky="nsew")

    log_body = ttk.Frame(log_canvas, style="Card.TFrame")
    log_window = log_canvas.create_window((0, 0), window=log_body, anchor="nw")

    y_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=log_canvas.yview)
    y_scroll.grid(row=1, column=1, sticky="nsw", padx=(8, 0))
    log_canvas.configure(yscrollcommand=y_scroll.set)

    def _on_frame_configure(event):
        log_canvas.configure(scrollregion=log_canvas.bbox("all"))

    def _on_canvas_configure(event):
        log_canvas.itemconfigure(log_window, width=event.width)

    log_body.bind("<Configure>", _on_frame_configure)
    log_canvas.bind("<Configure>", _on_canvas_configure)

    def _can_scroll():
        region = log_canvas.bbox("all")
        if not region:
            return False
        content_height = region[3] - region[1]
        return content_height > log_canvas.winfo_height()

    def _on_mousewheel(event):
        if not _can_scroll():
            return "break"
        log_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _on_linux_scroll(event):
        if not _can_scroll():
            return "break"
        direction = -1 if event.num == 4 else 1
        log_canvas.yview_scroll(direction, "units")
        return "break"

    def _bind_scrollwheel(widget):
        widget.bind_all("<MouseWheel>", _on_mousewheel)
        widget.bind_all("<Button-4>", _on_linux_scroll)
        widget.bind_all("<Button-5>", _on_linux_scroll)

    def _unbind_scrollwheel(widget):
        widget.unbind_all("<MouseWheel>")
        widget.unbind_all("<Button-4>")
        widget.unbind_all("<Button-5>")

    def _on_scroll_area_enter(event):
        _bind_scrollwheel(event.widget)

    def _on_scroll_area_leave(event):
        _unbind_scrollwheel(event.widget)

    for scroll_area in (log_canvas, log_body, log_frame):
        scroll_area.bind("<Enter>", _on_scroll_area_enter)
        scroll_area.bind("<Leave>", _on_scroll_area_leave)
    log_frame.columnconfigure(0, weight=1)
    log_frame.columnconfigure(1, weight=0)
    log_frame.rowconfigure(1, weight=1)

    log_entries = []
    log_visible = {"value": False}

    log_column_width = {"value": 0}

    def _sync_layout():
        if log_visible["value"]:
            log_frame.update_idletasks()
            content_width = log_body.winfo_reqwidth()
            scrollbar_width = y_scroll.winfo_reqwidth()
            table_width = max(results_card.winfo_width(), results_card.winfo_reqwidth())
            desired_width = max(table_width, content_width + scrollbar_width)
            if desired_width > log_column_width["value"]:
                log_column_width["value"] = desired_width
            root.columnconfigure(0, weight=1)
            root.columnconfigure(1, weight=0, minsize=log_column_width["value"])
        else:
            root.columnconfigure(0, weight=1)
            root.columnconfigure(1, weight=0, minsize=0)

    def _refresh_log(event=None):
        render_log(log_body, log_entries, log_equipment_filter.get())
        _sync_layout()

    _refresh_log()

    equipment_select.bind("<<ComboboxSelected>>", _refresh_log)

    def toggle_log():
        log_visible["value"] = not log_visible["value"]
        if log_visible["value"]:
            log_frame.grid()
            log_toggle_button.configure(text="기록 닫기")
        else:
            log_frame.grid_remove()
            log_toggle_button.configure(text="기록")
        _sync_layout()

    log_toggle_button.configure(command=toggle_log)

    def toggle_theme():
        new_theme = "dark" if theme_var.get() == "light" else "light"
        theme_var.set(new_theme)
        apply_theme(
            root,
            new_theme,
            solution_tables=[low_rows, high_rows],
            log_body=log_body,
            log_entries=log_entries,
            log_equipment_filter=log_equipment_filter,
        )
        # 현재 상태에 맞게 아이콘 갱신
        _apply_toggle_icon(new_theme)

    theme_toggle.configure(command=toggle_theme)

    def _apply_toggle_icon(mode: str):
        if mode == "light":
            img = root.light_icon_base if root.light_icon_base else None
            theme_toggle.configure(image=img, text="" if img else "🌞")
        else:
            img = root.dark_icon_base if root.dark_icon_base else None
            theme_toggle.configure(image=img, text="" if img else "🌙")

    _sync_layout()
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
            log_body,
            _sync_layout,
        )
    )

    return root


def main():
    root = build_gui()
    root.mainloop()


if __name__ == "__main__":
    main()
