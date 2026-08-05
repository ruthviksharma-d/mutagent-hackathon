/**
 * Mounts the content-script React app inside a closed Shadow DOM so
 * ChatGPT/Claude/Gemini's own styles can never bleed into our modals, and
 * our Tailwind reset can never bleed into theirs. The CSS is imported as a
 * raw string (via the `?inline` suffix) and baked directly into content.js
 * at build time - a content script can't reliably fetch a separate CSS
 * asset at runtime (Chrome blocks it unless the file is explicitly listed
 * under manifest.json's web_accessible_resources), so embedding it as a
 * string sidesteps that entirely.
 */
import { createRoot } from "react-dom/client"
import { App } from "./App"
import { getTheme, onThemeChange } from "@/services/theme"
import cssText from "@/content/ui/content.css?inline"

const HOST_ID = "promptshield-ui-host"

export async function mountContentUI(): Promise<void> {
  if (document.getElementById(HOST_ID)) return
  const host = document.createElement("div")
  host.id = HOST_ID
  document.documentElement.appendChild(host)
  const shadow = host.attachShadow({ mode: "open" })
  const style = document.createElement("style")
  style.textContent = cssText
  shadow.appendChild(style)
  const container = document.createElement("div")
  shadow.appendChild(container)
  const applyTheme = (theme: "light" | "dark") => {
    container.className = theme === "dark" ? "dark" : ""
  }
  applyTheme(await getTheme())
  onThemeChange(applyTheme)
  createRoot(container).render(<App />)
}