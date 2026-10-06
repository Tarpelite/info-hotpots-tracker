# 科技信息战略情报系统

科技战略情报启动数据及其 Python 处理脚本。各目录的详细说明见其内部 README。

## 目录

- `20261005科技战略情报启动数据_v1/` —— 启动数据包（只读原始数据），说明见其中的 `README_先读我.txt`
  - 团队快照：344 条候选团队，6 个领域、27 个子领域
  - news-data：49 份采集 JSON 共 30,842 条记录（2026-08-12 至 09-29），另含推送报告与相关性材料
- `scripts/` —— 数据处理脚本（仅用 Python 标准库），说明见 `scripts/README.md`
  - 三个提交流程入口：`import_snapshot.py`（导入建表）→ `validate_snapshot.py`（校验）→ `build_map.py`（图谱与 HTML 预览）
  - `data_cleaning_v1/`：数据清洗工具包
