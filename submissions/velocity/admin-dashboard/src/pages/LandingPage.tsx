import { Link } from "react-router-dom"
import { motion, type Variants } from "framer-motion"
import {
  ScanEye,
  Regex,
  FileWarning,
  Users,
  BarChart3,
  ShieldCheck,
  ArrowRight,
  Check,
  Puzzle,
  Moon,
  Sun,
  Server,
  Database,
  LayoutDashboard,
  KeyRound,
  FileCode2,
  Mail,
  MapPin,
} from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Card, CardContent } from "@/components/ui/Card"
import { Logo } from "@/components/Logo"
import { useTheme } from "@/context/ThemeContext"

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
}

function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode
  className?: string
  delay?: number
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-80px" }}
      variants={fadeUp}
      transition={{ delay }}
    >
      {children}
    </motion.div>
  )
}

const PRODUCT_PILLARS = [
  {
    icon: Puzzle,
    title: "Browser Extension",
    desc: "A Manifest V3 extension that watches ChatGPT, Claude, and Gemini in real time and intercepts every prompt before it's sent.",
  },
  {
    icon: Server,
    title: "FastAPI Detection Backend",
    desc: "A nine-stage inspection pipeline — regex, Presidio, spaCy, secrets, source code, keywords, and a policy + risk engine — returns a decision in milliseconds.",
  },
  {
    icon: LayoutDashboard,
    title: "Admin Dashboard",
    desc: "A full security console for your team: live prompt logs, policy authoring, employee risk scores, and analytics — all backed by real MySQL data.",
  },
]

const FEATURES = [
  { icon: ScanEye, title: "Real-time prompt inspection", desc: "Every prompt to ChatGPT, Claude, and Gemini is scanned before it leaves the browser." },
  { icon: Regex, title: "Deep detection pipeline", desc: "Regex, Microsoft Presidio, spaCy NER, secret scanning, and source-code detection in one pass." },
  { icon: FileWarning, title: "Redaction, not just blocking", desc: "Sensitive spans are redacted automatically so employees keep working without losing productivity." },
  { icon: Users, title: "Employee-level visibility", desc: "Department, role, prompt volume, and violation history for every seat in your org." },
  { icon: BarChart3, title: "Security analytics", desc: "Risk distribution, top violations, and website usage trends for security teams." },
  { icon: ShieldCheck, title: "Policy engine", desc: "Author allow / warn / redact / block policies per detection type, with priority ordering." },
]

const STEPS = [
  { step: "1", title: "Employee types a prompt", desc: "In ChatGPT, Claude, or Gemini — no workflow change." },
  { step: "2", title: "Extension intercepts it", desc: "Before submission, the prompt (and any files) is sent to the backend for inspection." },
  { step: "3", title: "Backend scans & decides", desc: "Regex → Presidio → spaCy → secrets → policy engine → risk engine → a decision." },
  { step: "4", title: "Action is enforced", desc: "Allow, warn, redact, or block — with a full audit trail for security teams." },
]

const WORKFLOW_OUTCOMES = [
  { action: "ALLOW", color: "text-success", bg: "bg-success/10", border: "border-success/30", desc: "No risk found — the prompt is sent through untouched." },
  { action: "WARN", color: "text-warning", bg: "bg-warning/10", border: "border-warning/30", desc: "A custom modal explains the risk. Employee can cancel or continue." },
  { action: "REDACT", color: "text-primary", bg: "bg-primary/10", border: "border-primary/30", desc: "Sensitive spans are replaced automatically. The employee re-sends manually." },
  { action: "BLOCK", color: "text-danger", bg: "bg-danger/10", border: "border-danger/30", desc: "Submission is stopped entirely — the AI website never receives it." },
]

const ARCHITECTURE_LAYERS = [
  { icon: Puzzle, title: "Browser Extension", detail: "Manifest V3 · React · site adapters for ChatGPT / Claude / Gemini" },
  { icon: Server, title: "FastAPI Backend", detail: "POST /api/scan · JWT auth · RBAC · SQLAlchemy 2.0" },
  { icon: KeyRound, title: "Detection Engine", detail: "Regex → Presidio → spaCy → Secrets → Source Code → Policy → Risk → Decision" },
  { icon: Database, title: "MySQL 8.4", detail: "Users · Audit Logs · Policies · Company Keywords · Org Settings" },
]

const PRICING = [
  {
    name: "Starter",
    price: "₹1,999",
    period: "/month",
    seats: "Up to 25 users",
    cta: "Start free trial",
    features: ["Core detection pipeline", "ChatGPT + Claude + Gemini", "30-day audit log retention", "Email support"],
  },
  {
    name: "Growth",
    price: "₹9,999",
    period: "/month",
    seats: "Up to 100 users",
    cta: "Start free trial",
    highlighted: true,
    features: ["Everything in Starter", "Full policy engine", "Analytics dashboard", "Priority support"],
  },
  {
    name: "Business",
    price: "₹29,999",
    period: "/month",
    seats: "Up to 500 users",
    cta: "Talk to sales",
    features: ["Everything in Growth", "Department-level reporting", "Custom company keyword lists", "Dedicated onboarding"],
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    seats: "Unlimited users, SSO, SIEM",
    cta: "Contact us",
    features: ["Everything in Business", "SSO / SAML", "SIEM export", "Custom SLAs"],
  },
]

const FAQS = [
  { q: "Do employees have to change how they use ChatGPT?", a: "No. They keep using the original AI websites — the extension works quietly in the background." },
  { q: "Where does the scanning happen?", a: "Prompts are sent to your PromptShield backend for inspection before the AI site ever receives them." },
  { q: "What AI tools are supported today?", a: "ChatGPT, Claude, and Gemini. Firefox/Edge, Gmail, Outlook, Teams, and Slack are on the roadmap." },
  { q: "What happens to a blocked prompt?", a: "It never reaches the AI website. The employee sees a branded modal explaining exactly why, with the triggered policy and detected findings." },
  { q: "Can we write our own detection rules?", a: "Yes — the policy engine lets admins map any detection category (PII, secrets, source code, company keywords, and more) to allow, warn, redact, or block, with priority ordering." },
  { q: "Is our prompt data stored anywhere outside our infrastructure?", a: "No. Everything runs against your own FastAPI backend and MySQL database — PromptShield does not proxy your data through a third party." },
]

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  return (
    <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
      {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  )
}

function BrowserMockupFrame({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-center gap-2 border-b border-border bg-muted/50 px-3 py-2">
        <span className="h-2.5 w-2.5 rounded-full bg-danger/60" />
        <span className="h-2.5 w-2.5 rounded-full bg-warning/60" />
        <span className="h-2.5 w-2.5 rounded-full bg-success/60" />
        <span className="ml-2 truncate rounded bg-background px-2 py-0.5 text-[11px] text-muted-foreground">
          {label}
        </span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <Logo className="h-6 w-6" />
            <span className="text-sm font-semibold">PromptShield AI</span>
          </div>
          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <a href="#product" className="hover:text-foreground">Product</a>
            <a href="#features" className="hover:text-foreground">Features</a>
            <a href="#how-it-works" className="hover:text-foreground">How it works</a>
            <a href="#architecture" className="hover:text-foreground">Architecture</a>
            <a href="#pricing" className="hover:text-foreground">Pricing</a>
            <a href="#faq" className="hover:text-foreground">FAQ</a>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link to="/login">
              <Button size="sm">Sign in</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <div className="mx-auto max-w-3xl text-center">
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-4 inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
          >
            <Puzzle className="h-3.5 w-3.5" /> Chrome extension + enterprise dashboard
          </motion.span>
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05 }}
            className="text-4xl font-semibold tracking-tight sm:text-5xl"
          >
            The AI firewall for teams using ChatGPT, Claude &amp; Gemini
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground"
          >
            Inspect, redact, and control every prompt your employees send to public AI tools —
            without asking them to change a single habit.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="mt-8 flex items-center justify-center gap-3"
          >
            <Link to="/login">
              <Button>
                Get started <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <a href="#how-it-works">
              <Button variant="outline">See how it works</Button>
            </a>
          </motion.div>
        </div>

        <Reveal delay={0.3} className="mx-auto mt-16 max-w-3xl">
          <BrowserMockupFrame label="chatgpt.com">
            <div className="space-y-3">
              <div className="h-3 w-2/3 rounded bg-muted" />
              <div className="h-3 w-1/2 rounded bg-muted" />
              <div className="mt-4 flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/10 p-3">
                <FileWarning className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                <div>
                  <p className="text-sm font-medium text-foreground">Prompt Risk Analysis — WARN (42/100)</p>
                  <p className="text-xs text-muted-foreground">
                    Detected: company-sensitive term "Project Phoenix". Triggered policy: Block Confidential
                    Company Terms. Recommended action: proceed with caution.
                  </p>
                </div>
              </div>
            </div>
          </BrowserMockupFrame>
        </Reveal>
      </section>

      {/* Product overview */}
      <section id="product" className="border-t border-border py-20">
        <div className="mx-auto max-w-6xl px-6">
          <Reveal className="mb-10 text-center">
            <h2 className="text-2xl font-semibold">One product, three tightly-integrated parts</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              PromptShield AI ships as a browser extension, a detection backend, and an admin dashboard —
              deployed together, working as one system.
            </p>
          </Reveal>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {PRODUCT_PILLARS.map((p, i) => (
              <Reveal key={p.title} delay={i * 0.08}>
                <Card className="h-full">
                  <CardContent className="pt-6">
                    <p.icon className="mb-3 h-6 w-6 text-primary" />
                    <h3 className="mb-1 text-sm font-semibold">{p.title}</h3>
                    <p className="text-sm text-muted-foreground">{p.desc}</p>
                  </CardContent>
                </Card>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-t border-border bg-muted/40 py-20">
        <div className="mx-auto max-w-5xl px-6">
          <Reveal className="mb-10 text-center">
            <h2 className="text-2xl font-semibold">How PromptShield works</h2>
          </Reveal>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <Reveal key={s.step} delay={i * 0.08} className="text-center">
                <div className="mx-auto mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                  {s.step}
                </div>
                <h3 className="mb-1 text-sm font-semibold">{s.title}</h3>
                <p className="text-sm text-muted-foreground">{s.desc}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Browser extension workflow */}
      <section className="border-t border-border py-20">
        <div className="mx-auto max-w-6xl px-6">
          <Reveal className="mb-10 text-center">
            <h2 className="text-2xl font-semibold">Browser extension workflow</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Every scan resolves to exactly one of four outcomes, enforced in the browser itself.
            </p>
          </Reveal>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {WORKFLOW_OUTCOMES.map((o, i) => (
              <Reveal key={o.action} delay={i * 0.08}>
                <div className={`rounded-xl border ${o.border} ${o.bg} p-5`}>
                  <p className={`text-sm font-bold tracking-wide ${o.color}`}>{o.action}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{o.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Key features */}
      <section id="features" className="border-t border-border bg-muted/40 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <Reveal className="mb-10 text-center">
            <h2 className="text-2xl font-semibold">Everything security teams need</h2>
          </Reveal>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f, i) => (
              <Reveal key={f.title} delay={(i % 3) * 0.08}>
                <Card className="h-full">
                  <CardContent className="pt-5">
                    <f.icon className="mb-3 h-5 w-5 text-primary" />
                    <h3 className="mb-1 text-sm font-semibold">{f.title}</h3>
                    <p className="text-sm text-muted-foreground">{f.desc}</p>
                  </CardContent>
                </Card>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture diagram */}
      <section id="architecture" className="border-t border-border py-20">
        <div className="mx-auto max-w-5xl px-6">
          <Reveal className="mb-10 text-center">
            <h2 className="text-2xl font-semibold">System architecture</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              No Redis, no Kafka, no Kubernetes — a lean stack built to run anywhere.
            </p>
          </Reveal>
          <div className="flex flex-col items-stretch gap-3">
            {ARCHITECTURE_LAYERS.map((l, i) => (
              <Reveal key={l.title} delay={i * 0.08}>
                <div className="flex items-center gap-4 rounded-xl border border-border bg-card p-4 shadow-sm">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <l.icon className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">{l.title}</p>
                    <p className="truncate text-xs text-muted-foreground">{l.detail}</p>
                  </div>
                </div>
                {i < ARCHITECTURE_LAYERS.length - 1 && (
                  <div className="ml-9 h-4 w-px bg-border" />
                )}
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Product screenshots (styled mockups) */}
      <section className="border-t border-border bg-muted/40 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <Reveal className="mb-10 text-center">
            <h2 className="text-2xl font-semibold">See it in action</h2>
          </Reveal>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Reveal>
              <BrowserMockupFrame label="app.promptshield.ai/dashboard">
                <div className="grid grid-cols-3 gap-2">
                  {["Total prompts", "Security score", "Blocked"].map((label) => (
                    <div key={label} className="rounded-lg border border-border p-3">
                      <p className="text-[10px] text-muted-foreground">{label}</p>
                      <div className="mt-2 h-4 w-10 rounded bg-primary/30" />
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex h-24 items-end gap-1 rounded-lg border border-border p-3">
                  {[40, 65, 30, 80, 55, 70, 45].map((h, idx) => (
                    <div key={idx} className="flex-1 rounded-t bg-primary/40" style={{ height: `${h}%` }} />
                  ))}
                </div>
              </BrowserMockupFrame>
            </Reveal>
            <Reveal delay={0.1}>
              <BrowserMockupFrame label="app.promptshield.ai/prompt-logs">
                <div className="space-y-2">
                  {[
                    { action: "BLOCK", color: "bg-danger/70" },
                    { action: "WARN", color: "bg-warning/70" },
                    { action: "ALLOW", color: "bg-success/70" },
                    { action: "REDACT", color: "bg-primary/70" },
                  ].map((row) => (
                    <div key={row.action} className="flex items-center gap-3 rounded-lg border border-border p-2">
                      <span className={`h-2 w-2 rounded-full ${row.color}`} />
                      <div className="h-2.5 flex-1 rounded bg-muted" />
                      <span className="text-[10px] font-medium text-muted-foreground">{row.action}</span>
                    </div>
                  ))}
                </div>
              </BrowserMockupFrame>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-t border-border py-20">
        <div className="mx-auto max-w-6xl px-6">
          <Reveal className="mb-2 text-center">
            <h2 className="text-2xl font-semibold">Simple, transparent pricing</h2>
          </Reveal>
          <Reveal delay={0.05} className="mb-10 text-center">
            <p className="text-sm text-muted-foreground">
              Built for startups, IT companies, SaaS, healthcare, fintech, and consulting. Prices in INR.
            </p>
          </Reveal>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PRICING.map((tier, i) => (
              <Reveal key={tier.name} delay={i * 0.06}>
                <Card className={`h-full ${tier.highlighted ? "border-primary ring-1 ring-primary" : ""}`}>
                  <CardContent className="pt-5">
                    <h3 className="text-sm font-semibold">{tier.name}</h3>
                    <p className="mt-2 text-2xl font-semibold">
                      {tier.price}
                      <span className="text-sm font-normal text-muted-foreground">{tier.period}</span>
                    </p>
                    <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
                      <Check className="h-3.5 w-3.5 text-success" /> {tier.seats}
                    </p>
                    <ul className="mt-4 space-y-1.5">
                      {tier.features.map((f) => (
                        <li key={f} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                          <Check className="mt-0.5 h-3 w-3 shrink-0 text-success" /> {f}
                        </li>
                      ))}
                    </ul>
                    <Button className="mt-5 w-full" variant={tier.highlighted ? "default" : "outline"} size="sm">
                      {tier.cta}
                    </Button>
                  </CardContent>
                </Card>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="border-t border-border bg-muted/40 py-20">
        <div className="mx-auto max-w-3xl px-6">
          <Reveal className="mb-10 text-center">
            <h2 className="text-2xl font-semibold">Frequently asked questions</h2>
          </Reveal>
          <div className="space-y-6">
            {FAQS.map((f, i) => (
              <Reveal key={f.q} delay={i * 0.04}>
                <h3 className="mb-1 text-sm font-semibold">{f.q}</h3>
                <p className="text-sm text-muted-foreground">{f.a}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Contact */}
      <section id="contact" className="border-t border-border py-20">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <Reveal>
            <h2 className="text-2xl font-semibold">Talk to us</h2>
            <p className="mx-auto mt-2 max-w-xl text-sm text-muted-foreground">
              Want a walkthrough for your security team, or help scoping a rollout across your org?
              Reach out and we'll get back to you.
            </p>
          </Reveal>
          <Reveal delay={0.1} className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a href="mailto:hello@promptshield.ai">
              <Button>
                <Mail className="h-4 w-4" /> hello@promptshield.ai
              </Button>
            </a>
            <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <MapPin className="h-3.5 w-3.5" /> Bengaluru, India
            </span>
          </Reveal>
        </div>
      </section>

      <footer className="border-t border-border py-14">
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-6 sm:grid-cols-4">
          <div className="col-span-2 sm:col-span-1">
            <div className="flex items-center gap-2">
              <Logo className="h-5 w-5" />
              <span className="text-sm font-semibold">PromptShield AI</span>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              The AI firewall for enterprise teams.
            </p>
          </div>
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Product</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><a href="#features" className="hover:text-foreground">Features</a></li>
              <li><a href="#architecture" className="hover:text-foreground">Architecture</a></li>
              <li><a href="#pricing" className="hover:text-foreground">Pricing</a></li>
            </ul>
          </div>
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Company</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><a href="#contact" className="hover:text-foreground">Contact</a></li>
              <li><a href="#faq" className="hover:text-foreground">FAQ</a></li>
              <li><Link to="/login" className="hover:text-foreground">Sign in</Link></li>
            </ul>
          </div>
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Resources</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-center gap-1.5"><FileCode2 className="h-3.5 w-3.5" /> API docs</li>
              <li className="flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" /> Security</li>
            </ul>
          </div>
        </div>
        <div className="mx-auto mt-10 max-w-6xl border-t border-border px-6 pt-6 text-center text-xs text-muted-foreground">
          © 2026 PromptShield AI. Built for enterprise AI governance.
        </div>
      </footer>
    </div>
  )
}
