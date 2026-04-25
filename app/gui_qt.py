from __future__ import annotations

from typing import Callable

import pandas as pd
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services_ import AppServices


class MainWindow(QMainWindow):
    """PyQt6 MVP 主窗口：案件、上传、分析和结果查看。"""

    def __init__(self, services: AppServices):
        super().__init__()
        self._services = services
        self._result_df = pd.DataFrame()
        self.setWindowTitle("案件侦查分析系统 - PyQt6 MVP")
        self.resize(1200, 780)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        main = QVBoxLayout(root)

        main.addWidget(self._case_group())
        main.addWidget(self._upload_group())
        main.addWidget(self._case_info_group())
        main.addWidget(self._analysis_group())
        main.addWidget(self._result_group())

        self.setStatusBar(QStatusBar(self))
        self._refresh_cases()

    def _case_group(self) -> QGroupBox:
        box = QGroupBox("案件管理")
        row = QHBoxLayout(box)
        self.case_input = QLineEdit()
        self.case_input.setPlaceholderText("输入案件ID，如 case_001")
        self.case_combo = QComboBox()
        btn_new = QPushButton("新建/切换")
        btn_new.clicked.connect(self._create_or_switch_case)
        row.addWidget(QLabel("案件ID"))
        row.addWidget(self.case_input)
        row.addWidget(btn_new)
        row.addWidget(QLabel("当前案件"))
        row.addWidget(self.case_combo)
        return box

    def _upload_group(self) -> QGroupBox:
        box = QGroupBox("文件上传")
        row = QHBoxLayout(box)
        btn_upload = QPushButton("选择并导入文件")
        btn_upload.clicked.connect(self._upload_files)
        row.addWidget(btn_upload)
        return box

    def _case_info_group(self) -> QGroupBox:
        box = QGroupBox("案件信息")
        layout = QHBoxLayout(box)

        left = QVBoxLayout()
        point_row = QHBoxLayout()
        self.point_date = QDateEdit()
        self.point_date.setCalendarPopup(True)
        self.point_date.setDate(QDate.currentDate())
        self.point_city = QLineEdit()
        self.point_city.setPlaceholderText("案发城市或区域")
        btn_add = QPushButton("添加案发点")
        btn_add.clicked.connect(self._add_case_point)
        btn_clear = QPushButton("清空案发点")
        btn_clear.clicked.connect(self._clear_case_points)
        point_row.addWidget(self.point_date)
        point_row.addWidget(self.point_city)
        point_row.addWidget(btn_add)
        point_row.addWidget(btn_clear)
        left.addLayout(point_row)
        self.case_points_list = QListWidget()
        left.addWidget(self.case_points_list)

        right = QFormLayout()
        self.gender = QComboBox()
        self.gender.addItems(["", "男性", "女性"])
        self.region = QComboBox()
        self.region.addItems(["", "北方", "南方"])
        self.rental_company = QLineEdit()
        self.car_brand = QLineEdit()
        btn_sync = QPushButton("同步画像到状态")
        btn_sync.clicked.connect(self._sync_profiles)
        right.addRow("性别", self.gender)
        right.addRow("户籍", self.region)
        right.addRow("租赁公司", self.rental_company)
        right.addRow("车辆品牌", self.car_brand)
        right.addRow(btn_sync)

        layout.addLayout(left, 3)
        layout.addLayout(right, 2)
        return box

    def _analysis_group(self) -> QGroupBox:
        box = QGroupBox("分析执行")
        layout = QVBoxLayout(box)

        r1 = QHBoxLayout()
        btn_flight = QPushButton("航班分析")
        btn_flight.clicked.connect(lambda: self._run("航班分析", self._services.run_flight))
        self.plate_pattern = QLineEdit()
        self.plate_pattern.setPlaceholderText("车牌模糊片段")
        btn_plate = QPushButton("车牌搜索")
        btn_plate.clicked.connect(
            lambda: self._run("车牌搜索", lambda: self._services.run_plate_search(self.plate_pattern.text()))
        )
        self.buffer_days = QSpinBox()
        self.buffer_days.setRange(0, 30)
        self.buffer_days.setValue(0)
        btn_spatial = QPushButton("时空分析")
        btn_spatial.clicked.connect(
            lambda: self._run("时空分析", lambda: self._services.run_spatial(self.buffer_days.value()))
        )
        r1.addWidget(btn_flight)
        r1.addWidget(self.plate_pattern)
        r1.addWidget(btn_plate)
        r1.addWidget(QLabel("缓冲天数"))
        r1.addWidget(self.buffer_days)
        r1.addWidget(btn_spatial)

        r2 = QHBoxLayout()
        btn_rental = QPushButton("租赁分析")
        btn_rental.clicked.connect(lambda: self._run("租赁分析", self._services.run_rental))
        self.lodging_id = QLineEdit()
        self.lodging_id.setPlaceholderText("住宿查询身份证")
        self.lodging_name = QLineEdit()
        self.lodging_name.setPlaceholderText("住宿查询姓名")
        btn_lodging = QPushButton("住宿查询")
        btn_lodging.clicked.connect(
            lambda: self._run(
                "住宿查询",
                lambda: self._services.run_lodging_query(self.lodging_id.text(), self.lodging_name.text()),
            )
        )
        r2.addWidget(btn_rental)
        r2.addWidget(self.lodging_id)
        r2.addWidget(self.lodging_name)
        r2.addWidget(btn_lodging)

        r3 = QHBoxLayout()
        btn_cohabit = QPushButton("同住分析")
        btn_cohabit.clicked.connect(lambda: self._run("同住分析", self._services.run_cohabit))
        btn_hotel = QPushButton("住宿渗透")
        btn_hotel.clicked.connect(lambda: self._run("住宿渗透", self._services.run_hotel))
        self.vehicle_plate = QLineEdit()
        self.vehicle_plate.setPlaceholderText("核查车牌")
        btn_vehicle = QPushButton("车辆核查")
        btn_vehicle.clicked.connect(
            lambda: self._run("车辆核查", lambda: self._services.run_vehicle(self.vehicle_plate.text()))
        )
        r3.addWidget(btn_cohabit)
        r3.addWidget(btn_hotel)
        r3.addWidget(self.vehicle_plate)
        r3.addWidget(btn_vehicle)

        layout.addLayout(r1)
        layout.addLayout(r2)
        layout.addLayout(r3)
        return box

    def _result_group(self) -> QGroupBox:
        box = QGroupBox("结果表")
        layout = QVBoxLayout(box)
        self.result_hint = QLabel("执行分析后在此显示结果")
        self.result_table = QTableWidget()
        layout.addWidget(self.result_hint)
        layout.addWidget(self.result_table)
        return box

    def _refresh_cases(self) -> None:
        cases = self._services.list_cases()
        self.case_combo.blockSignals(True)
        self.case_combo.clear()
        self.case_combo.addItems(cases)
        self.case_combo.blockSignals(False)
        self._refresh_case_points()

    def _refresh_case_points(self) -> None:
        self.case_points_list.clear()
        try:
            points = self._services.current_state()["case_points"]
        except Exception:
            points = []
        for d, c in points:
            self.case_points_list.addItem(f"{d} - {c}")

    def _create_or_switch_case(self) -> None:
        case_id = self.case_input.text().strip() or self.case_combo.currentText().strip()
        if not case_id:
            QMessageBox.warning(self, "提示", "请先输入案件ID。")
            return
        self._services.create_case(case_id)
        self._refresh_cases()
        self.case_combo.setCurrentText(case_id)
        self.statusBar().showMessage(f"当前案件: {case_id}", 5000)

    def _sync_profiles(self) -> None:
        self._services.set_profiles(
            self.gender.currentText(),
            self.region.currentText(),
            self.rental_company.text(),
            self.car_brand.text(),
        )
        self.statusBar().showMessage("画像条件已同步", 3000)

    def _add_case_point(self) -> None:
        city = self.point_city.text().strip()
        if not city:
            QMessageBox.warning(self, "提示", "案发城市不能为空。")
            return
        self._services.add_case_point(self.point_date.date().toString("yyyy-MM-dd"), city)
        self.point_city.clear()
        self._refresh_case_points()

    def _clear_case_points(self) -> None:
        self._services.clear_case_points()
        self._refresh_case_points()

    def _upload_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择数据文件",
            "",
            "Data Files (*.xlsx *.xls *.csv);;All Files (*)",
        )
        if not files:
            return
        summary = self._services.upload_files(files)
        msg = (
            f"导入完成 成功 {summary['succeeded']} 失败 {summary['failed']} "
            f"本案累计表格 {summary['frames_in_state']}"
        )
        self.statusBar().showMessage(msg, 8000)
        if summary["errors"]:
            QMessageBox.warning(self, "部分文件失败", "\n".join(summary["errors"][:8]))

    def _run(self, title: str, fn: Callable[[], pd.DataFrame]) -> None:
        try:
            self._sync_profiles()
            self._result_df = fn()
            self._render_df(self._result_df)
            self.statusBar().showMessage(f"{title} 完成，结果 {len(self._result_df)} 行", 8000)
        except Exception as e:
            QMessageBox.critical(self, f"{title}失败", str(e))

    def _render_df(self, df: pd.DataFrame) -> None:
        if df is None or df.empty:
            self.result_hint.setText("无结果")
            self.result_table.clear()
            self.result_table.setRowCount(0)
            self.result_table.setColumnCount(0)
            return

        self.result_hint.setText(f"共 {len(df)} 行，显示前 500 行")
        view = df.head(500).copy()
        self.result_table.setRowCount(len(view))
        self.result_table.setColumnCount(len(view.columns))
        self.result_table.setHorizontalHeaderLabels([str(c) for c in view.columns])

        for r, row in enumerate(view.itertuples(index=False)):
            for c, val in enumerate(row):
                self.result_table.setItem(r, c, QTableWidgetItem("" if pd.isna(val) else str(val)))
