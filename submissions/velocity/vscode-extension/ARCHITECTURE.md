# PromptShield for VS Code / Antigravity — Architecture

## Where this fits

PromptShield already has three production clients sharing one backend: the Browser Extension, the CLI (`psh`), and the Admin Dashboard. This adds a **fourth client** — the VS Code extension — without touching the analysis/policy logic. It is a thin client: every ALLOW/WARN/REDACT/BLOCK decision comes from the backend's 9-stage analyzer + policy engine, never computed locally.

```
                 ┌──────────────────────────┐
                 │        User (IDE)        │
                 └─────────────┬─────────────┘
                               │ invokes @promptshield chat
                               │ or a PromptShield: ... command
                               ▼
        ┌───────────────────────────────────────────┐
        │   VS Code / Antigravity Extension (thin)   │
        │  interceptor.ts → scanner.ts → backend.ts  │
        │  (captures prompt, history, files, code)   │
        └─────────────────────┬───────────────────────┘
                               │ POST /api/scan (HTTPS/JSON)
                               │ same request shape as
                               │ browser-extension/src/services/api.ts
                               ▼
        ┌───────────────────────────────────────────┐
        │           PromptShield Backend (FastAPI)   │
        │  routers/scan.py, routers/auth.py,         │
        │  routers/vscode.py (new, additive)         │
        └─────────────────────┬───────────────────────┘
                               ▼
        ┌───────────────────────────────────────────┐
        │   Mutagent 9-Stage Analyzer (unchanged)    │
        │  Normalizer → Context → PII → Secrets →    │
        │  Injection → Compliance → FileIntel →      │
        │  RiskFusion → Decision                     │
        └─────────────────────┬───────────────────────┘
                               ▼
        ┌───────────────────────────────────────────┐
        │              Policy Engine                 │
        └─────────────────────┬───────────────────────┘
                               ▼
                 ALLOW / WARN / REDACT / BLOCK
                               │
                               ▼
        ┌───────────────────────────────────────────┐
        │  Extension enforces the decision:          │
        │  ALLOW  → shows result, nothing blocked    │
        │  WARN   → modal w/ findings, user confirms │
        │           (unless strictMode)              │
        │  REDACT → sanitized text substituted       │
        │  BLOCK  → nothing forwarded, reason shown  │
        └─────────────────────┬───────────────────────┘
                               ▼
                 User pastes/sends approved text
                    into Copilot Chat / Antigravity
                    AI panel / any AI tool → LLM
```

## Why interception works this way

VS Code's extension API has no universal hook that intercepts "a prompt about to be sent" for arbitrary third-party AI extensions (Copilot Chat, Antigravity's assistant, Cursor-style tools, etc.) — there is no cross-extension network interception surface. Given that constraint, this extension implements interception the way real VS Code security tools do it:

1. **Chat participant** (`@promptshield`) — the user can invoke PromptShield directly inside VS Code's native Chat view, ask it to scan a draft prompt (with `context.history` supplying prior turns as conversation context), and get an ALLOW/WARN/REDACT/BLOCK verdict before they paste that same text into Copilot Chat, Antigravity's panel, or any other AI surface.
2. **Commands** (`promptshield.scanSelection`, `promptshield.scanClipboardPrompt`, `promptshield.interceptAndSend`, `promptshield.scanActiveFile`) — a fast keyboard/context-menu-driven path: scan selected code, scan clipboard text, or scan-then-copy-the-approved/redacted text back to the clipboard so it's ready to paste into whatever AI tool the user is about to use.
3. **Workspace monitoring** (optional, off by default) — background scanning of opened/saved/new files, independent of any specific prompt, surfaced as VS Code diagnostics (Problems panel) — this catches sensitive content sitting in the workspace itself, not just what's typed into a prompt.

This is documented here explicitly so it's not mistaken for silent network-level interception of Copilot/Antigravity traffic, which VS Code's extension sandboxing does not allow.

## Reused backend surface (no duplicated logic)

| Concern | Endpoint | Notes |
|---|---|---|
| Auth | `POST /api/auth/login`, `GET /api/auth/me` | identical to browser-extension's `services/api.ts` |
| Prompt/file analysis | `POST /api/scan` | same request/response shape as the browser extension; same 9-stage pipeline, same audit logging |
| Policy summary (new) | `GET /api/policies/summary` | new additive endpoint, see below |
| Health | `GET /api/health` | used for the fail-open/fail-closed reachability check |

The extension never re-implements PII/secret/injection detection, risk scoring, or policy evaluation — it only formats a request, sends it, and enforces whatever decision comes back.

## Backend changes (additive only)

- **`backend/routers/vscode.py` (new file)** — adds `GET /api/policies/summary`, a read-only, any-authenticated-role endpoint that returns a minimal `{name, detection_type, action, priority}` list of enabled policies. The existing `GET /api/policies` (admin/security_analyst-only, full CRUD detail) is untouched; this new route exists solely because the VS Code extension runs as whatever role the logged-in user has and only needs enough summary detail to populate its local read-only policy cache/status bar/risk panel display — it never uses this to make a decision itself.
- **`backend/schemas/vscode.py` (new file)** — Pydantic response models for the above (`PolicySummaryItem`, `PolicySummaryResponse`).
- **`backend/main.py`** — one new import + one new `app.include_router(vscode_router.router)` line, additive only.
- **`backend/mutagent/analyzers/decision_analyzer.py`** and **`backend/mutagent/models.py`** / **`backend/mutagent/analyzers/risk_fusion_analyzer.py`** — a pre-existing bug fix surfaced while building/validating the VS Code extension's file-scanning path (see "Bug fix" below). This affects the shared pipeline used by **all** clients (CLI, browser extension, VS Code), not just the new one.

### Bug fix uncovered during this work (affects all clients)

While validating that file scanning actually blocks sensitive files, we found that `FileIntelAnalyzer` (Stage 2) builds its per-file summary/action **before** the content analyzers (Secrets/PII/Injection/Compliance, Stage 3) run, so a file whose *only* risk was content-based (e.g. a plain `.txt` containing a leaked AWS key, with no risky filename/extension) always reported `action: ALLOW` at the file level even when the top-level prompt decision was `BLOCK`. `decision_analyzer.py` now recomputes each file's action/risk once Stage 3 findings exist, mirroring the exact same `assess_risk` / `evaluate_policies` / `decide` calls `ai/pipeline.py::_scan_one_file` already uses. Separately, `FileIntelAnalyzer`'s risk-fusion weight was raised from `0.7` to `1.0` in `DEFAULT_RISK_WEIGHTS`, because file-identity CRITICAL findings (e.g. a bare `.env`/`id_rsa` upload, scored 80 in `ai/file_risk.py`) are documented to cross the CRITICAL threshold (≥75) on their own; a weight below ~0.94 silently diluted that below the cutoff and downgraded the decision to REDACT, contradicting the documented "bare `.env` upload blocks by default" behavior.

This is a correctness fix, not a contract/shape change: response fields, decision enum values, and existing ALLOW-path behavior are all unchanged. `backend/tests/test_cli.py::test_cli_scan_attached_file` (unmodified) exercises exactly this path and passes. See "Verification" in `README.md` for full test results.

## Antigravity compatibility

Antigravity IDE supports standard VS Code extensions (`.vsix` install, same extension host APIs). No Antigravity-specific code path was added or is needed — the only requirement is declaring a compatible `engines.vscode` range in `package.json`, which is already set to `^1.85.0`. If Antigravity ships a materially different Chat API version, the chat participant path may need adjustment, but the command-based scan paths (selection/clipboard/file/workspace) have no such dependency and work identically.
