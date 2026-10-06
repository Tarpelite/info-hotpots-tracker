科技战略情报系统：启动数据包

一、这包里有什么

团队快照：344条原始候选，6个领域、27个子领域。
news-data：完整保留200个文件，其中49份采集JSON共有30,842条记录，日期为2026年8月12日至9月29日。
另外附团队CSV清单、领域定义、新闻按日索引和文件校验清单。

二、团队快照在哪里，怎样读

团队快照/team_snapshot_20261005.json是原系统返回的完整JSON。
读取data.teams得到团队，读取data.domains得到领域树。原字段、来源链接、成员、分数与状态均保留。
团队快照/teams_原始候选清单.csv是同一批344条记录的平铺视图，便于打开查阅和导入。
团队快照/domains_领域定义.csv给出6个领域、27个子领域的原始ID、名称和说明。

本次导出时间：2026-10-05T20:01:54+08:00。
这些记录原本更新于2026年9月23日至9月29日；原系统本次没有刷新数据。
10月1日临时保存的原快照文件已不在，本包是从同一数据接口重新导出的已保存资料，不能描述为10月5日新增的团队结果。
344是原系统完整候选数。前一版原型用过332条筛选后的记录，两个数字都不是本次已核实数量。
原系统的verified、graph_verified、分数和国内标记只是来源字段，需按开发说明书重新检查，不能直接作为我们的验收结果。

三、news-data在哪里，怎样读

news-data文件夹与桌面AI4S-Daily-done/news-data的现有内容一致。
采集数据读取fetch-*.json顶层的entries，每条通常含title、link、published、source、content、tags、score、summary、fetched_at。
日报、周报和月报为push-*.md；即时推送为notify-*.md；专项相关性材料为relevance-*.md。
fetch-2026-0809.zip是目录中原有的历史压缩备份，已原样保留；不要把它和散文件一起重复计算。
pushed-links.json、search-state.json是原运行状态记录；采集条目以fetch-*.json为准。

news-data_按日索引.csv列出49份JSON的日期、记录数和原score≥70记录数。原score只是筛选字段，不表示事实已经核实。

四、先怎么开工

1. 读团队和领域JSON，保留原team_id、domain_id、subdomain_id。
2. 读fetch-*.json，把title映射为证据标题，link映射为来源链接，published映射为发布时间，source映射为来源名；保留原文和原始记录。
3. 按开发说明书核实机构归属、具体团队与代表成果，再建立团队和证据之间的关系。完整原始输入保留，清洗结果另存。
4. 生成7号需要的团队、证据、关系和覆盖表。所有数字从同一版清洗数据计算。

最短读取示例：

import json
from pathlib import Path
root = Path("20261005科技战略情报启动数据_v1")
snapshot = json.loads((root / "团队快照" / "team_snapshot_20261005.json").read_text(encoding="utf-8"))
teams = snapshot["data"]["teams"]
domains = snapshot["data"]["domains"]
entries = []
for path in sorted((root / "news-data").glob("fetch-*.json")):
    entries.extend(json.loads(path.read_text(encoding="utf-8"))["entries"])
print(len(teams), len(domains), len(entries))
# 应输出：344 6 30842

五、来源与完整性

原团队接口和实际导出时间记录在数据来源与统计.json。
文件清单_SHA256.csv列出本包各数据文件和说明的大小、校验值；清单自身不列入自身校验。
本包仅含本次需要的团队快照与news-data及其读取说明，未包含源码配置或API密钥文件。
