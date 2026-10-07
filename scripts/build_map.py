"""Build the strategic-intelligence map from one ``data.json``.

Produces the 7 October deliverable "可复现预览" (03):

* ``total_graph_<YYYYMMDD>.svg``   领域 → 机构/子领域/团队 的总图
* ``domain_graph_<NN-领域>_<YYYYMMDD>.svg``  六领域分图（子领域分组 + 团队条目）
* ``team_cards/``                  每个团队一张卡片页 + 索引页
* ``teams.csv`` / ``evidence.csv`` / ``relations.csv`` / ``coverage.csv``
* ``README.md``                    重建说明

本地预览首页 ``index.html`` 固定存放在项目根目录，不再由本脚本生成；
页面在浏览器中运行时读取 ``result/data.json``。

Only the Python standard library is used, so it runs directly::

    python scripts/build_map.py --data <data.json> --output <map_dir>

输出文件名保持稳定，README / 验收命令引用的就是这些名字。
"""

from __future__ import annotations

import argparse
import ast
import csv
import html
import json
import math
import re
import sys
from pathlib import Path
from string import Template
from typing import Any

if __package__ in (None, ""):
    # data_cleaning_v1 包与本脚本同处 scripts/ 目录，将 scripts/ 加入 sys.path。
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_cleaning_v1.submission_schema import (
    COVERAGE_COLUMNS,
    EVIDENCE_COLUMNS,
    RELATIONS_COLUMNS,
    TEAMS_COLUMNS,
)
from data_cleaning_v1.taxonomy import DOMAIN_NAMES


# --------------------------------------------------------------------------
# 视觉规范（浅色编辑部风格，公开站 / 报告的配色口径）
# --------------------------------------------------------------------------
FONT_STACK = (
    '"Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", '
    '"Source Han Sans SC", "Noto Sans CJK SC", Arial, sans-serif'
)
MONO_STACK = '"Consolas", "SFMono-Regular", Menlo, monospace'

INK = "#1f2a37"
INK_SOFT = "#5a6675"
INK_FAINT = "#8b96a8"
LINE = "#e4e9f0"
PAGE = "#ffffff"
PANEL = "#f7f9fc"
ACCENT = "#2f6bd8"

DOMAIN_COLORS = {
    "科学通用底座": "#3b6fd4",
    "通用 AI": "#7a5cf0",
    "高能物理与量子科技": "#0f9bd7",
    "化学与材料": "#2aa06b",
    "生命科学与医学": "#d4547a",
    "地球科学": "#d98324",
}
FALLBACK_DOMAIN_COLOR = ACCENT

STATUS_ORDER = ("verified", "candidate", "rejected")
STATUS_LABELS = {"verified": "已核实", "candidate": "待核实", "rejected": "已剔除"}
STATUS_COLORS = {"verified": "#1a9c6b", "candidate": "#c07a1e", "rejected": "#c04a45"}
STATUS_TINTS = {"verified": "#e8f6ef", "candidate": "#fdf4e4", "rejected": "#fbeceb"}

ATTENTION_LABELS = {"A": "A 重点关注", "B": "B 持续关注", "pending": "关注等级待定"}
ATTENTION_COLORS = {"A": "#b03a3a", "B": "#b06a1e", "pending": "#8b96a8"}

# 内部代码 → 页面可读文案。未收录的值不展示，避免把工程字段漏到界面上。
MAPPING_METHOD_LABELS = {
    "source_taxonomy_id": "快照领域树直接映射",
    "legacy_domain_id_plus_direction_rule": "旧领域 ID + 方向关键词推断",
    "source_domain_plus_direction_rule": "快照领域 + 方向关键词推断",
}
MAPPING_CONFIDENCE_LABELS = {"high": "高", "medium": "中", "low": "低"}
RELATION_TYPE_LABELS = {
    "team_source": "团队来源链接",
    "score_evidence_source": "评分来源证据",
    "evidence_source": "证据来源",
}
# 少数来源名是内部代码，页面上换成可读文案；其余来源名原样展示。
SOURCE_NAME_LABELS = {"team_snapshot_source_url": "团队快照来源"}


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="基于一份 data.json 生成图谱、团队卡片、提交表与本地预览。"
    )
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="import_snapshot.py 生成的 data.json 路径。"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="图谱 SVG、团队卡片、提交表与本地预览的输出目录。"
    )
    return parser.parse_args()


def load_data(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in columns} for row in rows)


def slug(value: str) -> str:
    value = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value, flags=re.UNICODE).strip("-")
    return value or "item"


def code_for_domain(domain: str, domains: list[str]) -> str:
    return f"{domains.index(domain) + 1:02d}-{slug(domain)}"


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def one_line(value: Any) -> str:
    return " ".join(str("" if value is None else value).split())


def clean_list_text(value: Any, sep: str = "；") -> str:
    """Turn a list / list-repr / plain string into a readable inline string."""
    if isinstance(value, (list, tuple)):
        return sep.join(part for part in (one_line(item) for item in value) if part)
    text = one_line(value)
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, (list, tuple)):
            return sep.join(part for part in (one_line(item) for item in parsed) if part)
        return text[1:-1].replace("'", "").replace('"', "")
    return text


def label_of(value: Any, mapping: dict[str, str]) -> str:
    """Translate an internal code into page copy; unknown codes are dropped."""
    return mapping.get(one_line(value), "")


def normalize_status(value: Any) -> str:
    text = one_line(value)
    if text in ("verified", "已核实"):
        return "verified"
    if text in ("rejected", "已剔除"):
        return "rejected"
    return "candidate"


def normalize_attention(value: Any) -> str:
    text = one_line(value).upper()
    if text.startswith("A"):
        return "A"
    if text.startswith("B"):
        return "B"
    return "pending"


def text_width(text: str, size: float) -> float:
    """Rough advance width: CJK ≈ 1.0em, latin ≈ 0.56em."""
    width = 0.0
    for char in text:
        width += size if ord(char) > 0x2E7F else size * 0.56
    return width


def fit_text(value: Any, size: float, max_width: float) -> str:
    text = one_line(value)
    if max_width <= 0:
        return ""
    if text_width(text, size) <= max_width:
        return text
    ellipsis = "…"
    out = ""
    for char in text:
        if text_width(out + char + ellipsis, size) > max_width:
            break
        out += char
    return f"{out}{ellipsis}" if out else ellipsis


# --------------------------------------------------------------------------
# SVG 基础图元
# --------------------------------------------------------------------------
def svg_open(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )


def svg_text(
    x: float,
    y: float,
    text: Any,
    size: float = 16,
    weight: str = "400",
    fill: str = INK,
    anchor: str = "start",
    family: str = FONT_STACK,
) -> str:
    extra = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{esc(family)}" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}"{extra}>'
        f"{esc(text)}</text>"
    )


def svg_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    stroke: str | None = None,
    rx: float = 0,
    stroke_width: float = 1.0,
) -> str:
    stroke_attr = f' stroke="{stroke}" stroke-width="{stroke_width}"' if stroke else ""
    rx_attr = f' rx="{rx:.1f}"' if rx else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}"'
        f'{rx_attr} fill="{fill}"{stroke_attr}/>'
    )


def svg_line(x1: float, y1: float, x2: float, y2: float, stroke: str, width: float = 1.0) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width}" stroke-linecap="round"/>'
    )


def svg_path(path: str, stroke: str, width: float = 1.4) -> str:
    return (
        f'<path d="{path}" fill="none" stroke="{stroke}" '
        f'stroke-width="{width}" stroke-linecap="round"/>'
    )


def svg_circle(cx: float, cy: float, r: float, fill: str) -> str:
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"/>'


def chip(
    x: float,
    y: float,
    label: str,
    color: str,
    tint: str,
    size: float = 13,
    height: float = 24,
    pad: float = 11,
) -> tuple[str, float]:
    """A pill-shaped label. ``y`` is the top edge. Returns (svg, width)."""
    width = text_width(label, size) + pad * 2
    svg = svg_rect(x, y, width, height, tint, rx=height / 2) + svg_text(
        x + pad, y + height / 2 + size * 0.36, label, size=size, weight="600", fill=color
    )
    return svg, width


def domain_color(name: str) -> str:
    return DOMAIN_COLORS.get(name, FALLBACK_DOMAIN_COLOR)


def status_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = {"verified": 0, "candidate": 0, "rejected": 0}
    for row in rows:
        counts[normalize_status(row.get(key))] += 1
    return counts


def status_summary_text(counts: dict[str, int]) -> str:
    return " · ".join(f"{STATUS_LABELS[key]} {counts[key]}" for key in STATUS_ORDER)


# --------------------------------------------------------------------------
# 总图
# --------------------------------------------------------------------------
def domain_summary(teams: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for name in DOMAIN_NAMES:
        rows = [team for team in teams if (team.get("mapped_domain_name") or "待核实") == name]
        institutions = {
            one_line(team.get("organization") or team.get("institution_name"))
            for team in rows
        }
        institutions.discard("")
        subdomains: dict[str, int] = {}
        for team in rows:
            key = one_line(team.get("mapped_subdomain_name")) or "待核实"
            subdomains[key] = subdomains.get(key, 0) + 1
        summary[name] = {
            "count": len(rows),
            "institutions": len(institutions),
            "subdomains": subdomains,
            "status": status_counts(rows, "project_verification_status"),
        }
    return summary


def write_total_svg(output: Path, data: dict[str, Any]) -> None:
    date = str(data["metadata"].get("snapshot_date", ""))
    teams = data.get("teams", [])
    summary = domain_summary(teams)
    total = sum(item["count"] for item in summary.values())
    totals: dict[str, int] = {"verified": 0, "candidate": 0, "rejected": 0}
    for item in summary.values():
        for key in totals:
            totals[key] += item["status"][key]

    width = 1680
    row_height = 132
    row_gap = 20
    rows_top = 208
    domains = list(DOMAIN_NAMES)
    rows_height = len(domains) * (row_height + row_gap) - row_gap
    legend_top = rows_top + rows_height + 52
    height = legend_top + 110

    root_x, root_width, root_height = 88, 372, 268
    center_y = rows_top + rows_height / 2
    root_y = center_y - root_height / 2
    card_x, card_width = 720, 880

    pieces = [
        svg_open(width, height),
        svg_rect(0, 0, width, height, PAGE),
        svg_text(88, 84, "国内战略力量图谱 · 总图", 34, "700"),
        svg_text(
            88,
            118,
            f"快照日期 {date} · 全部数字来自同一份清洗数据；候选团队不等同于已核实",
            15,
            "400",
            INK_SOFT,
        ),
        svg_rect(88, 138, 76, 4, ACCENT, rx=2),
    ]

    # 连接线先画，卡片覆盖其上，避免线头压住卡片文字。
    for index, name in enumerate(domains):
        row_center = rows_top + index * (row_height + row_gap) + row_height / 2
        span = root_height - 96
        port_y = root_y + 48 + index * (span / max(1, len(domains) - 1))
        start_x = root_x + root_width
        control_x = start_x + (card_x - start_x) * 0.5
        pieces.append(
            svg_path(
                f"M {start_x:.1f} {port_y:.1f} C {control_x:.1f} {port_y:.1f}, "
                f"{control_x:.1f} {row_center:.1f}, {card_x:.1f} {row_center:.1f}",
                "#c3d2ea",
                1.6,
            )
        )
        pieces.append(svg_circle(start_x, port_y, 3.4, "#a9bede"))

    # 根节点
    pieces.append(svg_rect(root_x, root_y, root_width, root_height, "#eef4fe", "#c8d9f4", rx=20, stroke_width=1.2))
    pieces.append(svg_rect(root_x, root_y + 22, 6, root_height - 44, ACCENT, rx=3))
    pieces.append(svg_text(root_x + 30, root_y + 52, "国内战略力量", 22, "700"))
    pieces.append(svg_text(root_x + 30, root_y + 128, str(total), 60, "700", ACCENT))
    pieces.append(svg_text(root_x + 30, root_y + 156, "支候选团队（未核实）", 15, "400", INK_SOFT))
    pieces.append(svg_line(root_x + 30, root_y + 178, root_x + root_width - 30, root_y + 178, "#c8d9f4"))
    pieces.append(
        svg_text(root_x + 30, root_y + 206, f"覆盖 {len(domains)} 个领域", 14, "600", INK_SOFT)
    )
    pieces.append(
        svg_text(root_x + 30, root_y + 232, status_summary_text(totals), 13.5, "400", INK_FAINT)
    )

    # 领域卡片
    for index, name in enumerate(domains):
        item = summary[name]
        color = domain_color(name)
        y = rows_top + index * (row_height + row_gap)
        pieces.append(svg_rect(card_x, y, card_width, row_height, "#ffffff", LINE, rx=16, stroke_width=1.2))
        pieces.append(svg_rect(card_x, y + 18, 6, row_height - 36, color, rx=3))
        pieces.append(svg_text(card_x + 32, y + 46, name, 22, "700"))
        pieces.append(
            svg_text(
                card_x + 32,
                y + 76,
                f"机构 {item['institutions']} 家 · 子领域 {len(item['subdomains'])} 个",
                14,
                "400",
                INK_SOFT,
            )
        )
        chip_x = card_x + 32
        for status in STATUS_ORDER:
            label = f"{STATUS_LABELS[status]} {item['status'][status]}"
            svg, chip_width = chip(
                chip_x, y + 92, label, STATUS_COLORS[status], STATUS_TINTS[status], size=13, height=26
            )
            pieces.append(svg)
            chip_x += chip_width + 8
        number_x = card_x + card_width - 34
        pieces.append(svg_text(number_x, y + 74, str(item["count"]), 46, "700", color, anchor="end"))
        pieces.append(
            svg_text(number_x, y + 100, "支候选团队", 14, "400", INK_SOFT, anchor="end")
        )

    # 图例与脚注
    pieces.append(svg_text(88, legend_top, "图例", 14, "600", INK_SOFT))
    chip_x = 138
    for status in STATUS_ORDER:
        svg, chip_width = chip(
            chip_x, legend_top - 17, STATUS_LABELS[status], STATUS_COLORS[status], STATUS_TINTS[status],
            size=13, height=24,
        )
        pieces.append(svg)
        chip_x += chip_width + 10
    pieces.append(
        svg_text(
            88,
            legend_top + 38,
            f"候选 {total} 支 · {status_summary_text(totals)}。"
            "本图为候选图谱，已核实 / 已剔除数量按实际核实结果填写，未核实项不并入成果。",
            13,
            "400",
            INK_FAINT,
        )
    )
    pieces.append("</svg>")
    output.write_text("\n".join(pieces), encoding="utf-8")


# --------------------------------------------------------------------------
# 领域分图
# --------------------------------------------------------------------------
def columns_for(count: int) -> int:
    if count <= 6:
        return 1
    if count <= 18:
        return 2
    return 3


def write_domain_svg(output: Path, domain: str, data: dict[str, Any], domain_index: int) -> None:
    date = str(data["metadata"].get("snapshot_date", ""))
    color = domain_color(domain)
    teams = [
        team
        for team in data.get("teams", [])
        if (team.get("mapped_domain_name") or "待核实") == domain
    ]
    groups: dict[str, list[dict[str, Any]]] = {}
    for team in teams:
        key = one_line(team.get("mapped_subdomain_name")) or "待核实"
        groups.setdefault(key, []).append(team)

    def group_order(item: tuple[str, list[dict[str, Any]]]) -> tuple[int, int, str]:
        name, members = item
        return (1 if name == "待核实" else 0, -len(members), name)

    ordered_groups = sorted(groups.items(), key=group_order)
    counts = status_counts(teams, "project_verification_status")

    width = 1900
    margin = 56
    panel_width = width - margin * 2
    top = 196
    card_height = 62
    row_gap = 10
    header_height = 56
    panel_pad_left = 52
    panel_pad_right = 28
    content_width = panel_width - panel_pad_left - panel_pad_right
    panel_gap = 18

    layout: list[tuple[str, list[dict[str, Any]], int, int, float, int]] = []
    cursor = top
    for name, members in ordered_groups:
        cols = columns_for(len(members))
        rows = max(1, math.ceil(len(members) / cols))
        panel_height = header_height + rows * (card_height + row_gap) - row_gap + 22
        layout.append((name, members, cols, rows, cursor, panel_height))
        cursor += panel_height + panel_gap
    height = int(cursor + 96)

    pieces = [
        svg_open(width, height),
        svg_rect(0, 0, width, height, PAGE),
        svg_text(margin, 76, f"{domain} · 领域分图", 32, "700"),
        svg_text(
            margin,
            110,
            f"快照日期 {date} · 候选团队 {len(teams)} 支 · 子领域 {len(ordered_groups)} 个 · "
            f"{status_summary_text(counts)}",
            15,
            "400",
            INK_SOFT,
        ),
        svg_rect(margin, 130, 76, 4, color, rx=2),
    ]

    legend_x = width - margin - 330
    for status in STATUS_ORDER:
        svg, chip_width = chip(
            legend_x, 92, f"{STATUS_LABELS[status]} {counts[status]}",
            STATUS_COLORS[status], STATUS_TINTS[status], size=13, height=26,
        )
        pieces.append(svg)
        legend_x += chip_width + 10

    if not teams:
        pieces.append(svg_text(margin, top + 40, "该领域暂无候选团队。", 16, "400", INK_SOFT))

    for name, members, cols, rows, panel_y, panel_height in layout:
        pieces.append(
            svg_rect(margin, panel_y, panel_width, panel_height, PANEL, LINE, rx=18, stroke_width=1.2)
        )
        pieces.append(svg_rect(margin, panel_y + 18, 6, panel_height - 36, color, rx=3))
        pieces.append(svg_text(margin + panel_pad_left - 16, panel_y + 37, name, 19, "700", color))
        svg, chip_width = chip(
            margin + panel_width - 20 - (text_width(f"{len(members)} 支", 13) + 22),
            panel_y + 15,
            f"{len(members)} 支",
            color,
            "#eef3fb",
            size=13,
            height=26,
        )
        pieces.append(svg)

        ordered = sorted(
            members,
            key=lambda team: (
                0 if normalize_status(team.get("project_verification_status")) == "verified" else 1,
                team.get("team_name", ""),
            ),
        )
        card_width = (content_width - (cols - 1) * 14) / cols
        content_x = margin + panel_pad_left
        first_center = panel_y + header_height + card_height / 2 - row_gap / 2
        last_center = first_center + (rows - 1) * (card_height + row_gap)
        spine_x = margin + 30
        pieces.append(svg_line(spine_x, panel_y + 30, spine_x, last_center, "#dfe6f1", 2.0))

        for idx, team in enumerate(ordered):
            col = idx % cols
            line_index = idx // cols
            card_y = panel_y + header_height + line_index * (card_height + row_gap)
            card_x = content_x + col * (card_width + 14)
            card_center = card_y + card_height / 2
            status = normalize_status(team.get("project_verification_status"))
            accent = ATTENTION_COLORS.get(normalize_attention(team.get("attention_level")), INK_FAINT)

            pieces.append(
                svg_line(spine_x, card_center, card_x, card_center, "#e4eaf4", 1.4)
            )
            pieces.append(
                svg_rect(card_x, card_y, card_width, card_height, "#ffffff", LINE, rx=12, stroke_width=1.1)
            )
            pieces.append(svg_rect(card_x, card_y + 11, 5, card_height - 22, STATUS_COLORS[status], rx=2.5))

            label = STATUS_LABELS[status]
            chip_width = text_width(label, 12.5) + 20
            chip_x = card_x + card_width - chip_width - 14
            svg, _ = chip(
                chip_x, card_y + 19, label, STATUS_COLORS[status], STATUS_TINTS[status],
                size=12.5, height=24, pad=10,
            )
            pieces.append(svg)

            pieces.append(svg_circle(card_x + 22, card_y + 24, 3.2, accent))
            name_width = chip_x - (card_x + 32) - 10
            pieces.append(
                svg_text(card_x + 32, card_y + 28, fit_text(team.get("team_name"), 15, name_width), 15, "700")
            )
            meta = " · ".join(
                part
                for part in (
                    one_line(team.get("organization") or team.get("institution_name")),
                    one_line(team.get("leader_name")),
                    one_line(team.get("mapped_research_direction")),
                )
                if part
            )
            pieces.append(
                svg_text(
                    card_x + 32,
                    card_y + 48,
                    fit_text(meta, 12.5, card_width - 32 - 14),
                    12.5,
                    "400",
                    INK_SOFT,
                )
            )

    pieces.append(
        svg_text(
            margin,
            height - 44,
            "说明：团队按子领域分组；左侧竖线表示从子领域到团队的归属关系。"
            "条目颜色为项目核实状态，未核实项保留待核实标记。",
            13,
            "400",
            INK_FAINT,
        )
    )
    pieces.append("</svg>")
    output.write_text("\n".join(pieces), encoding="utf-8")


# --------------------------------------------------------------------------
# 团队卡片
# --------------------------------------------------------------------------
def build_evidence_index(tables: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    evidence = {
        row.get("evidence_id", ""): row
        for row in tables.get("evidence", [])
        if row.get("evidence_id")
    }
    by_team: dict[str, list[dict[str, Any]]] = {}
    for relation in tables.get("relations", []):
        team_id = relation.get("team_id")
        if team_id:
            by_team.setdefault(team_id, []).append(relation)
    return evidence, by_team


def url_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [one_line(item) for item in value if one_line(item)]
    text = one_line(value)
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [one_line(item) for item in parsed if one_line(item)]
    return [part for part in re.split(r"[\s,]+", text) if part]


TEAM_CARD_TEMPLATE = Template(
    """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$team_name</title>
<style>
  :root { --ink:#1f2a37; --soft:#5a6675; --faint:#8b96a8; --line:#e4e9f0; --accent:$accent; }
  * { box-sizing: border-box; }
  body { margin:0; background:#f5f7fb; color:var(--ink); line-height:1.65;
         font-family:"Microsoft YaHei","PingFang SC","Source Han Sans SC",Arial,sans-serif; }
  a { color:#2f6bd8; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .wrap { max-width:1040px; margin:0 auto; padding:26px 22px 64px; }
  .back { font-size:14px; }
  .card { background:#fff; border:1px solid var(--line); border-radius:18px; padding:26px 30px 30px;
          box-shadow:0 10px 30px rgba(31,42,55,.05); margin-top:14px; border-top:5px solid var(--accent); }
  h1 { font-size:26px; margin:0; }
  .badges { display:flex; gap:8px; flex-wrap:wrap; margin:14px 0 2px; }
  .badge { font-size:13px; font-weight:600; border-radius:999px; padding:4px 13px; }
  dl.grid { display:grid; grid-template-columns:132px 1fr; gap:7px 18px; margin:20px 0 0; }
  dl.grid dt { color:var(--soft); font-size:13.5px; margin:0; }
  dl.grid dd { margin:0; font-size:14.5px; }
  h2 { font-size:16px; margin:28px 0 12px; padding-left:11px; border-left:4px solid var(--accent); }
  ul.ev { list-style:none; margin:0; padding:0; }
  ul.ev li { border:1px solid var(--line); border-radius:12px; padding:11px 15px; margin-bottom:9px; background:#fbfcfe; }
  .ev-title { font-weight:600; font-size:14.5px; }
  .ev-meta { color:var(--faint); font-size:12.5px; margin-top:4px; }
  ul.src { list-style:none; margin:0; padding:0; }
  ul.src li { font-size:13.5px; margin-bottom:6px; word-break:break-all; }
  .footnote { color:var(--faint); font-size:12.5px; text-align:center; margin:16px 0 0; }
  .empty { color:var(--faint); font-size:14px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="back"><a href="../../../index.html">← 返回图谱首页</a></div>
  <article class="card">
    <h1>$team_name</h1>
    <div class="badges">$badges</div>
    <dl class="grid">$meta</dl>
    $attention_block
    $evidence_block
    $source_block
  </article>
  <p class="footnote">团队ID $team_id · 快照日期 $date</p>
</div>
</body>
</html>
"""
)


def badge(label: str, color: str, tint: str) -> str:
    return f'<span class="badge" style="color:{color};background:{tint}">{esc(label)}</span>'


def team_card_html(
    team: dict[str, Any],
    internal: dict[str, Any],
    date: str,
    evidence_index: dict[str, dict[str, Any]],
    relations: list[dict[str, Any]],
) -> str:
    domain = one_line(team.get("domain") or internal.get("mapped_domain_name")) or "待核实"
    subdomain = one_line(team.get("subdomain") or internal.get("mapped_subdomain_name")) or "待核实"
    status = normalize_status(team.get("verification_status") or internal.get("project_verification_status"))
    attention = normalize_attention(team.get("attention") or internal.get("attention_level"))
    accent = domain_color(domain)

    badges = [
        badge(domain, "#ffffff", accent),
        badge(STATUS_LABELS[status], STATUS_COLORS[status], STATUS_TINTS[status]),
        badge(ATTENTION_LABELS[attention], ATTENTION_COLORS[attention], "#f1f4f9"),
    ]

    def value(*keys: str) -> str:
        for key in keys:
            text = one_line(team.get(key)) or one_line(internal.get(key))
            if text:
                return text
        return ""

    meta_rows = [
        ("具体团队", value("team_name")),
        ("所属机构", value("institution")),
        ("城市 / 国家", " / ".join(part for part in (value("city"), value("country")) if part)),
        ("主领域 / 子领域", f"{domain} / {subdomain}"),
        ("负责人", value("leader", "leader_name")),
        ("研究方向", value("direction", "mapped_research_direction")),
    ]
    mapping_text = " · ".join(
        part
        for part in (
            label_of(value("mapping_method"), MAPPING_METHOD_LABELS),
            label_of(value("mapping_confidence"), MAPPING_CONFIDENCE_LABELS),
        )
        if part
    )
    if mapping_text:
        meta_rows.append(("领域映射", mapping_text))
    meta_html = "".join(
        f"<dt>{esc(label)}</dt><dd>{esc(text) or '<span class=\"empty\">待核实</span>'}</dd>"
        for label, text in meta_rows
    )

    reason = value("attention_reason")
    review = " · ".join(part for part in (value("reviewer"), value("reviewed_at")) if part)
    pending = clean_list_text(internal.get("pending_materials"))
    if attention == "pending":
        # 关注等级还是“待定”时，attention_reason 是程序的初始说明，不作为页面结论。
        reason_html = (
            '<p class="empty">关注理由：待人工填写。候选清单阶段，'
            "原系统评分与核实状态不作为项目结论。</p>"
        )
    elif reason:
        reason_html = f"<p>理由：{esc(reason)}</p>"
    else:
        reason_html = '<p class="empty">关注理由：待人工填写。</p>'
    attention_block = (
        "<h2>关注建议与复核</h2>"
        f"<p>关注等级：<strong>{esc(ATTENTION_LABELS[attention])}</strong>"
        + (f"　复核：{esc(review)}" if review else "")
        + "</p>"
        + reason_html
        + (f"<p>待补材料：{esc(pending)}</p>" if pending else "")
    )

    ev_items = []
    seen: set[str] = set()
    for relation in relations:
        evidence_id = relation.get("evidence_id")
        if not evidence_id or evidence_id in seen:
            continue
        seen.add(evidence_id)
        row = evidence_index.get(evidence_id)
        if not row:
            continue
        link = one_line(row.get("source_url"))
        title = one_line(row.get("title")) or evidence_id
        title_html = f'<a href="{esc(link)}" target="_blank" rel="noopener">{esc(title)}</a>' if link else esc(title)
        ev_meta = " · ".join(
            part
            for part in (
                label_of(row.get("source_name"), SOURCE_NAME_LABELS) or one_line(row.get("source_name")),
                one_line(row.get("published_at"))[:10],
                label_of(relation.get("relation_type"), RELATION_TYPE_LABELS),
            )
            if part
        )
        ev_items.append(
            f'<li><div class="ev-title">{title_html}</div><div class="ev-meta">{esc(ev_meta)}</div></li>'
        )
        if len(ev_items) >= 8:
            break
    evidence_block = (
        "<h2>关联证据</h2>" + "<ul class=\"ev\">" + "".join(ev_items) + "</ul>"
        if ev_items
        else '<h2>关联证据</h2><p class="empty">尚无已核实的关联证据，待人工核实后补充。</p>'
    )

    urls = url_list(internal.get("source_urls"))
    source_block = (
        "<h2>来源链接</h2><ul class=\"src\">"
        + "".join(
            f'<li><a href="{esc(url)}" target="_blank" rel="noopener">{esc(url)}</a></li>' for url in urls[:6]
        )
        + "</ul>"
        if urls
        else '<h2>来源链接</h2><p class="empty">来源链接待补充。</p>'
    )

    return TEAM_CARD_TEMPLATE.safe_substitute(
        team_name=esc(value("team_name")),
        team_id=esc(team.get("team_id", "")),
        date=esc(date),
        accent=accent,
        badges="".join(badges),
        meta=meta_html,
        attention_block=attention_block,
        evidence_block=evidence_block,
        source_block=source_block,
    )


def write_team_cards(output: Path, data: dict[str, Any]) -> None:
    cards_dir = output / "team_cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    date = str(data["metadata"].get("snapshot_date", ""))
    tables = data.get("tables", {})
    evidence_index, relations_by_team = build_evidence_index(tables)
    internal_by_id = {
        row.get("team_id", ""): row for row in data.get("teams", []) if row.get("team_id")
    }

    links = []
    for team in tables.get("teams", []):
        team_id = str(team.get("team_id", ""))
        internal = internal_by_id.get(team_id, {})
        filename = f"team_{slug(team_id)}.html"
        (cards_dir / filename).write_text(
            team_card_html(team, internal, date, evidence_index, relations_by_team.get(team_id, [])),
            encoding="utf-8",
        )
        domain = one_line(team.get("domain")) or "待核实"
        status = normalize_status(team.get("verification_status"))
        links.append(
            f'<li data-domain="{esc(domain)}">'
            f'<span class="dot" style="background:{domain_color(domain)}"></span>'
            f'<a href="{esc(filename)}">{esc(team.get("team_name", ""))}</a>'
            f'<span class="muted">{esc(domain)} · {esc(STATUS_LABELS[status])}</span></li>'
        )
    (cards_dir / "index.html").write_text(
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>团队卡片</title><style>"
        "body{margin:0;background:#f5f7fb;color:#1f2a37;line-height:1.6;"
        "font-family:'Microsoft YaHei','PingFang SC',Arial,sans-serif}"
        ".wrap{max-width:1040px;margin:0 auto;padding:26px 22px 64px}"
        ".card{background:#fff;border:1px solid #e4e9f0;border-radius:18px;padding:24px 28px;margin-top:14px}"
        "h1{font-size:24px;margin:0 0 6px}.back{font-size:14px}"
        "a{color:#2f6bd8;text-decoration:none}a:hover{text-decoration:underline}"
        "ul{list-style:none;margin:0;padding:0;columns:2;column-gap:28px}"
        "li{break-inside:avoid;padding:7px 0;border-bottom:1px solid #eef2f7;font-size:14.5px}"
        ".dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px;vertical-align:middle}"
        ".muted{color:#8b96a8;font-size:12.5px;margin-left:8px}"
        "</style></head><body><div class='wrap'>"
        "<div class='back'><a href='../../../index.html'>← 返回图谱首页</a></div>"
        "<div class='card'><h1>团队卡片</h1>"
        f"<p class='muted'>共 {len(tables.get('teams', []))} 张卡片 · 快照日期 {esc(date)}</p>"
        "<ul>" + "".join(links) + "</ul></div></div></body></html>",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------
def write_readme(output: Path, data_path: Path, data: dict[str, Any]) -> None:
    date = data["metadata"].get("snapshot_date", "")
    text = f"""# 国内战略力量图谱本地预览

输入快照日期：`{date}`

## 启动

预览首页 `index.html` 固定在项目根目录（本目录的上两级），请在项目根目录执行：

```powershell
python -m http.server 8000
```

然后打开 `http://localhost:8000/`。页面会在浏览器中读取 `result/data.json`，
本目录提供总图、分领域图与团队卡片页面。

## 生成命令

```powershell
python scripts/build_map.py `
  --data "{data_path}" `
  --output "map_{str(date).replace('-', '')}"
```

## 目录内容

| 文件 / 目录 | 说明 |
| --- | --- |
| `total_graph_*.svg` | 总图：领域 → 机构 / 子领域 / 团队 |
| `domain_graph_*.svg` | 六领域分图，按子领域分组的团队条目 |
| `team_cards/` | 每支团队一张卡片页，含关联证据与来源链接 |
| `teams.csv` / `evidence.csv` / `relations.csv` / `coverage.csv` | 提交用四张表 |

本目录中的总图、六领域分图、团队卡片和覆盖表均由同一份 `data.json` 生成。
没有写入演示数字；未核实团队在图表中保持“待核实”。
"""
    (output / "README.md").write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
def main() -> int:
    args = parse_args()
    data_path = args.data.resolve()
    output = args.output.resolve()
    if not data_path.is_file():
        raise FileNotFoundError(f"data.json does not exist: {data_path}")
    data = load_data(data_path)
    output.mkdir(parents=True, exist_ok=True)
    date = str(data["metadata"].get("snapshot_date", ""))
    compact_date = date.replace("-", "") or "snapshot"

    write_csv(output / "teams.csv", data["tables"]["teams"], TEAMS_COLUMNS)
    write_csv(output / "evidence.csv", data["tables"]["evidence"], EVIDENCE_COLUMNS)
    write_csv(output / "relations.csv", data["tables"]["relations"], RELATIONS_COLUMNS)
    write_csv(output / "coverage.csv", data["tables"]["coverage"], COVERAGE_COLUMNS)
    write_total_svg(output / f"total_graph_{compact_date}.svg", data)
    for index, domain in enumerate(DOMAIN_NAMES):
        filename = f"domain_graph_{code_for_domain(domain, list(DOMAIN_NAMES))}_{compact_date}.svg"
        write_domain_svg(output / filename, domain, data, index)
    write_team_cards(output, data)
    write_readme(output, data_path, data)

    print(f"输出目录：{output}")
    print(f"快照日期：{date}")
    print(f"团队数：{len(data['tables']['teams'])}")
    print(f"领域数：{len(DOMAIN_NAMES)}")
    print("原始数据修改：无")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())