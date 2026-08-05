/**
 * Shared light/dark theme preference for the extension's own surfaces
 * (popup + content-script modals). Stored in chrome.storage.local (not
 * localStorage - content scripts and the popup are different JS contexts
 * and don't share a DOM/localStorage) so both stay in sync automatically.
 */
export type Theme = "light" | "dark"

const THEME_KEY = "promptshield_ext_theme"

export async function getTheme(): Promise<Theme> {
  const stored = await chrome.storage.local.get(THEME_KEY)
  const value = stored[THEME_KEY] as Theme | undefined
  if (value === "light" || value === "dark") return value
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light"
}

export async function setTheme(theme: Theme): Promise<void> {
  await chrome.storage.local.set({ [THEME_KEY]: theme })
}

export function onThemeChange(callback: (theme: Theme) => void): () => void {
  const listener = (changes: { [key: string]: chrome.storage.StorageChange }, area: string) => {
    if (area !== "local" || !changes[THEME_KEY]) return
    const next = changes[THEME_KEY].newValue as Theme | undefined
    if (next === "light" || next === "dark") callback(next)
  }
  chrome.storage.onChanged.addListener(listener)
  return () => chrome.storage.onChanged.removeListener(listener)
}
