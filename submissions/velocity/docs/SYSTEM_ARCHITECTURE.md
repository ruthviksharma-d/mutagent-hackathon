# System Architecture

## Overview

PromptShield AI is a three-component system that shares one contract: the
`POST /api/scan` request/response shape. Everything else — the extension's
UI, the dashboard's tables and charts, the policy engine's rules — is built
on top of that one contract, which keeps the three components loosely
coupled while still acting as one product.

```
Browser Extension  --POST /api/scan-->  FastAPI Backend  -->  MySQL 8.4
        ^                                     |
        |                                     v
   ChatGPT / Claude /                  Detection Pipeline
   Gemini page DOM                     (9 stages, see below)

Admin Dashboard  --GET/POST/PATCH/DELETE /api/*-->  FastAPI Backend --> MySQL 8.4
```

There is no message queue, no cache layer, and no separate worker process.
Every scan runs synchronously inside the FastAPI request handler and
returns a decision in the same HTTP response — deliberately, per the
project's "no Redis/Kafka/Docker/Kubernetes" constraint. At the traffic
volumes a single organization generates, synchronous in-process scanning
is simpler to reason about and fast enough (each stage is a few
milliseconds of regex/rule evaluation; the only stage with real latency is
the optional OpenRouter semantic classifier, which is skipped entirely
when `OPENROUTER_API_KEY` is unset).

## The Detection Pipeline

`backend/ai/pipeline.py` orchestrates nine stages in a fixed order. Every
stage returns the same `DetectionResult` object
(`backend/schemas/detection.py`): `detector`, `severity`, `score`,
`matches: list[Match]`, `recommendation`, `reason`. This uniform shape is
what lets the Risk Engine aggregate across all nine stages without
special-casing any individual detector.

1. **Normalizer** (`normalizer.py`) — lowercases, strips control
   characters, and collapses whitespace so downstream regex/NLP stages see
   consistent input regardless of how the prompt was formatted in the
   browser.
2. **Regex Detector** (`regex_detector.py`) — pattern matches for emails,
   phone numbers, URLs, credit cards, AWS access keys, GitHub/GitLab
   tokens, JWTs, and IP addresses.
3. **Presidio Detector** (`presidio_detector.py`) — Microsoft Presidio
   Analyzer for PII entities (PERSON, LOCATION, CREDIT_CARD, and more).
   Degrades to a neutral no-op result if the spaCy model backing it isn't
   installed (see the README's Known Limitations).
4. **spaCy Detector** (`spacy_detector.py`) — a second NER pass used as a
   lower-confidence corroborating signal, same degrade-gracefully behavior.
5. **Source Code Detector** (`code_detector.py`) — heuristic detection of
   Python/JavaScript/SQL/etc. syntax pasted into a prompt (keyword
   density, bracket balance, common language idioms).
6. **Company Keyword Detector** (`keyword_detector.py`) — matches the
   admin-configured `CompanyKeyword` table (case-insensitive substring
   match against enabled keywords).
7. **detect-secrets Detector** (`secret_detector.py`) — runs
   `detect-secrets` with a curated 24-plugin set (deliberately excluding
   entropy-based plugins — see Known Limitations in the README) to find
   live credentials: private keys, Slack/Stripe/Twilio/SendGrid tokens,
   and more.
8. **File Scanner** (`file_scanner.py`) — when a prompt includes attached
   files, extracts text from PDFs (`pypdf`), Word docs (`python-docx`),
   spreadsheets (`openpyxl`), images (`pytesseract` OCR), and YAML/config
   files, then re-runs the relevant detectors against the extracted text.
9. **Semantic Classifier** (`semantic_classifier.py`, optional) — calls
   OpenRouter for a holistic "does this look like an intent to exfiltrate
   sensitive data" judgment. Only runs if `OPENROUTER_API_KEY` is set.

**Fault isolation (Milestone 6 hardening)**: every detector call in
`_run_deterministic_detectors` is wrapped by a small `_safe_call` helper
that catches any unexpected exception and degrades that one detector to a
neutral no-op result instead of letting it crash the entire `/api/scan`
request. Before this, a bug in any single detector (a malformed-unicode
edge case, a third-party library quirk) took down the whole scan with a
500 and no audit log entry - a security tool that fails a *legitimate*
prompt because of its own bug is worse than one that logs the failure and
keeps scanning with the other eight detectors.

After all nine stages run, three more engines turn the raw findings into a
decision:

- **Policy Engine** (`policy_engine.py`) — loads every enabled `Policy`
  row from MySQL, maps each detector's individual `Match.label` values to
  fine-grained categories (`email`, `api_key`, `ssh_key`, `pii`,
  `source_code`, `company_keyword`, `secrets`, or the catch-all `all`),
  and evaluates policies in ascending `priority` order. The first matching
  enabled policy wins.
- **Risk Engine** (`risk_engine.py`) — if no policy explicitly fires,
  aggregates every detector's severity/score into one overall risk score
  and severity (`NONE`/`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`).
- **Decision Engine** (`decision_engine.py`) — combines the policy result
  (if any) and the risk score into one final `ALLOW` / `WARN` / `REDACT` /
  `BLOCK` decision.

If the decision is `REDACT`, the **Redactor** (`redactor.py`) replaces
every matched span in the prompt with a typed placeholder (e.g.
`[REDACTED_EMAIL]`) before the response is returned — the extension never
receives the original sensitive text for a REDACT decision.

Finally, the **Audit Logger** (`services/audit_service.py`) writes one
`AuditLog` row per scan — this is the single source of truth every
dashboard page and analytics chart reads from.

## Request Flow (a single scan)

1. Employee types a prompt in ChatGPT/Claude/Gemini and hits send.
2. The content script (`browser-extension/src/content/index.ts`)
   intercepts the submit event, cancels it, and calls
   `POST /api/scan` with the prompt text, the site name, and any attached
   files.
3. `routers/scan.py` authenticates the JWT, runs the pipeline described
   above, writes the `AuditLog` row, and returns a `ScanResponse`
   (`decision`, `risk`, `score`, `reason`, `sanitized_prompt`, `findings`).
4. The content script acts on `decision`: `ALLOW` re-submits silently;
   `WARN` shows a modal; `REDACT` replaces the textbox content and waits
   for a manual re-send (which triggers a fresh scan); `BLOCK` shows a
   modal and never re-submits.
5. The admin dashboard, on its own schedule (page load / TanStack Query
   refetch), calls the read-only `/api/dashboard`, `/api/analytics`,
   `/api/prompt-logs`, `/api/policies`, `/api/employees`, `/api/settings`
   endpoints, all of which run live SQL aggregates against the same
   `audit_logs` table step 3 wrote to.

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

## Why no Redis/Kafka/Kubernetes

The project's constraints (no Redis, Docker, Alembic, Kafka, or
Kubernetes) push every piece of state into MySQL and every computation
into the FastAPI request/response cycle. This keeps local setup to
"install Python deps, install Node deps, create one database, run
`seed.py`" — appropriate for a hackathon MVP evaluated by people who don't
want to stand up infrastructure to try it. See `docs/BUSINESS_MODEL.md`
for how this would evolve for a production multi-tenant deployment.
