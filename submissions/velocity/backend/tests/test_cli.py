"""
Tests for PromptShield CLI integration:
- Backend /api/cli/scan API endpoint
- Audit logging for CLI providers (Claude CLI, Gemini CLI)
- File scanning for CLI attachments (txt, md, pdf, docx, json, csv, xlsx, .env)
- Provider abstraction (BaseCLIProvider, ClaudeProvider, GeminiProvider)
- CLI utils and file encoding helpers
"""
import base64
import os
import sys
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from database import get_db, Base, engine, SessionLocal
from models.user import User, UserRole
from models.audit_log import AuditLog
from auth.security import hash_password

# Add cli directory to sys.path for testing cli package imports
CLI_DIR = Path(__file__).resolve().parent.parent.parent / "cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from cli.providers.base import BaseCLIProvider
from cli.providers.claude import ClaudeProvider
from cli.providers.gemini import GeminiProvider
from cli.utils import infer_file_extension, load_and_encode_file, SUPPORTED_EXTENSIONS
from cli.backend import BackendClient


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Ensure default admin user exists
        user = db.scalar(select(User).where(User.email == "testadmin@promptshield.ai"))
        if not user:
            user = User(
                email="testadmin@promptshield.ai",
                full_name="Test Admin",
                hashed_password=hash_password("Password123!"),
                role=UserRole.ADMIN,
                department="Security",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_cli_scan_allow(client, db_session):
    response = client.post(
        "/api/cli/scan",
        json={"prompt": "What is the capital of France?", "site": "Claude CLI"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "ALLOW"
    assert data["risk"] == "NONE" or data["risk"] == "LOW"

    # Verify audit log recorded under provider "Claude CLI"
    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.website == "Claude CLI").order_by(AuditLog.created_at.desc())
    )
    assert audit is not None
    assert audit.original_prompt == "What is the capital of France?"


def test_cli_scan_block_secrets(client, db_session):
    response = client.post(
        "/api/cli/scan",
        json={"prompt": "Here is my secret AWS key: AKIAIOSFODNN7EXAMPLE", "site": "Gemini CLI"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert "AWS" in data["reason"] or "Secret" in data["reason"] or "policy" in data["reason"].lower()

    # Verify audit log recorded under provider "Gemini CLI"
    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.website == "Gemini CLI").order_by(AuditLog.created_at.desc())
    )
    assert audit is not None
    assert audit.action == "BLOCK"


def test_cli_scan_attached_file(client, db_session):
    content = "password = supersecret123"
    b64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")

    response = client.post(
        "/api/cli/scan",
        json={
            "prompt": "Analyze this file",
            "site": "Claude CLI",
            "files": [
                {
                    "filename": "config.env",
                    "content_base64": b64_content,
                    "mime_type": "text/plain",
                    "size_bytes": len(content),
                }
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["file_findings"]) == 1
    assert data["file_findings"][0]["filename"] == "config.env"


def test_provider_abstractions():
    claude = ClaudeProvider()
    gemini = GeminiProvider()

    assert claude.name == "Claude"
    assert claude.binary_name == "claude"
    assert isinstance(claude, BaseCLIProvider)

    assert gemini.name == "Gemini"
    assert gemini.binary_name == "gemini"
    assert isinstance(gemini, BaseCLIProvider)


def test_file_utils():
    assert infer_file_extension("test.txt") == "txt"
    assert infer_file_extension("README.md") == "md"
    assert infer_file_extension(".env") == "env"
    assert infer_file_extension("data.csv") == "csv"

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write("# Hello Markdown")
        tmp_path = tmp.name

    try:
        encoded = load_and_encode_file(tmp_path)
        assert encoded["filename"] == Path(tmp_path).name
        assert "content_base64" in encoded
        decoded = base64.b64decode(encoded["content_base64"]).decode("utf-8")
        assert decoded == "# Hello Markdown"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_unsupported_file_type():
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
        tmp.write(b"\x00\x01\x02")
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_and_encode_file(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_provider_missing_executable():
    class DummyProvider(BaseCLIProvider):
        @property
        def name(self) -> str:
            return "NonExistentAI"

        @property
        def binary_name(self) -> str:
            return "non_existent_binary_12345"

        def execute(self, prompt: str, extra_args=None) -> int:
            if not self.is_installed():
                return 127
            return 0

    dummy = DummyProvider()
    assert dummy.is_installed() is False
    assert dummy.get_executable_path() is None
    assert dummy.execute("test") == 127

