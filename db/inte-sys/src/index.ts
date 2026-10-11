import { errorResponse, json, noContent } from "./lib/http";
import { routeApi } from "./routes/api";

const worker = {
	async fetch(request: Request, env: Env): Promise<Response> {
		try {
			if (request.method === "OPTIONS") return noContent();
			if (request.method !== "GET") {
				return json({ error: { code: "METHOD_NOT_ALLOWED", message: "Only GET is supported" } }, 405, {
					Allow: "GET, OPTIONS",
				});
			}

			const { pathname } = new URL(request.url);
			if (pathname === "/" || pathname === "") {
				return json({ service: "inte-sys", status: "ok", docs: "/api" });
			}
			if (pathname === "/api" || pathname.startsWith("/api/")) {
				return routeApi(request, env);
			}
			return json({ error: { code: "NOT_FOUND", message: "Route not found" } }, 404);
		} catch (error) {
			return errorResponse(error);
		}
	},
};

export default worker;
