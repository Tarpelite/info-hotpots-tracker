# AMiner 开放平台数据 API 接入指南（README）

> 面向 **AMiner 开放平台**（[https://www.aminer.cn/open/docs](https://www.aminer.cn/open/docs)，镜像地址 [https://open.aminer.cn/open/docs](https://open.aminer.cn/open/docs)）的接口调用说明。
> 平台提供学者、论文、机构、期刊/会议、专利等全维度学术数据，共 **28 个开放 API**。

---

## 一、接入准备

| 项目 | 说明 |
|---|---|
| 官方文档 | https://open.aminer.cn/open/docs （每个接口均可在文档站查看独立页面） |
| 控制台（生成 Token） | https://open.aminer.cn/open/board?tab=control |
| 接口网关（Base URL） | `https://datacenter.aminer.cn/gateway/open_platform` |

1. 登录控制台，进入 **API 控制台**，点击"一键生成 Token"（Token 在有效期内可重复使用）。
2. 将 Token 配置到环境变量，避免明文写入代码：

```bash
export AMINER_API_KEY="<YOUR_TOKEN>"
```

> ⚠️ 注意：免费接口也必须要携带 Token。请勿打印、记录或提交 Token 明文。

---

## 二、通用调用规范

### 2.1 请求地址

```
https://datacenter.aminer.cn/gateway/open_platform + <接口路径>
示例：https://datacenter.aminer.cn/gateway/open_platform/api/paper/search
```

### 2.2 请求方式

- **GET**：参数以 **Query String** 形式拼接在 URL 后（如 `?page=1&size=5&title=BERT`）。
- **POST**：参数以 **JSON 字符串** 形式放在 Request Body 中。

### 2.3 HTTP Header

| Header | 是否必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | 值为控制台生成/获取的 Token，**直接拼接、无需加 `Bearer` 前缀** |
| `Content-Type` | POST 必填 | `application/json;charset=utf-8` |
| `X-Platform` | 否 | 调用来源标识（如 `openclaw`、`claude-code` 等），用于平台统计 |

### 2.4 通用响应结构（HTTP 返回 JSON）

所有接口返回统一的包裹结构：

```json
{
  "code": 200,          // 返回码，200 表示成功
  "success": true,      // 是否成功
  "msg": "",            // 错误/提示信息
  "data": [],           // 业务数据（结构因接口而异，见各接口说明）
  "log_id": "30dFKtSXCSRM9mGqpTmvZIxmBub"  // 请求日志 ID，排查问题时提供给官方
}
```

### 2.5 通用错误码

| 代码 | 说明 |
|---|---|
| 40001 | 参数错误 |
| 40301 | 权限禁用 |
| 40302 | Token 过期 |
| 40306 | 访问频率过快 |
| 40307 | 无效的 API Key |
| 40308 | 无效的 Token，请检查过期时间或其他数据 |
| 50001 | 服务出错 |

### 2.6 调用建议

- 建议设置超时（如 30s），并对 `408 / 429 / 500 / 502 / 503 / 504` 做指数退避重试（1s → 2s → 4s），其余 4xx 错误直接返回不重试。
- 优先使用免费接口定位实体 ID（`paper/search`、`person/search`、`venue/search`、`organization/search`、`patent/search`、`paper/info`），再按需调用计费详情接口，控制成本。
- 批量接口注意上限，如 `paper/info` 单次最多 100 个 ID。

---

## 三、接口总览（28 个 API）

Base 路径均为 `datacenter.aminer.cn/gateway/open_platform`。

| # | 接口名称 | 方法 | 价格 | 路径 |
|---|---|---|---|---|
| 1 | 论文问答搜索 | POST | ¥0.05/次 | `/api/paper/qa/search` |
| 2 | 学者搜索 | POST | 免费 | `/api/person/search` |
| 3 | 论文搜索 | GET | 免费 | `/api/paper/search` |
| 4 | 论文搜索 Pro | GET | ¥0.01/次 | `/api/paper/search/pro` |
| 5 | 专利搜索 | POST | 免费 | `/api/patent/search` |
| 6 | 机构搜索 | POST | 免费 | `/api/organization/search` |
| 7 | 期刊搜索 | POST | 免费 | `/api/venue/search` |
| 8 | 学者详情 | GET | ¥1.00/次 | `/api/person/detail` |
| 9 | 学者项目 | GET | ¥3.00/次 | `/api/project/person/v3/open` |
| 10 | 学者论文 | GET | ¥1.50/次 | `/api/person/paper/relation` |
| 11 | 学者专利 | GET | ¥1.50/次 | `/api/person/patent/relation` |
| 12 | 学者画像 | GET | ¥0.50/次 | `/api/person/figure` |
| 13 | 论文信息（批量） | POST | 免费 | `/api/paper/info` |
| 14 | 论文详情 | GET | ¥0.01/次 | `/api/paper/detail` |
| 15 | 论文引用 | GET | ¥0.10/次 | `/api/paper/relation` |
| 16 | 专利信息 | GET | 免费 | `/api/patent/info` |
| 17 | 专利详情 | GET | ¥0.01/次 | `/api/patent/detail` |
| 18 | 机构详情 | POST | ¥0.01/次 | `/api/organization/detail` |
| 19 | 机构专利 | GET | ¥0.10/次 | `/api/organization/patent/relation` |
| 20 | 机构学者 | GET | ¥0.50/次 | `/api/organization/person/relation` |
| 21 | 机构论文 | GET | ¥0.10/次 | `/api/organization/paper/relation` |
| 22 | 期刊详情 | POST | ¥0.20/次 | `/api/venue/detail` |
| 23 | 期刊论文 | POST | ¥0.10/次 | `/api/venue/paper/relation` |
| 24 | 机构消歧 | POST | ¥0.01/次 | `/api/organization/na` |
| 25 | 机构消歧 Pro | POST | ¥0.05/次 | `/api/organization/na/pro` |
| 26 | 按期刊组合搜索论文 | GET | ¥0.30/次 | `/api/paper/list/by/search/venue` |
| 27 | 按关键词批量查询论文 | GET | ¥0.10/次 | `/api/paper/list/citation/by/keywords` |
| 28 | 按年份/期刊查询论文详情 | GET | ¥0.20/次 | `/api/paper/platform/allpubs/more/detail/by/ts/org/venue` |

---

## 四、核心接口详细说明

### 4.1 论文搜索 `GET /api/paper/search`（免费）

- **请求地址**：`https://datacenter.aminer.cn/gateway/open_platform/api/paper/search`
- **请求方式**：GET
- **HTTP Header**：`Authorization`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| title | string | 是 | 论文标题（模糊匹配） |
| page | int | 否 | 页码，默认 1 |
| size | int | 否 | 每页条数 |

**请求示例**：

```bash
curl -X GET "https://datacenter.aminer.cn/gateway/open_platform/api/paper/search?page=1&size=5&title=BERT" \
  -H "Authorization: ${AMINER_API_KEY}"
```

**返回 data**：论文基础信息数组，字段含 `id`（论文 ID）、`title`、`title_zh`（中文标题）、`doi`、`authors`、`venue`、`year`、`n_citation`（被引数）等。

---

### 4.2 论文搜索 Pro `GET /api/paper/search/pro`（¥0.01/次）

- **请求地址**：`.../api/paper/search/pro`
- **请求方式**：GET
- **HTTP Header**：`Authorization`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page | int | 否 | 页码 |
| size | int | 否 | 每页条数（每页最多 100 条） |
| title | string | 否 | 标题 |
| keyword | string | 否 | 关键词 |
| abstract | string | 否 | 摘要 |
| author | string | 否 | 作者 |
| org | string | 否 | 机构 |
| venue | string | 否 | 期刊/会议 |
| order | string | 否 | 排序：`year` 或 `n_citation`（降序），不传为默认排序 |

**请求示例**：

```bash
curl -X GET "https://datacenter.aminer.cn/gateway/open_platform/api/paper/search/pro?size=5&keyword=transformer&order=n_citation" \
  -H "Authorization: ${AMINER_API_KEY}"
```

**返回 data**：论文数组，示例字段：

```json
{
  "code": 200, "success": true, "msg": "", "log_id": "...",
  "data": [
    { "id": "...", "title": "...", "title_zh": "...", "doi": "..." }
  ]
}
```

---

### 4.3 论文问答搜索 `POST /api/paper/qa/search`（¥0.05/次）

- **请求地址**：`.../api/paper/qa/search`
- **请求方式**：POST
- **HTTP Header**：`Authorization`、`Content-Type: application/json;charset=utf-8`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| query | string | 二选一 | 自然语言问句（与 topic_* 互斥） |
| topic_high | string | 二选一 | 高权重主题词，二维 JSON 数组字符串，如 `"[[\"人工智能\",\"AI\"]]"` |
| topic_middle | string | 否 | 中权重主题词（格式同上） |
| topic_low | string | 否 | 低权重主题词（格式同上） |
| use_topic | bool | topic 模式必填 | 是否启用主题词模式 |
| size | int | 否 | 返回条数 |
| year / year_from / year_to | int | 否 | 年份过滤 |
| citation_sort | bool | 否 | 是否按引用量排序 |

**请求示例**：

```bash
curl -X POST "https://datacenter.aminer.cn/gateway/open_platform/api/paper/qa/search" \
  -H "Content-Type: application/json;charset=utf-8" \
  -H "Authorization: ${AMINER_API_KEY}" \
  -d '{"query":"生首乌和何首乌与肝损伤的关系","topic_high":"[[\"生首乌\"]]","use_topic":true}'
```

**返回 data**：`[{ "id": "5c7cb7514895d9cbc648b492" }, ...]`（论文 ID 列表），配合 `paper/info` 获取完整信息。

---

### 4.4 学者搜索 `POST /api/person/search`（免费）

- **请求地址**：`.../api/person/search`
- **请求方式**：POST
- **HTTP Header**：`Authorization`、`Content-Type: application/json;charset=utf-8`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 是 | 学者姓名 |
| size | int | 否 | 返回条数 |
| page | int | 否 | 页码 |
| org / orgs | array | 否 | 机构过滤 |

**请求示例**：

```bash
curl -X POST "https://datacenter.aminer.cn/gateway/open_platform/api/person/search" \
  -H "Content-Type: application/json;charset=utf-8" \
  -H "Authorization: ${AMINER_API_KEY}" \
  -d '{"name":"Andrew Ng","size":5}'
```

**返回 data**：学者列表，字段含 `id`（学者 ID）、`name`、`name_zh`、`affiliation`（机构）、`position`（职称）、`interests`（研究兴趣）、`h_index`、`n_citation`、`n_pubs` 等。

---

### 4.5 论文信息（批量）`POST /api/paper/info`（免费）

- **请求地址**：`.../api/paper/info`
- **请求方式**：POST
- **HTTP Header**：`Authorization`、`Content-Type: application/json;charset=utf-8`

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | array | 是 | 论文 ID 数组，单次最多 100 个 |

**请求示例**：

```bash
curl -X POST "https://datacenter.aminer.cn/gateway/open_platform/api/paper/info" \
  -H "Content-Type: application/json;charset=utf-8" \
  -H "Authorization: ${AMINER_API_KEY}" \
  -d '{"ids":["<PAPER_ID_1>","<PAPER_ID_2>"]}'
```

**返回 data**：论文基础信息数组（title、authors、venue、year、abstract、doi、n_citation 等），适合搜索/问答接口返回 ID 后的批量补全。

---

### 4.6 论文详情 `GET /api/paper/detail`（¥0.01/次）

- **请求地址**：`.../api/paper/detail`
- **请求方式**：GET（单篇详情，注意与 `paper/info` 的批量 `ids` 区分，本篇用单数参数）

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| paper_id | string | 是 | 论文 ID |

**返回 data**：单篇论文完整详情（完整元数据、摘要、作者及单位、期刊卷期页、DOI、引用数等）。

---

### 4.7 论文引用 `GET /api/paper/relation`（¥0.10/次）

- **请求地址**：`.../api/paper/relation`
- **请求方式**：GET

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 论文 ID |

**请求示例**：

```bash
curl -X GET "https://datacenter.aminer.cn/gateway/open_platform/api/paper/relation?id=64d4995c3fda6d7f06cee437" \
  -H "Authorization: ${AMINER_API_KEY}"
```

**返回 data**：

| 参数 | 类型 | 说明 |
|---|---|---|
| _id | string | 论文 ID |
| title | string | 标题 |
| n_citation | int | 被引用数量 |
| cited | array | 引用其他论文的基本信息（无引用时为 null） |

```json
{
  "code": 200, "success": true, "msg": "",
  "data": [{
    "_id": "64d4995c3fda6d7f06cee437",
    "title": "Heterogeneous Graph Attention Networks for Semi-supervised Short Text Classification",
    "n_citation": 187,
    "cited": null
  }],
  "log_id": "30dFKtSXCSRM9mGqpTmvZIxmBub"
}
```

---

### 4.8 机构搜索 `POST /api/organization/search`（免费）

- **请求地址**：`.../api/organization/search`
- **请求方式**：POST

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| orgs | array | 是 | 机构名称数组 |

```bash
curl -X POST ".../api/organization/search" \
  -H "Content-Type: application/json;charset=utf-8" \
  -H "Authorization: ${AMINER_API_KEY}" \
  -d '{"orgs":["MIT CSAIL","清华大学"]}'
```

**返回 data**：机构列表，含 `id`（机构 ID）、`name`（及别名/缩写）、`type`、`image`（标识）等。

---

### 4.9 机构详情 `POST /api/organization/detail`（¥0.01/次）

- **请求方式**：POST
- **请求参数**：`ids`（array，必填，机构 ID 数组）
- **返回 data**：机构详情（名称、别名、缩写、类型、Logo 等）。

---

### 4.10 期刊搜索 `POST /api/venue/search`（免费）

- **请求地址**：`.../api/venue/search`
- **请求方式**：POST

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 是 | 期刊/会议名称（支持缩写，如 `tkde`） |

```bash
curl -X POST ".../api/venue/search" \
  -H "Content-Type: application/json;charset=utf-8" \
  -H "Authorization: ${AMINER_API_KEY}" \
  -d '{"name":"tkde"}'
```

**返回 data**：期刊/会议列表，含 `id`、`name`、`type`（期刊/会议）等。

---

### 4.11 期刊论文 `POST /api/venue/paper/relation`（¥0.10/次）

- **请求地址**：`.../api/venue/paper/relation`
- **请求方式**：POST

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 期刊 ID |
| offset | int | 否 | 起始位置（偏移量） |
| limit | int | 否 | 条数 |
| year | int | 否 | 年份过滤 |

```bash
curl -X POST ".../api/venue/paper/relation" \
  -H "Content-Type: application/json;charset=utf-8" \
  -H "Authorization: ${AMINER_API_KEY}" \
  -d '{"id":"5ea1d5ebedb6e7d53c0101f4","offset":0,"limit":20,"year":2024}'
```

**返回 data**：`[{ "id": "...", "title": "...", "year": "..." }, ...]`，可再经 `paper/info` 补全字段。

---

### 4.12 专利搜索 `POST /api/patent/search`（免费）

- **请求地址**：`.../api/patent/search`
- **请求方式**：POST

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| query | string | 是 | 检索词（技术主题/关键词） |
| page | int | 否 | 页码（从 0 开始） |
| size | int | 否 | 每页条数 |

```bash
curl -X POST ".../api/patent/search" \
  -H "Content-Type: application/json;charset=utf-8" \
  -H "Authorization: ${AMINER_API_KEY}" \
  -d '{"query":"quantum computing chip","page":0,"size":10}'
```

**返回 data**：专利列表，含 `id`、标题、申请人、发明人、申请/公开日期、摘要等。

---

### 4.13 按期刊组合搜索论文 `GET /api/paper/list/by/search/venue`（¥0.30/次）

- **请求方式**：GET
- **说明**：`keyword`、`venue`、`author` 三者选其一。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword / venue / author | string | 三选一 | 关键词 / 期刊名称 / 作者名称 |
| page | int | 是 | 页码 |
| size | int | 是 | 条数 |
| order | string | 否 | 不传为综合排序，可传 `year`、`n_citation` |

**返回 data**：字段更完整的论文数组（`id`、`title`、`authors`、`doi`、`keywords`、`abstract_zh` 等），适合直接用于分析/报告。

---

### 4.14 按关键词批量查询论文 `GET /api/paper/list/citation/by/keywords`（¥0.10/次）

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keywords | array | 是 | 关键词数组，如 `["人工智能","机器学习"]` |
| page | int | 是 | 页码 |
| size | int | 是 | 条数 |

---

### 4.15 其余计费接口（参数请以官方文档为准）

| 接口 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 学者详情 | GET | `/api/person/detail` | 学者完整档案（教育/工作经历、代表作等） |
| 学者画像 | GET | `/api/person/figure` | 学者画像数据 |
| 学者论文 | GET | `/api/person/paper/relation` | 学者全部论文关系列表 |
| 学者专利 | GET | `/api/person/patent/relation` | 学者专利关系列表 |
| 学者项目 | GET | `/api/project/person/v3/open` | 学者科研项目 |
| 专利信息 | GET | `/api/patent/info` | 专利批量基础信息 |
| 专利详情 | GET | `/api/patent/detail` | 单篇专利详情 |
| 机构论文 | GET | `/api/organization/paper/relation` | 机构论文列表 |
| 机构学者 | GET | `/api/organization/person/relation` | 机构学者列表 |
| 机构专利 | GET | `/api/organization/patent/relation` | 机构专利列表 |
| 期刊详情 | POST | `/api/venue/detail` | 期刊/会议详情 |
| 机构消歧 | POST | `/api/organization/na` | 机构名称消歧（返回标准机构） |
| 机构消歧 Pro | POST | `/api/organization/na/pro` | 高精度机构消歧 |
| 按年份/期刊查论文详情 | GET | `/api/paper/platform/allpubs/more/detail/by/ts/org/venue` | 年份+期刊维度批量详情 |

---


## 参考资料

- 官方文档：https://open.aminer.cn/open/docs
- 控制台：https://open.aminer.cn/open/board?tab=control
- 官方 Skill 仓库（含全部 28 个接口的完整参数目录 `references/api-catalog.md`）：https://github.com/AMinerOrg/aminer-open-skill