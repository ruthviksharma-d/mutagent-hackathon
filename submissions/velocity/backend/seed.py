"""
Seed script: creates a default admin user, a starter set of enabled
policies, default company keywords, a full roster of demo employees across
multiple departments, org settings, and ~30 days of realistic prompt-scan
history - so the admin dashboard (Milestones 4-5) has real MySQL rows to
query on a fresh checkout instead of staring at an empty database, and the
"Demo Organization" looks genuinely alive for a hackathon walkthrough. This
is the "use seed data where necessary" the spec calls for; every
dashboard/analytics number is a live aggregate query over these rows, not
a hardcoded value.

Usage:
    python seed.py
"""
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from database import Base, engine, SessionLocal
from auth.security import hash_password
from models.user import User, UserRole
from models.policy import Policy
from models.company_keyword import CompanyKeyword
from models.audit_log import AuditLog
from services.settings_service import get_or_create_settings
import models  # noqa: F401

DEFAULT_ADMIN_EMAIL = "admin@promptshield.ai"
DEFAULT_ADMIN_PASSWORD = "Admin@12345"

DEFAULT_POLICIES = [
    dict(
        name="Block Secrets",
        description="Deny any prompt containing a live credential found by detect-secrets.",
        priority=10,
        detection_type="secrets",
        action="BLOCK",
    ),
    dict(
        name="Block Cloud/API Keys",
        description="Deny prompts containing AWS keys, GitHub tokens, OpenAI/Google API keys, or JWTs.",
        priority=20,
        detection_type="api_key",
        action="BLOCK",
    ),
    dict(
        name="Block Confidential Company Terms",
        description="Deny prompts referencing highly sensitive internal project codenames or classifications.",
        priority=30,
        detection_type="company_keyword",
        action="WARN",
    ),
    dict(
        name="Redact Personal Data",
        description="Redact PII identified by Presidio (names, addresses, phone numbers, etc.) rather than blocking outright.",
        priority=40,
        detection_type="pii",
        action="REDACT",
    ),
    dict(
        name="Warn on Source Code",
        description="Warn employees pasting source code into public AI tools, without blocking their work.",
        priority=50,
        detection_type="source_code",
        action="WARN",
    ),
]

DEFAULT_KEYWORDS = [
    "Project Phoenix",
    "Revenue2026",
    "Confidential",
    "InternalOnly",
    "PromptShield",
]

DEFAULT_EMPLOYEES = [
    dict(email="priya.sharma@acme.com", full_name="Priya Sharma", department="Engineering", role=UserRole.EMPLOYEE),
    dict(email="arjun.kapoor@acme.com", full_name="Arjun Kapoor", department="Engineering", role=UserRole.EMPLOYEE),
    dict(email="rohan.mehta@acme.com", full_name="Rohan Mehta", department="Engineering", role=UserRole.EMPLOYEE),
    dict(email="ishaan.verma@acme.com", full_name="Ishaan Verma", department="Engineering", role=UserRole.EMPLOYEE),
    dict(email="kavya.reddy@acme.com", full_name="Kavya Reddy", department="Data Science", role=UserRole.EMPLOYEE),
    dict(email="aditya.joshi@acme.com", full_name="Aditya Joshi", department="Data Science", role=UserRole.EMPLOYEE),
    dict(email="megha.rao@acme.com", full_name="Megha Rao", department="Marketing", role=UserRole.EMPLOYEE),
    dict(email="sanya.malhotra@acme.com", full_name="Sanya Malhotra", department="Marketing", role=UserRole.EMPLOYEE),
    dict(email="vikram.nair@acme.com", full_name="Vikram Nair", department="Sales", role=UserRole.EMPLOYEE),
    dict(email="ritika.bose@acme.com", full_name="Ritika Bose", department="Sales", role=UserRole.EMPLOYEE),
    dict(email="ananya.iyer@acme.com", full_name="Ananya Iyer", department="Finance", role=UserRole.SECURITY_ANALYST),
    dict(email="karan.desai@acme.com", full_name="Karan Desai", department="Finance", role=UserRole.EMPLOYEE),
    dict(email="neha.gupta@acme.com", full_name="Neha Gupta", department="Legal", role=UserRole.SECURITY_ANALYST),
    dict(email="siddharth.rao@acme.com", full_name="Siddharth Rao", department="Legal", role=UserRole.EMPLOYEE),
    dict(email="pooja.menon@acme.com", full_name="Pooja Menon", department="Human Resources", role=UserRole.EMPLOYEE),
    dict(email="dev.patel@acme.com", full_name="Dev Patel", department="Product", role=UserRole.EMPLOYEE),
    dict(email="tanvi.chopra@acme.com", full_name="Tanvi Chopra", department="Product", role=UserRole.EMPLOYEE),
    dict(email="varun.saxena@acme.com", full_name="Varun Saxena", department="Customer Support", role=UserRole.EMPLOYEE),
    dict(email="riya.kulkarni@acme.com", full_name="Riya Kulkarni", department="Customer Support", role=UserRole.EMPLOYEE),
    dict(email="aman.singh@acme.com", full_name="Aman Singh", department="Operations", role=UserRole.SECURITY_ANALYST),
]

WEBSITES = ["ChatGPT", "Claude", "Gemini"]

# (action, risk, score_range, reason, detector_summaries)
SCENARIOS = [
    ("ALLOW", "NONE", (0, 5), "No sensitive content detected across regex, PII, NER, code, keyword, or secret scans.", []),
    ("ALLOW", "NONE", (0, 5), "No sensitive content detected across regex, PII, NER, code, keyword, or secret scans.", []),
    ("ALLOW", "LOW", (5, 20), "regex (LOW): Matched: URL.", [("regex", "LOW", 5, "Matched: URL.")]),
    (
        "ALLOW",
        "LOW",
        (5, 15),
        "spacy (LOW): Detected a generic organization name with low confidence.",
        [("spacy", "LOW", 8, "Detected a generic organization name with low confidence.")],
    ),
    (
        "WARN",
        "MEDIUM",
        (25, 45),
        "company_keyword (MEDIUM): Company-sensitive terms found: Project Phoenix.",
        [("company_keyword", "MEDIUM", 40, "Company-sensitive terms found: Project Phoenix.")],
    ),
    (
        "WARN",
        "MEDIUM",
        (25, 45),
        "source_code (MEDIUM): Prompt appears to contain Python source code (confidence 70%).",
        [("source_code", "MEDIUM", 30, "Prompt appears to contain Python source code (confidence 70%).")],
    ),
    (
        "WARN",
        "MEDIUM",
        (30, 50),
        "company_keyword (MEDIUM): Company-sensitive terms found: Revenue2026, Confidential.",
        [("company_keyword", "MEDIUM", 38, "Company-sensitive terms found: Revenue2026, Confidential.")],
    ),
    (
        "WARN",
        "MEDIUM",
        (25, 45),
        "source_code (MEDIUM): Prompt appears to contain JavaScript source code (confidence 65%).",
        [("source_code", "MEDIUM", 28, "Prompt appears to contain JavaScript source code (confidence 65%).")],
    ),
    (
        "REDACT",
        "LOW",
        (10, 25),
        "regex (LOW): Matched: EMAIL, PHONE_NUMBER.",
        [("regex", "LOW", 14, "Matched: EMAIL, PHONE_NUMBER.")],
    ),
    (
        "REDACT",
        "MEDIUM",
        (20, 35),
        "presidio (MEDIUM): PII detected: PERSON, LOCATION.",
        [("presidio", "MEDIUM", 25, "PII detected: PERSON, LOCATION.")],
    ),
    (
        "REDACT",
        "LOW",
        (10, 25),
        "presidio (LOW): PII detected: CREDIT_CARD.",
        [("presidio", "LOW", 18, "PII detected: CREDIT_CARD.")],
    ),
    (
        "BLOCK",
        "CRITICAL",
        (75, 100),
        "Policy 'Block Cloud/API Keys' triggered by detection type 'api_key'.",
        [("regex", "CRITICAL", 45, "Matched: AWS_ACCESS_KEY.")],
    ),
    (
        "BLOCK",
        "CRITICAL",
        (75, 100),
        "Policy 'Block Secrets' triggered by detection type 'secrets'.",
        [("secrets", "CRITICAL", 45, "detect-secrets found: Private Key.")],
    ),
    (
        "BLOCK",
        "CRITICAL",
        (80, 100),
        "Policy 'Block Cloud/API Keys' triggered by detection type 'api_key'.",
        [("regex", "CRITICAL", 45, "Matched: GITHUB_TOKEN, JWT.")],
    ),
    (
        "BLOCK",
        "HIGH",
        (65, 85),
        "Policy 'Block Confidential Company Terms' triggered by detection type 'company_keyword'.",
        [("company_keyword", "HIGH", 42, "Company-sensitive terms found: InternalOnly, Project Phoenix.")],
    ),
]

# Weighted so most traffic is benign, matching a realistic org.
SCENARIO_WEIGHTS = [22, 14, 10, 6, 8, 7, 6, 5, 6, 5, 3, 4, 3, 3, 2]

SAMPLE_PROMPTS = {
    "ALLOW": [
        "What's a good structure for a quarterly OKR doc?",
        "Summarize the benefits of server-side rendering.",
        "Draft a friendly out-of-office reply.",
        "Give me five headline ideas for a product launch blog post.",
        "Explain the difference between REST and GraphQL in simple terms.",
        "Help me write a polite follow-up email after a job interview.",
        "What are some icebreaker questions for a team offsite?",
        "Suggest a workout routine for someone who sits at a desk all day.",
        "How do I convert a CSV file to JSON using Python?",
        "Write a short product description for a wireless charging pad.",
    ],
    "WARN": [
        "Can you review the Project Phoenix rollout plan I pasted below?",
        "Here's a Python function, can you optimize it: def foo(): import os\\n  self.x = 1",
        "Our Revenue2026 targets are attached, can you turn this into a chart summary?",
        "This is Confidential but I need help rephrasing the executive summary.",
        "Here's our internal auth middleware in JavaScript, can you find bugs in it?",
        "Can you refactor this SQL migration script for our internal billing service?",
    ],
    "REDACT": [
        "Reach me at jane.doe@acme.com or 555-201-4432 if you have questions.",
        "My colleague Rahul Mehta from our Bangalore office can confirm this.",
        "Card ending in 4242, can you help me draft a refund request email?",
        "Please loop in priya.sharma@acme.com and call her at 91-98765-43210.",
    ],
    "BLOCK": [
        "Here is my key AKIAABCDEFGHIJKLMNOP, can you help me debug this Terraform script?",
        "-----BEGIN RSA PRIVATE KEY-----\\nMIIEpAIBAAKCAQEA1234567890abcdefgh\\n-----END RSA PRIVATE KEY-----",
        "My GitHub token is ghp_1A2B3C4D5E6F7G8H9I0JklMnOpQrStUvWxYz, can you push this fix for me?",
        "This mentions our InternalOnly Project Phoenix roadmap, can you summarize it for the board deck?",
    ],
}


def seed_admin(db) -> None:
    existing = db.scalar(select(User).where(User.email == DEFAULT_ADMIN_EMAIL))
    if existing:
        print(f"Admin user already exists: {DEFAULT_ADMIN_EMAIL}")
        return
    admin = User(
        email=DEFAULT_ADMIN_EMAIL,
        full_name="PromptShield Admin",
        hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
        role=UserRole.ADMIN,
        department="Security",
    )
    db.add(admin)
    db.commit()
    print(f"Created admin user -> email: {DEFAULT_ADMIN_EMAIL}  password: {DEFAULT_ADMIN_PASSWORD}")


def seed_policies(db) -> None:
    existing_names = {p.name for p in db.scalars(select(Policy)).all()}
    created = 0
    for policy_data in DEFAULT_POLICIES:
        if policy_data["name"] in existing_names:
            continue
        db.add(Policy(enabled=True, **policy_data))
        created += 1
    if created:
        db.commit()
    print(f"Seeded {created} new policies ({len(DEFAULT_POLICIES) - created} already existed).")


def seed_keywords(db) -> None:
    existing = {k.keyword for k in db.scalars(select(CompanyKeyword)).all()}
    created = 0
    for keyword in DEFAULT_KEYWORDS:
        if keyword in existing:
            continue
        db.add(CompanyKeyword(keyword=keyword, enabled=True))
        created += 1
    if created:
        db.commit()
    print(f"Seeded {created} new company keywords ({len(DEFAULT_KEYWORDS) - created} already existed).")


def seed_employees(db) -> list[User]:
    existing_emails = {u.email for u in db.scalars(select(User)).all()}
    created = 0
    for emp in DEFAULT_EMPLOYEES:
        if emp["email"] in existing_emails:
            continue
        db.add(
            User(
                email=emp["email"],
                full_name=emp["full_name"],
                hashed_password=hash_password("Employee@12345"),
                role=emp["role"],
                department=emp["department"],
            )
        )
        created += 1
    if created:
        db.commit()
    print(f"Seeded {created} new employee accounts ({len(DEFAULT_EMPLOYEES) - created} already existed).")
    return list(db.scalars(select(User).where(User.role != UserRole.ADMIN)).all())


def seed_activity(db, employees: list[User], num_entries: int = 260) -> None:
    if db.scalar(select(AuditLog).limit(1)) is not None:
        print("Audit log already has data - skipping activity seeding.")
        return
    if not employees:
        print("No employees to attribute activity to - skipping activity seeding.")
        return

    rng = random.Random(42)
    now = datetime.now(timezone.utc)

    for _ in range(num_entries):
        action, risk, score_range, reason, detectors = rng.choices(SCENARIOS, weights=SCENARIO_WEIGHTS, k=1)[0]
        user = rng.choice(employees)
        website = rng.choice(WEBSITES)
        score = rng.randint(*score_range)
        days_ago = rng.uniform(0, 30)
        created_at = now - timedelta(days=days_ago, hours=rng.uniform(0, 23))
        prompt_pool = SAMPLE_PROMPTS.get(action, SAMPLE_PROMPTS["ALLOW"])
        original_prompt = rng.choice(prompt_pool)
        sanitized_prompt = original_prompt
        if action in ("REDACT", "BLOCK"):
            sanitized_prompt = "[REDACTED_EMAIL] or [REDACTED_PHONE]" if action == "REDACT" else "[REDACTED_API_KEY]"

        triggered_rules = [
            {"detector": d, "severity": s, "score": sc, "reason": r} for d, s, sc, r in detectors
        ]

        entry = AuditLog(
            user_id=user.id,
            website=website,
            original_prompt=original_prompt,
            sanitized_prompt=sanitized_prompt,
            risk=risk,
            score=score,
            action=action,
            reason=reason,
            triggered_rules=triggered_rules,
            created_at=created_at,
        )
        db.add(entry)

        user.prompt_count += 1
        if action != "ALLOW":
            user.violation_count += 1

    db.commit()
    print(f"Seeded {num_entries} sample audit log entries across {len(employees)} employees.")


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_admin(db)
        seed_policies(db)
        seed_keywords(db)
        employees = seed_employees(db)
        seed_activity(db, employees)
        get_or_create_settings(db)
        print("Org settings ready.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
