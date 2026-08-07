# Project Structure

```
submissions/velocity/
│
├── backend/                          FastAPI + MySQL detection service
│   ├── ai/                           Detector functions + legacy sequential orchestrator
│   │   ├── normalizer.py
│   │   ├── regex_detector.py
│   │   ├── presidio_detector.py
│   │   ├── spacy_detector.py
│   │   ├── code_detector.py
│   │   ├── keyword_detector.py
│   │   ├── secret_detector.py
│   │   ├── file_scanner.py
│   │   ├── file_risk.py              File-identity risk (bare .env, id_rsa, docker-compose.yml, etc.)
│   │   ├── semantic_classifier.py
│   │   ├── risk_engine.py
│   │   ├── policy_engine.py
│   │   ├── decision_engine.py
│   │   ├── redactor.py
│   │   ├── pipeline.py               run_pipeline_for_user() — delegates to mutagent/engine.py;
│   │   │                             also keeps the legacy sequential run_pipeline() for direct callers
│   │   └── nlp_loader.py             Lazy spaCy model loader (degrades gracefully if missing)
│   ├── mutagent/                     Multi-agent investigation engine (primary detection path)
│   │   ├── engine.py                 InvestigationEngine — auto-discovers & orchestrates analyzers
│   │   ├── workflow.py                5-stage workflow graph (context → file intel → parallel analysis → risk fusion → decision)
│   │   ├── context.py                Builds InvestigationContext (one DB read upfront)
│   │   ├── models.py                 InvestigationContext, AnalyzerResult, Evidence, TimelineEvent, DEFAULT_RISK_WEIGHTS
│   │   ├── trace.py                  Persists investigation/agent_execution/timeline_event rows
│   │   └── analyzers/                ContextAnalyzer, FileIntelAnalyzer, PiiAnalyzer, SecretsAnalyzer,
│   │                                 InjectionAnalyzer, ComplianceAnalyzer, RiskFusionAnalyzer, DecisionAnalyzer
│   ├── auth/                         Password hashing, JWT issuing, RBAC dependencies
│   ├── config/                       Pydantic settings (env-driven)
│   ├── middleware/                   Request logging, auth rate limiting
│   ├── models/                       SQLAlchemy models: User, Policy, CompanyKeyword, AuditLog, OrgSettings,
│   │                                 Investigation, AgentExecution, TimelineEvent
│   ├── routers/                      auth, health, scan, cli, dashboard, analytics, prompt_logs,
│   │                                 policies, employees, settings, investigations
│   ├── schemas/                      Pydantic request/response models, incl. the shared DetectionResult, FileFindingSummary
│   ├── services/                     Business logic shared by routers (analytics, employees, settings, audit, policy, keyword)
│   ├── tests/                        pytest suite, incl. tests/mutagent/ (engine/analyzer/trace tests) and tests/test_cli.py
│   ├── seed.py                       Idempotent demo-data seeder (users, policies, company keywords)
│   ├── seed_investigations.py        Seeds sample investigation traces for the Security Investigations Console
│   ├── main.py                       FastAPI app entrypoint, CORS, router registration
│   ├── database.py                   SQLAlchemy engine/session/Base
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                          (gitignored — created by you)
│
├── cli/                              PromptShield CLI (`psh`) — protects Claude CLI / Gemini CLI
│   ├── cli/
│   │   ├── main.py                   Argument parsing, one-shot & interactive modes, decision enforcement
│   │   ├── backend.py                BackendClient — calls POST /api/cli/scan
│   │   ├── config.py                 Env vars + ~/.promptshield/config.json
│   │   ├── utils.py                  File loading/encoding, terminal output formatting
│   │   └── providers/                BaseCLIProvider + ClaudeProvider, GeminiProvider
│   ├── psh / psh.bat                 Launcher scripts (python -m cli.main)
│   ├── setup.py                      console_scripts entry point (`psh = cli.main:main`)
│   └── README.md
│
├── admin-dashboard/                  React 19 + Vite + TypeScript + Tailwind v4
│   ├── public/
│   │   └── favicon.svg
│   └── src/
│       ├── components/
│       │   ├── ui/                   Button, Card, Badge, Drawer, Pagination, Select, Toggle, Skeleton, EmptyState, ErrorState, ConfirmDialog, Input
│       │   ├── layout/               AppLayout, Navbar, Sidebar, ProtectedRoute
│       │   ├── Logo.tsx               Shared brand mark
│       │   ├── StatusBadges.tsx        ActionBadge, RiskBadge, ExtensionStatusBadge
│       │   └── PolicyFormModal.tsx
│       ├── context/                  AuthContext, ThemeContext
│       ├── lib/                      adminApi.ts (typed API client), format.ts, utils.ts
│       ├── pages/                    LandingPage, LoginPage, DashboardPage, InvestigationsPage, InvestigationDetailPage,
│       │                             PromptLogsPage, PoliciesPage, EmployeesPage, AnalyticsPage, SettingsPage, NotFoundPage
│       ├── types/                    TS mirrors of backend Pydantic schemas
│       ├── App.tsx                   Route table
│       └── main.tsx                  React entrypoint
│
├── browser-extension/                Manifest V3 + React 19 + Vite + TypeScript
│   ├── public/
│   │   ├── manifest.json
│   │   └── icons/                    icon16.png, icon48.png, icon128.png
│   ├── scripts/
│   │   └── generate_icons.py         Regenerates the toolbar icons from the shared brand mark
│   └── src/
│       ├── adapters/                 SiteAdapter implementations: chatgpt.ts, claude.ts, gemini.ts, observe.ts, types.ts, index.ts
│       ├── background/               Service worker: JWT check, health polling, protection toggle
│       ├── content/
│       │   ├── index.ts              Orchestration: intercept submit → scan → act on decision
│       │   └── ui/                   App.tsx, ModalShell, WarnModal, BlockModal, RedactToast, RiskAnalysisPanel, store.ts, mount.tsx, content.css
│       ├── popup/                    Popup UI: App.tsx, main.tsx, index.css
│       ├── services/                 api.ts (backend client + retry), theme.ts
│       ├── types/                    messages.ts (the ExtensionMessage contract)
│       └── utils/                    dom.ts, jwt.ts, labels.ts, org.ts
│
├── docs/                             This documentation suite
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   ├── API_DOCUMENTATION.md
│   ├── EXTENSION_ARCHITECTURE.md
│   ├── BUSINESS_MODEL.md
│   ├── architecture.md, workflow.md, investigation_flow.md,
│   │   security_model.md, evaluation_results.md   (mirror the root-level docs of the same name)
│   └── PROJECT_STRUCTURE.md          (this file)
│
├── README.md                         Project overview, architecture, screenshots, setup for browser + CLI
├── USING.md                          Day-to-day usage guide (dashboard, extension, CLI)
├── MANUAL_TESTING_GUIDE.md           Step-by-step CLI verification guide
├── architecture.md, workflow.md, investigation_flow.md,
│   security_model.md, evaluation.md,
│   evaluation_results.md             Root-level copies of the docs listed above
└── .gitignore
```

## Conventions

- **Backend**: one module per responsibility inside `ai/`, `services/`,
  and `routers/` — routers stay thin (auth + validation + calling a
  service), business logic and SQL aggregation live in `services/`.
- **Frontend (both apps)**: `@/` resolves to `src/` (see `tsconfig.app.json`
  `paths` + `vite.config.ts` `resolve.alias`). Shared primitives live in
  `components/ui/`; page-specific composition lives in `pages/`.
- **No dead code**: `tsconfig.app.json` enables `noUnusedLocals` and
  `noUnusedParameters` in both frontend apps, so an unused import fails
  the build rather than silently accumulating.
- **Naming**: React components and their files are `PascalCase.tsx`;
  hooks, utilities, and services are `camelCase.ts`.
