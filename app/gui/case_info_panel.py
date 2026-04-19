"""当前案件的静态信息录入（写入 AppState，与上传/分析共用 StateManager）。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from app.core.state_manager import StateManager
from app.utils.case_points_text import format_case_points, parse_case_points_text

if TYPE_CHECKING:
    from app.gui.main_window import MainWindow


class CaseInfoPanel(ttk.Frame):
    """案件信息：案发点、嫌疑人画像、租赁与车辆辅助字段。"""

    def __init__(self, parent: ttk.Frame, main_window: "MainWindow"):
        super().__init__(parent)
        self.main_window = main_window
        self._gender = tk.StringVar()
        self._region = tk.StringVar()
        self._rental_company = tk.StringVar()
        self._car_brand = tk.StringVar()
        self._create_widgets()

    def _create_widgets(self) -> None:
        hint = (
            "案发记录：每行一条，格式为「日期, 城市」（示例：2024-03-15, 杭州市）。"
            " 保存后写入当前案件内存状态，退出程序不保留。"
        )
        ttk.Label(self, text=hint, wraplength=900).pack(anchor='w', padx=10, pady=(10, 4))

        text_frame = ttk.Frame(self)
        text_frame.pack(fill='both', expand=True, padx=10, pady=4)
        ttk.Label(text_frame, text="案发记录 (case_points)").pack(anchor='w')
        inner = ttk.Frame(text_frame)
        inner.pack(fill='both', expand=True, pady=4)
        scroll = ttk.Scrollbar(inner)
        scroll.pack(side='right', fill='y')
        self._points_text = tk.Text(inner, height=12, width=80, wrap='none', yscrollcommand=scroll.set)
        self._points_text.pack(side='left', fill='both', expand=True)
        scroll.config(command=self._points_text.yview)

        grid = ttk.LabelFrame(self, text="画像与辅助信息")
        grid.pack(fill='x', padx=10, pady=8)
        for r, (lab, var) in enumerate(
            [
                ("嫌疑人性别", self._gender),
                ("嫌疑人户籍", self._region),
                ("租赁公司名称", self._rental_company),
                ("车辆品牌", self._car_brand),
            ],
            start=0,
        ):
            ttk.Label(grid, text=f"{lab}:").grid(row=r, column=0, sticky='w', padx=8, pady=4)
            ttk.Entry(grid, textvariable=var, width=50).grid(row=r, column=1, sticky='ew', padx=8, pady=4)
        grid.columnconfigure(1, weight=1)

        btn_row = ttk.Frame(self)
        btn_row.pack(fill='x', padx=10, pady=10)
        ttk.Button(btn_row, text="保存到当前案件", command=self._on_save, width=18).pack(side='left', padx=4)
        ttk.Button(btn_row, text="从当前案件重新加载", command=self.refresh, width=18).pack(side='left', padx=4)

    def _on_save(self) -> None:
        case_id = self.main_window.get_current_case_id()
        if not case_id:
            messagebox.showwarning("警告", "请先创建或选择案件")
            return
        raw = self._points_text.get("1.0", tk.END)
        points, err = parse_case_points_text(raw)
        if err:
            messagebox.showerror("格式错误", err)
            return
        try:
            state = StateManager.get(case_id)
            state["case_points"] = points
            state["profile_gender"] = self._gender.get().strip()
            state["profile_region"] = self._region.get().strip()
            state["rental_company"] = self._rental_company.get().strip()
            state["car_brand"] = self._car_brand.get().strip()
        except KeyError as e:
            messagebox.showerror("错误", f"状态字段未注册: {e}")
            return
        messagebox.showinfo("成功", "案件信息已写入当前案件（内存）。")

    def refresh(self) -> None:
        case_id = self.main_window.get_current_case_id()
        self._points_text.delete("1.0", tk.END)
        self._gender.set("")
        self._region.set("")
        self._rental_company.set("")
        self._car_brand.set("")
        if not case_id:
            return
        try:
            state = StateManager.get(case_id)
            pts = state["case_points"]
            if isinstance(pts, list) and pts and all(isinstance(t, (list, tuple)) and len(t) >= 2 for t in pts):
                pairs = [(str(t[0]), str(t[1])) for t in pts]
            else:
                pairs = []
            self._points_text.insert("1.0", format_case_points(pairs))
            self._gender.set(str(state["profile_gender"] or ""))
            self._region.set(str(state["profile_region"] or ""))
            self._rental_company.set(str(state["rental_company"] or ""))
            self._car_brand.set(str(state["car_brand"] or ""))
        except (KeyError, RuntimeError):
            pass
