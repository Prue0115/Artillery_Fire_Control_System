"""UI 테마 및 스타일 관련 유틸리티."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import afcs.ui_theme as ui_theme
from afcs.ui_theme import ensure_dpi_awareness, set_theme  # re-export for convenience


__all__ = ["apply_theme", "apply_styles", "configure_log_canvas", "refresh_solution_rows", "ensure_dpi_awareness"]


def apply_styles(root: tk.Tk) -> None:
    style = ttk.Style()
    style.theme_use("clam")

    style.configure("TFrame", background=ui_theme.APP_BG)
    style.configure("Main.TFrame", background=ui_theme.APP_BG)
    style.configure("Card.TFrame", background=ui_theme.CARD_BG, relief="flat", borderwidth=0)

    style.configure(
        "Body.TLabel", background=ui_theme.APP_BG, foreground=ui_theme.TEXT_COLOR, font=ui_theme.BODY_FONT
    )
    style.configure(
        "Muted.TLabel", background=ui_theme.APP_BG, foreground=ui_theme.MUTED_COLOR, font=ui_theme.BODY_FONT
    )
    style.configure(
        "Title.TLabel", background=ui_theme.APP_BG, foreground=ui_theme.TEXT_COLOR, font=ui_theme.TITLE_FONT
    )
    style.configure(
        "CardBody.TLabel", background=ui_theme.CARD_BG, foreground=ui_theme.TEXT_COLOR, font=ui_theme.BODY_FONT, anchor="w"
    )
    style.configure(
        "TableHeader.TLabel",
        background=ui_theme.CARD_BG,
        foreground=ui_theme.MUTED_COLOR,
        font=(ui_theme.BODY_FONT[0], 11, "bold"),
    )
    style.configure(
        "TableStatus.TLabel", background=ui_theme.CARD_BG, foreground=ui_theme.MUTED_COLOR, font=ui_theme.BODY_FONT
    )

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


def refresh_solution_rows(rows: list[dict[str, tk.Label]]) -> None:
    for row in rows:
        for key in ("ch", "mill", "eta"):
            widget = row[key]
            widget.configure(bg=ui_theme.CARD_BG)
            widget.configure(
                fg=ui_theme.MUTED_COLOR if widget.cget("text") == "—" else ui_theme.TEXT_COLOR
            )


def configure_log_canvas(canvas: tk.Canvas) -> None:
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
) -> None:
    set_theme(theme_name)
    root.configure(bg=ui_theme.APP_BG)
    apply_styles(root)

    for rows in solution_tables:
        refresh_solution_rows(rows)

    configure_log_canvas(log_body.master)

    from afcs.ui.log_view import render_log

    render_log(log_body, log_entries, log_equipment_filter.get())
