import { ArrowUpRight } from "lucide-react";
import { domainColor } from "../data/domain.js";
import { formatNumber } from "../utils/format.js";

export default function DomainOverview({ coverage, activeDomain, onDomainChange }) {
  return (
    <section className="section-band" id="领域">
      <div className="section-head">
        <div>
          <span className="eyebrow">领域</span>
          <h2>六个方向的候选团队覆盖</h2>
        </div>
        <button className="text-action" type="button" onClick={() => onDomainChange("全部")}>
          <ArrowUpRight size={16} aria-hidden="true" />
          全部领域
        </button>
      </div>
      <div className="domain-grid">
        {coverage.map((item) => {
          const count = Number(item.candidate_count || 0);
          const width = Math.max(8, Math.min(100, (count / 120) * 100));
          return (
            <button
              type="button"
              className={activeDomain === item.domain ? "domain-card active" : "domain-card"}
              onClick={() => onDomainChange(item.domain)}
              key={item.domain}
              style={{ "--domain": domainColor(item.domain), "--bar": `${width}%` }}
            >
              <span className="domain-name">{item.domain}</span>
              <span className="domain-count">{formatNumber(count)}</span>
              <span className="domain-bar" />
              <span className="domain-gap">{item.missing_items || "待补资料"}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
