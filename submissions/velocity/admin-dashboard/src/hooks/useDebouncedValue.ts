import { useEffect, useState } from "react"

/**
 * Milestone 6 hardening: PromptLogsPage and EmployeesPage both fed their
 * search input's value directly into a TanStack Query `queryKey`, so every
 * single keystroke fired a new network request (typing a 6-character
 * search term meant 6 requests, all but the last one wasted). This debounces
 * the value used for the actual query while the input itself stays fully
 * responsive on every keystroke.
 */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timeout = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timeout)
  }, [value, delayMs])

  return debounced
}
