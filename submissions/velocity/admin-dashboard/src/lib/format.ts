export function formatDateTime(iso: string): string {
  const date = new Date(iso.endsWith("Z") ? iso : `${iso}Z`)
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export function timeAgo(iso: string): string {
  const date = new Date(iso.endsWith("Z") ? iso : `${iso}Z`)
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 10) return "just now"
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
}

export function formatShortDate(dateStr: string): string {
  const date = new Date(`${dateStr}T00:00:00Z`)
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}
