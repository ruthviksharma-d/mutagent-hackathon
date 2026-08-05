# API Documentation

Base URL (local development): `http://localhost:8000`

All endpoints except `/api/health`, `/api/auth/register`, and
`/api/auth/login` require a `Authorization: Bearer <jwt>` header. Most
read endpoints require the `admin` or `security_analyst` role
(`require_analyst_or_admin`); all write endpoints (policy/keyword
create/update/delete, settings update) require `admin`
(`require_admin`) — see `backend/auth/dependencies.py`.

Interactive, always-up-to-date docs are also available at
`GET /docs` (Swagger UI) and `GET /redoc` once the backend is running.

## Authentication — `/api/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | none | Creates a new **employee** account. Returns a `Token`. The request body has no `role` field — self-registration can never create an admin or security_analyst account (see Security note below). Rate-limited: 10 attempts/minute per IP. |
| `POST` | `/api/auth/login` | none | `{ email, password }` → `Token` (JWT access token). Rate-limited: 10 attempts/minute per IP. |
| `GET` | `/api/auth/me` | Bearer | Returns the current user's profile, with `extension_status` computed live (not read from the stale DB default). |

The JWT payload includes the user's `id`, `role`, and an `exp` claim. The
extension decodes this client-side to detect expiry (see
`docs/EXTENSION_ARCHITECTURE.md`) — there is no refresh-token endpoint in
this MVP.

**Security note (Milestone 6)**: `POST /api/auth/register` is public and
unauthenticated by design (it's how a new employee gets their first
account), so it must never let the caller choose their own role. An
earlier version accepted a client-supplied `role` field, which meant
anyone could self-register as `"admin"` and receive an admin JWT
immediately — this has been fixed; the endpoint now hardcodes
`role=employee` and the field no longer exists on the request schema.
Provisioning an admin or security_analyst account is an out-of-band
operation (`seed.py`, or a future admin-only "create user" endpoint), not
something a public POST body can request.

Both `/login` and `/register` are rate-limited (10 attempts/minute per
client IP, in-memory — see `middleware/rate_limit.py`) since they're the
only endpoints an attacker can hit without a valid JWT.

## Scan — `/api/scan`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/scan` | Bearer | Runs the full detection pipeline against a prompt. |

**Request** (`ScanRequest`):

```json
{
  "prompt": "string",
  "site": "ChatGPT | Claude | Gemini",
  "files": [{ "filename": "string", "content_base64": "string" }]
}
```

Limits (Milestone 6 hardening — an unbounded file list/size was a memory-
exhaustion DoS vector): `prompt` max 50,000 characters, at most 5 files per
request, each file's base64 payload capped at ~10MB decoded. Requests
exceeding these limits get a `422` with a Pydantic validation error.

**Response** (`ScanResponse`):

```json
{
  "decision": "ALLOW | WARN | REDACT | BLOCK",
  "risk": "NONE | LOW | MEDIUM | HIGH | CRITICAL",
  "score": 0,
  "reason": "string",
  "sanitized_prompt": "string",
  "findings": [
    { "detector": "string", "severity": "string", "score": 0, "reason": "string" }
  ]
}
```

This is the one contract every other part of the system is built around —
`findings`/`reason` drive the extension's Explainable AI panel, and the
whole response (plus the identity of the caller) is what gets written to
`audit_logs`.

## Dashboard — `/api/dashboard`

| Method | Path | Role | Description |
|---|---|---|---|
| `GET` | `/api/dashboard/summary` | analyst/admin | One call powers every Dashboard card, chart, and the recent-activity table: `security_score`, `total_prompts`, `allowed`/`warned`/`redacted`/`blocked`, `active_employees`, `protected_websites`, `daily_activity[]`, `risk_distribution[]`, `top_violations[]`, `website_usage[]`, `department_usage[]`, `recent_activity[]`. |

## Analytics — `/api/analytics`

| Method | Path | Role | Description |
|---|---|---|---|
| `GET` | `/api/analytics/summary` | analyst/admin | Powers the Analytics page's charts. Shares its SQL aggregation logic with the dashboard endpoint via `services/analytics_service.py` — no duplicated queries. |

## Prompt Logs — `/api/prompt-logs`

| Method | Path | Role | Description |
|---|---|---|---|
| `GET` | `/api/prompt-logs` | analyst/admin | Paginated, filterable, searchable list. Query params: `page`, `page_size`, `search`, `action`, `risk`, `website`, `sort`. |
| `GET` | `/api/prompt-logs/{log_id}` | analyst/admin | Full detail for one log: both prompts, every detector finding, the triggered policy (parsed from `reason`), employee info. |

## Policies — `/api/policies`

| Method | Path | Role | Description |
|---|---|---|---|
| `GET` | `/api/policies` | analyst/admin | List all policies, ordered by priority. |
| `POST` | `/api/policies` | admin | Create a policy. |
| `PATCH` | `/api/policies/{policy_id}` | admin | Partial update (e.g. toggle `enabled`, change `priority`). |
| `DELETE` | `/api/policies/{policy_id}` | admin | Delete a policy. Returns `204`. |

## Employees — `/api/employees`

| Method | Path | Role | Description |
|---|---|---|---|
| `GET` | `/api/employees` | analyst/admin | Directory with `prompt_count`, `violation_count`, and a live-derived `last_active` / `extension_status` computed from recent `audit_logs` rows. Supports a free-text `department` filter (case-insensitive partial match). |

## Settings — `/api/settings`

| Method | Path | Role | Description |
|---|---|---|---|
| `GET` | `/api/settings` | analyst/admin | Returns the singleton `OrgSettings` row (created on first read if missing). |
| `PUT` | `/api/settings` | admin | Update organization name, risk threshold, supported websites, allowed file types, default theme. |
| `GET` | `/api/settings/keywords` | analyst/admin | List company keywords. |
| `POST` | `/api/settings/keywords` | admin | Add a keyword. |
| `PATCH` | `/api/settings/keywords/{keyword_id}` | admin | Toggle enabled / rename. |
| `DELETE` | `/api/settings/keywords/{keyword_id}` | admin | Remove a keyword. Returns `204`. |

## Health — `/api/health`

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | none | Liveness check. Polled by the extension's background service worker every 2 minutes via `chrome.alarms` to drive the popup's Backend Status indicator. |

## Error Format

All error responses follow FastAPI's default shape:

```json
{ "detail": "human-readable message" }
```

`401` for missing/invalid/expired tokens, `403` for an authenticated user
lacking the required role, `404` for a missing resource, `422` for
request validation errors (Pydantic).
