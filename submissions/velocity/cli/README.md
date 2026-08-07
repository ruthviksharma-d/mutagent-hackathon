# PromptShield CLI Wrapper (`psh`)

The PromptShield CLI Wrapper (`psh`) extends enterprise AI firewall protection to CLI tools, supporting **Claude CLI** and **Gemini CLI** out-of-the-box.

Both browser extension traffic and CLI usage share the exact same PromptShield backend security engine, policy enforcement, and audit log tracking.

---

## Architecture

```
User -> PromptShield Browser Extension  \
                                         +---> Existing PromptShield Backend -> Policy Engine -> ALLOW / WARN / REDACT / BLOCK -> Target AI
User -> PromptShield CLI Wrapper (`psh`) /
```

When a user executes `psh claude` or `psh gemini`:
1. The wrapper captures prompt input (via command line arguments, piped stdin, or interactive prompt).
2. It detects and encodes attached files (`txt`, `md`, `pdf`, `docx`, `json`, `csv`, `xlsx`, `.env`).
3. Sends the prompt and file payloads to the PromptShield backend (`POST /api/cli/scan`).
4. Receives the risk assessment, triggered rules, and security decision (`ALLOW`, `WARN`, `REDACT`, `BLOCK`).
5. Enforces the decision before invoking the target CLI (`claude` or `gemini`).

---

## Installation & Setup

### 1. Requirements
- Python 3.8+
- PromptShield backend server running (default: `http://localhost:8000`)

### 2. Install CLI Wrapper
Run editable install inside the `submissions/velocity/cli` directory:

```bash
cd submissions/velocity/cli
pip install -e .
```

Alternatively, invoke directly with Python:

```bash
python -m cli.main claude "Your prompt"
```

or using the included launcher scripts:
- Windows: `psh.bat claude "Your prompt"`
- Linux/macOS: `./psh claude "Your prompt"`

---

## Usage Examples

### 1. Basic Scanning (`ALLOW`)
```bash
$ psh claude "What is the capital of France?"

PromptShield

Provider : Claude
Status   : Scanning...

Risk Score : 0

Decision : ALLOW

Launching Claude...
```

### 2. Scanning with File Attachments
Every attached file gets its own independent risk assessment (`file_findings` in the API response) in addition to the overall prompt+files decision — so a batch upload doesn't have to be all-or-nothing. A bare `.env` file, for example, is flagged `BLOCK`/`CRITICAL` on its own file-identity risk alone (see `backend/ai/file_risk.py`), even if the overall prompt decision comes back as `REDACT` because the file-identity score is weighted down alongside every other analyzer's contribution in the aggregate risk fusion:

```bash
$ psh gemini "Analyze attached project configuration" -f config.env

PromptShield

Provider : Gemini
Status   : Scanning...

Risk Score : 56

Decision : REDACT

File 'config.env': BLOCK (CRITICAL) — Environment file, frequently contains live
API keys, database credentials, and secrets.

Sensitive data detected and redacted by PromptShield policy.
```

### 3. Policy Warning (`WARN`)
`WARN` is issued either when the aggregate risk score lands in the `MEDIUM` band (25-49), or when an admin-authored policy explicitly maps a detection category to `WARN` (the default seed data includes a "Warn on Source Code" policy). Example — two credit-card-shaped numbers in one prompt:

```bash
$ psh claude "Card numbers on file: 4111 1111 1111 1111 and 5500 0000 0000 0004"

PromptShield

Provider : Claude
Status   : Scanning...

Risk Score : 36

Decision : WARN

Detected:
- 2 credit-card-shaped numbers (PII Agent)

Continue? (y/N) y
Launching Claude...
```

### 4. Automatic Redaction (`REDACT`)
`REDACT` fires whenever the default "Redact Personal Data" policy matches (any Presidio/spaCy-classified personal-data entity — person names, physical addresses, SSNs, passport numbers, IBANs) regardless of the aggregate score, or whenever the risk score alone lands in the `HIGH` band (50-74) with no other policy overriding it. Example — a name Presidio's NLP model classifies as `PERSON`:

```bash
$ psh claude "Please loop in my manager Sarah Chen on this"

PromptShield

Provider : Claude
Status   : Scanning...

Decision : REDACT

Sensitive data detected and redacted by PromptShield policy.

Sanitized Prompt:
Please loop in my manager [REDACTED_PERSON] on this

Launching Claude...
```
*(Requires the optional `en_core_web_sm` spaCy model — see the backend `README.md` — since PERSON detection comes from Presidio/spaCy, not a regex pattern. Without it, this specific example scores `LOW`/`ALLOW` instead.)*

### 5. Policy Block (`BLOCK`)
If live AWS keys or hardcoded secrets are detected:

```bash
$ psh gemini "AWS secret: AKIAIOSFODNN7EXAMPLE"

PromptShield

Provider : Gemini
Status   : Scanning...

Risk Score : 90

Decision : BLOCK

Reason:
AWS Secret Key detected.

Action blocked by PromptShield policy. Execution aborted.
```

---

## Configuration

CLI settings can be configured via environment variables or in `~/.promptshield/config.json`:

```json
{
  "backend_url": "http://localhost:8000",
  "timeout": 30,
  "api_token": "YOUR_JWT_TOKEN"
}
```

Environment variables:
- `PROMPTSHIELD_BACKEND_URL`: Override backend server URL.
- `PROMPTSHIELD_API_TOKEN`: Set authorization Bearer token.
- `PROMPTSHIELD_TIMEOUT`: Set HTTP request timeout in seconds.

---

## Extending Providers

Adding support for new AI CLIs (e.g. OpenAI CLI, Ollama, etc.) requires implementing a single class inheriting from `BaseCLIProvider`:

```python
from cli.providers.base import BaseCLIProvider

class OpenAIProvider(BaseCLIProvider):
    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def binary_name(self) -> str:
        return "openai"

    def execute(self, prompt: str, extra_args: list[str] = None) -> int:
        # launch binary with prompt
        ...
```

Then register it in `cli/main.py` in the `PROVIDERS` dict.
