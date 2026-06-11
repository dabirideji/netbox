# API Reference

The backend exposes a small localhost JSON/SSE API from the Python standard-library HTTP server. All timestamps are Unix epoch milliseconds and are rendered in the browser’s local timezone.

## Base URL

```text
http://127.0.0.1:4177
```

`make run` also starts Vite on `http://127.0.0.1:5177`, which proxies `/api/*` and `/events` to the backend.

## Query Parameters

History and incident endpoints share bounded date filters:

| Parameter | Type | Required | Notes |
| --- | --- | --- | --- |
| `from` | integer | No | Inclusive epoch-ms lower bound. |
| `to` | integer | No | Inclusive epoch-ms upper bound. Must be greater than or equal to `from`. |
| `points` | integer | No | History point count, `1` to `2000`. Defaults to `360`. |
| `limit` | integer | No | Incident page size, `1` to `500`. Defaults to `50`. |
| `offset` | integer | No | Incident offset, `0` to `100000`. Defaults to `0`. |

Invalid query values return `400` with a structured error payload:

```json
{
  "code": "API-4001",
  "error": "from must be less than or equal to to"
}
```

Stable response codes are defined in `backend/src/netbox/responses.py` and mirrored in `frontend/src/responses.ts`.

## `GET /api/status`

Returns the latest in-memory monitor summary.

```json
{
  "startedAt": 1781090000000,
  "now": 1781090060000,
  "endsAt": null,
  "intervalMs": 1000,
  "durationMs": null,
  "overallStatus": "degraded",
  "diagnosis": "Gateway is healthy, but external targets are degraded. Likely upstream/ISP jitter.",
  "network": {
    "name": "Office WiFi",
    "ssid": "Office WiFi",
    "interface": "en0",
    "service": "Wi-Fi"
  },
  "targets": [],
  "events": [],
  "sampleCount": 60
}
```

## `GET /api/history`

Returns aggregated persisted history for the overview chart.

```text
/api/history?points=360&from=1781090000000&to=1781093600000
```

```json
{
  "from": 1781090000000,
  "to": 1781093600000,
  "points": [
    {
      "at": 1781090000000,
      "severity": 0,
      "avgLatencyMs": 12.4,
      "failurePct": 0
    }
  ]
}
```

Monitor status and severity mapping:

| Status | Code | Severity |
| --- | --- | --- |
| `operational` | `MON-000` | `0` |
| `degraded` | `MON-110` | `1` |
| `down` | `MON-120` | `2` |
| `unknown` | `MON-900` | `0` |

## `GET /api/targets/history`

Returns persisted history grouped by target for historical target breakdowns.

```text
/api/targets/history?points=180
```

```json
{
  "from": null,
  "to": null,
  "targets": [
    {
      "id": "gateway",
      "host": "192.168.1.1",
      "label": "Local Gateway",
      "scope": "gateway",
      "type": "host",
      "protocol": "icmp",
      "points": [
        {
          "at": 1781090000000,
          "severity": 0,
          "status": "operational",
          "ok": true,
          "latencyMs": 8.6,
          "error": null
        }
      ]
    }
  ]
}
```

## Target CRUD

Targets are stored in SQLite after first startup. `config/targets.json` seeds defaults only when an id is absent.

### `GET /api/targets`

Returns all configured targets.

### `POST /api/targets`

Creates a target. The backend validates common fields and protocol-specific config.

```json
{
  "label": "API health",
  "type": "api",
  "protocol": "https",
  "scope": "external",
  "group": "Production",
  "environment": "local",
  "enabled": true,
  "intervalMs": 1000,
  "timeoutMs": 900,
  "config": {
    "url": "https://example.com/health",
    "method": "GET",
    "expectedStatus": 200,
    "keyword": "ok"
  }
}
```

Supported protocols:

- `http` / `https`: `url`, `method`, `headers`, `expectedStatus`, optional `keyword`.
- `tcp`: `host`, `port`.
- `icmp`: `host`.
- `dns`: `name`, `recordType`, optional `expectedValue`.

### `GET /api/targets/{id}`

Returns one target.

### `PATCH /api/targets/{id}`

Partially updates one target. SQLite remains the source of truth after seeding.

### `DELETE /api/targets/{id}`

Deletes the target configuration. Historical check rows are retained.

### `POST /api/targets/preview-check`

Runs one immediate check from an unsaved target payload without creating or updating the target.

```json
{
  "label": "API health",
  "type": "api",
  "protocol": "https",
  "scope": "external",
  "group": "Default",
  "environment": "local",
  "enabled": true,
  "intervalMs": 5000,
  "timeoutMs": 10000,
  "config": {
    "url": "https://example.com/health",
    "method": "GET",
    "expectedStatus": 200
  }
}
```

Response:

```json
{
  "preview": true,
  "status": "operational",
  "severity": 0,
  "result": {
    "id": "api-health-example-com",
    "host": "example.com",
    "label": "API health",
    "scope": "external",
    "type": "api",
    "protocol": "https",
    "ok": true,
    "latencyMs": 42.1,
    "checkedAt": 1781090060000,
    "durationMs": 41,
    "error": null
  }
}
```

### `POST /api/targets/{id}/check-now`

Runs one immediate check and persists the result.

### `GET /api/targets/{id}/results`

Returns raw check results newest-first. Supports `from`, `to`, `limit`, and `offset`.

## `GET /api/incidents`

Returns durable incident windows derived from status transitions.

```json
{
  "from": null,
  "to": null,
  "limit": 50,
  "offset": 0,
  "total": 1,
  "incidents": [
    {
      "id": 1,
      "targetId": "gateway",
      "targetLabel": "Local Gateway",
      "openedAt": 1781090060000,
      "resolvedAt": null,
      "status": "open",
      "message": "Local Gateway changed from operational to degraded"
    }
  ]
}
```

## `GET /api/events`

Returns status transition incidents newest-first with pagination metadata.

```text
/api/events?limit=10&offset=20
```

```json
{
  "from": null,
  "to": null,
  "limit": 10,
  "offset": 20,
  "total": 72,
  "events": [
    {
      "at": 1781090060000,
      "targetId": "cloudflare",
      "targetLabel": "Cloudflare DNS",
      "from": "operational",
      "to": "degraded",
      "message": "Cloudflare DNS changed from operational to degraded"
    }
  ]
}
```

## `GET /api/speed-tests`

Returns speed-test policy, aggregate stats, and persisted attempts newest-first. Supports the same bounded `from`, `to`, `limit`, and `offset` query parameters.

```text
/api/speed-tests?limit=20&from=1781090000000&to=1781093600000
```

```json
{
  "from": null,
  "to": null,
  "limit": 20,
  "offset": 0,
  "total": 1,
  "stats": {
    "avgDownloadMbps": 121.4,
    "avgUploadMbps": 42.8,
    "minLatencyMs": 18.2,
    "totalRuns": 1,
    "completedRuns": 1
  },
  "policy": {
    "enabled": true,
    "provider": "mlab-ndt7",
    "providerName": "Measurement Lab NDT7",
    "privacyUrl": "https://www.measurementlab.net/privacy/",
    "dataPolicyUrl": "https://www.measurementlab.net/privacy/",
    "metadata": {
      "client_name": "netbox",
      "client_version": "1.0.0"
    },
    "minIntervalMs": 900000,
    "dailyRunLimit": 4,
    "runsLast24h": 1,
    "lastTestedAt": 1781090060000,
    "nextRunAt": 1781090960000,
    "canRun": false
  },
  "tests": [
    {
      "id": 1,
      "testedAt": 1781090060000,
      "provider": "mlab-ndt7",
      "status": "completed",
      "downloadMbps": 121.4,
      "uploadMbps": 42.8,
      "latencyMs": 18.2,
      "jitterMs": 2.1,
      "packetLossPct": null,
      "retransmissionPct": null,
      "durationMs": 22000,
      "serverName": "ndt-server",
      "serverLocation": "Lagos, NG",
      "serverHost": "ndt.example.net",
      "error": null
    }
  ]
}
```

## `POST /api/speed-tests`

Persists one browser-run speed-test attempt. The backend validates body size, required fields, metric ranges, status, and string lengths before writing to SQLite.

```json
{
  "testedAt": 1781090060000,
  "provider": "mlab-ndt7",
  "status": "completed",
  "downloadMbps": 121.4,
  "uploadMbps": 42.8,
  "latencyMs": 18.2,
  "jitterMs": 2.1,
  "packetLossPct": null,
  "retransmissionPct": null,
  "durationMs": 22000,
  "serverName": "ndt-server",
  "serverLocation": "Lagos, NG",
  "serverHost": "ndt.example.net",
  "error": null
}
```

Successful responses return `201`:

```json
{
  "test": { "id": 1 },
  "policy": { "canRun": false }
}
```

## `GET /api/preferences`

Returns persisted UI preferences from SQLite. The payload is a JSON object stored under `data`.

```json
{
  "data": {
    "dashboard_sections_collapsed": {
      "timeline": true,
      "speedTest": false
    },
    "timeline_range": {
      "from": "2026-06-10T00:00",
      "to": "2026-06-10T23:59"
    },
    "event_page": 1,
    "speed_test_page": 1
  }
}
```

When no preferences exist yet, `data` is an empty object.

## `PATCH /api/preferences`

Merges one or more preference keys into the stored JSON object and returns the updated document.

```json
{
  "dashboard_sections_collapsed": {
    "timeline": true,
    "incidentLog": false
  }
}
```

Response:

```json
{
  "data": {
    "dashboard_sections_collapsed": {
      "timeline": true,
      "incidentLog": false
    }
  }
}
```

Unknown keys are preserved. The body must be a JSON object.

## `GET /api/storage`

Returns configured retention limits and current SQLite usage.

```json
{
  "autoPrune": true,
  "limits": {
    "maxDatabaseBytes": 52428800,
    "maxIncidents": 10000,
    "maxPingSamples": 500000,
    "maxSpeedTests": 1000
  },
  "usage": {
    "databaseBytes": 204800,
    "incidents": 42,
    "pingSamples": 12000,
    "speedTests": 3
  },
  "percentUsed": {
    "database": 0.4,
    "incidents": 0.4,
    "pingSamples": 2.4,
    "speedTests": 0.3
  }
}
```

## `POST /api/storage/clear`

Deletes persisted rows for one scope. Valid scopes: `incidents`, `ping`, `speedTests`, or `all`.

```json
{ "scope": "incidents" }
```

Response:

```json
{
  "deleted": {
    "incidents": 42,
    "pingSamples": 0,
    "speedTests": 0
  },
  "stats": {
    "autoPrune": true,
    "limits": { "maxIncidents": 10000 },
    "usage": { "incidents": 0 },
    "percentUsed": { "incidents": 0 }
  }
}
```

Invalid scopes return `400`.

## `GET /api/wallpaper`

Returns one curated nature landscape image proxied from the Pexels API. The backend reads `PEXELS_API_KEY` from the environment and keeps the key off the frontend bundle.

```json
{
  "url": "https://images.pexels.com/photos/example.jpeg",
  "photographer": "Jane Doe",
  "photoUrl": "https://www.pexels.com/photo/example/"
}
```

If the key is missing or Pexels is unavailable, the endpoint returns `400`:

```json
{ "error": "PEXELS_API_KEY is not configured" }
```

## `GET /events`

Streams server-sent events for live status and incident updates.

Status payload:

```text
data: {"type":"status","summary":{...}}
```

Incident payload:

```text
data: {"type":"event","event":{...}}
```

Speed-test payload:

```text
data: {"type":"speedTest","test":{...}}
```

Heartbeat comments are emitted periodically to keep long-lived browser connections alive:

```text
: heartbeat
```
