export default {
	async fetch(request, env) {
		const { pathname } = new URL(request.url);

		if (pathname === "/api/beverages") {
			// If you did not use `DB` as your binding name, change it here
			const { results } = await env.intelligence_system
				.prepare("SELECT * FROM paper")
				.bind("Bs Beverages")
				.run();
			return Response.json(results);
		}

		return new Response(
			"Call /api/beverages to see everyone who works at Bs Beverages",
		);
	},
};