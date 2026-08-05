# Investigation Flow & Multi-Agent DAG

The **Security Investigations Console** renders an interactive Directed Acyclic Graph (DAG) for every scan executed by Mutagent.

---

## Investigation DAG Diagram

```mermaid
graph TD
    classDef nodeSuccess fill:#10B981,stroke:#059669,color:#ffffff,font-weight:bold;
    classDef nodeFailed fill:#EF4444,stroke:#DC2626,color:#ffffff,font-weight:bold;
    classDef nodeSkipped fill:#6B7280,stroke:#4B5563,color:#ffffff,font-weight:bold;
    classDef nodeRoot fill:#3B82F6,stroke:#1D4ED8,color:#ffffff,font-weight:bold;

    N_PROMPT["Input Prompt / Files"]:::nodeRoot --> N_CTX["Context Agent<br/>(Stage 1)"]:::nodeSuccess
    N_CTX --> N_FILE["File Intel Agent<br/>(Stage 2)"]:::nodeSuccess
    
    N_FILE -->|Bezier Fan-Out| N_PII["PII Agent<br/>(Stage 3)"]:::nodeSuccess
    N_FILE -->|Bezier Fan-Out| N_SEC["Secrets Agent<br/>(Stage 3)"]:::nodeSuccess
    N_FILE -->|Bezier Fan-Out| N_INJ["Injection Agent<br/>(Stage 3)"]:::nodeSuccess
    N_FILE -->|Bezier Fan-Out| N_CMP["Compliance Agent<br/>(Stage 3)"]:::nodeSuccess
    
    N_PII -->|Bezier Fan-In| N_FUS["Risk Fusion Agent<br/>(Stage 4)"]:::nodeSuccess
    N_SEC -->|Bezier Fan-In| N_FUS
    N_INJ -->|Bezier Fan-In| N_FUS
    N_CMP -->|Bezier Fan-In| N_FUS
    
    N_FUS --> N_DEC["Decision Agent<br/>(Stage 5)"]:::nodeSuccess
```

---

## UI DAG Execution Node Statuses

- **`SUCCESS`** (🟢 `#10B981`): Analyzer completed successfully within timeout limits and produced valid security findings.
- **`FAILED`** (🔴 `#EF4444`): Analyzer encountered an unhandled exception or syntax error; caught safely without halting parent trace.
- **`SKIPPED`** (⚪ `#6B7280`): Analyzer disabled by organization settings or skipped due to absence of input files.
- **`TIMEOUT`** (🟡 `#F59E0B`): Analyzer exceeded the 2.0-second execution threshold and was safely terminated.

---

© 2026 PromptShield AI. Powered by Mutagent Multi-Agent Security Engine.
