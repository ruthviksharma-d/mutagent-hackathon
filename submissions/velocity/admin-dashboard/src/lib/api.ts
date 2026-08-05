/**
 * Axios instance wired to the PromptShield backend.
 * Attaches the JWT bearer token to every request and redirects
 * to /login on 401 so the dashboard never gets stuck in a broken auth state.
 */
import axios from "axios"

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
})

const TOKEN_STORAGE_KEY = "promptshield_token"

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setStoredToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token)
  else localStorage.removeItem(TOKEN_STORAGE_KEY)
}

api.interceptors.request.use((config) => {
  const token = getStoredToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      setStoredToken(null)
      if (window.location.pathname !== "/login") {
        window.location.href = "/login"
      }
    }
    return Promise.reject(error)
  }
)
