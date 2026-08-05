import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "@/context/ThemeContext"
import { AuthProvider } from "@/context/AuthContext"
import { AppLayout } from "@/components/layout/AppLayout"
import { ProtectedRoute } from "@/components/layout/ProtectedRoute"
import { LandingPage } from "@/pages/LandingPage"
import { LoginPage } from "@/pages/LoginPage"
import { DashboardPage } from "@/pages/DashboardPage"
import { PromptLogsPage } from "@/pages/PromptLogsPage"
import { PoliciesPage } from "@/pages/PoliciesPage"
import { EmployeesPage } from "@/pages/EmployeesPage"
import { AnalyticsPage } from "@/pages/AnalyticsPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { NotFoundPage } from "@/pages/NotFoundPage"
import InvestigationsPage from "@/pages/InvestigationsPage"
import InvestigationDetailPage from "@/pages/InvestigationDetailPage"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />

              <Route element={<ProtectedRoute />}>
                <Route element={<AppLayout />}>
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/prompt-logs" element={<PromptLogsPage />} />
                  <Route path="/investigations" element={<InvestigationsPage />} />
                  <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
                  <Route path="/policies" element={<PoliciesPage />} />
                  <Route path="/employees" element={<EmployeesPage />} />
                  <Route path="/analytics" element={<AnalyticsPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Route>
              </Route>

              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
