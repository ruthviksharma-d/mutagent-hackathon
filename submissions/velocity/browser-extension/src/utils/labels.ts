/**
 * Friendly display names for the detector/finding vocabulary produced by
 * the Milestone 2 backend (ai/regex_detector.py, presidio_detector.py,
 * secret_detector.py, keyword_detector.py, code_detector.py). Purely a
 * frontend presentation layer - the backend API response is untouched.
 */

export const DETECTOR_DISPLAY_NAMES: Record<string, string> = {
  regex: "Pattern Match",
  presidio: "Personal Information (PII)",
  spacy: "Named Entity",
  source_code: "Source Code",
  company_keyword: "Company-Sensitive Term",
  secrets: "Leaked Credential",
  semantic: "AI Risk Assessment",
}

export function friendlyDetectorName(detector: string): string {
  // Strip a "[file:xyz.pdf] " source-file prefix if present (Milestone 2's
  // file scanner tags findings this way) and surface it separately.
  return DETECTOR_DISPLAY_NAMES[detector] ?? detector
}

/**
 * The backend's decision.reason string is deterministically formatted by
 * ai/policy_engine.py as: "Policy '<name>' triggered by detection type '<type>'."
 * Parsing it client-side lets the Explainable AI panel show which policy
 * fired without requiring a new backend field.
 */
export function extractTriggeredPolicy(reason: string): string | null {
  const match = reason.match(/Policy '([^']+)'/)
  return match ? match[1] : null
}

/** Strip a leading "[file:xyz.pdf] " tag some findings carry, returning { source, text }. */
export function splitFileSource(reason: string): { source: string | null; text: string } {
  const match = reason.match(/^\[file:([^\]]+)\]\s*(.*)$/)
  if (!match) return { source: null, text: reason }
  return { source: match[1], text: match[2] }
}

export const RISK_COLORS: Record<string, string> = {
  NONE: "#16a34a",
  LOW: "#16a34a",
  MEDIUM: "#d97706",
  HIGH: "#dc2626",
  CRITICAL: "#991b1b",
}

export const ACTION_LABELS: Record<string, string> = {
  ALLOW: "Allow",
  WARN: "Warn",
  REDACT: "Redact",
  BLOCK: "Block",
}
