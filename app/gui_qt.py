# app/gui_qt.py
from __future__ import annotations

from pathlib import Path
from typing import Callable, Union

import pandas as pd
from PyQt6.QtCore import QDate, QThread, pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDateEdit, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QProgressDialog, QSpinBox, QStatusBar, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QTabWidget, QScrollArea, QFrame,
    QMenu, QDialog, QTextEdit, QListWidgetItem, QInputDialog
)

from app.services_ import AppServices


def _resource_dir() -> str:
    """返回 app/resources 目录的绝对路径，兼容 PyInstaller 打包与开发模式。"""
    import sys
    if getattr(sys, 'frozen', False):
        # PyInstaller onedir: _MEIPASS 指向 _internal 目录
        return str(Path(sys._MEIPASS) / 'app' / 'resources')
    return str(Path(__file__).resolve().parent / 'resources')


class AnalysisWorker(QThread):
    """专门用于在后台执行耗时分析任务的线程，防止UI卡死"""
    finished_sig = pyqtSignal(str, object)  # 发射 (任务标题, 结果DataFrame或Dict)
    error_sig = pyqtSignal(str, str)        # 发射 (任务标题, 错误信息)

    def __init__(self, title: str, fn: Callable):
        super().__init__()
        self.title = title
        self.fn = fn

    def run(self):
        try:
            res = self.fn()
            self.finished_sig.emit(self.title, res)
        except Exception as e:
            self.error_sig.emit(self.title, str(e))


class ResultTabWidget(QWidget):
    """独立的分析结果标签页（带分页、全局列排序、可选的下一步操作按钮和内联查询组件）"""

    def __init__(self, title: str, data: Union[pd.DataFrame, dict], export_dir: Path, parent=None,
                 action_buttons: list | None = None, bottom_widget: QWidget | None = None,
                 descriptions: dict[str, str] | None = None,
                 summary_text: str = ''):
        """action_buttons: [(按钮文字, 回调函数), ...] 在表格下方显示下一步操作按钮
           bottom_widget: 可选的自定义组件，渲染在操作按钮下方
           descriptions: 可选，表名→描述文字的映射，用于在表格上方显示提示
           summary_text: 可选，查询结果总结文字，渲染在表格下方、操作按钮上方"""
        super().__init__(parent)
        self.export_dir = export_dir
        self.title = title
        self._page_size = 10
        self._current_page = 1
        self._action_buttons = action_buttons or []
        self._bottom_widget = bottom_widget
        self._descriptions = descriptions or {}
        self._summary_text = summary_text

        # 排序状态记录
        self._sort_col = None
        self._sort_asc = True

        if isinstance(data, dict):
            self._tables = data
        else:
            self._tables = {f"{title}结果": data if data is not None else pd.DataFrame()}

        self._active_key = list(self._tables.keys())[0] if self._tables else ""
        self._build_ui()
        # 设置初始表格描述
        if self._active_key and self._active_key in self._descriptions:
            self.desc_label.setText(self._descriptions[self._active_key])
        self._render_page()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        top_bar = QHBoxLayout()

        self.view_combo = QComboBox()
        self.view_combo.addItems(list(self._tables.keys()))
        self.view_combo.currentTextChanged.connect(self._switch_table)
        top_bar.addWidget(QLabel("视图:"))
        top_bar.addWidget(self.view_combo)
        if len(self._tables) <= 1:
            self.view_combo.hide()
            top_bar.itemAt(0).widget().hide()

        self.btn_export_curr = QPushButton("导出当前表")
        self.btn_export_curr.clicked.connect(self._export_current)
        top_bar.addWidget(self.btn_export_curr)

        if len(self._tables) > 1:
            self.btn_export_all = QPushButton("一键导出全部相关表")
            self.btn_export_all.setStyleSheet("background-color: #f0ad4e; color: black;")
            self.btn_export_all.clicked.connect(self._export_all)
            top_bar.addWidget(self.btn_export_all)

        top_bar.addStretch()

        self.btn_prev = QPushButton("◀ 上一页")
        self.btn_next = QPushButton("下一页 ▶")
        self.btn_prev.clicked.connect(lambda: self._change_page(-1))
        self.btn_next.clicked.connect(lambda: self._change_page(1))
        self.page_label = QLabel("1 / 1")
        top_bar.addWidget(self.btn_prev)
        top_bar.addWidget(self.page_label)
        top_bar.addWidget(self.btn_next)

        # 表格描述提示（如航班三张表的来源说明）
        self.desc_label = QLabel()
        self.desc_label.setStyleSheet(
            "color: #475569; font-size: 13px; padding: 6px 10px; "
            "background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 4px;"
        )
        self.desc_label.setWordWrap(True)
        self.desc_label.setVisible(bool(self._descriptions))

        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # 禁止双击修改
        # 绑定点击表头排序事件
        self.table_widget.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table_widget.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self._show_context_menu)

        layout.addLayout(top_bar)
        layout.addWidget(self.desc_label)
        layout.addWidget(self.table_widget)

        # 查询结果总结标签（表格下方，蓝色提示条）
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet(
            "color: #1e40af; font-size: 14px; font-weight: bold; padding: 8px 12px; "
            "background-color: #eff6ff; border: 1px solid #93c5fd; border-radius: 6px;"
        )
        self.summary_label.setWordWrap(True)
        self.summary_label.setText(self._summary_text)
        self.summary_label.setVisible(bool(self._summary_text))
        layout.addWidget(self.summary_label)

        # 下一步操作按钮区域（可选）
        if self._action_buttons:
            action_bar = QHBoxLayout()
            action_bar.addStretch()
            for btn_text, callback in self._action_buttons:
                btn = QPushButton(btn_text)
                btn.setObjectName("ActionBtn")
                btn.clicked.connect(callback)
                action_bar.addWidget(btn)
            action_bar.addStretch()
            layout.addLayout(action_bar)

        # 内联查询组件（可选，如轨迹结果页嵌入真伪查询）
        if self._bottom_widget:
            layout.addWidget(self._bottom_widget)

    def _on_header_clicked(self, logical_index: int):
        """点击表头，触发底层 DataFrame 排序，并刷新页面"""
        df = self._tables.get(self._active_key, pd.DataFrame())
        if df.empty or logical_index >= len(df.columns): return
        
        col_name = df.columns[logical_index]
        if self._sort_col == col_name:
            self._sort_asc = not self._sort_asc  # 切换升降序
        else:
            self._sort_col = col_name
            self._sort_asc = True
            
        try:
            # 执行 Pandas 底层全局排序 (na_position='last' 保证空值沉底)
            self._tables[self._active_key] = df.sort_values(
                by=col_name, ascending=self._sort_asc, na_position='last'
            )
            self._current_page = 1  # 排序后重置回第一页
            self._render_page()
        except Exception:
            pass  # 防止个别无法比较的数据类型（如混杂字典）崩溃
    def _on_cell_double_clicked(self, row: int, col: int):
        """双击单元格：弹出统一尺寸的固定窗口，内容可鼠标划选复制"""
        item = self.table_widget.item(row, col)
        if not item or not item.text():
            return
            
        header_item = self.table_widget.horizontalHeaderItem(col)
        col_name = header_item.text().replace(' ▲', '').replace(' ▼', '') if header_item else "详情"
        
        # 使用自定义 QDialog 替代原来的 QMessageBox，以统一长宽并支持文本复制
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{col_name}")
        dialog.resize(400, 220)  # 【统一提示框尺寸：宽400，高220】
        
        layout = QVBoxLayout(dialog)
        
        # 使用只读的文本域展示数据，支持用鼠标自由划选和 Ctrl+C
        text_edit = QTextEdit()
        text_edit.setPlainText(item.text())
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("font-size: 14px; padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; background-color: #f8fafc;")
        
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(dialog.accept)
        btn_close.setMinimumHeight(32)
        
        layout.addWidget(text_edit)
        layout.addWidget(btn_close)
        
        dialog.exec()

    def _show_context_menu(self, position):
        """右键菜单：提供一键快捷复制单元格内容的功能"""
        item = self.table_widget.itemAt(position)
        if not item or not item.text():
            return
            
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: white; border: 1px solid #cbd5e1; font-size: 14px; }"
                           "QMenu::item { padding: 8px 25px; }"
                           "QMenu::item:selected { background-color: #e2e8f0; color: #0f172a; }")
        
        copy_action = menu.addAction(" 复制")
        
        # 在鼠标点击位置弹出菜单
        action = menu.exec(self.table_widget.viewport().mapToGlobal(position))
        
        if action == copy_action:
            # 写入系统剪贴板
            QApplication.clipboard().setText(item.text())

    def _switch_table(self, key: str):
        if not key: return
        self._active_key = key
        self._current_page = 1
        self._sort_col = None  # 切换表时重置排序状态
        # 更新表格描述文字
        desc = self._descriptions.get(key, '')
        self.desc_label.setText(desc)
        self.desc_label.setVisible(bool(desc))
        self._render_page()

    def _change_page(self, delta: int):
        df = self._tables.get(self._active_key, pd.DataFrame())
        if df.empty: return
        total_pages = max(1, (len(df) + self._page_size - 1) // self._page_size)
        self._current_page = max(1, min(total_pages, self._current_page + delta))
        self._render_page()

    def _render_page(self):
        df = self._tables.get(self._active_key, pd.DataFrame())
        if df.empty:
            self.table_widget.clear()
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            self.page_label.setText("无数据")
            return

        total_pages = max(1, (len(df) + self._page_size - 1) // self._page_size)
        start = (self._current_page - 1) * self._page_size
        end = start + self._page_size
        view = df.iloc[start:end].copy()

        self.page_label.setText(f"{self._current_page} / {total_pages} (共{len(df)}条)")
        self.table_widget.setRowCount(len(view))
        self.table_widget.setColumnCount(len(view.columns))
        
        # 渲染带 ▲ ▼ 排序箭头的表头
        headers =[]
        for c in view.columns:
            if c == self._sort_col:
                headers.append(f"{c} {'▲' if self._sort_asc else '▼'}")
            else:
                headers.append(str(c))
        self.table_widget.setHorizontalHeaderLabels(headers)

        for r, row in enumerate(view.itertuples(index=False)):
            for c, val in enumerate(row):
                text_val = "" if pd.isna(val) else str(val)
                item = QTableWidgetItem(text_val)
                # 【新增】设置鼠标悬停提示（ToolTip），不用点击也能看全内容
                item.setToolTip(text_val) 
                self.table_widget.setItem(r, c, item)

    def _detect_export_format(self, dest: str):
        """根据文件扩展名返回 ('csv'|'xlsx'|'xls') 和对应的 pandas 写入参数"""
        ext = Path(dest).suffix.lower()
        if ext == '.xlsx':
            return 'xlsx', {'index': False, 'engine': 'openpyxl'}
        elif ext == '.xls':
            return 'xls', {'index': False}
        else:
            return 'csv', {'index': False, 'encoding': 'utf-8-sig'}

    def _export_current(self):
        df = self._tables.get(self._active_key, pd.DataFrame())
        if df.empty:
            QMessageBox.warning(self, "导出", "当前表为空。")
            return
        base_name = self._active_key.replace(' ', '_')
        dest, _ = QFileDialog.getSaveFileName(
            self, "导出当前表", f"{base_name}.csv",
            "CSV (*.csv);;Excel (*.xlsx);;Excel 97-2003 (*.xls);;所有文件 (*)"
        )
        if not dest:
            return
        fmt, kw = self._detect_export_format(dest)
        getattr(df, f'to_{fmt}')(dest, **kw)
        QMessageBox.information(self, "导出成功", f"文件已保存至:\n{dest}")

    def _export_all(self):
        fmt_name, ok = QInputDialog.getItem(
            self, "选择导出格式", "请选择批量导出的文件格式:",
            ["CSV (.csv)", "Excel (.xlsx)", "Excel 97-2003 (.xls)"], 0, False
        )
        if not ok:
            return
        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not dir_path:
            return
        ext_map = {"CSV": ".csv", "Excel": ".xlsx", "Excel 97-2003": ".xls"}
        ext = next((v for k, v in ext_map.items() if k in fmt_name), ".csv")
        export_dir = Path(dir_path)
        exported = []
        for name, df in self._tables.items():
            if df.empty:
                continue
            dest = export_dir / f"{name.replace(' ', '_')}{ext}"
            fmt, kw = self._detect_export_format(str(dest))
            getattr(df, f'to_{fmt}')(dest, **kw)
            exported.append(dest.name)
        if exported:
            QMessageBox.information(self, "导出成功", "成功导出以下文件:\n" + "\n".join(exported))
        else:
            QMessageBox.warning(self, "导出", "无数据可导出。")


class MainWindow(QMainWindow):
    """基于浏览器多标签模式的 PyQt6 主窗口"""

    def __init__(self, services: AppServices):
        super().__init__()
        self._services = services
        self._last_checked_plate = ''  # 记录最后一次真伪查询的车牌号
        self.setWindowTitle("案件侦查数据分析系统")
        self.resize(1200, 800)
        self._build_ui()
        self._apply_readable_style()
        self._refresh_cases()

# 在 MainWindow 类中新增此方法
    def closeEvent(self, event):
        reply = self._centered_msgbox(
            QMessageBox.Icon.Question, "确认退出",
            "您确定要退出吗？\n未导出的分析结果将会丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ).exec()
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
    def _apply_readable_style(self):
        # 使用 SVG 文件路径替代 data: URL，避免 Qt CSS 解析器中分号截断问题
        _res = _resource_dir()
        _down = (_res + '/chevron-down.svg').replace('\\', '/')
        _up = (_res + '/chevron-up.svg').replace('\\', '/')

        self.setStyleSheet(f"""
            QWidget {{ font-size: 14px; color: #334155; }}
            QTableWidget {{ font-size: 12px; }}

            QPushButton {{
                min-height: 32px; padding: 6px 14px; border-radius: 4px;
                background-color: #ffffff; border: 1px solid #cbd5e1;
                color: #0f172a; text-align: center;
            }}
            QPushButton {{ background-color: #2563eb; color: white; border: none; font-weight: bold; border-radius: 4px; padding: 6px 16px; }}
            QPushButton:hover {{ background-color: #3b82f6; }}
            QPushButton:pressed {{ background-color: #1d4ed8; }}

            QLineEdit, QComboBox, QDateEdit, QSpinBox {{
                min-height: 30px; border: 1px solid #cbd5e1; border-radius: 4px;
                padding: 0 8px; background-color: #ffffff;
            }}
            QSpinBox, QDateEdit, QComboBox {{ padding-right: 28px; }}

            /* ================= 核心修复：彻底隐藏日期框的上下调节按钮 ================= */
            QDateEdit::up-button, QDateEdit::down-button {{
                width: 0px; height: 0px; border: none; background: none; image: none;
            }}

            /* ================= 下拉按钮 (日历/下拉框) ================= */
            QComboBox::drop-down, QDateEdit::drop-down {{
                subcontrol-origin: padding; subcontrol-position: top right;
                width: 24px; border-left: 1px solid #cbd5e1;
                background-color: #f1f5f9; border-top-right-radius: 3px; border-bottom-right-radius: 3px;
            }}
            QComboBox::drop-down:hover, QDateEdit::drop-down:hover {{ background-color: #e2e8f0; }}
            QComboBox::down-arrow, QDateEdit::down-arrow {{
                width: 12px; height: 12px;
                image: url("{_down}");
            }}

            /* ================= SpinBox 上下调节按钮 ================= */
            QSpinBox::up-button {{
                subcontrol-origin: border; subcontrol-position: top right; width: 22px;
                border-left: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1;
                background-color: #f1f5f9; border-top-right-radius: 3px;
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border; subcontrol-position: bottom right; width: 22px;
                border-left: 1px solid #cbd5e1; background-color: #f1f5f9; border-bottom-right-radius: 3px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: #e2e8f0; }}

            QSpinBox::up-arrow {{
                width: 10px; height: 10px;
                image: url("{_up}");
            }}
            QSpinBox::down-arrow {{
                width: 10px; height: 10px;
                image: url("{_down}");
            }}

            QGroupBox {{
                font-size: 15px; font-weight: bold; margin-top: 25px; padding-top: 15px;
                border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; subcontrol-position: top left; left: 15px; top: 0px;
                padding: 0 8px; color: #0f172a;
            }}
            QTabWidget::pane {{ border: 1px solid #e2e8f0; background: #ffffff; border-radius: 4px; }}
            QTabBar::tab {{
                background: #f1f5f9; padding: 8px 16px; margin-right: 2px;
                border: 1px solid #e2e8f0; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{ background: #ffffff; font-weight: bold; color: #2563eb; padding-bottom: 9px; }}
        """)

    def _build_ui(self):
        # 使用 QTabWidget 作为主容器，模拟浏览器标签页
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self.tabs)

        # 固定的第一页：工作台
        self.workspace = QWidget()
        self._build_workspace(self.workspace)
        self.tabs.addTab(self.workspace, "主界面")
        # 禁用关闭第一个标签页
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition.RightSide, None)

        self.setStatusBar(QStatusBar(self))

    def _close_tab(self, index: int):
        if index > 0:  # 工作台不允许关闭
            self.tabs.removeTab(index)

    def _build_workspace(self, parent_widget: QWidget):
        """按照 PPT 顺序梳理出的工作台布局"""
        layout = QVBoxLayout(parent_widget)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)

        # ================== 准备工作 ==================
        prep_group = QGroupBox(" 第一步：案件准备与数据导入")
        p_layout = QHBoxLayout(prep_group)
        self.case_input = QLineEdit(placeholderText="输入案件名称或ID")
        self.case_combo = QComboBox()
        self.case_combo.textActivated.connect(self._on_case_selected)  # 仅用户交互触发，不响程序化修改
        btn_create = QPushButton("新建案件")
        btn_create.clicked.connect(self._create_case)
        btn_upload = QPushButton("选择并导入数据文件 (.xls/.csv)")
        btn_upload.clicked.connect(self._upload_files)

        p_layout.addWidget(QLabel("当前案件:"))
        p_layout.addWidget(self.case_combo)
        p_layout.addWidget(self.case_input)
        p_layout.addWidget(btn_create)
        p_layout.addSpacing(30)
        p_layout.addWidget(btn_upload)
        content_layout.addWidget(prep_group)

        # ================== 基础信息 ==================
        info_group = QGroupBox(" 第二步：嫌疑人基础信息录入")
        i_layout = QHBoxLayout(info_group)
        
        # 左：案发记录
        i_left = QVBoxLayout()
        row_pt = QHBoxLayout()
        self.point_date = QDateEdit()
        self.point_date.setCalendarPopup(True)
        self.point_date.setDate(QDate(2013, 11, 18))  # 默认案发时间
        self.point_date.setMinimumWidth(140)
        self.point_city = QLineEdit(placeholderText="案发城市")
        btn_add_pt = QPushButton("添加记录")
        btn_add_pt.clicked.connect(self._add_case_point)
        btn_clr_pt = QPushButton("清空")
        btn_clr_pt.clicked.connect(self._clear_case_points)
        row_pt.addWidget(self.point_date)
        row_pt.addWidget(self.point_city)
        row_pt.addWidget(btn_add_pt)
        row_pt.addWidget(btn_clr_pt)
        i_left.addLayout(row_pt)
        self.case_points_list = QListWidget()
        self.case_points_list.setMaximumHeight(120)
        i_left.addWidget(self.case_points_list)
        
        # 右：画像约束
        i_right = QFormLayout()
        self.gender = QComboBox(); self.gender.addItems(["", "男性", "女性"])
        self.region = QComboBox(); self.region.addItems(["", "北方", "南方"])
        self.rental_company = QLineEdit(placeholderText="选填")
        self.car_brand = QLineEdit(placeholderText="选填")
        i_right.addRow("嫌疑人性别:", self.gender)
        i_right.addRow("嫌疑人户籍:", self.region)
        i_right.addRow("嫌疑车辆租赁公司:", self.rental_company)
        i_right.addRow("嫌疑车辆品牌:", self.car_brand)
        
        i_layout.addLayout(i_left, 1)
        i_layout.addLayout(i_right, 1)
        content_layout.addWidget(info_group)

        # 同步按钮（Step 2 正下方居中）
        sync_bar = QHBoxLayout()
        sync_bar.addStretch()
        btn_sync = QPushButton("将嫌疑人基础信息同步至该案件")
        btn_sync.clicked.connect(self._on_sync_button_clicked)
        sync_bar.addWidget(btn_sync)
        sync_bar.addStretch()
        content_layout.addLayout(sync_bar)

       # ================== 核心分析(三大侦查区域) ==================
        flow_label = QLabel(" 第三步：核心侦查查询 ")
        flow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; margin-top: 10px;")
        content_layout.addWidget(flow_label)

        # 采用双栏布局
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        content_layout.addLayout(cards_layout)

        left_col = QVBoxLayout()
        right_col = QVBoxLayout()
        cards_layout.addLayout(left_col, 1)
        cards_layout.addLayout(right_col, 1)

        def _make_action(title, widget_layout, obj_name="ActionBtn"):
            btn = QPushButton(title)
            btn.setObjectName(obj_name)
            widget_layout.addWidget(btn)
            return btn

        # ═══════════════════════════════════════════════════
        # Area 1: 链式侦查流程 (左列)
        # ═══════════════════════════════════════════════════
        area1_label = QLabel("▌侦查流程")
        area1_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2563eb; margin-top: 5px;")
        left_col.addWidget(area1_label)

        # --- Step 1: 航班嫌疑人查询 ---
        card_flight = QGroupBox("Step 1: 航班嫌疑人查询")
        l_flight = QVBoxLayout(card_flight)
        btn_flight = _make_action("航班嫌疑人查询", l_flight)
        btn_flight.clicked.connect(lambda: self._run_chain_flight())
        left_col.addWidget(card_flight)

        # --- Step 2: 汽车租赁查询 (使用航班时间窗) ---
        card_rental = QGroupBox("Step 2: 汽车租赁查询")
        l_rental = QVBoxLayout(card_rental)
        self.rental_start_label = QLabel("起租时间来源: (请先执行航班查询)")
        self.rental_start_label.setStyleSheet("color: #64748b; font-size: 13px; font-weight: normal;")
        l_rental.addWidget(self.rental_start_label)
        self.rental_end_label = QLabel("停租时间来源: (请先执行航班查询)")
        self.rental_end_label.setStyleSheet("color: #64748b; font-size: 13px; font-weight: normal;")
        l_rental.addWidget(self.rental_end_label)
        btn_rental = _make_action("嫌疑人租赁车辆信息查询", l_rental)
        btn_rental.clicked.connect(lambda: self._run_chain_rental())
        left_col.addWidget(card_rental)

        left_col.addStretch()

        # ═══════════════════════════════════════════════════
        # Area 2: 团伙分析 (右列上半)
        # ═══════════════════════════════════════════════════
        area2_label = QLabel("▌团伙分析")
        area2_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2563eb; margin-top: 5px;")
        right_col.addWidget(area2_label)

        # --- 嫌疑团伙住宿查询 ---
        card_gang_c = QGroupBox("嫌疑团伙住宿查询")
        l_gang_c = QVBoxLayout(card_gang_c)
        l_gang_c.addWidget(QLabel("根据已录入的案发地点和时间，查询嫌疑团伙多个案发地的住宿信息"))
        btn_hotel = _make_action("嫌疑团伙住宿查询", l_gang_c)
        btn_hotel.clicked.connect(lambda: self._run_analysis("嫌疑团伙住宿查询", self._services.run_hotel))
        right_col.addWidget(card_gang_c)

        right_col.addSpacing(15)

        # ═══════════════════════════════════════════════════
        # Area 3: 车辆与轨迹侦查 (右列下半)
        # ═══════════════════════════════════════════════════
        area3_label = QLabel("▌车辆与轨迹侦查")
        area3_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2563eb; margin-top: 5px;")
        right_col.addWidget(area3_label)

        card_vehicle = QGroupBox("涉案车辆与轨迹追踪")
        l_vehicle = QVBoxLayout(card_vehicle)
        l_vehicle.setSpacing(12)

        # 3.1 模糊搜索
        v_box1 = QVBoxLayout()
        v_box1.addWidget(QLabel("第一步：嫌疑车牌模糊搜索"))
        r_plate = QHBoxLayout()
        self.plate_pattern = QLineEdit(placeholderText="输入已知车牌片段 (如:辽A)")
        r_plate.addWidget(self.plate_pattern)
        btn_plate = _make_action("嫌疑车牌模糊查询", r_plate)
        btn_plate.clicked.connect(lambda: self._run_analysis("嫌疑车牌模糊查询", lambda: self._services.run_plate_search(self.plate_pattern.text())))
        v_box1.addLayout(r_plate)
        l_vehicle.addLayout(v_box1)


        right_col.addWidget(card_vehicle)
        right_col.addStretch()

        # 封口及添加滚动条包裹
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    # ================= 业务方法 =================
    def _centered_msgbox(self, icon: QMessageBox.Icon, title: str, text: str,
                         buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok) -> QMessageBox:
        """创建居中于父窗口的提示框"""
        msg = QMessageBox(icon, title, text, buttons, self)
        center = self.geometry().center()
        size = msg.sizeHint()
        msg.move(center.x() - size.width() // 2, center.y() - size.height() // 2)
        return msg

    def _show_center_info(self, title: str, text: str) -> None:
        self._centered_msgbox(QMessageBox.Icon.Information, title, text).exec()

    def _show_center_warning(self, title: str, text: str) -> None:
        self._centered_msgbox(QMessageBox.Icon.Warning, title, text).exec()

    def _show_center_critical(self, title: str, text: str) -> None:
        self._centered_msgbox(QMessageBox.Icon.Critical, title, text).exec()

    def _show_center_question(self, title: str, text: str,
                               buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) -> QMessageBox.StandardButton:
        return self._centered_msgbox(QMessageBox.Icon.Question, title, text, buttons).exec()

    def _ensure_active_case(self) -> bool:
        """确保当前有活跃案件，如果没有则弹出警告并返回False。"""
        try:
            self._services.current_state()
            return True
        except RuntimeError:
            self._show_center_warning("提示", "请先新建或选择一个案件，再执行操作。")
            return False

    def _refresh_cases(self) -> None:
        cases = self._services.list_cases()
        self.case_combo.blockSignals(True)
        self.case_combo.clear()
        self.case_combo.addItems(cases)
        self.case_combo.blockSignals(False)
        self._refresh_case_points()

    def _refresh_case_points(self) -> None:
        # 手动逐项移除，避免 clear() 与 setItemWidget() 交互导致的闪退
        while self.case_points_list.count():
            self.case_points_list.takeItem(0)
        try:
            points = self._services.current_state()["case_points"]
        except:
            points = []

        # 构建 × 图标路径（修复下拉选项的同逻辑：用 SVG 文件替代内联文本）
        _x_path = _resource_dir() + '/x-mark.svg'

        for i, (d, c) in enumerate(points):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 0, 4, 0)
            row_layout.setSpacing(6)
            row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            btn_del = QPushButton()
            btn_del.setFixedSize(22, 22)
            btn_del.setIcon(QIcon(_x_path))
            btn_del.setIconSize(QSize(16, 16))
            btn_del.setFlat(True)
            btn_del.setStyleSheet(
                "QPushButton { border: none; background: transparent; }"
                "QPushButton:hover { background: #fee2e2; border-radius: 3px; }"
            )
            btn_del.clicked.connect(lambda checked, idx=i: self._remove_case_point(idx))

            label = QLabel(f"{d} - {c}")

            row_layout.addWidget(btn_del)
            row_layout.addWidget(label)
            row_layout.addStretch()

            item = QListWidgetItem(self.case_points_list)
            self.case_points_list.setItemWidget(item, row_widget)

    def _remove_case_point(self, index: int) -> None:
        self._services.remove_case_point(index)
        self._refresh_case_points()

    def _create_case(self) -> None:
        """新建案件：从输入框读取案件ID创建新案件，不允许重复"""
        case_id = self.case_input.text().strip()
        if not case_id:
            self._show_center_warning( "提示", "请在输入框中填写要新建的案件名称或ID。")
            return
        if case_id in self._services.list_cases():
            self._show_center_warning( "提示", f"案件「{case_id}」已存在，请更换名称。")
            return
        self._services.create_case(case_id)
        self.case_input.clear()
        self._refresh_cases()
        self.case_combo.setCurrentText(case_id)
        self.statusBar().showMessage(f"案件已创建: {case_id}", 3000)

    def _on_case_selected(self, case_id: str) -> None:
        """下拉框选择案件 → 自动切换并刷新主界面"""
        if not case_id:
            return
        self._services.switch_case(case_id)
        self._refresh_main_interface()
        self.statusBar().showMessage(f"当前案件为: {case_id}", 5000)

    def _refresh_main_interface(self) -> None:
        """切换案件后刷新主界面：案发记录、画像字段、时间窗标签"""
        self._refresh_case_points()
        # 从 state 恢复画像字段
        try:
            state = self._services.current_state()
            self.gender.setCurrentText(state.get('profile_gender', ''))
            self.region.setCurrentText(state.get('profile_region', ''))
            self.rental_company.setText(state.get('rental_company', ''))
            self.car_brand.setText(state.get('car_brand', ''))
        except RuntimeError:
            pass
        # 重置链式侦查时间窗标签
        self.rental_start_label.setText("起租时间来源: (请先执行航班查询)")
        self.rental_end_label.setText("停租时间来源: (请先执行航班查询)")

    def _on_sync_button_clicked(self) -> None:
        if not self._ensure_active_case():  # 没有活跃案件时弹窗警告，防止闪退
            return
        self._sync_profiles_silent()
        self._show_center_info("同步完成", "嫌疑人信息已同步到当前案件，请继续下一步查询。")

    def _sync_profiles_silent(self) -> None:
        self._services.set_profiles(
            self.gender.currentText(), self.region.currentText(),
            self.rental_company.text(), self.car_brand.text()
        )

    def _add_case_point(self) -> None:
        city = self.point_city.text().strip()
        if not city:
            self._show_center_warning( "提示", "案发城市不能为空。")
            return
        try:
            self._services.add_case_point(self.point_date.date().toString("yyyy-MM-dd"), city)
        except RuntimeError:
            self._show_center_warning( "提示", "请先创建或切换到一个案件，才能添加案发记录。")
            return
        self.point_city.clear()
        self._refresh_case_points()

    def _clear_case_points(self) -> None:
        if not self._ensure_active_case():  # 没有活跃案件时弹窗警告，防止闪退
            return
        self._services.clear_case_points()
        self._refresh_case_points()
        self._show_center_info( "提示", "案发记录已清空。")

    def _upload_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "选择数据文件", "", "Data (*.xlsx *.xls *.csv);;All (*)")
        if not files: return
        progress = QProgressDialog("正在导入文件...", "取消", 0, len(files), self)
        progress.setWindowTitle("上传")
        progress.setModal(True)
        progress.show()

        def _step(idx, total, name):
            progress.setMaximum(total)
            progress.setLabelText(f"处理: {name} ({idx}/{total})")
            progress.setValue(idx)
            QApplication.processEvents()

        try:
            summary = self._services.upload_files_with_progress(files, _step)
            # 统计每个文件导入的行数
            frames = self._services.current_state().get('uploaded_frames', {})
            row_details = []
            for fname, df in frames.items():
                row_details.append(f"   {fname}: {len(df)} 条")
            msg = f"成功导入 {summary['succeeded']} 个文件，失败 {summary['failed']} 个。\n\n各文件导入行数:\n" + "\n".join(row_details)
            if summary.get("errors"):
                msg += "\n\n部分失败原因:\n" + "\n".join(summary["errors"][:5])
            self._show_center_info("导入结果", msg)
        except Exception as e:
            self._show_center_critical( "导入失败", str(e))
        finally:
            progress.close()

    # ================= 异步分析核心流 =================
    def _run_analysis(self, title: str, fn: Callable) -> None:
        if not self._ensure_active_case():  # 没有活跃案件时弹窗警告，防止闪退
            return
        self._sync_profiles_silent() # 每次查前静默同步一次参数
        
        self.progress_dialog = QProgressDialog(f"正在查询【{title}】\n请耐心等待...", None, 0, 0, self)
        self.progress_dialog.setWindowTitle("后台计算中")
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()

        self.worker = AnalysisWorker(title, fn)
        self.worker.finished_sig.connect(self._on_analysis_finished)
        self.worker.error_sig.connect(self._on_analysis_error)
        self.worker.start()

    def _on_analysis_finished(self, title: str, result_df: pd.DataFrame) -> None:
        self.progress_dialog.close()

        # 依据不同查询类型决定数据负载和操作按钮
        data_payload = result_df
        bottom_widget = None

        descriptions = None

        if title == "航班嫌疑人分析":
            data_payload = self._services.get_flight_tables()
            # 更新主界面的时间窗标签
            earliest, latest = self._services.get_flight_earliest_latest()
            if earliest and latest:
                self.flight_time_label.setText(f"交叉表时间窗: {earliest[:16]} ~ {latest[:16]}")
                self.rental_start_label.setText(f"起租时间来源: 航班嫌疑人最早到达时间 → {earliest[:16]}")
                self.rental_end_label.setText(f"停租时间来源: 航班嫌疑人最晚离开时间 → {latest[:16]}")
            # 构建三张表的来源描述
            first_date, last_date = self._services.get_case_point_date_range()
            if first_date and last_date:
                descriptions = {
                    "到达乘客（案发前）": f"根据首案时间，以下乘客在 {first_date} 及之前到达案发城市/案发城市附近有机场的城市：",
                    "离开乘客（案发后）": f"根据末案时间，以下乘客在 {last_date} 及之后离开案发城市/案发城市附近有机场的城市：",
                    "交叉比对嫌疑人": "对前两张表取交集，得出以下同时满足到达与离开条件的嫌疑人：",
                }

        elif title == "汽车租赁查询":
            # 在租车结果页嵌入司机住宿查询组件
            bottom_widget = self._make_lodging_query_widget()

        elif title == "司机住宿查询(姓名)" or title == "司机住宿查询(身份证)":
            # 获取双路查询结果
            data_payload = self._services.get_lodging_dual_results()

        elif title == "嫌疑车牌模糊查询":
            # 在车牌模糊查询结果页嵌入案发相邻时间段筛查组件
            bottom_widget = self._make_trajectory_search_widget()

        elif title == "案发相邻时间段筛查":
            # 在轨迹结果页嵌入车辆真伪查询组件
            bottom_widget = self._make_vehicle_check_widget()

        # 生成操作按钮
        action_buttons = self._get_action_buttons_for(title)

        # 生成查询总结文字
        summary_text = self._build_summary_text(title, result_df if isinstance(result_df, pd.DataFrame) else pd.DataFrame())

        # 生成标签页
        tab = ResultTabWidget(title, data_payload, self._services.current_case_cache_dir(),
                              action_buttons=action_buttons, bottom_widget=bottom_widget,
                              descriptions=descriptions, summary_text=summary_text)
        idx = self.tabs.addTab(tab, f" {title}")
        self.tabs.setCurrentIndex(idx)

        self.statusBar().showMessage(f"【{title}】完成", 5000)

        # 特殊处理: 真伪查询完成后弹窗告知结果
        if title == "车辆真伪查询":
            is_fake = self._services.get_plate_verification_alert()
            if is_fake:
                self._show_center_warning( "核查结论", "该车牌在机动车登记库和租赁库中均无记录，疑似假牌/套牌！")
            else:
                self._show_center_info( "核查结论", "该车牌在备案库中有记录，为真牌。详见结果页。")

    def _get_action_buttons_for(self, title: str) -> list:
        """根据查询类型返回结果页上的'下一步'操作按钮"""
        mapping = {
            "航班嫌疑人分析": [],
            "汽车租赁查询": [],  # 司机住宿查询已嵌入结果页底部
            "司机住宿查询(姓名)": [
                ("→ 下一步：司机关联嫌疑人住宿查询", lambda: self._run_analysis("司机关联嫌疑人住宿查询", self._services.run_cohabit_from_lodging)),
            ],
            "司机住宿查询(身份证)": [
                ("→ 下一步：司机关联嫌疑人住宿查询", lambda: self._run_analysis("司机关联嫌疑人住宿查询", self._services.run_cohabit_from_lodging)),
            ],
            "司机关联同住查询": [],
            "嫌疑团伙住宿查询": [],
            "嫌疑车牌模糊查询": [],  # 案发相邻时间段筛查已嵌入结果页底部
            "案发相邻时间段筛查": [],  # 车辆真伪查询已嵌入结果页底部
        }
        return mapping.get(title, [])

    def _build_summary_text(self, title: str, result_df: pd.DataFrame) -> str:
        """根据查询类型和结果数据，生成查询总结文字。
        在结果表格下方展示，帮助用户快速理解锁定的嫌疑人或核查结论。"""
        state = self._services.current_state()

        if title == "航班嫌疑人分析":
            df = state.get('flight_suspect_cross', pd.DataFrame())
            if not df.empty and '姓名' in df.columns:
                names = df['姓名'].dropna().unique().tolist()
                if names:
                    display = "、".join(names[:20])
                    suffix = "..." if len(names) > 20 else ""
                    return f"交叉表锁定嫌疑人（共{len(names)}人）：{display}{suffix}"
            return "交叉表锁定嫌疑人：无"

        elif title == "汽车租赁查询":
            # 提示用户使用下方的住宿查询功能进一步锁定嫌疑人
            drivers = state.get('rental_driver_suspects', [])
            if drivers:
                return "提示：嫌疑人租车后可能在不同地点住宿，请在下方「司机住宿查询」中选择司机，查询其住宿记录，以便通过同住关系锁定更多团伙成员。"
            return ""

        elif title in ("司机住宿查询(姓名)", "司机住宿查询(身份证)"):
            # 提示用户嫌疑人可能使用假身份证登记，建议交叉查询
            if title == "司机住宿查询(身份证)":
                return "提示：嫌疑人可能使用假身份证登记住宿，建议同时尝试按姓名查询，交叉验证结果。"
            elif title == "司机住宿查询(姓名)":
                return "提示：按姓名查询可能匹配到多名同名人，建议结合身份证号进一步筛选确认。"

        elif title == "司机关联同住查询":
            if not result_df.empty and '姓名' in result_df.columns:
                if '同住关系' in result_df.columns:
                    cohabit_names = result_df[result_df['同住关系'] != '本人']['姓名'].dropna().unique().tolist()
                else:
                    cohabit_names = result_df['姓名'].dropna().unique().tolist()
                if cohabit_names:
                    display = "、".join(cohabit_names[:20])
                    suffix = "..." if len(cohabit_names) > 20 else ""
                    return f"同住嫌疑人（共{len(cohabit_names)}人）：{display}{suffix}"
            return ""

        elif title == "嫌疑团伙住宿查询":
            if not result_df.empty and '姓名' in result_df.columns:
                names = result_df['姓名'].dropna().unique().tolist()
                # 去重（保持出现顺序）
                names_dedup = list(dict.fromkeys(names))
                if names_dedup:
                    display = "、".join(names_dedup[:20])
                    suffix = "..." if len(names_dedup) > 20 else ""
                    return f"锁定嫌疑人（共{len(names_dedup)}人）：{display}{suffix}"
            return ""

        elif title == "车辆真伪查询":
            plate = getattr(self, '_last_checked_plate', '未知车牌')
            is_fake = state.get('plate_verification_alert', False)
            if is_fake:
                return f"核查结论：车牌【{plate}】在机动车登记库和租赁库中均无记录，疑似假牌/套牌！"
            else:
                return f"核查结论：车牌【{plate}】在备案库中有记录，为真牌。详见结果页。"

        return ""

    # ── Area 1: 链式侦查流程 handlers ─────────────────

    def _run_chain_flight(self) -> None:
        """执行航班查询，完成后自动更新时间窗显示"""
        self._run_analysis("航班嫌疑人分析", self._services.run_flight)

    def _run_chain_rental(self) -> None:
        """执行租车查询（使用航班时间窗），然后填充司机下拉框"""
        self._run_analysis("汽车租赁查询", self._services.run_rental)

    def _on_chain_lodging_selected(self, index: int) -> None:
        """下拉框选择司机时，自动填充姓名和身份证号（绑定联动）"""
        if index < 0:
            return
        data = self.chain_lodging_combo.itemData(index)
        if data:
            name, id_ = data
            self.chain_lodging_name.setText(name)
            self.chain_lodging_id.setText(id_)

    def _run_chain_lodging_name(self) -> None:
        """按姓名查询司机住宿"""
        name = self.chain_lodging_name.text().strip()
        if not name:
            self._show_center_warning( "提示", "请先在「选择司机嫌疑人」下拉框中选择司机。")
            return
        self._run_analysis("司机住宿查询(姓名)",
                           lambda: self._services.run_lodging_query('', name))

    def _run_chain_lodging_id(self) -> None:
        """按身份证查询司机住宿"""
        id_ = self.chain_lodging_id.text().strip()
        if not id_:
            self._show_center_warning( "提示", "请先在「选择司机嫌疑人」下拉框中选择司机。")
            return
        self._run_analysis("司机住宿查询(身份证)",
                           lambda: self._services.run_lodging_query(id_, ''))

    # ── Area 3: 车辆与轨迹 ────────────────────────────

    # ── 租车结果页：嵌入住宿查询控件 ─────────────────

    def _make_lodging_query_widget(self) -> QWidget:
        """构建司机住宿查询内联组件，嵌入租车查询结果页底部。
        包含下拉框（姓名↔身份证绑定）+ 双路查询按钮。
        """
        widget = QWidget()
        widget.setObjectName("LodgingQueryCard")
        widget.setStyleSheet(
            "QWidget#LodgingQueryCard { background-color: #e8f4fd; border: 1px solid #3b82f6; "
            "border-radius: 8px; padding: 10px; }"
        )
        layout = QVBoxLayout(widget)

        title_label = QLabel("司机住宿查询")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e40af;")
        layout.addWidget(title_label)

        self.result_lodging_combo = QComboBox()
        self.result_lodging_combo.setPlaceholderText("选择司机嫌疑人")
        self.result_lodging_combo.currentIndexChanged.connect(self._on_result_lodging_selected)
        layout.addWidget(self.result_lodging_combo)

        form = QFormLayout()
        self.result_lodging_name = QLineEdit()
        self.result_lodging_name.setReadOnly(True)
        self.result_lodging_id = QLineEdit()
        self.result_lodging_id.setReadOnly(True)
        form.addRow("姓名:", self.result_lodging_name)
        form.addRow("身份证:", self.result_lodging_id)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_name = QPushButton("按姓名查询住宿")
        btn_name.setObjectName("ActionBtn")
        btn_name.clicked.connect(lambda: self._run_result_lodging_name())
        btn_id = QPushButton("按身份证查询住宿")
        btn_id.setObjectName("ActionBtn")
        btn_id.clicked.connect(lambda: self._run_result_lodging_id())
        btn_row.addWidget(btn_name)
        btn_row.addWidget(btn_id)
        layout.addLayout(btn_row)

        self._populate_result_lodging_combo()
        return widget

    def _populate_result_lodging_combo(self) -> None:
        """从 state 读取租车司机嫌疑人填充下拉框"""
        suspects = self._services.get_rental_driver_suspects()
        self.result_lodging_combo.blockSignals(True)
        self.result_lodging_combo.clear()
        if suspects:
            for name, id_ in suspects:
                self.result_lodging_combo.addItem(f"{name} ({id_})", (name, id_))
            self.result_lodging_combo.setCurrentIndex(-1)
        else:
            self.result_lodging_combo.setPlaceholderText("未找到司机嫌疑人")
        self.result_lodging_combo.blockSignals(False)

    def _on_result_lodging_selected(self, index: int) -> None:
        """结果页下拉框选择司机 → 自动填充姓名/身份证"""
        if index < 0:
            return
        data = self.result_lodging_combo.itemData(index)
        if data:
            name, id_ = data
            self.result_lodging_name.setText(name)
            self.result_lodging_id.setText(id_)

    def _run_result_lodging_name(self) -> None:
        """从结果页触发按姓名查询住宿"""
        name = self.result_lodging_name.text().strip()
        if not name:
            self._show_center_warning( "提示", "请先在下拉框中选择司机。")
            return
        self._run_analysis("司机住宿查询(姓名)",
                           lambda: self._services.run_lodging_query('', name))

    def _run_result_lodging_id(self) -> None:
        """从结果页触发按身份证查询住宿"""
        id_ = self.result_lodging_id.text().strip()
        if not id_:
            self._show_center_warning( "提示", "请先在下拉框中选择司机。")
            return
        self._run_analysis("司机住宿查询(身份证)",
                           lambda: self._services.run_lodging_query(id_, ''))

    def _make_trajectory_search_widget(self) -> QWidget:
        """构建案发相邻时间段筛查内联组件，嵌入车牌模糊查询结果页底部。
        用户可选择起始/结束日期，默认取案发首末时间。
        """
        widget = QWidget()
        widget.setObjectName("TrajSearchCard")
        widget.setStyleSheet(
            "QWidget#TrajSearchCard { background-color: #e8f4fd; border: 1px solid #3b82f6; "
            "border-radius: 8px; padding: 10px; }"
        )
        layout = QVBoxLayout(widget)

        title_row = QHBoxLayout()
        title_label = QLabel("案发相邻时间段筛查")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e40af;")
        hint_label = QLabel("基于模糊搜索结果，按案发相邻时间段进一步筛查嫌疑车辆的轨迹信息")
        hint_label.setStyleSheet("color: #64748b; font-size: 13px;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        title_row.addWidget(hint_label)
        layout.addLayout(title_row)

        # 日期选择行
        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("起始日期:"))
        self.traj_start_date = QDateEdit()
        self.traj_start_date.setCalendarPopup(True)
        self.traj_start_date.setDisplayFormat("yyyy-MM-dd")
        date_row.addWidget(self.traj_start_date)
        date_row.addSpacing(20)
        date_row.addWidget(QLabel("结束日期:"))
        self.traj_end_date = QDateEdit()
        self.traj_end_date.setCalendarPopup(True)
        self.traj_end_date.setDisplayFormat("yyyy-MM-dd")
        date_row.addWidget(self.traj_end_date)
        date_row.addStretch()

        btn_search = QPushButton("查询轨迹")
        btn_search.setObjectName("ActionBtn")
        btn_search.setMinimumHeight(36)
        btn_search.clicked.connect(lambda: self._run_trajectory_search())
        date_row.addWidget(btn_search)
        layout.addLayout(date_row)

        # 从案发点设置默认日期
        self._set_traj_default_dates()
        return widget

    def _set_traj_default_dates(self) -> None:
        """根据案发点设置轨迹查询的默认起止日期"""
        try:
            state = self._services.current_state()
            if state and state.get('case_points'):
                dates = [pd.to_datetime(p[0]) for p in state['case_points']]
                earliest = min(dates)
                latest = max(dates)
                self.traj_start_date.setDate(QDate(earliest.year, earliest.month, earliest.day))
                self.traj_end_date.setDate(QDate(latest.year, latest.month, latest.day))
                return
        except Exception:
            pass
        # 回退到当天
        today = QDate.currentDate()
        self.traj_start_date.setDate(today)
        self.traj_end_date.setDate(today)

    def _run_trajectory_search(self) -> None:
        """从车牌模糊查询结果页触发案发相邻时间段筛查"""
        start_str = self.traj_start_date.date().toString("yyyy-MM-dd")
        end_str = self.traj_end_date.date().toString("yyyy-MM-dd")
        self._run_analysis("案发相邻时间段筛查",
                           lambda: self._services.run_spatial(start_str, end_str))

    def _make_vehicle_check_widget(self) -> QWidget:
        """构建车辆真伪查询内联组件，嵌入轨迹筛查结果页底部。"""
        widget = QWidget()
        widget.setStyleSheet(
            "QWidget#VehicleCheckCard { background-color: #fef3c7; border: 1px solid #f59e0b; "
            "border-radius: 8px; padding: 10px; }"
        )
        widget.setObjectName("VehicleCheckCard")
        layout = QVBoxLayout(widget)

        title_row = QHBoxLayout()
        title_label = QLabel("嫌疑车辆真伪查询")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #92400e;")
        warn_label = QLabel("注意: 嫌疑人可能使用假牌/套牌车辆")
        warn_label.setStyleSheet("color: #dc2626; font-weight: bold; font-size: 13px;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        title_row.addWidget(warn_label)
        layout.addLayout(title_row)

        input_row = QHBoxLayout()
        self.traj_plate_input = QLineEdit()
        self.traj_plate_input.setPlaceholderText("输入完整嫌疑车牌号 (如: 辽A12345)")
        self.traj_plate_input.setMinimumHeight(36)
        self.traj_plate_input.setStyleSheet("font-size: 15px; padding: 4px 10px;")
        input_row.addWidget(self.traj_plate_input)

        btn_check = QPushButton("核查车牌号真伪")
        btn_check.setObjectName("ActionBtn")
        btn_check.setMinimumHeight(36)
        btn_check.clicked.connect(lambda: self._run_vehicle_check_from_traj())
        input_row.addWidget(btn_check)
        layout.addLayout(input_row)

        return widget

    def _run_vehicle_check_from_traj(self) -> None:
        """从轨迹结果页的嵌入组件触发车辆真伪查询"""
        plate = self.traj_plate_input.text().strip()
        if not plate:
            self._show_center_warning( "提示", "请输入需要核查的完整车牌号。")
            return
        self._last_checked_plate = plate  # 记录当前核查的车牌号供总结使用
        self._run_analysis("车辆真伪查询",
                           lambda: self._services.run_vehicle(plate))

    def _on_analysis_error(self, title: str, err: str) -> None:
        self.progress_dialog.close()
        # 弹窗提示，不生成新页面
        self._show_center_warning( f"【{title}】查询中止", f"提示信息：\n{err}")