from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from app.config_manager import ConfigManager
from app.core.state_manager import StateManager

if TYPE_CHECKING:
    from app.gui.upload_panel import UploadPanel
    from app.gui.case_info_panel import CaseInfoPanel
    from app.gui.analysis_panel import AnalysisPanel
    from app.gui.result_panel import ResultPanel


class MainWindow(tk.Tk):
    """主窗口，包含案件管理和多个功能面板。"""

    def __init__(self, config_manager: ConfigManager):
        """
        初始化主窗口。

        Args:
            config_manager: 配置管理器
        """
        super().__init__()
        self.config_manager = config_manager
        self.title("案件分析系统")
        self.geometry("1200x800")
        self._create_widgets()

    def _create_widgets(self) -> None:
        """创建窗口组件。"""
        self._create_menu()
        self._create_case_bar()
        self._create_notebook()

    def _create_menu(self) -> None:
        """创建菜单栏。"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建案件", command=self._on_new_case)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit)

        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="配置", command=self._on_settings)

    def _create_case_bar(self) -> None:
        """创建案件管理栏。"""
        case_frame = ttk.Frame(self)
        case_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(case_frame, text="当前案件:").pack(side='left', padx=5)

        self.case_combobox = ttk.Combobox(case_frame, width=30, state='readonly')
        self.case_combobox.pack(side='left', padx=5)
        self.case_combobox.bind('<<ComboboxSelected>>', self._on_case_changed)

        ttk.Button(case_frame, text="新建", command=self._on_new_case, width=8).pack(side='left', padx=5)
        ttk.Button(case_frame, text="删除", command=self._on_delete_case, width=8).pack(side='left', padx=5)

        self._refresh_case_list()

    def _create_notebook(self) -> None:
        """创建功能面板标签页。"""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)

        from app.gui.upload_panel import UploadPanel
        from app.gui.case_info_panel import CaseInfoPanel
        from app.gui.analysis_panel import AnalysisPanel
        from app.gui.result_panel import ResultPanel

        self.upload_panel = UploadPanel(self.notebook, self)
        self.case_info_panel = CaseInfoPanel(self.notebook, self)
        self.analysis_panel = AnalysisPanel(self.notebook, self)
        self.result_panel = ResultPanel(self.notebook, self)

        self.notebook.add(self.upload_panel, text="文件上传")
        self.notebook.add(self.case_info_panel, text="案件信息")
        self.notebook.add(self.analysis_panel, text="分析功能")
        self.notebook.add(self.result_panel, text="结果查看")

    def _refresh_case_list(self) -> None:
        """刷新案件列表。"""
        cases = StateManager.list_cases()
        self.case_combobox['values'] = cases
        if cases:
            current = StateManager.current_case_id()
            if current and current in cases:
                self.case_combobox.set(current)
            else:
                self.case_combobox.set(cases[0])
                StateManager.switch(cases[0])
        else:
            self.case_combobox.set('')

    def _on_case_changed(self, event) -> None:
        """案件切换事件。"""
        case_id = self.case_combobox.get()
        if case_id:
            StateManager.switch(case_id)
            self._refresh_panels()

    def _on_new_case(self) -> None:
        """新建案件。"""
        dialog = tk.Toplevel(self)
        dialog.title("新建案件")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="案件ID:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        case_id_entry = ttk.Entry(dialog, width=30)
        case_id_entry.grid(row=0, column=1, padx=10, pady=10)

        def on_ok():
            case_id = case_id_entry.get().strip()
            if not case_id:
                messagebox.showerror("错误", "案件ID不能为空")
                return
            if case_id in StateManager.list_cases():
                messagebox.showerror("错误", "案件ID已存在")
                return

            StateManager.create(case_id)
            self._refresh_case_list()
            self.case_combobox.set(case_id)
            self._refresh_panels()
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=1, column=0, columnspan=2, pady=20)
        ttk.Button(button_frame, text="确定", command=on_ok, width=10).pack(side='left', padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=10).pack(side='left', padx=5)

    def _on_delete_case(self) -> None:
        """删除案件。"""
        case_id = self.case_combobox.get()
        if not case_id:
            messagebox.showwarning("警告", "请先选择案件")
            return

        if messagebox.askyesno("确认", f"确定要删除案件 '{case_id}' 吗？"):
            StateManager.destroy(case_id)
            self._refresh_case_list()
            self._refresh_panels()

    def _on_settings(self) -> None:
        """打开设置窗口。"""
        from app.gui.setting_windows import SettingsWindow
        SettingsWindow(self, self.config_manager)

    def _refresh_panels(self) -> None:
        """刷新所有面板。"""
        self.upload_panel.refresh()
        self.case_info_panel.refresh()
        self.analysis_panel.refresh()
        self.result_panel.refresh()

    def get_current_case_id(self) -> str:
        """获取当前案件ID。"""
        return self.case_combobox.get()

    def flush_case_info_to_state(self) -> None:
        """把「案件信息」页当前输入同步到内存状态，供各分析模块读取。"""
        self.case_info_panel.flush_to_state()