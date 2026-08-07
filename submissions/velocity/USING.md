# Using PromptShield AI

This is a step-by-step usage guide for PromptShield AI, written for the people
who will run it day to day: security/IT admins who configure policy, security analysts who investigate multi-agent security traces,
and employees who use it seamlessly. If you're looking for
installation instructions, see [`README.md`](README.md) — this guide
assumes the backend, admin dashboard, and browser extension are already
running.

---

## Table of Contents

1. [What PromptShield AI Is](#what-promptshield-ai-is)
2. [The Three Things You're Running](#the-three-things-youre-running)
3. [Signing In](#signing-in)
4. [Using the Admin Dashboard](#using-the-admin-dashboard)
   - [Dashboard page](#dashboard-page)
   - [Security Investigations page (Mutagent Trace)](#security-investigations-page-mutagent-trace)
   - [Investigation Detail View (SVG DAG, Gauge & Evidence)](#investigation-detail-view-svg-dag-gauge--evidence)
   - [Prompt Logs page](#prompt-logs-page)
   - [Policies page](#policies-page)
   - [Employees page](#employees-page)
   - [Analytics page](#analytics-page)
   - [Settings page (Mutagent Configuration)](#settings-page-mutagent-configuration)
5. [Using the Browser Extension](#using-the-browser-extension)
   - [Installing it in Chrome](#installing-it-in-chrome)
   - [Signing in from the popup](#signing-in-from-the-popup)
   - [What the popup shows you](#what-the-popup-shows-you)
   - [What happens when you type a prompt or attach a file](#what-happens-when-you-type-a-prompt-or-attach-a-file)
   - [Reading the Explainable AI panel](#reading-the-explainable-ai-panel)
6. [Using the PromptShield CLI (`psh`)](#using-the-promptshield-cli-psh)
   - [Installing psh](#installing-psh)
   - [One-shot prompts](#one-shot-prompts)
   - [Interactive mode](#interactive-mode)
   - [Attaching files](#attaching-files)
   - [Configuring the backend URL](#configuring-the-backend-url)
7. [Common Workflows, Step by Step](#common-workflows-step-by-step)
   - [Workflow: onboarding a new employee](#workflow-onboarding-a-new-employee)
   - [Workflow: investigating a multi-agent trace](#workflow-investigating-a-multi-agent-trace)
   - [Workflow: writing your first policy](#workflow-writing-your-first-policy)
   - [Workflow: adding a company keyword](#workflow-adding-a-company-keyword)
   - [Workflow: reviewing weekly risk trends](#workflow-reviewing-weekly-risk-trends)
8. [Understanding the Four Decisions](#understanding-the-four-decisions)
9. [Troubleshooting](#troubleshooting)
10. [Default Credentials Reference](#default-credentials-reference)

---

## What PromptShield AI Is

PromptShield AI is an AI firewall for organizations whose employees use
ChatGPT, Claude, and Gemini — in the browser or from the terminal via Claude
CLI / Gemini CLI — in their day-to-day work. It doesn't ask anyone to
stop using those tools or switch to a different one. Instead, it sits quietly
between the employee and the AI: every time someone types a prompt or attaches a file and
hits send (or runs `psh claude`/`psh gemini`), PromptShield inspects it first via the **Mutagent Multi-Agent Engine**, decides whether it's safe, and only
then lets it (or a cleaned-up version of it) reach the AI.

It's made of four parts:

- **A browser extension** — Manifest V3 extension that sits inside ChatGPT, Claude, and Gemini to intercept prompts and file uploads before submission.
- **A CLI wrapper (`psh`)** — intercepts prompts and file attachments before they reach the real `claude`/`gemini` CLI binary, using the exact same backend and policy engine as the browser extension.
- **An admin dashboard** — React console featuring live security analytics, policy editor, and the **Mutagent Security Investigations Console**.
- **FastAPI Backend & Mutagent Engine** — 5-stage Multi-Agent execution pipeline (`ContextAgent` → `FileIntelAgent` → `PiiAgent`/`SecretsAgent`/`InjectionAgent`/`ComplianceAgent` → `RiskFusionAgent` → `DecisionAgent`) shared, unmodified, by both the extension and the CLI.

---

## The Three Things You're Running

Before you start, make sure you know:

- The **dashboard URL** (`http://localhost:5173`).
- The **backend URL** (`http://localhost:8000`).
- Your **login email and password** (see [Default Credentials Reference](#default-credentials-reference)).

---

## Signing In

Both the dashboard and the extension use the same account system.

**Dashboard:**
1. Open `http://localhost:5173`.
2. Click **Sign in** in the top-right corner.
3. Enter your email and password (`admin@promptshield.ai` / `Admin@12345`).
4. You're taken to the main Dashboard page.

---

## Using the Admin Dashboard

The sidebar contains 7 primary sections: **Dashboard**, **Security Investigations**, **Prompt Logs**, **Policies**, **Employees**, **Analytics**, and **Settings**.

### Dashboard page

Home screen summarizing security posture:
- **Summary Cards**: Security Score, Total Prompts, Allowed, Warned, Redacted, Blocked, Active Employees, Protected AI Websites.
- **Charts & Feeds**: Daily activity breakdown, risk distribution, top triggered detectors, website usage, and recent scan feed.

---

### Security Investigations page (Mutagent Trace)

Located at `/investigations`, this console provides deep multi-agent visibility into every scan:

1. **Filterable Table**: Filter investigations by **Decision** (`BLOCK`, `WARN`, `REDACT`, `ALLOW`) and **Severity** (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `NONE`).
2. **Employee Attribution**: Every row shows **Employee Full Name**, **Email**, and **Department Badge** (e.g., `Karan Desai` · `karan.desai@acme.com` · `Finance`).
3. **Execution Summary**: Displays Scan ID, Target AI platform (`ChatGPT`, `Claude`, `Gemini`), Risk Score (0-100), Agent Status (`8✓`), Total Execution Duration (ms), and Scan Timestamp.
4. **Click Any Row**: Navigates directly to the full investigation trace view (`/investigations/:id`).

---

### Investigation Detail View (SVG DAG, Gauge & Evidence)

The trace view at `/investigations/:id` renders three interactive security panels:

1. **Summary Card**:
   - Shows Employee Name, Email, Department, Target AI, Scanned Files count, Decision badge, Risk Score, Severity, and Total Duration.

2. **Interactive SVG Agent Flow Graph (DAG)**:
   - Visualizes the 5-stage Mutagent workflow: `Prompt` → `Context Agent` → `File Intel Agent` → Parallel Stage (`PII`, `Secrets`, `Injection`, `Compliance`) → `Risk Fusion` → `Decision`.
   - Node colors indicate execution status: 🟢 `SUCCESS`, 🔴 `FAILED`, ⚪ `SKIPPED`, 🟡 `TIMEOUT`.
   - Curved Bezier fan-out/fan-in edges with directional arrowheads cleanly connect parallel analyzers.

3. **Unclipped Ring Risk Score Gauge**:
   - High-contrast animated gauge dial (0-100) with a ring-constrained indicator needle that highlights score levels without overlapping the central bold score typography.

4. **Evidence Panel & Millisecond Timeline**:
   - **Evidence Cards**: Expandable findings per agent with character offsets, confidence ratings, raw detector outputs, and match previews (Presidio PII, detect-secrets, jailbreaks, keywords).
   - **Timeline Stream**: Chronological event log tracking start time, execution duration, and completion for every analyzer.

---

### Prompt Logs page

Searchable, filterable, paginated log of every scan.
- Filter by Action, Risk, and AI Website.
- Click any row to reveal original/sanitized text, triggered rules, and attached file risk breakdowns.

---

### Policies page

Define organization-wide enforcement rules:
- Create policies with Priority (lower numbers evaluate first), Action (`ALLOW`, `WARN`, `REDACT`, `BLOCK`), and Detection Type (`API Key`, `PII`, `Source Code`, `Company Keyword`, etc.).
- Enable or disable policies with one click directly from the table.

---

### Employees page

Organization directory showing:
- Name, Department, Role, Prompt Count, Violation Count, Last Active timestamp, and live **Extension Status** badge (`Active`, `Inactive`, `Not Installed`).

---

### Analytics page

Deep analytics for reporting:
- Risk trends over time, department risk distribution, website usage breakdown, top triggered rules, and top employees by violations.

---

### Settings page (Mutagent Configuration)

Organization-wide settings:
- Organization Name & Risk Threshold (0-100).
- Supported AI Websites & Allowed File Types by category (`Documents`, `Source Code`, `Config`, `Data`, `Logs`, `Images OCR`).
- **Company Keywords**: Add sensitive codenames (`Project Phoenix`, `Revenue2026`) with immediate live matching.

---

## Using the Browser Extension

### Installing it in Chrome

1. Open `chrome://extensions` and enable **Developer mode**.
2. Click **Load unpacked** and select `browser-extension/dist`.
3. Click the PromptShield extension icon in the toolbar and sign in.

---

### What happens when you type a prompt or attach a file

1. PromptShield intercepts the prompt text or attached file before submission.
2. Mutagent runs all 8 analyzers concurrently in **~100ms**.
3. Verdict enforced:
   - **ALLOW**: Passes through silently.
   - **WARN**: Displays Explainable AI panel with Cancel/Continue.
   - **REDACT**: Replaces sensitive data with placeholders (e.g. `[REDACTED_EMAIL]`) in the textbox.
   - **BLOCK**: Halts submission outright with a full explanation.

---

## Using the PromptShield CLI (`psh`)

`psh` extends the exact same backend, policy engine, and audit logging to terminal AI tools — **Claude CLI** and **Gemini CLI** — for developers and power users who work outside the browser. Every `psh` scan runs through the identical Mutagent pipeline as the extension and shows up on the same Admin Dashboard, under provider `"Claude CLI"` or `"Gemini CLI"`.

### Installing psh

```bash
cd cli
pip install -e .
```

This registers the `psh` command on your `PATH` (Windows: `psh.bat`, Linux/macOS: `./psh` also work without an editable install). See [`cli/README.md`](cli/README.md) for full installation and configuration details.

### One-shot prompts

```bash
psh claude "What is the capital of France?"
psh gemini "Summarize this changelog"
```

`psh` scans the prompt, prints the decision, and — if `ALLOW`/`WARN`(confirmed)/`REDACT` — launches the real `claude`/`gemini` CLI binary with the (possibly sanitized) prompt. A `BLOCK` decision never launches the target CLI at all.

### Interactive mode

Run `psh claude` or `psh gemini` with no prompt argument (or pass `-i`) to start a multi-turn session where every line you type at the `> ` prompt is scanned before it reaches the AI:

```bash
psh claude
> hello
> Card numbers on file: 4111 1111 1111 1111 and 5500 0000 0000 0004
```

Type `exit`, `quit`, or `:q` to end the session; `Ctrl+C` ends it cleanly with no traceback.

### Attaching files

```bash
psh gemini "Analyze this document" -f report.pdf -f config.env
```

Repeat `-f` for multiple files. Each attachment gets its own risk assessment independent of the prompt and every other file (see the [Understanding the Four Decisions](#understanding-the-four-decisions) note on per-file vs. overall decisions below), and every file's finding is visible on the **Prompt Logs** detail page in the dashboard exactly like a browser-uploaded file.

### Configuring the backend URL

By default `psh` talks to `http://localhost:8000`. Override it per-command with `--backend-url`, or set it once via the `PROMPTSHIELD_BACKEND_URL` environment variable or `~/.promptshield/config.json` — see [`cli/README.md`](cli/README.md#configuration) for the full list of options (`PROMPTSHIELD_API_TOKEN`, `PROMPTSHIELD_TIMEOUT`).

---

## Common Workflows, Step by Step

### Workflow: investigating a multi-agent trace

1. Navigate to **Security Investigations** (`/investigations`).
2. Search or filter for a `BLOCK` or `CRITICAL` scan.
3. Click the row to open the trace detail page.
4. Inspect the **SVG Agent Flow Graph** to verify which analyzers succeeded or triggered.
5. Review the **Risk Score Gauge** and expand the **Evidence Panel** to inspect exact character offsets and raw detector findings.

---

## Understanding the Four Decisions

| Decision | Browser Extension Experience | CLI (`psh`) Experience | Action Taken |
|---|---|---|---|
| **ALLOW** | Silent — no popup | `Decision : ALLOW`, no prompt | Sent through unmodified |
| **WARN** | Modal with Cancel/Continue | `Continue? (y/N)` prompt | Sent only if the employee confirms |
| **REDACT** | Textbox updated + Toast notice | Sanitized prompt printed and sent | Sensitive spans replaced with placeholders |
| **BLOCK** | Explanatory modal, no proceed option | Error message, target CLI never launched | Blocked outright before reaching AI |

A decision is driven by a policy match if one exists (evaluated in ascending priority order — the first enabled policy that matches wins), otherwise by the aggregate risk score's severity band (`LOW` → `ALLOW`, `MEDIUM` → `WARN`, `HIGH` → `REDACT`, `CRITICAL` → `BLOCK`).

**Per-file vs. overall decisions**: when files are attached (browser or CLI), each file also gets its *own* independent `action`/`risk` (visible in the Prompt Logs detail view and in the CLI's per-file output), computed only from that file's own findings — separate from the single overall decision that governs the prompt text. This is what lets a multi-file upload hold back just the one risky attachment instead of failing the whole batch, and it means the overall decision and an individual file's decision can legitimately differ (e.g. a bare `.env` upload is flagged `BLOCK`/`CRITICAL` on its own file-identity risk, even when the overall prompt+files decision comes back `REDACT` once every analyzer's score is combined).

---

## Default Credentials Reference

Default accounts initialized during setup:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@promptshield.ai` | `Admin@12345` |
| Employee (Finance) | `karan.desai@acme.com` | `Employee@12345` |
| Employee (Legal) | `neha.gupta@acme.com` | `Employee@12345` |
| Employee (Product) | `dev.patel@acme.com` | `Employee@12345` |

---

© 2026 PromptShield AI. Powered by Mutagent Multi-Agent Security Engine.
