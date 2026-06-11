#!/usr/bin/env bash
# Ensure Python 3.11+ is available for Netbox setup; optionally install it by OS.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_MARKER="$ROOT/.dev/python-bin"
MIN_VERSION=(3 11)

log() {
  printf '%s\n' "$*"
}

err() {
  printf '%s\n' "$*" >&2
}

refresh_path() {
  export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin:$PATH"
}

python_cmd() {
  refresh_path
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$(command -v "$candidate")"
      return 0
    fi
  done
  return 1
}

version_ok() {
  "$1" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (${MIN_VERSION[0]}, ${MIN_VERSION[1]}) else 1)" 2>/dev/null
}

write_marker() {
  mkdir -p "$(dirname "$PYTHON_MARKER")"
  python_cmd >"$PYTHON_MARKER"
}

confirm_install() {
  if [ "${NETBOX_AUTO_INSTALL_PYTHON:-}" = "1" ]; then
    return 0
  fi
  if [ ! -t 0 ] || [ "${CI:-}" = "true" ]; then
    return 1
  fi

  printf '\nPython %s+ was not found.\n' "${MIN_VERSION[0]}.${MIN_VERSION[1]}"
  printf 'Netbox needs Python to run the backend.\n\n'
  printf 'Install Python now? [y/N] '
  read -r reply
  case "${reply}" in
    [yY] | [yY][eE][sS]) return 0 ;;
    *) return 1 ;;
  esac
}

install_python_macos() {
  if command -v brew >/dev/null 2>&1; then
    log "Installing Python via Homebrew..."
    if brew install python@3.12; then
      return 0
    fi
    brew install python3
    return 0
  fi

  err "Homebrew was not found."
  err "Install Homebrew from https://brew.sh or Python from https://www.python.org/downloads/macos/"
  return 1
}

install_python_linux() {
  if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
  fi

  local id_like="${ID_LIKE:-}"
  local distro="${ID:-unknown}"

  case "$distro:$id_like" in
    ubuntu:* | debian:* | *ubuntu* | *debian*)
      log "Installing Python via apt..."
      sudo apt-get update
      sudo apt-get install -y python3 python3-pip python3-venv
      return 0
      ;;
    fedora:* | rhel:* | centos:* | rocky:* | almalinux:* | *fedora* | *rhel* | *centos*)
      if command -v dnf >/dev/null 2>&1; then
        log "Installing Python via dnf..."
        sudo dnf install -y python3 python3-pip
        return 0
      fi
      if command -v yum >/dev/null 2>&1; then
        log "Installing Python via yum..."
        sudo yum install -y python3 python3-pip
        return 0
      fi
      ;;
    arch:* | manjaro:* | *arch*)
      log "Installing Python via pacman..."
      sudo pacman -Sy --noconfirm python python-pip
      return 0
      ;;
    alpine:* | *alpine*)
      log "Installing Python via apk..."
      sudo apk add python3 py3-pip
      return 0
      ;;
    opensuse*:* | sles:* | *suse*)
      log "Installing Python via zypper..."
      sudo zypper --non-interactive install python3 python3-pip
      return 0
      ;;
  esac

  err "Unsupported Linux distribution: ${PRETTY_NAME:-$distro}"
  err "Install Python ${MIN_VERSION[0]}.${MIN_VERSION[1]}+ with your package manager, then run make run again."
  return 1
}

install_python_windows() {
  if command -v winget >/dev/null 2>&1; then
    log "Installing Python via winget..."
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    return 0
  fi
  if command -v choco >/dev/null 2>&1; then
    log "Installing Python via Chocolatey..."
    choco install python -y
    return 0
  fi

  err "Install Python from https://www.python.org/downloads/windows/"
  err "Enable \"Add python.exe to PATH\" during installation, then run make run again."
  return 1
}

install_python() {
  case "$(uname -s)" in
    Darwin) install_python_macos ;;
    Linux) install_python_linux ;;
    MINGW* | MSYS* | CYGWIN*) install_python_windows ;;
    *)
      err "Unsupported operating system: $(uname -s)"
      err "Install Python ${MIN_VERSION[0]}.${MIN_VERSION[1]}+ manually, then run make run again."
      return 1
      ;;
  esac
}

main() {
  refresh_path

  if cmd="$(python_cmd)"; then
    if version_ok "$cmd"; then
      write_marker
      exit 0
    fi
    err "Python ${MIN_VERSION[0]}.${MIN_VERSION[1]}+ is required; found $($cmd --version 2>&1 || true)"
    exit 1
  fi

  if ! confirm_install; then
    err "Python ${MIN_VERSION[0]}.${MIN_VERSION[1]}+ was not found in PATH."
    err "Install Python from https://www.python.org/downloads/ and run make run again."
    exit 1
  fi

  install_python
  refresh_path

  if cmd="$(python_cmd)" && version_ok "$cmd"; then
    log "Python installed: $($cmd --version)"
    write_marker
    exit 0
  fi

  err "Python installation finished, but python3 is still not available in PATH."
  err "Open a new terminal or add Python to PATH, then run make run again."
  exit 1
}

main "$@"
