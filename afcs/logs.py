from datetime import datetime
import tkinter as tk
from tkinter import ttk

from .theme import (
    ACCENT_COLOR,
    CARD_BG,
    CH_WIDTH,
    ETA_WIDTH,
    MILL_WIDTH,
    MONO_FONT,
    MUTED_COLOR,
    TEXT_COLOR,
)


def render_log(log_body: ttk.Frame, entries, equipment_filter: str):
    log_body.configure(bg=CARD_BG)
    for child in log_body.winfo_children():
        child.destroy()

    filtered_entries = sorted(entries, key=lambda e: e["timestamp"], reverse=True)
    if equipment_filter and equipment_filter != "전체":
        filtered_entries = [e for e in filtered_entries if e["system"] == equipment_filter]

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
                font=(MONO_FONT[0], 12, "bold"),
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

        for idx_col, (label_text, width) in enumerate((("CH", CH_WIDTH), ("MILL", MILL_WIDTH), ("ETA", ETA_WIDTH))):
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

            for col_offset, key, width in ((0, "charge", CH_WIDTH), (1, "mill", MILL_WIDTH), (2, "eta", ETA_WIDTH)):
                _row(fmt(low, key, width), width, row_idx, col_offset)
                _row(fmt(high, key, width), width, row_idx, col_offset + 4)

        if idx < len(filtered_entries) - 1:
            ttk.Separator(log_body, orient="horizontal").grid(row=idx * 2 + 1, column=0, sticky="ew", pady=4)


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
