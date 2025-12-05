import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk

import afcs.ui_theme as ui_theme
from afcs.device_profile import DeviceProfile, resolve_device_profile
from afcs.equipment import EquipmentRegistry
from afcs.log_view import log_calculation, render_log
from afcs.menu_bar import MenuBar
from afcs.range_tables import available_charges, find_solutions
from afcs.ui_theme import (
    ACCENT_COLOR,
    APP_BG,
    BODY_FONT,
    CARD_BG,
    BORDER_COLOR,
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
from afcs.versioning import (
    DEFAULT_GITHUB_REPO,
    fetch_latest_release,
    get_version,
    normalize_version_string,
    update_version,
)


def _sync_theme_constants():
    global APP_BG, CARD_BG, TEXT_COLOR, MUTED_COLOR, ACCENT_COLOR, BORDER_COLOR
    global INPUT_BG, INPUT_BORDER, HOVER_BG, PRESSED_BG, SECONDARY_ACTIVE, PRIMARY_PRESSED
    APP_BG = ui_theme.APP_BG
    CARD_BG = ui_theme.CARD_BG
    TEXT_COLOR = ui_theme.TEXT_COLOR
    MUTED_COLOR = ui_theme.MUTED_COLOR
    ACCENT_COLOR = ui_theme.ACCENT_COLOR
    BORDER_COLOR = ui_theme.BORDER_COLOR
    INPUT_BG = ui_theme.INPUT_BG
    INPUT_BORDER = ui_theme.INPUT_BORDER
    HOVER_BG = ui_theme.HOVER_BG
    PRESSED_BG = ui_theme.PRESSED_BG
    SECONDARY_ACTIVE = ui_theme.SECONDARY_ACTIVE
    PRIMARY_PRESSED = ui_theme.PRIMARY_PRESSED


set_theme("light")
_sync_theme_constants()
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
            row["ch"].config(text=f"{solution['charge']}", fg=ui_theme.TEXT_COLOR)
            row["mill"].config(text=f"{solution['mill']:.2f}", fg=ui_theme.TEXT_COLOR)
            row["eta"].config(text=f"{solution['eta']:.1f}", fg=ui_theme.TEXT_COLOR)
        else:
            row["ch"].config(text="—", fg=ui_theme.MUTED_COLOR)
            row["mill"].config(text="—", fg=ui_theme.MUTED_COLOR)
            row["eta"].config(text="—", fg=ui_theme.MUTED_COLOR)


def check_latest_release(root: tk.Tk, version_var: tk.StringVar, title_label: ttk.Label):
    def _prompt_update(release):
        latest_version = normalize_version_string(release.get("version") or "")
        current_version = normalize_version_string(version_var.get())
        if not latest_version or latest_version == current_version:
            return

        repo_slug = os.environ.get("AFCS_GITHUB_REPO", DEFAULT_GITHUB_REPO)
        release_url = release.get("url") or (
            f"https://github.com/{repo_slug}/releases/latest" if repo_slug else None
        )

        prompt_lines = [f"{latest_version} 최신 버전을 업데이트하시겠습니까?"]

        if not messagebox.askyesno("업데이트 확인", "\n".join(prompt_lines), parent=root):
            return

        normalized = update_version(latest_version)
        version_var.set(normalized)
        title_label.config(text=f"AFCS {normalized}")
        if release_url:
            webbrowser.open(release_url, new=1)

    def _worker():
        release = fetch_latest_release()
        if release:
            root.after(0, lambda: _prompt_update(release))

    threading.Thread(target=_worker, daemon=True).start()
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

    share_manager.share_results(
        {
            "system": system,
            "distance": distance,
            "altitude_delta": altitude_delta,
            "low": low_solutions,
            "high": high_solutions,
        }
    )


def apply_styles(root: tk.Tk):
    style = ttk.Style()
    style.theme_use("clam")

    style.configure("TFrame", background=ui_theme.APP_BG)
    style.configure("Main.TFrame", background=ui_theme.APP_BG)
    style.configure("Card.TFrame", background=ui_theme.CARD_BG, relief="flat", borderwidth=0)

    style.configure("Body.TLabel", background=ui_theme.APP_BG, foreground=ui_theme.TEXT_COLOR, font=ui_theme.BODY_FONT)
    style.configure("Muted.TLabel", background=ui_theme.APP_BG, foreground=ui_theme.MUTED_COLOR, font=ui_theme.BODY_FONT)
    style.configure("Title.TLabel", background=ui_theme.APP_BG, foreground=ui_theme.TEXT_COLOR, font=ui_theme.TITLE_FONT)
    style.configure("CardBody.TLabel", background=ui_theme.CARD_BG, foreground=ui_theme.TEXT_COLOR, font=ui_theme.BODY_FONT, anchor="w")
    style.configure("TableHeader.TLabel", background=ui_theme.CARD_BG, foreground=ui_theme.MUTED_COLOR, font=(ui_theme.BODY_FONT[0], 11, "bold"))
    style.configure("TableStatus.TLabel", background=ui_theme.CARD_BG, foreground=ui_theme.MUTED_COLOR, font=ui_theme.BODY_FONT)

    style.configure(
        "TEntry",
        fieldbackground=ui_theme.INPUT_BG,
        background=ui_theme.INPUT_BG,
        foreground=ui_theme.TEXT_COLOR,
        bordercolor=ui_theme.INPUT_BORDER,
        lightcolor=ui_theme.INPUT_BORDER,
        darkcolor=ui_theme.INPUT_BORDER,
        insertcolor=ui_theme.TEXT_COLOR,
        relief="solid",
    )

    style.configure(
        "TCombobox",
        fieldbackground=ui_theme.INPUT_BG,
        background=ui_theme.INPUT_BG,
        foreground=ui_theme.TEXT_COLOR,
        bordercolor=ui_theme.INPUT_BORDER,
        lightcolor=ui_theme.INPUT_BORDER,
        darkcolor=ui_theme.INPUT_BORDER,
        arrowcolor=ui_theme.TEXT_COLOR,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", ui_theme.INPUT_BG), ("!disabled", ui_theme.INPUT_BG)],
        foreground=[("readonly", ui_theme.TEXT_COLOR), ("!disabled", ui_theme.TEXT_COLOR)],
        bordercolor=[("focus", ui_theme.ACCENT_COLOR), ("!focus", ui_theme.INPUT_BORDER)],
        arrowcolor=[("disabled", ui_theme.MUTED_COLOR), ("!disabled", ui_theme.TEXT_COLOR)],
    )
    combobox_popup_options = {
        "background": ui_theme.INPUT_BG,
        "foreground": ui_theme.TEXT_COLOR,
        "selectBackground": ui_theme.ACCENT_COLOR,
        "selectForeground": "#ffffff",
        "borderColor": ui_theme.BORDER_COLOR,
    }
    for key, value in combobox_popup_options.items():
        root.option_add(f"*TCombobox*Listbox.{key}", value)
        root.option_add(f"*Combobox*Listbox.{key}", value)

    style.configure(
        "Primary.TButton",
        font=(ui_theme.BODY_FONT[0], 12, "bold"),
        foreground="#ffffff",
        background=ui_theme.ACCENT_COLOR,
        borderwidth=0,
        padding=(14, 10),
    )
    style.map(
        "Primary.TButton",
        background=[("active", ui_theme.ACCENT_COLOR), ("pressed", ui_theme.PRIMARY_PRESSED)],
        foreground=[("disabled", "#d1d1d6")],
    )

    style.configure(
        "Secondary.TButton",
        font=(ui_theme.BODY_FONT[0], 12, "bold"),
        foreground=ui_theme.ACCENT_COLOR,
        background=ui_theme.CARD_BG,
        borderwidth=1,
        padding=(14, 10),
        relief="solid",
    )
    style.map(
        "Secondary.TButton",
        background=[("active", ui_theme.SECONDARY_ACTIVE), ("pressed", ui_theme.HOVER_BG)],
        foreground=[("disabled", "#c7c7cc")],
    )

    style.configure(
        "ThemeToggle.TButton",
        padding=(6, 6),
        relief="solid",
        borderwidth=1,
        background=ui_theme.CARD_BG,
        foreground=ui_theme.ACCENT_COLOR,
    )
    style.map(
        "ThemeToggle.TButton",
        background=[("active", ui_theme.HOVER_BG), ("pressed", ui_theme.PRESSED_BG)],
    )

    style.configure(
        "Card.TLabelframe",
        background=ui_theme.CARD_BG,
        borderwidth=0,
        relief="flat",
        padding=(12, 12, 12, 10),
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=ui_theme.CARD_BG,
        foreground=ui_theme.TEXT_COLOR,
        font=(ui_theme.BODY_FONT[0], 12, "bold"),
    )


def refresh_solution_rows(rows):
    for row in rows:
        for key in ("ch", "mill", "eta"):
            widget = row[key]
            widget.configure(bg=ui_theme.CARD_BG)
            widget.configure(fg=ui_theme.MUTED_COLOR if widget.cget("text") == "—" else ui_theme.TEXT_COLOR)


def configure_log_canvas(canvas: tk.Canvas):
    canvas.configure(
        bg=ui_theme.CARD_BG,
        highlightbackground=ui_theme.BORDER_COLOR,
        highlightcolor=ui_theme.BORDER_COLOR,
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
    ui_theme.set_theme(theme_name)
    root.configure(bg=ui_theme.APP_BG)
    apply_styles(root)

    for rows in solution_tables:
        refresh_solution_rows(rows)

    configure_log_canvas(log_body.master)
    render_log(log_body, log_entries, log_equipment_filter.get())


def open_share_window(root: tk.Tk):
    if getattr(root, "share_window", None) and root.share_window.winfo_exists():
        root.share_window.deiconify()
        root.share_window.lift()
        return

    window = tk.Toplevel(root)
    window.title("사격 제원 공유")
    window.configure(bg=ui_theme.APP_BG)
    root.share_window = window

    container = ttk.Frame(window, padding=16, style="Main.TFrame")
    container.grid(row=0, column=0, sticky="nsew")
    container.columnconfigure(0, weight=1)

    status_var = tk.StringVar(value="공유가 꺼져 있습니다")
    code_var = tk.StringVar(value="—")
    payload_var = tk.StringVar(value=describe_shared_payload(None))

    ttk.Label(container, text="사격 제원 공유", style="Title.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    ttk.Label(
        container,
        text="계산 버튼을 누를 때마다 현재 방코드로 제원이 공유됩니다.",
        style="Muted.TLabel",
    ).grid(row=1, column=0, sticky="w", pady=(2, 10))

    status_row = ttk.Frame(container, style="Main.TFrame")
    status_row.grid(row=2, column=0, sticky="ew", pady=(0, 10))
    status_row.columnconfigure(1, weight=1)

    ttk.Label(status_row, text="상태", style="Body.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    ttk.Label(status_row, textvariable=status_var, style="Muted.TLabel").grid(
        row=0, column=1, sticky="w", padx=(8, 0)
    )

    code_row = ttk.Frame(container, style="Main.TFrame")
    code_row.grid(row=3, column=0, sticky="ew", pady=(0, 10))
    ttk.Label(code_row, text="현재 방코드", style="Body.TLabel").grid(
        row=0, column=0, sticky="w"
    )
    ttk.Label(code_row, textvariable=code_var, style="Title.TLabel").grid(
        row=0, column=1, sticky="w", padx=(8, 0)
    )

    controls = ttk.Frame(container, style="Main.TFrame")
    controls.grid(row=4, column=0, sticky="ew", pady=(0, 12))
    controls.columnconfigure(1, weight=1)

    join_code = tk.StringVar()

    def _on_create_room():
        code = share_manager.start_new_room()
        code_var.set(code)
        messagebox.showinfo("방코드 생성", f"일회용 방코드가 생성되었습니다:\n{code}")

    def _on_join_room():
        share_manager.join_room(join_code.get())
        if share_manager.active_code:
            code_var.set(share_manager.active_code)
            messagebox.showinfo("방 입장", f"{share_manager.active_code} 방에 입장했습니다.")
        else:
            messagebox.showwarning("방 입장 실패", "유효한 방코드를 입력하세요.")

    ttk.Button(controls, text="새 방코드 생성", style="Secondary.TButton", command=_on_create_room).grid(
        row=0, column=0, sticky="w", padx=(0, 8)
    )
    join_entry = ttk.Entry(controls, textvariable=join_code)
    join_entry.grid(row=0, column=1, sticky="ew")
    ttk.Button(controls, text="방 입장", style="Secondary.TButton", command=_on_join_room).grid(
        row=0, column=2, sticky="w", padx=(8, 0)
    )
    ttk.Button(
        controls,
        text="제원 공유 중단",
        style="Secondary.TButton",
        command=share_manager.stop_sharing,
    ).grid(row=0, column=3, sticky="w", padx=(8, 0))

    summary = ttk.Frame(container, style="Card.TFrame", padding=12)
    summary.grid(row=5, column=0, sticky="nsew")
    summary.columnconfigure(0, weight=1)
    tk.Label(
        summary,
        textvariable=payload_var,
        bg=ui_theme.CARD_BG,
        fg=ui_theme.TEXT_COLOR,
        justify="left",
        anchor="w",
        font=ui_theme.MONO_FONT,
    ).grid(row=0, column=0, sticky="nsew")

    def _refresh(payload, code, mode):
        if mode == "host":
            status_var.set("내가 만든 방에서 공유 중")
        elif mode == "guest":
            status_var.set("참여 중인 방에서 제원 수신")
        else:
            status_var.set("공유가 꺼져 있습니다")

        code_var.set(code if code else "—")
        payload_var.set(describe_shared_payload(payload))

    listener = share_manager.register_listener(_refresh)

    def _on_close():
        share_manager.unregister_listener(listener)
        window.destroy()
        root.share_window = None

    window.protocol("WM_DELETE_WINDOW", _on_close)
    window.resizable(False, False)

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


def build_gui(profile: DeviceProfile):
    root = tk.Tk()
    root.title("AFCS : Artillery Fire Control System")
    root.configure(bg=ui_theme.APP_BG)
    root.option_add("*Font", ui_theme.BODY_FONT)
    apply_styles(root)

    version_var = tk.StringVar(value=get_version())
    theme_var = tk.StringVar(value="light")

    main = ttk.Frame(root, style="Main.TFrame", padding=pad(20))
    main.grid(row=0, column=0, sticky="nsew")

    menu_bar = MenuBar(main, theme_var=theme_var)
    menu_bar.grid(row=0, column=0, sticky="w", pady=(0, 8))
    if menu_bar.light_icon_base is None or menu_bar.dark_icon_base is None:
        messagebox.showerror(
            "아이콘 로드 오류", "테마 아이콘을 불러오지 못했습니다. 기본 아이콘을 사용합니다.",
        )

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
    system_picker.grid(row=0, column=1, rowspan=2, sticky="e", padx=(pad(12), 0))
    ttk.Label(system_picker, text="장비", style="Body.TLabel").grid(row=0, column=0, sticky="e")
    system_select = ttk.Combobox(
        system_picker,
        textvariable=system_var,
        values=equipment_names,
        state="readonly",
        width=8,
        font=ui_theme.BODY_FONT,
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
    low_frame.grid(row=0, column=0, sticky="nsew", padx=(0, pad(8)))
    high_frame = ttk.Labelframe(results_card, text="HIGH", style="Card.TLabelframe")
    high_frame.grid(row=0, column=1, sticky="nsew", padx=(pad(8), 0))
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

    log_frame = ttk.Labelframe(
        root,
        text="기록",
        style="Card.TLabelframe",
        padding=pad(14),
    )
    log_grid = {
        "row": 0 if not profile.narrow_layout else 1,
        "column": 1 if not profile.narrow_layout else 0,
        "sticky": "nsew",
        "padx": (0, pad(12)) if not profile.narrow_layout else pad(12),
        "pady": pad(12),
    }
    log_frame.grid(**log_grid)
    log_frame.grid_remove()

    log_header = ttk.Frame(log_frame, style="Main.TFrame", padding=(0, 0, 0, pad(6)))
    log_header.grid(row=0, column=0, columnspan=2, sticky="ew")
    log_header.columnconfigure(0, weight=1)

    equipment_wrap = ttk.Frame(log_header, style="Card.TFrame")
    equipment_wrap.grid(row=0, column=0, sticky="e")
    ttk.Label(equipment_wrap, text="장비", style="Muted.TLabel").grid(
        row=0, column=0, sticky="e", padx=(0, pad(6))
    )
    log_equipment_filter = tk.StringVar(value="전체")
    equipment_select = ttk.Combobox(
        equipment_wrap,
        textvariable=log_equipment_filter,
        values=["전체", *equipment_names],
        state="readonly",
        width=8,
        font=ui_theme.BODY_FONT,
    )
    equipment_select.grid(row=0, column=1, sticky="e")
    log_canvas = tk.Canvas(
        log_frame,
        height=int(380 * profile.padding_scale),
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
        if profile.narrow_layout:
            root.columnconfigure(0, weight=1)
            root.columnconfigure(1, weight=0, minsize=0)
            root.rowconfigure(0, weight=1)
            root.rowconfigure(1, weight=1 if log_visible["value"] else 0)
            return

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
        else:
            log_frame.grid_remove()
        menu_bar.set_log_active(log_visible["value"])
        _sync_layout()

    menu_bar.log_button.configure(command=toggle_log)

    menu_bar.share_button.configure(command=lambda: open_share_window(root))

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

        menu_bar.apply_theme_icon(new_theme)

    menu_bar.theme_toggle.configure(command=toggle_theme)

    _sync_layout()
    root.rowconfigure(0, weight=1)
    main.columnconfigure(0, weight=1)
    main.rowconfigure(4, weight=1)

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

    root.after(500, lambda: check_latest_release(root, version_var, title))

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
