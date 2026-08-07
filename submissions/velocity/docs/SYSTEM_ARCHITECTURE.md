# System Architecture

## Overview

PromptShield AI is a four-component system that shares one backend and one
detection pipeline: the **Browser Extension**, the **PromptShield CLI**
(`psh`), the **FastAPI Backend & Mutagent Engine**, and the **React Admin
Dashboard**. The extension and the CLI each have their own thin API
contract (`POST /api/scan` and `POST /api/cli/scan` respectively), but both
routers delegate to the exact same `mutagent.engine.InvestigationEngine` —
there is no duplicated detection, policy, or audit logic between the two
clients.

```
Browser Extension  --POST /api/scan----->  FastAPI Backend  -->  MySQL 8.4
        ^                                        |
        |                                        v
   ChatGPT / Claude /                    Mutagent InvestigationEngine
   Gemini page DOM                       (5-stage multi-agent pipeline,
                                          see below)
PromptShield CLI    --POST /api/cli/scan-^         ^
   (psh claude/gemini)                             |
        ^                                          |
        |                                          |
   Claude CLI / Gemini CLI binary                   |
                                                     |
Admin Dashboard  --GET/POST/PATCH/DELETE /api/*-->--+--> MySQL 8.4
```

There is no message queue, no cache layer, and no separate worker process.
Every scan runs synchronously inside the FastAPI request handler and
returns a decision in the same HTTP response — deliberately, per the
project's "no Redis/Kafka/Docker/Kubernetes" constraint. At the traffic
volumes a single organization generates, synchronous in-process scanning
is simpler to reason about and fast enough (each detector is a few
milliseconds of regex/rule evaluation; the only stage with real latency is
the optional OpenRouter semantic classifier, which is skipped entirely
when `OPENROUTER_API_KEY` is unset).

## The Detection Pipeline: Mutagent InvestigationEngine

The primary entry point for every scan — from either client — is
`ai/pipeline.py::run_pipeline_for_user()`, which delegates to
`mutagent/engine.py::InvestigationEngine`. The engine auto-discovers every
`BaseAnalyzer` subclass under `mutagent/analyzers/` and executes them
according to the fixed workflow graph in `mutagent/workflow.py`:

1. **Stage 1 — `ContextAnalyzer`** (sequential): resolves identity/context
   metadata for the investigation (user, target site, prompt length).
2. **Stage 2 — `FileIntelAnalyzer`** (sequential): checks each uploaded
   file's extension against the org's `allowed_file_types` allow-list,
   assesses *identity* risk (`ai/file_risk.py` — e.g. a bare `.env` or
   `id_rsa` file is inherently risky regardless of content), and extracts
   text (`ai/file_scanner.py`) for the content analyzers in Stage 3.
3. **Stage 3 — four analyzers in parallel** (`ThreadPoolExecutor`, each
   analyzer individually timeboxed — `DEFAULT_ANALYZER_TIMEOUT_SECONDS`):
   - **`PiiAnalyzer`** — wraps Presidio (`presidio_detector.py`), spaCy NER
     (`spacy_detector.py`), and the PII-relevant regex patterns (email,
     phone, credit card) from `regex_detector.py`.
   - **`SecretsAnalyzer`** — wraps `detect-secrets` (`secret_detector.py`,
     a curated plugin set excluding entropy-based detectors — see Known
     Limitations) and the credential-relevant regex patterns (AWS/GitHub/
     OpenAI/Anthropic/etc. API keys, JWTs, passwords, DB connection
     strings) from `regex_detector.py`.
   - **`InjectionAnalyzer`** — jailbreak / prompt-override pattern
     matching.
   - **`ComplianceAnalyzer`** — the admin-configured `CompanyKeyword` list
     plus the source-code heuristic detector (`code_detector.py`).
   Each analyzer also re-runs its own detectors against every uploaded
   file's extracted text (tagged `[file:<filename>]` in the resulting
   findings), not just the prompt.
4. **Stage 4 — `RiskFusionAnalyzer`** (sequential): aggregates every
   analyzer's findings into one weighted overall score, using
   configurable per-analyzer weights (`mutagent/models.py::
   DEFAULT_RISK_WEIGHTS`, overridable per-org from Settings → Risk
   Weights).
5. **Stage 5 — `DecisionAnalyzer`** (sequential): combines the risk score
   with any matching `Policy` (`ai/policy_engine.py` — an explicit policy
   match always wins over the default severity-based action) into the
   final `ALLOW` / `WARN` / `REDACT` / `BLOCK` decision, redacts the
   prompt if the decision is `REDACT`, and — separately — recomputes each
   attached file's *own* `action`/`risk` from just that file's tagged
   findings, so a batch upload can hold back only the risky attachment
   instead of vetoing every file in the request.

**Fault isolation**: every detector call is wrapped so an unexpected
exception in any single detector degrades that one detector to a neutral
no-op result instead of crashing the whole scan; at the analyzer level, a
timeout or unhandled exception in Stage 3 is caught, recorded as
`TIMEOUT`/`FAILED` in the investigation trace, and the remaining analyzers
still complete. A security tool that fails a *legitimate* prompt because
of its own bug is worse than one that logs the failure and keeps scanning
with the other analyzers.

Every detector still returns the same `DetectionResult` shape
(`backend/schemas/detection.py`): `detector`, `severity`, `score`,
`matches: list[Match]`, `recommendation`, `reason`. The underlying
detector functions in `ai/*.py` (`regex_detector.py`,
`presidio_detector.py`, `spacy_detector.py`, `code_detector.py`,
`keyword_detector.py`, `secret_detector.py`, `file_scanner.py`,
`semantic_classifier.py`) are unchanged from earlier milestones and are
called directly by the Mutagent analyzers above — `ai/pipeline.py` also
still exposes a `run_pipeline()` legacy sequential path (preserved for any
direct callers and for the existing unit tests that import its helpers
directly), but the FastAPI routers (`routers/scan.py`, `routers/cli.py`)
both call `run_pipeline_for_user()`, which always goes through the
Mutagent engine described above.

Finally, the **Audit Logger** (`services/audit_service.py`) writes one
`AuditLog` row per scan (regardless of which client produced it) — this is
what every dashboard card, chart, and Prompt Logs row reads from. The
Mutagent engine additionally persists a richer trace across the
`investigations`, `agent_executions`, and `timeline_events` tables (see
`docs/DATABASE_SCHEMA.md`), linked to the `audit_logs` row by a shared UUID,
which powers the Security Investigations Console's DAG/gauge/evidence
views.

## Request Flow (a single scan)

**Browser Extension**:
1. Employee types a prompt in ChatGPT/Claude/Gemini and hits send.
2. The content script (`browser-extension/src/content/index.ts`)
   intercepts the submit event, cancels it, and calls
   `POST /api/scan` with the prompt text, the site name, and any attached
   files.
3. `routers/scan.py` authenticates the JWT, runs the Mutagent pipeline
   described above, writes the `AuditLog` row (and investigation trace),
   and returns a `ScanResponse` (`decision`, `risk`, `score`, `reason`,
   `sanitized_prompt`, `findings`, `file_findings`).
4. The content script acts on `decision`: `ALLOW` re-submits silently;
   `WARN` shows a modal; `REDACT` replaces the textbox content and waits
   for a manual re-send (which triggers a fresh scan); `BLOCK` shows a
   modal and never re-submits.

**PromptShield CLI (`psh`)**:
1. A developer runs `psh claude "..."` or `psh gemini "..."` (optionally
   with `-f <file>` attachments), or types into the interactive `> `
   session.
2. `cli/backend.py::BackendClient` calls `POST /api/cli/scan` with the
   same shape (`prompt`, `site`, `files`).
3. `routers/cli.py` resolves the calling user (Bearer JWT if provided,
   otherwise the org's default admin/active user for local single-user
   usage), runs the identical Mutagent pipeline, writes the same
   `AuditLog`/investigation trace tables under provider name `"Claude CLI"`
   or `"Gemini CLI"`, and returns the same `ScanResponse` shape.
4. `cli/main.py` enforces the decision: `ALLOW`/`WARN`(confirmed)/`REDACT`
   launch the real `claude`/`gemini` binary (via `cli/providers/`);
   `BLOCK` never launches it.

**Admin Dashboard** (either client's scans):
The dashboard, on its own schedule (page load / TanStack Query refetch),
calls the read-only `/api/dashboard`, `/api/analytics`, `/api/prompt-logs`,
`/api/policies`, `/api/employees`, `/api/settings`, `/api/investigations`
endpoints, all of which run live SQL aggregates against the same
`audit_logs`/`investigations` tables both clients write to — a CLI scan
and a browser scan are indistinguishable to the dashboard beyond the
`website`/`target_ai` field.

## Production Hardening (Milestone 6)

A staff-engineer-level review of the whole codebase (backend, dashboard,
extension, database, docs) turned up and fixed a handful of real issues
before this MVP could be called production-ready:

- **Critical**: `POST /api/auth/register` accepted a client-supplied
  `role` field, letting anyone self-register as an admin. Fixed - public
  registration now always creates an employee account.
- **High**: no per-detector fault isolation in the pipeline (see above), no
  file-upload size/count limits on `/api/scan` (DoS via oversized base64
  payloads), and the extension's `scanPrompt()` failed open on *any*
  non-2xx response - including 401, which meant an expired session
  silently meant zero protection instead of prompting re-login.
- **Medium**: missing indexes on `audit_logs.website/action/risk` (see
  `docs/DATABASE_SCHEMA.md`), the `User.extension_status` DB column being
  permanently stale on `/api/auth/me` while `/api/employees` computed it
  correctly, unthrottled `/api/auth/login`/`register` (brute-force risk),
  search inputs on the Prompt Logs and Employees pages firing a network
  request on every keystroke instead of debouncing, and the Drawer/
  ConfirmDialog/PolicyFormModal components each reimplementing a different
  (and incomplete) subset of modal accessibility behavior.
- **Low**: the identical `SEVERITY_RANK` dict was copy-pasted into five
  different detector files instead of defined once.

See `README.md`'s changelog and the Milestone 6 production-readiness
report for the full list, including the handful of items that were
reviewed and deliberately left alone (e.g. JWT stored in
`chrome.storage.local` is a real but unavoidable Manifest V3 constraint,
not a code bug).

## CLI Integration Hardening

Manual end-to-end verification of the PromptShield CLI surfaced one real
bug in the Mutagent engine, fixed since:

- **`FileFindingSummary` computed before content analysis ran**: each
  uploaded file's own `action`/`risk` (`schemas/scan.py::
  FileFindingSummary` — what the extension and CLI use to gate that
  specific attachment, independent of the overall prompt decision) was
  built by `FileIntelAnalyzer` in Stage 2, before the Stage 3 content
  analyzers (`SecretsAnalyzer`, `PiiAnalyzer`, `InjectionAnalyzer`,
  `ComplianceAnalyzer`) had run. A file whose *only* risk was
  content-based — e.g. a plain `.txt` containing leaked AWS/OpenAI keys —
  stayed permanently stamped `ALLOW` / `"No detectors ran"` in its
  per-file summary, even though the overall scan decision correctly came
  back `BLOCK`. Fixed in `mutagent/analyzers/decision_analyzer.py`: Stage 5
  now recomputes each file's `risk`/`score`/`action`/`reason` from its
  `[file:<filename>]`-tagged findings once all content analyzers have run,
  using the same `assess_risk`/`evaluate_policies`/`decide` calls the rest
  of the pipeline already uses.

## Why no Redis/Kafka/Kubernetes

The project's constraints (no Redis, Docker, Alembic, Kafka, or
Kubernetes) push every piece of state into MySQL and every computation
into the FastAPI request/response cycle. This keeps local setup to
"install Python deps, install Node deps, create one database, run
`seed.py`" — appropriate for a hackathon MVP evaluated by people who don't
want to stand up infrastructure to try it. See `docs/BUSINESS_MODEL.md`
for how this would evolve for a production multi-tenant deployment.
