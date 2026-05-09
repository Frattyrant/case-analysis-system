# app/main.py
"""
桌面端程序入口。
职责：
  1. 注册所有业务字段（SlotSpec）
  2. 初始化数据库连接
  3. 启动主窗口
"""
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication

from app.core.state_manager import StateManager, SlotSpec
from app.core.database import init_db
from app.utils.logger import get_logger
from app.config_manager import ConfigManager
from app.data_paths import ensure_data_dirs, paths_from_config
from app.gui_qt import MainWindow
from app.services_ import AppServices

import pandas as pd 

logger = get_logger(__name__)


def _register_slots() -> None:
    """集中注册所有业务字段，对应 notebook Cell 2 的注册表。"""
    StateManager.register([
        # 文件上传模块
        SlotSpec('uploaded_frames',             dict,           '原始数据表 {filename: DataFrame}'),

        # 案件信息模块
        SlotSpec('case_points',                 list,           '案发记录 [(日期, 城市), ...]'),
        SlotSpec('profile_gender',              str,            '嫌疑人性别'),
        SlotSpec('profile_region',              str,            '嫌疑人户籍'),
        SlotSpec('rental_company',              str,            '租赁公司名称'),
        SlotSpec('car_brand',                   str,            '车辆品牌'),

        # 轨迹模块
        SlotSpec('matched_plates',              list,           '模糊搜索出的车牌号'),

        # 航班碰撞结果（供租赁等模块按「抵达时间」约束起租）
        SlotSpec('flight_enter_candidates',  pd.DataFrame, '航班到达乘客信息（首案日前到达）'),
        SlotSpec('flight_leave_candidates',  pd.DataFrame, '航班离开乘客信息（末案日后离开）'),
        SlotSpec('flight_suspect_cross',     pd.DataFrame, '航班到达、离开交叉嫌疑人表'),

        # 租赁模块
        SlotSpec('df_real_car',                 pd.DataFrame,   '租赁全库匹配正式名单'),
        SlotSpec('rental_trajectory_suspects',  list,           '租赁期内有轨迹记录的租车人姓名'),

        # 住宿 / 车辆核查模块
        SlotSpec('current_lodging_res',         pd.DataFrame,   '住宿档案或车辆核查结果'),

        # ── 链式侦查流程 ──
        # 航班 → 租车 时间窗
        SlotSpec('flight_earliest_arrival',  str,          '航班交叉表最早到达时间'),
        SlotSpec('flight_latest_departure',  str,          '航班交叉表最晚离开时间'),

        # 租车 → 住宿 司机嫌疑人下拉框
        SlotSpec('rental_driver_suspects',   list,         '租赁司机嫌疑人 [(姓名, 身份证号), ...]'),

        # 住宿 姓名/身份证双路查询
        SlotSpec('lodging_driver_result_by_name', pd.DataFrame, '按司机姓名查询的住宿记录'),
        SlotSpec('lodging_driver_result_by_id',   pd.DataFrame, '按司机身份证查询的住宿记录'),

        # 车辆轨迹
        SlotSpec('plate_verification_alert', bool,         '假牌警告标记'),
    ])


def main() -> None:
    # 1. 初始化配置管理器（兼容 PyInstaller：exe 目录即根目录）
    if getattr(sys, 'frozen', False):
        _root = Path(sys.executable).resolve().parent
    else:
        _root = Path(__file__).resolve().parent.parent
    config_path = _root / 'config.json'
    config_manager = ConfigManager(config_path)
    ensure_data_dirs(paths_from_config(config_manager))

    # 2. 注册字段（必须在任何 state 操作之前）
    _register_slots()
    logger.info("字段注册完成，共 %d 个 slot", len(StateManager.registered_keys()))

    # 3. 初始化数据库（建表、检查连接）
    try:
        init_db()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error("数据库初始化失败: %s", e)

    # 4. 启动 PyQt6 应用
    app = QApplication(sys.argv)
    services = AppServices(paths_from_config(config_manager))
    window = MainWindow(services)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()