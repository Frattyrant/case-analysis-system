from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import TYPE_CHECKING

import pandas as pd

from app.core.state_manager import StateManager
from app.data_paths import paths_from_config

if TYPE_CHECKING:
    from app.gui.main_window import MainWindow


class ResultPanel(ttk.Frame):
    """结果查看面板。"""

    def __init__(self, parent: ttk.Frame, main_window: 'MainWindow'):
        """
        初始化结果面板。

        Args:
            parent: 父容器
            main_window: 主窗口
        """
        super().__init__(parent)
        self.main_window = main_window
        self.current_df = None
        self.page_size = 20
        self.current_page = 0
        self._create_widgets()

    def _create_widgets(self) -> None:
        """创建面板组件。"""
        control_frame = ttk.Frame(self)
        control_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(control_frame, text="结果类型:").pack(side='left', padx=5)
        self.result_type_combobox = ttk.Combobox(control_frame, width=20, state='readonly')
        self.result_type_combobox.pack(side='left', padx=5)
        self.result_type_combobox.bind('<<ComboboxSelected>>', self._on_result_type_changed)

        ttk.Button(control_frame, text="导出CSV", command=self._on_export, width=12).pack(side='right', padx=5)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame)
        scrollbar_y = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')

        page_frame = ttk.Frame(self)
        page_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(page_frame, text="上一页", command=self._on_prev_page, width=10).pack(side='left', padx=5)
        self.page_label = ttk.Label(page_frame, text="第 0 / 0 页")
        self.page_label.pack(side='left', padx=5)
        ttk.Button(page_frame, text="下一页", command=self._on_next_page, width=10).pack(side='left', padx=5)

    def _on_result_type_changed(self, event) -> None:
        """结果类型切换事件。"""
        self._load_result()

    def _load_result(self) -> None:
        """加载结果数据。"""
        case_id = self.main_window.get_current_case_id()
        if not case_id:
            return

        result_type = self.result_type_combobox.get()
        if not result_type:
            return

        try:
            state = StateManager.get(case_id)
            # AppState 使用 __getitem__，无 dict 风格 .get()
            if result_type in (
                'matched_trajectories',
                'df_real_car',
                'current_lodging_res',
            ):
                df = state[result_type]
                if not isinstance(df, pd.DataFrame):
                    df = pd.DataFrame()
            else:
                df = pd.DataFrame()

            self.current_df = df
            self.current_page = 0
            self._display_page()
        except Exception as e:
            messagebox.showerror("错误", f"加载结果失败: {str(e)}")

    def _display_page(self) -> None:
        """显示当前页数据。"""
        if self.current_df is None or self.current_df.empty:
            self.tree.delete(*self.tree.get_children())
            self.page_label.config(text="第 0 / 0 页")
            return

        total_pages = (len(self.current_df) + self.page_size - 1) // self.page_size
        start = self.current_page * self.page_size
        end = min(start + self.page_size, len(self.current_df))
        page_df = self.current_df.iloc[start:end]

        self.tree.delete(*self.tree.get_children())
        self.tree['columns'] = list(page_df.columns)
        self.tree.column('#0', width=0, stretch=False)

        for col in page_df.columns:
            self.tree.column(col, width=100, anchor='w')
            self.tree.heading(col, text=col)

        for _, row in page_df.iterrows():
            self.tree.insert('', 'end', values=list(row))

        self.page_label.config(text=f"第 {self.current_page + 1} / {total_pages} 页")

    def _on_prev_page(self) -> None:
        """上一页。"""
        if self.current_page > 0:
            self.current_page -= 1
            self._display_page()

    def _on_next_page(self) -> None:
        """下一页。"""
        if self.current_df is not None:
            total_pages = (len(self.current_df) + self.page_size - 1) // self.page_size
            if self.current_page < total_pages - 1:
                self.current_page += 1
                self._display_page()

    def _on_export(self) -> None:
        """导出CSV。"""
        if self.current_df is None or self.current_df.empty:
            messagebox.showwarning("警告", "没有可导出的数据")
            return

        case_id = self.main_window.get_current_case_id()
        paths = paths_from_config(self.main_window.config_manager)
        initial = paths.case_cache_dir(case_id) if case_id else paths.cache
        initial.mkdir(parents=True, exist_ok=True)

        file_path = filedialog.asksaveasfilename(
            title="保存CSV",
            initialdir=str(initial),
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )

        if file_path:
            try:
                self.current_df.to_csv(file_path, index=False, encoding='utf-8-sig')
                messagebox.showinfo("成功", f"文件已保存到: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")

    def refresh(self) -> None:
        """刷新面板。"""
        result_types = ['matched_trajectories', 'df_real_car', 'current_lodging_res']
        self.result_type_combobox['values'] = result_types
        if result_types:
            self.result_type_combobox.set(result_types[0])
            self._load_result()
        else:
            self.result_type_combobox.set('')
            self.tree.delete(*self.tree.get_children())
            self.page_label.config(text="第 0 / 0 页")