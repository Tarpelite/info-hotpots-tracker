from __future__ import annotations

from dataclasses import dataclass
from typing import Any


LEGACY_DOMAIN_TO_CURRENT_NAME = {
    # 这些 ID 存在于快照文件中，但不在当前六领域树内。该映射仅作为候选机构
    # 归属的临时最优适配，不构成最终的科学判断。
    "domain_2d548948ff53477dba153c7dc6e6ee53": "生命科学与医学",
    "domain_1f41e1921c1c490697a747962d6c37fe": "化学与材料",
    "domain_9b9636ad749440149509588133273d63": "地球科学",
    "domain_0983c185ba224811b9acf41f0926dd3a": "通用 AI",
    "domain_115f1f20625c480e8341cf84fe3578b9": "科学通用底座",
}


DOMAIN_NAMES = (
    "科学通用底座",
    "通用 AI",
    "高能物理与量子科技",
    "化学与材料",
    "生命科学与医学",
    "地球科学",
)


SUBDOMAIN_KEYWORDS = {
    "科研数据与知识工程": (
        "科研数据",
        "知识工程",
        "知识图谱",
        "数据集",
        "数据工程",
        "数据库",
        "信息融合",
        "知识库",
    ),
    "科学计算与仿真": (
        "科学计算",
        "数值模拟",
        "仿真",
        "模拟",
        "数字孪生",
        "计算方法",
        "计算系统",
        "高性能计算",
    ),
    "科学基础模型": (
        "科学基础模型",
        "科学大模型",
        "ai4s",
        "人工智能赋能科学",
        "科学智能",
        "基础模型",
    ),
    "自主实验室与科研Agent": (
        "自主实验室",
        "科研agent",
        "科研 agent",
        "实验室机器人",
        "自动化实验",
        "智能实验室",
    ),
    "基础模型与多模态": (
        "大模型",
        "基础模型",
        "语言模型",
        "多模态",
        "视觉语言",
        "生成式人工智能",
        "生成式ai",
        "llm",
        "vlm",
    ),
    "推理与智能体": (
        "智能体",
        "agent",
        "推理",
        "自主决策",
        "规划",
        "强化学习",
    ),
    "AI系统与算力": (
        "人工智能芯片",
        "ai芯片",
        "算力",
        "芯片",
        "eda",
        "集成电路",
        "计算系统",
        "存储器",
        "处理器",
        "系统架构",
    ),
    "安全评测与治理": (
        "安全评测",
        "可信人工智能",
        "人工智能安全",
        "模型评测",
        "对齐",
        "治理",
        "隐私",
        "鲁棒",
    ),
    "高能粒子物理": (
        "高能物理",
        "粒子物理",
        "粒子",
        "对撞机",
        "标准模型",
    ),
    "核物理与加速器": (
        "核物理",
        "核科学",
        "加速器",
        "核能",
        "核技术",
    ),
    "量子计算与模拟": (
        "量子计算",
        "量子模拟",
        "量子算法",
        "量子芯片",
        "量子信息",
    ),
    "量子通信与精密测量": (
        "量子通信",
        "量子传感",
        "精密测量",
        "量子测量",
        "量子雷达",
    ),
    "计算化学与分子设计": (
        "计算化学",
        "分子设计",
        "分子模拟",
        "量子化学",
        "化学信息学",
    ),
    "材料发现与材料基因组": (
        "材料发现",
        "材料基因",
        "材料数据库",
        "高通量筛选",
        "材料信息学",
    ),
    "催化与能源材料": (
        "催化",
        "能源材料",
        "电池",
        "储能",
        "氢能",
        "燃料电池",
        "电催化",
        "光催化",
    ),
    "合金与结构材料": (
        "合金",
        "结构材料",
        "金属材料",
        "陶瓷",
        "复合材料",
        "增材制造",
        "材料加工",
        "先进材料",
    ),
    "超高温轻质金属材料合成": (
        "超高温",
        "轻质金属",
        "高温轻质",
        "钛合金",
        "镁合金",
        "铝合金",
    ),
    "蛋白质结构与设计": (
        "蛋白质",
        "蛋白结构",
        "结构生物学",
        "抗体设计",
        "蛋白设计",
    ),
    "药物研发": (
        "药物",
        "药理",
        "药物筛选",
        "药物研发",
        "免疫治疗",
        "肿瘤",
        "疾病",
        "疫苗",
    ),
    "基因组与单细胞": (
        "基因",
        "基因组",
        "单细胞",
        "组学",
        "rna",
        "dna",
        "遗传",
        "转录组",
    ),
    "医学影像与临床AI": (
        "医学影像",
        "临床",
        "医疗ai",
        "医学人工智能",
        "影像",
        "诊断",
        "医院",
    ),
    "合成生物与智能育种": (
        "合成生物",
        "生物制造",
        "代谢工程",
        "智能育种",
        "育种",
        "生物工程",
    ),
    "虚拟细胞": (
        "虚拟细胞",
        "细胞状态",
        "细胞扰动",
        "细胞表型",
        "细胞建模",
    ),
    "天气与气候": (
        "天气",
        "气候",
        "气象",
        "大气",
        "数值预报",
    ),
    "遥感与地理空间": (
        "遥感",
        "地理空间",
        "卫星",
        "空间信息",
        "地理信息",
        "gis",
        "测绘",
    ),
    "海洋与水文": (
        "海洋",
        "水文",
        "水资源",
        "河流",
        "海岸",
        "海洋环境",
    ),
    "地质资源与灾害": (
        "地质",
        "地球物理",
        "地震",
        "矿产",
        "地质灾害",
        "灾害",
        "岩石",
    ),
}


DOMAIN_KEYWORDS = {
    "科学通用底座": (
        "科研数据",
        "知识工程",
        "知识图谱",
        "科学计算",
        "数值模拟",
        "数字孪生",
        "自主实验室",
        "科研智能",
        "科学基础模型",
        "科研agent",
        "科学智能",
    ),
    "通用 AI": (
        "人工智能",
        "大模型",
        "基础模型",
        "多模态",
        "机器学习",
        "深度学习",
        "智能体",
        "推理",
        "芯片",
        "算力",
        "eda",
        "集成电路",
        "处理器",
        "存储器",
    ),
    "高能物理与量子科技": (
        "高能物理",
        "粒子物理",
        "量子",
        "核物理",
        "加速器",
        "精密测量",
        "粒子",
        "对撞机",
    ),
    "化学与材料": (
        "材料",
        "合金",
        "金属",
        "陶瓷",
        "复合材料",
        "催化",
        "能源材料",
        "电池",
        "储能",
        "化学",
        "分子",
        "增材制造",
    ),
    "生命科学与医学": (
        "生命科学",
        "生物",
        "医学",
        "药物",
        "细胞",
        "基因",
        "蛋白",
        "肿瘤",
        "免疫",
        "临床",
        "育种",
        "组学",
    ),
    "地球科学": (
        "地球科学",
        "遥感",
        "地理空间",
        "气候",
        "天气",
        "气象",
        "海洋",
        "水文",
        "地质",
        "灾害",
        "卫星",
        "空间信息",
    ),
}


@dataclass(frozen=True)
class Taxonomy:
    domains_by_id: dict[str, dict[str, Any]]
    subdomains_by_id: dict[str, dict[str, Any]]
    subdomain_domain_id: dict[str, str]
    domain_id_by_name: dict[str, str]
    subdomain_id_by_name: dict[str, str]

    @classmethod
    def from_domain_rows(cls, domain_rows: list[dict[str, Any]]) -> "Taxonomy":
        domains_by_id: dict[str, dict[str, Any]] = {}
        subdomains_by_id: dict[str, dict[str, Any]] = {}
        subdomain_domain_id: dict[str, str] = {}
        domain_id_by_name: dict[str, str] = {}
        subdomain_id_by_name: dict[str, str] = {}
        for row in domain_rows:
            domain_id = row["domain_id"]
            subdomain_id = row["subdomain_id"]
            domains_by_id[domain_id] = {
                "id": domain_id,
                "name": row["domain_name"],
                "description": row["domain_description"],
            }
            subdomains_by_id[subdomain_id] = {
                "id": subdomain_id,
                "name": row["subdomain_name"],
                "description": row["subdomain_description"],
            }
            subdomain_domain_id[subdomain_id] = domain_id
            domain_id_by_name[row["domain_name"]] = domain_id
            subdomain_id_by_name[row["subdomain_name"]] = subdomain_id
        return cls(
            domains_by_id=domains_by_id,
            subdomains_by_id=subdomains_by_id,
            subdomain_domain_id=subdomain_domain_id,
            domain_id_by_name=domain_id_by_name,
            subdomain_id_by_name=subdomain_id_by_name,
        )

    def domain_id_for_name(self, name: str) -> str:
        return self.domain_id_by_name.get(name, "")

    def subdomain_id_for_name(self, name: str) -> str:
        return self.subdomain_id_by_name.get(name, "")


def searchable_team_text(team_row: dict[str, Any]) -> str:
    raw = team_row.get("raw_record", {})
    directions = raw.get("researchDirections", raw.get("research_directions", []))
    if not isinstance(directions, list):
        directions = [directions]
    values = [
        team_row.get("team_name", ""),
        team_row.get("organization", ""),
        team_row.get("description", ""),
        team_row.get("location", ""),
        raw.get("focus", ""),
        raw.get("coreDirection", raw.get("core_direction", "")),
        *directions,
    ]
    return " ".join(str(value or "").lower() for value in values)


def score_keywords(text: str, keywords: tuple[str, ...]) -> tuple[int, list[str]]:
    hits = [keyword for keyword in keywords if keyword.lower() in text]
    return len(hits), hits


def infer_domain_name(text: str) -> tuple[str, int, list[str]]:
    scores: list[tuple[int, str, list[str]]] = []
    for domain_name in DOMAIN_NAMES:
        score, hits = score_keywords(text, DOMAIN_KEYWORDS.get(domain_name, ()))
        scores.append((score, domain_name, hits))
    scores.sort(reverse=True, key=lambda item: item[0])
    best_score, best_name, best_hits = scores[0]
    second_score = scores[1][0] if len(scores) > 1 else 0
    if best_score == 0:
        return "", 0, []
    confidence_score = best_score if best_score > second_score else max(1, best_score - 1)
    return best_name, confidence_score, best_hits


def infer_subdomain_name(domain_name: str, text: str) -> tuple[str, int, list[str]]:
    domain_id = domain_name
    candidates = [
        (name, keywords)
        for name, keywords in SUBDOMAIN_KEYWORDS.items()
        if name in SUBDOMAIN_KEYWORDS
    ]
    domain_groups = {
        "科学通用底座": {
            "科研数据与知识工程",
            "科学计算与仿真",
            "科学基础模型",
            "自主实验室与科研Agent",
        },
        "通用 AI": {
            "基础模型与多模态",
            "推理与智能体",
            "AI系统与算力",
            "安全评测与治理",
        },
        "高能物理与量子科技": {
            "高能粒子物理",
            "核物理与加速器",
            "量子计算与模拟",
            "量子通信与精密测量",
        },
        "化学与材料": {
            "计算化学与分子设计",
            "材料发现与材料基因组",
            "催化与能源材料",
            "合金与结构材料",
            "超高温轻质金属材料合成",
        },
        "生命科学与医学": {
            "蛋白质结构与设计",
            "药物研发",
            "基因组与单细胞",
            "医学影像与临床AI",
            "合成生物与智能育种",
            "虚拟细胞",
        },
        "地球科学": {
            "天气与气候",
            "遥感与地理空间",
            "海洋与水文",
            "地质资源与灾害",
        },
    }
    allowed = domain_groups.get(domain_id, set())
    scored: list[tuple[int, str, list[str]]] = []
    for name, keywords in candidates:
        if name not in allowed:
            continue
        score, hits = score_keywords(text, keywords)
        if score:
            scored.append((score, name, hits))
    scored.sort(reverse=True, key=lambda item: item[0])
    if not scored:
        return "", 0, []
    return scored[0][1], scored[0][0], scored[0][2]
