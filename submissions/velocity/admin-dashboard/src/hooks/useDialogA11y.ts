import { useEffect, useRef } from "react"

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Milestone 6 hardening: Drawer, ConfirmDialog, and PolicyFormModal each
 * reimplemented their own (inconsistent, partial) version of "how a modal
 * behaves" - Drawer had Escape-to-close but ConfirmDialog didn't,
 * PolicyFormModal had neither, and none of them trapped keyboard focus
 * inside the dialog or restored focus to the trigger element on close. A
 * sighted mouse user never notices, but a keyboard-only user could Tab
 * straight through a "modal" into the page content behind it.
 *
 * One hook, applied consistently to all three: Escape closes, Tab/Shift+Tab
 * cycle only within the dialog's focusable elements, the dialog is
 * autofocused when it opens, and focus returns to whatever was focused
 * before the dialog opened once it closes.
 */
export function useDialogA11y(open: boolean, onClose: () => void) {
  const containerRef = useRef<HTMLDivElement>(null)
  const previouslyFocused = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return

    previouslyFocused.current = document.activeElement as HTMLElement | null
    containerRef.current?.focus()

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose()
        return
      }
      if (e.key !== "Tab" || !containerRef.current) return

      const focusable = containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    window.addEventListener("keydown", onKeyDown)
    return () => {
      window.removeEventListener("keydown", onKeyDown)
      previouslyFocused.current?.focus?.()
    }
  }, [open, onClose])

  return containerRef
}
