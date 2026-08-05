# Security Model & Data Governance — PromptShield AI v2.0

PromptShield AI enforces strict data governance, privacy controls, and audit trails.

---

## Database Relationships Diagram

```mermaid
erDiagram
    users ||--o{ audit_logs : "triggers"
    users ||--o{ investigations : "conducts"
    investigations ||--|{ agent_executions : "contains"
    investigations ||--|{ timeline_events : "emits"
    policies ||--o{ audit_logs : "enforces"

    users {
        string id PK
        string email UK
        string full_name
        string department
        string role "ADMIN | SECURITY_ANALYST | EMPLOYEE"
        string password_hash
        datetime created_at
    }

    investigations {
        string id PK
        string user_id FK
        string target_ai "ChatGPT | Claude | Gemini"
        int prompt_length
        int file_count
        int total_analyzers
        int overall_score
        string overall_severity
        string decision "ALLOW | WARN | REDACT | BLOCK"
        float total_execution_ms
        json summary
        datetime created_at
    }

    agent_executions {
        string id PK
        string investigation_id FK
        string agent_name
        string status "SUCCESS | FAILED | SKIPPED | TIMEOUT"
        float execution_time_ms
        float confidence
        string severity
        string recommendation
        json findings
        json evidence
    }

    timeline_events {
        string id PK
        string investigation_id FK
        string event_type
        string analyzer_name
        string message
        float duration_ms
        datetime timestamp
    }

    policies {
        string id PK
        string name
        int priority
        string detection_type
        string action "ALLOW | WARN | REDACT | BLOCK"
        boolean enabled
    }

    audit_logs {
        string id PK
        string user_id FK
        string prompt_text_preview
        string action_taken
        int risk_score
        datetime timestamp
    }
```

---

## Investigation Lifecycle Diagram

```mermaid
stateDiagram-v2
    [*] --> Submitted: Extension Intercepts Event
    Submitted --> ContextExtracted: Stage 1 (ContextAgent)
    ContextExtracted --> FilesInspected: Stage 2 (FileIntelAgent)
    
    state Stage3_Parallel {
        [*] --> PiiScanning
        [*] --> SecretsScanning
        [*] --> InjectionScanning
        [*] --> ComplianceScanning
        PiiScanning --> ParallelComplete
        SecretsScanning --> ParallelComplete
        InjectionScanning --> ParallelComplete
        ComplianceScanning --> ParallelComplete
    }
    
    FilesInspected --> Stage3_Parallel
    Stage3_Parallel --> RiskFused: Stage 4 (RiskFusionAgent)
    RiskFused --> DecisionEvaluated: Stage 5 (DecisionAgent)
    
    DecisionEvaluated --> Allowed: Decision == ALLOW
    DecisionEvaluated --> Warned: Decision == WARN
    DecisionEvaluated --> Redacted: Decision == REDACT
    DecisionEvaluated --> Blocked: Decision == BLOCK
    
    Allowed --> TraceRecorded
    Warned --> TraceRecorded
    Redacted --> TraceRecorded
    Blocked --> TraceRecorded
    
    TraceRecorded --> [*]: Rendered on Security Console
```

---

## Security Guarantees & Privacy Controls

1. **Client-Side Dom Interception**: Prompts and file attachments are intercepted locally inside the browser before any HTTP request is dispatched to OpenAI, Anthropic, or Google servers.
2. **Metadata-Only MySQL Storage**: Prompt texts are previewed or masked in audit logs; raw uploaded file binaries are never stored in MySQL.
3. **Role-Based Access Control (RBAC)**:
   - `admin`: Full configuration access (policy authoring, keyword management, user management).
   - `security_analyst`: Read-only access to audit logs, analytics, and investigation traces.
   - `employee`: Standard user access for Chrome extension authentication.

---

© 2026 PromptShield AI. Powered by Mutagent Multi-Agent Security Engine.
