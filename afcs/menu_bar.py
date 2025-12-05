import tkinter as tk
from tkinter import ttk

from afcs.ui_theme import ICONS_DIR


class MenuBar(ttk.Frame):
    def __init__(self, parent, *, theme_var: tk.StringVar):
        super().__init__(parent, style="Main.TFrame")
        self.columnconfigure(0, weight=0)

        self.theme_var = theme_var

        self.log_button = ttk.Button(self, text="기록", style="Secondary.TButton")
        self.log_button.grid(row=0, column=0, sticky="w", padx=(0, 8))

        try:
            self.light_icon_base = tk.PhotoImage(file=str(ICONS_DIR / "Light Mode.png"))
            self.dark_icon_base = tk.PhotoImage(file=str(ICONS_DIR / "Dark Mode.png"))
        except Exception:
            self.light_icon_base = self.dark_icon_base = None

        self.theme_toggle = ttk.Button(
            self,
            text="" if self.light_icon_base else "🌞",
            style="ThemeToggle.TButton",
            image=self.light_icon_base if self.light_icon_base else None,
            cursor="hand2",
        )
        self.theme_toggle.grid(row=0, column=1, sticky="w", padx=(0, 8))

        self.share_button = ttk.Button(
            self, text="사격 제원 공유", style="Secondary.TButton"
        )
        self.share_button.grid(row=0, column=2, sticky="w")

    def set_log_active(self, active: bool):
        self.log_button.configure(text="기록 닫기" if active else "기록")

    def apply_theme_icon(self, mode: str | None = None):
        target_mode = mode or self.theme_var.get()
        if target_mode == "light":
            img = self.light_icon_base if self.light_icon_base else None
            self.theme_toggle.configure(image=img, text="" if img else "🌞")
        else:
            img = self.dark_icon_base if self.dark_icon_base else None
            self.theme_toggle.configure(image=img, text="" if img else "🌙")
