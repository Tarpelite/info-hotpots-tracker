import { AlertCircle, Radio } from "lucide-react";
import { ComposableMap, Geographies, Geography, Marker as GeoMarker } from "react-simple-maps";
import worldCountries from "world-atlas/countries-110m.json";
import AskBar from "./AskBar.jsx";
import { domainColor } from "../data/domain.js";
import { formatDate, formatNumber } from "../utils/format.js";

const MAP_WIDTH = 1000;
const MAP_HEIGHT = 420;
const LAND_DOTS = Array.from({ length: Math.floor(MAP_WIDTH / 10) * Math.floor(MAP_HEIGHT / 10) }, (_, index) => {
  const columns = Math.floor(MAP_WIDTH / 10);
  return {
    x: (index % columns) * 10 + 3,
    y: Math.floor(index / columns) * 10 + 3
  };
});

function TeamMarker({ point }) {
  const radius = Math.max(4, Math.min(13, 3.5 + Math.sqrt(point.count) * 1.4));
  return (
    <GeoMarker coordinates={[Number(point.lon), Number(point.lat)]}>
      <g className="geo-marker" style={{ color: domainColor(point.domain) }}>
        <title>{`${point.place}｜${point.domain}｜${point.count} 支团队`}</title>
        <circle className="geo-marker-halo" r={radius + 3.5} />
        <circle className="geo-marker-core" r={radius} />
        <text textAnchor="middle" y="3">
          {point.count}
        </text>
      </g>
    </GeoMarker>
  );
}

function RealWorldMap({ points }) {
  return (
    <ComposableMap
      className="world-map"
      width={MAP_WIDTH}
      height={MAP_HEIGHT}
      projection="geoNaturalEarth1"
      projectionConfig={{ scale: 168, center: [0, 4] }}
      role="img"
      aria-label="真实国家边界世界地图"
    >
      <Geographies geography={worldCountries}>
        {({ geographies }) => (
          <>
            <defs>
              <clipPath id="land-dot-clip" clipPathUnits="userSpaceOnUse">
                {geographies.map((geo) => (
                  <Geography
                    className="land-clip-geography"
                    geography={geo}
                    key={`${geo.rsmKey}-clip`}
                  />
                ))}
              </clipPath>
            </defs>
            <g className="land-dot-grid" clipPath="url(#land-dot-clip)">
              {LAND_DOTS.map((dot) => (
                <circle className="land-dot" cx={dot.x} cy={dot.y} r="1.25" key={`${dot.x}-${dot.y}`} />
              ))}
            </g>
            <g className="country-layer">
              {geographies.map((geo) => (
                <Geography className="map-country" geography={geo} key={geo.rsmKey} tabIndex={-1} />
              ))}
            </g>
            {points.map((point) => (
              <TeamMarker point={point} key={point.id} />
            ))}
          </>
        )}
      </Geographies>
    </ComposableMap>
  );
}

export default function Map({ snapshot, stats, loading, error, activeDomain, onDomainChange, showAsk = true }) {
  const coverage = snapshot?.coverage ?? [];
  const points = (snapshot?.mapPoints ?? []).filter(
    (point) => activeDomain === "全部" || point.domain === activeDomain
  );
  const shownPoints = points.slice(0, 44);

  return (
    <section className="hero-map" id="战略地图">
      <div className="map-layer">
        <RealWorldMap points={shownPoints} />
      </div>

      <div className="hero-copy">
        <p className="dateline">
          {formatDate(stats.snapshotDate)} 快照更新。{formatNumber(stats.teamCount)} 支团队、
          {formatNumber(stats.evidenceCount)} 条证据、{formatNumber(stats.domainCount)} 个领域进入公开站。
        </p>
        <div className="hero-status">
          <Radio size={15} aria-hidden="true" />
          最近采集 {formatDate(stats.latestNewsDate)}
          {stats.latestNewsHighScore ? `，${formatNumber(stats.latestNewsHighScore)} 条高相关` : ""}
        </div>
      </div>

      {loading && <div className="load-banner">正在读取公开数据...</div>}
      {error && (
        <div className="load-banner error">
          <AlertCircle size={16} aria-hidden="true" />
          数据接口暂不可用
        </div>
      )}

      {showAsk && <AskBar coverage={coverage} />}

      <div className="map-legend" aria-label="领域图例">
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
      <p className="map-note">圆点大小是团队数或证据数，脉冲是今天有新证据。</p>
    </section>
  );
}
