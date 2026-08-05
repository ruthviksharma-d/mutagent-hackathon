/**
 * Contract every site adapter must implement so the content script can
 * treat ChatGPT, Claude, and Gemini identically. Adapters are pure DOM
 * detection/manipulation - no UI, no fetch calls, no business logic (that
 * all lives in content/index.ts and the backend).
 */
export interface SiteAdapter {
  siteName: "ChatGPT" | "Claude" | "Gemini"

  /** Locate the prompt textbox currently on screen (null if not rendered yet). */
  findPromptInput(): HTMLElement | null

  /** Locate the submit/send button tied to the prompt textbox. */
  findSendButton(): HTMLElement | null

  /** Read the current prompt text out of the input. */
  getPromptText(input: HTMLElement): string

  /** Overwrite the prompt text (used after redaction). Picks the correct
   * replacement strategy (native textarea vs. rich-text contenteditable)
   * based on the element itself. */
  replacePrompt(input: HTMLElement, newText: string): void

  /**
   * Watch the page for the prompt input/send button being (re)mounted -
   * SPA navigation on these sites frequently remounts the composer.
   * Implementations should be resilient to being called many times.
   */
  observeDOM(onReady: (input: HTMLElement, sendButton: HTMLElement | null) => void): MutationObserver
}
