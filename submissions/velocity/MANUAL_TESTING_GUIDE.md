# PromptShield CLI — Manual End-to-End Testing & Verification Guide

This guide provides step-by-step instructions for installing, configuring, running, and validating the **PromptShield CLI Protection Wrapper (`psh`)** with **Claude CLI** and **Gemini CLI**.

---

## 1. Installation

### PromptShield CLI Installation
From the repository root, navigate to the `cli` folder and install in editable mode:

```bash
cd submissions/velocity/cli
pip install -e .
```

Verify installation:
```bash
psh --help
```
*(Alternative executable scripts included: `psh.bat` on Windows and `./psh` on Linux/macOS).*

### Target AI CLI Installations
To test real CLI execution:

- **Claude CLI**:
  ```bash
  npm install -g @anthropic-ai/claude-code
  claude --version
  ```
- **Gemini CLI**:
  ```bash
  npm install -g @google/gemini-cli
  gemini --version
  ```

---

## 2. Starting Backend Server & Health Check

Navigate to the `backend` directory and start the FastAPI server:

```bash
cd submissions/velocity/backend
.\venv\Scripts\activate        # Linux/macOS: source venv/bin/activate
python -m uvicorn main:app --reload --port 8000
```

### Health Check
Verify backend is healthy:
```bash
curl http://localhost:8000/health
```
Expected Output:
```json
{"status": "ok", "service": "PromptShield API", "version": "1.0.0"}
```

---

## 3. Basic One-Shot Decision Tests

### 1. `ALLOW` Decision Test
Prompt with clean, safe text:
```bash
psh claude "What is the capital of France?"
```
Expected Output:
```text
PromptShield

Provider : Claude
Status   : Scanning...

Risk Score : 0

Decision : ALLOW

Launching Claude...
```

### 2. `WARN` Decision Test
`WARN` fires when the aggregate risk score lands in the `MEDIUM` band (25-49), or when a policy explicitly maps a category to `WARN` (the seeded "Warn on Source Code" policy). A prompt with two credit-card-shaped numbers is a reliable, regex-only trigger for the score-based path (no NLP model required):
```bash
psh claude "Card numbers on file: 4111 1111 1111 1111 and 5500 0000 0000 0004"
```
Expected Output:
```text
PromptShield

Provider : Claude
Status   : Scanning...

Risk Score : 36

Decision : WARN

Detected:
- 2 credit-card-shaped numbers (PII Agent)

Continue? (y/N)
```
- Entering `y` continues and launches Claude CLI.
- Entering `n` aborts execution cleanly without invoking AI.

### 3. `REDACT` Decision Test
`REDACT` fires when the seeded "Redact Personal Data" policy matches (any Presidio/spaCy-classified name, address, SSN, passport, or IBAN — requires the optional `en_core_web_sm` spaCy model), or when the aggregate score alone lands in the `HIGH` band (50-74) with no other policy overriding it. A single email or phone number alone stays `LOW` severity and is `ALLOW`ed, not redacted — redaction needs either the PII policy or enough combined signal to cross into `HIGH`. A bare `.env`/config file attachment is a reliable way to trigger `HIGH`/`REDACT` at the prompt level (see the file attachment test below) without depending on the optional NLP model.

With the spaCy model installed, a name Presidio/spaCy tags as `PERSON` also redacts via the seeded policy regardless of score:
```bash
psh claude "Please loop in my manager Sarah Chen on this"
```
Expected Output:
```text
PromptShield

Provider : Claude
Status   : Scanning...

Decision : REDACT

Sensitive data detected and redacted by PromptShield policy.

Sanitized Prompt:
Please loop in my manager [REDACTED_PERSON] on this

Launching Claude...
```

### 4. `BLOCK` Decision Test
Prompt containing a live credential or hardcoded AWS secret key:
```bash
psh gemini "My AWS key is AKIAIOSFODNN7EXAMPLE"
```
Expected Output:
```text
PromptShield

Provider : Gemini
Status   : Scanning...

Risk Score : 90

Decision : BLOCK

Reason:
secrets (CRITICAL, +45): detect-secrets found: AWS Access Key.

Action blocked by PromptShield policy. Execution aborted.
```
*(Target AI CLI is NEVER launched and prompt never leaves the local machine).*

---

## 4. Interactive Multi-Turn Chat Testing

To start an interactive chat session, run `psh` without prompt arguments:

```bash
psh claude
```

Expected Output & Session Interaction:
```text
PromptShield Ready (Intercepting all prompts for Claude)
Type 'exit' or 'quit' to end session.

> hello

[PromptShield Scanning...]
Risk Score : 0
Decision : ALLOW

Launching Claude...
Hello! How can I assist you today?

> Card numbers on file: 4111 1111 1111 1111 and 5500 0000 0000 0004

[PromptShield Scanning...]
Risk Score : 36
Decision : WARN

Detected:
- 2 credit-card-shaped numbers (PII Agent)

Continue? (y/N) y
Launching Claude...
Understood — I won't store those card numbers in plain text.

> exit
Exiting PromptShield session.
```

*(Every prompt typed in the `> ` loop is intercepted, scanned by PromptShield backend, decision-enforced, and logged).*

---

## 5. File Attachment Scanning Tests

Test attached file scanning across supported formats (`txt`, `md`, `pdf`, `docx`, `json`, `csv`, `xlsx`, `.env`, plus source code and config formats — see the CLI `README.md` for the full list).

Every attached file also gets its own independent risk assessment (returned as `file_findings` in the API response and shown per-file on the Admin Dashboard), separate from the overall prompt+files decision — this is what lets a batch upload flag just the risky file instead of vetoing the whole batch. A bare `.env` file is a reliable test case: its file-identity risk alone (regardless of content) is `BLOCK`/`CRITICAL` at the per-file level, while the overall prompt decision can land on `REDACT` once that identity-risk score is combined with every other analyzer's contribution:

```bash
psh gemini "Analyze attached project configuration" -f config.env
```

Expected Output:
```text
PromptShield

Provider : Gemini
Status   : Scanning...

Risk Score : 56

Decision : REDACT

File 'config.env': BLOCK (CRITICAL) — Environment file, frequently contains live
API keys, database credentials, and secrets.

Sensitive data detected and redacted by PromptShield policy.
```

Verify on the Admin Dashboard (Prompt Logs → this scan → file attachments) that `config.env` shows its own `action: BLOCK` / `risk: CRITICAL`, independent of the overall `REDACT` decision on the scan itself.

---

## 6. Failure & Error Handling Tests

Verify that errors produce clean, helpful messages with **zero Python tracebacks**:

### 1. Backend Server Offline
Stop the backend server and run:
```bash
psh claude "Hello"
```
Expected Output:
```text
PromptShield Error: PromptShield backend unavailable at 'http://localhost:8000'. Ensure the backend server is running (uvicorn main:app --reload).
```

### 2. Missing Provider Binary
Attempt to run a non-installed provider:
```bash
psh claude "Hello"   # (If claude CLI is not installed on PATH)
```
Expected Output:
```text
PromptShield Error: Claude CLI ('claude') is not installed or not found in system PATH.
```

### 3. Unsupported File Extension
Attach an unsupported file:
```bash
psh claude "Check file" -f payload.exe
```
Expected Output:
```text
PromptShield Error: Unsupported file type '.exe' for file 'payload.exe'. Supported file types: csv, docx, env, json, md, pdf, txt, xlsx
```

### 4. Keyboard Interrupt (`Ctrl+C`)
Press `Ctrl+C` during an interactive session:
```text
> ^C

Session ended by user.
```

---

## 7. Admin Dashboard Audit Log Validation

1. Open the Admin Dashboard: `http://localhost:5173`.
2. Login with default credentials (`admin@promptshield.ai` / `Admin@12345`).
3. Navigate to **Prompt Logs** or **Dashboard**.
4. Verify that each CLI scan generates a new Audit Log row containing:
   - **Timestamp**: Current UTC timestamp.
   - **Website / Provider**: `"Claude CLI"` or `"Gemini CLI"`.
   - **Decision**: `ALLOW`, `WARN`, `REDACT`, or `BLOCK`.
   - **Risk Score**: Calculated aggregate risk score.
   - **Triggered Rules**: List of triggered detectors and policy reasons.
   - **File Attachments**: File count, filenames, categories, and per-file risk metadata.

---

## 8. Success Checklist

- [x] **Browser PromptShield intact**: Browser extension and `/api/scan` endpoint work unchanged.
- [x] **Real CLI Launch**: `psh claude` and `psh gemini` resolve and launch real installed CLI binaries.
- [x] **Every Prompt Intercepted**: Multi-turn interactive mode (`> ` loop) intercepts 100% of prompts.
- [x] **Decision Engine**: `ALLOW`, `WARN`, `REDACT`, `BLOCK` enforced accurately.
- [x] **File Attachments**: Supports `txt`, `md`, `pdf`, `docx`, `json`, `csv`, `xlsx`, `.env`.
- [x] **Audit Trail**: Audit logs written to database and displayed on Admin Dashboard.
- [x] **Zero Stack Traces**: All network, timeout, missing binary, and keyboard interrupt exceptions handled cleanly.
