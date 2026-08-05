import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search, Filter, Users } from "lucide-react"
import { Card, CardContent } from "@/components/ui/Card"
import { Input } from "@/components/ui/Input"
import { Select } from "@/components/ui/Select"
import { Skeleton } from "@/components/ui/Skeleton"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Pagination } from "@/components/ui/Pagination"
import { ExtensionStatusBadge } from "@/components/StatusBadges"
import { getEmployees } from "@/lib/adminApi"
import { timeAgo } from "@/lib/format"
import { useDebouncedValue } from "@/hooks/useDebouncedValue"

const ROLES = [
  { value: "employee", label: "Employee" },
  { value: "security_analyst", label: "Security Analyst" },
]

export function EmployeesPage() {
  const [search, setSearch] = useState("")
  const debouncedSearch = useDebouncedValue(search, 300)
  const [department, setDepartment] = useState("")
  const debouncedDepartment = useDebouncedValue(department, 300)
  const [role, setRole] = useState("")
  const [page, setPage] = useState(1)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["employees", { search: debouncedSearch, department: debouncedDepartment, role, page }],
    queryFn: () =>
      getEmployees({
        page,
        page_size: 15,
        search: debouncedSearch || undefined,
        department: debouncedDepartment || undefined,
        role: role || undefined,
      }),
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name or email..."
            className="pl-8"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Department..."
            className="w-40"
            value={department}
            onChange={(e) => { setDepartment(e.target.value); setPage(1) }}
          />
          <Select value={role} onChange={(e) => { setRole(e.target.value); setPage(1) }}>
            <option value="">All roles</option>
            {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </Select>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {isError ? (
            <ErrorState message="Couldn't load employees." onRetry={() => refetch()} />
          ) : isLoading ? (
            <div className="space-y-2 p-5">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !data || data.items.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No employees found"
              description="Either no accounts exist yet, or no results match your current filters."
            />
          ) : (
            <>
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="px-5 py-3 font-medium">Name</th>
                    <th className="px-5 py-3 font-medium">Department</th>
                    <th className="px-5 py-3 font-medium">Role</th>
                    <th className="px-5 py-3 font-medium">Total Prompts</th>
                    <th className="px-5 py-3 font-medium">Violations</th>
                    <th className="px-5 py-3 font-medium">Last Active</th>
                    <th className="px-5 py-3 font-medium">Extension</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((emp) => (
                    <tr key={emp.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                      <td className="px-5 py-3">
                        <p className="font-medium">{emp.full_name}</p>
                        <p className="text-xs text-muted-foreground">{emp.email}</p>
                      </td>
                      <td className="px-5 py-3">{emp.department ?? "—"}</td>
                      <td className="px-5 py-3 capitalize">{emp.role.replace("_", " ")}</td>
                      <td className="px-5 py-3">{emp.prompt_count.toLocaleString()}</td>
                      <td className="px-5 py-3">
                        <span className={emp.violation_count > 0 ? "font-medium text-warning" : ""}>
                          {emp.violation_count.toLocaleString()}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-muted-foreground">
                        {emp.last_active ? timeAgo(emp.last_active) : "Never"}
                      </td>
                      <td className="px-5 py-3">
                        <ExtensionStatusBadge status={emp.extension_status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <Pagination
                page={data.page}
                totalPages={data.total_pages}
                total={data.total}
                pageSize={data.page_size}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
