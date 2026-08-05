export type UserRole = "admin" | "security_analyst" | "employee"
export type ExtensionStatus = "active" | "inactive" | "not_installed"

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  department: string | null
  is_active: boolean
  extension_status: ExtensionStatus
  prompt_count: number
  violation_count: number
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}
