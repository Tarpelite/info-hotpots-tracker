from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

if __package__ in (None, ""):
    # data_cleaning_v1 包与本脚本同处 scripts/ 目录，将 scripts/ 加入 sys.path。
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_cleaning_v1.evidence_cleaner import load_and_clean_evidence
from data_cleaning_v1.io_utils import write_csv, write_json
from data_cleaning_v1.organization import build_deliverables
from data_cleaning_v1.submission_schema import (
    COVERAGE_COLUMNS,
    EVIDENCE_COLUMNS,
    RELATIONS_COLUMNS,
    RESOURCE_COLUMNS,
    TEAMS_COLUMNS,
    coverage_submission_rows,
    deduplication_rows,
    evidence_submission_row,
    missing_item_rows,
    relation_submission_row,
    team_submission_row,
)
from data_cleaning_v1.taxonomy import DOMAIN_NAMES
from data_cleaning_v1.team_cleaner import load_and_clean_teams


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import a team snapshot and fetch entries into one data.json, "
            "four submission tables, a deduplication list, and a missing-item list."
        )
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        required=True,
        help="Path to team_snapshot_*.json.",
    )
    parser.add_argument(
        "--news-data",
        type=Path,
        required=True,
        help="Directory containing fetch-*.json files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for data.json and generated tables.",
    )
    return parser.parse_args()


def snapshot_date(snapshot_path: Path) -> str:
    match = re.search(r"(20\d{6})", snapshot_path.name)
    if match:
        value = match.group(1)
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return ""


def imported_at() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def write_csv_with_columns(
    path: Path,
    rows: list[dict[str, object]],
    columns: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def compact_rows(rows: list[dict[str, object]], columns: list[str]) -> list[dict[str, object]]:
    return [{column: row.get(column, "") for column in columns} for row in rows]


def main() -> int:
    args = parse_args()
    snapshot = args.snapshot.resolve()
    news_data = args.news_data.resolve()
    output = args.output.resolve()
    if not snapshot.is_file():
        raise FileNotFoundError(f"Snapshot does not exist: {snapshot}")
    if not news_data.is_dir():
        raise NotADirectoryError(f"News-data directory does not exist: {news_data}")

    imported = imported_at()
    date = snapshot_date(snapshot)
    batch = f"snapshot_{date or snapshot.stem}_{imported.replace(':', '').replace('+', '_')}"

    team_rows, domain_rows, team_issues, team_metadata = load_and_clean_teams(snapshot)
    evidence_rows, evidence_issues, evidence_metadata = load_and_clean_evidence(news_data)
    deliverables = build_deliverables(team_rows, domain_rows, evidence_rows)

    mapped_teams = deliverables["teams"]
    all_evidence = deliverables["evidence"]
    all_relations = deliverables["relations"]
    table_teams = compact_rows(
        [team_submission_row(team) for team in mapped_teams],
        TEAMS_COLUMNS,
    )
    table_evidence = compact_rows(
        [
            evidence_submission_row(row, imported, snapshot.name)
            for row in all_evidence
        ],
        EVIDENCE_COLUMNS,
    )
    table_relations = compact_rows(
        [relation_submission_row(row) for row in all_relations],
        RELATIONS_COLUMNS,
    )
    table_coverage = compact_rows(
        coverage_submission_rows(mapped_teams, DOMAIN_NAMES),
        COVERAGE_COLUMNS,
    )

    dedup_rows = deduplication_rows(all_evidence)
    missing_rows = missing_item_rows(
        mapped_teams,
        all_evidence,
        team_issues,
        evidence_issues,
    )
    output.mkdir(parents=True, exist_ok=True)
    write_csv_with_columns(output / "teams.csv", table_teams, TEAMS_COLUMNS)
    write_csv_with_columns(output / "evidence.csv", table_evidence, EVIDENCE_COLUMNS)
    write_csv_with_columns(output / "relations.csv", table_relations, RELATIONS_COLUMNS)
    write_csv_with_columns(output / "coverage.csv", table_coverage, COVERAGE_COLUMNS)
    write_csv_with_columns(
        output / "deduplication.csv",
        dedup_rows,
        [
            "duplicate_key",
            "record_count",
            "evidence_ids",
            "source_urls",
            "titles",
            "decision",
            "reason",
        ],
    )
    write_csv_with_columns(
        output / "missing_items.csv",
        missing_rows,
        [
            "record_type",
            "record_id",
            "field",
            "status",
            "message",
            "source_file",
            "source_record_key",
        ],
    )
    write_csv_with_columns(
        output / "resource_requirements.csv",
        deliverables["resources"],
        RESOURCE_COLUMNS,
    )

    taxonomy_rows = []
    for row in domain_rows:
        taxonomy_rows.append(
            {
                "domain_id": row["domain_id"],
                "domain_name": row["domain_name"],
                "subdomain_id": row["subdomain_id"],
                "subdomain_name": row["subdomain_name"],
                "description": row["subdomain_description"] or row["domain_description"],
            }
        )

    data = {
        "schema_version": "2026-10-07.snapshot.v1",
        "metadata": {
            "snapshot_date": date,
            "snapshot_file": snapshot.name,
            "news_data_dir": str(news_data),
            "imported_at": imported,
            "import_batch": batch,
            "raw_data_modified": False,
            "source_notes": [
                "source_name is the RSS/feed source name and is not used as institution.",
                "score and tags remain in evidence.raw_record and evidence metadata.",
                "Team verification_status is initialized to candidate and attention to pending; evidence verification_status is initialized to 待核实.",
                "raw_path preserves the source file and original entry identifier.",
            ],
        },
        "taxonomy": taxonomy_rows,
        "teams": mapped_teams,
        "evidence": all_evidence,
        "relations": all_relations,
        "coverage": table_coverage,
        "tables": {
            "teams": table_teams,
            "evidence": table_evidence,
            "relations": table_relations,
            "coverage": table_coverage,
        },
        "deduplication": dedup_rows,
        "missing_items": missing_rows,
        "resources": deliverables["resources"],
    }
    write_json(output / "data.json", data)
    write_json(
        output / "import_summary.json",
        {
            "metadata": data["metadata"],
            "counts": {
                "teams": len(table_teams),
                "evidence": len(table_evidence),
                "relations": len(table_relations),
                "coverage": len(table_coverage),
                "duplicate_groups": len(dedup_rows),
                "missing_items": len(missing_rows),
                "resources": len(deliverables["resources"]),
            },
            "source_diagnostics": {
                "team_issues": len(team_issues),
                "evidence_issues": len(evidence_issues),
                "team_metadata": team_metadata,
                "evidence_metadata": evidence_metadata,
            },
        },
    )

    print(f"Output: {output}")
    print(f"data.json teams: {len(table_teams)}")
    print(f"data.json evidence: {len(table_evidence)}")
    print(f"data.json relations: {len(table_relations)}")
    print(f"duplicate groups: {len(dedup_rows)}")
    print(f"missing items: {len(missing_rows)}")
    print("raw input modified: no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
