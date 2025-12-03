import sys
import tkinter as tk
from tkinter import ttk

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

TITLE_FONT = ("SF Pro Display", 18, "bold")
BODY_FONT = ("SF Pro Text", 12)
MONO_FONT = ("SF Mono", 12)

CH_WIDTH = 4
MILL_WIDTH = 12
ETA_WIDTH = 6


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


def ensure_dpi_awareness():
    """Enable high-DPI awareness on Windows to avoid blurry rendering."""

    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


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
    style.configure("TableCell.TLabel", background=CARD_BG, foreground=TEXT_COLOR, font=MONO_FONT, anchor="w")
    style.configure(
        "TableCellMuted.TLabel",
        background=CARD_BG,
        foreground=MUTED_COLOR,
        font=MONO_FONT,
        anchor="w",
    )
    style.configure(
        "LogAccent.TLabel",
        background=CARD_BG,
        foreground=ACCENT_COLOR,
        font=(MONO_FONT[0], 12, "bold"),
        anchor="w",
    )
    style.configure(
        "LogMuted.TLabel",
        background=CARD_BG,
        foreground=MUTED_COLOR,
        font=MONO_FONT,
        anchor="w",
    )
    style.configure(
        "LogHeader.TLabel",
        background=CARD_BG,
        foreground=TEXT_COLOR,
        font=(MONO_FONT[0], 12, "bold"),
        anchor="w",
    )

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
            text = widget.cget("text")
            widget.configure(style="TableCellMuted.TLabel" if text == "—" else "TableCell.TLabel")


def configure_log_canvas(canvas: tk.Canvas):
    canvas.configure(
        bg=CARD_BG,
        highlightbackground=BORDER_COLOR,
        highlightcolor=BORDER_COLOR,
    )


set_theme("light")
