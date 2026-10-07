import { useEffect, useMemo, useState } from "react";
import { domainColor, statusLabel } from "../data/domain.js";
import Pagination from "./Pagination.jsx";
import TeamSearchControls from "./TeamSearchControls.jsx";

export default function TeamExplorer({ teams, activeDomain }) {
  const [keyword, setKeyword] = useState("");
  const [domain, setDomain] = useState(activeDomain);
  const [status, setStatus] = useState("全部");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(18);

  useEffect(() => {
    setDomain(activeDomain);
  }, [activeDomain]);

  const filtered = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    return teams
      .filter((team) => domain === "全部" || team.domain === domain)
      .filter((team) => status === "全部" || team.verification_status === status)
      .filter((team) => {
        if (!kw) return true;
        return [
          team.team_name,
          team.institution,
          team.domain,
          team.subdomain,
          team.direction,
          team.leader,
          team.location?.city,
          team.location?.country,
          team.location?.display_name
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(kw);
      });
  }, [teams, domain, status, keyword]);

  const domains = useMemo(() => [...new Set(teams.map((team) => team.domain).filter(Boolean))], [teams]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, pageCount);
  const startIndex = (safePage - 1) * pageSize;
  const pagedTeams = filtered.slice(startIndex, startIndex + pageSize);

  useEffect(() => {
    setPage(1);
  }, [keyword, domain, status, pageSize]);

  function resetFilters() {
    setKeyword("");
    setDomain("全部");
    setStatus("全部");
  }

  return (
    <section className="section-band" id="团队">
      <div className="section-head">
        <div>
          <span className="eyebrow">团队</span>
          <h2>战略团队索引</h2>
        </div>
      </div>
      <TeamSearchControls
        keyword={keyword}
        onKeywordChange={setKeyword}
        domain={domain}
        onDomainChange={setDomain}
        status={status}
        onStatusChange={setStatus}
        domains={domains}
        totalCount={teams.length}
        resultCount={filtered.length}
        onReset={resetFilters}
      />
      <div className="team-grid">
        {pagedTeams.map((team) => (
          <a
            className="team-card"
            href={`#/teams/${encodeURIComponent(team.team_id)}`}
            key={team.team_id}
            style={{ "--domain": domainColor(team.domain) }}
          >
            <div className="team-topline">
              <span>{team.domain}</span>
              <em>{statusLabel(team.verification_status)}</em>
            </div>
            <h3>{team.team_name}</h3>
            <p className="team-meta">
              {[team.institution, team.leader].filter(Boolean).join(" / ") || "机构待补"}
            </p>
            <p className="team-location">
              {[team.location?.country, team.location?.city || team.location?.raw].filter(Boolean).join(" · ") || "位置待补"}
            </p>
            <p className="team-direction">{team.direction || "研究方向待补充"}</p>
          </a>
        ))}
      </div>
      <Pagination
        page={safePage}
        pageCount={pageCount}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
        total={filtered.length}
        start={filtered.length ? startIndex + 1 : 0}
        end={Math.min(startIndex + pageSize, filtered.length)}
      />
    </section>
  );
}
