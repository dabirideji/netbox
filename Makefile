PYTHON = $(shell if [ -x "$(CURDIR)/.venv/bin/python" ]; then printf '%s/.venv/bin/python' '$(CURDIR)'; elif [ -f .dev/python-bin ]; then cat .dev/python-bin; elif command -v python3 >/dev/null 2>&1; then command -v python3; else printf 'python3'; fi)
-include .env
CODEX_NODE_DIR := $(HOME)/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin
NPM ?= $(shell if [ -x "$(CODEX_NODE_DIR)/node" ] && [ -f "/opt/homebrew/lib/node_modules/npm/bin/npm-cli.js" ]; then printf '%s %s' "$(CODEX_NODE_DIR)/node" "/opt/homebrew/lib/node_modules/npm/bin/npm-cli.js"; else printf 'npm'; fi)
IMAGE ?= netbox
PORT ?= $(or $(NETBOX_PORT),4177)
HOST ?= $(or $(NETBOX_HOST),127.0.0.1)
FRONTEND_PORT ?= $(or $(NETBOX_FRONTEND_PORT),5177)
FRONTEND_URL ?= http://$(HOST):$(FRONTEND_PORT)
BACKEND_URL ?= http://$(HOST):$(PORT)
ARGS ?=
PYTHONPATH := $(CURDIR)/backend/src
export PYTHONPATH
export NPM
ifneq ($(wildcard $(CODEX_NODE_DIR)/node),)
export PATH := $(CODEX_NODE_DIR):$(PATH)
endif

.PHONY: help setup setup-check setup-dirs setup-env seed-targets ensure-ready install install-backend install-frontend install-electron build frontend-build run run-prod run-backend dev frontend-dev electron-dev electron-build-backend electron-package backend-test frontend-test test coverage lint db-shell clean clean-data docker-build docker-run

.DEFAULT_GOAL := help

help:
	@printf "\n"
	@printf "  Netbox - local network stability monitor\n\n"
	@printf "  Getting started\n"
	@printf "    make setup            First-time install, folders, and local env\n"
	@printf "    make run              Backend API + Vite dashboard (hot reload)\n\n"
	@printf "  Development\n"
	@printf "    make install          Install backend and frontend dependencies\n"
	@printf "    make dev              Alias for make run\n"
	@printf "    make frontend-dev     Run only the Vite frontend dev server\n"
	@printf "    make run-backend      Run only the backend monitor/API\n"
	@printf "    make lint             Run Ruff and vue-tsc\n"
	@printf "    make test             Run backend pytest and frontend Vitest\n"
	@printf "    make coverage         Run test suites with coverage reports\n\n"
	@printf "  Production\n"
	@printf "    make build            Build frontend/dist\n"
	@printf "    make run-prod         Build frontend, then serve from backend\n"
	@printf "    make docker-build     Build the Docker image\n"
	@printf "    make docker-run       Run the container on port $(PORT)\n\n"
	@printf "  Desktop (Electron)\n"
	@printf "    make electron-dev     Run the desktop shell against local backend\n"
	@printf "    make electron-build-backend  Bundle Python backend with PyInstaller\n"
	@printf "    make electron-package Build installers (.dmg, .exe, AppImage)\n\n"
	@printf "  Data\n"
	@printf "    make db-shell         Open the SQLite history database\n"
	@printf "    make clean-data       Delete persisted local history\n"
	@printf "    make clean            Remove build output and test caches\n\n"
	@printf "  Dev URLs (default)\n"
	@printf "    Dashboard  $(FRONTEND_URL)\n"
	@printf "    API        $(BACKEND_URL)\n\n"

setup: setup-check setup-dirs setup-env install seed-targets
	@printf "\n"
	@printf "  Setup complete.\n\n"
	@printf "  Next steps:\n"
	@printf "    make run              Start the hot-reload dev stack\n"
	@printf "    make test             Verify backend and frontend tests\n\n"
	@printf "  Optional: add PEXELS_API_KEY to .env.local for dashboard wallpapers.\n"
	@printf "  For production, copy .env.example to .env.production and adjust hosts.\n\n"

setup-check:
	@bash scripts/ensure-python.sh
	@command -v node >/dev/null 2>&1 || (printf "node is required but was not found in PATH.\n" && exit 1)
	@command -v npm >/dev/null 2>&1 || (printf "npm is required but was not found in PATH.\n" && exit 1)

setup-dirs:
	@mkdir -p data .dev/static

setup-env:
	@if [ ! -f .env ] && [ -f .env.example ]; then \
		cp .env.example .env; \
		printf "  Created .env from .env.example\n"; \
	fi

seed-targets:
	@$(PYTHON) backend/monitor.py seed

DB_FILE ?= data/netbox.sqlite3

ensure-ready:
	@needs=0; \
	if [ ! -d frontend/node_modules ]; then needs=1; fi; \
	if ! $(PYTHON) -c "import netbox" 2>/dev/null; then needs=1; fi; \
	if ! $(PYTHON) -c "import dns.resolver" 2>/dev/null; then needs=1; fi; \
	if [ ! -f "$(or $(NETBOX_DB_PATH),$(DB_FILE))" ]; then needs=1; fi; \
	if [ "$$needs" = "1" ]; then \
		printf "\n  First-time or incomplete setup detected. Running make setup...\n\n"; \
		$(MAKE) setup; \
	fi

install: install-backend install-frontend

install-backend:
	@bash scripts/ensure-venv.sh

install-frontend:
	cd frontend && $(NPM) install

install-electron:
	cd electron && $(NPM) install

build: frontend-build

frontend-build:
	cd frontend && $(NPM) run build

run: ensure-ready
	$(PYTHON) -u scripts/dev.py --host $(HOST) --backend-port $(PORT) --frontend-port $(FRONTEND_PORT) -- $(ARGS)

run-prod: ensure-ready build
	$(PYTHON) backend/monitor.py --host $(HOST) --port $(PORT) $(ARGS)

run-backend: ensure-ready
	$(PYTHON) backend/monitor.py --host $(HOST) --port $(PORT) $(ARGS)

dev: run

frontend-dev:
	cd frontend && $(NPM) run dev -- --host $(HOST) --port $(FRONTEND_PORT)

electron-dev: ensure-ready build install-electron
	NETBOX_PROJECT_ROOT="$(CURDIR)" NETBOX_PYTHON="$(PYTHON)" cd electron && $(NPM) run dev

electron-build-backend:
	bash scripts/build-backend.sh

electron-package:
	bash scripts/package-desktop.sh

backend-test:
	cd backend && $(PYTHON) -m pytest --cov=netbox --cov-report=term-missing --cov-fail-under=70

frontend-test:
	cd frontend && $(NPM) test

test: backend-test frontend-test

coverage:
	cd backend && $(PYTHON) -m pytest --cov=netbox --cov-report=term-missing --cov-report=xml
	cd frontend && $(NPM) test
	@printf "\nBackend coverage: backend/coverage.xml\n"
	@printf "Frontend coverage: frontend/coverage/\n"

lint:
	cd backend && $(PYTHON) -m ruff check src tests
	cd frontend && $(NPM) run typecheck

db-shell:
	sqlite3 data/netbox.sqlite3

clean:
	rm -rf frontend/dist frontend/coverage backend/.pytest_cache backend/coverage.xml backend/src/*.egg-info .dev dist-backend electron/dist electron/release
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

clean-data:
	rm -f data/netbox.sqlite3 data/netbox.sqlite3-wal data/netbox.sqlite3-shm

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm -p $(PORT):4177 $(IMAGE)
