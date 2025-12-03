import os
import sys
import threading
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from afcs.equipment import EquipmentRegistry
from afcs.range_tables import available_charges, find_solutions
from afcs.ui_theme import (
    ACCENT_COLOR,
    APP_BG,
    BODY_FONT,
    CARD_BG,
    CH_WIDTH,
    ETA_WIDTH,
    HOVER_BG,
    ICONS_DIR,
    INPUT_BG,
    INPUT_BORDER,
    MILL_WIDTH,
    MONO_FONT,
    MUTED_COLOR,
    PRESSED_BG,
    PRIMARY_PRESSED,
    SECONDARY_ACTIVE,
    TEXT_COLOR,
    THEMES,
    TITLE_FONT,
    ensure_dpi_awareness,
    set_theme,
)
from afcs.versioning import get_latest_release_version, get_version, update_version


set_theme("light")
VERSION = get_version()
registry = EquipmentRegistry()


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


def prompt_version_update(root: tk.Tk, version_var: tk.StringVar, title_label: ttk.Label):
    new_version = simpledialog.askstring(
        "버전 업데이트",
        "새 버전을 입력하세요",
        initialvalue=version_var.get(),
        parent=root,
    )
    if new_version is None:
        return

    try:
        normalized = update_version(new_version)
    except ValueError:
        messagebox.showerror("버전 업데이트", "빈 문자열은 버전으로 사용할 수 없습니다.")
        return

    version_var.set(normalized)
    title_label.config(text=f"AFCS {normalized}")
    messagebox.showinfo("버전 업데이트", f"버전이 {normalized}(으)로 저장되었습니다.")


def check_latest_release_async(root: tk.Tk, version_var: tk.StringVar, title_label: ttk.Label):
    def _apply_latest(latest_version: str | None):
        if not latest_version:
            return

        current = version_var.get().strip()
        if latest_version == current:
            return

        if not root.winfo_exists():
            return

        if not messagebox.askyesno(
            "업데이트 확인",
            f"최신 릴리즈 {latest_version} 버전이 있습니다.\n"
            f"현재 버전은 {current}입니다. 업데이트할까요?",
            parent=root,
        ):
            return

        try:
            normalized = update_version(latest_version)
        except ValueError:
            messagebox.showerror("버전 업데이트", "빈 문자열은 버전으로 사용할 수 없습니다.")
            return

        version_var.set(normalized)
        title_label.config(text=f"AFCS {normalized}")
        messagebox.showinfo("버전 업데이트", f"버전이 {normalized}(으)로 저장되었습니다.")

    def _worker():
        try:
            latest = get_latest_release_version()
        except Exception as exc:  # pragma: no cover - best-effort network call
            print(f"최신 릴리즈 조회 실패: {exc}")
            return

        root.after(0, lambda: _apply_latest(latest))

    threading.Thread(target=_worker, daemon=True).start()


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
    
    altitude_delta = my_alt - target_alt
    system = system_var.get()
    equipment = registry.get(system)
    if equipment is None:
        messagebox.showerror("장비 오류", f"'{system}' 장비 정보를 찾을 수 없습니다.")
        return

    equipment_charges = equipment.charges_override
    low_override = equipment_charges.get("low") if equipment_charges else None
    high_override = equipment_charges.get("high") if equipment_charges else None

    low_charges = (
        low_override if low_override is not None else available_charges(equipment, "low")
    )
    high_charges = (
        high_override if high_override is not None else available_charges(equipment, "high")
    )

    if low_charges:
        low_solutions = find_solutions(
            distance,
            altitude_delta,
            "low",
            equipment=equipment,
            limit=3,
            charges=low_charges,
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
            distance,
            altitude_delta,
            "high",
            equipment=equipment,
            limit=3,
            charges=high_charges,
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

    version_var = tk.StringVar(value=VERSION)

    main = ttk.Frame(root, style="Main.TFrame", padding=20)
    main.grid(row=0, column=0, sticky="nsew")

    header = ttk.Frame(main, style="Main.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    header.columnconfigure(0, weight=1)
    title = ttk.Label(header, text=f"AFCS {version_var.get()}", style="Title.TLabel")
    title.grid(row=0, column=0, sticky="w")
    subtitle = ttk.Label(
        header,
        text="Made by Prue\nDiscord - prue._.0115",
        style="Muted.TLabel",
    )
    subtitle.grid(row=1, column=0, sticky="w")

    equipment_names = registry.names
    default_system = equipment_names[0] if equipment_names else ""
    system_var = tk.StringVar(value=default_system)
    system_picker = ttk.Frame(header, style="Main.TFrame")
    system_picker.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 0))
    ttk.Label(system_picker, text="장비", style="Body.TLabel").grid(row=0, column=0, sticky="e")
    system_select = ttk.Combobox(
        system_picker,
        textvariable=system_var,
        values=equipment_names,
        state="readonly",
        width=8,
        font=BODY_FONT,
    )
    system_select.grid(row=0, column=1, sticky="w", padx=(6, 0))

    update_version_button = ttk.Button(
        header,
        text="버전 업데이트",
        style="Secondary.TButton",
        command=lambda: prompt_version_update(root, version_var, title),
    )
    update_version_button.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))
    root.after(500, lambda: check_latest_release_async(root, version_var, title))

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
        values=["전체", *equipment_names],
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
            root_width = max(root.winfo_width(), root.winfo_reqwidth())

            content_width = log_body.winfo_reqwidth()
            scrollbar_width = y_scroll.winfo_reqwidth()
            table_width = max(results_card.winfo_width(), results_card.winfo_reqwidth())
            desired_width = max(table_width, content_width + scrollbar_width)

            if desired_width > log_column_width["value"]:
                log_column_width["value"] = desired_width

            capped_width = min(log_column_width["value"], max(root_width // 2, desired_width))

            root.columnconfigure(0, weight=1)
            root.columnconfigure(1, weight=0, minsize=capped_width)
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


def resource_path(relative_path):
    """ PyInstaller로 빌드된 경우 올바른 경로 반환 """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def main():
    ensure_dpi_awareness()
    root = build_gui()
    
    # tkinter 윈도우 아이콘 설정
    try:
        icon_path = resource_path('icons/afcs.ico')
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"아이콘 로드 실패: {e}")
    
    root.mainloop()


if __name__ == "__main__":
    main()
