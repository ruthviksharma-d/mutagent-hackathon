# Business Model

_Illustrative business plan for the PromptShield AI hackathon pitch. Figures
are planning estimates, not audited financials._

## The Problem

Employees at almost every company now use ChatGPT, Claude, or Gemini
directly in their browser — for code review, document drafting, data
analysis, customer support drafts. IT and security teams have no
visibility into what's being pasted into those tools, and existing DLP
(data-loss-prevention) products either don't cover browser-based AI tools
at all, or require network-level proxying that breaks on modern
TLS-pinned SPAs. The result: source code, customer PII, financial
projections, and credentials routinely leave the company with zero
record of it happening.

## Target Customers

- **Mid-size IT services & SaaS companies (200-2,000 employees)** — high
  developer headcount, high AI-tool adoption, existing compliance
  pressure (SOC 2, ISO 27001) but no budget for enterprise DLP suites.
- **Fintech and healthcare companies** — regulatory exposure (RBI/SEBI
  guidelines, HIPAA-equivalent data handling) makes "an employee pasted a
  customer's PAN number into ChatGPT" a board-level risk, not just an IT
  concern.
- **Consulting and BPO firms** — client-confidential data is the entire
  product; a single leaked client deliverable is a contract-ending event.
- **Startups scaling past ~50 employees** — the point where "everyone
  just uses ChatGPT however they want" stops being an acceptable answer
  to a Series A/B investor's security questionnaire.

## Indian Pricing

Priced per-seat, billed monthly, in INR — positioned below typical
enterprise DLP pricing (which is usually USD-denominated and requires an
annual contract) to be accessible to Indian mid-market companies.

| Tier | Price | Seats | Positioning |
|---|---|---|---|
| Starter | ₹1,999/month | Up to 25 | Small teams, single department |
| Growth | ₹9,999/month | Up to 100 | Most common tier — full policy engine + analytics |
| Business | ₹29,999/month | Up to 500 | Department-level reporting, dedicated onboarding |
| Enterprise | Custom | Unlimited | SSO/SAML, SIEM export, custom SLAs |

At the Growth tier this works out to roughly ₹100/seat/month — deliberately
priced to be an easy "yes" for a security team lead to expense without
procurement sign-off, undercutting typical enterprise DLP tools that price
in the $10-25/seat/month range.

## Competitive Advantages

- **Zero workflow change** — employees keep using the AI tools they
  already prefer; there's no new app to adopt, no VPN, no proxy
  configuration.
- **Browser-native interception**, not network-level DLP. Network
  proxying breaks on modern TLS-pinned single-page apps and can't see
  which specific field a piece of text came from; a browser extension can.
- **Explainable, not just binary** — every WARN/BLOCK shows exactly what
  was detected and why, so employees learn what's risky instead of just
  hitting a wall (lower support burden, better long-term behavior change
  than a silent block).
- **Redact, don't just block** — REDACT lets an employee keep working
  with sanitized text instead of losing their prompt entirely, which is
  the difference between a security tool people route around and one they
  tolerate.
- **Self-hostable, lean infrastructure** — no Redis/Kafka/Kubernetes
  requirement means a customer's own DevOps team can stand up the whole
  system in an afternoon, which matters a great deal to security-conscious
  buyers who don't want another vendor holding their prompt data.

## Estimated Infrastructure Cost (per 500-seat deployment)

| Item | Estimate (monthly, INR) |
|---|---|
| Application server (FastAPI, 2 vCPU / 4 GB) | ₹2,500 |
| MySQL 8.4 managed instance | ₹3,500 |
| Object storage (file-scan attachments, logs) | ₹500 |
| Bandwidth | ₹1,000 |
| Monitoring/alerting | ₹500 |
| **Total** | **~₹8,000/month** |

Against Business-tier revenue of ₹29,999/month for that same 500-seat
deployment, infrastructure is roughly 27% of revenue at that tier — leaving
room for support, R&D, and margin even before accounting for the
economies of scale a shared multi-tenant deployment would bring.

## Revenue Projection (illustrative, 24-month)

| Milestone | Customers | Avg. tier | MRR (₹) |
|---|---|---|---|
| Month 6 | 15 | Starter/Growth mix | ~₹1,20,000 |
| Month 12 | 60 | Growth-weighted | ~₹5,50,000 |
| Month 18 | 150 | Growth/Business mix | ~₹15,00,000 |
| Month 24 | 300 | Growth/Business/Enterprise mix | ~₹35,00,000 |

These figures assume a land-and-expand motion: most customers start at
Starter or Growth during a pilot, then upgrade as rollout expands past
the initial pilot department.

## Roadmap

- **Now (hackathon MVP)**: ChatGPT/Claude/Gemini on Chrome, single-tenant
  self-hosted deployment, full detection pipeline, admin dashboard.
- **Next 3 months**: multi-tenant SaaS hosting option, refresh-token auth,
  Firefox/Edge builds.
- **6 months**: Gmail/Outlook/Teams/Slack adapters (the same interception
  pattern extended beyond AI chat tools to any text field), SSO/SAML,
  SIEM export (Splunk/Datadog webhooks).
- **12 months**: fine-grained per-department policy overrides, a managed
  cloud offering with usage-based pricing for very large enterprises,
  compliance certifications (SOC 2 Type II).

## Go-to-Market Strategy

- **Bottom-up pilot motion**: a single security team or engineering
  manager can install the extension and stand up the backend without a
  procurement cycle, using the Starter tier as a frictionless entry point.
- **Compliance-driven outbound**: target companies actively pursuing
  SOC 2 / ISO 27001, where "how do you prevent data exfiltration to
  third-party AI tools" is now a standard audit question with no easy
  existing answer.
- **Developer-community content**: technical writeups of the detection
  pipeline (regex → Presidio → spaCy → secrets → policy engine) aimed at
  security engineers, who are typically the actual buyers even when
  finance signs the invoice.
- **Partnerships**: IT MSPs and consulting firms serving the mid-market as
  a resale/implementation channel, since they already own the
  relationship with the target customer profile above.
