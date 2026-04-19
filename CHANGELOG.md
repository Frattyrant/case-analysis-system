# Changelog

本文件用于记录项目每次功能修改与修复。

## 2026-04-18

### Added
- 新增 `app/utils/loading_visualizer.py`，提供统一加载可视化驱动。
- 新增 `tests/test_state_manager.py`，覆盖多案件状态隔离与切换逻辑。
- 新增 `tests/test_task_manager.py`，覆盖异步执行与同案件分组隔离。
- 新增 `tests/test_modules_pipeline.py`，覆盖核心分析链路可用性验证。

### Changed
- `app/core/task_manager.py` 升级为按 `case_id + group` 隔离的异步任务管理。
- `app/gui/analysis_panel.py` 改为后台任务执行 + 主线程轮询，避免 UI 卡死。
- `app/modules/*` 接入统一进度驱动接口，保留原有 `run()` 风格。
- `README.md` 增加测试说明与运行命令。

### Fixed
- 修复后台线程直接更新 Tk 组件的风险，改为主线程 `drain()` 刷新进度。

## 2026-04-19

### Added
- 新增 `app/data_paths.py`，约定 `data/raw`、`data/cache`、`data/sample` 及按案件子目录落盘/导出。
- 新增 `data/raw/`、`data/cache/`、`data/sample/` 目录说明与占位；`data/README.md` 描述数据层结构。
- 新增 `tests/test_data_paths.py`，校验路径解析、建目录与原始文件落盘。
- 异常体系补充：`MissingFieldError`、`InvalidTimeFormatError`；`AppError` / 部分异常支持 `cause` 链式原因。
- 新增根目录 `.gitignore`，默认忽略 `logs/`、`__pycache__/` 等常见噪声文件。

### Changed
- `app/config_manager.py`：默认路径改为 `data_root` / `raw_dir` / `cache_dir` / `sample_dir`，并迁移旧版 `upload_dir` / `export_dir`。
- `app/main.py`：启动时 `ensure_data_dirs`，保证配置的数据目录存在；GUI 入口改为直接 `MainWindow(config_manager).mainloop()`（与 `MainWindow` 继承 `tk.Tk` 一致）。
- `app/gui/upload_panel.py`：增加「导入到案件」按钮；导入时同步写入 `raw/<案件ID>/`；补全 `StateManager` 引用。
- `app/gui/result_panel.py`：导出 CSV 默认打开 `cache/<案件ID>/`。
- `app/gui/setting_windows.py`：路径设置页改为 raw / cache / sample 三项。
- `app/exceptions/*`：精简类说明、统一四类业务错误（数据为空、字段缺失、时间/日期格式、模块执行失败）表述与 `code`。
- `README.md`：补充指向 `data/README.md` 的说明。

### Fixed
- `app/gui/result_panel.py`：从 `AppState` 读取结果改为 `state[key]`（原 `.get()` 在 `AppState` 上不可用，会导致加载失败）；结果表格与滚动条放入独立 `Frame` 并用 `grid` 布局，避免将滚动条挂在 `Treeview` 子级导致布局异常。

### Changed（同日 GUI 整理）
- `app/gui/analysis_panel.py`：抽取 `_require_case_id()`，统一「未选案件」提示与早退逻辑。
- `app/gui/main_window.py`：新建案件对话框改为模态（`transient` / `grab_set`），移除未接入业务逻辑的「描述」输入。
- `app/gui/setting_windows.py`：路径浏览统一使用 `from tkinter import filedialog`。
- `app/gui/result_panel.py`：移除未使用的 `Path` 导入。
