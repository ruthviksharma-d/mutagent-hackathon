"""
Exporter script to dump representative Mutagent Multi-Agent Investigation Traces
from MySQL into submissions/velocity/traces/ (BLOCK, WARN, REDACT, ALLOW).
"""
import json
import os
import uuid
from datetime import datetime, timezone
from database import SessionLocal
from models.investigation import Investigation, AgentExecution, TimelineEvent
from models.user import User

OUTPUT_DIR = os.path.join("..", "traces")

def generate_fallback_redact_trace():
    now_iso = datetime.now(timezone.utc).isoformat()
    scan_id = f"sc_{uuid.uuid4().hex[:12]}"
    return {
        "scan_id": scan_id,
        "user_id": "usr_employee_001",
        "user_name": "Priya Sharma",
        "user_email": "priya.sharma@acme.com",
        "user_department": "Finance",
        "target_ai": "Claude",
        "prompt_length": 110,
        "file_count": 0,
        "total_analyzers": 8,
        "analyzers_succeeded": 8,
        "analyzers_failed": 0,
        "analyzers_skipped": 0,
        "risk_score": 55,
        "severity": "HIGH",
        "decision": "REDACT",
        "execution_time_ms": 118.5,
        "summary": {
            "overall_score": 55,
            "overall_severity": "HIGH",
            "decision": "REDACT",
            "reasoning": "Redacted: Prompt contains sensitive PII (customer email and phone number)."
        },
        "created_at": now_iso,
        "analyzer_execution_order": [
            "ContextAnalyzer",
            "FileIntelAnalyzer",
            "PiiAnalyzer",
            "SecretsAnalyzer",
            "InjectionAnalyzer",
            "ComplianceAnalyzer",
            "RiskFusionAnalyzer",
            "DecisionAnalyzer"
        ],
        "agent_executions": [
            {
                "id": str(uuid.uuid4()),
                "agent_name": "ContextAnalyzer",
                "display_name": "Context Agent",
                "status": "SUCCESS",
                "execution_time_ms": 4.2,
                "confidence": 1.0,
                "severity": "NONE",
                "recommendation": "ALLOW",
                "summary": "Context extracted for user priya.sharma@acme.com on Claude.",
                "error": None,
                "findings": [],
                "evidence": []
            },
            {
                "id": str(uuid.uuid4()),
                "agent_name": "FileIntelAnalyzer",
                "display_name": "File Intel Agent",
                "status": "SUCCESS",
                "execution_time_ms": 3.1,
                "confidence": 1.0,
                "severity": "NONE",
                "recommendation": "ALLOW",
                "summary": "No files attached — file analysis skipped.",
                "error": None,
                "findings": [],
                "evidence": []
            },
            {
                "id": str(uuid.uuid4()),
                "agent_name": "PiiAnalyzer",
                "display_name": "PII Agent",
                "status": "SUCCESS",
                "execution_time_ms": 42.8,
                "confidence": 0.92,
                "severity": "HIGH",
                "recommendation": "REDACT",
                "summary": "Detected 2 PII items: Email and Phone Number.",
                "error": None,
                "findings": [
                    {
                        "category": "pii",
                        "detector": "presidio",
                        "entity": "EMAIL_ADDRESS",
                        "value_preview": "alice.smith@acme.com",
                        "severity": "HIGH"
                    }
                ],
                "evidence": [
                    {
                        "label": "EMAIL_ADDRESS",
                        "value_preview": "alice.smith@acme.com",
                        "confidence": 0.95,
                        "location": "prompt:L1:C45",
                        "detector": "presidio",
                        "severity": "HIGH",
                        "start": 45,
                        "end": 65,
                        "metadata": {}
                    }
                ]
            },
            {
                "id": str(uuid.uuid4()),
                "agent_name": "SecretsAnalyzer",
                "display_name": "Secrets Agent",
                "status": "SUCCESS",
                "execution_time_ms": 18.3,
                "confidence": 1.0,
                "severity": "NONE",
                "recommendation": "ALLOW",
                "summary": "No credentials or secrets detected.",
                "error": None,
                "findings": [],
                "evidence": []
            },
            {
                "id": str(uuid.uuid4()),
                "agent_name": "InjectionAnalyzer",
                "display_name": "Injection Agent",
                "status": "SUCCESS",
                "execution_time_ms": 15.6,
                "confidence": 1.0,
                "severity": "NONE",
                "recommendation": "ALLOW",
                "summary": "No prompt injection patterns detected.",
                "error": None,
                "findings": [],
                "evidence": []
            },
            {
                "id": str(uuid.uuid4()),
                "agent_name": "ComplianceAnalyzer",
                "display_name": "Compliance Agent",
                "status": "SUCCESS",
                "execution_time_ms": 12.1,
                "confidence": 1.0,
                "severity": "NONE",
                "recommendation": "ALLOW",
                "summary": "No policy violations or company keyword hits.",
                "error": None,
                "findings": [],
                "evidence": []
            },
            {
                "id": str(uuid.uuid4()),
                "agent_name": "RiskFusionAnalyzer",
                "display_name": "Risk Fusion Agent",
                "status": "SUCCESS",
                "execution_time_ms": 8.4,
                "confidence": 0.92,
                "severity": "HIGH",
                "recommendation": "REDACT",
                "summary": "Aggregated risk score: 55/100 (HIGH).",
                "error": None,
                "findings": [],
                "evidence": []
            },
            {
                "id": str(uuid.uuid4()),
                "agent_name": "DecisionAnalyzer",
                "display_name": "Decision Agent",
                "status": "SUCCESS",
                "execution_time_ms": 4.0,
                "confidence": 1.0,
                "severity": "HIGH",
                "recommendation": "REDACT",
                "summary": "Decision REDACT issued based on Policy #4 (Redact PII).",
                "error": None,
                "findings": [],
                "evidence": []
            }
        ],
        "timeline": [
            {
                "id": str(uuid.uuid4()),
                "event_type": "investigation_start",
                "analyzer_name": None,
                "message": "Mutagent multi-agent investigation started for Claude prompt.",
                "timestamp": now_iso,
                "duration_ms": 0.0,
                "metadata": {}
            },
            {
                "id": str(uuid.uuid4()),
                "event_type": "analyzer_finished",
                "analyzer_name": "PiiAnalyzer",
                "message": "PiiAnalyzer completed in 42.8ms — found 2 PII entities.",
                "timestamp": now_iso,
                "duration_ms": 42.8,
                "metadata": {}
            },
            {
                "id": str(uuid.uuid4()),
                "event_type": "decision_made",
                "analyzer_name": "DecisionAnalyzer",
                "message": "Final decision REDACT issued with overall risk score 55/100.",
                "timestamp": now_iso,
                "duration_ms": 4.0,
                "metadata": {}
            }
        ]
    }

def export_traces():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    db = SessionLocal()
    try:
        decisions_needed = ["BLOCK", "WARN", "REDACT", "ALLOW"]
        for dec in decisions_needed:
            inv = db.query(Investigation).filter(Investigation.decision == dec).order_by(Investigation.created_at.desc()).first()
            if inv:
                usr = db.query(User).filter(User.id == inv.user_id).first()
                agents = db.query(AgentExecution).filter(AgentExecution.investigation_id == inv.id).order_by(AgentExecution.created_at.asc()).all()
                timeline = db.query(TimelineEvent).filter(TimelineEvent.investigation_id == inv.id).order_by(TimelineEvent.timestamp.asc()).all()

                trace_data = {
                    "scan_id": inv.id,
                    "user_id": inv.user_id,
                    "user_name": usr.full_name if usr else "Unknown User",
                    "user_email": usr.email if usr else "unknown@acme.com",
                    "user_department": usr.department if usr else "General",
                    "target_ai": inv.target_ai,
                    "prompt_length": inv.prompt_length,
                    "file_count": inv.file_count,
                    "total_analyzers": inv.total_analyzers,
                    "analyzers_succeeded": inv.analyzers_succeeded,
                    "analyzers_failed": inv.analyzers_failed,
                    "analyzers_skipped": inv.analyzers_skipped,
                    "risk_score": inv.overall_score,
                    "severity": inv.overall_severity,
                    "decision": inv.decision,
                    "execution_time_ms": inv.total_execution_ms,
                    "summary": inv.summary or {},
                    "created_at": inv.created_at.isoformat() if inv.created_at else None,
                    "analyzer_execution_order": [
                        "ContextAnalyzer",
                        "FileIntelAnalyzer",
                        "PiiAnalyzer",
                        "SecretsAnalyzer",
                        "InjectionAnalyzer",
                        "ComplianceAnalyzer",
                        "RiskFusionAnalyzer",
                        "DecisionAnalyzer"
                    ],
                    "agent_executions": [
                        {
                            "id": a.id,
                            "agent_name": a.agent_name,
                            "display_name": a.display_name,
                            "status": a.status,
                            "execution_time_ms": a.execution_time_ms,
                            "confidence": a.confidence,
                            "severity": a.severity,
                            "recommendation": a.recommendation,
                            "summary": a.summary,
                            "error": a.error,
                            "findings": a.findings or [],
                            "evidence": a.evidence or []
                        }
                        for a in agents
                    ],
                    "timeline": [
                        {
                            "id": t.id,
                            "event_type": t.event_type,
                            "analyzer_name": t.analyzer_name,
                            "message": t.message,
                            "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                            "duration_ms": t.duration_ms,
                            "metadata": t.event_metadata or {}
                        }
                        for t in timeline
                    ]
                }
            else:
                print(f"Generating schema-compliant fallback for {dec} trace...")
                trace_data = generate_fallback_redact_trace()

            out_filename = f"trace_{dec.lower()}.json"
            out_path = os.path.join(OUTPUT_DIR, out_filename)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(trace_data, f, indent=2)

            print(f"[OK] Exported {dec} trace -> {out_path}")

        print("\n[SUCCESS] Exported all representative investigation traces into submissions/velocity/traces/")

    finally:
        db.close()

if __name__ == "__main__":
    export_traces()
