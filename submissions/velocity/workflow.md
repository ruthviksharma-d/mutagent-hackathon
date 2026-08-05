# Multi-Agent Workflow — Mutagent Detection Engine

The **Mutagent Multi-Agent Detection Engine** organizes security scanning into an isolated, fault-tolerant 5-stage Directed Acyclic Graph (DAG).

---

## Multi-Agent Workflow Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Client as Browser Extension
    participant API as FastAPI Gateway
    participant Orchestrator as Mutagent Orchestrator
    participant Stage1 as Stage 1: ContextAgent
    participant Stage2 as Stage 2: FileIntelAgent
    participant Stage3 as Stage 3: Parallel ThreadPool
    participant Stage4 as Stage 4: RiskFusionAgent
    participant Stage5 as Stage 5: DecisionAgent
    participant DB as MySQL Database

    Client->>API: POST /api/scan (prompt, files, target_ai)
    API->>Orchestrator: execute_investigation(context)
    
    Orchestrator->>Stage1: run(context)
    Stage1-->>Orchestrator: Context Metadata (user, site, prompt len)
    
    Orchestrator->>Stage2: run(context)
    Stage2-->>Orchestrator: Extracted File Text & Identity Risk
    
    par Stage 3 Parallel Analyzers (ThreadPoolExecutor)
        Orchestrator->>Stage3: PiiAgent.run()
        Orchestrator->>Stage3: SecretsAgent.run()
        Orchestrator->>Stage3: InjectionAgent.run()
        Orchestrator->>Stage3: ComplianceAgent.run()
    end
    Stage3-->>Orchestrator: Return Findings (PII, Credentials, Injections, Keywords)
    
    Orchestrator->>Stage4: run(findings, risk_weights)
    Stage4-->>Orchestrator: Aggregated Risk Score (0-100) & Severity
    
    Orchestrator->>Stage5: run(score, policies)
    Stage5-->>Orchestrator: Final Verdict (ALLOW / WARN / REDACT / BLOCK)
    
    Orchestrator->>DB: Persist Investigation, Executions & Timeline
    Orchestrator-->>API: Return ScanResponse
    API-->>Client: Return Verdict + Explainable AI Evidence
```

---

## Stage Descriptions

1. **Stage 1 (Context)**: `ContextAgent` parses identity headers, user account attributes, and target AI domain.
2. **Stage 2 (File Intelligence)**: `FileIntelAgent` inspects file mime-types, checks file extension policies, and decodes binary/text content (`.pdf`, `.docx`, `.xlsx`, `.csv`, `.py`, `.js`, image OCR).
3. **Stage 3 (Parallel ThreadPool)**: Four specialized analyzers execute concurrently:
   - **`PiiAgent`**: Microsoft Presidio + spaCy NER.
   - **`SecretsAgent`**: `detect-secrets` 24 credential rules.
   - **`InjectionAgent`**: Jailbreak and prompt override pattern matcher.
   - **`ComplianceAgent`**: Company keyword list matcher.
4. **Stage 4 (Risk Fusion)**: `RiskFusionAgent` applies org risk multipliers (`risk_weights`) to construct a unified 0–100 risk score.
5. **Stage 5 (Decision Gate)**: `DecisionAgent` evaluates rules in priority order to return the final verdict.

---

© 2026 PromptShield AI. Powered by Mutagent Multi-Agent Security Engine.
