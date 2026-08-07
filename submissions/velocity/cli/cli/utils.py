"""
CLI Utility functions: file loading, base64 encoding, terminal output formatting, error display.
"""
import base64
import os
import sys
from pathlib import Path

SUPPORTED_EXTENSIONS = {"txt", "md", "pdf", "docx", "json", "csv", "xlsx", "env"}


def infer_file_extension(filepath: str) -> str:
    name = Path(filepath).name.lower()
    if name == ".env" or name.endswith(".env"):
        return "env"
    if "." in name:
        return name.rsplit(".", 1)[-1]
    return ""


def load_and_encode_file(filepath: str) -> dict:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: '{filepath}'")
    if not path.is_file():
        raise ValueError(f"Path is not a regular file: '{filepath}'")

    ext = infer_file_extension(filepath)
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '.{ext}' for file '{path.name}'. "
            f"Supported file types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    try:
        raw_bytes = path.read_bytes()
    except Exception as exc:
        raise RuntimeError(f"Could not read file '{path.name}': {exc}")

    content_b64 = base64.b64encode(raw_bytes).decode("ascii")
    return {
        "filename": path.name,
        "content_base64": content_b64,
        "size_bytes": len(raw_bytes),
    }


def print_banner(provider_name: str) -> None:
    print("\nPromptShield\n")
    print(f"Provider : {provider_name}")
    print("Status   : Scanning...\n")


def print_scan_result(decision_data: dict) -> None:
    risk_score = decision_data.get("score", 0)
    decision = decision_data.get("decision", "UNKNOWN")

    print(f"Risk Score : {risk_score}\n")
    print(f"Decision : {decision}\n")


def print_warning_details(decision_data: dict) -> None:
    findings = decision_data.get("findings", [])
    file_findings = decision_data.get("file_findings", [])

    print("Detected:\n")
    reasons = []
    for f in findings:
        reasons.append(f.get("reason", f.get("detector", "Security warning")))
    for ff in file_findings:
        if ff.get("action") in ("WARN", "REDACT", "BLOCK") or ff.get("risk") != "NONE":
            reasons.append(f"File '{ff.get('filename')}': {ff.get('reason', 'Risky file attachment')}")

    if not reasons:
        reasons.append(decision_data.get("reason", "Potential security policy warning"))

    for item in sorted(set(reasons)):
        print(f"- {item}")
    print()


def print_block_details(decision_data: dict) -> None:
    reason = decision_data.get("reason", "Security policy violation detected.")
    print("Reason:\n")
    print(f"{reason}\n")


def print_error(message: str) -> None:
    print(f"\nPromptShield Error: {message}\n", file=sys.stderr)
