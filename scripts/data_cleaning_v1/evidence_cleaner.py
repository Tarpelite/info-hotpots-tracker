import hashlib
from pathlib import Path
from typing import Any

from .io_utils import as_raw_text, as_text, read_json


EVIDENCE_CSV_FIELDS = [
    "evidence_id",
    "source_record_key",
    "duplicate_key",
    "evidence_title",
    "source_url",
    "published_at",
    "source_name",
    "raw_text",
    "summary",
    "tags_json",
    "score_source",
    "fetched_at",
    "source_file",
    "source_date",
    "source_entry_index",
]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _identity_key(entry: dict[str, Any]) -> str:
    link = as_text(entry.get("link"))
    if link:
        return f"url:{link}"
    return "|".join(
        [
            as_text(entry.get("title")),
            as_text(entry.get("published")),
            as_text(entry.get("source")),
            as_text(entry.get("content")),
        ]
    )


def load_and_clean_evidence(news_data_dir: Path) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    fetch_files = sorted(news_data_dir.glob("fetch-*.json"))
    evidence_rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    duplicate_counts: dict[str, int] = {}

    for fetch_path in fetch_files:
        try:
            payload = read_json(fetch_path)
        except Exception as exc:
            issues.append(
                {
                    "record_type": "evidence_file",
                    "issue_type": "invalid_json",
                    "source_file": fetch_path.name,
                    "message": str(exc),
                }
            )
            continue

        entries = payload.get("entries")
        if not isinstance(entries, list):
            issues.append(
                {
                    "record_type": "evidence_file",
                    "issue_type": "missing_entries",
                    "source_file": fetch_path.name,
                    "message": "Top-level entries is not a list.",
                }
            )
            continue

        source_date = as_text(payload.get("meta", {}).get("date"))
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                issues.append(
                    {
                        "record_type": "evidence",
                        "issue_type": "invalid_record",
                        "source_file": fetch_path.name,
                        "source_entry_index": index,
                        "message": "Evidence record is not an object.",
                    }
                )
                continue

            identity_key = _identity_key(entry)
            duplicate_key = f"duplicate_{_sha256(identity_key)[:24]}"
            source_record_key = f"{fetch_path.name}#{index}"
            evidence_id = f"evidence_{_sha256(source_record_key)[:24]}"
            duplicate_counts[duplicate_key] = duplicate_counts.get(duplicate_key, 0) + 1

            row = {
                "evidence_id": evidence_id,
                "source_record_key": source_record_key,
                "duplicate_key": duplicate_key,
                "evidence_title": as_raw_text(entry.get("title")),
                "source_url": as_raw_text(entry.get("link")),
                "published_at": as_raw_text(entry.get("published")),
                "source_name": as_raw_text(entry.get("source")),
                "raw_text": as_raw_text(entry.get("content")),
                "summary": as_raw_text(entry.get("summary")),
                "tags": entry.get("tags", []),
                "score_source": entry.get("score"),
                "fetched_at": as_raw_text(entry.get("fetched_at")),
                "source_file": fetch_path.name,
                "source_date": source_date,
                "source_entry_index": index,
                "raw_record": entry,
            }
            evidence_rows.append(row)

            for field, issue_type in [
                ("evidence_title", "missing_title"),
                ("source_url", "missing_link"),
                ("published_at", "missing_published"),
                ("source_name", "missing_source"),
                ("raw_text", "missing_content"),
            ]:
                if not row[field]:
                    issues.append(
                        {
                            "record_type": "evidence",
                            "issue_type": issue_type,
                            "evidence_id": evidence_id,
                            "source_file": fetch_path.name,
                            "source_entry_index": index,
                            "message": f"Mapped field {field} is empty.",
                        }
                    )

    duplicate_group_count = sum(1 for count in duplicate_counts.values() if count > 1)
    duplicate_record_count = sum(
        count for count in duplicate_counts.values() if count > 1
    )
    metadata = {
        "fetch_file_count": len(fetch_files),
        "evidence_record_count": len(evidence_rows),
        "duplicate_group_count": duplicate_group_count,
        "duplicate_record_count": duplicate_record_count,
        "fetch_files": [path.name for path in fetch_files],
    }
    return evidence_rows, issues, metadata


def evidence_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    import json

    return {
        "evidence_id": row["evidence_id"],
        "source_record_key": row["source_record_key"],
        "duplicate_key": row["duplicate_key"],
        "evidence_title": row["evidence_title"],
        "source_url": row["source_url"],
        "published_at": row["published_at"],
        "source_name": row["source_name"],
        "raw_text": row["raw_text"],
        "summary": row["summary"],
        "tags_json": json.dumps(
            row["tags"],
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "score_source": row["score_source"],
        "fetched_at": row["fetched_at"],
        "source_file": row["source_file"],
        "source_date": row["source_date"],
        "source_entry_index": row["source_entry_index"],
    }
