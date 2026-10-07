# scripts — 科技战略情报数据处理脚本集

本目录存放科技信息战略情报系统启动数据（`20261005科技战略情报启动数据_v1`）的全部 Python 处理脚本，包含提交流程的三个入口（`import_snapshot.py`、`validate_snapshot.py`、`build_map.py`），以及被它们复用的一阶段清洗工具包 `data_cleaning_v1/`。所有脚本只使用 Python 标准库，无需安装第三方依赖。

## 环境要求

- Python 3.12（当前验证版本；仅使用标准库，3.10 及以上原则上可运行）
- 运行位置：工作区根目录（即本 `scripts/` 文件夹的上一级，与 `20261005科技战略情报启动数据_v1/` 同级）
- 操作系统：Windows PowerShell（命令示例为 PowerShell 写法）
- 位置补全默认访问 Nominatim 公共接口，离线时加 `--location-query off` 即可，无需其他网络

## 目录结构

```text
scripts/
├── README.md                 # 本说明文件
├── __init__.py               # 标识 scripts 为 Python 包
├── import_snapshot.py        # 入口 1：导入快照与采集数据，生成 data.json、提交表与各类清单
├── validate_snapshot.py      # 入口 2：校验 data.json，输出通过/未通过检查报告
├── build_map.py              # 入口 3：生成总图、分领域图、团队卡片、提交表副本与 README
└── data_cleaning_v1/         # 一阶段清洗工具包，供三个入口导入复用
    ├── __init__.py
    ├── config.py             # 默认源路径与预期记录数常量（保留作核对基准，入口脚本不导入）
    ├── io_utils.py           # JSON/JSONL/CSV 读写与文本规范化工具
    ├── team_cleaner.py       # 读取快照 data.teams / data.domains，字段映射与源数据问题登记
    ├── evidence_cleaner.py   # 读取 news-data/fetch-*.json，证据字段映射、证据 ID 与重复键生成
    ├── taxonomy.py           # 六领域顺序、27 个子领域关键词表、旧领域 ID 对照与关键词推断
    ├── organization.py       # 领域映射、稳定团队 ID、团队合并去重、证据关联、关系与覆盖度构建
    ├── location_query.py     # 按机构名查询 Nominatim 兼容接口，回填 country/city
    └── submission_schema.py  # 四张提交表列定义、行转换、去重清单与缺项清单生成
```

## data_cleaning_v1 模块说明

| 模块                     | 职责                                                                                                                                                                                                                               |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `config.py`            | 工作区默认源数据路径与预期记录数（344 团队、6 领域、27 子领域、49 个 fetch 文件、30842 条证据）常量；当前入口脚本的路径全部来自命令行参数，不导入本模块                                                                            |
| `io_utils.py`          | `read_json` / `write_json` / `write_jsonl` / `write_csv`，以及 `as_text`、`as_raw_text`、`as_json_text` 等文本规范化函数；CSV 统一以 `utf-8-sig`、`\n` 换行写出                                                  |
| `team_cleaner.py`      | `load_and_clean_teams(snapshot)` 读取快照内嵌的 `data.teams` 与 `data.domains`，输出规范化团队行、领域行、问题清单与元数据；不修改原始记录，原始对象保留在 `raw_record`                                                    |
| `evidence_cleaner.py`  | `load_and_clean_evidence(news_data_dir)` 逐个读取 `fetch-*.json` 的 `entries`，按 `fetch文件名#下标` 生成 SHA256 证据 ID，按 URL（无 URL 时按标题/发布时间/来源/正文）生成重复键，并登记缺字段问题                         |
| `taxonomy.py`          | `Taxonomy` 索引由快照领域树构建；`DOMAIN_NAMES` 固定六领域顺序；`SUBDOMAIN_KEYWORDS` 覆盖 27 个子领域，子领域推断只在所属领域的候选集内打分；`LEGACY_DOMAIN_TO_CURRENT_NAME` 维护 5 个旧领域 ID 的临时对照                 |
| `organization.py`      | `build_deliverables()` 是核心编排：团队经 `map_team()` 映射领域、生成稳定团队 ID，再按稳定 ID 分组合并；证据与团队通过归一化 URL 精确关联，快照登记但未采集到正文的来源链接生成 `team_source_url` 证据；最后产出关系与覆盖度 |
| `location_query.py`    | `enrich_missing_team_locations()` 按机构名去重后调用位置 API，命中则回填 `location_country` / `location_city` 并记录查询来源；网络错误只写诊断，首个网络错误后剩余机构标记跳过，不中断导入                                   |
| `submission_schema.py` | 定义四张提交表列名与行转换函数；内部状态映射为提交枚举（团队 `candidate/verified/rejected`、关注级 `A/B/pending`），并负责 `deduplication_rows()` 与 `missing_item_rows()` 两张清单                                        |

## 提交流程（权威入口，按顺序执行）

以下命令均在工作区根目录执行。

### 第 1 步：导入与建表 —— import_snapshot.py

读取团队快照与 `news-data/fetch-*.json`，完成字段清洗、六领域/子领域映射、团队去重合并与证据 URL 关联，生成一份 `data.json`、四张提交表和三张清单。默认会按机构名调用位置 API 补全 `country/city`，失败只记录诊断、不中断导入。

```powershell
python scripts/import_snapshot.py --snapshot "20261005科技战略情报启动数据_v1/团队快照/team_snapshot_20261005.json" --news-data "20261005科技战略情报启动数据_v1/news-data" --output "result"
```

离线环境可关闭位置查询：

```powershell
python scripts/import_snapshot.py --snapshot "20261005科技战略情报启动数据_v1/团队快照/team_snapshot_20261005.json" --news-data "20261005科技战略情报启动数据_v1/news-data" --output "result" --location-query off
```

参数说明：

| 参数                          | 必填 | 默认值                                         | 说明                                             |
| ----------------------------- | ---- | ---------------------------------------------- | ------------------------------------------------ |
| `--snapshot`                | 是   | —                                             | `team_snapshot_*.json` 团队快照文件路径        |
| `--news-data`               | 是   | —                                             | 包含 `fetch-*.json` 的 news-data 目录路径      |
| `--output`                  | 是   | —                                             | 产物输出目录，不存在会自动创建                   |
| `--location-query`          | 否   | `on`                                         | 位置补全开关：`on` 启用、`off` 跳过 API 查询 |
| `--location-api-url`        | 否   | `https://nominatim.openstreetmap.org/search` | Nominatim 兼容的地理编码搜索端点                 |
| `--location-api-user-agent` | 否   | `Intelligence-System/1.0 (...)`              | 发往位置 API 的 User-Agent                       |
| `--location-api-timeout`    | 否   | `10.0`                                       | 位置 API 超时时间（秒）                          |

输出产物（均在 `--output` 指定目录下）：

- `data.json`：完整结构化产物（`schema_version` 为 `2026-10-07.snapshot.v1`），包含 `metadata`、`taxonomy`、`teams`、`evidence`、`relations`、`coverage`、`tables`、`deduplication`、`team_deduplication`、`missing_items` 等区段
- `import_summary.json`：团队/证据/关系/清单计数与来源诊断摘要，含位置查询逐条记录
- `teams.csv`、`evidence.csv`、`relations.csv`、`coverage.csv`：四张提交表
- `deduplication.csv`：疑似重复证据清单（`保留全部，待人工去重`，不删除记录）
- `team_deduplication.csv`：按机构 + 团队名称 + 带头人合并的重复团队清单
- `missing_items.csv`：缺失字段与待补材料清单（只标记，不替业务下结论）

### 第 2 步：校验 —— validate_snapshot.py

对第 1 步生成的 `data.json` 执行结构、ID 唯一性、字段映射、关系完整性、领域枚举、覆盖度统计和原始记录保留等十余项检查。

```powershell
python scripts/validate_snapshot.py --data "result/data.json" --output "result/validation"
```

输出产物：`validation_report.json`（完整报告，含每项检查的状态、说明与细节）、`validation_passed.csv`（通过项）、`validation_failed.csv`（未通过项）。全部检查通过时报告状态为“通过”且退出码为 0；存在未通过项时状态为“未通过”、退出码为 1，并在终端逐条打印失败原因。

### 第 3 步：生成图谱与卡片 —— build_map.py

基于同一份 `data.json` 生成领域总图、六张分领域图、每支团队一张的卡片页、四张提交表副本和重建说明。

```powershell
python scripts/build_map.py --data "result/data.json" --output "result/map"
```

输出产物（均在 `--output` 指定目录下）：

- `total_graph_YYYYMMDD.svg`：国内战略力量总图（根节点 → 六领域卡片，含机构数、子领域数与状态徽标）
- `domain_graph_NN-<领域名>_YYYYMMDD.svg`：六领域分图，按子领域分组列出团队条目，共 6 张
- `team_cards/index.html`：团队卡片索引页；`team_cards/team_<team_id>.html`：每支团队一张详情卡（含领域映射说明、关注建议、关联证据与来源链接，返回链接指向项目根目录的 `index.html`）
- `teams.csv`、`evidence.csv`、`relations.csv`、`coverage.csv`：四张提交表副本
- `README.md`：本输出目录的自动生成版重建说明

## 本地预览

项目根目录的 `index.html` 是 `frontend/` 下 React/Vite 前端工程的入口（不再是静态单文件），首页优先请求 `/api/public/snapshot`，后端不可用时自动回退读取 `result/data.json`。首次运行需安装依赖，之后在项目根目录启动开发服务器：

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

然后打开 `http://127.0.0.1:5173/`。第 3 步生成的 SVG 与团队卡片是静态文件，可直接经同一服务访问，例如 `http://127.0.0.1:5173/result/map/total_graph_20261005.svg` 或 `http://127.0.0.1:5173/result/map/team_cards/index.html`；若只查看这些静态产物，也可在项目根目录执行 `python -m http.server 8000` 后访问对应路径，但根目录首页必须经 Vite 启动才能正常渲染。
