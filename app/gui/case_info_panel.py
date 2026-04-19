"""案件基础信息录入"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from app.core.state_manager import StateManager

if TYPE_CHECKING:
    from app.gui.main_window import MainWindow

_DEFAULT_CRIME_DATE = date(2013, 11, 18)
_GENDER_OPTIONS = ("", "男性", "女性")
_REGION_OPTIONS = ("", "南方", "北方")


def _parse_iso_date(s: str) -> date | None:
    s = s.strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


class CaseInfoPanel(ttk.Frame):
    """案件信息：案发点逐条添加、嫌疑人画像下拉、租赁与车辆文本。"""

    def __init__(self, parent: ttk.Frame, main_window: "MainWindow"):
        super().__init__(parent)
        self.main_window = main_window
        self._date_var = tk.StringVar(value=_DEFAULT_CRIME_DATE.isoformat())
        self._location_var = tk.StringVar()
        self._gender_var = tk.StringVar(value="")
        self._region_var = tk.StringVar(value="")
        self._rental_var = tk.StringVar()
        self._brand_var = tk.StringVar()
        self._create_widgets()

    def _create_widgets(self) -> None:
        ttk.Label(self, text="案件嫌疑人基础信息录入", font=("", 11, "bold")).pack(
            anchor="w", padx=10, pady=(10, 6)
        )

        style_wide = {"width": 38}
        ttk.Label(self, text="1. 案发城市（关键字）:").pack(anchor="w", padx=10, pady=(4, 0))
        ttk.Entry(self, textvariable=self._location_var, **style_wide).pack(anchor="w", padx=10, pady=2)

        ttk.Label(self, text="2. 案发日期 (YYYY-MM-DD):").pack(anchor="w", padx=10, pady=(8, 0))
        ttk.Entry(self, textvariable=self._date_var, **style_wide).pack(anchor="w", padx=10, pady=2)

        ttk.Button(self, text="确认添加", command=self._on_add_point).pack(anchor="w", padx=10, pady=6)

        ttk.Label(self, text="已保存案发记录:").pack(anchor="w", padx=10, pady=(6, 0))
        disp_frame = ttk.Frame(self)
        disp_frame.pack(fill="both", expand=False, padx=10, pady=2)
        self._points_display = tk.Text(
            disp_frame, height=5, width=62, wrap="word", state="disabled", relief="solid", borderwidth=1
        )
        self._points_display.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(disp_frame, command=self._points_display.yview)
        scroll.pack(side="right", fill="y")
        self._points_display.config(yscrollcommand=scroll.set)

        ttk.Label(self, text="3. 嫌疑人性别:").pack(anchor="w", padx=10, pady=(10, 0))
        self._gender_cb = ttk.Combobox(
            self, textvariable=self._gender_var, values=_GENDER_OPTIONS, state="readonly", width=35
        )
        self._gender_cb.pack(anchor="w", padx=10, pady=2)

        ttk.Label(self, text="4. 嫌疑人户籍:").pack(anchor="w", padx=10, pady=(6, 0))
        self._region_cb = ttk.Combobox(
            self, textvariable=self._region_var, values=_REGION_OPTIONS, state="readonly", width=35
        )
        self._region_cb.pack(anchor="w", padx=10, pady=2)

        ttk.Label(self, text="5. 租赁公司:").pack(anchor="w", padx=10, pady=(6, 0))
        ttk.Entry(self, textvariable=self._rental_var, **style_wide).pack(anchor="w", padx=10, pady=2)

        ttk.Label(self, text="6. 车辆品牌:").pack(anchor="w", padx=10, pady=(6, 0))
        ttk.Entry(self, textvariable=self._brand_var, **style_wide).pack(anchor="w", padx=10, pady=2)

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", padx=10, pady=12)
        ttk.Button(btn_row, text="完成", command=self._on_complete, width=12).pack(side="left", padx=(0, 6))
        self._btn_clear = ttk.Button(btn_row, text="清空记录", command=self._on_clear_init, width=12)
        self._btn_clear.pack(side="left", padx=4)

        self._confirm_frame = ttk.Frame(btn_row)
        ttk.Label(self._confirm_frame, text="确认清空记录？").pack(side="left", padx=(8, 4))
        ttk.Button(self._confirm_frame, text="是，确认清空", command=self._on_clear_yes, width=14).pack(
            side="left", padx=2
        )
        ttk.Button(self._confirm_frame, text="否，点错了", command=self._on_clear_no, width=12).pack(side="left", padx=2)

    def _require_case_id(self) -> str | None:
        case_id = self.main_window.get_current_case_id()
        if not case_id:
            messagebox.showwarning("警告", "请先创建或选择案件")
            return None
        return case_id

    def _set_points_display_text(self, text: str) -> None:
        self._points_display.configure(state="normal")
        self._points_display.delete("1.0", tk.END)
        self._points_display.insert("1.0", text)
        self._points_display.configure(state="disabled")

    def _format_saved_points(self, state) -> str:
        pts = state["case_points"]
        if not pts:
            return "[无记录]"
        lines = []
        for i, p in enumerate(pts):
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                lines.append(f"记录{i + 1}: 地点={p[1]}, 时间={p[0]}")
        return "\n".join(lines) if lines else "[无记录]"

    def _refresh_points_display(self) -> None:
        case_id = self.main_window.get_current_case_id()
        if not case_id:
            self._set_points_display_text("[无记录]")
            return
        try:
            state = StateManager.get(case_id)
            self._set_points_display_text(self._format_saved_points(state))
        except KeyError:
            self._set_points_display_text("[无记录]")

    def _on_add_point(self) -> None:
        case_id = self._require_case_id()
        if not case_id:
            return
        loc = self._location_var.get().strip()
        if not loc:
            messagebox.showwarning("提示", "请先输入案发地点！")
            return
        d = _parse_iso_date(self._date_var.get())
        if d is None:
            messagebox.showerror("格式错误", "案发日期须为 YYYY-MM-DD，例如 2013-11-18")
            return
        try:
            state = StateManager.get(case_id)
            state["case_points"].append((d.isoformat(), loc))
        except KeyError as e:
            messagebox.showerror("错误", f"状态异常: {e}")
            return
        self._location_var.set("")
        self._refresh_points_display()

    def _sync_profile_to_state(self, case_id: str) -> None:
        state = StateManager.get(case_id)
        state["profile_gender"] = self._gender_var.get().strip()
        state["profile_region"] = self._region_var.get().strip()
        state["rental_company"] = self._rental_var.get().strip()
        state["car_brand"] = self._brand_var.get().strip()

    def flush_to_state(self) -> None:
        """将当前界面上的画像/租赁/车辆字段写回 AppState（分析前调用，避免未点「完成」导致仍用旧值）。"""
        case_id = self.main_window.get_current_case_id()
        if not case_id:
            return
        try:
            self._sync_profile_to_state(case_id)
        except KeyError:
            pass

    def _on_complete(self) -> None:
        case_id = self._require_case_id()
        if not case_id:
            return
        try:
            self._sync_profile_to_state(case_id)
        except KeyError as e:
            messagebox.showerror("错误", f"状态异常: {e}")
            return
        messagebox.showinfo("完成", "基础信息已录入完毕，请继续后续分析。")

    def _on_clear_init(self) -> None:
        self._btn_clear.pack_forget()
        self._confirm_frame.pack(side="left", padx=4)

    def _on_clear_no(self) -> None:
        self._confirm_frame.pack_forget()
        self._btn_clear.pack(side="left", padx=4)

    def _on_clear_yes(self) -> None:
        case_id = self._require_case_id()
        if case_id:
            try:
                state = StateManager.get(case_id)
                state["case_points"] = []
                state["profile_gender"] = ""
                state["profile_region"] = ""
                state["rental_company"] = ""
                state["car_brand"] = ""
            except KeyError:
                pass
        self._gender_var.set("")
        self._region_var.set("")
        self._rental_var.set("")
        self._brand_var.set("")
        self._date_var.set(_DEFAULT_CRIME_DATE.isoformat())
        self._location_var.set("")
        self._refresh_points_display()
        self._on_clear_no()
        messagebox.showinfo("提示", "已清空记录！")

    def refresh(self) -> None:
        """切换案件或外部刷新时，从 StateManager 回填控件。"""
        self._confirm_frame.pack_forget()
        self._btn_clear.pack(side="left", padx=4)

        case_id = self.main_window.get_current_case_id()
        self._location_var.set("")
        self._date_var.set(_DEFAULT_CRIME_DATE.isoformat())
        if not case_id:
            self._gender_var.set("")
            self._region_var.set("")
            self._rental_var.set("")
            self._brand_var.set("")
            self._set_points_display_text("[无记录]")
            return
        try:
            state = StateManager.get(case_id)
            g = str(state["profile_gender"] or "")
            r = str(state["profile_region"] or "")
            self._gender_var.set(g if g in _GENDER_OPTIONS else "")
            self._region_var.set(r if r in _REGION_OPTIONS else "")
            self._rental_var.set(str(state["rental_company"] or ""))
            self._brand_var.set(str(state["car_brand"] or ""))
            self._set_points_display_text(self._format_saved_points(state))
        except (KeyError, RuntimeError):
            self._gender_var.set("")
            self._region_var.set("")
            self._rental_var.set("")
            self._brand_var.set("")
            self._set_points_display_text("[无记录]")
