# Netbox

Local network stability monitor with a Python backend and Vue dashboard. Netbox pings your gateway and external targets every second, persists history in SQLite, and helps separate local network issues from upstream/ISP problems.

## Quick start

```bash
make setup
make run
```

| Service | URL |
| --- | --- |
| Dashboard | http://localhost:5177 |
| API | http://localhost:4177 |

Backend options can be passed through `make run`:

```bash
make run ARGS='--wifi-name "Office Wi-Fi"'
```

## Commands

| Command | Description |
| --- | --- |
| `make setup` | First-time install, folders, and local env |
| `make install` | Install backend and frontend dependencies |
| `make run` | Start backend + Vite dev server with hot reload |
| `make run-prod` | Build frontend and run production-style backend |
| `make build` | Build `frontend/dist` |
| `make test` | Run backend pytest (with coverage gate) and frontend Vitest |
| `make coverage` | Run both suites with coverage reports |
| `make lint` | Run Ruff and `vue-tsc` |
| `make db-shell` | Open the local SQLite database |
| `make clean-data` | Delete persisted local history |
| `make docker-build` | Build the Docker image |
| `make docker-run` | Run the container on port 4177 |

## Layout

```text
backend/                 Python package, tests, and monitor entrypoint
backend/monitor.py       Run the backend locally
config/                  JSON configuration
frontend/                Vite + Vue dashboard
frontend/public/         Static assets served by Vite (NDT7 workers)
docs/                    API, architecture, and development notes
scripts/dev.py           Hot-reload dev stack runner
data/                    Local SQLite database (gitignored)
```

## Configuration

Defaults live in `config/*.json`. Runtime values load from `.env`, then optional `.env.local` (gitignored), then `.env.<NETBOX_ENV>` files.

| Path | Purpose |
| --- | --- |
| `config/backend.json` | Host, port, monitor thresholds, database path |
| `config/frontend.json` | App name and dev-server defaults |
| `config/targets.json` | Default external ping targets |
| `config/speed.json` | NDT7 speed-test policy |
| `config/security.json` | Bind allow-list and security headers |
| `.env` | Development ports and shared defaults |
| `.env.production` | Production defaults when `NETBOX_ENV=production` |
| `.env.local` | Private overrides and secrets (gitignored) |

Optional Pexels wallpaper support proxies nature images through the backend. Copy `.env.example` to `.env.local` and set `PEXELS_API_KEY`. Never commit real API keys.

## Dashboard features

- **Live monitoring** — gateway and external ping checks with SSE updates
- **History and incidents** — persisted timeline, target breakdown, and paginated incident log
- **Speed tests** — user-initiated M-Lab NDT7 runs with policy limits
- **Theme** — light, dark, or system preference (stored in browser localStorage)
- **Wallpaper** — optional Pexels nature backgrounds with glass-style cards when enabled

UI preferences such as collapsed dashboard sections sync to SQLite via `/api/preferences`.

## Git and secrets

`.gitignore` excludes local secrets, runtime data, build output, and tool caches. Safe to commit: source, `config/`, `.env`, `.env.production`, and `.env.example`. Keep private values in `.env.local` only.

Before your first push, run `git add -A && git status` and confirm no secrets or `data/` files are staged.

## Production

```bash
make run-prod
```

Or:

```bash
make docker-build
make docker-run
```

After `make install`, you can also run `netbox` directly.

## Documentation

- [`docs/API.md`](docs/API.md) — REST and SSE endpoints
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design and security
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — workflow, layout, and standards

## Authorship

Roughly **5%** of this codebase was written by [Marvelous Solomon](https://github.com/solomonmarvel97). The remaining **95%** was written by **Cursor Composer** in under 6 hours.
