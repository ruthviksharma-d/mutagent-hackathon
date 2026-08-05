# System Architecture — PromptShield AI v2.0

PromptShield AI is an enterprise AI firewall composed of three primary subsystems:
1. **Browser Extension (Manifest V3)**: Intercepts prompt text submissions and file attachments on `chatgpt.com`, `chat.openai.com`, `claude.ai`, and `gemini.google.com`.
2. **FastAPI Backend & Mutagent Engine**: A 5-stage Multi-Agent execution pipeline that processes input text and file attachments concurrently.
3. **React Admin Dashboard**: A web-based security console for configuring organization policies, viewing analytics, and inspecting **interactive SVG Multi-Agent Investigation DAGs**.

---

## Overall Architecture Diagram

```mermaid
flowchart TD
    subgraph Client ["Client Devices & Browser Environment"]
        EXT["Browser Extension (Manifest V3)<br/>Shadow DOM Interceptor"]
        UI_CG["ChatGPT / Claude / Gemini"]
    end

    subgraph Backend ["FastAPI Security Gateway (Port 8000)"]
        API["/api/scan Endpoint"]
        
        subgraph Mutagent ["Mutagent Multi-Agent Engine"]
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
        DB[(MySQL 8.4 Database<br/>investigations, agent_executions,<br/>timeline_events, users, policies)]
    end

    subgraph Admin ["Admin Security Console (Port 5173)"]
        DASH["React 19 Admin Dashboard"]
        DAG_UI["Interactive SVG DAG & Gauge"]
    end

    EXT -->|1. Intercept Prompt & Files| API
    API --> S1
    S1 --> S2
    S2 --> S3
    PII & SEC & INJ & CMP --> S4
    S4 --> S5
    S5 -->|2. Return Verdict (ALLOW/WARN/REDACT/BLOCK)| EXT
    Mutagent -->|3. Record Investigation Trace| DB
    DASH -->|4. Query Traces & Analytics| DB
    DB -->|5. Render Live Traces| DAG_UI
```

---

© 2026 PromptShield AI. Powered by Mutagent Multi-Agent Security Engine.
