本地桌面客户端
多线程异步
多案件并发查询
前端采用tkinter
后端py 无api接入
数据库mysql

本地数据目录约定见 `data/README.md`（`raw` / `cache` / `sample`）。

## 运行

```bash
python -m app.main
```

## 持久化与后续 MySQL 扩展

| 层次 | 说明 |
|------|------|
| 运行时状态 | `StateManager` / `AppState`：多案件内存隔离；案件信息、上传解析表、分析结果 DataFrame 默认仅存内存。 |
| 本地文件 | 原始上传字节：`data/raw/<案件ID>/`；结果导出：用户在「结果查看」中导出 CSV（默认目录见 `paths.cache_dir`）。 |
| 数据库 | `app/core/database.py` + `app/repo/*`：已接 SQLAlchemy + MySQL（`config.json` / 设置窗口与 `app/config_db.py` 环境变量）。当前分析链路**不**把结果表写入 DB；后续可在 `app.repo` 增加仓储，由服务层在任务完成或「归档」时写入，与现有 CSV 导出并存。 |

## 打包 Windows exe

1. 安装运行依赖与 PyInstaller：`python -m pip install -r requirements.txt -r requirements-build.txt`（`pymysql` 等需在**打包环境**中存在，否则 frozen 程序在连接 MySQL 时会失败）。
2. 在项目根目录执行：`pyinstaller case_analysis.spec --noconfirm`  
   或在 PowerShell 中：`.\scripts\build_exe.ps1`  
3. 产物：`dist/case_analysis.exe`（单文件、`console=False`）。首次运行需在 exe 同目录或用户目录提供可用的 `config.json` / `.env`（数据库与路径），或通过程序内「设置」保存配置。

## 测试

- 多案件状态隔离（`StateManager`）
- 异步任务执行与任务隔离（`TaskManager`）
- 关键业务分析链路可用性（轨迹 / 租赁 / 住宿 / 车辆 / 航班）

运行方式：

```bash
python -m unittest discover -s tests -v
```
