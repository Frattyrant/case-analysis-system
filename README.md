
基于 PyQt6 + pandas + SQLite 的桌面端侦查数据分析工具，支持多案件管理、链式侦查流程（航班→租车→住宿→同住）、团伙分析与车辆轨迹追踪。

<img width="2239" height="1299" alt="image" src="https://github.com/user-attachments/assets/dd8199f1-e37c-40e0-93ea-238d16fb5a2f" />


## 技术栈

| 分层 | 技术 |
|------|------|
| 前端 | PyQt6 |
| 后端 | Python 3.10+ |
| 数据库 | SQLite（默认）/ MySQL（可选） |


## 功能概览

### 链式侦查流程

1. **航班嫌疑人查询** — 根据案发城市定位目标机场，筛选到达/离开航班，交叉比对锁定航班乘客嫌疑人
2. **汽车租赁查询** — 利用航班交叉表时间窗，筛选嫌疑人（司机）租赁记录并关联轨迹
3. **司机住宿查询** — 支持按姓名/身份证号双路查询，交叉验证住宿记录
4. **同住关联分析** — 基于旅馆+入住时间段发现潜在同伙

### 团伙分析

- 嫌疑团伙住宿查询：在多个案发地附近旅馆中查找共同入住团伙嫌疑人

### 车辆与轨迹侦查

- **车牌模糊搜索**：输入车牌片段正则匹配
- **案发相邻时间段筛查**：按时间窗口+案发城市过滤轨迹
- **车辆真伪核查**：对比机动车登记库与租赁库，判定真假牌

## 使用流程

1. **新建案件** → 输入案件 ID/名称

<img width="892" height="48" alt="image" src="https://github.com/user-attachments/assets/63a2d7da-6565-4489-bccd-de5633b79ba8" />

2. **上传数据** → 选择 .xlsx/.xls/.csv 文件（文件名含"航班""租赁""旅店""轨迹""机动车"等关键字）

<img width="325" height="89" alt="image" src="https://github.com/user-attachments/assets/82bb1548-7aea-4f29-8cbf-6474e6bc5dae" />

3. **录入案发信息** → 添加案发日期与城市，录入嫌疑人画像（性别/户籍/车辆品牌/车辆公司等），并点击同步到此案件

<img width="2221" height="467" alt="image" src="https://github.com/user-attachments/assets/033c46d4-ebf4-4a54-a25d-49ab37f6537f" />

4. **执行查询流程** → 按主界面查询模块任意进行，结果以新TAB呈现，支持分页浏览、列排序、导出、复制文本等

<img width="2195" height="597" alt="image" src="https://github.com/user-attachments/assets/db54ebba-7b9b-4546-8976-fa8129d60c75" />

5. **导出结果** → 支持 CSV / Excel 单表导出或一键全导出

## 项目结构

```
project/
├── app/
│   ├── main.py                # 程序入口，字段注册，启动主窗口
│   ├── gui_qt.py              # PyQt6 主界面（工作台 + 多标签页 + 异步任务线程）
│   ├── services_.py           # 服务层（案件管理 + 分析模块调度）
│   ├── config_db.py           # 全局配置（路径/数据库/日志）
│   ├── data_paths.py          # 数据目录管理
│   ├── core/
│   │   ├── state_manager.py   # 多案件状态管理（SlotSpec 注册模式 + AppState 容器）
│   │   └── database.py        # 数据库初始化与连接
│   ├── modules/
│   │   ├── upload_module.py   # 文件上传与 Schema 匹配
│   │   ├── flight_module.py   # 航班嫌疑人分析
│   │   ├── rental_module.py   # 租赁全库匹配
│   │   ├── lodging_module.py  # 住宿查询 + 同住关联 + 渗透分析
│   │   ├── trajectory_module.py # 车牌模糊搜索 + 时空筛查
│   │   └── vehicle_module.py  # 车辆真伪核查
│   └── utils/
│       ├── geo_utils.py       # 地理工具（省份三层兜底 + 机场→城市映射）
│       ├── datetime_utils.py  # 日期向量化解析（多格式兼容）
│       └── identity_utils.py  # 身份证性别/籍贯提取
├── data/                      # 数据目录（数据库 + 缓存 + 原始文件）
├── config.json                # 用户配置文件
├── app.spec                   # PyInstaller 打包配置
└── requirements.txt
```

## 核心优化

航班筛选采用 **向量化 `.map()` 替代逐行 `.apply()`**：

| 方案 | 10万行耗时 | 原理 |
|------|-----------|------|
| `.apply(lambda)` 逐行 | ~30s | 每行一次 Python 函数调用（栈帧创建/GIL 竞争/对象装箱） |
| `.map(precomputed_dict)` | ~20ms | pandas C 层哈希表查表，只对去重后的唯一 IATA 码预计算 |

地理查询采用**三层兜底**：cpca 库解析 → 省份关键字匹配 → 城市→省份字典映射，结果自动缓存避免重复调用。
