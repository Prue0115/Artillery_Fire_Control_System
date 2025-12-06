"""사격 제원 계산 및 결과 테이블 관련 모듈."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from afcs.ui import theme as ui_theme
from afcs.range_tables import available_charges, find_solutions
from afcs.ui.log_view import append_log_entry


def update_solution_table(rows, status_label, solutions, message: str | None = None) -> None:
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
        ch = tk.Label(table, text="—", bg=ui_theme.CARD_BG, fg=ui_theme.MUTED_COLOR, font=ui_theme.MONO_FONT, anchor="w", width=4)
        mill = tk.Label(table, text="—", bg=ui_theme.CARD_BG, fg=ui_theme.MUTED_COLOR, font=ui_theme.MONO_FONT, anchor="w", width=12)
        eta = tk.Label(table, text="—", bg=ui_theme.CARD_BG, fg=ui_theme.MUTED_COLOR, font=ui_theme.MONO_FONT, anchor="w", width=6)

        ch.grid(row=i + 1, column=0, sticky="w", pady=3)
        mill.grid(row=i + 1, column=1, sticky="w", pady=3)
        eta.grid(row=i + 1, column=2, sticky="w", pady=3)

        rows.append({"ch": ch, "mill": mill, "eta": eta})

    status = ttk.Label(parent, text="계산 결과가 여기에 표시됩니다", style="TableStatus.TLabel")
    status.grid(row=1, column=0, sticky="w", pady=(8, 0))

    table.grid(row=0, column=0, sticky="nsew")
    parent.columnconfigure(0, weight=1)
    return rows, status


def calculate_and_display(
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

    low_charges = low_override if low_override is not None else available_charges(equipment, "low")
    high_charges = high_override if high_override is not None else available_charges(equipment, "high")

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
        low_message = "저각 사격을 지원하지 않습니다" if low_override == [] else "저각 데이터가 없습니다."

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
        high_message = "고각 사격을 지원하지 않습니다" if high_override == [] else "고각 데이터가 없습니다."

    update_solution_table(low_rows, low_status, low_solutions, message=low_message)
    update_solution_table(high_rows, high_status, high_solutions, message=high_message)
    delta_label.config(text=f"고도 차이(사수-목표): {altitude_delta:+.1f} m")

    append_log_entry(
        log_entries,
        log_body,
        log_equipment_filter,
        my_alt,
        target_alt,
        distance,
        system,
        low_solutions,
        high_solutions,
        sync_layout=sync_layout,
    )
