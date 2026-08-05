# Database Schema

PromptShield AI uses MySQL 8.4 with five tables, all defined as SQLAlchemy
2.0 models under `backend/models/` and created automatically via
`Base.metadata.create_all()` on backend startup — there is no migration
tool (Alembic is explicitly excluded per the project's constraints). All
primary keys are UUID strings (`String(36)`) generated in Python via
`uuid.uuid4()`, not auto-increment integers, so IDs are safe to expose in
API responses and stable across environments.

## `users`

Employees, security analysts, and admins all live in one table,
distinguished by `role`.

| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `email` | `String(255)` | unique, indexed |
| `full_name` | `String(255)` | |
| `hashed_password` | `String(255)` | bcrypt via Passlib |
| `role` | `Enum(admin, security_analyst, employee)` | default `employee` |
| `department` | `String(120)` nullable | free text, used for department-level analytics |
| `is_active` | `Boolean` | default `true` |
| `extension_status` | `Enum(active, inactive, not_installed)` | default `not_installed` — see note below |
| `prompt_count` | `Integer` | incremented on every scan attributed to this user |
| `violation_count` | `Integer` | incremented on every non-`ALLOW` scan |
| `created_at` / `updated_at` | `DateTime` | UTC |

**Note on `extension_status`**: the column exists on the model, but
nothing in the codebase ever writes to it — it always holds its default
(`not_installed`). Every API that returns an `extension_status` value
(`GET /api/employees`, and — as of Milestone 6 — `POST /api/auth/register`,
`POST /api/auth/login`, `GET /api/auth/me`) computes it live instead, via
`services/employee_service.py`'s `_derive_extension_status` /
`get_live_extension_status`: "active" / "inactive" / "not_installed" based
on whether `audit_logs` has a recent row for that user. This avoids
requiring the extension to implement a heartbeat message the backend never
asked for in Milestone 3, while still giving the dashboard (and the user's
own profile) an accurate signal. Earlier in the project only the Employees
API computed this live, while `/api/auth/me` returned the raw (always
stale) DB column — that inconsistency was fixed in Milestone 6.

## `audit_logs`

The system of record for every scan. Every dashboard card, chart, and
table row traces back to this table.

| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `user_id` | `String(36)` FK → `users.id` | implicitly indexed by MySQL InnoDB as a foreign key |
| `website` | `String(50)`, indexed | `ChatGPT` \| `Claude` \| `Gemini` |
| `original_prompt` | `Text` | the prompt as typed |
| `sanitized_prompt` | `Text` | equals `original_prompt` unless the decision was `REDACT`/`BLOCK` |
| `risk` | `String(20)`, indexed | `NONE` \| `LOW` \| `MEDIUM` \| `HIGH` \| `CRITICAL` |
| `score` | `Integer` | 0-100 aggregate risk score |
| `action` | `String(20)`, indexed | `ALLOW` \| `WARN` \| `REDACT` \| `BLOCK` |
| `reason` | `Text` | human-readable explanation, also parsed client-side for the Explainable AI panel |
| `triggered_rules` | `JSON` | list of `{detector, severity, score, reason}` — one entry per detector that fired |
| `created_at` | `DateTime`, indexed | UTC, indexed for the dashboard's date-range and daily-activity queries |

**Milestone 6 hardening**: `website`, `risk`, and `action` were added as
indexes — the Dashboard, Prompt Logs, and Analytics pages all filter or
`GROUP BY` these columns on every request. At demo-seed scale (a few
hundred rows) this makes no visible difference, but an unindexed
`GROUP BY` becomes a full table scan once a real org's `audit_logs` table
reaches tens of thousands of rows. Since this project has no Alembic,
`Base.metadata.create_all()` only creates *new* tables — it will not add
these indexes to a database that was already created by an earlier
version. If you have an existing deployment, add them manually:

```sql
ALTER TABLE audit_logs ADD INDEX ix_audit_logs_website (website);
ALTER TABLE audit_logs ADD INDEX ix_audit_logs_action (action);
ALTER TABLE audit_logs ADD INDEX ix_audit_logs_risk (risk);
```

## `policies`

Admin-authored rules that override the Risk Engine's default behavior for
a specific detection category.

| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `name` | `String(150)` | |
| `description` | `Text` | |
| `priority` | `Integer` | lower is evaluated first; default `100` |
| `detection_type` | `String(50)` | one of `email`, `phone`, `api_key`, `pii`, `ssh_key`, `source_code`, `company_keyword`, `secrets`, `all`, etc. — matched against `Match.label` categories, not raw detector names |
| `action` | `String(20)` | `ALLOW` \| `WARN` \| `REDACT` \| `BLOCK` |
| `enabled` | `Boolean` | default `true` |
| `created_at` / `updated_at` | `DateTime` | UTC |

## `company_keywords`

A flat, admin-managed list consumed by the Company Keyword Detector.

| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `keyword` | `String(200)` | unique |
| `enabled` | `Boolean` | default `true` |
| `created_at` | `DateTime` | UTC |

## `org_settings`

A singleton table — exactly one row per deployment, created lazily on
first read by `services/settings_service.get_or_create_settings()`.

| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `organization_name` | `String(200)` | default `Acme Corp` |
| `risk_threshold` | `Integer` | default `70` — informational threshold surfaced on the Settings page |
| `supported_websites` | `JSON` | default `["ChatGPT", "Claude", "Gemini"]` |
| `allowed_file_types` | `JSON` | default `["pdf", "docx", "csv", "xlsx", "txt", "png", "jpg", "jpeg"]` |
| `theme_default` | `String(10)` | default `light` — org-wide preference, independent of each browser's own per-device `ThemeContext` |
| `updated_at` | `DateTime` | UTC |

## Entity Relationships

```
users (1) ───< audit_logs (many)      one employee generates many scan records
policies                              standalone — referenced by name in audit_logs.reason, not FK'd
company_keywords                      standalone — read by the Company Keyword Detector
org_settings                          singleton — no relationships
```

There is intentionally no foreign key from `audit_logs` to `policies`:
the policy that fired (if any) is recorded as free text inside `reason`
(e.g. `"Policy 'Block Cloud/API Keys' triggered by detection type
'api_key'."`), since a policy can be edited or deleted after the fact and
the audit log should preserve what happened at scan time, not a live
reference that could later point to a modified or missing row.
