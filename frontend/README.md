# AI4S public frontend

React/Vite implementation for the public site. The repository root `index.html` is the entry; UI source lives under `frontend/src`.

## Commands

- `npm --prefix frontend install`
- `npm --prefix frontend run dev`
- `npm --prefix frontend run build`

The public page first requests `/api/public/snapshot`; if unavailable it falls back to `result/data.json` and normalizes the cleaned result in the browser. The ask box posts to `/api/ask` and does not synthesize demo answers.

## Routes

- `#/`: public homepage with the map hero, ask entry, and top bar.
- `#/map`: strategic map without the ask entry.
- `#/hot`: latest evidence feed.
- `#/domains`: domain coverage.
- `#/teams`: team cards.
- `#/teams/:team_id`: team detail.
- `#/monthly`, `#/workspace`, `#/developers`: reserved workbench routes.
