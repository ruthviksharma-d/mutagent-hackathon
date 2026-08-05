/**
 * Client-side JWT expiry check. The Milestone 1/2 backend issues short-lived
 * access tokens with no refresh-token endpoint (and Milestone 3 is
 * explicitly scoped to leave the backend API unchanged), so "token
 * refresh" here means: proactively detect expiry from the token itself
 * and force a clean re-login instead of waiting for the backend to
 * eventually return a 401. This avoids an extra network round-trip on
 * every popup open/content-script scan once a session has expired.
 */
export function decodeJwtPayload(token: string): { exp?: number; sub?: string; role?: string } | null {
  try {
    const [, payloadB64] = token.split(".")
    if (!payloadB64) return null
    const normalized = payloadB64.replace(/-/g, "+").replace(/_/g, "/")
    const json = atob(normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "="))
    return JSON.parse(json)
  } catch {
    return null
  }
}

export function isTokenExpired(token: string, leewaySeconds = 30): boolean {
  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return true
  const nowSeconds = Date.now() / 1000
  return payload.exp - leewaySeconds <= nowSeconds
}
