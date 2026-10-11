#!/usr/bin/env python3
"""Build the slim data.json that the public frontend loads.

Keeps only the raw fields that frontend/src/utils/normalizeSnapshot.js reads.
Evidence and news summaries are cut to an excerpt of at most 200 characters.
Other strings longer than 500 characters are cut to 500 (URLs are never cut).
After writing, a self-check runs; it exits 1 if any check fails.
"""
import argparse
import gzip
import json
import os
import sys

EXCERPT_LIMIT = 200
STRING_LIMIT = 500
SIZE_LIMIT = 40 * 1024 * 1024

METADATA_KEYS = ["snapshot_date", "snapshot_file", "imported_at"]
TEAM_KEYS = [
    "team_id", "institution_name", "organization", "location", "location_country",
    "location_city", "description", "leader_role", "official_source_urls",
    "score_evidence_urls", "source_urls", "project_verification_status",
    "candidate_status", "attention_reason", "mapping_status", "mapping_method",
    "mapping_confidence", "mapping_reason", "evidence_count", "pending_materials",
    "leaders", "members", "source_data_updated_at", "recentUpdate", "recent_update",
    "raw_record",
]
RAW_RECORD_KEYS = [
    "sourceUrls", "evidenceUrls", "location", "description", "updatedAt",
    "leader", "leaders", "members",
]
PERSON_KEYS = [
    "id", "name", "title", "role", "profile_url", "profileUrl",
    "verification_status", "verificationStatus", "last_verified_at", "lastVerifiedAt",
]
TABLE_TEAM_KEYS = [
    "team_id", "team_name", "institution", "country", "city", "domain", "subdomain",
    "leader", "direction", "verification_status", "attention", "attention_reason",
]
TABLE_EVIDENCE_KEYS = [
    "evidence_id", "source_type", "title", "source_url", "source_name", "published_at",
    "captured_at", "summary", "verification_status",
]
TABLE_RELATION_KEYS = [
    "team_id", "evidence_id", "relation_type", "claim", "reviewer", "reviewed_at",
]
TABLE_COVERAGE_KEYS = [
    "domain", "candidate_count", "verified_count", "pending_count", "rejected_count",
    "missing_items",
]


def pick(record, keys):
    return {key: record[key] for key in keys if key in record}


def is_url_key(key):
    lowered = (key or "").lower()
    return lowered.endswith("url") or lowered.endswith("urls")


def cut(text, limit):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def clip_strings(value, key=None):
    if isinstance(value, str):
        return value if is_url_key(key) else cut(value, STRING_LIMIT)
    if isinstance(value, list):
        return [clip_strings(item, key) for item in value]
    if isinstance(value, dict):
        return {k: clip_strings(v, k) for k, v in value.items()}
    return value


def slim_person(person):
    return pick(person, PERSON_KEYS) if isinstance(person, dict) else person


def slim_raw_team(team):
    out = pick(team, TEAM_KEYS)
    if isinstance(out.get("raw_record"), dict):
        record = pick(out["raw_record"], RAW_RECORD_KEYS)
        if isinstance(record.get("leader"), dict):
            record["leader"] = pick(record["leader"], ["role"])
        for key in ("leaders", "members"):
            if isinstance(record.get(key), list):
                record[key] = [slim_person(p) for p in record[key]]
        out["raw_record"] = record
    for key in ("leaders", "members"):
        if isinstance(out.get(key), list):
            out[key] = [slim_person(p) for p in out[key]]
    return out


def build_site_doc(data):
    tables = data.get("tables") or {}
    evidence = []
    for item in tables.get("evidence", []):
        row = pick(item, TABLE_EVIDENCE_KEYS)
        if isinstance(row.get("summary"), str):
            row["summary"] = cut(row["summary"], EXCERPT_LIMIT)
        evidence.append(row)
    return {
        "metadata": pick(data.get("metadata") or {}, METADATA_KEYS),
        "teams": [slim_raw_team(t) for t in data.get("teams", [])],
        "tables": {
            "teams": [pick(t, TABLE_TEAM_KEYS) for t in tables.get("teams", [])],
            "evidence": evidence,
            "relations": [pick(r, TABLE_RELATION_KEYS) for r in tables.get("relations", [])],
            "coverage": [pick(c, TABLE_COVERAGE_KEYS) for c in tables.get("coverage", [])],
        },
    }


def walk_strings(value, key=None, path="$"):
    if isinstance(value, str):
        yield path, key, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_strings(item, key, f"{path}[{index}]")
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from walk_strings(v, k, f"{path}.{k}")


def self_check(doc, max_bytes=SIZE_LIMIT):
    """Return a list of problems; an empty list means the check passed."""
    problems = []
    for path, key, text in walk_strings(doc):
        if not is_url_key(key) and len(text) > STRING_LIMIT:
            problems.append(f"{path}: {len(text)} chars > {STRING_LIMIT}")
    for row in doc["tables"]["evidence"]:
        if len(row.get("summary", "")) > EXCERPT_LIMIT:
            problems.append(f"evidence {row.get('evidence_id')}: summary over {EXCERPT_LIMIT}")
        if "raw_text" in row or "raw_record" in row:
            problems.append(f"evidence {row.get('evidence_id')}: body field kept")
    encoded = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > max_bytes:
        problems.append(f"output {len(encoded)} bytes > limit {max_bytes}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True, help="full result/data.json")
    parser.add_argument("--output", required=True, help="slim data.json to write")
    args = parser.parse_args(argv)

    with open(args.input, encoding="utf-8") as handle:
        data = json.load(handle)
    doc = clip_strings(build_site_doc(data))

    problems = self_check(doc, SIZE_LIMIT)
    if problems:
        print("自检未通过：")
        for line in problems[:50]:
            print("  " + line)
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(text)

    raw_size = os.path.getsize(args.input)
    out_size = os.path.getsize(args.output)
    gz_size = len(gzip.compress(text.encode("utf-8"), compresslevel=9))
    print(f"输入 {raw_size} 字节，输出 {out_size} 字节，gzip {gz_size} 字节")
    print(f"团队 {len(doc['teams'])}，证据 {len(doc['tables']['evidence'])}，自检通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
