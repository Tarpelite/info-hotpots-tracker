from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .io_utils import as_text


DEFAULT_LOCATION_API_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_LOCATION_API_USER_AGENT = (
    "Intelligence-System/1.0 (institution-location; local data pipeline)"
)

@dataclass(frozen=True)
class LocationLookupConfig:
    mode: str = "on"
    endpoint: str = DEFAULT_LOCATION_API_URL
    user_agent: str = DEFAULT_LOCATION_API_USER_AGENT
    timeout_seconds: float = 10.0


def _team_institution(team: dict[str, Any]) -> str:
    identity = team.get("team_identity", {})
    if not isinstance(identity, dict):
        identity = {}
    return (
        as_text(team.get("institution_name"))
        or as_text(team.get("organization"))
        or as_text(identity.get("institution"))
    )


def _raw_location(team: dict[str, Any], key: str) -> str:
    raw = team.get("raw_record", {})
    if not isinstance(raw, dict):
        raw = {}
    return as_text(team.get(f"location_{key}")) or as_text(raw.get(key))


def _location_candidate(team: dict[str, Any]) -> bool:
    return bool(_team_institution(team))


def _extract_city(address: dict[str, Any]) -> str:
    return as_text(address.get("city"))


def _source_url(endpoint: str, institution: str) -> str:
    query = urlencode(
        {
            "format": "jsonv2",
            "q": institution,
            "limit": "1",
            "addressdetails": "1",
            "accept-language": "zh-CN,en",
        }
    )
    separator = "&" if "?" in endpoint else "?"
    return f"{endpoint}{separator}{query}"


def lookup_institution_location(
    institution: str,
    config: LocationLookupConfig,
) -> dict[str, Any]:
    url = _source_url(config.endpoint, institution)
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": config.user_agent,
        },
    )
    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return {
            "status": "error",
            "error_type": "http",
            "institution": institution,
            "message": f"HTTP {exc.code}: {exc.reason}",
            "source_url": url,
        }
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {
            "status": "error",
            "error_type": "network",
            "institution": institution,
            "message": str(exc),
            "source_url": url,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error_type": "unexpected",
            "institution": institution,
            "message": str(exc),
            "source_url": url,
        }

    if not isinstance(payload, list) or not payload:
        return {
            "status": "not_found",
            "error_type": "",
            "institution": institution,
            "source_url": url,
        }

    first = payload[0]
    if not isinstance(first, dict):
        return {
            "status": "not_found",
            "error_type": "",
            "institution": institution,
            "source_url": url,
        }
    address = first.get("address", {})
    if not isinstance(address, dict):
        address = {}
    country = as_text(address.get("country"))
    city = _extract_city(address)
    return {
        "status": "found" if country or city else "partial",
        "error_type": "",
        "institution": institution,
        "country": country,
        "city": city,
        "display_name": as_text(first.get("display_name")),
        "lat": as_text(first.get("lat")),
        "lon": as_text(first.get("lon")),
        "source": "nominatim",
        "source_url": url,
    }


def enrich_missing_team_locations(
    teams: list[dict[str, Any]],
    config: LocationLookupConfig,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "mode": config.mode,
        "provider": "nominatim",
        "endpoint": config.endpoint,
        "queried": 0,
        "updated": 0,
        "candidate_count": 0,
        "institution_count": 0,
        "skipped_after_network_error": 0,
        "network_unavailable": False,
        "records": [],
    }
    if config.mode == "off":
        return summary
    if config.mode != "on":
        raise ValueError(f"Unsupported location enrichment mode: {config.mode}")

    candidates = [team for team in teams if _location_candidate(team)]
    summary["candidate_count"] = len(candidates)
    if not candidates:
        return summary

    teams_by_institution: dict[str, list[dict[str, Any]]] = {}
    for team in candidates:
        teams_by_institution.setdefault(_team_institution(team), []).append(team)
    summary["institution_count"] = len(teams_by_institution)

    for institution, members in teams_by_institution.items():
        if summary["network_unavailable"]:
            summary["skipped_after_network_error"] += len(members)
            continue

        result = lookup_institution_location(institution, config)
        summary["queried"] += 1
        if result.get("error_type") == "network":
            summary["network_unavailable"] = True

        updated = 0
        if result.get("country") or result.get("city"):
            for team in members:
                before = (_raw_location(team, "country"), _raw_location(team, "city"))
                if result.get("country"):
                    team["location_country"] = result["country"]
                if result.get("city"):
                    team["location_city"] = result["city"]
                after = (_raw_location(team, "country"), _raw_location(team, "city"))
                if after != before:
                    updated += 1
                team["location_lookup"] = {
                    "source": result.get("source", ""),
                    "source_url": result.get("source_url", ""),
                    "display_name": result.get("display_name", ""),
                    "lat": result.get("lat", ""),
                    "lon": result.get("lon", ""),
                }
        summary["updated"] += updated

        summary["records"].append(
            {
                "institution": institution,
                "team_count": len(members),
                "updated": updated,
                "status": result.get("status", ""),
                "error_type": result.get("error_type", ""),
                "country": result.get("country", ""),
                "city": result.get("city", ""),
                "display_name": result.get("display_name", ""),
                "message": result.get("message", ""),
                "source_url": result.get("source_url", ""),
            }
        )
    return summary
