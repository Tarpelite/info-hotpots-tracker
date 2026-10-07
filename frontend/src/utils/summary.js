export function buildSnapshotStats(snapshot) {
  if (!snapshot) {
    return {
      teamCount: 0,
      evidenceCount: 0,
      domainCount: 0,
      latestNewsDate: "",
      latestNewsEntries: 0,
      latestNewsHighScore: 0,
      snapshotDate: ""
    };
  }

  const stats = snapshot.stats ?? {};
  return {
    teamCount: stats.teamCount ?? snapshot.teams?.length ?? 0,
    evidenceCount: stats.evidenceCount ?? 0,
    domainCount: stats.domainCount ?? snapshot.coverage?.length ?? 0,
    latestNewsDate: stats.latestNewsDate ?? "",
    latestNewsEntries: stats.latestNewsEntries ?? 0,
    latestNewsHighScore: stats.latestNewsHighScore ?? 0,
    snapshotDate: snapshot.metadata?.snapshotDate ?? snapshot.metadata?.snapshot_date ?? ""
  };
}

export function getTopDomains(coverage, limit = 3) {
  return [...coverage]
    .sort((a, b) => Number(b.candidate_count || 0) - Number(a.candidate_count || 0))
    .slice(0, limit);
}
