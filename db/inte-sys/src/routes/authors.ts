import { collectionResponse } from "../lib/http";
import { parsePagination } from "../lib/query";
import { listAuthors } from "../services/author-service";

const AUTHOR_PATHS = new Set(["/api/paper-authors", "/api/paper_authors", "/api/paper_author"]);

export async function routeAuthors(pathname: string, params: URLSearchParams, db: D1Database): Promise<Response | null> {
	if (!AUTHOR_PATHS.has(pathname)) return null;
	const page = parsePagination(params);
	const result = await listAuthors(db, params);
	return collectionResponse(result.rows, result.total, page.limit, page.offset);
}
