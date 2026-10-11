import { notFound } from "../lib/errors";
import {
	escapeLike,
	likePattern,
	optionalText,
	parsePagination,
	selectFirst,
	selectMany,
	WhereBuilder,
} from "../lib/query";
import type { Organization, PagedResult, Pagination } from "../types";

interface CountRow {
	total: number;
}

export interface OrganizationListQuery {
	page: Pagination;
	where: WhereBuilder;
}

function buildOrganizationQuery(params: URLSearchParams): OrganizationListQuery {
	const page = parsePagination(params);
	const where = new WhereBuilder();

	const id = optionalText(params, "id");
	if (id) where.add("id = ?", id);

	const q = optionalText(params, "q");
	if (q) {
		const pattern = likePattern(q);
		where.add(
			`(${escapeLike("name LIKE ?")} OR ${escapeLike("name_en LIKE ?")} OR ${escapeLike("name_zh LIKE ?")} OR ${escapeLike("acronyms LIKE ?")} OR ${escapeLike("aliases LIKE ?")} OR ${escapeLike("location LIKE ?")})`,
			pattern,
			pattern,
			pattern,
			pattern,
			pattern,
			pattern,
		);
	}
	for (const field of ["name", "type", "location"] as const) {
		const value = optionalText(params, field);
		if (value) where.add(`${field} = ?`, value);
	}
	return { page, where };
}

export async function listOrganizations(
	db: D1Database,
	params: URLSearchParams,
): Promise<PagedResult<Organization>> {
	const query = buildOrganizationQuery(params);
	const where = query.where.toSql();
	const [count, rows] = await Promise.all([
		selectFirst<CountRow>(db, {
			sql: `SELECT COUNT(*) AS total FROM organization${where.sql}`,
			binds: where.binds,
		}),
		selectMany<Organization>(db, {
			sql: `SELECT * FROM organization${where.sql} ORDER BY name COLLATE NOCASE ASC, id ASC LIMIT ? OFFSET ?`,
			binds: [...where.binds, query.page.limit, query.page.offset],
		}),
	]);
	return { rows, total: Number(count?.total ?? 0) };
}

export async function findOrganization(db: D1Database, id: string): Promise<Organization> {
	const organization = await selectFirst<Organization>(db, {
		sql: "SELECT * FROM organization WHERE id = ?",
		binds: [id],
	});
	if (!organization) throw notFound(`Organization '${id}' was not found`);
	return organization;
}
