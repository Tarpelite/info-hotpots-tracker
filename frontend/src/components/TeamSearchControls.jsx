import { Search, SlidersHorizontal, X } from "lucide-react";
import { statusLabel } from "../data/domain.js";

const STATUSES = ["candidate", "verified", "rejected", "collected", "legacy_unverified"];

export default function TeamSearchControls({
  keyword,
  onKeywordChange,
  domain,
  onDomainChange,
  status,
  onStatusChange,
  domains,
  totalCount,
  resultCount,
  onReset
}) {
  const hasFilter = keyword || domain !== "全部" || status !== "全部";

  return (
    <section className="team-controls" aria-label="团队搜索与筛选">
      <label className="team-searchbox">
        <Search size={17} aria-hidden="true" />
        <input
          value={keyword}
          onChange={(event) => onKeywordChange(event.target.value)}
          placeholder="搜索团队、机构、负责人、方向、地点"
          aria-label="搜索团队、机构、负责人、方向、地点"
        />
      </label>
      <label className="team-filter">
        <SlidersHorizontal size={16} aria-hidden="true" />
        <select value={domain} onChange={(event) => onDomainChange(event.target.value)} aria-label="按领域筛选">
          <option value="全部">全部领域</option>
          {domains.map((item) => (
            <option value={item} key={item}>
              {item}
            </option>
          ))}
        </select>
      </label>
      <label className="team-filter">
        <select value={status} onChange={(event) => onStatusChange(event.target.value)} aria-label="按状态筛选">
          <option value="全部">全部状态</option>
          {STATUSES.map((item) => (
            <option value={item} key={item}>
              {statusLabel(item)}
            </option>
          ))}
        </select>
      </label>
      <div className="team-result-count">
        匹配 <strong>{resultCount}</strong> / {totalCount}
      </div>
      {hasFilter && (
        <button className="team-reset" type="button" onClick={onReset}>
          <X size={15} aria-hidden="true" />
          清空
        </button>
      )}
    </section>
  );
}
