# Browser Extension Architecture

The extension is a Manifest V3 Chrome extension built with React 19 +
Vite + TypeScript. It has three independent entry points, each built as
its own bundle (`vite.config.ts` uses fixed `entryFileNames` so the
manifest can reference stable file names):

| Entry | File | Role |
|---|---|---|
| Popup | `src/popup/main.tsx` → `popup.html` | Sign-in, org info, backend status, protection toggle, last scan, theme |
| Background | `src/background/index.ts` → `assets/background.js` | Service worker: JWT/session state, health polling, protection toggle storage |
| Content script | `src/content/index.ts` → `assets/content.js` | Runs on ChatGPT/Claude/Gemini pages: intercepts submit, calls the backend, enforces the decision |

## Message Protocol

All three surfaces communicate through one discriminated union,
`ExtensionMessage` (`src/types/messages.ts`), sent via
`chrome.runtime.sendMessage`:

`SCAN_PROMPT`, `LOGIN`, `LOGOUT`, `GET_AUTH_STATE`, `LOG_ACTIVITY`,
`GET_BACKEND_STATUS`, `GET_PROTECTION_ENABLED`,
`SET_PROTECTION_ENABLED`, `GET_LAST_SCAN`.

The background worker is the only surface that holds the JWT and talks to
`chrome.storage`; the popup and content script both go through it rather
than reading storage directly, so there is one source of truth for auth
state.

## Site Adapters

`src/adapters/{chatgpt,claude,gemini}.ts` each implement the same
`SiteAdapter` interface (`src/adapters/types.ts`):

- `findPromptInput()` / `findSendButton()` — located with 3-5 fallback
  selector strategies per element (`data-testid` → `aria-label` → ARIA
  `role` → generic `contenteditable`/`textarea`), since these sites change
  their DOM structure without notice and a single brittle selector would
  break the extension on the next site update.
- `getPromptText()` / `replacePrompt()` — abstracts over native
  `<textarea>` value assignment vs. rich-text `contenteditable` editors
  (ChatGPT and Claude use different composer implementations), so
  `content/index.ts` never needs to know which one it's talking to.
- `observeDOM()` — returns a `MutationObserver` so the content script
  reconnects automatically when a site's SPA router remounts the composer
  (e.g. starting a new chat), combined with a periodic poll and
  `history.pushState`/`popstate` hooks as a safety net for navigation
  patterns a `MutationObserver` alone might miss.

## Content Script Decision Handling

On submit, the content script cancels the native submit event, calls
`SCAN_PROMPT` (which the background worker forwards to
`POST /api/scan`), and then branches on `decision`:

- **ALLOW** — re-submits the original prompt programmatically; no UI shown.
- **WARN** — mounts `WarnModal` inside the Shadow DOM UI root with the
  Explainable AI panel; submission only proceeds if the employee clicks
  Continue.
- **REDACT** — calls `adapter.replacePrompt()` with the sanitized text and
  shows `RedactToast`; **does not auto-resend** — the employee reviews the
  redacted text and clicks Send themselves, which triggers a fresh scan
  against the now-sanitized prompt.
- **BLOCK** — mounts `BlockModal` with the Explainable AI panel;
  submission is never allowed to proceed, and the original prompt is
  discarded client-side (never reaches the AI site's own backend).

## Shadow DOM UI

`src/content/ui/mount.tsx` creates a closed Shadow DOM root and injects
the compiled `content.css` into it at runtime (fetched via
`chrome.runtime.getURL` + `fetch`, then appended as a `<style>` tag)
rather than relying on manifest-declared `content_scripts` CSS injection —
this guarantees the host page's styles can never leak into PromptShield's
UI, and vice versa. All modals/toasts (`WarnModal.tsx`, `BlockModal.tsx`,
`RedactToast.tsx`) are custom React components; the extension never calls
`alert()`/`confirm()`. A small `useSyncExternalStore`-based store
(`content/ui/store.ts`) holds the currently-visible modal/toast state.

## Explainable AI Panel

`content/ui/RiskAnalysisPanel.tsx` renders on every WARN/BLOCK: overall
risk score (as a gauge), each individual finding with a friendly label
(`utils/labels.ts` maps detector/category codes to human-readable names),
the policy that fired (parsed from the scan response's `reason` string via
`content/ui/riskAnalysis.ts`), the recommended action, and the reason —
entirely derived from fields already present in the `/api/scan` response,
so no backend changes were needed to add this panel.

## Background Worker Responsibilities

- **JWT expiry detection**: decodes the JWT payload client-side
  (`utils/jwt.ts`) and checks the `exp` claim before every scan; if
  expired, forces a clean re-login rather than silently refreshing (there
  is no refresh-token endpoint in this MVP).
- **Health polling**: calls `GET /api/health` every 2 minutes via
  `chrome.alarms` (not `setInterval`, since MV3 service workers can be
  suspended and killed, which would silently stop a `setInterval` timer)
  to drive the popup's Backend Status indicator.
- **Protection toggle**: persists an on/off switch to `chrome.storage`;
  when off, the content script still observes the page but skips the scan
  call and lets prompts through unmodified.
- **Retry with backoff**: transient network failures to the backend are
  retried with exponential backoff before the extension fails open
  (allows the prompt through) rather than silently hanging.
- **Distinguishing "backend is down" from "my session is invalid"**
  (Milestone 6 hardening): `scanPrompt()` used to fail open (silently
  ALLOW) on *any* non-2xx response, which meant an expired or revoked JWT
  looked identical to a healthy backend that simply had nothing to flag -
  zero protection, with no indication to the employee. A 401 specifically
  now throws `ScanUnauthorizedError`, which the `SCAN_PROMPT` handler
  catches to clear the stored session (so the next popup open / auth
  check surfaces a re-login prompt) - the in-flight prompt still fails
  open (an employee's immediate work is never blocked), but the extension
  no longer silently stays "signed in" with no real protection
  indefinitely. The handler also now checks `isTokenExpired()` up front,
  matching `GET_AUTH_STATE`'s existing behavior, to skip a doomed round
  trip entirely when the expiry is already obvious client-side.

## Icons and Branding

`public/icons/icon{16,48,128}.png` and the popup's inline `Logo.tsx` are
generated from the same shield-mark geometry as the admin dashboard's
`Logo.tsx` (`scripts/generate_icons.py` draws the identical shape via
Pillow), so the toolbar icon, popup header, and dashboard sidebar are
visually one brand.
