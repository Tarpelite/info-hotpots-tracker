export const DOMAIN_COLORS = {
  科学通用底座: "#2b6cb0",
  "通用 AI": "#7157b8",
  高能物理与量子科技: "#c07b2d",
  化学与材料: "#20885f",
  生命科学与医学: "#bf4f6c",
  地球科学: "#2d7d8f"
};

export const STATUS_LABELS = {
  verified: "已核实",
  candidate: "待核实",
  rejected: "已剔除",
  collected: "已采集",
  legacy_unverified: "待复核"
};

export const DOMAIN_ORDER = [
  "科学通用底座",
  "通用 AI",
  "高能物理与量子科技",
  "化学与材料",
  "生命科学与医学",
  "地球科学"
];

export function domainColor(domain) {
  return DOMAIN_COLORS[domain] ?? "#5d6b7a";
}

export function statusLabel(status) {
  return STATUS_LABELS[status] ?? STATUS_LABELS.candidate;
}
