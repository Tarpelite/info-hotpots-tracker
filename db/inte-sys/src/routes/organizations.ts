import { collectionResponse, json } from "../lib/http";
import { badRequest } from "../lib/errors";
import { parsePagination } from "../lib/query";
import { findOrganization, listOrganizations } from "../services/organization-service";

function pathPart(value: string): string {
	try {
		return decodeURIComponent(value);
	} catch {
		throw badRequest("The resource id is not valid URL encoding");
	}
}

export async function routeOrganizations(
	pathname: string,
	params: URLSearchParams,
	db: D1Database,
): Promise<Response | null> {
	if (pathname === "/api/organizations") {
		const page = parsePagination(params);
		const result = await listOrganizations(db, params);
		return collectionResponse(result.rows, result.total, page.limit, page.offset);
	}

	const detailMatch = pathname.match(/^\/api\/organizations\/([^/]+)$/);
	if (detailMatch) {
		return json(await findOrganization(db, pathPart(detailMatch[1])));
	}

	return null;
}
