from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .io_utils import as_text
from .taxonomy import (
    DOMAIN_NAMES,
    LEGACY_DOMAIN_TO_CURRENT_NAME,
    Taxonomy,
    infer_domain_name,
    infer_subdomain_name,
    searchable_team_text,
)


def normalize_url(url: str) -> str:
    url = as_text(url)
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
        return urlunsplit(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip("/") or "/",
                parsed.query,
                "",
            )
        )
    except ValueError:
        return url


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def normalize_identity_value(value: Any) -> str:
    text = unicodedata.normalize("NFKC", as_text(value)).lower()
    text = re.sub(r"\s+", "", text)
    return text


def team_identity_key(team_row: dict[str, Any]) -> str:
    institution = team_row.get("institution_name") or team_row.get("organization", "")
    parts = [
        normalize_identity_value(institution),
        normalize_identity_value(team_row.get("team_name", "")),
        normalize_identity_value(team_row.get("leader_name", "")),
    ]
    return "|".join(parts)


def stable_team_id(team_row: dict[str, Any]) -> str:
    key = team_identity_key(team_row)
    if key == "||":
        key = normalize_identity_value(team_row.get("team_id", ""))
    return stable_id("team", f"institution_team_leader:{key}")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _domain_row_by_id(taxonomy: Taxonomy, domain_id: str) -> dict[str, Any]:
    return taxonomy.domains_by_id.get(domain_id, {})


def _subdomain_row_by_id(taxonomy: Taxonomy, subdomain_id: str) -> dict[str, Any]:
    return taxonomy.subdomains_by_id.get(subdomain_id, {})


def map_team(team_row: dict[str, Any], taxonomy: Taxonomy) -> dict[str, Any]:
    raw = team_row.get("raw_record", {})
    source_team_id = team_row.get("team_id", "")
    source_domain_id = team_row.get("domain_id", "")
    source_subdomain_id = team_row.get("subdomain_id", "")
    text = searchable_team_text(team_row)
    reasons: list[str] = []
    method = ""
    confidence = "low"
    mapping_status = "needs_review"

    mapped_domain_id = ""
    mapped_domain_name = ""
    mapped_subdomain_id = ""
    mapped_subdomain_name = ""

    if source_domain_id in taxonomy.domains_by_id:
        mapped_domain_id = source_domain_id
        mapped_domain_name = taxonomy.domains_by_id[source_domain_id]["name"]
        reasons.append("源领域 id 存在于当前六领域树中")
        method = "source_taxonomy_id"
        confidence = "high"
        mapping_status = "source_mapped"

        if (
            source_subdomain_id in taxonomy.subdomains_by_id
            and taxonomy.subdomain_domain_id.get(source_subdomain_id) == source_domain_id
        ):
            mapped_subdomain_id = source_subdomain_id
            mapped_subdomain_name = taxonomy.subdomains_by_id[source_subdomain_id]["name"]
            reasons.append("源子领域 id 隶属于该源领域")
        else:
            inferred_name, _, hits = infer_subdomain_name(mapped_domain_name, text)
            if inferred_name:
                mapped_subdomain_name = inferred_name
                mapped_subdomain_id = taxonomy.subdomain_id_for_name(inferred_name)
                reasons.append("依据研究方向推断子领域")
                method = "source_domain_plus_direction_rule"
            else:
                mapping_status = "subdomain_pending"
                reasons.append("源子领域 id 无效且无可靠关键词匹配")
    elif source_domain_id in LEGACY_DOMAIN_TO_CURRENT_NAME:
        mapped_domain_name = LEGACY_DOMAIN_TO_CURRENT_NAME[source_domain_id]
        mapped_domain_id = taxonomy.domain_id_for_name(mapped_domain_name)
        method = "legacy_domain_id_plus_direction_rule"
        confidence = "medium"
        mapping_status = "legacy_domain_mapped"
        reasons.append("源领域 id 为旧版 ID，不在当前领域树中")
        inferred_name, _, hits = infer_subdomain_name(mapped_domain_name, text)
        if inferred_name:
            mapped_subdomain_name = inferred_name
            mapped_subdomain_id = taxonomy.subdomain_id_for_name(inferred_name)
            reasons.append(f"子领域关键词命中：{','.join(hits)}")
        else:
            mapping_status = "domain_mapped_subdomain_pending"
            reasons.append("无可靠的子领域关键词匹配")
    else:
        inferred_domain, _, domain_hits = infer_domain_name(text)
        if inferred_domain:
            mapped_domain_name = inferred_domain
            mapped_domain_id = taxonomy.domain_id_for_name(inferred_domain)
            method = "research_direction_rule"
            confidence = "low"
            mapping_status = "direction_inferred"
            reasons.append(f"领域关键词命中：{','.join(domain_hits)}")
            inferred_name, _, subdomain_hits = infer_subdomain_name(inferred_domain, text)
            if inferred_name:
                mapped_subdomain_name = inferred_name
                mapped_subdomain_id = taxonomy.subdomain_id_for_name(inferred_name)
                reasons.append(f"子领域关键词命中：{','.join(subdomain_hits)}")
            else:
                mapping_status = "domain_inferred_subdomain_pending"
                reasons.append("无可靠的子领域关键词匹配")
        else:
            mapping_status = "unmapped"
            method = "no_matching_rule"
            reasons.append("源领域 id 与研究方向均无法映射到当前领域体系")

    directions = raw.get("researchDirections", raw.get("research_directions", []))
    directions = [as_text(value) for value in as_list(directions) if as_text(value)]
    if not directions:
        for candidate in (
            raw.get("focus"),
            raw.get("coreDirection", raw.get("core_direction")),
            team_row.get("description"),
        ):
            if as_text(candidate):
                directions = [as_text(candidate)]
                break

    official_source_urls = unique_urls(
        [
            *as_list(raw.get("sourceUrls", raw.get("source_urls", []))),
            *as_list(raw.get("evidenceUrls", raw.get("evidence_urls", []))),
        ]
    )
    score_evidence_urls = unique_urls(
        as_list(raw.get("scoreEvidenceIds", raw.get("score_evidence_ids", [])))
    )
    source_urls = unique_urls(
        [
            *official_source_urls,
            *score_evidence_urls,
        ]
    )
    leaders = raw.get("leaders", [])
    leader_available = bool(team_row.get("leader_id") or leaders or raw.get("leader"))
    pending_materials: list[str] = []
    if not directions:
        pending_materials.append("具体研究方向")
    if not leader_available:
        pending_materials.append("负责人或团队负责人证明")
    if not official_source_urls:
        pending_materials.append("团队官网或代表成果来源")
    if mapping_status not in {"source_mapped"}:
        pending_materials.append("六领域/子领域归属人工确认")
    if as_text(raw.get("verificationStatus", raw.get("verification_status"))) in {
        "collected",
        "legacy_unverified",
        "pending_llm_review",
    }:
        pending_materials.append("机构归属、具体团队和代表成果核验")

    if pending_materials:
        candidate_status = "待补材料"
    else:
        candidate_status = "候选待核实"

    return {
        **team_row,
        "team_id": stable_team_id(team_row),
        "source_team_id": source_team_id,
        "source_team_ids": [source_team_id] if source_team_id else [],
        "source_domain_ids": [source_domain_id] if source_domain_id else [],
        "source_subdomain_ids": [source_subdomain_id] if source_subdomain_id else [],
        "team_identity_key": team_identity_key(team_row),
        "team_identity": {
            "institution": team_row.get("institution_name")
            or team_row.get("organization", ""),
            "team_name": team_row.get("team_name", ""),
            "leader_name": team_row.get("leader_name", ""),
        },
        "raw_records": [raw] if raw else [],
        "mapped_domain_id": mapped_domain_id,
        "mapped_domain_name": mapped_domain_name,
        "mapped_subdomain_id": mapped_subdomain_id,
        "mapped_subdomain_name": mapped_subdomain_name,
        "mapping_status": mapping_status,
        "mapping_method": method,
        "mapping_confidence": confidence,
        "mapping_reason": "；".join(reasons),
        "mapped_research_direction": "；".join(directions),
        "research_directions": directions,
        "source_urls": source_urls,
        "official_source_urls": official_source_urls,
        "score_evidence_urls": score_evidence_urls,
        "pending_materials": pending_materials,
        "candidate_status": candidate_status,
        "project_verification_status": "待核实",
        "attention_level": "待人工判定",
        "attention_reason": "初始候选清单，不将原系统评分或 verified 状态作为项目结论",
    }


def unique_texts(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = as_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def merge_mapped_team_group(records: list[dict[str, Any]]) -> dict[str, Any]:
    if len(records) == 1:
        record = records[0]
        return {
            **record,
            "dedup_record_count": 1,
            "dedup_source_team_ids": record.get("source_team_ids", []),
        }

    def quality(record: dict[str, Any]) -> tuple[int, int, int, int, str]:
        return (
            int(bool(record.get("mapped_subdomain_name"))),
            int(bool(record.get("leader_name"))),
            len(record.get("official_source_urls", [])),
            len(record.get("research_directions", [])),
            record.get("source_team_id", ""),
        )

    primary = sorted(records, key=quality, reverse=True)[0]
    merged = dict(primary)
    merged["source_team_ids"] = unique_texts(
        [value for record in records for value in record.get("source_team_ids", [])]
    )
    merged["source_domain_ids"] = unique_texts(
        [value for record in records for value in record.get("source_domain_ids", [])]
    )
    merged["source_subdomain_ids"] = unique_texts(
        [value for record in records for value in record.get("source_subdomain_ids", [])]
    )
    merged["source_team_id"] = ";".join(merged["source_team_ids"])
    merged["domain_id"] = ";".join(merged["source_domain_ids"])
    merged["subdomain_id"] = ";".join(merged["source_subdomain_ids"])
    merged["source_urls"] = unique_urls(
        [value for record in records for value in record.get("source_urls", [])]
    )
    merged["official_source_urls"] = unique_urls(
        [value for record in records for value in record.get("official_source_urls", [])]
    )
    merged["score_evidence_urls"] = unique_urls(
        [value for record in records for value in record.get("score_evidence_urls", [])]
    )
    merged["research_directions"] = unique_texts(
        [value for record in records for value in record.get("research_directions", [])]
    )
    merged["mapped_research_direction"] = "；".join(merged["research_directions"])
    merged["pending_materials"] = unique_texts(
        [value for record in records for value in record.get("pending_materials", [])]
    )
    if "重复团队合并结果人工确认" not in merged["pending_materials"]:
        merged["pending_materials"].append("重复团队合并结果人工确认")
    if len({record.get("mapped_domain_name", "") for record in records}) > 1:
        if "六领域/子领域归属人工确认" not in merged["pending_materials"]:
            merged["pending_materials"].append("六领域/子领域归属人工确认")
    merged["raw_records"] = [
        raw
        for record in records
        for raw in record.get("raw_records", [record.get("raw_record", {})])
        if raw
    ]
    merged["raw_record"] = primary.get("raw_record", {})
    merged["dedup_record_count"] = len(records)
    merged["dedup_source_team_ids"] = merged["source_team_ids"]
    merged["dedup_basis"] = "机构+团队名称+带头人"
    merged["candidate_status"] = "待补材料"
    return merged


def deduplicate_mapped_teams(
    mapped_teams: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for team in mapped_teams:
        groups[team["team_id"]].append(team)

    deduped = [merge_mapped_team_group(records) for records in groups.values()]
    dedup_rows = []
    for team_id, records in sorted(groups.items()):
        if len(records) < 2:
            continue
        first = records[0]
        dedup_rows.append(
            {
                "team_id": team_id,
                "team_identity_key": first.get("team_identity_key", ""),
                "record_count": len(records),
                "source_team_ids": ";".join(
                    unique_texts(
                        [
                            value
                            for record in records
                            for value in record.get("source_team_ids", [])
                        ]
                    )
                ),
                "institution": first.get("institution_name")
                or first.get("organization", ""),
                "team_name": first.get("team_name", ""),
                "leader_name": first.get("leader_name", ""),
                "decision": "已合并为稳定团队ID",
                "reason": "按机构、团队名称和带头人生成稳定ID并合并重复原始记录。",
            }
        )
    return deduped, dedup_rows


def unique_urls(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        url = as_text(value)
        normalized = normalize_url(url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(url)
    return result


def build_evidence_index(evidence_rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for row in evidence_rows:
        url = normalize_url(row.get("source_url", ""))
        if url:
            index[url].append(row["evidence_id"])
    return index


def add_evidence_types(evidence_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in evidence_rows:
        rows.append(
            {
                **row,
                "evidence_type": "news_fetch",
            }
        )
    return rows


def build_team_source_evidence(
    teams: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_by_url = build_evidence_index(evidence_rows)
    new_evidence: dict[str, dict[str, Any]] = {}
    relations: list[dict[str, Any]] = []
    relation_seen: set[tuple[str, str, str]] = set()

    for team in teams:
        team_id = team["team_id"]
        raw_records = team.get("raw_records") or [team.get("raw_record", {})]
        source_roles = [
            ("sourceUrls", "team_source"),
            ("evidenceUrls", "evidence_source"),
            ("scoreEvidenceIds", "score_evidence_source"),
        ]
        for raw in raw_records:
            if not isinstance(raw, dict):
                continue
            source_team_id = as_text(raw.get("id"))
            for field, relation_type in source_roles:
                values = unique_urls(
                    as_list(raw.get(field, raw.get(_snake_case(field), [])))
                )
                for url in values:
                    normalized = normalize_url(url)
                    matched_ids = evidence_by_url.get(normalized, [])
                    if matched_ids:
                        for evidence_id in matched_ids:
                            key = (team_id, evidence_id, relation_type)
                            if key in relation_seen:
                                continue
                            relation_seen.add(key)
                            relations.append(
                                _relation(
                                    team_id,
                                    evidence_id,
                                    relation_type,
                                    url,
                                    "与已采集证据的 URL 精确匹配",
                                )
                            )
                        continue

                    evidence_id = stable_id("evidence_team_source", normalized)
                    if evidence_id not in new_evidence:
                        new_evidence[evidence_id] = {
                            "evidence_id": evidence_id,
                            "evidence_type": "team_source_url",
                            "source_record_key": f"team_snapshot_url:{normalized}",
                            "duplicate_key": stable_id("duplicate", normalized),
                            "evidence_title": f"团队来源链接（待核实）：{team['team_name']}",
                            "source_url": url,
                            "published_at": "",
                            "source_name": "team_snapshot_source_url",
                            "raw_text": "",
                            "summary": "来自团队快照的来源链接，尚未在本地采集正文。",
                            "tags": ["team_snapshot_source"],
                            "score_source": "",
                            "fetched_at": "",
                            "source_file": "team_snapshot_20261005.json",
                            "source_date": "",
                            "source_entry_index": "",
                            "raw_record": {
                                "source_url": url,
                                "origin_team_id": team_id,
                                "source_team_id": source_team_id,
                                "source_field": field,
                            },
                        }
                        evidence_by_url[normalized] = [evidence_id]
                    key = (team_id, evidence_id, relation_type)
                    if key in relation_seen:
                        continue
                    relation_seen.add(key)
                    relations.append(
                        _relation(
                            team_id,
                            evidence_id,
                            relation_type,
                            url,
                            "来源 URL 来自团队快照登记，待人工核实",
                        )
                    )
    return list(new_evidence.values()), relations


def _snake_case(name: str) -> str:
    output = []
    for char in name:
        if char.isupper():
            output.append("_")
            output.append(char.lower())
        else:
            output.append(char)
    return "".join(output)


def _relation(
    team_id: str,
    evidence_id: str,
    relation_type: str,
    source_url: str,
    claim: str,
) -> dict[str, Any]:
    return {
        "team_id": team_id,
        "evidence_id": evidence_id,
        "relation_type": relation_type,
        "claim": claim,
        "source_role": source_url,
        "relation_status": "待核实",
        "reviewer": "",
        "reviewed_at": "",
    }


def attach_relation_counts(
    teams: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    counts = Counter(relation["team_id"] for relation in relations)
    return [{**team, "evidence_count": counts.get(team["team_id"], 0)} for team in teams]

def build_coverage(
    teams: list[dict[str, Any]],
    taxonomy: Taxonomy,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain_name in DOMAIN_NAMES:
        domain_id = taxonomy.domain_id_for_name(domain_name)
        domain_teams = [team for team in teams if team["mapped_domain_name"] == domain_name]
        subdomain_rows = []
        missing_subdomains = []
        for subdomain_id, subdomain in taxonomy.subdomains_by_id.items():
            if taxonomy.subdomain_domain_id.get(subdomain_id) != domain_id:
                continue
            subdomain_teams = [
                team for team in domain_teams if team["mapped_subdomain_id"] == subdomain_id
            ]
            item = {
                "subdomain_id": subdomain_id,
                "subdomain_name": subdomain["name"],
                "candidate_count": len(subdomain_teams),
                "pending_count": sum(
                    team["project_verification_status"] == "待核实"
                    for team in subdomain_teams
                ),
            }
            subdomain_rows.append(item)
            if not subdomain_teams:
                missing_subdomains.append(subdomain["name"])

        material_counts: Counter[str] = Counter()
        for team in domain_teams:
            material_counts.update(team["pending_materials"])
        pending_materials = [
            {"item": item, "team_count": count}
            for item, count in sorted(material_counts.items())
        ]

        direct_count = sum(
            team["mapping_status"] == "source_mapped" for team in domain_teams
        )
        inferred_count = len(domain_teams) - direct_count
        review_count = sum(
            team["mapping_status"]
            in {
                "subdomain_pending",
                "domain_mapped_subdomain_pending",
                "domain_inferred_subdomain_pending",
                "direction_inferred",
                "unmapped",
            }
            for team in domain_teams
        )
        rows.append(
            {
                "domain_id": domain_id,
                "domain_name": domain_name,
                "candidate_count": len(domain_teams),
                "source_taxonomy_count": direct_count,
                "legacy_or_inferred_count": inferred_count,
                "mapping_review_count": review_count,
                "verified_count": 0,
                "pending_count": len(domain_teams),
                "rejected_count": 0,
                "subdomain_coverage_json": json.dumps(
                    subdomain_rows,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "missing_subdomains_json": json.dumps(
                    missing_subdomains,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "pending_materials_json": json.dumps(
                    pending_materials,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "notes": "候选清单阶段；项目核实状态尚未由人工复核确认。",
            }
        )
    return rows


def build_deliverables(
    team_rows: list[dict[str, Any]],
    domain_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    taxonomy = Taxonomy.from_domain_rows(domain_rows)
    mapped_teams = [map_team(row, taxonomy) for row in team_rows]
    mapped_teams, team_deduplication = deduplicate_mapped_teams(mapped_teams)
    domain_order = {name: index for index, name in enumerate(DOMAIN_NAMES)}
    mapped_teams.sort(
        key=lambda team: (
            domain_order.get(team["mapped_domain_name"], len(DOMAIN_NAMES)),
            team["mapped_subdomain_name"],
            team["team_name"],
            team["team_id"],
        )
    )
    existing_evidence = add_evidence_types(evidence_rows)
    source_evidence, relations = build_team_source_evidence(
        mapped_teams,
        existing_evidence,
    )
    all_evidence = existing_evidence + source_evidence
    mapped_teams = attach_relation_counts(mapped_teams, relations)
    coverage = build_coverage(mapped_teams, taxonomy)
    return {
        "teams": mapped_teams,
        "evidence": all_evidence,
        "relations": relations,
        "coverage": coverage,
        "team_deduplication": team_deduplication,
        "taxonomy": taxonomy,
    }
