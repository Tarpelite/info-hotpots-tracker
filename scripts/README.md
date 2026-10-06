# scripts — 科技战略情报数据处理脚本集

本目录存放科技信息战略情报系统启动数据（`20261005科技战略情报启动数据_v1`）的全部 Python 处理脚本，包含**提交流程的三个权威入口**，以及一个一阶段清洗工具包 `data_cleaning_v1/`。所有脚本只使用 Python 标准库，无需安装第三方依赖。

## 环境要求

- Python 3.12（当前验证版本；仅使用标准库，3.10 及以上原则上可运行）
- 运行位置：**工作区根目录**（即本 `scripts/` 文件夹的上一级，与 `20261005科技战略情报启动数据_v1/` 同级）
- 操作系统：Windows PowerShell（命令示例为 PowerShell 写法）

## 目录结构

```text
scripts/
├── README.md                 # 本说明文件
├── __init__.py               # 标识 scripts 为 Python 包
├── import_snapshot.py        # 提交流程入口 1：导入快照与采集数据，生成 data.json 及各表
├── validate_snapshot.py      # 提交流程入口 2：校验 data.json，输出通过/失败检查报告
├── build_map.py              # 提交流程入口 3：生成关系图谱、团队卡片与本地 HTML 预览
└── data_cleaning_v1/         # 一阶段清洗工具包（2026-10-06 起整合至本目录）
    ├── __init__.py
    ├── run_cleaning.py       # 一阶段清洗入口：只读清洗，输出规范化 CSV/JSONL
    ├── build_deliverables.py # 辅助脚本：生成候选团队/证据/关系等表（非提交流程入口）
    ├── config.py             # 默认输入/输出路径与预期记录数常量
    ├── evidence_cleaner.py   # news-data/fetch-*.json 证据数据读取与字段映射
    ├── team_cleaner.py       # 团队快照 data.teams / data.domains 读取与字段映射
    ├── organization.py       # 团队到六领域分类的映射、证据关联、覆盖度与资源表构建
    ├── taxonomy.py           # 六领域/子领域定义、旧领域 ID 对照与关键词推断规则
    ├── submission_schema.py  # 提交用四张表的列定义与行转换函数
    ├── io_utils.py           # JSON/JSONL/CSV 读写及文本规范化工具
    └── README.md             # 一阶段清洗的英文说明（历史文档，路径已同步更新）
```

## 提交流程（权威入口，按顺序执行）

以下命令均在**工作区根目录**执行。

### 第 1 步：导入与建表 —— import_snapshot.py

读取团队快照与 `news-data/fetch-*.json`，完成字段清洗、六领域映射、证据关联，
生成一份 `data.json` 和全部提交用表格。

```powershell
python scripts/import_snapshot.py --snapshot "20261005科技战略情报启动数据_v1/团队快照/team_snapshot_20261005.json"  --news-data "20261005科技战略情报启动数据_v1/news-data" --output "<输出目录>"
```

参数说明：

| 参数          | 必填 | 说明                                      |
| ------------- | ---- | ----------------------------------------- |
| `--snapshot`  | 是   | `team_snapshot_*.json` 团队快照文件路径   |
| `--news-data` | 是   | 包含 `fetch-*.json` 的 news-data 目录路径 |
| `--output`    | 是   | 产物输出目录（不存在会自动创建）          |

输出产物：`data.json`、`import_summary.json`、`teams.csv`、`evidence.csv`、`relations.csv`、`coverage.csv`、`deduplication.csv`（重复证据清单，不删除记录）、`missing_items.csv`（待补材料清单）、`resource_requirements.csv`。

### 第 2 步：校验 —— validate_snapshot.py

对第 1 步生成的 `data.json` 执行结构与业务规则校验。

```powershell
python scripts/validate_snapshot.py `
  --data "<输出目录>/data.json" `
  --output "<输出目录>/validation"
```

输出产物：`validation_report.json`（完整报告）、`validation_passed.csv`（通过项）、`validation_failed.csv`（失败项）。

### 第 3 步：生成图谱与预览 —— build_map.py

基于 `data.json` 生成领域关系图谱、团队卡片和可离线浏览的本地 HTML 预览。

```powershell
python scripts/build_map.py `
  --data "<输出目录>/data.json" `
  --output "<输出目录>/map_YYYYMMDD"
```

输出产物：`index.html`（本地预览首页）、`total_graph_YYYYMMDD.svg`（总图）、`domain_graph_*.svg`（分领域图）、`team_cards/`（团队卡片页面）、四张提交表副本以及自动生成的 `README.md`。

## 一阶段清洗工具包 data_cleaning_v1

提交流程之外，可单独运行一阶段只读清洗，用于检查原始数据质量：

```powershell
python scripts/data_cleaning_v1/run_cleaning.py
```

默认从 `20261005科技战略情报启动数据_v1/` 读取，输出到 `20261005科技战略情报清洗结果_v1/`，也可用 `--source-root`、`--output-root` 覆盖。预期记录数（团队 344、领域 6、子领域 27、fetch 文件 49、证据 30842）定义在[config.py](data_cleaning_v1/config.py) 中，运行后会在 `cleaning_summary.json`里比对实际值与预期值。

输出目录说明：

- `normalized/`：三张规范化 CSV（团队、领域、证据）
- `raw_preserved/`：对应 JSONL，每条记录保留完整 `raw_record` 原始字段
- `diagnostics/validation_issues.jsonl`：字段缺失、标识异常、重复 ID 等问题清单
- `cleaning_summary.json`：计数、来源元数据与校验汇总

## 重要约定

1. **不修改原始数据**：所有脚本只读取启动数据包，不写回、不删除任何原始文件；原始记录通过 `raw_record` / `raw_path` 保留可追溯性。
2. **证据只读 fetch 文件**：证据清洗仅读取 `news-data/fetch-*.json`，不读取 Markdown 报告、状态文件和历史 ZIP 备份。
3. **不做事实性结论**：来源中的 `verificationStatus`、`score`、`isDomestic`仅以 `*_source` 命名的字段保留；teams.csv 中 `verification_status` 一律初始化为 `candidate`（允许取值 `candidate` / `verified` / `rejected`），`attention` 一律初始化为 `pending`（允许取值 `A` / `B` / `pending`）；evidence.csv 的 `verification_status` 仍初始化为“待核实”。不把原系统评分或 verified 状态当作项目核实结论。
4. **重复证据不自动删除**：通过 `duplicate_key` 标记疑似重复，在 `deduplication.csv` 中列出，由人工决定去重。
5. **直接脚本运行**：入口脚本均按 `python scripts/<脚本名>` 的方式直接运行；脚本会自动把 `scripts/` 加入模块搜索路径，无需设置 PYTHONPATH。
