export default {
	async fetch(request, env) {
		const { pathname, searchParams } = new URL(request.url);
		const db = env.inte_sys;
		// ============ /api/papers ============
		// 支持可选参数： id, year, venue, limit
		if (pathname === "/api/papers") {
			const id = searchParams.get("id");
			const year = searchParams.get("year");
			const venue = searchParams.get("venue");
			const limit = Number(searchParams.get("limit")) || 50;

			if (id) {
				const { results } = await db
					.prepare("SELECT * FROM paper WHERE id = ?")
					.bind(id)
					.run();
				return Response.json(results);
			}

			let sql = "SELECT * FROM paper WHERE 1 = 1";
			const binds = [];
			if (year) {
				sql += " AND year = ?";
				binds.push(Number(year));
			}
			if (venue) {
				sql += " AND venue = ?";
				binds.push(venue);
			}
			sql += " LIMIT ?";
			binds.push(limit);

			const { results } = await db
				.prepare(sql)
				.bind(...binds)
				.run();
			return Response.json(results);
		}

		// ============ /api/organizations ============
		// 支持可选参数： id, name, type, limit
		if (pathname === "/api/organizations") {
			const id = searchParams.get("id");
			const name = searchParams.get("name");
			const type = searchParams.get("type");
			const limit = Number(searchParams.get("limit")) || 50;

			if (id) {
				const { results } = await db
					.prepare("SELECT * FROM organization WHERE id = ?")
					.bind(id)
					.run();
				return Response.json(results);
			}

			let sql = "SELECT * FROM organization WHERE 1 = 1";
			const binds = [];
			if (name) {
				sql += " AND name = ?";
				binds.push(name);
			}
			if (type) {
				sql += " AND type = ?";
				binds.push(type);
			}
			sql += " LIMIT ?";
			binds.push(limit);

			const { results } = await db
				.prepare(sql)
				.bind(...binds)
				.run();
			return Response.json(results);
		}

		// ============ /api/paperid_orgid ============
		// 支持可选参数： paperid, orgid, limit
		if (pathname === "/api/paperid_orgid") {
			const paperid = searchParams.get("paperid");
			const orgid = searchParams.get("orgid");
			const limit = Number(searchParams.get("limit")) || 50;

			let sql = "SELECT * FROM paperid_orgid WHERE 1 = 1";
			const binds = [];
			if (paperid) {
				sql += " AND paperid = ?";
				binds.push(paperid);
			}
			if (orgid) {
				sql += " AND orgid = ?";
				binds.push(orgid);
			}
			sql += " LIMIT ?";
			binds.push(limit);

			const { results } = await db
				.prepare(sql)
				.bind(...binds)
				.run();
			return Response.json(results);
		}

		return new Response(
			"Available endpoints: /api/papers?id=xxx | /api/organizations?id=xxx | /api/paperid_orgid?paperid=xxx",
		);
	},
};