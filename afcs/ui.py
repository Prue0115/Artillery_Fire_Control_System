import os
import sys
from typing import Callable, Sequence, cast

import tkinter as tk
from tkinter import messagebox, ttk

from .calculations import (
    SYSTEM_TRAJECTORY_CHARGES,
    Solution,
    available_charges,
    find_solutions,
)
from .config import ICONS_DIR
from .logs import LogEntry, log_calculation, render_log
from .theme import (
    APP_BG,
    BODY_FONT,
    apply_styles,
    configure_log_canvas,
    ensure_dpi_awareness,
    refresh_solution_rows,
    set_theme,
)
from .update import prompt_for_updates
from .version import __version__


SolutionRow = dict[str, ttk.Label]
SolutionRows = list[SolutionRow]


set_theme("light")


def update_solution_table(
    rows: Sequence[SolutionRow],
    status_label: ttk.Label,
    solutions: Sequence[Solution],
    message: str | None = None,
) -> None:
    if message:
        status_label.config(text=message)
    elif not solutions:
        status_label.config(text="지원 범위 밖입니다")
    else:
        status_label.config(text="")

    for idx, row in enumerate(rows):
        if idx < len(solutions):
            solution = solutions[idx]
            row["ch"].config(text=f"{solution['charge']}", style="TableCell.TLabel")
            row["mill"].config(text=f"{solution['mill']:.2f}", style="TableCell.TLabel")
            row["eta"].config(text=f"{solution['eta']:.1f}", style="TableCell.TLabel")
        else:
            row["ch"].config(text="—", style="TableCellMuted.TLabel")
            row["mill"].config(text="—", style="TableCellMuted.TLabel")
            row["eta"].config(text="—", style="TableCellMuted.TLabel")


def calculate_and_display(
    system_var: tk.StringVar,
    low_rows: Sequence[SolutionRow],
    high_rows: Sequence[SolutionRow],
    low_status: ttk.Label,
    high_status: ttk.Label,
    delta_label: ttk.Label,
    my_altitude_entry: ttk.Entry,
    target_altitude_entry: ttk.Entry,
    distance_entry: ttk.Entry,
    log_entries: list[LogEntry],
    log_equipment_filter: tk.StringVar,
    log_body: ttk.Frame,
    sync_layout: Callable[[], None] | None = None,
) -> None:
    try:
        my_alt = float(my_altitude_entry.get())
        target_alt = float(target_altitude_entry.get())
        distance = float(distance_entry.get())
    except ValueError:
        messagebox.showerror("입력 오류", "숫자만 입력하세요.")
        return

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


def apply_theme(
    root: tk.Tk,
    theme_name: str,
    *,
    solution_tables: Sequence[Sequence[SolutionRow]],
    log_body: ttk.Frame,
    log_entries: list[LogEntry],
    log_equipment_filter: tk.StringVar,
) -> None:
    set_theme(theme_name)
    root.configure(bg=APP_BG)
    apply_styles(root)

    for rows in solution_tables:
        refresh_solution_rows(rows)

    configure_log_canvas(cast(tk.Canvas, log_body.master))
    render_log(log_body, log_entries, log_equipment_filter.get())


def build_solution_table(parent: tk.Misc) -> tuple[SolutionRows, ttk.Label]:
    table = ttk.Frame(parent, style="Card.TFrame")
    table.columnconfigure(0, weight=1)
    table.columnconfigure(1, weight=3)
    table.columnconfigure(2, weight=2)

    headers = ["CH", "MILL", "ETA"]
    for col, text in enumerate(headers):
        ttk.Label(table, text=text, style="TableHeader.TLabel").grid(row=0, column=col, sticky="w", padx=(0, 8))

    rows: SolutionRows = []
    for i in range(3):
        ch = ttk.Label(table, text="—", style="TableCellMuted.TLabel", anchor="w", width=4)
        mill = ttk.Label(table, text="—", style="TableCellMuted.TLabel", anchor="w", width=12)
        eta = ttk.Label(table, text="—", style="TableCellMuted.TLabel", anchor="w", width=6)

        ch.grid(row=i + 1, column=0, sticky="w", pady=3)
        mill.grid(row=i + 1, column=1, sticky="w", pady=3)
        eta.grid(row=i + 1, column=2, sticky="w", pady=3)

        rows.append({"ch": ch, "mill": mill, "eta": eta})

    status = ttk.Label(parent, text="계산 결과가 여기에 표시됩니다", style="TableStatus.TLabel")
    status.grid(row=1, column=0, sticky="w", pady=(8, 0))

    table.grid(row=0, column=0, sticky="nsew")
    parent.columnconfigure(0, weight=1)
    return rows, status


def build_gui() -> tk.Tk:
    root = tk.Tk()
    root.title("AFCS : Artillery Fire Control System")
    root.configure(bg=APP_BG)
    root.option_add("*Font", " ".join(str(part) for part in BODY_FONT))
    apply_styles(root)

    main = ttk.Frame(root, style="Main.TFrame", padding=20)
    main.grid(row=0, column=0, sticky="nsew")

    header = ttk.Frame(main, style="Main.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    header.columnconfigure(0, weight=1)
    header.columnconfigure(2, weight=0)
    title = ttk.Label(header, text=f"AFCS {__version__}", style="Title.TLabel")
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

    theme_icons: dict[str, tk.PhotoImage | None] = {"light": None, "dark": None}

    try:
        theme_icons["light"] = tk.PhotoImage(file=str(ICONS_DIR / "Light Mode.png"))
        theme_icons["dark"] = tk.PhotoImage(file=str(ICONS_DIR / "Dark Mode.png"))
    except Exception as e:
        messagebox.showerror("아이콘 로드 오류", f"테마 아이콘을 불러오지 못했습니다.\n{e}")

    theme_toggle = ttk.Button(
        bottom_bar,
        text="" if theme_icons["light"] else "🌞",
        style="ThemeToggle.TButton",
        image=theme_icons["light"] or "",
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
    log_canvas: tk.Canvas = tk.Canvas(
        log_frame,
        height=380,
        highlightthickness=1,
        borderwidth=0,
    )
    configure_log_canvas(log_canvas)
    log_canvas.grid(row=1, column=0, sticky="nsew")

    log_body = ttk.Frame(log_canvas, style="Card.TFrame")
    log_window = log_canvas.create_window((0, 0), window=log_body, anchor="nw")

    y_scroll = ttk.Scrollbar(
        log_frame, orient="vertical", command=lambda *args: log_canvas.yview(*args)
    )
    y_scroll.grid(row=1, column=1, sticky="nsw", padx=(8, 0))
    log_canvas.configure(yscrollcommand=y_scroll.set)

    def _on_frame_configure(event: tk.Event) -> None:
        log_canvas.configure(scrollregion=log_canvas.bbox("all"))

    def _on_canvas_configure(event: tk.Event) -> None:
        log_canvas.itemconfigure(log_window, width=event.width)

    log_body.bind("<Configure>", _on_frame_configure)
    log_canvas.bind("<Configure>", _on_canvas_configure)

    def _can_scroll() -> bool:
        region = log_canvas.bbox("all")
        if not region:
            return False
        content_height = region[3] - region[1]
        return content_height > log_canvas.winfo_height()

    def _on_mousewheel(event: tk.Event) -> str:
        if not _can_scroll():
            return "break"
        log_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _on_linux_scroll(event: tk.Event) -> str:
        if not _can_scroll():
            return "break"
        direction = -1 if event.num == 4 else 1
        log_canvas.yview_scroll(direction, "units")
        return "break"

    def _bind_scrollwheel(widget: tk.Misc) -> None:
        widget.bind_all("<MouseWheel>", _on_mousewheel)
        widget.bind_all("<Button-4>", _on_linux_scroll)
        widget.bind_all("<Button-5>", _on_linux_scroll)

    def _unbind_scrollwheel(widget: tk.Misc) -> None:
        widget.unbind_all("<MouseWheel>")
        widget.unbind_all("<Button-4>")
        widget.unbind_all("<Button-5>")

    def _on_scroll_area_enter(event: tk.Event) -> None:
        _bind_scrollwheel(event.widget)

    def _on_scroll_area_leave(event: tk.Event) -> None:
        _unbind_scrollwheel(event.widget)

    for scroll_area in (log_canvas, log_body, log_frame):
        scroll_area.bind("<Enter>", _on_scroll_area_enter)
        scroll_area.bind("<Leave>", _on_scroll_area_leave)
    log_frame.columnconfigure(0, weight=1)
    log_frame.columnconfigure(1, weight=0)
    log_frame.rowconfigure(1, weight=1)

    log_entries: list[LogEntry] = []
    log_visible = {"value": False}

    log_column_width = {"value": 0}

    def _sync_layout() -> None:
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

    def _refresh_log(event: tk.Event | None = None) -> None:
        render_log(log_body, log_entries, log_equipment_filter.get())
        _sync_layout()

    _refresh_log()

    equipment_select.bind("<<ComboboxSelected>>", _refresh_log)

    def toggle_log() -> None:
        log_visible["value"] = not log_visible["value"]
        if log_visible["value"]:
            log_frame.grid()
            log_toggle_button.configure(text="기록 닫기")
        else:
            log_frame.grid_remove()
            log_toggle_button.configure(text="기록")
        _sync_layout()

    log_toggle_button.configure(command=toggle_log)

    def toggle_theme() -> None:
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

    def _apply_toggle_icon(mode: str) -> None:
        if mode == "light":
            img = theme_icons["light"]
            theme_toggle.configure(image=img or "", text="" if img else "🌞")
        else:
            img = theme_icons["dark"]
            theme_toggle.configure(image=img or "", text="" if img else "🌙")

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

    root.after(500, prompt_for_updates)

    return root


def resource_path(relative_path: str) -> str:
    """ PyInstaller로 빌드된 경우 올바른 경로 반환 """
    base_path: str = cast(str, getattr(sys, "_MEIPASS", os.path.abspath(".")))
    return os.path.join(base_path, relative_path)


def main():
    ensure_dpi_awareness()
    root = build_gui()

    try:
        icon_path = resource_path('icons/afcs.ico')
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"아이콘 로드 실패: {e}")

    root.mainloop()


if __name__ == "__main__":
    main()
