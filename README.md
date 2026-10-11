# 科技信息战略情报系统

科技战略情报启动数据、数据处理脚本与公开前端的汇总工程。原始数据只读，全部产物由脚本从同一份数据生成；各目录的详细说明见其内部 README。

## 目录结构

- `20261005科技战略情报启动数据_v1/` —— 启动数据包（只读原始数据，勿修改），含团队快照（344 条候选团队、6 领域 27 子领域）、`news-data/`（49 份采集 JSON 共 30,842 条记录，2026-08-12 至 09-29）、按日索引与 SHA256 校验清单；详细说明见其中的 `README_先读我.txt`
- `scripts/` —— 数据处理脚本（仅用 Python 标准库），三个提交流程入口依次为 `import_snapshot.py`（导入建表）→ `validate_snapshot.py`（校验）→ `build_map.py`（图谱与团队卡片），另有清洗工具包 `data_cleaning_v1/`；详细说明见 `scripts/README.md`
- `AMiner/` —— AMiner API 请求学习模板，包含 key/token 配置占位、GET/POST 示例与可复用 Python client；详细说明见 `AMiner/README.md`
- `result/` —— 脚本产物目录：根下为 `data.json`、四张提交表（teams/evidence/relations/coverage）、去重与缺项清单、`import_summary.json`；`validation/` 为校验报告；`map/` 为总图、六领域分图 SVG、团队卡片与提交表副本，重建说明见 `result/map/README.md`
- `frontend/` —— 公开站点的 React/Vite 前端源码（首页、地图、领域覆盖、团队与证据视图），优先请求 `/api/public/snapshot`，后端不可用时回退读取 `result/data.json`；安装与启动命令见 `frontend/README.md`
- `index.html` —— 前端工程入口，经 Vite 启动后访问；不直接用浏览器打开
- `.idea/` —— IDE 配置目录，与业务逻辑无关

## 快速开始

1. 在工作区根目录按顺序执行 `scripts/README.md` 中的三个命令，生成并校验 `result/data.json` 与图谱产物。
2. 执行 `npm --prefix frontend install` 与 `npm --prefix frontend run dev`，打开 `http://127.0.0.1:5173/` 预览站点。

## 数据在哪

原始数据不进 git。仓库只放代码、测试和小样本（`pipeline/tests/fixtures/`）。

- 服务器：原始数据放在 `/srv/radar/raw/`。站点数据由服务器上的流水线生成，nginx 提供 `/result/data.json`。
- 开发机：原始数据放在 g513 项目目录下的 `raw/`。
- 已取消跟踪的路径：`20261005科技战略情报启动数据_v1/`、`db/inte-sys/sql/insert_data.sql` 和四个 AMiner 大数据文件，已写入 `.gitignore`。本地文件保留。
