# Project Structure

```
firewall appln/
│
├── backend/                          FastAPI + MySQL detection service
│   ├── ai/                           Detection engine (9-stage pipeline)
│   │   ├── normalizer.py
│   │   ├── regex_detector.py
│   │   ├── presidio_detector.py
│   │   ├── spacy_detector.py
│   │   ├── code_detector.py
│   │   ├── keyword_detector.py
│   │   ├── secret_detector.py
│   │   ├── file_scanner.py
│   │   ├── semantic_classifier.py
│   │   ├── risk_engine.py
│   │   ├── policy_engine.py
│   │   ├── decision_engine.py
│   │   ├── redactor.py
│   │   ├── pipeline.py               Orchestrates all of the above
│   │   └── nlp_loader.py             Lazy spaCy model loader (degrades gracefully if missing)
│   ├── auth/                         Password hashing, JWT issuing, RBAC dependencies
│   ├── config/                       Pydantic settings (env-driven)
│   ├── middleware/                   Request logging
│   ├── models/                       SQLAlchemy models: User, Policy, CompanyKeyword, AuditLog, OrgSettings
│   ├── routers/                      auth, health, scan, dashboard, analytics, prompt_logs, policies, employees, settings
│   ├── schemas/                      Pydantic request/response models, incl. the shared DetectionResult
│   ├── services/                     Business logic shared by routers (analytics, employees, settings, audit, policy, keyword)
│   ├── seed.py                       Idempotent demo-data seeder
│   ├── main.py                       FastAPI app entrypoint, CORS, router registration
│   ├── database.py                   SQLAlchemy engine/session/Base
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                          (gitignored — created by you)
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
│       ├── pages/                    LandingPage, LoginPage, DashboardPage, PromptLogsPage, PoliciesPage, EmployeesPage, AnalyticsPage, SettingsPage, NotFoundPage
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
│   └── PROJECT_STRUCTURE.md          (this file)
│
├── README.md
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
