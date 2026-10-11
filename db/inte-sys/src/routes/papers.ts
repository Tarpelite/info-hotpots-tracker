import { collectionResponse, json } from "../lib/http";
import { badRequest } from "../lib/errors";
import { parsePagination } from "../lib/query";
import { findPaperWithAuthors, listPaperAuthors, listPapers } from "../services/paper-service";

function pathPart(value: string): string {
	try {
		return decodeURIComponent(value);
	} catch {
		throw badRequest("The resource id is not valid URL encoding");
	}
}

export async function routePapers(pathname: string, params: URLSearchParams, db: D1Database): Promise<Response | null> {
	if (pathname === "/api/papers") {
		const page = parsePagination(params);
		const result = await listPapers(db, params);
		return collectionResponse(result.rows, result.total, page.limit, page.offset);
	}

	const authorsMatch = pathname.match(/^\/api\/papers\/([^/]+)\/authors$/);
	if (authorsMatch) {
		const authors = await listPaperAuthors(db, pathPart(authorsMatch[1]));
		return json(authors);
	}

	const detailMatch = pathname.match(/^\/api\/papers\/([^/]+)$/);
	if (detailMatch) {
		return json(await findPaperWithAuthors(db, pathPart(detailMatch[1])));
	}

	return null;
}
