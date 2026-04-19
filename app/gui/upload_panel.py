from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.state_manager import StateManager
from app.data_paths import paths_from_config, persist_upload_bytes
from app.modules.upload_module import FileDataSource

if TYPE_CHECKING:
    from app.gui.main_window import MainWindow


class UploadPanel(ttk.Frame):
    """文件上传面板。"""

    def __init__(self, parent: ttk.Frame, main_window: 'MainWindow'):
        """
        初始化上传面板。

        Args:
            parent: 父容器
            main_window: 主窗口
        """
        super().__init__(parent)
        self.main_window = main_window
        self.data_source = FileDataSource()
        self._create_widgets()

    def _create_widgets(self) -> None:
        """创建面板组件。"""
        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="选择文件", command=self._on_select_files, width=15).pack(side='left', padx=5)
        ttk.Button(button_frame, text="导入到案件", command=self._on_upload, width=15).pack(side='left', padx=5)
        ttk.Button(button_frame, text="清空", command=self._on_clear, width=15).pack(side='left', padx=5)

        self.file_listbox = tk.Listbox(self, height=20)
        self.file_listbox.pack(fill='both', expand=True, padx=10, pady=5)

        self.status_label = ttk.Label(self, text="")
        self.status_label.pack(fill='x', padx=10, pady=5)

    def _on_select_files(self) -> None:
        """选择文件对话框。"""
        case_id = self.main_window.get_current_case_id()
        if not case_id:
            messagebox.showwarning("警告", "请先创建案件")
            return

        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=[("Excel文件", "*.xls *.xlsx"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )

        if files:
            for file_path in files:
                self.file_listbox.insert(tk.END, file_path)

    def _on_clear(self) -> None:
        """清空文件列表。"""
        self.file_listbox.delete(0, tk.END)
        self.status_label.config(text="")

    def _on_upload(self) -> None:
        """上传文件。"""
        case_id = self.main_window.get_current_case_id()
        if not case_id:
            messagebox.showwarning("警告", "请先创建案件")
            return

        files = self.file_listbox.get(0, tk.END)
        if not files:
            messagebox.showwarning("警告", "请先选择文件")
            return

        try:
            state = StateManager.get(case_id)
            files_dict = {}

            paths = paths_from_config(self.main_window.config_manager)
            for file_path in files:
                path = Path(file_path)
                with open(path, 'rb') as f:
                    content = f.read()
                files_dict[path.name] = content
                persist_upload_bytes(paths, case_id, path.name, content)

            result = self.data_source.process_files(files_dict, state)
            self.status_label.config(
                text=(
                    f"成功: {result['succeeded']}, 失败: {result['failed']}, "
                    f"本批文件数: {result['total_files']}, 已载入表数: {result['frames_in_state']}"
                )
            )
            lines = [
                f"成功: {result['succeeded']}, 失败: {result['failed']}",
            ]
            err_list = result.get('errors') or []
            if err_list:
                lines.append("")
                lines.extend(err_list[:10])
                if len(err_list) > 10:
                    lines.append(f"… 另有 {len(err_list) - 10} 条错误未显示")
            body = "\n".join(lines)
            title = "上传完成" if result['failed'] == 0 else "上传完成（含失败）"
            if result['failed']:
                messagebox.showwarning(title, body)
            else:
                messagebox.showinfo(title, body)
        except Exception as e:
            messagebox.showerror("错误", f"上传失败: {str(e)}")

    def refresh(self) -> None:
        """刷新面板。"""
        self.file_listbox.delete(0, tk.END)
        self.status_label.config(text="")