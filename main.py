import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk

import afcs.ui_theme as ui_theme
from afcs.equipment import EquipmentRegistry
from afcs.ui.log_view import render_log
from afcs.ui.solutions import build_solution_table, calculate_and_display
from afcs.ui.theme import apply_styles, apply_theme, configure_log_canvas, ensure_dpi_awareness
from afcs.versioning import (
    DEFAULT_GITHUB_REPO,
    fetch_latest_release,
    get_version,
    normalize_version_string,
    update_version,
)

ui_theme.set_theme("light")
registry = EquipmentRegistry()


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


def build_gui():
    root = tk.Tk()
    root.title("AFCS : Artillery Fire Control System")
    root.configure(bg=ui_theme.APP_BG)
    root.option_add("*Font", ui_theme.BODY_FONT)
    apply_styles(root)

    version_var = tk.StringVar(value=get_version())

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
        root.light_icon_base = tk.PhotoImage(file=str(ui_theme.ICONS_DIR / "Light Mode.png"))
        root.dark_icon_base = tk.PhotoImage(file=str(ui_theme.ICONS_DIR / "Dark Mode.png"))
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
        font=ui_theme.BODY_FONT,
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

    def _apply_toggle_icon(mode: str):
        if mode == "light":
            img = root.light_icon_base if root.light_icon_base else None
            theme_toggle.configure(image=img, text="" if img else "🌞")
        else:
            img = root.dark_icon_base if root.dark_icon_base else None
            theme_toggle.configure(image=img, text="" if img else "🌙")

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

    calculate_button.configure(
        command=lambda: calculate_and_display(
            registry,
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

    root.rowconfigure(0, weight=1)
    main.columnconfigure(0, weight=1)
    main.rowconfigure(3, weight=1)

    _apply_toggle_icon(theme_var.get())

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

    try:
        icon_path = resource_path('icons/afcs.ico')
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"아이콘 로드 실패: {e}")

    root.mainloop()


if __name__ == "__main__":
    main()
