# PromptShield Browser Extension Demo Video & Asset Documentation

This directory contains the recorded product demonstration video and captured screenshot assets for the **PromptShield AI Browser Extension** and **Admin Security Console**.

---

## 🎥 Demo Video Overview

- **MP4 Video File**: `promptshield_browser_demo.mp4` (~8.9 MB, H.264 HD)
- **WebP Video File**: `promptshield_browser_demo.webp` (15.01 MB, Animated WebP)
- **Target Audience**: Hackathon Judges, Enterprise Security Teams, Product Showcase
- **Mode**: Strict Read-Only Mode (Zero code or database modifications)

---

## 🚀 How the Recording Was Made

### 1. Environment & Prerequisites
- **Backend**: FastAPI Security Gateway running on `http://localhost:8000`
- **Frontend / Console**: React 19 + Vite Admin Security Console running on `http://localhost:5173`
- **Browser Extension**: Manifest V3 extension built from `submissions/velocity/browser-extension/dist`

### 2. Live Automated Demo Execution
The demo was conducted and recorded using `browser_subagent` following a systematic end-to-end interactive workflow:

1. **Authentication**:
   - Navigated to `http://localhost:5173/login`.
   - Logged in with enterprise admin credentials (`admin@promptshield.ai`).

2. **Dashboard Overview (`/dashboard`)**:
   - Inspected high-level security score (64/100), total prompts scanned (434), action breakdown (Allowed: 195, Warned: 57, Redacted: 46, Blocked: 136).
   - Reviewed daily prompt activity trends and risk distribution charts.

3. **Prompt Logs & Audit Trail (`/prompt-logs`)**:
   - Filtered prompt logs by action (`ALLOW`, `WARN`, `REDACT`, `BLOCK`).
   - Selected individual prompt audit records to view original prompt content, sanitization masking, target AI provider, and detector execution details.

4. **Multi-Agent Security Investigations (`/investigations` & `/investigations/:id`)**:
   - Navigated the Security Investigations console.
   - Selected active investigation traces (`e0331e18-7519-4249-96fe-8a0696a56d5c`).
   - Inspected the interactive **SVG Multi-Agent Flow Graph (DAG)** showing parallel stage execution:
     - `ContextAgent` -> `FileIntelAgent` -> Parallel Analyzers (`PIIAgent`, `SecretsAgent`, `InjectionAgent`, `ComplianceAgent`) -> `RiskFusionAgent` -> `DecisionAgent`.
   - Reviewed the **Unclipped Ring Risk Gauge** and execution status indicators.
   - Toggled between the **Execution Timeline Log** (millisecond timing breakdown) and **Evidence Panel** (raw findings, confidence scores, character offsets).

5. **Policy Authoring (`/policies`)**:
   - Viewed active organization policies (`Block Live AWS Keys`, `Warn on PII Credit Cards`, `Redact Employee SSNs`).
   - Opened the Policy Editor modal to demonstrate rule matching, threshold configuration, and verdict mapping.

6. **Employee Directory (`/employees`)**:
   - Audited employee risk scores, department badges (Finance, Engineering, Legal), active extension statuses, and total prompt volume per user.

7. **Analytics Console (`/analytics`)**:
   - Analyzed long-term risk trends, top triggered policy rules, target AI website breakdown (ChatGPT, Claude, Gemini), and department-level risk exposure.

8. **Settings & Risk Thresholds (`/settings`)**:
   - Reviewed Stage 3 multi-agent risk weights, enabled analyzer toggles, supported AI domains, and file extension rules.

---

## 🖼️ Captured Screenshot Assets

| Filename | Description | Viewport / Section |
|---|---|---|
| `01_dashboard_overview.png` | Executive security dashboard with metrics cards, prompt volume, and risk distribution | `/dashboard` |
| `02_prompt_logs_audit.png` | Audit logs table with action filters (`ALLOW`, `WARN`, `REDACT`, `BLOCK`) | `/prompt-logs` |
| `03_investigations_console.png` | Security investigations list with severity badges and employee attribution | `/investigations` |
| `04_multi_agent_dag_graph.png` | Interactive SVG Multi-Agent Directed Acyclic Graph (DAG) flow execution | `/investigations/:id` |
| `05_evidence_panel.png` | Detailed evidence findings panel with confidence scores and detector matches | `/investigations/:id#evidence` |
| `06_policy_authoring.png` | Enterprise policy management table and active enforcement rules | `/policies` |
| `07_edit_policy_modal.png` | Policy authoring and rule configuration modal interface | `/policies` |
| `08_employee_directory.png` | Employee directory with risk score badges and department metrics | `/employees` |
| `09_analytics_dashboard.png` | Analytics charts showing policy violation breakdown and provider usage | `/analytics` |
| `10_settings_risk_weights.png` | Stage 3 Multi-Agent risk weights and detector configuration settings | `/settings` |

---

## 🔒 Verification & Compliance

- **No Code Modifications**: All source code, build targets, and configurations remained 100% untouched.
- **Reproducibility**: The demo can be re-run at any time by starting the backend (`uvicorn main:app --port 8000`) and frontend (`npm run dev` in `admin-dashboard`).
