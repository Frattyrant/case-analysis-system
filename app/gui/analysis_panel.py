from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING
from concurrent.futures import Future

from app.core.task_manager import get_task_manager
from app.core.state_manager import StateManager
from app.modules.flight_module import FlightAnalysis
from app.modules.trajectory_module import PlateSearchAnalysis, SpatialPenetrationAnalysis
from app.modules.rental_module import RentalAnalysis
from app.modules.lodging_module import LodgingQueryAnalysis, CohabitAnalysis, HotelPenetrationAnalysis
from app.modules.vehicle_module import PlateVerificationAnalysis
from app.utils.loading_visualizer import LoadingDriver

if TYPE_CHECKING:
    from app.gui.main_window import MainWindow


class AnalysisPanel(ttk.Frame):
    """分析功能面板。"""

    def __init__(self, parent: ttk.Frame, main_window: 'MainWindow'):
        """
        初始化分析面板。

        Args:
            parent: 父容器
            main_window: 主窗口
        """
        super().__init__(parent)
        self.main_window = main_window
        self._progress_ui = {}
        self._task_manager = get_task_manager()
        self._create_widgets()

    def _create_widgets(self) -> None:
        """创建面板组件。"""
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        flight_frame = ttk.Frame(notebook)
        trajectory_frame = ttk.Frame(notebook)
        rental_frame = ttk.Frame(notebook)
        lodging_frame = ttk.Frame(notebook)
        vehicle_frame = ttk.Frame(notebook)

        notebook.add(flight_frame, text="航班分析")
        notebook.add(trajectory_frame, text="轨迹分析")
        notebook.add(rental_frame, text="租赁分析")
        notebook.add(lodging_frame, text="住宿分析")
        notebook.add(vehicle_frame, text="车辆核查")

        self._create_flight_tab(flight_frame)
        self._create_trajectory_tab(trajectory_frame)
        self._create_rental_tab(rental_frame)
        self._create_lodging_tab(lodging_frame)
        self._create_vehicle_tab(vehicle_frame)

    def _create_flight_tab(self, parent: ttk.Frame) -> None:
        """创建航班分析标签页。"""
        ttk.Button(parent, text="执行航班分析", command=self._on_flight_analysis, width=20).pack(pady=20)
        self._attach_progress_ui(parent, 'flight')

    def _create_trajectory_tab(self, parent: ttk.Frame) -> None:
        """创建轨迹分析标签页。"""
        input_frame = ttk.Frame(parent)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="车牌号:").pack(side='left', padx=5)
        self.plate_entry = ttk.Entry(input_frame, width=20)
        self.plate_entry.pack(side='left', padx=5)

        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="车牌搜索", command=self._on_plate_search, width=15).pack(side='left', padx=5)
        ttk.Button(button_frame, text="时空分析", command=self._on_spatial_analysis, width=15).pack(side='left', padx=5)
        self._attach_progress_ui(parent, 'trajectory')

    def _create_rental_tab(self, parent: ttk.Frame) -> None:
        """创建租赁分析标签页。"""
        ttk.Button(parent, text="执行租赁分析", command=self._on_rental_analysis, width=20).pack(pady=20)
        self._attach_progress_ui(parent, 'rental')

    def _create_lodging_tab(self, parent: ttk.Frame) -> None:
        """创建住宿分析标签页。"""
        input_frame = ttk.Frame(parent)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="身份证号:").pack(side='left', padx=5)
        self.id_entry = ttk.Entry(input_frame, width=20)
        self.id_entry.pack(side='left', padx=5)

        ttk.Label(input_frame, text="姓名:").pack(side='left', padx=5)
        self.name_entry = ttk.Entry(input_frame, width=20)
        self.name_entry.pack(side='left', padx=5)

        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="住宿查询", command=self._on_lodging_query, width=15).pack(side='left', padx=5)
        ttk.Button(button_frame, text="同住分析", command=self._on_cohabit_analysis, width=15).pack(side='left', padx=5)
        ttk.Button(button_frame, text="渗透分析", command=self._on_hotel_penetration, width=15).pack(side='left', padx=5)
        self._attach_progress_ui(parent, 'lodging')

    def _create_vehicle_tab(self, parent: ttk.Frame) -> None:
        """创建车辆核查标签页。"""
        input_frame = ttk.Frame(parent)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="车牌号:").pack(side='left', padx=5)
        self.vehicle_plate_entry = ttk.Entry(input_frame, width=20)
        self.vehicle_plate_entry.pack(side='left', padx=5)

        ttk.Button(parent, text="执行真伪核查", command=self._on_plate_verification, width=20).pack(pady=10)
        self._attach_progress_ui(parent, 'vehicle')

    def _attach_progress_ui(self, parent: ttk.Frame, key: str) -> None:
        """在标签页底部挂载统一进度组件。"""
        holder = ttk.Frame(parent)
        holder.pack(fill='x', padx=10, pady=5)
        status_var = tk.StringVar(value='待执行')
        ttk.Label(holder, textvariable=status_var).pack(anchor='w')
        bar = ttk.Progressbar(holder, orient='horizontal', mode='determinate', maximum=100)
        bar.pack(fill='x', pady=(2, 0))
        self._progress_ui[key] = {'bar': bar, 'status': status_var}

    def _get_driver(self, key: str) -> LoadingDriver:
        ui = self._progress_ui[key]
        ui['bar']['value'] = 0
        ui['status'].set('准备执行...')
        return LoadingDriver(ui['bar'], ui['status'], max_steps=100)

    def _require_case_id(self) -> str | None:
        case_id = self.main_window.get_current_case_id()
        if not case_id:
            messagebox.showwarning("警告", "请先创建案件")
            return None
        return case_id

    def _run_module_with_progress(
        self,
        group: str,
        module,
        state,
        success_msg: str,
        empty_msg: str,
        **kwargs
    ) -> None:
        """统一异步执行模块并驱动进度条。"""
        self.main_window.flush_case_info_to_state()
        driver = self._get_driver(group)
        module.set_progress_driver(driver)
        case_id = str(getattr(state, 'case_id', 'global'))
        task_id = f'{case_id}:{group}:{module.__class__.__name__}'
        try:
            future = self._task_manager.submit(
                task_id=task_id,
                module=module,
                state=state,
                group=group,
                **kwargs
            )
        except RuntimeError as exc:
            messagebox.showwarning("提示", str(exc))
            return
        self._poll_task(
            future=future,
            driver=driver,
            success_msg=success_msg,
            empty_msg=empty_msg,
            module=module,
        )

    def _poll_task(
        self,
        future: Future,
        driver: LoadingDriver,
        success_msg: str,
        empty_msg: str,
        module: object | None = None,
    ) -> None:
        """轮询后台任务，保持 UI 不阻塞。"""
        driver.drain()
        if not future.done():
            self.after(
                120,
                lambda: self._poll_task(future, driver, success_msg, empty_msg, module),
            )
            return
        try:
            result = future.result()
        except Exception as e:
            driver.error('执行失败')
            driver.drain()
            messagebox.showerror("错误", f"分析任务失败: {str(e)}")
            return
        driver.drain()
        if not result.empty:
            messagebox.showinfo("完成", success_msg.format(count=len(result)))
        else:
            diag = getattr(module, "last_diag", "") or ""
            body = empty_msg if not diag else f"{empty_msg}\n\n说明：{diag}"
            messagebox.showinfo("完成", body)

    def _on_flight_analysis(self) -> None:
        """执行航班分析。"""
        case_id = self._require_case_id()
        if not case_id:
            return

        try:
            state = StateManager.get(case_id)
            module = FlightAnalysis()
            self._run_module_with_progress(
                'flight',
                module,
                state,
                "航班分析完成，找到 {count} 条记录",
                "航班分析完成，未找到符合条件的记录"
            )
        except Exception as e:
            messagebox.showerror("错误", f"航班分析失败: {str(e)}")

    def _on_plate_search(self) -> None:
        """执行车牌搜索。"""
        case_id = self._require_case_id()
        if not case_id:
            return

        pattern = self.plate_entry.get().strip()
        if not pattern:
            messagebox.showwarning("警告", "请输入车牌号")
            return

        try:
            state = StateManager.get(case_id)
            module = PlateSearchAnalysis()
            self._run_module_with_progress(
                'trajectory',
                module,
                state,
                "车牌搜索完成，找到 {count} 条轨迹",
                "车牌搜索完成，未找到符合条件的轨迹",
                pattern=pattern
            )
        except Exception as e:
            messagebox.showerror("错误", f"车牌搜索失败: {str(e)}")

    def _on_spatial_analysis(self) -> None:
        """执行时空分析。"""
        case_id = self._require_case_id()
        if not case_id:
            return

        try:
            state = StateManager.get(case_id)
            module = SpatialPenetrationAnalysis()
            self._run_module_with_progress(
                'trajectory',
                module,
                state,
                "时空分析完成，找到 {count} 条关联轨迹",
                "时空分析完成，未找到关联轨迹"
            )
        except Exception as e:
            messagebox.showerror("错误", f"时空分析失败: {str(e)}")

    def _on_rental_analysis(self) -> None:
        """执行租赁分析。"""
        case_id = self._require_case_id()
        if not case_id:
            return

        try:
            state = StateManager.get(case_id)
            module = RentalAnalysis()
            self._run_module_with_progress(
                'rental',
                module,
                state,
                "租赁分析完成，找到 {count} 条记录",
                "租赁分析完成，未找到符合条件的记录"
            )
        except Exception as e:
            messagebox.showerror("错误", f"租赁分析失败: {str(e)}")

    def _on_lodging_query(self) -> None:
        """执行住宿查询。"""
        case_id = self._require_case_id()
        if not case_id:
            return

        id_val = self.id_entry.get().strip()
        name_val = self.name_entry.get().strip()

        if not id_val and not name_val:
            messagebox.showwarning("警告", "请输入身份证号或姓名")
            return

        try:
            state = StateManager.get(case_id)
            module = LodgingQueryAnalysis()
            self._run_module_with_progress(
                'lodging',
                module,
                state,
                "住宿查询完成，找到 {count} 条记录",
                "住宿查询完成，未找到符合条件的记录",
                id_val=id_val,
                name_val=name_val
            )
        except Exception as e:
            messagebox.showerror("错误", f"住宿查询失败: {str(e)}")

    def _on_cohabit_analysis(self) -> None:
        """执行同住分析。"""
        case_id = self._require_case_id()
        if not case_id:
            return

        try:
            state = StateManager.get(case_id)
            module = CohabitAnalysis()
            self._run_module_with_progress(
                'lodging',
                module,
                state,
                "同住分析完成，找到 {count} 条记录",
                "同住分析完成，未找到符合条件的记录"
            )
        except Exception as e:
            messagebox.showerror("错误", f"同住分析失败: {str(e)}")

    def _on_hotel_penetration(self) -> None:
        """执行住宿渗透分析。"""
        case_id = self._require_case_id()
        if not case_id:
            return

        try:
            state = StateManager.get(case_id)
            module = HotelPenetrationAnalysis()
            self._run_module_with_progress(
                'lodging',
                module,
                state,
                "住宿渗透分析完成，找到 {count} 条记录",
                "住宿渗透分析完成，未找到符合条件的记录"
            )
        except Exception as e:
            messagebox.showerror("错误", f"住宿渗透分析失败: {str(e)}")

    def _on_plate_verification(self) -> None:
        """执行车辆真伪核查。"""
        case_id = self._require_case_id()
        if not case_id:
            return

        plate = self.vehicle_plate_entry.get().strip()
        if not plate:
            messagebox.showwarning("警告", "请输入车牌号")
            return

        try:
            state = StateManager.get(case_id)
            module = PlateVerificationAnalysis()
            self._run_module_with_progress(
                'vehicle',
                module,
                state,
                "车辆核查完成，找到 {count} 条备案记录",
                "车辆核查完成，未找到备案记录（假牌）",
                plate=plate
            )
        except Exception as e:
            messagebox.showerror("错误", f"车辆核查失败: {str(e)}")

    def refresh(self) -> None:
        """刷新面板。"""
        pass