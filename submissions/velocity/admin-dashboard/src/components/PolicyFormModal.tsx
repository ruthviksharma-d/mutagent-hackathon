import { useState, type FormEvent } from "react"
import { X } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Select } from "@/components/ui/Select"
import { Toggle } from "@/components/ui/Toggle"
import { useDialogA11y } from "@/hooks/useDialogA11y"
import type { Action, Policy, PolicyInput } from "@/types/admin"

const DETECTION_TYPES: { value: string; label: string }[] = [
  { value: "api_key", label: "API Key" },
  { value: "password", label: "Password" },
  { value: "email", label: "Email Address" },
  { value: "phone", label: "Phone Number" },
  { value: "credit_card", label: "Credit Card" },
  { value: "jwt", label: "JWT Token" },
  { value: "ssh_key", label: "SSH Key / Certificate" },
  { value: "pii", label: "Personal Information (PII)" },
  { value: "source_code", label: "Source Code" },
  { value: "company_keyword", label: "Company Keyword" },
  { value: "secrets", label: "Any Leaked Credential (detector)" },
  { value: "regex", label: "Any Regex Match (detector)" },
  { value: "presidio", label: "Any PII Match (detector)" },
  { value: "semantic", label: "AI Semantic Risk" },
  { value: "all", label: "Any Detection" },
]

const ACTIONS: Action[] = ["ALLOW", "WARN", "REDACT", "BLOCK"]

interface PolicyFormModalProps {
  policy: Policy | null
  onClose: () => void
  onSubmit: (input: PolicyInput) => void
  isSubmitting: boolean
}

export function PolicyFormModal({ policy, onClose, onSubmit, isSubmitting }: PolicyFormModalProps) {
  const [name, setName] = useState(policy?.name ?? "")
  const [description, setDescription] = useState(policy?.description ?? "")
  const [priority, setPriority] = useState(policy?.priority ?? 100)
  const [detectionType, setDetectionType] = useState(policy?.detection_type ?? "api_key")
  const [action, setAction] = useState<Action>(policy?.action ?? "BLOCK")
  const [enabled, setEnabled] = useState(policy?.enabled ?? true)
  const containerRef = useDialogA11y(true, onClose)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit({ name, description, priority, detection_type: detectionType, action, enabled })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="policy-form-title"
        tabIndex={-1}
        className="w-full max-w-lg rounded-xl border border-border bg-card shadow-2xl focus:outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border p-5">
          <h2 id="policy-form-title" className="text-base font-semibold">{policy ? "Edit Policy" : "Create Policy"}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1.5 text-muted-foreground hover:bg-muted">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-5">
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. Block API Keys" />
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">Description</label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this policy does" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Priority</label>
              <Input
                type="number"
                value={priority}
                onChange={(e) => setPriority(Number(e.target.value))}
                min={1}
                max={999}
              />
              <p className="text-xs text-muted-foreground">Lower number = evaluated first</p>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Action</label>
              <Select value={action} onChange={(e) => setAction(e.target.value as Action)} className="w-full">
                {ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">Detection Type</label>
            <Select value={detectionType} onChange={(e) => setDetectionType(e.target.value)} className="w-full">
              {DETECTION_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </Select>
          </div>

          <div className="flex items-center justify-between rounded-md border border-border px-3 py-2.5">
            <span className="text-sm font-medium">Enabled</span>
            <Toggle checked={enabled} onChange={setEnabled} />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {policy ? "Save Changes" : "Create Policy"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
