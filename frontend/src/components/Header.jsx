import { Database, LockKeyhole, Search } from "lucide-react";
import { formatDate, formatNumber } from "../utils/format.js";

const NAV_ITEMS = [
  ["热点", "#/hot", "/hot"],
  ["领域", "#/domains", "/domains"],
  ["战略地图", "#/map", "/map"],
  ["团队", "#/teams", "/teams"],
  ["月报", "#/monthly", "/monthly"],
  ["工作台", "#/workspace", "/workspace"],
  ["开发者", "#/developers", "/developers"]
];

function isActiveRoute(routePath, itemPath) {
  if (itemPath === "/teams") return routePath === "/teams" || routePath.startsWith("/teams/");
  return routePath === itemPath;
}

export default function Header({ routePath, stats, source, domains, activeDomain, onDomainChange }) {
  return (
    <header className="topbar">
      <a className="brand" href="#/" aria-label="AI4S 前沿情报站">
        <span className="brand-mark">A</span>
        <span>AI4S 前沿情报站</span>
      </a>
      <nav className="nav-tabs" aria-label="公开站导航">
        {NAV_ITEMS.map(([item, href, itemPath]) => (
          <a className={isActiveRoute(routePath, itemPath) ? "active" : ""} href={href} key={item}>
            {item}
          </a>
        ))}
      </nav>
      <div className="top-actions">
        <label className="domain-select">
          <Search size={16} aria-hidden="true" />
          <select
            value={activeDomain}
            onChange={(event) => onDomainChange(event.target.value)}
            aria-label="筛选领域"
          >
            <option value="全部">全部领域</option>
            {domains.map((domain) => (
              <option value={domain} key={domain}>
                {domain}
              </option>
            ))}
          </select>
        </label>
        <span className="evidence-pill" title={source === "api" ? "API 数据" : "公开快照数据"}>
          <Database size={14} aria-hidden="true" />
          证据库 {formatNumber(stats.evidenceCount)} 条
        </span>
        <span className="snapshot-date">{formatDate(stats.snapshotDate)}</span>
        <button className="login-button" type="button">
          <LockKeyhole size={15} aria-hidden="true" />
          登录
        </button>
      </div>
    </header>
  );
}
