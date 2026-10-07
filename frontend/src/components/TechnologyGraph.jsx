import { useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, GitMerge, Network, Users } from "lucide-react";
import { domainColor } from "../data/domain.js";
import { formatDate, formatNumber } from "../utils/format.js";

const WIDTH = 1000;
const HEIGHT = 560;
const CENTER = { x: 500, y: 284 };
const collator = new Intl.Collator("zh-CN");
const STOP_TERMS = new Set(["AI", "人工智能", "智能", "科学", "技术", "研究", "系统", "平台", "模型", "算法", "应用"]);

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function teamScore(team) {
  return Number(team.evidence_count || team.associated_evidence?.length || 0);
}

function shortLabel(label, limit = 8) {
  if (!label) return "未命名";
  return label.length > limit ? `${label.slice(0, limit)}...` : label;
}

function compactText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim();
}

function getDirectionTags(team) {
  const raw = [team.subdomain, team.direction]
    .filter(Boolean)
    .join("；")
    .split(/[；;、,，/|｜]+/);

  return unique(
    raw
      .map((item) => compactText(item).replace(/[()（）\[\]【】]/g, ""))
      .filter((item) => item.length >= 3 && !STOP_TERMS.has(item))
  ).slice(0, 12);
}

function polarPoint(angle, radius, yScale = 0.74, origin = CENTER) {
  return {
    x: origin.x + Math.cos(angle) * radius,
    y: origin.y + Math.sin(angle) * radius * yScale
  };
}

function groupBy(items, getKey) {
  const groups = new Map();
  for (const item of items) {
    const key = getKey(item);
    if (!key) continue;
    const rows = groups.get(key) ?? [];
    rows.push(item);
    groups.set(key, rows);
  }
  return groups;
}

function buildSelectedTeams(snapshot, activeDomain) {
  const coverage = snapshot?.coverage ?? [];
  const allTeams = snapshot?.teams ?? [];
  const domains = unique([...coverage.map((item) => item.domain), ...allTeams.map((team) => team.domain)]).filter(
    (domain) => activeDomain === "全部" || domain === activeDomain
  );
  const teamsByDomain = groupBy(
    allTeams.filter((team) => domains.includes(team.domain)),
    (team) => team.domain
  );
  const perDomainLimit = activeDomain === "全部" ? 7 : 54;
  const selected = domains.flatMap((domain) =>
    [...(teamsByDomain.get(domain) ?? [])]
      .sort((a, b) => teamScore(b) - teamScore(a) || collator.compare(a.team_name, b.team_name))
      .slice(0, perDomainLimit)
  );

  if (activeDomain !== "全部") return selected;

  const selectedIds = new Set(selected.map((team) => team.team_id));
  const fill = allTeams
    .filter((team) => domains.includes(team.domain) && !selectedIds.has(team.team_id))
    .sort((a, b) => teamScore(b) - teamScore(a) || collator.compare(a.team_name, b.team_name))
    .slice(0, Math.max(0, 42 - selected.length));

  return [...selected, ...fill].slice(0, 48);
}

function relationBetween(source, target) {
  const reasons = [];
  let weight = 0;
  let type = "domain";
  let sharedTags = [];

  if (source.institution && source.institution === target.institution) {
    weight += 5;
    type = "institution";
    reasons.push(`同机构：${source.institution}`);
  }

  if (source.leader && source.leader === target.leader) {
    weight += 4;
    type = "leader";
    reasons.push(`同负责人：${source.leader}`);
  }

  const sourceTags = getDirectionTags(source);
  const targetTags = new Set(getDirectionTags(target));
  sharedTags = sourceTags.filter((tag) => targetTags.has(tag)).slice(0, 3);
  if (sharedTags.length) {
    weight += 3 + sharedTags.length;
    if (type === "domain") type = "topic";
    reasons.push(`共同方向：${sharedTags.map((tag) => shortLabel(tag, 12)).join("、")}`);
  }

  if (source.domain && source.domain === target.domain) {
    weight += 1.2;
    reasons.push(`同领域：${source.domain}`);
  }

  if (weight < 1.2) return null;

  const displayLabel =
    type === "institution"
      ? "同机构"
      : type === "leader"
        ? "同负责人"
        : type === "topic"
          ? `共同方向：${shortLabel(sharedTags[0], 6)}`
          : `同领域：${shortLabel(source.domain, 6)}`;

  return {
    weight,
    type,
    label: reasons.slice(0, 2).join("；"),
    displayLabel
  };
}

function buildEdges(teams, activeDomain) {
  const candidates = [];
  for (let i = 0; i < teams.length; i += 1) {
    for (let j = i + 1; j < teams.length; j += 1) {
      const relation = relationBetween(teams[i], teams[j]);
      if (!relation) continue;
      const threshold = activeDomain === "全部" ? 2.2 : 1.2;
      if (relation.weight < threshold) continue;
      candidates.push({
        id: `${teams[i].team_id}-${teams[j].team_id}`,
        source: teams[i].team_id,
        target: teams[j].team_id,
        ...relation
      });
    }
  }

  candidates.sort((a, b) => b.weight - a.weight || collator.compare(a.label, b.label));

  const maxEdges = clamp(Math.round(teams.length * 2.1), 18, 92);
  const degrees = new Map();
  const selected = [];

  for (const edge of candidates) {
    if (selected.length >= maxEdges) break;
    const sourceDegree = degrees.get(edge.source) ?? 0;
    const targetDegree = degrees.get(edge.target) ?? 0;
    if (sourceDegree >= 4 && targetDegree >= 4) continue;
    selected.push(edge);
    degrees.set(edge.source, sourceDegree + 1);
    degrees.set(edge.target, targetDegree + 1);
  }

  for (const edge of candidates) {
    if (selected.length >= maxEdges) break;
    if (selected.some((item) => item.id === edge.id)) continue;
    if ((degrees.get(edge.source) ?? 0) > 0 && (degrees.get(edge.target) ?? 0) > 0) continue;
    selected.push(edge);
    degrees.set(edge.source, (degrees.get(edge.source) ?? 0) + 1);
    degrees.set(edge.target, (degrees.get(edge.target) ?? 0) + 1);
  }

  return selected;
}

function edgeTargetLength(edge) {
  if (edge.type === "institution" || edge.type === "leader") return 108;
  if (edge.type === "topic") return 138;
  return 176;
}

function buildNodes(teams, edges) {
  const degrees = new Map();
  for (const edge of edges) {
    degrees.set(edge.source, (degrees.get(edge.source) ?? 0) + 1);
    degrees.set(edge.target, (degrees.get(edge.target) ?? 0) + 1);
  }

  const nodes = teams.map((team, index) => {
    const count = Math.max(teams.length, 1);
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count;
    const ring = 196 + ((index * 17) % 7) * 9;
    const point = polarPoint(angle, count <= 1 ? 0 : ring, 0.72);
    const degree = degrees.get(team.team_id) ?? 0;

    return {
      id: team.team_id,
      type: "team",
      label: team.team_name,
      x: clamp(point.x, 64, WIDTH - 64),
      y: clamp(point.y, 64, HEIGHT - 72),
      vx: 0,
      vy: 0,
      radius: 14 + Math.min(8, Math.sqrt(teamScore(team) + degree + 1) * 1.08),
      color: domainColor(team.domain),
      team,
      degree,
      meta: {
        领域: team.domain || "未分领域",
        机构: team.institution || "待补",
        负责人: team.leader || "待补",
        关联团队: `${formatNumber(degree)} 支`,
        关联证据: `${formatNumber(teamScore(team))} 条`,
        研究方向: team.subdomain || team.direction || "待补"
      }
    };
  });

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const linkedEdges = edges
    .map((edge) => ({ ...edge, sourceNode: nodeById.get(edge.source), targetNode: nodeById.get(edge.target) }))
    .filter((edge) => edge.sourceNode && edge.targetNode);

  for (let tick = 0; tick < 180; tick += 1) {
    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const source = nodes[i];
        const target = nodes[j];
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const distance = Math.max(1, Math.hypot(dx, dy));
        const minDistance = source.radius + target.radius + 18;
        const repulsion = 2800 / (distance * distance);
        const collision = distance < minDistance ? (minDistance - distance) * 0.032 : 0;
        const force = repulsion + collision;
        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;
        source.vx -= fx;
        source.vy -= fy;
        target.vx += fx;
        target.vy += fy;
      }
    }

    for (const edge of linkedEdges) {
      const source = edge.sourceNode;
      const target = edge.targetNode;
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.max(1, Math.hypot(dx, dy));
      const targetLength = edgeTargetLength(edge);
      const strength = 0.006 + Math.min(edge.weight, 7) * 0.0016;
      const force = (distance - targetLength) * strength;
      const fx = (dx / distance) * force;
      const fy = (dy / distance) * force;
      source.vx += fx;
      source.vy += fy;
      target.vx -= fx;
      target.vy -= fy;
    }

    for (const node of nodes) {
      node.vx += (CENTER.x - node.x) * 0.0038;
      node.vy += (CENTER.y - node.y) * 0.0042;
      node.x = clamp(node.x + node.vx, 58, WIDTH - 58);
      node.y = clamp(node.y + node.vy, 58, HEIGHT - 68);
      node.vx *= 0.72;
      node.vy *= 0.72;
    }
  }

  return nodes.map(({ vx, vy, ...node }) => node);
}

function buildGraph(snapshot, activeDomain) {
  const teams = buildSelectedTeams(snapshot, activeDomain);
  const rawEdges = buildEdges(teams, activeDomain);
  const nodes = buildNodes(teams, rawEdges);
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const edges = rawEdges
    .map((edge) => ({ ...edge, sourceNode: nodeById.get(edge.source), targetNode: nodeById.get(edge.target) }))
    .filter((edge) => edge.sourceNode && edge.targetNode);

  return {
    nodes,
    edges
  };
}

function svgPointFromPointer(svg, event) {
  const matrix = svg?.getScreenCTM();
  if (!svg || !matrix) return null;

  const point = svg.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  return point.matrixTransform(matrix.inverse());
}

function GraphEdge({ edge, selected }) {
  const x = (edge.sourceNode.x + edge.targetNode.x) / 2;
  const y = (edge.sourceNode.y + edge.targetNode.y) / 2;
  const label = shortLabel(edge.displayLabel, 12);
  const labelWidth = clamp([...label].length * 10 + 16, 44, 136);

  return (
    <g className={selected ? "tg-edge-group related" : "tg-edge-group"}>
      <title>{`${edge.sourceNode.label} - ${edge.targetNode.label}：${edge.label}`}</title>
      <line
        className={`tg-edge tg-edge-${edge.type}`}
        x1={edge.sourceNode.x}
        y1={edge.sourceNode.y}
        x2={edge.targetNode.x}
        y2={edge.targetNode.y}
        style={{ "--edge-color": edge.sourceNode.color }}
      />
      <g className="tg-edge-label" transform={`translate(${x} ${y})`}>
        <rect x={-labelWidth / 2} y="-10" width={labelWidth} height="20" rx="4" />
        <text textAnchor="middle" dominantBaseline="central">
          {label}
        </text>
      </g>
    </g>
  );
}

function GraphNode({ node, selected, onSelect, onPositionChange }) {
  const dragRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleKeyDown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(node.id);
    }
  };

  const handlePointerDown = (event) => {
    if (event.button !== 0) return;
    const svg = event.currentTarget.ownerSVGElement;
    const point = svgPointFromPointer(svg, event);
    if (!point) return;

    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      offsetX: point.x - node.x,
      offsetY: point.y - node.y
    };
    setDragging(true);
    onSelect(node.id);
  };

  const handlePointerMove = (event) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const point = svgPointFromPointer(event.currentTarget.ownerSVGElement, event);
    if (!point) return;

    event.preventDefault();
    onPositionChange(node.id, {
      x: clamp(point.x - drag.offsetX, node.radius + 8, WIDTH - node.radius - 8),
      y: clamp(point.y - drag.offsetY, node.radius + 8, HEIGHT - node.radius - 24)
    });
  };

  const finishDrag = (event) => {
    if (dragRef.current?.pointerId !== event.pointerId) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    dragRef.current = null;
    setDragging(false);
  };

  return (
    <g
      className={`tg-node${selected ? " selected" : ""}${dragging ? " dragging" : ""}`}
      transform={`translate(${node.x} ${node.y})`}
      style={{ "--node-color": node.color }}
      role="button"
      tabIndex="0"
      aria-label={`团队：${node.label}`}
      onClick={() => onSelect(node.id)}
      onKeyDown={handleKeyDown}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={finishDrag}
      onPointerCancel={finishDrag}
    >
      <title>{node.label}</title>
      <circle r={node.radius} />
      <text textAnchor="middle" y={node.radius + 16}>
        {shortLabel(node.label, 7)}
      </text>
    </g>
  );
}

function GraphInspector({ node, edges }) {
  const related = edges
    .filter((edge) => edge.source === node?.id || edge.target === node?.id)
    .slice(0, 6)
    .map((edge) => {
      const peer = edge.source === node.id ? edge.targetNode : edge.sourceNode;
      return { ...edge, peer };
    });
  const entries = Object.entries(node?.meta ?? {}).filter(([, value]) => value);

  return (
    <aside className="tech-inspector" style={{ "--node-color": node?.color ?? "#234f73" }}>
      <span>团队节点</span>
      <h2>{node?.label ?? "暂无团队"}</h2>
      <dl>
        {entries.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <section className="tech-related">
        <h3>相互关联团队</h3>
        {related.length ? (
          related.map((edge) => (
            <a href={`#/teams/${encodeURIComponent(edge.peer.id)}`} key={edge.id}>
              <strong>{edge.peer.label}</strong>
              <span>{edge.label}</span>
            </a>
          ))
        ) : (
          <p>当前筛选下暂无强关联团队。</p>
        )}
      </section>
      {node?.id && (
        <a href={`#/teams/${encodeURIComponent(node.id)}`} className="graph-detail-link">
          查看团队详情
        </a>
      )}
    </aside>
  );
}

export default function TechnologyGraph({ snapshot, stats, loading, error, activeDomain, onDomainChange }) {
  const coverage = snapshot?.coverage ?? [];
  const graph = useMemo(() => buildGraph(snapshot, activeDomain), [snapshot, activeDomain]);
  const [selectedId, setSelectedId] = useState("");
  const [nodePositions, setNodePositions] = useState({});

  useEffect(() => {
    setNodePositions({});
  }, [graph]);

  const renderedGraph = useMemo(() => {
    const nodes = graph.nodes.map((node) => ({ ...node, ...(nodePositions[node.id] ?? {}) }));
    const nodeById = new Map(nodes.map((node) => [node.id, node]));
    const edges = graph.edges.map((edge) => ({
      ...edge,
      sourceNode: nodeById.get(edge.source),
      targetNode: nodeById.get(edge.target)
    }));
    return { nodes, edges };
  }, [graph, nodePositions]);

  const selectedNode = renderedGraph.nodes.find((node) => node.id === selectedId) ?? renderedGraph.nodes[0];
  const handlePositionChange = (nodeId, position) => {
    setNodePositions((current) => ({ ...current, [nodeId]: position }));
  };

  return (
    <section className="technology-graph" id="战略地图技术图谱">
      <div className="graph-head">
        <div>
          <span className="eyebrow">战略地图</span>
          <h1>技术图谱</h1>
        </div>
        <div className="graph-stats" aria-label="技术图谱统计">
          <span>
            <Users size={15} aria-hidden="true" />
            {formatNumber(graph.nodes.length)} 个团队节点
          </span>
          <span>
            <GitMerge size={15} aria-hidden="true" />
            {formatNumber(graph.edges.length)} 条团队关系
          </span>
          <span>{formatDate(stats.snapshotDate)} 快照</span>
        </div>
      </div>

      {(loading || error) && (
        <div className={error ? "graph-banner error" : "graph-banner"}>
          {error && <AlertCircle size={16} aria-hidden="true" />}
          {error ? "数据接口暂不可用" : "正在读取公开数据..."}
        </div>
      )}

      <div className="technology-shell">
        <div className="technology-stage">
          <svg className="technology-graph-svg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="技术图谱团队关系">
            <defs>
              <filter id="tg-node-shadow" x="-40%" y="-40%" width="180%" height="180%">
                <feDropShadow dx="0" dy="8" stdDeviation="8" floodColor="#1f2a37" floodOpacity="0.12" />
              </filter>
            </defs>
            <g className="tg-edges">
              {renderedGraph.edges.map((edge) => (
                <GraphEdge
                  edge={edge}
                  selected={edge.source === selectedNode?.id || edge.target === selectedNode?.id}
                  key={edge.id}
                />
              ))}
            </g>
            <g className="tg-nodes">
              {renderedGraph.nodes.map((node) => (
                <GraphNode
                  node={node}
                  selected={selectedNode?.id === node.id}
                  onSelect={setSelectedId}
                  onPositionChange={handlePositionChange}
                  key={node.id}
                />
              ))}
            </g>
          </svg>
        </div>
        <GraphInspector node={selectedNode} edges={renderedGraph.edges} />
      </div>

      <div className="graph-footer">
        <div className="graph-type-legend" aria-label="关系类型">
          <span>
            <Network size={14} aria-hidden="true" />
            节点均为团队
          </span>
          <span>粗线优先表示同机构、同负责人或共同方向</span>
        </div>
        <div className="graph-domain-filter" aria-label="领域筛选">
          {coverage.map((item) => (
            <button
              type="button"
              className={activeDomain === item.domain ? "legend-item active" : "legend-item"}
              key={item.domain}
              onClick={() => onDomainChange(activeDomain === item.domain ? "全部" : item.domain)}
            >
              <span style={{ backgroundColor: domainColor(item.domain) }} />
              {item.domain}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
