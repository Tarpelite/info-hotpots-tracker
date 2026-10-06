from pathlib import Path


# 本文件位于 scripts/data_cleaning_v1/config.py，向上三级为工作区根目录。
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_ROOT = WORKSPACE_ROOT / "20261005科技战略情报启动数据_v1"
SNAPSHOT_PATH = SOURCE_ROOT / "团队快照" / "team_snapshot_20261005.json"
DOMAINS_CSV_PATH = SOURCE_ROOT / "团队快照" / "domains_领域定义.csv"
NEWS_DATA_DIR = SOURCE_ROOT / "news-data"

DEFAULT_OUTPUT_ROOT = WORKSPACE_ROOT / "20261005科技战略情报清洗结果_v1"

EXPECTED_COUNTS = {
    "teams": 344,
    "domains": 6,
    "subdomains": 27,
    "fetch_files": 49,
    "evidence_records": 30_842,
}
