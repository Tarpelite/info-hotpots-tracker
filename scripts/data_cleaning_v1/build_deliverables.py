from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_cleaning_v1.config import DEFAULT_OUTPUT_ROOT, NEWS_DATA_DIR, SNAPSHOT_PATH
from data_cleaning_v1.evidence_cleaner import load_and_clean_evidence
from data_cleaning_v1.io_utils import write_csv, write_json, write_jsonl
from data_cleaning_v1.organization import (
    COVERAGE_FIELDS,
    EVIDENCE_FIELDS,
    RELATION_FIELDS,
    RESOURCE_FIELDS,
    TEAM_FIELDS,
    build_deliverables,
    evidence_csv_row,
    team_csv_row,
)
from data_cleaning_v1.team_cleaner import (
    DOMAIN_CSV_FIELDS,
    domain_csv_row,
    load_and_clean_teams,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build candidate team, evidence, relation, coverage, and resource tables."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT / "deliverables",
        help="Directory for the four requested CSVs and the resource table.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT.parent / "20261005科技战略情报启动数据_v1",
        help="Path to the original seed data package.",
    )
    return parser.parse_args()


def relation_csv_row(row: dict[str, object]) -> dict[str, object]:
    return {field: row.get(field, "") for field in RELATION_FIELDS}


def coverage_csv_row(row: dict[str, object]) -> dict[str, object]:
    return {field: row.get(field, "") for field in COVERAGE_FIELDS}


def resource_csv_row(row: dict[str, object]) -> dict[str, object]:
    return {field: row.get(field, "") for field in RESOURCE_FIELDS}


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    snapshot_path = source_root / "团队快照" / SNAPSHOT_PATH.name
    news_data_dir = source_root / "news-data"

    if not snapshot_path.exists():
        raise FileNotFoundError(f"Team snapshot does not exist: {snapshot_path}")
    if not news_data_dir.exists():
        raise FileNotFoundError(f"News data directory does not exist: {news_data_dir}")

    team_rows, domain_rows, team_issues, team_metadata = load_and_clean_teams(
        snapshot_path
    )
    evidence_rows, evidence_issues, evidence_metadata = load_and_clean_evidence(
        news_data_dir
    )
    deliverables = build_deliverables(team_rows, domain_rows, evidence_rows)

    output_root.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_root / "teams.csv",
        [team_csv_row(row) for row in deliverables["teams"]],
        TEAM_FIELDS,
    )
    write_csv(
        output_root / "evidence.csv",
        [evidence_csv_row(row) for row in deliverables["evidence"]],
        EVIDENCE_FIELDS,
    )
    write_csv(
        output_root / "relations.csv",
        deliverables["relations"],
        RELATION_FIELDS,
    )
    write_csv(
        output_root / "coverage.csv",
        [coverage_csv_row(row) for row in deliverables["coverage"]],
        COVERAGE_FIELDS,
    )
    write_csv(
        output_root / "resource_requirements.csv",
        [resource_csv_row(row) for row in deliverables["resources"]],
        RESOURCE_FIELDS,
    )

    # JSONL keeps the newly constructed mappings and source-only evidence
    # inspectable without changing the original cleaned input files.
    write_jsonl(
        output_root / "teams_mapped.jsonl",
        deliverables["teams"],
    )
    write_jsonl(
        output_root / "team_source_evidence.jsonl",
        [
            row
            for row in deliverables["evidence"]
            if row["evidence_type"] == "team_source_url"
        ],
    )
    write_jsonl(
        output_root / "relations.jsonl",
        deliverables["relations"],
    )
    write_json(
        output_root / "mapping_summary.json",
        {
            "source_root": str(source_root),
            "output_root": str(output_root),
            "raw_data_modified": False,
            "source_cleaning_diagnostics": {
                "team_issue_count": len(team_issues),
                "evidence_issue_count": len(evidence_issues),
                "team_metadata": team_metadata,
                "evidence_metadata": evidence_metadata,
            },
            "deliverables": deliverables["mapping_summary"],
            "notes": [
                "Current source verificationStatus, score, and isDomestic remain source fields.",
                "project_verification_status is initialized to 待核实.",
                "Legacy or keyword-derived domain mappings are provisional and flagged in teams.csv.",
                "No original snapshot or news-data file was modified.",
            ],
        },
    )

    print(f"Output: {output_root}")
    print(f"teams.csv: {len(deliverables['teams'])}")
    print(f"evidence.csv: {len(deliverables['evidence'])}")
    print(f"relations.csv: {len(deliverables['relations'])}")
    print(f"coverage.csv: {len(deliverables['coverage'])}")
    print(f"resource_requirements.csv: {len(deliverables['resources'])}")
    print(f"raw input modified: no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
