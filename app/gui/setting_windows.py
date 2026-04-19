from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import TYPE_CHECKING

from app.config_manager import ConfigManager

if TYPE_CHECKING:
    from app.gui.main_window import MainWindow


class SettingsWindow(tk.Toplevel):
    """设置窗口，用于配置数据库连接和路径。"""

    def __init__(self, parent: tk.Tk, config_manager: ConfigManager):
        """
        初始化设置窗口。

        Args:
            parent: 父窗口
            config_manager: 配置管理器
        """
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.title("设置")
        self.geometry("520x460")
        self.resizable(False, False)
        self._create_widgets()

    def _create_widgets(self) -> None:
        """创建窗口组件。"""
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        database_frame = ttk.Frame(notebook)
        paths_frame = ttk.Frame(notebook)

        notebook.add(database_frame, text="数据库")
        notebook.add(paths_frame, text="路径")

        self._create_database_tab(database_frame)
        self._create_paths_tab(paths_frame)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="保存", command=self._on_save).pack(side='right', padx=5)
        ttk.Button(button_frame, text="取消", command=self.destroy).pack(side='right', padx=5)

    def _create_database_tab(self, parent: ttk.Frame) -> None:
        """创建数据库配置标签页。"""
        db_config = self.config_manager.database_config

        ttk.Label(parent, text="主机:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.host_entry = ttk.Entry(parent, width=30)
        self.host_entry.insert(0, db_config.get('host', 'localhost'))
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(parent, text="端口:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.port_entry = ttk.Entry(parent, width=30)
        self.port_entry.insert(0, str(db_config.get('port', 3306)))
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(parent, text="用户名:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.user_entry = ttk.Entry(parent, width=30)
        self.user_entry.insert(0, db_config.get('user', 'root'))
        self.user_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(parent, text="密码:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.password_entry = ttk.Entry(parent, width=30, show='*')
        self.password_entry.insert(0, db_config.get('password', ''))
        self.password_entry.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(parent, text="数据库名:").grid(row=4, column=0, sticky='w', padx=5, pady=5)
        self.name_entry = ttk.Entry(parent, width=30)
        self.name_entry.insert(0, db_config.get('name', 'case_analysis'))
        self.name_entry.grid(row=4, column=1, padx=5, pady=5)

    def _create_paths_tab(self, parent: ttk.Frame) -> None:
        """创建路径配置标签页。"""
        paths_config = self.config_manager.paths_config
        raw = paths_config.get('raw_dir') or paths_config.get('upload_dir', '')
        cache = paths_config.get('cache_dir') or paths_config.get('export_dir', '')
        sample = paths_config.get('sample_dir', '')

        ttk.Label(parent, text="原始上传(raw):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.raw_path_entry = ttk.Entry(parent, width=30)
        self.raw_path_entry.insert(0, raw)
        self.raw_path_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(parent, text="浏览...", command=self._browse_raw_path).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(parent, text="分析缓存(cache):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.cache_path_entry = ttk.Entry(parent, width=30)
        self.cache_path_entry.insert(0, cache)
        self.cache_path_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(parent, text="浏览...", command=self._browse_cache_path).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(parent, text="测试样本(sample):").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.sample_path_entry = ttk.Entry(parent, width=30)
        self.sample_path_entry.insert(0, sample)
        self.sample_path_entry.grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(parent, text="浏览...", command=self._browse_sample_path).grid(row=2, column=2, padx=5, pady=5)

    def _browse_raw_path(self) -> None:
        path = filedialog.askdirectory(title="选择原始上传目录 (raw)")
        if path:
            self.raw_path_entry.delete(0, tk.END)
            self.raw_path_entry.insert(0, path)

    def _browse_cache_path(self) -> None:
        path = filedialog.askdirectory(title="选择分析缓存目录 (cache)")
        if path:
            self.cache_path_entry.delete(0, tk.END)
            self.cache_path_entry.insert(0, path)

    def _browse_sample_path(self) -> None:
        path = filedialog.askdirectory(title="选择测试样本目录 (sample)")
        if path:
            self.sample_path_entry.delete(0, tk.END)
            self.sample_path_entry.insert(0, path)

    def _on_save(self) -> None:
        """保存配置。"""
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("错误", "端口必须是数字")
            return

        self.config_manager.set('database.host', self.host_entry.get())
        self.config_manager.set('database.port', port)
        self.config_manager.set('database.user', self.user_entry.get())
        self.config_manager.set('database.password', self.password_entry.get())
        self.config_manager.set('database.name', self.name_entry.get())
        raw = self.raw_path_entry.get().strip()
        cache = self.cache_path_entry.get().strip()
        sample = self.sample_path_entry.get().strip()
        self.config_manager.set('paths.raw_dir', raw)
        self.config_manager.set('paths.cache_dir', cache)
        self.config_manager.set('paths.sample_dir', sample)
        if raw:
            self.config_manager.set('paths.data_root', str(Path(raw).parent))

        self.config_manager.save()
        messagebox.showinfo("成功", "配置已保存")
        self.destroy()