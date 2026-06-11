# Development Guide

This project is intentionally small and dependency-light: Python standard library for the backend, SQLite for persistence, and Vite/Vue for the dashboard.

## Local Setup

```bash
make setup   # optional on first clone
make run
```

`make setup` and first `make run` both install dependencies, create `.env` when needed, and seed the local database.

Open `http://127.0.0.1:5177` for the hot-reload dashboard. The backend API runs on `http://127.0.0.1:4177`.

## Module size

Keep modules focused and easy to scan:

- **Soft cap:** ~300 lines per `.py`, `.ts`, or `.vue` file. Split when a file mixes responsibilities or grows past this.
- **Hard split triggers:** distinct persistence domains, HTTP method handlers, large Vue sections, or reusable composables that can stand alone.
- **Backend packages:** use folders with a thin `__init__.py` re-export (`storage/`, `server/`) so imports stay stable (`from netbox.storage import StatusStore`).
- **Frontend:** move section logic into composables (`useTargetsConfigSection.ts`) and small child components instead of growing a single `.vue` file.

## Code Organization

```text
backend/monitor.py        Local backend entrypoint
backend/tests/            Pytest suite
backend/src/netbox/
  config.py       Dotenv and JSON configuration loading
  cli.py          CLI parsing and process lifecycle
  models.py       Shared dataclasses and status types
  network.py      Gateway/interface/Wi-Fi detection
  ping.py         Platform-specific ping command and parsing
  state.py        Thread-safe samples, summaries, and SSE fanout
  storage/        SQLite persistence package (schema, targets, history, events, pruning)
  server/         HTTP API package (routing dispatch, handler, static files, SSE)
  summary.py      Status aggregation and incident capture
  speed.py        Speed-test validation and policy helpers
  terminal.py     Terminal dashboard renderer
  validation.py   CLI/API validation helpers
  wallpaper.py    Pexels wallpaper proxy for the dashboard

frontend/src/
  App.vue         Dashboard composition and live state
  api.ts          REST/SSE client
  chart.ts        SVG line-chart geometry for the overview timeline
  speed-test.ts   Browser-side M-Lab NDT7 orchestration
  theme.ts        Theme preference helpers
  wallpaper.ts    Wallpaper preference helpers
  components/     Dashboard sections, app chrome, and UI primitives
    AppChrome.vue       Fixed viewport controls (spinner, wallpaper, theme)
    ThemeSwitcher.vue   Light/dark/system cycle button
    WallpaperToggle.vue Optional Pexels background switch
  composables/    Shared Vue composables for theme, wallpaper, and loading
  format.ts       Display formatting helpers
  range.ts        Date-range parsing and query params
  stores/         Pinia stores for monitor, history, speed tests, and UI prefs
  types.ts        Frontend API contracts
  components/ui/  Local shadcn-vue style primitives

frontend/public/
  ndt7-*.js       NDT7 web workers served by Vite during speed tests

config/
  backend.json    Backend, monitor, storage, and network defaults
  frontend.json   Vite, app-name, and proxy defaults
  security.json   Bind allow-list and HTTP security headers
  targets.json    Default external targets
  speed.json      M-Lab NDT7 speed-test policy and metadata
```

## Configuration

Use JSON config for structured application defaults and dotenv files for environment-specific values:

- `.env.example` is the committed template copied to `.env` on first `make run`.
- `.env` holds local development environment values such as ports, database path, and config directory (gitignored).
- `.env.production` holds production runtime defaults and is loaded when `NETBOX_ENV=production` (gitignored).
- `config/*.json` holds reviewable, typed defaults for backend behavior, frontend dev behavior, targets, and security policy.
- `.env.local` and `.env.*.local` are reserved for private machine-specific overrides and secrets (gitignored).
- `PEXELS_API_KEY` enables the optional dashboard wallpaper proxy; keep it in `.env.local`, not in committed files.

Runtime precedence is shell environment variables first, dotenv files second, JSON config third, and safe code defaults last. Dotenv files load as `.env`, `.env.local`, `.env.<NETBOX_ENV>`, and `.env.<NETBOX_ENV>.local`. Prefer adding new cross-cutting defaults to `config/*.json`; use environment variables for deployment-specific overrides or sensitive values.

## Git and Ignored Files

`.gitignore` excludes:

- Secrets: `.env`, `.env.production`, `.env.local`, `.env.*.local`, key material
- Runtime data: `data/`, `*.sqlite3`
- Build and cache output: `frontend/dist`, `frontend/node_modules`, Python `__pycache__`, coverage reports
- IDE and OS clutter: `.idea/`, `.vscode/`, `.DS_Store`

Safe to commit: source code, `config/`, `.env.example`, and documentation.

## Coding Standards

- Keep modules focused on one responsibility.
- Keep configuration centralized in `config/*.json` and `.env*`; avoid scattering magic constants through runtime code.
- Prefer pure helper functions for parsing, formatting, validation, and chart geometry.
- Document module purpose and public functions with short docstrings/JSDoc.
- Use comments to explain intent, constraints, or non-obvious decisions; avoid narrating obvious code.
- Keep backend subprocess calls shell-free by passing argument arrays.
- Keep SQL parameterized and validate/bound all API query inputs before database access.
- Keep frontend UI controls routed through `frontend/src/components/ui` shadcn-style primitives.
- Keep active speed tests user-initiated; do not add automatic bandwidth tests against public providers.
- Keep API keys and tokens out of the frontend bundle; proxy third-party calls through the backend when needed.
- Preserve compact neutral styling and keep border radius at `var(--radius)` or none.

## Testing

Run the full verification stack:

```bash
make lint
make test
make build
```

Quality checks:

```bash
make lint
make test
```

### Backend

- Framework: pytest + pytest-cov
- Location: `backend/tests/`
- `make test` runs `pytest --cov=netbox --cov-fail-under=70` for the backend
- Integration tests start a real HTTP server on an ephemeral port and write to temp SQLite files
- Mocks are limited to external I/O: ping subprocess output, Pexels HTTP, and similar boundaries

### Frontend

- Framework: Vitest + jsdom + `@vue/test-utils`
- Test files live next to the code they cover (`*.test.ts`)
- `make test` also runs `vitest run --coverage` with baseline thresholds in `frontend/vite.config.ts`
- Component tests mount real Vue components; fetch is stubbed only when the test target is not the API client
- NDT7 is mocked in `speed-test.test.ts` so speed-test orchestration is verified without hitting M-Lab

### Coverage artifacts

- Backend XML: `backend/coverage.xml`
- Frontend HTML/LCOV: `frontend/coverage/`

## Persistence

The default SQLite database lives at `data/netbox.sqlite3` and is gitignored.

Useful local commands:

```bash
sqlite3 data/netbox.sqlite3
make clean DATA=1
```

Use `--db-path` to test against a temporary database:

```bash
make run ARGS='--db-path /tmp/netbox.sqlite3'
```

## Hot Reload

`make run` starts `scripts/dev.py`, which manages two processes:

- Vite dev server with Vue/TypeScript/CSS HMR.
- Python backend process that restarts when `backend/monitor.py` or `backend/src/**/*.py` changes.

The frontend proxies `/api/*` and `/events` to the backend.

## Release-Style Run

```bash
make build
.venv/bin/python backend/monitor.py --host 127.0.0.1 --port 4177
```

This serves `frontend/dist` from the Python backend.

## Docker

```bash
make docker-build
make docker-run
```

The container runs as a non-root user, includes `ping`, and exposes port `4177`. The image bundles built frontend assets and production dotenv defaults; mount secrets at runtime rather than baking them into the image.
