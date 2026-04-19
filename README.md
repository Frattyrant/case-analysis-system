# 案件侦查数据分析系统（桌面端）

面向公安辅助研判场景的 **Windows 桌面程序**：用 Python 写好业务逻辑和界面，**没有单独的 Web 前端工程**，也没有对外 HTTP API。你看到的窗口是 **Tkinter**（Python 自带）画的，界面代码和后端逻辑在同一个仓库里，只是按文件夹分了职责。

---

## 写给负责界面 / 交互的同学（前端视角）

这里说的「前端」= **客户端界面与体验**（`app/gui/` 里的 Tkinter），不是 Vue/React 网页。后端同事已经把 **多案件、上传、案件信息录入、各类分析、结果表格与 CSV 导出、异步不卡界面** 等主线跑通；你可以在不动或少动业务算法的前提下，继续改布局、配色、文案、交互细节、空状态提示等。

### 后端已经做到哪了（你可以直接基于现状改 UI）

- **主窗口**：菜单（新建案件、设置）、当前案件下拉、删除案件；主区域多个标签页。
- **文件上传**：选文件 → 导入到当前案件；文件会落到本地 `data/raw/<案件ID>/`，表格读进内存里的 `AppState`。
- **案件信息**：与早期 Colab demo 接近的录入方式（案发城市 + 日期 + 确认添加、画像下拉、完成 / 清空等）。
- **分析功能**：航班、轨迹（车牌搜索 / 时空）、租赁、住宿（查询 / 同住 / 渗透）、车辆核查等；**后台线程跑分析**，界面用进度条 + 轮询，避免长时间卡死。
- **结果查看**：对若干类结果用表格分页展示，并支持 **导出 CSV**（分析结果**默认不写数据库**，只导出文件）。
- **设置**：数据库连接、本地路径（raw / cache / sample）等。
- **多案件**：内存里按 `case_id` 隔离；切换案件会刷新各面板。
- **数据库**：MySQL + SQLAlchemy 已接好，用于建表、配置和部分仓储代码；**分析结果链路尚未接「自动入库」**。
- **打包**：可按文档打出 `dist/case_analysis.exe`（单文件）。

### 还差什么 / 当前限制（方便你对齐预期）

- **界面技术栈是 Tkinter**，不是现代 Web；美化空间有限，但布局、组件组合、提示文案仍可优化。
- **结果面板**目前只对少数几种 DataFrame 结果做了表格 + CSV；其它类型（例如列表类字段）没有统一结果页。
- **案件与状态**关闭程序后默认不持久化（除已落盘的上传原始文件和导出的 CSV）；「下次打开自动恢复上次案件」这类要另做。
- **ORM / `app/repo`** 里已有任务、结果等模型，**与分析主流程的自动写库尚未打通**；若要做「历史任务列表」「结果归档到库」，需要和后端一起定接口再改界面。

### 你可以继续做什么（建议方向）

- 优化 **布局与间距**、主窗口默认大小、标签页顺序、按钮禁用态（无案件时灰掉等）。
- 加强 **引导与校验**：必填项、格式错误时的就地提示（不仅 `messagebox`）。
- **结果查看**：增加更多结果类型、空数据占位图、列宽自适应、导出格式选项等（需与 `AppState` 里注册的字段对齐）。
- **无障碍 / 操作流**：快捷键、最近使用案件、操作确认文案统一等。
- 若团队后续切 **Web + API**，当前 `app/modules/`、`StateManager` 仍是很好的业务核心，界面可整体替换；现阶段只改 `app/gui/` 即可尽量少碰算法。

**改界面时建议**：优先只动 `app/gui/`；若要从界面调新的后端能力，和后端说一声在 `modules` 或 `StateManager` 加稳接口再绑按钮。

---

## 写给全栈 / 后端：项目里都有啥

| 路径 | 作用（通俗说） |
|------|----------------|
| **`app/main.py`** | 程序入口：注册业务字段、建数据目录、尝试连库、启动主窗口。 |
| **`app/gui/`** | **所有窗口和面板**（主窗口、上传、案件信息、分析、结果、设置）。负责展示和点按钮；重活交给 `TaskManager` + `modules`。 |
| **`app/core/`** | **核心基础设施**：`state_manager` 多案件内存状态；`task_manager` 后台线程跑分析；`database` MySQL 连接与建表；`cache_manager` 等。 |
| **`app/modules/`** | **具体分析算法**（航班、轨迹、租赁、住宿、车辆、上传解析等），从 `AppState` 读数据、写回结果。 |
| **`app/repo/`** | **数据库表对应的增删改查**（SQLAlchemy 模型与 Repository）；目前偏「基建」，分析结果自动落库未接完。 |
| **`app/utils/`** | **通用工具**：日志、身份证/画像筛选、地理、时间、案发点文本解析、加载进度驱动等。 |
| **`app/exceptions/`** | **业务与系统异常类型**，方便统一报错码或日志。 |
| **`app/data_paths.py`** | **本地目录约定**（raw / cache / sample、按案件子目录），和 `config_manager` 里的路径配置一起用。 |
| **`app/config_manager.py`** | **读写 `config.json`**（路径、数据库等用户可保存配置）。 |
| **`app/config_db.py`** | **数据库连接串、连接池等**默认值（也可被 `.env` 覆盖）。 |
| **`tests/`** | **自动化测试**：状态管理、任务管理、数据路径、案发点文本、模块管线等。 |
| **`data/`** | **运行时产生的数据目录**：原始上传、缓存、样例数据说明见 `data/README.md`。 |
| **`scripts/`** | **构建脚本**（例如打 exe 的 PowerShell）。 |
| **`launcher.py`** | 给 PyInstaller 用的启动壳，转调 `app.main`。 |
| **`case_analysis.spec`** | PyInstaller 打包描述文件。 |
| **`requirements.txt`** | Python 运行依赖（pandas、SQLAlchemy、pymysql 等）。 |
| **`requirements-build.txt`** | 仅打包 exe 时需要（PyInstaller）。 |
| **`CHANGELOG.md`** | 每次较大改动时的变更记录。 |

根目录下 **`config.json`**（若存在）一般由程序内「设置」生成，**不要提交真实密码到 Git**。

---

## 技术栈一览（简短）

- **界面**：Tkinter / ttk  
- **语言**：Python 3  
- **数据**：pandas、本地目录、`config.json` / `.env`  
- **数据库**：MySQL（PyMySQL + SQLAlchemy 2）  
- **异步**：`concurrent.futures` 线程池 + 主线程轮询更新 UI  

---

## 运行

```bash
python -m app.main
```

本地数据目录约定见 `data/README.md`（`raw` / `cache` / `sample`）。

---

## 持久化与后续 MySQL 扩展

| 层次 | 说明 |
|------|------|
| 运行时状态 | `StateManager` / `AppState`：多案件内存隔离；案件信息、上传解析表、分析结果 DataFrame 默认仅存内存。 |
| 本地文件 | 原始上传字节：`data/raw/<案件ID>/`；结果导出：用户在「结果查看」中导出 CSV（默认目录见 `paths.cache_dir`）。 |
| 数据库 | `app/core/database.py` + `app/repo/*`：已接 SQLAlchemy + MySQL（`config.json` / 设置窗口与 `app/config_db.py` 环境变量）。当前分析链路**不**把结果表写入 DB；后续可在 `app.repo` 增加仓储，由服务层在任务完成或「归档」时写入，与现有 CSV 导出并存。 |

---

## 打包 Windows exe

1. 安装运行依赖与 PyInstaller：`python -m pip install -r requirements.txt -r requirements-build.txt`（`pymysql` 等需在**打包环境**中存在，否则 frozen 程序在连接 MySQL 时会失败）。
2. 在项目根目录执行：`pyinstaller case_analysis.spec --noconfirm`  
   或在 PowerShell 中：`.\scripts\build_exe.ps1`  
3. 产物：`dist/case_analysis.exe`（单文件、`console=False`）。首次运行需在 exe 同目录或用户目录提供可用的 `config.json` / `.env`（数据库与路径），或通过程序内「设置」保存配置。

---

## 测试

覆盖要点：多案件状态隔离（`StateManager`）、异步任务与分组隔离（`TaskManager`）、数据路径与上传落盘、案发点文本解析、核心分析管线可用性等。

```bash
python -m pytest tests/ -q
```

或使用 unittest：

```bash
python -m unittest discover -s tests -v
```
