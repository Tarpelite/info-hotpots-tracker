import { useMemo, useState } from "react";
import Header from "./components/Header.jsx";
import Map from "./components/Map.jsx";
import DomainOverview from "./components/DomainOverview.jsx";
import EvidenceRail from "./components/EvidenceRail.jsx";
import TeamExplorer from "./components/TeamExplorer.jsx";
import { usePublicSnapshot } from "./hooks/usePublicSnapshot.js";
import { useHashRoute } from "./hooks/useHashRoute.js";
import { buildSnapshotStats } from "./utils/summary.js";
import { domainColor, statusLabel } from "./data/domain.js";
import { formatDateTime, formatNumber } from "./utils/format.js";

function HomePage({ snapshot, stats, loading, error, activeDomain, onDomainChange }) {
  return (
    <Map
      snapshot={snapshot}
      stats={stats}
      loading={loading}
      error={error}
      activeDomain={activeDomain}
      onDomainChange={onDomainChange}
      showAsk
    />
  );
}

function StrategicMapPage({ snapshot, stats, loading, error, activeDomain, onDomainChange }) {
  return (
    <Map
      snapshot={snapshot}
      stats={stats}
      loading={loading}
      error={error}
      activeDomain={activeDomain}
      onDomainChange={onDomainChange}
      showAsk={false}
    />
  );
}

function PlaceholderPage({ title, eyebrow, body }) {
  return (
    <section className="route-page compact-route">
      <div className="section-head">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
        </div>
      </div>
      <p className="route-note">{body}</p>
    </section>
  );
}

function SourceLinks({ links }) {
  if (!links?.length) return <p className="empty-detail">暂无来源链接。</p>;

  return (
    <div className="source-list">
      {links.slice(0, 10).map((url, index) => (
        <a href={url} target="_blank" rel="noreferrer" key={`${url}-${index}`}>
          <span>来源 {index + 1}</span>
          <strong>{url}</strong>
        </a>
      ))}
    </div>
  );
}

function PeopleList({ title, people }) {
  if (!people?.length) return null;

  return (
    <section className="detail-block">
      <h2>{title}</h2>
      <div className="people-list">
        {people.map((person) => (
          <a
            className="person-chip"
            href={person.profile_url || "#"}
            target={person.profile_url ? "_blank" : undefined}
            rel={person.profile_url ? "noreferrer" : undefined}
            key={person.id || person.name}
          >
            <strong>{person.name || "未命名成员"}</strong>
            <span>{[person.role, person.title].filter(Boolean).join(" / ") || "角色待补"}</span>
          </a>
        ))}
      </div>
    </section>
  );
}

function EvidenceList({ evidence }) {
  if (!evidence?.length) return <p className="empty-detail">暂无可关联证据。</p>;

  return (
    <div className="detail-evidence-list">
      {evidence.map((item) => (
        <a
          className="detail-evidence-item"
          href={item.source_url || "#"}
          target={item.source_url ? "_blank" : undefined}
          rel={item.source_url ? "noreferrer" : undefined}
          key={item.evidence_id}
        >
          <div>
            <span>{item.source_name || item.relation_type || "公开证据"}</span>
            <strong>{item.summary || item.title}</strong>
            {item.claim && <p>{item.claim}</p>}
          </div>
          <em>{formatDateTime(item.published_at || item.captured_at)}</em>
        </a>
      ))}
    </div>
  );
}

function TeamDetailPage({ team, loading }) {
  if (loading) {
    return (
      <section className="route-page compact-route">
        <a className="back-link" href="#/teams">返回团队列表</a>
        <h2>正在加载团队详情</h2>
        <p className="route-note">数据来自 result/data.json，加载完成后会显示团队记录。</p>
      </section>
    );
  }

  if (!team) {
    return (
      <section className="route-page compact-route">
        <a className="back-link" href="#/teams">返回团队列表</a>
        <h2>未找到团队</h2>
        <p className="route-note">当前团队记录不存在或数据尚未加载完成。</p>
      </section>
    );
  }

  const locationText = [
    team.location?.country,
    team.location?.city,
    team.location?.raw && team.location.raw !== team.location.city ? team.location.raw : ""
  ]
    .filter(Boolean)
    .join(" / ");

  const details = [
    ["机构", team.institution || "待补"],
    ["负责人", [team.leader, team.leader_role].filter(Boolean).join(" / ") || "待补"],
    ["领域", [team.domain, team.subdomain].filter(Boolean).join(" / ") || "待补"],
    ["所在位置", locationText || "待补"],
    ["证据数", formatNumber(team.evidence_count || team.associated_evidence?.length || 0)],
    ["状态", team.project_verification_status || team.candidate_status || statusLabel(team.verification_status)]
  ];

  return (
    <section className="route-page detail-route">
      <a className="back-link" href="#/teams">返回团队列表</a>
      <article className="team-detail" style={{ "--domain": domainColor(team.domain) }}>
        <div className="team-detail-head">
          <span>{team.domain || "未分领域"}</span>
          <em>{statusLabel(team.verification_status)}</em>
        </div>
        <h1>{team.team_name}</h1>
        <div className="detail-grid">
          {details.map(([label, value]) => (
            <div className="detail-item" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
        <section className="detail-block">
          <h2>研究方向</h2>
          <p>{team.direction || "研究方向待补充"}</p>
        </section>
        {team.description && (
          <section className="detail-block">
            <h2>团队简介</h2>
            <p>{team.description}</p>
          </section>
        )}
        <section className="detail-block">
          <h2>所在位置</h2>
          <div className="location-panel">
            <div>
              <span>归属地</span>
              <strong>{locationText || "待补"}</strong>
            </div>
            <div>
              <span>地理编码</span>
              <strong>{team.location?.display_name || "暂无地理编码结果"}</strong>
            </div>
            <div>
              <span>经纬度</span>
              <strong>
                {[team.location?.lat, team.location?.lon].filter(Boolean).join(", ") || "待补"}
              </strong>
            </div>
            {team.location?.source_url && (
              <a href={team.location.source_url} target="_blank" rel="noreferrer">
                查看定位来源
              </a>
            )}
          </div>
        </section>
        <PeopleList title="负责人" people={team.leaders} />
        <PeopleList title="相关成员" people={team.members} />
        <section className="detail-block">
          <h2>关联证据</h2>
          <EvidenceList evidence={team.associated_evidence} />
        </section>
        <section className="detail-block">
          <h2>来源链接</h2>
          <SourceLinks links={team.source_urls} />
        </section>
        {team.pending_materials?.length > 0 && (
          <section className="detail-block">
            <h2>待补材料</h2>
            <div className="pending-list">
              {team.pending_materials.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </section>
        )}
        {team.attention_reason && (
          <section className="detail-block">
            <h2>复核说明</h2>
            <p>{team.attention_reason}</p>
          </section>
        )}
        <footer className="detail-footer">
          <span>最近更新：{formatDateTime(team.recent_update || team.source_data_updated_at)}</span>
          <span>映射方式：{team.mapping_method || "待补"}</span>
          <span>置信度：{team.mapping_confidence || "待补"}</span>
        </footer>
      </article>
    </section>
  );
}

export default function App() {
  const { snapshot, loading, error, source } = usePublicSnapshot();
  const route = useHashRoute();
  const [activeDomain, setActiveDomain] = useState("全部");

  const stats = useMemo(() => buildSnapshotStats(snapshot), [snapshot]);
  const domains = snapshot?.coverage?.map((item) => item.domain).filter(Boolean) ?? [];
  const teams = snapshot?.teams ?? [];
  const routePath = route.path;
  const teamId = routePath.startsWith("/teams/") ? decodeURIComponent(routePath.replace("/teams/", "")) : "";
  const selectedTeam = teamId ? teams.find((team) => team.team_id === teamId) : null;

  const page = (() => {
    if (routePath === "/") {
      return (
        <HomePage
          snapshot={snapshot}
          stats={stats}
          loading={loading}
          error={error}
          activeDomain={activeDomain}
          onDomainChange={setActiveDomain}
        />
      );
    }

    if (routePath === "/map") {
      return (
        <StrategicMapPage
          snapshot={snapshot}
          stats={stats}
          loading={loading}
          error={error}
          activeDomain={activeDomain}
          onDomainChange={setActiveDomain}
        />
      );
    }

    if (routePath === "/hot") {
      return <EvidenceRail evidence={snapshot?.latestEvidence ?? []} stats={stats} />;
    }

    if (routePath === "/domains") {
      return (
        <DomainOverview
          coverage={snapshot?.coverage ?? []}
          activeDomain={activeDomain}
          onDomainChange={setActiveDomain}
        />
      );
    }

    if (routePath === "/teams") {
      return <TeamExplorer teams={teams} activeDomain={activeDomain} />;
    }

    if (routePath.startsWith("/teams/")) {
      return <TeamDetailPage team={selectedTeam} loading={loading} />;
    }

    if (routePath === "/monthly") {
      return (
        <PlaceholderPage
          eyebrow="月报"
          title="月报工作区"
          body="月报页已作为独立路由预留，后续可接入后端月度报告接口。"
        />
      );
    }

    if (routePath === "/workspace") {
      return (
        <PlaceholderPage
          eyebrow="工作台"
          title="工作台"
          body="工作台页已作为独立路由预留，后续可接入登录态和内部工作流。"
        />
      );
    }

    if (routePath === "/developers") {
      return (
        <PlaceholderPage
          eyebrow="开发者"
          title="开发者入口"
          body="开发者页已作为独立路由预留，后续可放置接口说明和数据字典。"
        />
      );
    }

    return (
      <PlaceholderPage
        eyebrow="404"
        title="页面不存在"
        body="请通过上方工作栏切换到已有页面。"
      />
    );
  })();

  return (
    <div className="site-shell" id="top">
      <Header
        routePath={routePath}
        stats={stats}
        source={source}
        domains={domains}
        activeDomain={activeDomain}
        onDomainChange={setActiveDomain}
      />
      <main>{page}</main>
    </div>
  );
}
