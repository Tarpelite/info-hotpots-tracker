import { env, createExecutionContext, waitOnExecutionContext } from "cloudflare:test";
import { beforeAll, describe, expect, it } from "vitest";
import worker from "../src/index";

const IncomingRequest = Request<unknown, IncomingRequestCfProperties>;

async function request(path: string, init?: RequestInit): Promise<Response> {
	const context = createExecutionContext();
	const response = await worker.fetch(new IncomingRequest(`http://example.com${path}`, init), env, context);
	await waitOnExecutionContext(context);
	return response;
}

beforeAll(async () => {
	await env.inte_sys.exec("PRAGMA foreign_keys = ON");
	await env.inte_sys.exec(`
		CREATE TABLE IF NOT EXISTS paper (
			id TEXT NOT NULL PRIMARY KEY, doi TEXT, title TEXT, title_zh TEXT, abstract TEXT,
			abstract_zh TEXT, authors TEXT, keywords TEXT, keywords_zh TEXT, venue TEXT,
			issn TEXT, volume TEXT, issue TEXT, year INTEGER, n_citation INTEGER
		);
		CREATE TABLE IF NOT EXISTS organization (
			id TEXT NOT NULL PRIMARY KEY, name TEXT NOT NULL, name_en TEXT, name_zh TEXT,
			type TEXT, acronyms TEXT, aliases TEXT, details TEXT, location TEXT, url TEXT, image TEXT
		);
		CREATE TABLE IF NOT EXISTS paper_author (
			paperid TEXT NOT NULL, name TEXT, name_zh TEXT, org TEXT, org_zh TEXT,
			PRIMARY KEY (paperid, name, name_zh, org, org_zh),
			FOREIGN KEY (paperid) REFERENCES paper(id) ON UPDATE CASCADE ON DELETE CASCADE
		);
	`);
	await env.inte_sys.prepare("DELETE FROM paper_author").run();
	await env.inte_sys.prepare("DELETE FROM paper").run();
	await env.inte_sys.prepare("DELETE FROM organization").run();
	await env.inte_sys.prepare(
		"INSERT INTO paper (id, title, title_zh, abstract, venue, year, n_citation) VALUES (?, ?, ?, ?, ?, ?, ?)",
	).bind("paper-1", "Aerospace Intelligence", "航空情报研究", "Research abstract", "Aerospace Science", 2025, 12).run();
	await env.inte_sys.prepare(
		"INSERT INTO organization (id, name, name_en, name_zh, type, location) VALUES (?, ?, ?, ?, ?, ?)",
	).bind("org-1", "北京航空航天大学", "Beihang University", "北京航空航天大学", "TYPE_EDUCATION", "北京").run();
	await env.inte_sys.prepare(
		"INSERT INTO paper_author (paperid, name, name_zh, org, org_zh) VALUES (?, ?, ?, ?, ?)",
	).bind("paper-1", "A. Researcher", "研究员甲", "Beihang University", "北京航空航天大学").run();
});
describe("query API", () => {
	it("exposes the D1-backed API and health check", async () => {
		const docs = await request("/api");
		expect(docs.status).toBe(200);
		expect((await docs.json<{ endpoints: Record<string, string> }>()).endpoints["GET /api/paper-authors"]).toBeTruthy();

		const health = await request("/api/health");
		expect(await health.json()).toEqual({ status: "ok", database: "connected" });
	});

	it("searches and paginates papers with total count metadata", async () => {
		const response = await request("/api/papers?q=aerospace&yearFrom=2020&limit=1&offset=0");
		expect(response.status).toBe(200);
		expect(response.headers.get("X-Total-Count")).toBe("1");
		expect(await response.json()).toMatchObject([{ id: "paper-1", year: 2025 }]);
	});

	it("returns a paper with normalized author rows and supports the author table endpoint", async () => {
		const paper = await request("/api/papers/paper-1");
		expect(await paper.json()).toMatchObject({ id: "paper-1", author_rows: [{ name: "A. Researcher" }] });

		const authors = await request("/api/paper-authors?paperid=paper-1");
		expect(await authors.json()).toMatchObject([{ paperid: "paper-1", org_zh: "北京航空航天大学" }]);
	});

	it("filters organizations and returns clear client errors for invalid input", async () => {
		const organizations = await request("/api/organizations?q=Beihang");
		expect(await organizations.json()).toMatchObject([{ id: "org-1" }]);

		const invalid = await request("/api/papers?limit=500");
		expect(invalid.status).toBe(400);
		expect(await invalid.json()).toMatchObject({ error: { code: "BAD_REQUEST" } });

		const missing = await request("/api/organizations/missing");
		expect(missing.status).toBe(404);
	});

	it("handles CORS preflight and rejects write methods", async () => {
		const preflight = await request("/api/papers", { method: "OPTIONS" });
		expect(preflight.status).toBe(204);
		expect(preflight.headers.get("Access-Control-Allow-Origin")).toBe("*");

		const write = await request("/api/papers", { method: "POST" });
		expect(write.status).toBe(405);
	});
});
