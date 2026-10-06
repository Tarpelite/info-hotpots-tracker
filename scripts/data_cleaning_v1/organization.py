from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .io_utils import as_json_text, as_text
from .taxonomy import (
    DOMAIN_NAMES,
    LEGACY_DOMAIN_TO_CURRENT_NAME,
    Taxonomy,
    infer_domain_name,
    infer_subdomain_name,
    searchable_team_text,
)


TEAM_FIELDS = [
    "team_id",
    "source_domain_id",
    "source_subdomain_id",
    "domain_id",
    "domain_name",
    "subdomain_id",
    "subdomain_name",
    "mapping_status",
    "mapping_method",
    "mapping_confidence",
    "mapping_reason",
    "mapped_research_direction",
    "team_name",
    "organization",
    "institution_name",
    "leader_id",
    "leader_name",
    "leader_role",
    "description",
    "research_directions_json",
    "location",
    "source_is_domestic",
    "source_verification_status",
    "project_verification_status",
    "candidate_status",
    "attention_level",
    "attention_reason",
    "evidence_count",
    "source_url_count",
    "pending_materials",
    "source_record_ref",
]

EVIDENCE_FIELDS = [
    "evidence_id",
    "evidence_type",
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

RELATION_FIELDS = [
    "team_id",
    "evidence_id",
    "relation_type",
    "claim",
    "source_role",
    "relation_status",
    "reviewer",
    "reviewed_at",
]

COVERAGE_FIELDS = [
    "domain_id",
    "domain_name",
    "candidate_count",
    "source_taxonomy_count",
    "legacy_or_inferred_count",
    "mapping_review_count",
    "verified_count",
    "pending_count",
    "rejected_count",
    "subdomain_coverage_json",
    "missing_subdomains_json",
    "pending_materials_json",
    "resource_requirement_ids",
    "notes",
]

RESOURCE_FIELDS = [
    "resource_id",
    "resource_type",
    "resource_name",
    "status",
    "priority",
    "scope",
    "needed_for",
    "current_evidence",
    "missing_items",
    "fallback_plan",
    "requested_from",
    "request_status",
    "notes",
]


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
        reasons.append("source domain id exists in current six-domain tree")
        method = "source_taxonomy_id"
        confidence = "high"
        mapping_status = "source_mapped"

        if (
            source_subdomain_id in taxonomy.subdomains_by_id
            and taxonomy.subdomain_domain_id.get(source_subdomain_id) == source_domain_id
        ):
            mapped_subdomain_id = source_subdomain_id
            mapped_subdomain_name = taxonomy.subdomains_by_id[source_subdomain_id]["name"]
            reasons.append("source subdomain id exists under the source domain")
        else:
            inferred_name, _, hits = infer_subdomain_name(mapped_domain_name, text)
            if inferred_name:
                mapped_subdomain_name = inferred_name
                mapped_subdomain_id = taxonomy.subdomain_id_for_name(inferred_name)
                reasons.append("subdomain inferred from research directions")
                method = "source_domain_plus_direction_rule"
            else:
                mapping_status = "subdomain_pending"
                reasons.append("no valid source subdomain and no reliable keyword match")
    elif source_domain_id in LEGACY_DOMAIN_TO_CURRENT_NAME:
        mapped_domain_name = LEGACY_DOMAIN_TO_CURRENT_NAME[source_domain_id]
        mapped_domain_id = taxonomy.domain_id_for_name(mapped_domain_name)
        method = "legacy_domain_id_plus_direction_rule"
        confidence = "medium"
        mapping_status = "legacy_domain_mapped"
        reasons.append("source domain id is a legacy id absent from current tree")
        inferred_name, _, hits = infer_subdomain_name(mapped_domain_name, text)
        if inferred_name:
            mapped_subdomain_name = inferred_name
            mapped_subdomain_id = taxonomy.subdomain_id_for_name(inferred_name)
            reasons.append(f"subdomain keyword hits: {','.join(hits)}")
        else:
            mapping_status = "domain_mapped_subdomain_pending"
            reasons.append("no reliable subdomain keyword match")
    else:
        inferred_domain, _, domain_hits = infer_domain_name(text)
        if inferred_domain:
            mapped_domain_name = inferred_domain
            mapped_domain_id = taxonomy.domain_id_for_name(inferred_domain)
            method = "research_direction_rule"
            confidence = "low"
            mapping_status = "direction_inferred"
            reasons.append(f"domain keyword hits: {','.join(domain_hits)}")
            inferred_name, _, subdomain_hits = infer_subdomain_name(inferred_domain, text)
            if inferred_name:
                mapped_subdomain_name = inferred_name
                mapped_subdomain_id = taxonomy.subdomain_id_for_name(inferred_name)
                reasons.append(f"subdomain keyword hits: {','.join(subdomain_hits)}")
            else:
                mapping_status = "domain_inferred_subdomain_pending"
                reasons.append("no reliable subdomain keyword match")
        else:
            mapping_status = "unmapped"
            method = "no_matching_rule"
            reasons.append("source domain id and research direction do not map to current taxonomy")

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

    for team in teams:
        team_id = team["team_id"]
        raw = team.get("raw_record", {})
        source_roles = [
            ("sourceUrls", "team_source"),
            ("evidenceUrls", "evidence_source"),
            ("scoreEvidenceIds", "score_evidence_source"),
        ]
        for field, relation_type in source_roles:
            values = unique_urls(
                as_list(raw.get(field, raw.get(_snake_case(field), [])))
            )
            for url in values:
                normalized = normalize_url(url)
                matched_ids = evidence_by_url.get(normalized, [])
                if matched_ids:
                    for evidence_id in matched_ids:
                        relations.append(
                            _relation(
                                team_id,
                                evidence_id,
                                relation_type,
                                url,
                                "exact URL match to fetched evidence",
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
                            "source_field": field,
                        },
                    }
                    evidence_by_url[normalized] = [evidence_id]
                relations.append(
                    _relation(
                        team_id,
                        evidence_id,
                        relation_type,
                        url,
                        "source URL listed in the team snapshot; manual verification pending",
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


def team_csv_row(team: dict[str, Any]) -> dict[str, Any]:
    return {
        "team_id": team["team_id"],
        "source_domain_id": team["domain_id"],
        "source_subdomain_id": team["subdomain_id"],
        "domain_id": team["mapped_domain_id"],
        "domain_name": team["mapped_domain_name"],
        "subdomain_id": team["mapped_subdomain_id"],
        "subdomain_name": team["mapped_subdomain_name"],
        "mapping_status": team["mapping_status"],
        "mapping_method": team["mapping_method"],
        "mapping_confidence": team["mapping_confidence"],
        "mapping_reason": team["mapping_reason"],
        "mapped_research_direction": team["mapped_research_direction"],
        "team_name": team["team_name"],
        "organization": team["organization"],
        "institution_name": team["institution_name"],
        "leader_id": team["leader_id"],
        "leader_name": team["leader_name"],
        "leader_role": team["leader_role"],
        "description": team["description"],
        "research_directions_json": as_json_text(team["research_directions"]),
        "location": team["location"],
        "source_is_domestic": team["is_domestic_source"],
        "source_verification_status": team["verification_status_source"],
        "project_verification_status": team["project_verification_status"],
        "candidate_status": team["candidate_status"],
        "attention_level": team["attention_level"],
        "attention_reason": team["attention_reason"],
        "evidence_count": team.get("evidence_count", 0),
        "source_url_count": len(team["source_urls"]),
        "pending_materials": "；".join(team["pending_materials"]),
        "source_record_ref": f"raw_preserved/teams_cleaned.jsonl?team_id={team['team_id']}",
    }


def evidence_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": row["evidence_id"],
        "evidence_type": row["evidence_type"],
        "source_record_key": row["source_record_key"],
        "duplicate_key": row["duplicate_key"],
        "evidence_title": row["evidence_title"],
        "source_url": row["source_url"],
        "published_at": row["published_at"],
        "source_name": row["source_name"],
        "raw_text": row["raw_text"],
        "summary": row["summary"],
        "tags_json": json.dumps(row["tags"], ensure_ascii=False, separators=(",", ":")),
        "score_source": row["score_source"],
        "fetched_at": row["fetched_at"],
        "source_file": row["source_file"],
        "source_date": row["source_date"],
        "source_entry_index": row["source_entry_index"],
    }


def build_coverage(
    teams: list[dict[str, Any]],
    taxonomy: Taxonomy,
    resource_ids_by_domain: dict[str, list[str]],
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
                "resource_requirement_ids": ";".join(resource_ids_by_domain.get(domain_name, [])),
                "notes": "候选清单阶段；项目核实状态尚未由人工复核确认。",
            }
        )
    return rows


def build_resources(
    teams: list[dict[str, Any]],
    taxonomy: Taxonomy,
) -> list[dict[str, Any]]:
    missing_source_url_count = sum(not team["official_source_urls"] for team in teams)
    missing_direction_count = sum(not team["research_directions"] for team in teams)
    missing_leader_count = sum(not team["leader_id"] for team in teams)
    non_source_mapped_count = sum(
        team["mapping_status"] != "source_mapped" for team in teams
    )

    resources = [
        {
            "resource_id": "RES-001",
            "resource_type": "snapshot",
            "resource_name": "10月1日临时团队快照原件",
            "status": "not_received",
            "priority": "高",
            "scope": "团队、机构、领域和来源的历史基线",
            "needed_for": "核对10月5日重导快照与10月1日版本的差异",
            "current_evidence": "当前仅有2026-10-05重新导出的已保存资料",
            "missing_items": "10月1日临时保存的原始快照文件",
            "fallback_plan": "暂以team_snapshot_20261005.json作为候选输入，不表述为10月5日新增结果",
            "requested_from": "项目数据提供方",
            "request_status": "待索取",
            "notes": "来自README先读我.txt的明确说明",
        },
        {
            "resource_id": "RES-002",
            "resource_type": "interface",
            "resource_name": "团队与领域快照接口",
            "status": "partial",
            "priority": "高",
            "scope": "团队、领域树、来源和更新状态",
            "needed_for": "后续增量采集与重复运行",
            "current_evidence": "已收到一次完整保存快照，但未收到接口地址、请求样例和鉴权方式",
            "missing_items": "接口地址、请求参数、返回样例、鉴权方式、刷新规则",
            "fallback_plan": "使用本地快照继续完成10月7日候选图谱",
            "requested_from": "数据接口提供方",
            "request_status": "待补充",
            "notes": "",
        },
        {
            "resource_id": "RES-003",
            "resource_type": "interface",
            "resource_name": "模型服务",
            "status": "not_received",
            "priority": "高",
            "scope": "结构化抽取、摘要、引用问答",
            "needed_for": "后续自动抽取和问答功能",
            "current_evidence": "当前启动包未包含模型地址、模型名或API密钥",
            "missing_items": "兼容调用地址、模型名、密钥、请求/返回样例、使用限制",
            "fallback_plan": "10月7日前采用人工字段和已有摘要，不阻塞图谱候选清单",
            "requested_from": "模型服务提供方",
            "request_status": "待索取",
            "notes": "不得把原系统insufficient_quota状态当作核实结果",
        },
        {
            "resource_id": "RES-004",
            "resource_type": "interface",
            "resource_name": "AMiner",
            "status": "not_received",
            "priority": "中",
            "scope": "学者、机构、成果与外部ID",
            "needed_for": "补充负责人、机构和代表成果信息",
            "current_evidence": "当前没有接口地址、字段说明、返回样例和调用权限",
            "missing_items": "调用地址、字段字典、API密钥、限流规则和示例响应",
            "fallback_plan": "先使用团队官网、论文和已有来源链接",
            "requested_from": "外部数据服务提供方",
            "request_status": "待索取",
            "notes": "",
        },
        {
            "resource_id": "RES-005",
            "resource_type": "interface",
            "resource_name": "OpenAlex / arXiv",
            "status": "not_received",
            "priority": "中",
            "scope": "论文元数据、来源标识、作者机构和增量访问",
            "needed_for": "补充代表论文和预印本证据",
            "current_evidence": "当前仅有news-data和团队快照中的部分外链",
            "missing_items": "调用配置、字段映射、增量策略、限流与失败重试规则",
            "fallback_plan": "先导入现有论文和预印本材料，后续接入适配器",
            "requested_from": "开放学术数据服务",
            "request_status": "待索取",
            "notes": "",
        },
        {
            "resource_id": "RES-006",
            "resource_type": "interface",
            "resource_name": "搜索与网页正文提取服务",
            "status": "partial",
            "priority": "高",
            "scope": "官网、代表成果和原文正文",
            "needed_for": "完成机构归属、团队和代表成果核验",
            "current_evidence": f"已有团队来源链接；其中{missing_source_url_count}个团队没有来源链接",
            "missing_items": "检索接口、网页正文提取服务、失败重试和本地缓存规范",
            "fallback_plan": "按现有URL人工补充，保留待核实状态",
            "requested_from": "数据采集负责人",
            "request_status": "待补充",
            "notes": "",
        },
        {
            "resource_id": "RES-007",
            "resource_type": "material",
            "resource_name": "团队官网与代表成果材料",
            "status": "partial",
            "priority": "高",
            "scope": "全部候选团队",
            "needed_for": "确认机构归属、具体团队、研究方向和代表成果",
            "current_evidence": f"已有部分团队来源链接；缺少来源链接{missing_source_url_count}个、研究方向{missing_direction_count}个、负责人证明{missing_leader_count}个",
            "missing_items": "官网团队页、负责人页、代表论文/项目/代码、原文摘录和发布时间",
            "fallback_plan": "先生成候选清单，缺项写入coverage和本资源表",
            "requested_from": "各领域核实人员",
            "request_status": "持续补充",
            "notes": f"当前有{non_source_mapped_count}个团队需要旧领域ID或研究方向规则复核",
        },
        {
            "resource_id": "RES-008",
            "resource_type": "runtime",
            "resource_name": "开发仓库、数据库和运行配置",
            "status": "not_received",
            "priority": "中",
            "scope": "数据导入、接口联调和可复现运行",
            "needed_for": "后续系统开发和首月系统验收",
            "current_evidence": "启动数据包未包含源码配置或API密钥文件",
            "missing_items": "前端/后端仓库、数据库连接、intel schema迁移、.env.example和启动命令",
            "fallback_plan": "使用本地CSV、JSONL和静态预览推进10月7日交付",
            "requested_from": "项目开发负责人",
            "request_status": "待索取",
            "notes": "",
        },
    ]
    return resources


def build_deliverables(
    team_rows: list[dict[str, Any]],
    domain_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    taxonomy = Taxonomy.from_domain_rows(domain_rows)
    mapped_teams = [map_team(row, taxonomy) for row in team_rows]
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
    resources = build_resources(mapped_teams, taxonomy)
    resource_ids_by_domain = {
        domain_name: ["RES-002", "RES-006", "RES-007"]
        for domain_name in DOMAIN_NAMES
    }
    coverage = build_coverage(mapped_teams, taxonomy, resource_ids_by_domain)
    return {
        "teams": mapped_teams,
        "evidence": all_evidence,
        "relations": relations,
        "coverage": coverage,
        "resources": resources,
        "taxonomy": taxonomy,
        "mapping_summary": build_mapping_summary(mapped_teams, all_evidence, relations),
    }


def build_mapping_summary(
    teams: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "team_count": len(teams),
        "evidence_count": len(evidence),
        "relation_count": len(relations),
        "domain_counts": dict(
            sorted(Counter(team["mapped_domain_name"] for team in teams).items())
        ),
        "mapping_status_counts": dict(
            sorted(Counter(team["mapping_status"] for team in teams).items())
        ),
        "mapping_confidence_counts": dict(
            sorted(Counter(team["mapping_confidence"] for team in teams).items())
        ),
        "candidate_status_counts": dict(
            sorted(Counter(team["candidate_status"] for team in teams).items())
        ),
        "project_verification_status_counts": dict(
            sorted(
                Counter(team["project_verification_status"] for team in teams).items()
            )
        ),
        "relation_type_counts": dict(
            sorted(Counter(relation["relation_type"] for relation in relations).items())
        ),
        "evidence_type_counts": dict(
            sorted(Counter(row["evidence_type"] for row in evidence).items())
        ),
    }
