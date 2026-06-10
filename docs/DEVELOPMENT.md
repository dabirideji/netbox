# Development Guide

This project is intentionally small and dependency-light: Python standard library for the backend, SQLite for persistence, and Vite/Vue for the dashboard.

## Local Setup

```bash
make install
make run
```

Or, on first clone:

```bash
make setup
make run
```

Open `http://127.0.0.1:5177` for the hot-reload dashboard. The backend API runs on `http://127.0.0.1:4177`.

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
  server.py       JSON API, SSE, static assets, security headers
  state.py        Thread-safe samples, summaries, and SSE fanout
  storage.py      SQLite schema, writes, and read models
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

- `.env.example` is the committed template copied to `.env` by `make setup`.
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

First-time setup:

```bash
make setup
```

Focused commands:

```bash
make backend-test    # pytest with 70% coverage gate
make frontend-test   # vitest with coverage report
make coverage        # both suites with XML/HTML artifacts
cd frontend && npm run typecheck
```

### Backend

- Framework: pytest + pytest-cov
- Location: `backend/tests/`
- `make backend-test` runs `pytest --cov=netbox --cov-fail-under=70`
- Integration tests start a real HTTP server on an ephemeral port and write to temp SQLite files
- Mocks are limited to external I/O: ping subprocess output, Pexels HTTP, and similar boundaries

### Frontend

- Framework: Vitest + jsdom + `@vue/test-utils`
- Test files live next to the code they cover (`*.test.ts`)
- Component tests mount real Vue components; fetch is stubbed only when the test target is not the API client
- NDT7 is mocked in `speed-test.test.ts` so speed-test orchestration is verified without hitting M-Lab

### Coverage artifacts

- Backend XML: `backend/coverage.xml`
- Frontend HTML/LCOV: `frontend/coverage/`

## Persistence

The default SQLite database lives at `data/netbox.sqlite3` and is gitignored.

Useful local commands:

```bash
make db-shell
make clean-data
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
make run-prod
```

This builds `frontend/dist` and serves those static files from the Python backend.

## Docker

```bash
make docker-build
make docker-run
```

The container runs as a non-root user, includes `ping`, and exposes port `4177`. The image bundles built frontend assets and production dotenv defaults; mount secrets at runtime rather than baking them into the image.
