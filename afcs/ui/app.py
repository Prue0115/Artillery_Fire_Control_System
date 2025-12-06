"""AFCS 메인 GUI 애플리케이션 구성 모듈."""
from __future__ import annotations

import os
import sys
import threading
import webbrowser
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import messagebox, ttk

from afcs.equipment import EquipmentRegistry
from afcs.ui.log_view import render_log
from afcs.ui.solutions import build_solution_table, calculate_and_display
from afcs.ui import theme as ui_theme
from afcs.versioning import (
    DEFAULT_GITHUB_REPO,
    fetch_latest_release,
    get_version,
    normalize_version_string,
    update_version,
)


@dataclass
class SolutionTables:
    low_rows: list[dict[str, tk.Label]]
    high_rows: list[dict[str, tk.Label]]
    low_status: ttk.Label
    high_status: ttk.Label


@dataclass
class LogPanel:
    frame: ttk.Labelframe
    body: ttk.Frame
    canvas: tk.Canvas
    scroll_bar: ttk.Scrollbar
    equipment_filter: tk.StringVar
    entries: list = field(default_factory=list)
    visible: bool = False
    width_hint: int = 0


@dataclass
class InputControls:
    my_altitude: ttk.Entry
    target_altitude: ttk.Entry
    distance: ttk.Entry
    system_var: tk.StringVar


@dataclass
class Header:
    title: ttk.Label
    system_select: ttk.Combobox
    system_var: tk.StringVar


class AFCSApplication:
    def __init__(self):
        ui_theme.set_theme("light")
        ui_theme.ensure_dpi_awareness()
        self.registry = EquipmentRegistry()
        self.root = tk.Tk()
        self.root.title("AFCS : Artillery Fire Control System")
        self.root.configure(bg=ui_theme.APP_BG)
        self.root.option_add("*Font", ui_theme.BODY_FONT)

        self.version_var = tk.StringVar(value=get_version())
        self.theme_var = tk.StringVar(value="light")

        self.header: Header | None = None
        self.inputs: InputControls | None = None
        self.tables: SolutionTables | None = None
        self.log_panel: LogPanel | None = None
        self.delta_label: ttk.Label | None = None
        self.theme_toggle: ttk.Button | None = None
        self.log_toggle_button: ttk.Button | None = None
        self.menu_button: ttk.Button | None = None

        ui_theme.apply_styles(self.root)
        self._build_layout()
        self._apply_toggle_icon(self.theme_var.get())
        self.root.after(500, self._check_latest_release)

    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, style="Main.TFrame", padding=20)
        main.grid(row=0, column=0, sticky="nsew")

        shell = ttk.Frame(main, style="Main.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=0)
        shell.columnconfigure(1, weight=1)

        self._build_sidebar(shell)

        content = ttk.Frame(shell, style="Main.TFrame")
        content.grid(row=0, column=1, sticky="nsew")

        self.header = self._build_header(content)
        self.inputs = self._build_inputs(content)
        self.tables, self.delta_label = self._build_results(content)
        self.theme_toggle, self.log_toggle_button = self._build_bottom_bar(content)
        self.log_panel = self._build_log_panel()

        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)

    def _build_sidebar(self, parent: ttk.Frame) -> ttk.Frame:
        sidebar = ttk.Frame(parent, style="Sidebar.TFrame", padding=(0, 0, 12, 0))
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.rowconfigure(1, weight=1)

        self.menu_button = ttk.Button(
            sidebar,
            text="☰",
            width=3,
            style="Sidebar.TButton",
            command=self._open_sidebar_menu,
            cursor="hand2",
        )
        self.menu_button.grid(row=0, column=0, sticky="nw", pady=(0, 12))

        return sidebar

    def _build_header(self, parent: ttk.Frame) -> Header:
        header = ttk.Frame(parent, style="Main.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text=f"AFCS {self.version_var.get()}", style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w")
        subtitle = ttk.Label(
            header,
            text="Made by Prue\nDiscord - prue._.0115",
            style="Muted.TLabel",
        )
        subtitle.grid(row=1, column=0, sticky="w")

        equipment_names = self.registry.names
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

        return Header(title=title, system_select=system_select, system_var=system_var)

    def _build_inputs(self, parent: ttk.Frame) -> InputControls:
        input_card = ttk.Frame(parent, style="Card.TFrame", padding=(16, 16, 16, 12))
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

        calculate_button = ttk.Button(
            parent,
            text="계산",
            style="Primary.TButton",
            command=self._handle_calculate,
        )
        calculate_button.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        return InputControls(
            my_altitude=my_altitude_entry,
            target_altitude=target_altitude_entry,
            distance=distance_entry,
            system_var=self.header.system_var,
        )

    def _build_results(self, parent: ttk.Frame) -> tuple[SolutionTables, ttk.Label]:
        results_card = ttk.Frame(parent, style="Card.TFrame", padding=16)
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

        delta_label = ttk.Label(parent, text="고도 차이: 계산 필요", style="Muted.TLabel")
        delta_label.grid(row=4, column=0, sticky="w", pady=(10, 0))

        tables = SolutionTables(
            low_rows=low_rows,
            high_rows=high_rows,
            low_status=low_status,
            high_status=high_status,
        )
        return tables, delta_label

    def _build_bottom_bar(self, parent: ttk.Frame) -> tuple[ttk.Button, ttk.Button]:
        bottom_bar = ttk.Frame(parent, style="Main.TFrame")
        bottom_bar.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        bottom_bar.columnconfigure(0, weight=1)

        self._load_theme_icons()

        theme_toggle = ttk.Button(
            bottom_bar,
            text="" if getattr(self.root, "light_icon_base", None) else "🌞",
            style="ThemeToggle.TButton",
            image=getattr(self.root, "light_icon_base", None),
            cursor="hand2",
            command=self._toggle_theme,
        )
        theme_toggle.grid(row=0, column=1, sticky="e", padx=(0, 8))

        log_toggle_button = ttk.Button(
            bottom_bar,
            text="기록",
            style="Secondary.TButton",
            command=self._toggle_log,
        )
        log_toggle_button.grid(row=0, column=2, sticky="e")

        return theme_toggle, log_toggle_button

    def _build_log_panel(self) -> LogPanel:
        log_frame = ttk.Labelframe(self.root, text="기록", style="Card.TLabelframe", padding=14)
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
            values=["전체", *self.registry.names],
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
        ui_theme.configure_log_canvas(log_canvas)
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

        for widget in (log_canvas, log_body, log_frame):
            widget.bind("<Enter>", lambda event: self._bind_scroll(event.widget))
            widget.bind("<Leave>", lambda event: self._unbind_scroll(event.widget))

        log_frame.columnconfigure(0, weight=1)
        log_frame.columnconfigure(1, weight=0)
        log_frame.rowconfigure(1, weight=1)

        equipment_select.bind("<<ComboboxSelected>>", self._refresh_log)

        log_panel = LogPanel(
            frame=log_frame,
            body=log_body,
            canvas=log_canvas,
            scroll_bar=y_scroll,
            equipment_filter=log_equipment_filter,
            entries=[],
        )
        self.log_panel = log_panel
        self._refresh_log()
        return log_panel

    def _bind_scroll(self, widget):
        widget.bind_all("<MouseWheel>", self._on_mousewheel)
        widget.bind_all("<Button-4>", self._on_linux_scroll)
        widget.bind_all("<Button-5>", self._on_linux_scroll)

    def _unbind_scroll(self, widget):
        widget.unbind_all("<MouseWheel>")
        widget.unbind_all("<Button-4>")
        widget.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if not self.log_panel or not self._can_scroll():
            return "break"
        self.log_panel.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _on_linux_scroll(self, event):
        if not self.log_panel or not self._can_scroll():
            return "break"
        direction = -1 if event.num == 4 else 1
        self.log_panel.canvas.yview_scroll(direction, "units")
        return "break"

    def _can_scroll(self) -> bool:
        if not self.log_panel:
            return False
        region = self.log_panel.canvas.bbox("all")
        if not region:
            return False
        content_height = region[3] - region[1]
        return content_height > self.log_panel.canvas.winfo_height()

    def _sync_layout(self):
        if not (self.log_panel and self.tables):
            return
        if self.log_panel.visible:
            self.log_panel.frame.update_idletasks()
            root_width = max(self.root.winfo_width(), self.root.winfo_reqwidth())

            content_width = self.log_panel.body.winfo_reqwidth()
            scrollbar_width = self.log_panel.scroll_bar.winfo_reqwidth()
            table_width = max(
                self.tables.low_status.master.master.winfo_width(),
                self.tables.low_status.master.master.winfo_reqwidth(),
            )
            desired_width = max(table_width, content_width + scrollbar_width)

            if desired_width > self.log_panel.width_hint:
                self.log_panel.width_hint = desired_width

            capped_width = min(self.log_panel.width_hint, max(root_width // 2, desired_width))

            self.root.columnconfigure(0, weight=1)
            self.root.columnconfigure(1, weight=0, minsize=capped_width)
        else:
            self.root.columnconfigure(0, weight=1)
            self.root.columnconfigure(1, weight=0, minsize=0)

    def _refresh_log(self, event=None):
        if not self.log_panel:
            return
        render_log(self.log_panel.body, self.log_panel.entries, self.log_panel.equipment_filter.get())
        self._sync_layout()

    def _toggle_log(self):
        if not self.log_panel:
            return
        self.log_panel.visible = not self.log_panel.visible
        if self.log_panel.visible:
            self.log_panel.frame.grid()
            self.log_toggle_button.configure(text="기록 닫기")
        else:
            self.log_panel.frame.grid_remove()
            self.log_toggle_button.configure(text="기록")
        self._sync_layout()

    def _apply_toggle_icon(self, mode: str):
        if not self.theme_toggle:
            return
        if mode == "light":
            img = getattr(self.root, "light_icon_base", None)
            self.theme_toggle.configure(image=img, text="" if img else "🌞")
        else:
            img = getattr(self.root, "dark_icon_base", None)
            self.theme_toggle.configure(image=img, text="" if img else "🌙")
        self.theme_toggle.image = img

    def _toggle_theme(self):
        if not (self.tables and self.log_panel):
            return
        new_theme = "dark" if self.theme_var.get() == "light" else "light"
        self.theme_var.set(new_theme)
        ui_theme.apply_theme(
            self.root,
            new_theme,
            solution_tables=[self.tables.low_rows, self.tables.high_rows],
            log_body=self.log_panel.body,
            log_entries=self.log_panel.entries,
            log_equipment_filter=self.log_panel.equipment_filter,
        )

        self._apply_toggle_icon(new_theme)

    def _open_sidebar_menu(self):
        if not self.menu_button:
            return

        menu = tk.Menu(
            self.root,
            tearoff=0,
            background=ui_theme.CARD_BG,
            foreground=ui_theme.TEXT_COLOR,
            activebackground=ui_theme.HOVER_BG,
            activeforeground=ui_theme.TEXT_COLOR,
            borderwidth=1,
            relief="solid",
        )
        menu.add_command(label="테마 전환", command=self._toggle_theme)
        menu.add_command(
            label="기록 창 토글", command=self._toggle_log if self.log_panel else None
        )
        menu.add_separator()
        menu.add_command(label="업데이트 확인", command=self._check_latest_release)
        menu.add_command(label="입력 초기화", command=self._reset_inputs)
        menu.add_command(label="GitHub 열기", command=self._open_github)

        x = self.menu_button.winfo_rootx()
        y = self.menu_button.winfo_rooty() + self.menu_button.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _reset_inputs(self):
        if not self.inputs:
            return
        for entry in (
            self.inputs.my_altitude,
            self.inputs.target_altitude,
            self.inputs.distance,
        ):
            entry.delete(0, tk.END)
        self.inputs.my_altitude.focus_set()

    def _open_github(self):
        repo_slug = os.environ.get("AFCS_GITHUB_REPO", DEFAULT_GITHUB_REPO)
        if repo_slug:
            webbrowser.open(f"https://github.com/{repo_slug}", new=1)

    def _handle_calculate(self):
        if not (self.tables and self.inputs and self.log_panel):
            return
        calculate_and_display(
            self.registry,
            self.inputs.system_var,
            self.tables.low_rows,
            self.tables.high_rows,
            self.tables.low_status,
            self.tables.high_status,
            self.delta_label,
            self.inputs.my_altitude,
            self.inputs.target_altitude,
            self.inputs.distance,
            self.log_panel.entries,
            self.log_panel.equipment_filter,
            self.log_panel.body,
            self._sync_layout,
        )

    def _check_latest_release(self):
        def _prompt_update(release):
            latest_version = normalize_version_string(release.get("version") or "")
            current_version = normalize_version_string(self.version_var.get())
            if not latest_version or latest_version == current_version:
                return

            repo_slug = os.environ.get("AFCS_GITHUB_REPO", DEFAULT_GITHUB_REPO)
            release_url = release.get("url") or (
                f"https://github.com/{repo_slug}/releases/latest" if repo_slug else None
            )

            prompt_lines = [f"{latest_version} 최신 버전을 업데이트하시겠습니까?"]

            if not messagebox.askyesno("업데이트 확인", "\n".join(prompt_lines), parent=self.root):
                return

            normalized = update_version(latest_version)
            self.version_var.set(normalized)
            self.header.title.config(text=f"AFCS {normalized}")
            if release_url:
                webbrowser.open(release_url, new=1)

        def _worker():
            release = fetch_latest_release()
            if release:
                self.root.after(0, lambda: _prompt_update(release))

        threading.Thread(target=_worker, daemon=True).start()

    def _set_icon(self):
        try:
            icon_path = resource_path("icons/afcs.ico")
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"아이콘 로드 실패: {e}")

    def _load_theme_icons(self) -> None:
        def _find_icon(filename: str) -> Path | None:
            for path in (ui_theme.ICONS_DIR / filename, Path(resource_path(f"icons/{filename}"))):
                if path.exists():
                    return path
            return None

        def _load_icon(path: Path | None) -> tk.PhotoImage | None:
            if not path:
                return None
            try:
                return tk.PhotoImage(file=str(path))
            except Exception:
                return None

        light_icon = _load_icon(_find_icon("Light Mode.png"))
        dark_icon = _load_icon(_find_icon("Dark Mode.png"))

        self.root.light_icon_base = light_icon
        self.root.dark_icon_base = dark_icon

    def run(self):
        self._set_icon()
        self.root.mainloop()


def resource_path(relative_path):
    """PyInstaller로 빌드된 경우 올바른 경로 반환"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
