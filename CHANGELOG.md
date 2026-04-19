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

## 2026-04-19

### Added
- `app/gui/case_info_panel.py`：「案件信息」标签页；`app/utils/case_points_text.py` 与 `tests/test_case_points_text.py`。
- `launcher.py`、`case_analysis.spec`、`scripts/build_exe.ps1`、`requirements-build.txt`、`requirements.txt`：exe 构建与依赖清单。

### Changed
- `app/gui/main_window.py`：主笔记本增加「案件信息」页；新建案件后自动刷新各面板。
- `app/gui/case_info_panel.py`：交互对齐 `demo1_1 (3).py` 中 `CaseInfoUI`（案发城市 + 日期 + 确认添加、只读列表、画像下拉、完成 / 清空确认）。
- `app/gui/result_panel.py`：类文档说明分析结果以 CSV 导出为主、与后续入库扩展的边界。
- `app/core/database.py`：模块文档补充持久化分层与后续 MySQL 接入建议。
- `README.md`：运行方式、持久化、打包与测试；补充项目现状与缺口、目录职责表、面向界面同学的协作说明。

### Fixed
- `case_analysis.spec`：用 `collect_all` 收集 `sqlalchemy` / `pymysql`，避免单文件 exe 启动时报 `No module named 'sqlalchemy'`；`scripts/build_exe.ps1` 在 PyInstaller 前校验依赖可导入。
- `requirements.txt` / `requirements-build.txt`：首行注释改为 ASCII，避免简体中文注释在 GBK 默认编码下导致 `pip install -r` 解码失败，从而漏装运行依赖。

## 2026-04-19

### Added
- `tests/test_upload_module.py`：覆盖 CSV 的 utf-8-sig 与 GBK 解码。

### Changed
- `app/modules/upload_module.py`：CSV 依次尝试 utf-8-sig、utf-8、gb18030、gbk、cp936；`process_files` 返回 `errors` 明细，并将 `total_files` 修正为本批文件数，补充 `frames_in_state`。
- `app/gui/upload_panel.py`：上传结束弹窗列出失败原因（最多 10 条）；状态栏区分本批文件数与已载入表数；存在失败时用警告框提示。

### Fixed
- 修复公安业务常见「从 Excel 另存为 CSV（ANSI/GBK）」时仅按 utf-8 读取导致全部解析失败、界面只显示成功数却无原因的问题。
- `.xls`：支持「实为 xlsx 的 ZIP」与「HTML 表格伪 .xls」（`xlrd` 失败时回退 `read_html`+`lxml`）；`apply_schema` 在列数多于模板时截取前 N 列以兼容多出序号列等导出；新增运行依赖 `lxml`，`case_analysis.spec` 中一并收集进 exe。

## 2026-04-19

### Added
- `requirements.txt`：`cpca`、`airportsdata`，供航班地理匹配；`case_analysis.spec` 增加对 `cpca` 的打包收集。
- 上传结果返回 `per_file_rows`，弹窗与状态栏列出本批每个成功导入表的行数。

### Changed
- `app/gui/main_window.py` + `case_info_panel.py`：分析执行前 `flush_case_info_to_state()`，将画像/租赁/车辆等从界面写回 `AppState`，避免未点「完成」导致仍用空画像或旧值。
- `app/modules/flight_module.py`：`到达地` 同时支持 IATA 与中文地名解析省份；案发省解析失败时回退为不按省筛选并提示；身份证号列归一化；无结果时设置 `last_diag` 说明原因。
- `app/modules/rental_module.py`：无匹配时 `last_diag` 说明时间窗与筛选条件。
- `app/gui/analysis_panel.py`：结果为空时弹窗附带模块 `last_diag` 说明。

### Fixed
- 航班分析在缺少 `cpca` 时 `target_provinces` 为空导致「到达地」全部不匹配、结果恒为空的问题（改为解析失败时暂不按省过滤并提示安装依赖）。
- **租赁与航班衔接**：`demo1_1 (3).py` 中租赁仅用案发 `earliest`/`latest` 卡起租；现改为在存在航班碰撞表 `flight_suspect_cross` 时，用「进入」侧 `航班日期_进入` 约束起租（按日不晚于抵达日），停租仍须 ≥ 末案日；航班分析每次结束写入/清空该表。新增 `SlotSpec('flight_suspect_cross')`。
