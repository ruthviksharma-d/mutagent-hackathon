"""
Backend HTTP client communicating with PromptShield POST /api/cli/scan.
"""
import json
import urllib.request
import urllib.error
from typing import Optional


class BackendClient:
    def __init__(self, backend_url: str = "http://localhost:8000", timeout: int = 30, api_token: str = ""):
        self.backend_url = backend_url.rstrip("/")
        self.timeout = timeout
        self.api_token = api_token

    def scan(self, prompt: str, provider_name: str, files: Optional[list] = None) -> dict:
        url = f"{self.backend_url}/api/cli/scan"
        payload = {
            "prompt": prompt,
            "site": provider_name,
            "files": files or [],
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "PromptShield-CLI/1.0",
                **({"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}),
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                response_text = resp.read().decode("utf-8")
                return json.loads(response_text)
        except urllib.error.URLError as exc:
            reason_str = str(getattr(exc, "reason", exc)).lower()
            if "refused" in reason_str or "connect" in reason_str:
                raise ConnectionError(
                    f"PromptShield backend unavailable at '{self.backend_url}'. "
                    "Ensure the backend server is running (uvicorn main:app --reload)."
                )
            elif "timed out" in reason_str:
                raise TimeoutError(f"Backend scan timed out after {self.timeout}s.")
            else:
                raise ConnectionError(f"Network error connecting to PromptShield backend: {exc}")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Backend returned HTTP status {exc.code}: {err_body}")
        except Exception as exc:
            raise RuntimeError(f"Scan failure: {exc}")
