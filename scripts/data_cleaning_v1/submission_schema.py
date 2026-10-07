from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


TEAMS_COLUMNS = [
    "team_id",
    "team_name",
    "institution",
    "country",
    "city",
    "domain",
    "subdomain",
    "leader",
    "direction",
    "verification_status",
    "attention",
    "attention_reason",
    "reviewer",
    "reviewed_at",
]

EVIDENCE_COLUMNS = [
    "evidence_id",
    "source_type",
    "title",
    "source_url",
    "source_name",
    "published_at",
    "captured_at",
    "summary",
    "raw_path",
    "verification_status",
]

RELATIONS_COLUMNS = [
    "team_id",
    "evidence_id",
    "relation_type",
    "claim",
    "reviewer",
    "reviewed_at",
]

COVERAGE_COLUMNS = [
    "domain",
    "candidate_count",
    "verified_count",
    "pending_count",
    "rejected_count",
    "missing_items",
]


# teams.csv 中 verification_status / attention 的允许取值。
TEAM_VERIFICATION_STATUSES = ("candidate", "verified", "rejected")
TEAM_ATTENTION_LEVELS = ("A", "B", "pending")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _first_nonempty(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _text(record.get(key))
        if value:
            return value
    return ""


# 内部中文核实状态（organization.project_verification_status）到提交枚举的映射。
_VERIFICATION_STATUS_MAP = {
    "待核实": "candidate",
    "已核实": "verified",
    "已剔除": "rejected",
}
# 内部关注级别（organization.attention_level）到提交枚举的映射。
_ATTENTION_LEVEL_MAP = {
    "待人工判定": "pending",
    "A": "A",
    "B": "B",
}


def team_verification_status(value: Any) -> str:
    """将内部核实状态转换为 candidate/verified/rejected，未知值按候选处理。"""
    return _VERIFICATION_STATUS_MAP.get(_text(value), "candidate")


def team_attention(value: Any) -> str:
    """将内部关注级别转换为 A/B/pending，未知值按待人工判定处理。"""
    return _ATTENTION_LEVEL_MAP.get(_text(value), "pending")


def extract_country(team: dict[str, Any]) -> str:
    raw = team.get("raw_record", {})
    enriched = _text(team.get("location_country"))
    if enriched:
        return enriched
    # 源快照中的 institutionCountry 口径不一致：可能填的是城市或街道地址。
    # 除非原始数据明确提供国家，否则 country 保持为空。
    return _first_nonempty(raw, "country")


def extract_city(team: dict[str, Any]) -> str:
    raw = team.get("raw_record", {})
    enriched = _text(team.get("location_city"))
    if enriched:
        return enriched
    return _first_nonempty(raw, "city")


def team_submission_row(team: dict[str, Any]) -> dict[str, Any]:
    return {
        "team_id": team.get("team_id", ""),
        "team_name": team.get("team_name", ""),
        "institution": team.get("institution_name")
        or team.get("organization", ""),
        "country": extract_country(team),
        "city": extract_city(team),
        "domain": team.get("mapped_domain_name", ""),
        "subdomain": team.get("mapped_subdomain_name", ""),
        "leader": team.get("leader_name", ""),
        "direction": team.get("mapped_research_direction", ""),
        "verification_status": team_verification_status(
            team.get("project_verification_status")
        ),
        "attention": team_attention(team.get("attention_level")),
        "attention_reason": team.get("mapping_reason", ""),
        "reviewer": "",
        "reviewed_at": "",
    }


def evidence_raw_path(row: dict[str, Any], snapshot_name: str) -> str:
    if row.get("evidence_type") == "news_fetch":
        source_file = row.get("source_file", "")
        index = row.get("source_entry_index", "")
        return f"news-data/{source_file}#entries[{index}]"
    raw_record = row.get("raw_record", {})
    team_id = raw_record.get("origin_team_id", "")
    field = raw_record.get("source_field", "")
    return f"团队快照/{snapshot_name}#team_id={team_id}&field={field}"


def evidence_submission_row(
    row: dict[str, Any],
    imported_at: str,
    snapshot_name: str,
) -> dict[str, Any]:
    captured_at = _text(row.get("fetched_at")) or imported_at
    return {
        "evidence_id": row.get("evidence_id", ""),
        "source_type": row.get("evidence_type", ""),
        "title": row.get("evidence_title", ""),
        "source_url": row.get("source_url", ""),
        "source_name": row.get("source_name", ""),
        "published_at": row.get("published_at", ""),
        "captured_at": captured_at,
        "summary": row.get("summary", ""),
        "raw_path": evidence_raw_path(row, snapshot_name),
        "verification_status": "待核实",
    }


def relation_submission_row(row: dict[str, Any]) -> dict[str, Any]:
    claim = row.get("claim", "")
    relation_type = row.get("relation_type", "")
    if relation_type == "score_evidence_source":
        claim = "来源来自原始评分元数据，未作为已核实结论。"
    return {
        "team_id": row.get("team_id", ""),
        "evidence_id": row.get("evidence_id", ""),
        "relation_type": relation_type,
        "claim": claim,
        "reviewer": "",
        "reviewed_at": "",
    }


def coverage_submission_rows(
    teams: list[dict[str, Any]],
    domain_names: tuple[str, ...],
) -> list[dict[str, Any]]:
    rows = []
    for domain in domain_names:
        domain_teams = [team for team in teams if team.get("mapped_domain_name") == domain]
        missing: list[str] = []
        for team in domain_teams:
            for item in team.get("pending_materials", []):
                if item not in missing:
                    missing.append(item)
        verified_count = sum(
            team.get("project_verification_status") == "已核实"
            for team in domain_teams
        )
        rejected_count = sum(
            team.get("project_verification_status") == "已剔除"
            for team in domain_teams
        )
        pending_count = len(domain_teams) - verified_count - rejected_count
        rows.append(
            {
                "domain": domain,
                "candidate_count": len(domain_teams),
                "verified_count": verified_count,
                "pending_count": pending_count,
                "rejected_count": rejected_count,
                "missing_items": "；".join(missing),
            }
        )
    return rows


def deduplication_rows(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in evidence:
        groups[row.get("duplicate_key", row.get("evidence_id", ""))].append(row)
    rows = []
    for duplicate_key, records in sorted(groups.items()):
        if len(records) < 2:
            continue
        rows.append(
            {
                "duplicate_key": duplicate_key,
                "record_count": len(records),
                "evidence_ids": ";".join(row.get("evidence_id", "") for row in records),
                "source_urls": ";".join(
                    sorted({row.get("source_url", "") for row in records if row.get("source_url")})
                ),
                "titles": ";".join(
                    sorted({row.get("evidence_title", "") for row in records if row.get("evidence_title")})
                ),
                "decision": "保留全部，待人工去重",
                "reason": "本轮仅生成去重清单，不删除原始证据记录。",
            }
        )
    return rows


def missing_item_rows(
    teams: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    team_issues: list[dict[str, Any]],
    evidence_issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(
        record_type: str,
        record_id: str,
        field: str,
        status: str,
        message: str,
        source_file: str = "",
        source_record_key: str = "",
    ) -> None:
        key = (record_type, record_id, field)
        if key in seen:
            return
        seen.add(key)
        rows.append(
            {
                "record_type": record_type,
                "record_id": record_id,
                "field": field,
                "status": status,
                "message": message,
                "source_file": source_file,
                "source_record_key": source_record_key,
            }
        )

    for team in teams:
        for item in team.get("pending_materials", []):
            add(
                "team",
                team.get("team_id", ""),
                item,
                "待补",
                item,
                team.get("source_file", ""),
                team.get("team_id", ""),
            )
        if not team.get("mapped_domain_name"):
            add(
                "team",
                team.get("team_id", ""),
                "domain",
                "待核实",
                "未能映射到六领域枚举。",
                team.get("source_file", ""),
                team.get("team_id", ""),
            )
        if not team.get("mapped_subdomain_name"):
            add(
                "team",
                team.get("team_id", ""),
                "subdomain",
                "待核实",
                "未能映射到具体研究方向/子领域。",
                team.get("source_file", ""),
                team.get("team_id", ""),
            )

    for issue in [*team_issues, *evidence_issues]:
        add(
            issue.get("record_type", ""),
            issue.get("team_id") or issue.get("evidence_id", ""),
            issue.get("issue_type", ""),
            "待补",
            issue.get("message", ""),
            issue.get("source_file", ""),
            issue.get("source_record_key", ""),
        )

    for row in evidence:
        for field in ("evidence_title", "source_url", "source_name", "raw_text"):
            if not row.get(field):
                add(
                    "evidence",
                    row.get("evidence_id", ""),
                    field,
                    "待补",
                    f"{field}为空。",
                    row.get("source_file", ""),
                    row.get("source_record_key", ""),
                )
    return rows
