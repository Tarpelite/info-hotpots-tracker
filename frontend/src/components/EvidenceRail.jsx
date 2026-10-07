import { ExternalLink } from "lucide-react";
import { formatDateTime, formatNumber } from "../utils/format.js";

export default function EvidenceRail({ evidence, stats }) {
  return (
    <section className="section-band evidence-band" id="热点">
      <div className="section-head">
        <div>
          <span className="eyebrow">热点</span>
          <h2>最近进入证据库的线索</h2>
        </div>
        <p>{formatNumber(stats.evidenceCount)} 条证据已入库</p>
      </div>
      <div className="evidence-list">
        {evidence.map((item) => (
          <a className="evidence-item" href={item.source_url} target="_blank" rel="noreferrer" key={item.evidence_id}>
            <span className="evidence-time">{formatDateTime(item.published_at)}</span>
            <strong>{item.summary || item.title}</strong>
            <span className="evidence-source">
              {item.source_name || "公开来源"}
              <ExternalLink size={13} aria-hidden="true" />
            </span>
          </a>
        ))}
      </div>
    </section>
  );
}
