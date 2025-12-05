import json
import os
import random
import string
import sys
import tempfile
import threading
import time
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

import afcs.ui_theme as ui_theme
from afcs.equipment import EquipmentRegistry
from afcs.range_tables import available_charges, find_solutions
from afcs.ui_theme import (
    BODY_FONT,
    CH_WIDTH,
    ETA_WIDTH,
    ICONS_DIR,
    MILL_WIDTH,
    MONO_FONT,
    THEMES,
    TITLE_FONT,
    ensure_dpi_awareness,
)
from afcs.versioning import (
    DEFAULT_GITHUB_REPO,
    fetch_latest_release,
    get_version,
    normalize_version_string,
    update_version,
)


ui_theme.set_theme("light")
registry = EquipmentRegistry()


class ShareManager:
    def __init__(self, root: tk.Tk, on_receive, on_stop=None):
        self.root = root
        self.on_receive = on_receive
        self.on_stop = on_stop
        self.room_code: str | None = None
        self.role: str | None = None  # "host" or "viewer"
        self._poll_job = None
        self._last_seen: float | None = None

    def _room_file(self, code: str):
        return os.path.join(tempfile.gettempdir(), f"afcs_share_{code}.json")

    def _generate_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(random.choice(alphabet) for _ in range(6))

    def start_host(self):
        self.stop()
        for _ in range(10):
            candidate = self._generate_code()
            if not os.path.exists(self._room_file(candidate)):
                self.room_code = candidate
                self.role = "host"
                self._last_seen = None
                self._write_payload({"status": "ready"})
                return candidate
        raise RuntimeError("방 코드를 생성할 수 없습니다. 잠시 후 다시 시도하세요.")

    def join_room(self, code: str):
        self.stop()
        filepath = self._room_file(code)
        if not os.path.exists(filepath):
            raise FileNotFoundError("해당 방 코드를 찾을 수 없습니다.")
        self.room_code = code
        self.role = "viewer"
        self._last_seen = None
        self._start_polling()
        self._read_and_apply()

    def stop(self):
        if self._poll_job:
            self.root.after_cancel(self._poll_job)
            self._poll_job = None
        if self.role == "host" and self.room_code:
            try:
                os.remove(self._room_file(self.room_code))
            except FileNotFoundError:
                pass
        self.room_code = None
        self.role = None
        self._last_seen = None
        if self.on_stop:
            self.on_stop()

    def broadcast(self, payload: dict):
        if not self.room_code:
            return
        payload = payload | {"sent_at": time.time(), "role": self.role}
        self._write_payload(payload)

    def _write_payload(self, payload: dict):
        if not self.room_code:
            return
        data = {"updated_at": time.time(), "payload": payload}
        filepath = self._room_file(self.room_code)
        with open(filepath, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)

    def _read_and_apply(self):
        if not self.room_code:
            return
        filepath = self._room_file(self.room_code)
        try:
            with open(filepath, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except FileNotFoundError:
            messagebox.showwarning("제원 공유", "공유 방이 사라졌습니다. 공유를 종료합니다.")
            self.stop()
            return
        updated_at = data.get("updated_at")
        if updated_at is None or updated_at == self._last_seen:
            return
        self._last_seen = updated_at
        payload = data.get("payload")
        if payload:
            self.on_receive(payload)

    def _start_polling(self):
        if not self.room_code:
            return
        self._read_and_apply()
        self._poll_job = self.root.after(1000, self._start_polling)


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
def render_log(log_body: ttk.Frame, entries, equipment_filter: str):
    for child in log_body.winfo_children():
        child.destroy()

    filtered_entries = sorted(entries, key=lambda e: e["timestamp"], reverse=True)
    if equipment_filter and equipment_filter != "전체":
        filtered_entries = [
            e for e in filtered_entries if e["system"] == equipment_filter
        ]

    if not filtered_entries:
        tk.Label(
            log_body,
            text="선택한 조건에 맞는 기록이 없습니다.",
            bg=ui_theme.CARD_BG,
            fg=ui_theme.MUTED_COLOR,
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
            bg=ui_theme.CARD_BG,
            fg=ui_theme.ACCENT_COLOR,
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
            bg=ui_theme.CARD_BG,
            fg=ui_theme.MUTED_COLOR,
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
                bg=ui_theme.CARD_BG,
                fg=ui_theme.TEXT_COLOR,
                font=(MONO_FONT[0], 11, "bold"),
                anchor="w",
            ).grid(row=0, column=column, columnspan=columnspan, sticky="w")

        _header("LOW", 0, 3)
        _header("HIGH", 4, 3)

        def _column_header(label_text, column, width):
            tk.Label(
                table,
                text=label_text,
                width=width,
                bg=ui_theme.CARD_BG,
                fg=ui_theme.MUTED_COLOR,
                font=(MONO_FONT[0], 10, "bold"),
                anchor="w",
            ).grid(row=1, column=column, sticky="w")

        for idx_col, (label_text, width) in enumerate(
            (("CH", CH_WIDTH), ("MILL", MILL_WIDTH), ("ETA", ETA_WIDTH))
        ):
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
                bg=ui_theme.CARD_BG,
                fg=ui_theme.MUTED_COLOR if value == "—" else ui_theme.TEXT_COLOR,
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

            for col_offset, key, width in (
                (0, "charge", CH_WIDTH),
                (1, "mill", MILL_WIDTH),
                (2, "eta", ETA_WIDTH),
            ):
                _row(fmt(low, key, width), width, row_idx, col_offset)
                _row(fmt(high, key, width), width, row_idx, col_offset + 4)

        if idx < len(filtered_entries) - 1:
            ttk.Separator(log_body, orient="horizontal").grid(
                row=idx * 2 + 1, column=0, sticky="ew", pady=4
            )


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
    share_manager: ShareManager | None = None,
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

    if share_manager and share_manager.room_code:
        share_manager.broadcast(
            {
                "system": system,
                "my_alt": my_alt,
                "target_alt": target_alt,
                "distance": distance,
                "altitude_delta": altitude_delta,
                "low": low_solutions,
                "high": high_solutions,
            }
        )


def setup_share_feature(
    root: tk.Tk,
    equipment_names: list[str],
    system_var: tk.StringVar,
    my_altitude_entry: ttk.Entry,
    target_altitude_entry: ttk.Entry,
    distance_entry: ttk.Entry,
    low_rows,
    low_status: ttk.Label,
    high_rows,
    high_status: ttk.Label,
    delta_label: ttk.Label,
    share_button: ttk.Button,
):
    share_status_var = tk.StringVar(value="제원 공유 꺼짐")
    share_manager: ShareManager | None = None

    def _share_status_text(room_code: str | None, role: str | None) -> str:
        if not room_code:
            return "제원 공유 꺼짐"
        role_name = "호스트" if role == "host" else "뷰어" if role == "viewer" else "알 수 없음"
        return f"제원 공유 중 · 방 코드 {room_code} ({role_name})"

    def _update_share_status(room_code: str | None = None, role: str | None = None):
        share_status_var.set(_share_status_text(room_code, role))

    def apply_shared_payload(payload: dict):
        system = payload.get("system")
        if system and system in equipment_names:
            system_var.set(system)
        for entry, key in (
            (my_altitude_entry, "my_alt"),
            (target_altitude_entry, "target_alt"),
            (distance_entry, "distance"),
        ):
            value = payload.get(key)
            if value is not None:
                entry.delete(0, tk.END)
                entry.insert(0, str(value))

        low = payload.get("low") or []
        high = payload.get("high") or []
        update_solution_table(low_rows, low_status, low)
        update_solution_table(high_rows, high_status, high)

        altitude_delta = payload.get("altitude_delta")
        if altitude_delta is not None:
            delta_label.config(text=f"고도 차이(사수-목표): {altitude_delta:+.1f} m")

        _update_share_status(
            share_manager.room_code if share_manager else None,
            share_manager.role if share_manager else None,
        )

    share_manager = ShareManager(
        root,
        apply_shared_payload,
        lambda: _update_share_status(None, None),
    )

    def open_share_dialog():
        dialog = tk.Toplevel(root)
        dialog.title("사격 제원 공유")
        dialog.configure(bg=ui_theme.APP_BG)
        dialog.resizable(False, False)
        dialog.grab_set()

        status_value = tk.StringVar(
            value=share_manager.room_code or "생성된 방이 없습니다",
        )
        role_value = tk.StringVar(
            value="없음" if not share_manager.role else ("호스트" if share_manager.role == "host" else "뷰어"),
        )

        def refresh_status():
            status_value.set(share_manager.room_code or "생성된 방이 없습니다")
            role_value.set(
                "없음"
                if not share_manager.role
                else ("호스트" if share_manager.role == "host" else "뷰어")
            )

        def create_room():
            try:
                code = share_manager.start_host()
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("제원 공유", str(exc), parent=dialog)
                return
            _update_share_status(code, "host")
            status_value.set(code)
            role_value.set("호스트")
            messagebox.showinfo(
                "제원 공유", f"방 코드 {code}가 생성되었습니다. 상대에게 전달하세요.", parent=dialog
            )

        def join_room():
            code = code_entry.get().strip().upper()
            if not code:
                messagebox.showwarning("제원 공유", "방 코드를 입력하세요.", parent=dialog)
                return
            try:
                share_manager.join_room(code)
            except FileNotFoundError:
                messagebox.showerror("제원 공유", "해당 코드의 방을 찾을 수 없습니다.", parent=dialog)
                return
            _update_share_status(code, "viewer")
            refresh_status()
            messagebox.showinfo("제원 공유", "방에 입장했습니다. 계산 결과가 공유됩니다.", parent=dialog)

        def stop_share():
            if not share_manager.room_code:
                messagebox.showinfo("제원 공유", "현재 참여 중인 방이 없습니다.", parent=dialog)
                return
            share_manager.stop()
            refresh_status()
            _update_share_status(None, None)
            messagebox.showinfo("제원 공유", "제원 공유를 종료했습니다.", parent=dialog)

        ttk.Label(dialog, text="제원 공유", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6)
        )
        ttk.Label(
            dialog,
            text="계산 시 내 제원이 방 코드로 연결된 사용자에게 공유됩니다.\n"
            "방 코드 생성·입장 후 필요 시 공유 중단을 눌러 종료하세요.",
            style="Muted.TLabel",
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))

        ttk.Label(dialog, text="방 코드 생성", style="Body.TLabel").grid(
            row=2, column=0, sticky="w", padx=12, pady=4
        )
        ttk.Button(dialog, text="방 만들기", style="Primary.TButton", command=create_room).grid(
            row=2, column=1, sticky="e", padx=12, pady=4
        )

        ttk.Label(dialog, text="방 코드 입력", style="Body.TLabel").grid(
            row=3, column=0, sticky="w", padx=12, pady=4
        )
        code_entry = ttk.Entry(dialog)
        code_entry.grid(row=3, column=1, sticky="ew", padx=12, pady=4)
        dialog.columnconfigure(1, weight=1)

        ttk.Button(dialog, text="입장하기", style="Secondary.TButton", command=join_room).grid(
            row=4, column=1, sticky="e", padx=12, pady=(0, 8)
        )

        ttk.Button(dialog, text="공유 중단", style="Secondary.TButton", command=stop_share).grid(
            row=5, column=1, sticky="e", padx=12, pady=(0, 12)
        )

        status_frame = ttk.Frame(dialog, style="Card.TFrame", padding=12)
        status_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        status_frame.columnconfigure(1, weight=1)
        ttk.Label(status_frame, text="현재 코드", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(status_frame, textvariable=status_value, style="Body.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(status_frame, text="역할", style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
    ttk.Label(status_frame, textvariable=role_value, style="Body.TLabel").grid(
        row=1, column=1, sticky="w", pady=(4, 0)
    )

    share_button.configure(command=open_share_dialog)
    return share_manager, share_status_var


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
        ch = tk.Label(table, text="—", bg=ui_theme.CARD_BG, fg=ui_theme.MUTED_COLOR, font=MONO_FONT, anchor="w", width=4)
        mill = tk.Label(table, text="—", bg=ui_theme.CARD_BG, fg=ui_theme.MUTED_COLOR, font=MONO_FONT, anchor="w", width=12)
        eta = tk.Label(table, text="—", bg=ui_theme.CARD_BG, fg=ui_theme.MUTED_COLOR, font=MONO_FONT, anchor="w", width=6)

        ch.grid(row=i + 1, column=0, sticky="w", pady=3)
        mill.grid(row=i + 1, column=1, sticky="w", pady=3)
        eta.grid(row=i + 1, column=2, sticky="w", pady=3)

        rows.append({"ch": ch, "mill": mill, "eta": eta})

    status = ttk.Label(parent, text="계산 결과가 여기에 표시됩니다", style="TableStatus.TLabel")
    status.grid(row=1, column=0, sticky="w", pady=(8, 0))

    table.grid(row=0, column=0, sticky="nsew")
    parent.columnconfigure(0, weight=1)
    return rows, status


def build_gui():
    root = tk.Tk()
    root.title("AFCS : Artillery Fire Control System")
    root.configure(bg=ui_theme.APP_BG)
    root.option_add("*Font", BODY_FONT)
    ui_theme.apply_styles(root)

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
        font=BODY_FONT,
    )
    system_select.grid(row=0, column=1, sticky="w", padx=(6, 0))

    menu_bar = ttk.Frame(main, style="Main.TFrame")
    menu_bar.grid(row=1, column=0, sticky="ew", pady=(0, 12))
    for idx in range(3):
        menu_bar.columnconfigure(idx, weight=0)
    menu_bar.columnconfigure(3, weight=1)

    input_card = ttk.Frame(main, style="Card.TFrame", padding=(16, 16, 16, 12))
    input_card.grid(row=2, column=0, sticky="ew")
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
    button_row.grid(row=3, column=0, sticky="ew", pady=(12, 0))
    button_row.columnconfigure(0, weight=1)

    calculate_button = ttk.Button(
        button_row,
        text="계산",
        style="Primary.TButton",
        command=lambda: None,
    )
    calculate_button.grid(row=0, column=0, sticky="ew")

    results_card = ttk.Frame(main, style="Card.TFrame", padding=16)
    results_card.grid(row=4, column=0, sticky="ew", pady=(16, 0))
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
    delta_label.grid(row=5, column=0, sticky="w", pady=(10, 0))

    theme_var = tk.StringVar(value="light")

    try:
        root.light_icon_base = tk.PhotoImage(file=str(ICONS_DIR / "Light Mode.png"))
        root.dark_icon_base = tk.PhotoImage(file=str(ICONS_DIR / "Dark Mode.png"))
    except Exception as e:
        messagebox.showerror("아이콘 로드 오류", f"테마 아이콘을 불러오지 못했습니다.\n{e}")
        root.light_icon_base = root.dark_icon_base = None

    theme_toggle = ttk.Button(
        menu_bar,
        text="다크 모드",  # 기본 텍스트는 이미지가 없을 때만 노출
        style="ThemeToggle.TButton",
        image=root.light_icon_base if root.light_icon_base else None,
        cursor="hand2",
        padding=(10, 6),
    )
    theme_toggle.grid(row=0, column=1, sticky="w", padx=(6, 6))

    log_toggle_button = ttk.Button(menu_bar, text="기록", style="Secondary.TButton")
    log_toggle_button.grid(row=0, column=0, sticky="w")

    share_button = ttk.Button(menu_bar, text="사격 제원 공유", style="Primary.TButton")
    share_button.grid(row=0, column=2, sticky="w")

    share_manager, share_status_var = setup_share_feature(
        root,
        equipment_names,
        system_var,
        my_altitude_entry,
        target_altitude_entry,
        distance_entry,
        low_rows,
        low_status,
        high_rows,
        high_status,
        delta_label,
        share_button,
    )

    share_state_label = ttk.Label(
        main, textvariable=share_status_var, style="Muted.TLabel"
    )
    share_state_label.grid(row=6, column=0, sticky="w")

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
        font=BODY_FONT,
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

    def toggle_theme():
        new_theme = "dark" if theme_var.get() == "light" else "light"
        theme_var.set(new_theme)
        ui_theme.apply_theme(
            root,
            new_theme,
            solution_tables=[low_rows, high_rows],
            log_body=log_body,
            log_entries=log_entries,
            log_equipment_filter=log_equipment_filter,
            render_log_fn=render_log,
        )

        _apply_toggle_icon(new_theme)

    theme_toggle.configure(command=toggle_theme)

    def _apply_toggle_icon(mode: str):
        if mode == "light":
            img = root.light_icon_base if root.light_icon_base else None
            theme_toggle.configure(
                image=img,
                text="다크 모드" if img else "🌞",
                compound="left",
            )
        else:
            img = root.dark_icon_base if root.dark_icon_base else None
            theme_toggle.configure(
                image=img,
                text="라이트 모드" if img else "🌙",
                compound="left",
            )

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
            share_manager,
        )
    )

    def _on_close():
        share_manager.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

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
