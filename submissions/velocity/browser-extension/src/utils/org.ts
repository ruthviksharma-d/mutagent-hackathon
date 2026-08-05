/** Derives a friendly organization label from the authenticated user's
 * email domain. The backend has no organization field yet (Milestone 3
 * keeps the API unchanged), so this is computed client-side from real
 * data rather than fabricated. */
export function deriveOrgName(email: string): string {
  const domain = email.split("@")[1] ?? ""
  const label = domain.split(".")[0] ?? ""
  if (!label) return "Your Organization"
  return label.charAt(0).toUpperCase() + label.slice(1)
}

export function timeAgo(timestampMs: number): string {
  const seconds = Math.floor((Date.now() - timestampMs) / 1000)
  if (seconds < 10) return "just now"
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export const SUPPORTED_HOSTNAMES = ["chatgpt.com", "chat.openai.com", "claude.ai", "gemini.google.com"]

export function isSupportedHostname(hostname: string): boolean {
  return SUPPORTED_HOSTNAMES.some((h) => hostname.includes(h))
}
