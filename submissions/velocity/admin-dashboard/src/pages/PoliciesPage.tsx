import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, Pencil, Trash2, ShieldCheck } from "lucide-react"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { Toggle } from "@/components/ui/Toggle"
import { Skeleton } from "@/components/ui/Skeleton"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { ActionBadge } from "@/components/StatusBadges"
import { PolicyFormModal } from "@/components/PolicyFormModal"
import { createPolicy, deletePolicy, getPolicies, updatePolicy } from "@/lib/adminApi"
import type { Policy, PolicyInput } from "@/types/admin"

export function PoliciesPage() {
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState(false)
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null)
  const [deletingPolicy, setDeletingPolicy] = useState<Policy | null>(null)

  const { data: policies, isLoading, isError, refetch } = useQuery({
    queryKey: ["policies"],
    queryFn: getPolicies,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["policies"] })

  const createMutation = useMutation({
    mutationFn: createPolicy,
    onSuccess: () => {
      invalidate()
      setFormOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<PolicyInput> }) => updatePolicy(id, payload),
    onSuccess: () => {
      invalidate()
      setFormOpen(false)
      setEditingPolicy(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deletePolicy,
    onSuccess: () => {
      invalidate()
      setDeletingPolicy(null)
    },
  })

  function handleSubmit(input: PolicyInput) {
    if (editingPolicy) {
      updateMutation.mutate({ id: editingPolicy.id, payload: input })
    } else {
      createMutation.mutate(input)
    }
  }

  function handleToggleEnabled(policy: Policy) {
    updateMutation.mutate({ id: policy.id, payload: { enabled: !policy.enabled } })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Policies are evaluated in priority order (lowest number first) and override the AI Detection
          Engine's default action for a matching detection type.
        </p>
        <Button
          size="sm"
          onClick={() => {
            setEditingPolicy(null)
            setFormOpen(true)
          }}
        >
          <Plus className="h-4 w-4" />
          Create Policy
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {isError ? (
            <ErrorState message="Couldn't load policies." onRetry={() => refetch()} />
          ) : isLoading ? (
            <div className="space-y-2 p-5">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !policies || policies.length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title="No policies yet"
              description="Create your first policy to start overriding the default risk-based decisions."
            />
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-5 py-3 font-medium">Priority</th>
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Detection Type</th>
                  <th className="px-5 py-3 font-medium">Action</th>
                  <th className="px-5 py-3 font-medium">Enabled</th>
                  <th className="px-5 py-3 font-medium text-right">Manage</th>
                </tr>
              </thead>
              <tbody>
                {policies.map((policy) => (
                  <tr key={policy.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                    <td className="px-5 py-3 text-muted-foreground">{policy.priority}</td>
                    <td className="px-5 py-3">
                      <p className="font-medium">{policy.name}</p>
                      {policy.description && <p className="text-xs text-muted-foreground">{policy.description}</p>}
                    </td>
                    <td className="px-5 py-3">
                      <Badge tone="muted">{policy.detection_type}</Badge>
                    </td>
                    <td className="px-5 py-3">
                      <ActionBadge action={policy.action} />
                    </td>
                    <td className="px-5 py-3">
                      <Toggle checked={policy.enabled} onChange={() => handleToggleEnabled(policy)} />
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Edit policy ${policy.name}`}
                          onClick={() => {
                            setEditingPolicy(policy)
                            setFormOpen(true)
                          }}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Delete policy ${policy.name}`}
                          onClick={() => setDeletingPolicy(policy)}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-danger" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {formOpen && (
        <PolicyFormModal
          policy={editingPolicy}
          onClose={() => {
            setFormOpen(false)
            setEditingPolicy(null)
          }}
          onSubmit={handleSubmit}
          isSubmitting={createMutation.isPending || updateMutation.isPending}
        />
      )}

      <ConfirmDialog
        open={!!deletingPolicy}
        title="Delete this policy?"
        description={`"${deletingPolicy?.name}" will stop overriding scan decisions immediately. This can't be undone.`}
        onCancel={() => setDeletingPolicy(null)}
        onConfirm={() => deletingPolicy && deleteMutation.mutate(deletingPolicy.id)}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
