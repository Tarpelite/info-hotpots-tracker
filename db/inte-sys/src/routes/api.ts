import { errorResponse, json } from "../lib/http";
import { selectFirst } from "../lib/query";
import { routeAuthors } from "./authors";
import { routeOrganizations } from "./organizations";
import { routePapers } from "./papers";

const API_DESCRIPTION = {
	name: "inte-sys query API",
	version: "1.0.0",
	endpoints: {
		"GET /api/papers": "分页查询论文，支持 id、q、year、yearFrom、yearTo、venue、doi、issn、sort、order、limit、offset",
		"GET /api/papers/:id": "查询论文详情并返回 author_rows",
		"GET /api/papers/:id/authors": "查询论文作者",
		"GET /api/organizations": "分页查询机构，支持 id、q、name、type、location、limit、offset",
		"GET /api/organizations/:id": "查询机构详情",
		"GET /api/paper-authors": "分页查询 paper_author 关系，支持 paperid、q、name、name_zh、org、org_zh",
		"GET /api/health": "检查 Worker 到 D1 的连接",
	},
};

export async function routeApi(request: Request, env: Env): Promise<Response> {
	const url = new URL(request.url);
	const { pathname, searchParams } = url;

	try {
		if (pathname === "/api" || pathname === "/api/") return json(API_DESCRIPTION);
		if (pathname === "/api/health") {
			await selectFirst<{ ok: number }>(env.inte_sys, { sql: "SELECT 1 AS ok", binds: [] });
			return json({ status: "ok", database: "connected" });
		}

		return (
			(await routePapers(pathname, searchParams, env.inte_sys)) ??
			(await routeOrganizations(pathname, searchParams, env.inte_sys)) ??
			(await routeAuthors(pathname, searchParams, env.inte_sys)) ??
			json({ error: { code: "NOT_FOUND", message: "API endpoint not found" } }, 404)
		);
	} catch (error) {
		return errorResponse(error);
	}
}

