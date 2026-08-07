# System Architecture — PromptShield AI v2.0

PromptShield AI is an enterprise AI firewall composed of four primary subsystems, all sharing one backend and one detection pipeline — there is no duplicated security logic between them:
1. **Browser Extension (Manifest V3)**: Intercepts prompt text submissions and file attachments on `chatgpt.com`, `chat.openai.com`, `claude.ai`, and `gemini.google.com`.
2. **PromptShield CLI (`psh`)**: Intercepts prompts and file attachments before they reach the real **Claude CLI** or **Gemini CLI** binary on a developer's machine, via its own isolated `POST /api/cli/scan` endpoint that calls the identical pipeline.
3. **FastAPI Backend & Mutagent Engine**: A 5-stage Multi-Agent execution pipeline that processes input text and file attachments concurrently, invoked by both the extension and the CLI.
4. **React Admin Dashboard**: A web-based security console for configuring organization policies, viewing analytics, and inspecting **interactive SVG Multi-Agent Investigation DAGs** — for scans originating from either client.

---

## Overall Architecture Diagram

```mermaid
flowchart TD
    subgraph Client ["Browser Client"]
        EXT["Browser Extension (Manifest V3)<br/>Shadow DOM Interceptor"]
        UI_CG["ChatGPT / Claude / Gemini"]
    end

    subgraph Terminal ["Developer Terminal"]
        CLI["PromptShield CLI (psh)<br/>Local Interceptor"]
        UI_CLI["Claude CLI / Gemini CLI"]
    end

    subgraph Backend ["FastAPI Security Gateway (Port 8000)"]
        API["/api/scan Endpoint<br/>(extension)"]
        API_CLI["/api/cli/scan Endpoint<br/>(psh)"]

        subgraph Mutagent ["Mutagent Multi-Agent Engine — shared by both endpoints"]
            S1["Stage 1: ContextAgent"]
            S2["Stage 2: FileIntelAgent"]
            
            subgraph S3 ["Stage 3: Parallel Analyzers (ThreadPoolExecutor)"]
                PII["PiiAgent<br/>(Presidio + spaCy NER)"]
                SEC["SecretsAgent<br/>(detect-secrets)"]
                INJ["InjectionAgent<br/>(Jailbreak Matcher)"]
                CMP["ComplianceAgent<br/>(Org Keywords)"]
            end
            
            S4["Stage 4: RiskFusionAgent"]
            S5["Stage 5: DecisionAgent"]
        end
    end

    subgraph Storage ["Persistent Data Layer"]
        DB[(MySQL 8.4 Database<br/>investigations, agent_executions,<br/>timeline_events, audit_logs, users, policies)]
    end

    subgraph Admin ["Admin Security Console (Port 5173)"]
        DASH["React 19 Admin Dashboard"]
        DAG_UI["Interactive SVG DAG & Gauge"]
    end

    EXT -->|1a. Intercept Prompt & Files| API
    CLI -->|1b. Intercept Prompt & Files| API_CLI
    API --> S1
    API_CLI --> S1
    S1 --> S2
    S2 --> S3
    PII & SEC & INJ & CMP --> S4
    S4 --> S5
    S5 -->|2a. Return Verdict| EXT
    S5 -->|2b. Return Verdict| CLI
    Mutagent -->|3. Record Investigation Trace| DB
    DASH -->|4. Query Traces & Analytics| DB
    DB -->|5. Render Live Traces| DAG_UI
```

---

## Data Flow Lifecycle

1. **Client Interception**: When an employee hits "Send" or drops a file into ChatGPT, Claude, or Gemini, the extension's `content_scripts` intercept the DOM event before the web request leaves the browser. Equivalently, running `psh claude`/`psh gemini` intercepts the prompt and any `-f` file attachments before the real CLI binary ever launches.
2. **Mutagent Inspection**: The backend receives the JSON payload (`prompt`, `files`, `site`, `user`), passes it to the `ContextAgent`, extracts file text via `FileIntelAgent`, and spawns 4 parallel analyzer threads (`ThreadPoolExecutor`) — identically whether the request came from `/api/scan` (extension) or `/api/cli/scan` (`psh`).
3. **Risk Fusion & Verdict**: `RiskFusionAgent` applies org-defined analyzer risk multipliers, and `DecisionAnalyzer` checks priority rules to output an enforcement verdict (`ALLOW`, `WARN`, `REDACT`, `BLOCK`) for the prompt+files as a whole, plus an independent per-file verdict for each attachment (so one risky file in a batch doesn't have to block the rest).
4. **Audit Logging & Visualization**: The full trace is written to MySQL across `investigations`, `agent_executions`, and `timeline_events` tables (linked to the corresponding `audit_logs` row), instantly visible on the Admin Dashboard's `/investigations` and `/prompt-logs` pages regardless of which client produced the scan.

---

© 2026 PromptShield AI. Powered by Mutagent Multi-Agent Security Engine.
