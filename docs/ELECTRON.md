# Desktop app (Electron)

Netbox ships as a local-first desktop app: Electron supervises a bundled Python monitor and loads the dashboard from a single local origin.

## Development

```bash
make desktop
```

This builds `frontend/dist`, installs Electron dependencies, spawns the Python backend on `127.0.0.1:4177`, and opens the dashboard window with a tray icon.

## Packaging

```bash
make package
```

This will:

1. Build `frontend/dist`
2. Bundle the backend with PyInstaller into `dist-backend/netbox-backend`
3. Produce installers under `electron/release/` (`.dmg` on macOS, `.exe` on Windows, AppImage/deb on Linux)

## Runtime layout

```text
Electron main process
  ├── tray click → draggable live-checks popup (`/tray.html`, comfortable or compact dock mode)
  ├── optional full dashboard window from the tray menu
  ├── splash while backend boots
  └── child process: netbox-backend
        ├── serves frontend/dist
        ├── SQLite at app userData/netbox.sqlite3
        └── config from bundled resources/config
```

## Environment

| Variable | Purpose |
| --- | --- |
| `NETBOX_PROJECT_ROOT` | Repo root for `make desktop` |
| `NETBOX_PYTHON` | Python executable for dev backend spawn |
| `NETBOX_AUTO_UPDATE=0` | Disable `electron-updater` checks in packaged builds |

## Code signing

`electron-builder` config is ready for packaging. For distribution outside your machine:

- **macOS:** Apple Developer ID + notarization (`CSC_LINK`, `APPLE_ID`, etc.)
- **Windows:** Authenticode certificate
- **Linux:** optional GPG for package repos

Update `icons/black.png` and `icons/white.png`, then run `make generate-icons` to refresh web, tray, and app icons. Icon generation uses ImageMagick (`magick` or `convert`).
