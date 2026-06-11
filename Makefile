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
DB_FILE ?= data/netbox.sqlite3
PYTHONPATH := $(CURDIR)/backend/src
export PYTHONPATH
export NPM
ifneq ($(wildcard $(CODEX_NODE_DIR)/node),)
export PATH := $(CODEX_NODE_DIR):$(PATH)
endif

.PHONY: help setup run test lint build clean desktop package ensure-ready install-backend install-frontend install-electron seed-targets electron-build-backend generate-icons docker-build docker-run

.DEFAULT_GOAL := help

help:
	@printf "\n"
	@printf "  Netbox\n\n"
	@printf "    make setup     Prepare local env (optional; make run does this too)\n"
	@printf "    make run       Dev dashboard + API\n"
	@printf "    make test      Backend and frontend tests\n"
	@printf "    make lint      Ruff + vue-tsc\n"
	@printf "    make build     Frontend production build\n"
	@printf "    make clean     Remove build output and test caches\n"
	@printf "    make desktop   Electron shell (dev)\n"
	@printf "    make package   Desktop installers\n\n"
	@printf "  Dashboard  $(FRONTEND_URL)\n"
	@printf "  API        $(BACKEND_URL)\n\n"

setup: ensure-ready
	@if [ ! -f "$(or $(NETBOX_DB_PATH),$(DB_FILE))" ]; then \
		printf "\n  Seeding default monitor targets...\n\n"; \
		$(MAKE) seed-targets; \
	fi
	@printf "\n  Ready. Run make run to start the dev stack.\n\n"

ensure-ready:
	@bash scripts/ensure-python.sh
	@command -v node >/dev/null 2>&1 || (printf "node is required but was not found in PATH.\n" && exit 1)
	@command -v npm >/dev/null 2>&1 || (printf "npm is required but was not found in PATH.\n" && exit 1)
	@mkdir -p data .dev/static
	@if [ ! -f .env ] && [ -f .env.example ]; then \
		cp .env.example .env; \
		printf "  Created .env from .env.example\n"; \
	fi
	@if [ ! -d frontend/node_modules ]; then \
		printf "\n  Installing frontend dependencies...\n\n"; \
		$(MAKE) install-frontend; \
	fi
	@if ! $(PYTHON) -c "import netbox, dns.resolver, cryptography" 2>/dev/null; then \
		printf "\n  Installing backend dependencies...\n\n"; \
		$(MAKE) install-backend; \
	fi
install-backend:
	@bash scripts/ensure-venv.sh

install-frontend:
	cd frontend && $(NPM) install

install-electron:
	cd electron && $(NPM) install

seed-targets:
	@$(PYTHON) backend/monitor.py seed

run: ensure-ready
	$(PYTHON) -u scripts/dev.py --host $(HOST) --backend-port $(PORT) --frontend-port $(FRONTEND_PORT) -- $(ARGS)

generate-icons:
	bash scripts/generate-icons.sh

build: generate-icons
	cd frontend && $(NPM) run build

test:
	cd backend && $(PYTHON) -m pytest --cov=netbox --cov-report=term-missing --cov-fail-under=70
	cd frontend && $(NPM) test

lint:
	cd backend && $(PYTHON) -m ruff check src tests
	cd frontend && $(NPM) run typecheck

clean:
	rm -rf frontend/dist frontend/coverage backend/.pytest_cache backend/coverage.xml backend/src/*.egg-info .dev dist-backend electron/dist electron/release
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
ifeq ($(DATA),1)
	rm -f data/netbox.sqlite3 data/netbox.sqlite3-wal data/netbox.sqlite3-shm
endif

desktop: ensure-ready build install-electron
	NETBOX_PROJECT_ROOT="$(CURDIR)" NETBOX_PYTHON="$(PYTHON)" cd electron && $(NPM) run dev

electron-build-backend:
	bash scripts/build-backend.sh

package:
	bash scripts/package-desktop.sh

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm -p $(PORT):4177 $(IMAGE)
