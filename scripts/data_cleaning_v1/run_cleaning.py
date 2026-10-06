import argparse
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from .config import DEFAULT_OUTPUT_ROOT, EXPECTED_COUNTS, SOURCE_ROOT
    from .evidence_cleaner import (
        EVIDENCE_CSV_FIELDS,
        evidence_csv_row,
        load_and_clean_evidence,
    )
    from .io_utils import write_csv, write_json, write_jsonl
    from .team_cleaner import (
        DOMAIN_CSV_FIELDS,
        TEAM_CSV_FIELDS,
        domain_csv_row,
        load_and_clean_teams,
        team_csv_row,
    )
except ImportError:
    from data_cleaning_v1.config import DEFAULT_OUTPUT_ROOT, EXPECTED_COUNTS, SOURCE_ROOT
    from data_cleaning_v1.evidence_cleaner import (
        EVIDENCE_CSV_FIELDS,
        evidence_csv_row,
        load_and_clean_evidence,
    )
    from data_cleaning_v1.io_utils import write_csv, write_json, write_jsonl
    from data_cleaning_v1.team_cleaner import (
        DOMAIN_CSV_FIELDS,
        TEAM_CSV_FIELDS,
        domain_csv_row,
        load_and_clean_teams,
        team_csv_row,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean the strategic intelligence seed snapshot without modifying raw data."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=SOURCE_ROOT,
        help="Path to 20261005科技战略情报启动数据_v1.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory for cleaned outputs.",
    )
    return parser.parse_args()


def build_paths(source_root: Path) -> tuple[Path, Path, Path]:
    return (
        source_root / "团队快照" / "team_snapshot_20261005.json",
        source_root / "news-data",
        source_root / "README_先读我.txt",
    )


def write_outputs(
    output_root: Path,
    team_rows: list[dict[str, Any]],
    domain_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    normalized_dir = output_root / "normalized"
    raw_preserved_dir = output_root / "raw_preserved"
    diagnostics_dir = output_root / "diagnostics"

    write_csv(
        normalized_dir / "teams_cleaned.csv",
        [team_csv_row(row) for row in team_rows],
        TEAM_CSV_FIELDS,
    )
    write_csv(
        normalized_dir / "domains_cleaned.csv",
        [domain_csv_row(row) for row in domain_rows],
        DOMAIN_CSV_FIELDS,
    )
    write_csv(
        normalized_dir / "evidence_cleaned.csv",
        [evidence_csv_row(row) for row in evidence_rows],
        EVIDENCE_CSV_FIELDS,
    )

    write_jsonl(raw_preserved_dir / "teams_cleaned.jsonl", team_rows)
    write_jsonl(raw_preserved_dir / "domains_cleaned.jsonl", domain_rows)
    write_jsonl(raw_preserved_dir / "evidence_cleaned.jsonl", evidence_rows)
    write_jsonl(diagnostics_dir / "validation_issues.jsonl", issues)


def build_summary(
    source_root: Path,
    output_root: Path,
    team_metadata: dict[str, Any],
    evidence_metadata: dict[str, Any],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    actual = {
        "teams": team_metadata["team_count"],
        "domains": team_metadata["domain_count"],
        "subdomains": team_metadata["subdomain_count"],
        "fetch_files": evidence_metadata["fetch_file_count"],
        "evidence_records": evidence_metadata["evidence_record_count"],
    }
    expected_comparison = {
        key: {
            "expected": EXPECTED_COUNTS[key],
            "actual": actual[key],
            "matches": EXPECTED_COUNTS[key] == actual[key],
        }
        for key in EXPECTED_COUNTS
    }
    return {
        "source_root": str(source_root),
        "output_root": str(output_root),
        "raw_data_modified": False,
        "cleaning_scope": [
            "Read data.teams and data.domains from the team snapshot.",
            "Read only fetch-*.json entries from news-data.",
            "Map title/link/published/source/content to normalized evidence fields.",
            "Preserve full source records in raw_preserved JSONL outputs.",
            "Do not interpret source verification status, score, or domestic flag as final project verification.",
            "Do not remove duplicate evidence records in this stage.",
        ],
        "actual_counts": actual,
        "expected_count_comparison": expected_comparison,
        "diagnostics": {
            "issue_count": len(issues),
            "issue_types": _count_issue_types(issues),
            "duplicate_group_count": evidence_metadata["duplicate_group_count"],
            "duplicate_record_count": evidence_metadata["duplicate_record_count"],
        },
        "team_metadata": team_metadata,
        "evidence_metadata": evidence_metadata,
    }


def _count_issue_types(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for issue in issues:
        issue_type = str(issue.get("issue_type", "unknown"))
        counts[issue_type] = counts.get(issue_type, 0) + 1
    return dict(sorted(counts.items()))


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    snapshot_path, news_data_dir, readme_path = build_paths(source_root)

    for required_path in (snapshot_path, news_data_dir, readme_path):
        if not required_path.exists():
            raise FileNotFoundError(f"Required input does not exist: {required_path}")

    team_rows, domain_rows, team_issues, team_metadata = load_and_clean_teams(
        snapshot_path
    )
    evidence_rows, evidence_issues, evidence_metadata = load_and_clean_evidence(
        news_data_dir
    )
    issues = team_issues + evidence_issues

    write_outputs(output_root, team_rows, domain_rows, evidence_rows, issues)
    summary = build_summary(
        source_root,
        output_root,
        team_metadata,
        evidence_metadata,
        issues,
    )
    write_json(output_root / "cleaning_summary.json", summary)

    print(f"Output: {output_root}")
    print(f"Teams: {summary['actual_counts']['teams']}")
    print(f"Domains: {summary['actual_counts']['domains']}")
    print(f"Subdomains: {summary['actual_counts']['subdomains']}")
    print(f"Fetch files: {summary['actual_counts']['fetch_files']}")
    print(f"Evidence records: {summary['actual_counts']['evidence_records']}")
    print(f"Validation issues: {summary['diagnostics']['issue_count']}")
    print(
        "Raw input modified: "
        + ("yes" if summary["raw_data_modified"] else "no")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
