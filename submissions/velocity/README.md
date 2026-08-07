# PromptShield AI — Mutagent Multi-Agent Security Engine
> **Enterprise AI Firewall & Multi-Agent Security Investigation Console**  
> *Mutagent Hackathon Submission — Team Velocity*

---

## 1. Problem Statement

As enterprise adoption of generative AI tools like ChatGPT, Claude, and Gemini explodes, organizations face severe data governance and security risks:
- Employees regularly copy-paste **live API keys, AWS credentials, PII, and financial records** into prompt textboxes.
- Confidential attachments (`.env`, `id_rsa`, `.pdf`, `.docx`, source code) are uploaded directly to public AI platforms.
- IT and security teams remain completely blind to employee AI interactions and policy violations.

---

## 2. Why Existing AI Firewalls Are Insufficient

Legacy AI firewalls and proxy wrappers fail in enterprise environments:
1. **API Proxy Latency**: Routing all traffic through centralized proxies adds 1–3 seconds of latency per prompt.
2. **Single-Point-of-Failure Crashes**: Single-thread regex/llm scanners crash entirely when an individual detector encounters an exception.
3. **No Attached File Text Extraction**: Most firewalls inspect typed text only, ignoring attached documents, code files, and OCR images.
4. **Black-Box Decisions**: Generic blocking prompts leave security teams with zero visibility into why a decision was issued or which employee was responsible.

---

## 3. Live Demo & Session Recording

[![PromptShield AI Live Product Demo](assets/demo_thumbnail.png)](assets/demo_recording.webp)

*Click image above to watch the full WebP interactive session recording of PromptShield AI v2.0.*

---

## 4. System Architecture

PromptShield AI solves these challenges with a three-part architecture:
- **Client Interceptor (Manifest V3 Extension)**: Intercepts DOM submit events and file uploads locally on `chatgpt.com`, `chat.openai.com`, `claude.ai`, and `gemini.google.com` before requests leave the browser.
- **FastAPI Security Gateway & Mutagent Engine**: A 5-stage Multi-Agent execution pipeline running parallel detectors with 2.0s per-agent fault isolation.
- **React Admin Security Console**: Web dashboard for policy authoring, employee risk tracking, and **interactive SVG Multi-Agent Investigation DAGs**.

```mermaid
flowchart TD
    EXT["Browser Extension (Manifest V3)<br/>Client-Side Interceptor"] -->|POST /api/scan| API["FastAPI Gateway (8000)"]
    API --> S1["Stage 1: ContextAgent"]
    S1 --> S2["Stage 2: FileIntelAgent"]
    S2 --> S3["Stage 3: Parallel ThreadPool<br/>(PII, Secrets, Injection, Compliance)"]
    S3 --> S4["Stage 4: RiskFusionAgent"]
    S4 --> S5["Stage 5: DecisionAgent"]
    S5 -->|Enforcement Verdict| EXT
    Mutagent -->|Write Trace| DB[(MySQL 8.4 Database)]
    DB -->|Query Traces & Analytics| DASH["React 19 Admin Dashboard"]
```

---

## 5. Mutagent Multi-Agent Integration

The **Mutagent Engine** structures detection into an isolated 5-stage Directed Acyclic Graph (DAG):

```text
                     [ Prompt / Files Input ]
                                │
                        [ Stage 1: Context Agent ]
                                │
                     [ Stage 2: File Intel Agent ]
                                │
        ┌───────────────┬───────┴───────┬───────────────┐
        ▼               ▼               ▼               ▼  (Parallel Stage 3 - ThreadPoolExecutor)
    [PII Agent]  [Secrets Agent] [Injection Agent] [Compliance Agent]
        │               │               │               │
        └───────────────┴───────┬───────┴───────────────┘
                                ▼
                    [ Stage 4: Risk Fusion Agent ]  <-- Admin Risk Weights
                                │
                    [ Stage 5: Decision Agent ]     <-- Verdict: BLOCK / WARN / REDACT / ALLOW
```

### Key Technical Innovations
- **Fault-Isolated Execution**: Stage-3 parallel agents run inside a `ThreadPoolExecutor` with a strict 2.0-second timeout per agent. If an individual agent throws an unhandled exception, it is marked `FAILED` while the remaining pipeline completes safely.
- **Comprehensive Text Extraction**: `FileIntelAgent` extracts text from `.pdf`, `.docx`, `.xlsx`, `.csv`, `.log`, source code (`.py`, `.js`, `.ts`, `.sql`), configuration (`.env`, `.yaml`), and image OCR (`.png`, `.jpg` via `pytesseract`).

---

## 6. Security Model & Data Governance

1. **Pre-Flight Client Interception**: Prompts and file attachments are intercepted locally in the browser before any HTTP request leaves for AI servers.
2. **Metadata-Only MySQL Storage**: Prompt texts are previewed or masked in audit logs; raw uploaded file binaries are never stored in MySQL.
3. **Role-Based Access Control (RBAC)**: `admin` (full policies & settings), `security_analyst` (read-only audit traces), and `employee` (extension authentication).

---

## 7. Security Investigations Console

The Security Investigations Console (`/investigations` & `/investigations/:id`) provides complete visibility into every Multi-Agent scan execution:

- **Employee Attribution**: Displays Scan ID, **Employee Full Name, Email, and Department Badge** (e.g., `Karan Desai` · `karan.desai@acme.com` · `Finance`).
- **Interactive SVG Agent Flow Graph (DAG)**: Custom SVG DAG with curved Bezier fan-out/fan-in connector paths and status-coded nodes (🟢 `SUCCESS`, 🔴 `FAILED`, ⚪ `SKIPPED`, 🟡 `TIMEOUT`).
- **Unclipped Ring Risk Gauge**: 0–100 animated risk dial with an outer ring-constrained indicator needle that leaves the central score typography clear and legible.
- **Evidence Panel & Timeline**: Expandable findings cards with character offsets, confidence ratings, raw detector outputs, and timestamped event logs.

---

## 8. Live Application Screenshots

| Console View | High-Resolution Capture from Live Application |
|---|---|
| **Security Investigations Table** | ![Security Investigations List](assets/investigations_table.png) |
| **Interactive SVG Flow Graph (DAG)** | ![Multi-Agent DAG & Risk Gauge](assets/investigation_detail_graph.png) |
| **Evidence Panel & Findings** | ![Evidence Panel](assets/investigation_evidence.png) |
| **Millisecond Execution Timeline** | ![Timeline Log](assets/investigation_timeline.png) |
| **Prompt Logs Table** | ![Prompt Logs Table](assets/prompt_logs.png) |
| **Policy Authoring & Modal** | ![Policy Authoring](assets/policy_modal.png) |
| **Employee Directory** | ![Employee Directory](assets/employees.png) |
| **Analytics Trend Charts** | ![Analytics Charts](assets/analytics.png) |
| **Settings & Risk Thresholds** | ![Settings Page](assets/settings.png) |

---

## 9. Evaluation Methodology & Benchmark Results

PromptShield AI was evaluated against **25 representative enterprise security scenarios** ([evaluation.md](evaluation.md)):

### Key Benchmark Metrics

| Metric | Target Goal | Benchmark Result | Status |
|---|---|---|---|
| **Pipeline Latency** | `< 200 ms` | **108.4 ms avg** | PASS 🟢 |
| **Credential Recall** | `100%` | **100% (6/6 detected)** | PASS 🟢 |
| **PII Precision** | `> 95%` | **96.8%** | PASS 🟢 |
| **Injection Block Rate** | `> 90%` | **100% (3/3 blocked)** | PASS 🟢 |
| **Fault Isolation Survival** | `100%` | **100% (0 pipeline crashes)** | PASS 🟢 |
| **Overall Test Pass Rate** | `100%` | **25 / 25 Cases Passed** | PASS 🟢 |

---

## 10. How to Run PromptShield AI

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 20+**
- **MySQL 8.4**
- **Google Chrome**

### 2. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate        # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Initialize MySQL & seed investigation traces:
python check_mysql.py
python seed.py
python seed_investigations.py

# Start FastAPI server (Port 8000):
python -m uvicorn main:app --reload --port 8000
```

### 3. Admin Dashboard Setup
```bash
cd admin-dashboard
npm install
npm run dev
```
Open `http://localhost:5173`. Login with default credentials (`admin@promptshield.ai` / `Admin@12345`).

### 4. Browser Extension Setup
```bash
cd browser-extension
npm install
npm run build
```
In Chrome: Go to `chrome://extensions`, enable **Developer mode**, click **Load unpacked**, and select `browser-extension/dist`.

### 5. CLI Protection Setup (`psh`)
PromptShield CLI protects terminal AI usage for **Claude CLI** and **Gemini CLI**:

```bash
cd cli
pip install -e .
```

Run CLI commands:
```bash
psh claude "What is the capital of France?"
psh gemini "Analyze attached code" -f file.py -f config.env
```
Decisions (`ALLOW`, `WARN`, `REDACT`, `BLOCK`) are evaluated by the backend engine and automatically logged to the Admin Dashboard under provider `"Claude CLI"` or `"Gemini CLI"`.

---

## 11. Manual Verification & Latest Hardening

PromptShield AI v2.0's Browser Extension and CLI wrapper have both been manually verified end-to-end against a live backend + dashboard:

**Browser Extension** — ChatGPT/Claude/Gemini interception, prompt scanning, file scanning, `ALLOW`/`BLOCK` enforcement, and Admin Dashboard logging all confirmed working.

**PromptShield CLI (`psh`)** — installation, Claude CLI and Gemini CLI integration, interactive mode, prompt interception/forwarding, `ALLOW`/`BLOCK` enforcement, file scanning, dashboard logging, and error handling all confirmed working.

**Latest fix — per-file decision recomputation (Stage 5)**: manual file-scan testing surfaced a real bug where an uploaded file's *own* `FileFindingSummary` (the per-file `action`/`risk` the extension and CLI use to gate that specific attachment — see `schemas/scan.py::FileFindingSummary`) was computed by `FileIntelAnalyzer` in Stage 2, **before** the Stage 3 content analyzers (`SecretsAnalyzer`, `PiiAnalyzer`, `InjectionAnalyzer`, `ComplianceAnalyzer`) had run. A file whose *only* risk was content-based — e.g. a plain `.txt` containing leaked AWS/OpenAI keys — stayed permanently stamped `ALLOW` / `"No detectors ran"` in its per-file summary, even though the top-level scan decision correctly came back `BLOCK`. Identity-based file risk (a file literally named `.env`, `id_rsa`, etc.) was never affected, since that's computed at Stage 2 and doesn't depend on content analysis.

Fixed in `backend/mutagent/analyzers/decision_analyzer.py`: after all content analyzers have tagged their `[file:<filename>]` findings, Stage 5 (`DecisionAnalyzer`) now recomputes each file's `risk`/`score`/`action`/`reason` from those findings using the same `assess_risk` / `evaluate_policies` / `decide` calls the rest of the pipeline already uses — no duplicated logic. Verified against a reproduction of the exact bug (AWS + OpenAI keys in an uploaded `.txt` file: per-file summary now correctly reports `BLOCK` / `CRITICAL` instead of `ALLOW` / `NONE`), with a clean control file confirmed to still report `ALLOW`. Full backend test suite (49 non-DB tests) passes with no regressions.

---

## 12. Future Work

- **Multi-Tenant SSO/SAML**: Okta and Azure AD integration for enterprise user directory synchronization.
- **WebSocket Streaming**: Real-time streaming of live multi-agent investigation execution steps.
- **SIEM Integrations**: Native webhooks exporting JSON investigation traces directly to Splunk, Datadog, and Sumo Logic.

---

© 2026 PromptShield AI. Powered by Mutagent Multi-Agent Security Engine.
