import {
	escapeLike,
	likePattern,
	optionalText,
	parsePagination,
	selectFirst,
	selectMany,
	WhereBuilder,
} from "../lib/query";
import type { PaperAuthor, PagedResult, Pagination } from "../types";

interface CountRow {
	total: number;
}

function buildAuthorQuery(params: URLSearchParams): { page: Pagination; where: WhereBuilder } {
	const page = parsePagination(params);
	const where = new WhereBuilder();
	const paperid = optionalText(params, "paperid");
	if (paperid) where.add("paperid = ?", paperid);

	const q = optionalText(params, "q");
	if (q) {
		const pattern = likePattern(q);
		where.add(
			`(${escapeLike("name LIKE ?")} OR ${escapeLike("name_zh LIKE ?")} OR ${escapeLike("org LIKE ?")} OR ${escapeLike("org_zh LIKE ?")})`,
			pattern,
			pattern,
			pattern,
			pattern,
		);
	}
	for (const field of ["name", "name_zh", "org", "org_zh"] as const) {
		const value = optionalText(params, field);
		if (value) where.add(`${field} = ?`, value);
	}
	return { page, where };
}

export async function listAuthors(db: D1Database, params: URLSearchParams): Promise<PagedResult<PaperAuthor>> {
	const query = buildAuthorQuery(params);
	const where = query.where.toSql();
	const [count, rows] = await Promise.all([
		selectFirst<CountRow>(db, {
			sql: `SELECT COUNT(*) AS total FROM paper_author${where.sql}`,
			binds: where.binds,
		}),
		selectMany<PaperAuthor>(db, {
			sql: `SELECT * FROM paper_author${where.sql} ORDER BY paperid, name, name_zh LIMIT ? OFFSET ?`,
			binds: [...where.binds, query.page.limit, query.page.offset],
		}),
	]);
	return { rows, total: Number(count?.total ?? 0) };
}
