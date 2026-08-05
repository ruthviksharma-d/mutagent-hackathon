import type { SiteAdapter } from "./types"
import { chatgptAdapter } from "./chatgpt"
import { claudeAdapter } from "./claude"
import { geminiAdapter } from "./gemini"

export type { SiteAdapter }

export function getAdapterForHostname(hostname: string): SiteAdapter | null {
  if (hostname.includes("chatgpt.com") || hostname.includes("chat.openai.com")) return chatgptAdapter
  if (hostname.includes("claude.ai")) return claudeAdapter
  if (hostname.includes("gemini.google.com")) return geminiAdapter
  return null
}
