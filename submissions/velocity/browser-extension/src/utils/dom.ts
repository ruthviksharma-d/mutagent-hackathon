/**
 * Robust text-replacement helpers for the two composer flavors we see
 * across ChatGPT/Claude/Gemini: native <textarea> and rich-text
 * contenteditable editors (ProseMirror / Quill / Lexical-style).
 *
 * Directly overwriting `.innerText` on a contenteditable often desyncs the
 * editor's own internal document model, so the primary strategy here is
 * `document.execCommand("insertText", ...)` after selecting all existing
 * content - that fires the same native `beforeinput`/`input` events these
 * editors already listen to, so their internal state updates correctly.
 * Falls back to direct DOM manipulation if execCommand is unavailable.
 */

export function setTextareaValue(el: HTMLTextAreaElement, text: string): void {
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set
  if (setter) {
    setter.call(el, text)
  } else {
    el.value = text
  }
  el.dispatchEvent(new Event("input", { bubbles: true }))
  el.dispatchEvent(new Event("change", { bubbles: true }))
}

export function setContentEditableText(el: HTMLElement, text: string): void {
  el.focus()

  const selection = window.getSelection()
  if (selection) {
    const range = document.createRange()
    range.selectNodeContents(el)
    selection.removeAllRanges()
    selection.addRange(range)
  }

  let usedExecCommand = false
  try {
    usedExecCommand = document.execCommand("insertText", false, text)
  } catch {
    usedExecCommand = false
  }

  if (!usedExecCommand) {
    el.textContent = text
    el.dispatchEvent(new InputEvent("input", { bubbles: true, data: text, inputType: "insertText" }))
  }

  el.dispatchEvent(new Event("change", { bubbles: true }))
}

/** Find the first element in `candidates` that is actually visible/attached. */
export function firstVisible(candidates: (Element | null)[]): HTMLElement | null {
  for (const el of candidates) {
    if (!el || !(el instanceof HTMLElement)) continue
    if (!el.isConnected) continue
    const rect = el.getBoundingClientRect()
    if (rect.width === 0 && rect.height === 0) continue
    return el
  }
  return null
}

export function queryAll(selectors: string[]): Element[] {
  const results: Element[] = []
  for (const selector of selectors) {
    try {
      results.push(...Array.from(document.querySelectorAll(selector)))
    } catch {
      // invalid selector for this browser - skip
    }
  }
  return results
}
