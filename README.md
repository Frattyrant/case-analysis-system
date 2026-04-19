本地桌面客户端
多线程异步
多案件并发查询
前端采用tkinter
后端py 无api接入
数据库mysql

本地数据目录约定见 `data/README.md`（`raw` / `cache` / `sample`）。

## 测试

- 多案件状态隔离（`StateManager`）
- 异步任务执行与任务隔离（`TaskManager`）
- 关键业务分析链路可用性（轨迹 / 租赁 / 住宿 / 车辆 / 航班）

运行方式：

```bash
python -m unittest discover -s tests -v
```
