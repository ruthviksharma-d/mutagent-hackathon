"""
PromptShield AI - Backend entrypoint (Milestone 4: full admin dashboard APIs).

Run locally:
    uvicorn main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from database import Base, engine
from middleware.logging import RequestLoggingMiddleware
from middleware.rate_limit import AuthRateLimitMiddleware
from routers import auth as auth_router
from routers import health as health_router
from routers import scan as scan_router
from routers import dashboard as dashboard_router
from routers import analytics as analytics_router
from routers import prompt_logs as prompt_logs_router
from routers import policies as policies_router
from routers import employees as employees_router
from routers import settings as settings_router
from routers import investigations as investigations_router
from routers import cli as cli_router
from routers import vscode as vscode_router

# Import models so they're registered on Base.metadata before create_all()
import models  # noqa: F401

settings = get_settings()

_INSECURE_DEFAULT_JWT_SECRET = "insecure-dev-secret-change-me"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Milestone 6 hardening: refuse to boot in production with the
    # placeholder JWT secret still in place - this is the single most
    # important secret in the system (it can mint valid admin tokens) and
    # a config-only mistake here should fail loudly at startup, not
    # silently ship an exploitable deployment.
    if settings.ENVIRONMENT == "production" and settings.JWT_SECRET_KEY == _INSECURE_DEFAULT_JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET_KEY is still set to the insecure development default. "
            "Set a long, random JWT_SECRET_KEY in your production .env before starting the app."
        )

    Base.metadata.create_all(bind=engine)

    # Lightweight schema update for existing database tables
    from sqlalchemy import text
    with engine.begin() as conn:
        for col_name in ("risk_weights", "enabled_analyzers"):
            try:
                conn.execute(text(f"ALTER TABLE org_settings ADD COLUMN {col_name} JSON NULL"))
            except Exception:
                pass

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI Firewall for enterprise LLM usage - prompt inspection, redaction, and policy enforcement.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthRateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(scan_router.router)
app.include_router(dashboard_router.router)
app.include_router(analytics_router.router)
app.include_router(prompt_logs_router.router)
app.include_router(policies_router.router)
app.include_router(employees_router.router)
app.include_router(settings_router.router)
app.include_router(investigations_router.router)
app.include_router(cli_router.router)
# Additive-only: read-only policy summary for the VS Code/Antigravity
# extension client (submissions/velocity/vscode-extension). See
# routers/vscode.py for why this is separate from routers/policies.py.
app.include_router(vscode_router.router)


@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} API is running", "docs": "/docs"}
