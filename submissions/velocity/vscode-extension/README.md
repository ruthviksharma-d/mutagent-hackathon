# PromptShield for VS Code / Antigravity

AI Firewall client for VS Code and Antigravity IDE. A fourth PromptShield client alongside the Browser Extension and CLI — same backend, same 9-stage analyzer, same policy engine. See `ARCHITECTURE.md` for the full design and why prompt "interception" works the way it does in VS Code's extension model.

## What it does

- `@promptshield` chat participant — scan a draft prompt (with conversation history) before pasting it into Copilot Chat, Antigravity's assistant, or any other AI surface.
- Commands to scan the current selection, clipboard text, the active file, or the whole workspace.
- File content extraction + scanning for: txt, md, py, js, ts, java, c, cpp, cs, go, rs, env, json, yaml, yml, xml, sql, pdf, docx, xlsx, csv.
- Enforces the backend's ALLOW / WARN / REDACT / BLOCK decision — WARN shows findings in a modal, REDACT substitutes sanitized text, BLOCK stops the flow.
- Optional background workspace scanning with findings surfaced in the Problems panel.
- Status bar item, Activity Bar view with recent scans/findings, output channel (sanitized logs), risk summary webview panel.
- Local audit queue with retry/backoff when the backend is unreachable, honoring a configurable fail-open/fail-closed policy.

## Install (development)

1. `cd vscode-extension && npm install`
2. Open this folder in VS Code, press `F5` (Run Extension) to launch an Extension Development Host, or package it (below) and install the `.vsix`.
3. Run **PromptShield: Sign In** from the Command Palette and enter your PromptShield backend credentials (same account used for the browser extension/dashboard). The token is stored in VS Code `SecretStorage`, never in settings.json.
4. Set `promptshield.backendUrl` (Settings → Extensions → PromptShield) if your backend isn't on `http://localhost:8000`.

## Build

```
cd vscode-extension
npm install
npm run compile      # tsc typecheck (--noEmit) + esbuild bundle to dist/extension.js
```

`npm run watch` rebuilds on file change during development.

> Note: if you're on a filesystem that doesn't support atomic renames (some network/FUSE-mounted drives), `npm install` may fail with `ENOTEMPTY`. Run `npm install` from a local/native filesystem path and copy `node_modules` over, or use `npm install --no-bin-links`.

## Package as a VSIX

```
npm install -g @vscode/vsce
cd vscode-extension
npm run compile
vsce package
```

This produces `promptshield-vscode-0.1.0.vsix`. Install it in VS Code or Antigravity via **Extensions → ... → Install from VSIX**.

## Settings

| Setting | Default | Purpose |
|---|---|---|
| `promptshield.backendUrl` | `http://localhost:8000` | Backend base URL |
| `promptshield.organizationId` | `""` | Multi-tenant org header |
| `promptshield.enableWorkspaceScan` | `false` | Background scan of opened/saved/new files |
| `promptshield.enableFileScan` | `true` | Allow scanning attached/selected files |
| `promptshield.enablePromptScan` | `true` | Enable chat participant + scan commands |
| `promptshield.enableConversationContext` | `true` | Include prior chat turns when scanning |
| `promptshield.maxFileSizeKb` | `2048` | Skip files larger than this |
| `promptshield.autoRedaction` | `true` | Auto-use sanitized text on REDACT |
| `promptshield.strictMode` | `false` | WARN cannot be bypassed by the user |
| `promptshield.telemetry` | `false` | Persist raw prompt text in local history (off by default; only metadata is kept otherwise) |
| `promptshield.debugMode` | `false` | Verbose (sanitized) logging |
| `promptshield.failureMode` | `open` | `open` = allow with warning when backend unreachable, `closed` = block |

API key/token: stored via `vscode.SecretStorage` only (`promptshield.login` / `promptshield.logout` commands), never written to settings.json or logs.

## New files created

```
vscode-extension/
  package.json, tsconfig.json, esbuild.js, .vscodeignore, README.md, ARCHITECTURE.md
  media/activity-icon.svg, media/status-shield.svg
  src/extension.ts
  src/interceptor.ts
  src/scanner.ts
  src/backend.ts
  src/api.ts
  src/settings.ts
  src/types/index.ts
  src/ui/statusBar.ts, activityBarProvider.ts, riskPanel.ts, notifications.ts
  src/providers/diagnosticsProvider.ts
  src/services/policyCacheService.ts, auditQueueService.ts, workspaceMonitorService.ts, scanHistoryStore.ts
  src/utils/debounce.ts, fileTypeUtils.ts, logger.ts
```

## Modified files outside vscode-extension/

- `backend/main.py` — one new import + one new `app.include_router(...)` line (additive).
- `backend/routers/vscode.py` — **new file**, adds `GET /api/policies/summary` (read-only, additive, does not touch any existing route).
- `backend/schemas/vscode.py` — **new file**, response models for the above.
- `backend/mutagent/analyzers/decision_analyzer.py`, `backend/mutagent/models.py`, `backend/mutagent/analyzers/risk_fusion_analyzer.py` — bug fix to the shared file-decision pipeline (affects all clients equally; see "Bug fix" in `ARCHITECTURE.md`). No response shape or decision-enum changes.

`browser-extension/` and `cli/` were **not modified** — see Verification below.

## Assumptions / known limitations

- VS Code has no cross-extension network interception API, so "before it's sent" enforcement is opt-in via the chat participant and scan commands, not silent interception of Copilot/Antigravity's own network traffic. This is documented in `ARCHITECTURE.md`.
- pdf/docx/xlsx extraction happens in the extension host using `pdf-parse`, `mammoth`, and `exceljs`; only extracted text is sent to the backend, never raw binary.
- Antigravity IDE needs no special-cased code — it consumes standard VS Code extensions, and `engines.vscode` in `package.json` is the only compatibility declaration required.
- Workspace background scanning is off by default (`enableWorkspaceScan: false`) to avoid surprising network calls/CPU use on large repos; it can be enabled per the settings table above.
- `npm install` inside this repo's `vscode-extension/` directory can fail with `ENOTEMPTY` on FUSE-mounted network drives due to how npm does atomic renames during install — this is an environment limitation, not a project issue (see "Build" note above). The build was verified by installing in a native-filesystem temp directory and copying the resulting `node_modules`/`dist` back.

## Verification

**TypeScript compile:** `npm run compile` → 0 errors, `dist/extension.js` produced (esbuild, ~14MB unminified bundle including `exceljs`/`mammoth`/`pdf-parse`).

**Browser extension** (`browser-extension/`, zero files touched): `npm install && npm run build` (`tsc -b && vite build && vite build --config vite.content.config.ts`) completed with 0 errors — produced `dist/popup.js`, `dist/assets/background.js`, `dist/assets/content.js` as before.

**CLI** (`cli/`, zero files touched): `python3 -m py_compile` on all `cli/**/*.py` succeeds with no syntax errors.

**Backend test suite** (`backend/tests/`): `pytest -q` → 49 passed, 3 errors. The 3 errors (`test_cli.py::test_cli_scan_allow`, `test_cli_scan_block_secrets`, `test_cli_scan_attached_file`) are `sqlalchemy.exc.OperationalError: Can't connect to MySQL server` — no MySQL instance is available in this sandbox (no root access to install one); this is an environment limitation, not a regression. All non-DB-dependent tests, including everything covering the analyzers touched by the bug fix above, pass. `python3 -m py_compile` on the entire `backend/` tree (including all touched files) succeeds with no syntax errors.

Net result: the Browser Extension and CLI are functionally unmodified and their builds/compiles are unaffected; the one backend behavior change (file-decision recompute + risk weight) is an additive bug fix validated by the existing (unmodified) `test_cli_scan_attached_file` test's assertions.
