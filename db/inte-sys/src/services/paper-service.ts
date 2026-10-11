import { badRequest, notFound } from "../lib/errors";
import {
	escapeLike,
	likePattern,
	optionalText,
	parseInteger,
	parsePagination,
	selectFirst,
	selectMany,
	WhereBuilder,
} from "../lib/query";
import type { Paper, PaperAuthor, PagedResult, Pagination } from "../types";

interface CountRow {
	total: number;
}

export interface PaperListQuery {
	page: Pagination;
	where: WhereBuilder;
	sort: string;
	direction: "ASC" | "DESC";
}

const SORT_COLUMNS: Record<string, string> = {
	year: "year",
	citations: "n_citation",
	n_citation: "n_citation",
	title: "title",
	id: "id",
};

function buildPaperQuery(params: URLSearchParams): PaperListQuery {
	const page = parsePagination(params);
	const where = new WhereBuilder();

	const id = optionalText(params, "id");
	if (id) where.add("id = ?", id);

	const q = optionalText(params, "q");
	if (q) {
		const pattern = likePattern(q);
		where.add(
			`(${escapeLike("title LIKE ?")} OR ${escapeLike("title_zh LIKE ?")} OR ${escapeLike("abstract LIKE ?")} OR ${escapeLike("abstract_zh LIKE ?")} OR ${escapeLike("keywords LIKE ?")} OR ${escapeLike("keywords_zh LIKE ?")})`,
			pattern,
			pattern,
			pattern,
			pattern,
			pattern,
			pattern,
		);
	}

	const year = params.get("year");
	if (year !== null && year.trim() !== "") where.add("year = ?", parseInteger(year, 0, "year"));
	const yearFrom = params.get("yearFrom");
	if (yearFrom !== null && yearFrom.trim() !== "") {
		where.add("year >= ?", parseInteger(yearFrom, 0, "yearFrom"));
	}
	const yearTo = params.get("yearTo");
	if (yearTo !== null && yearTo.trim() !== "") {
		where.add("year <= ?", parseInteger(yearTo, 0, "yearTo"));
	}
	if (yearFrom !== null && yearTo !== null && yearFrom.trim() && yearTo.trim()) {
		const from = parseInteger(yearFrom, 0, "yearFrom");
		const to = parseInteger(yearTo, 0, "yearTo");
		if (from > to) throw badRequest("yearFrom must be less than or equal to yearTo");
	}

	for (const field of ["venue", "doi", "issn"] as const) {
		const value = optionalText(params, field);
		if (value) where.add(`${field} = ?`, value);
	}

	const sortKey = optionalText(params, "sort") ?? "year";
	const sort = SORT_COLUMNS[sortKey];
	if (!sort) throw badRequest(`sort must be one of ${Object.keys(SORT_COLUMNS).join(", ")}`);
	const directionValue = (optionalText(params, "order") ?? "desc").toUpperCase();
	if (directionValue !== "ASC" && directionValue !== "DESC") {
		throw badRequest("order must be ASC or DESC");
	}

	return { page, where, sort, direction: directionValue };
}

export async function listPapers(db: D1Database, params: URLSearchParams): Promise<PagedResult<Paper>> {
	const query = buildPaperQuery(params);
	const where = query.where.toSql();
	const [count, rows] = await Promise.all([
		selectFirst<CountRow>(db, { sql: `SELECT COUNT(*) AS total FROM paper${where.sql}`, binds: where.binds }),
		selectMany<Paper>(db, {
			sql: `SELECT * FROM paper${where.sql} ORDER BY ${query.sort} ${query.direction}, id ASC LIMIT ? OFFSET ?`,
			binds: [...where.binds, query.page.limit, query.page.offset],
		}),
	]);
	return { rows, total: Number(count?.total ?? 0) };
}

export async function findPaper(db: D1Database, id: string): Promise<Paper> {
	const paper = await selectFirst<Paper>(db, {
		sql: "SELECT * FROM paper WHERE id = ?",
		binds: [id],
	});
	if (!paper) throw notFound(`Paper '${id}' was not found`);
	return paper;
}

export async function listPaperAuthors(db: D1Database, paperid: string): Promise<PaperAuthor[]> {
	return selectMany<PaperAuthor>(db, {
		sql: "SELECT * FROM paper_author WHERE paperid = ? ORDER BY name, name_zh, org, org_zh",
		binds: [paperid],
	});
}

export async function findPaperWithAuthors(db: D1Database, id: string): Promise<Paper & { author_rows: PaperAuthor[] }> {
	const [paper, authorRows] = await Promise.all([findPaper(db, id), listPaperAuthors(db, id)]);
	return { ...paper, author_rows: authorRows };
}
