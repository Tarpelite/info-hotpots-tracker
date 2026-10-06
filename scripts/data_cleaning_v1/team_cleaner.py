from collections import Counter
from pathlib import Path
from typing import Any

from .io_utils import as_json_text, as_text, read_json


TEAM_CSV_FIELDS = [
    "team_id",
    "domain_id",
    "subdomain_id",
    "team_name",
    "organization",
    "institution_name",
    "description",
    "research_directions_json",
    "location",
    "is_domestic_source",
    "verification_status_source",
    "leader_id",
    "leader_name",
    "leader_role",
    "source_urls_json",
    "source_file",
    "snapshot_exported_at",
    "source_data_updated_at",
]

DOMAIN_CSV_FIELDS = [
    "domain_id",
    "domain_name",
    "domain_label",
    "domain_description",
    "subdomain_id",
    "subdomain_name",
    "subdomain_label",
    "subdomain_description",
    "parent_domain_id",
    "source_file",
]


def _first_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return ""


def _leader_fields(team: dict[str, Any]) -> tuple[str, str, str]:
    leader = team.get("leader")
    if not isinstance(leader, dict):
        leaders = team.get("leaders")
        leader = leaders[0] if isinstance(leaders, list) and leaders else {}
    if not isinstance(leader, dict):
        leader = {}
    return (
        as_text(_first_value(leader, "id")),
        as_text(_first_value(leader, "name")),
        as_text(_first_value(leader, "role", "title")),
    )


def _domain_maps(domains: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    domain_map: dict[str, dict[str, Any]] = {}
    subdomain_map: dict[str, dict[str, Any]] = {}
    for domain in domains:
        domain_id = as_text(domain.get("id"))
        if not domain_id:
            continue
        domain_map[domain_id] = domain
        for subdomain in domain.get("subdomains", []):
            if isinstance(subdomain, dict) and subdomain.get("id"):
                subdomain_map[as_text(subdomain["id"])] = subdomain
    return domain_map, subdomain_map


def load_and_clean_teams(snapshot_path: Path) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    snapshot = read_json(snapshot_path)
    data = snapshot.get("data", {})
    domains = data.get("domains", [])
    teams = data.get("teams", [])
    source_metadata = data.get("source", {})
    source_file = snapshot_path.name
    snapshot_exported_at = as_text(source_metadata.get("exportedAt"))

    domain_map, subdomain_map = _domain_maps(domains)
    domain_rows: list[dict[str, Any]] = []
    for domain in domains:
        domain_id = as_text(domain.get("id"))
        for subdomain in domain.get("subdomains", []) or []:
            if not isinstance(subdomain, dict):
                continue
            domain_rows.append(
                {
                    "domain_id": domain_id,
                    "domain_name": as_text(domain.get("name")),
                    "domain_label": as_text(domain.get("label")),
                    "domain_description": as_text(domain.get("description")),
                    "subdomain_id": as_text(subdomain.get("id")),
                    "subdomain_name": as_text(subdomain.get("name")),
                    "subdomain_label": as_text(subdomain.get("label")),
                    "subdomain_description": as_text(subdomain.get("description")),
                    "parent_domain_id": as_text(subdomain.get("parentId")),
                    "source_file": source_file,
                    "raw_domain_record": domain,
                    "raw_subdomain_record": subdomain,
                }
            )

    team_rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    seen_team_ids: Counter[str] = Counter()
    for index, team in enumerate(teams):
        if not isinstance(team, dict):
            issues.append(
                {
                    "record_type": "team",
                    "issue_type": "invalid_record",
                    "source_file": source_file,
                    "source_index": index,
                    "message": "Team record is not an object.",
                }
            )
            continue

        team_id = as_text(team.get("id"))
        domain_id = as_text(team.get("domainId"))
        subdomain_id = as_text(team.get("subdomainId"))
        team_name = as_text(_first_value(team, "teamName", "team_name", "name"))
        leader_id, leader_name, leader_role = _leader_fields(team)
        seen_team_ids[team_id] += 1

        row = {
            "team_id": team_id,
            "domain_id": domain_id,
            "subdomain_id": subdomain_id,
            "team_name": team_name,
            "organization": as_text(team.get("organization")),
            "institution_name": as_text(
                _first_value(team, "institutionName", "institution_name")
            ),
            "description": as_text(team.get("description")),
            "research_directions": team.get(
                "researchDirections",
                team.get("research_directions", []),
            ),
            "location": as_text(team.get("location")),
            "is_domestic_source": team.get(
                "isDomestic",
                team.get("is_domestic"),
            ),
            "verification_status_source": as_text(
                _first_value(team, "verificationStatus", "verification_status")
            ),
            "leader_id": leader_id,
            "leader_name": leader_name,
            "leader_role": leader_role,
            "source_urls": team.get("sourceUrls", team.get("source_urls", [])),
            "source_file": source_file,
            "source_index": index,
            "snapshot_exported_at": snapshot_exported_at,
            "source_data_updated_at": as_text(
                _first_value(team, "updatedAt", "updated_at")
            ),
            "raw_record": team,
        }
        team_rows.append(row)

        if not team_id:
            issues.append(_team_issue(row, "missing_team_id", "Missing team id."))
        if not domain_id:
            issues.append(_team_issue(row, "missing_domain_id", "Missing domain id."))
        elif domain_id not in domain_map:
            issues.append(
                _team_issue(row, "unknown_domain_id", "Domain id is absent from the domain tree.")
            )
        if not subdomain_id:
            issues.append(
                _team_issue(row, "missing_subdomain_id", "Missing subdomain id.")
            )
        elif subdomain_id not in subdomain_map:
            issues.append(
                _team_issue(
                    row,
                    "unknown_subdomain_id",
                    "Subdomain id is absent from the domain tree.",
                )
            )

    for team_id, count in seen_team_ids.items():
        if team_id and count > 1:
            issues.append(
                {
                    "record_type": "team",
                    "issue_type": "duplicate_team_id",
                    "team_id": team_id,
                    "count": count,
                    "source_file": source_file,
                    "message": "Team id occurs more than once; no record was removed.",
                }
            )

    metadata = {
        "source_file": source_file,
        "snapshot_source_metadata": source_metadata,
        "team_count": len(team_rows),
        "domain_count": len(domains),
        "subdomain_count": len(domain_rows),
    }
    return team_rows, domain_rows, issues, metadata


def _team_issue(row: dict[str, Any], issue_type: str, message: str) -> dict[str, Any]:
    return {
        "record_type": "team",
        "issue_type": issue_type,
        "team_id": row.get("team_id", ""),
        "domain_id": row.get("domain_id", ""),
        "subdomain_id": row.get("subdomain_id", ""),
        "source_file": row.get("source_file", ""),
        "source_index": row.get("source_index", ""),
        "message": message,
    }


def team_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "team_id": row["team_id"],
        "domain_id": row["domain_id"],
        "subdomain_id": row["subdomain_id"],
        "team_name": row["team_name"],
        "organization": row["organization"],
        "institution_name": row["institution_name"],
        "description": row["description"],
        "research_directions_json": as_json_text(row["research_directions"]),
        "location": row["location"],
        "is_domestic_source": row["is_domestic_source"],
        "verification_status_source": row["verification_status_source"],
        "leader_id": row["leader_id"],
        "leader_name": row["leader_name"],
        "leader_role": row["leader_role"],
        "source_urls_json": as_json_text(row["source_urls"]),
        "source_file": row["source_file"],
        "snapshot_exported_at": row["snapshot_exported_at"],
        "source_data_updated_at": row["source_data_updated_at"],
    }


def domain_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        field: row[field]
        for field in DOMAIN_CSV_FIELDS
    }
