import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import { getTheme, onThemeChange } from "@/services/theme"
import "./index.css"

async function applyInitialTheme() {
  const theme = await getTheme()
  document.documentElement.classList.toggle("dark", theme === "dark")
  onThemeChange((next) => document.documentElement.classList.toggle("dark", next === "dark"))
}

void applyInitialTheme()

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
