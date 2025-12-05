import sys
from pathlib import Path

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

BASE_TITLE_FONT = ("SF Pro Display", 18, "bold")
BASE_BODY_FONT = ("SF Pro Text", 12)
BASE_MONO_FONT = ("SF Mono", 12)
BASE_CH_WIDTH = 4
BASE_MILL_WIDTH = 12
BASE_ETA_WIDTH = 6

TITLE_FONT = BASE_TITLE_FONT
BODY_FONT = BASE_BODY_FONT
MONO_FONT = BASE_MONO_FONT
CH_WIDTH = BASE_CH_WIDTH
MILL_WIDTH = BASE_MILL_WIDTH
ETA_WIDTH = BASE_ETA_WIDTH

ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"


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


def apply_device_profile(profile):
    """폰트/폭을 디바이스 프로필에 맞춰 스케일링합니다."""

    def _scale_font(font):
        family, size, *rest = font
        scaled_size = max(8, int(round(size * profile.font_scale)))
        return (family, scaled_size, *rest)

    global TITLE_FONT, BODY_FONT, MONO_FONT
    global CH_WIDTH, MILL_WIDTH, ETA_WIDTH

    TITLE_FONT = _scale_font(BASE_TITLE_FONT)
    BODY_FONT = _scale_font(BASE_BODY_FONT)
    MONO_FONT = _scale_font(BASE_MONO_FONT)

    width_scale = 1.1 if getattr(profile, "narrow_layout", False) else 1.0
    CH_WIDTH = max(3, int(round(BASE_CH_WIDTH * width_scale)))
    MILL_WIDTH = max(10, int(round(BASE_MILL_WIDTH * width_scale)))
    ETA_WIDTH = max(5, int(round(BASE_ETA_WIDTH * width_scale)))


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
                # Best-effort: ignore if DPI awareness can't be set on this platform.
                pass
