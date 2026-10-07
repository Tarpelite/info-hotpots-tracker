const CITY_RULES = [
  ["北京", 116.4074, 39.9042, ["北京", "海淀", "朝阳", "昌平", "石景山", "清华", "北大", "中关村", "科学院南路", "玉泉路", "学院路"]],
  ["上海", 121.4737, 31.2304, ["上海", "复旦", "上海交通", "同济", "杨浦", "浦东", "岳阳路"]],
  ["深圳", 114.0579, 22.5431, ["深圳", "南山", "深圳大学", "华为"]],
  ["广州", 113.2644, 23.1291, ["广州", "中山大学", "华南理工"]],
  ["香港", 114.1694, 22.3193, ["香港"]],
  ["合肥", 117.2272, 31.8206, ["合肥", "安徽"]],
  ["南京", 118.7969, 32.0603, ["南京", "江苏省南京"]],
  ["武汉", 114.3054, 30.5931, ["武汉", "洪山", "东湖", "华中科技", "武汉大学"]],
  ["西安", 108.9398, 34.3416, ["西安", "陕西"]],
  ["成都", 104.0665, 30.5728, ["成都", "四川大学"]],
  ["哈尔滨", 126.6424, 45.7567, ["哈尔滨", "哈工大"]],
  ["沈阳", 123.4315, 41.8057, ["沈阳"]],
  ["郑州", 113.6254, 34.7466, ["郑州", "河南"]],
  ["重庆", 106.5516, 29.563],
  ["东莞", 113.7518, 23.0207, ["东莞", "松山湖"]],
  ["大连", 121.6147, 38.914],
  ["厦门", 118.0894, 24.4798],
  ["杭州", 120.1551, 30.2741, ["杭州", "浙江大学"]],
  ["天津", 117.2009, 39.0842],
  ["长沙", 112.9388, 28.2282],
  ["长春", 125.3235, 43.8171],
  ["青岛", 120.3826, 36.0671, ["中国海洋大学"]],
  ["兰州", 103.8343, 36.0611],
  ["中国聚合", 104.1954, 35.8617, ["中国（", "中国大陆", "中国 ", "国内", "未注明"]]
];

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function normalizePerson(person) {
  return {
    id: person.id,
    name: person.name || "",
    title: person.title || "",
    role: person.role || "",
    profile_url: person.profile_url || person.profileUrl || "",
    verification_status: person.verification_status || person.verificationStatus || "",
    last_verified_at: person.last_verified_at || person.lastVerifiedAt || ""
  };
}

function normalizeEvidence(item, relation) {
  if (!item && !relation?.source_role) return null;

  return {
    evidence_id: item?.evidence_id || relation?.evidence_id || relation?.source_role,
    title: item?.title || item?.evidence_title || relation?.claim || relation?.source_role || "未命名证据",
    summary: item?.summary || "",
    source_url: item?.source_url || relation?.source_role || "",
    source_name: item?.source_name || item?.source_type || "",
    published_at: item?.published_at || "",
    captured_at: item?.captured_at || item?.fetched_at || "",
    verification_status: item?.verification_status || relation?.relation_status || "",
    relation_type: relation?.relation_type || "",
    claim: relation?.claim || "",
    reviewer: relation?.reviewer || "",
    reviewed_at: relation?.reviewed_at || ""
  };
}

function buildEvidenceLookup(evidence) {
  return new Map(evidence.map((item) => [item.evidence_id, normalizeEvidence(item)]));
}

function buildTeamEvidence(relations, evidenceLookup) {
  const grouped = new Map();

  for (const relation of relations) {
    if (!relation.team_id) continue;
    const normalized = normalizeEvidence(evidenceLookup.get(relation.evidence_id), relation);
    if (!normalized) continue;
    const rows = grouped.get(relation.team_id) ?? [];
    rows.push(normalized);
    grouped.set(relation.team_id, rows);
  }

  for (const [teamId, rows] of grouped.entries()) {
    grouped.set(
      teamId,
      rows
        .sort((a, b) => {
          const bTime = new Date(b.published_at || b.captured_at || 0).getTime();
          const aTime = new Date(a.published_at || a.captured_at || 0).getTime();
          return bTime - aTime;
        })
        .slice(0, 18)
    );
  }

  return grouped;
}

function normalizeTeam(team, rawTeam = {}, teamEvidence = []) {
  const sourceUrls = unique([
    ...(rawTeam.official_source_urls ?? []),
    ...(rawTeam.score_evidence_urls ?? []),
    ...(rawTeam.source_urls ?? []),
    ...(rawTeam.raw_record?.sourceUrls ?? []),
    ...(rawTeam.raw_record?.evidenceUrls ?? [])
  ]);
  const lookup = rawTeam.location_lookup ?? {};

  return {
    team_id: team.team_id,
    team_name: team.team_name || "未命名团队",
    institution: team.institution || team.institution_name || team.organization || "",
    country: team.country || "",
    city: team.city || "",
    location: {
      country: team.country || rawTeam.location_country || "",
      city: team.city || rawTeam.location_city || "",
      raw: rawTeam.location || rawTeam.raw_record?.location || "",
      display_name: lookup.display_name || "",
      lat: lookup.lat || "",
      lon: lookup.lon || "",
      source: lookup.source || "",
      source_url: lookup.source_url || ""
    },
    domain: team.domain || team.mapped_domain_name || "",
    subdomain: team.subdomain || team.mapped_subdomain_name || "",
    leader: team.leader || team.leader_name || "",
    leader_role: rawTeam.leader_role || rawTeam.raw_record?.leader?.role || "",
    direction: team.direction || team.research_directions?.join("；") || "",
    description: rawTeam.description || rawTeam.raw_record?.description || "",
    verification_status: team.verification_status || "candidate",
    project_verification_status: rawTeam.project_verification_status || "",
    candidate_status: rawTeam.candidate_status || "",
    attention: team.attention || "",
    attention_reason: team.attention_reason || rawTeam.attention_reason || "",
    mapping_status: rawTeam.mapping_status || "",
    mapping_method: rawTeam.mapping_method || "",
    mapping_confidence: rawTeam.mapping_confidence || "",
    mapping_reason: rawTeam.mapping_reason || "",
    evidence_count: rawTeam.evidence_count ?? teamEvidence.length,
    pending_materials: rawTeam.pending_materials ?? [],
    source_urls: sourceUrls,
    leaders: (rawTeam.leaders ?? rawTeam.raw_record?.leaders ?? []).slice(0, 6).map(normalizePerson),
    members: (rawTeam.members ?? rawTeam.raw_record?.members ?? []).slice(0, 10).map(normalizePerson),
    associated_evidence: teamEvidence,
    source_data_updated_at: rawTeam.source_data_updated_at || rawTeam.raw_record?.updatedAt || "",
    recent_update: rawTeam.recentUpdate || rawTeam.recent_update || ""
  };
}

function inferGeo(team, rawTeam) {
  const text = [
    team.city,
    team.country,
    team.institution,
    team.team_name,
    rawTeam?.location,
    rawTeam?.institution_name,
    rawTeam?.organization
  ]
    .filter(Boolean)
    .join(" ");

  for (const [place, lon, lat, keys] of CITY_RULES) {
    const needles = keys ?? [place];
    if (needles.some((key) => text.includes(key))) {
      return { place, lon, lat };
    }
  }

  return null;
}

function project(lon, lat) {
  return {
    x: ((lon + 180) / 360) * 100,
    y: ((90 - lat) / 180) * 100
  };
}

function buildMapPoints(teams, rawTeams) {
  const rawById = new Map(rawTeams.map((team) => [team.team_id, team]));
  const groups = new Map();

  for (const team of teams) {
    const geo = inferGeo(team, rawById.get(team.team_id));
    if (!geo || !team.domain) continue;
    const key = `${geo.place}::${team.domain}`;
    const current = groups.get(key) ?? {
      id: key,
      place: geo.place,
      domain: team.domain,
      lon: geo.lon,
      lat: geo.lat,
      count: 0,
      teams: []
    };
    current.count += 1;
    if (current.teams.length < 4) current.teams.push(team.team_name);
    groups.set(key, current);
  }

  return [...groups.values()]
    .map((point) => ({ ...point, ...project(point.lon, point.lat) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 72);
}

function buildLatestEvidence(evidence) {
  return [...evidence]
    .filter((item) => item.published_at && item.source_url)
    .sort((a, b) => new Date(b.published_at) - new Date(a.published_at))
    .slice(0, 8)
    .map((item) => ({
      evidence_id: item.evidence_id,
      title: item.title || item.evidence_title,
      summary: item.summary,
      source_url: item.source_url,
      source_name: item.source_name,
      published_at: item.published_at
    }));
}

function buildLatestNewsStats(evidence) {
  const dates = evidence
    .map((item) => item.published_at?.slice(0, 10))
    .filter(Boolean)
    .sort();
  const latestNewsDate = dates.at(-1) ?? "";
  const latestNewsEntries = latestNewsDate
    ? dates.filter((date) => date === latestNewsDate).length
    : 0;

  return { latestNewsDate, latestNewsEntries };
}

function hasPublicSnapshotShape(data) {
  return Boolean(data?.mapPoints && data?.latestEvidence && data?.teams);
}

export function normalizeSnapshot(data) {
  if (!data) return null;
  if (hasPublicSnapshotShape(data)) return data;

  const rawTeams = data.teams ?? [];
  const evidence = data.tables?.evidence ?? data.evidence ?? [];
  const relations = data.tables?.relations ?? data.relations ?? [];
  const evidenceLookup = buildEvidenceLookup(evidence);
  const teamEvidence = buildTeamEvidence(relations, evidenceLookup);
  const rawById = new Map(rawTeams.map((team) => [team.team_id, team]));
  const teams = (data.tables?.teams ?? data.teams ?? []).map((team) =>
    normalizeTeam(team, rawById.get(team.team_id), teamEvidence.get(team.team_id) ?? [])
  );
  const coverage = data.tables?.coverage ?? data.coverage ?? [];
  const latestNewsStats = buildLatestNewsStats(evidence);

  return {
    schemaVersion: "frontend-normalized-result.v1",
    generatedAt: new Date().toISOString(),
    metadata: {
      snapshotDate: data.metadata?.snapshot_date ?? "",
      importedAt: data.metadata?.imported_at ?? "",
      sourceUrl: data.metadata?.snapshot_file ?? "",
      sourceRefreshed: false,
      sourceDescription: "result/data.json"
    },
    stats: {
      teamCount: teams.length,
      originalTeamCount: rawTeams.length,
      domainCount: coverage.length,
      evidenceCount: evidence.length,
      latestNewsDate: latestNewsStats.latestNewsDate,
      latestNewsEntries: latestNewsStats.latestNewsEntries,
      latestNewsHighScore: 0
    },
    coverage,
    mapPoints: buildMapPoints(teams, rawTeams),
    latestEvidence: buildLatestEvidence(evidence),
    teams
  };
}
