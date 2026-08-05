import type { SiteAdapter } from "./types"
import { watchForComposer } from "./observe"
import { firstVisible, setContentEditableText, setTextareaValue } from "@/utils/dom"

/**
 * ChatGPT (chatgpt.com / chat.openai.com).
 *
 * The composer has shipped as a contenteditable div (#prompt-textarea) for
 * the current UI, but earlier/alternate layouts (and some embedded
 * surfaces) use a plain <textarea>. Selectors are tried in order, most
 * specific first, falling back to generic attribute/role matches so a
 * markup tweak upstream doesn't silently break detection.
 */
export const chatgptAdapter: SiteAdapter = {
  siteName: "ChatGPT",

  findPromptInput() {
    return firstVisible([
      document.querySelector("#prompt-textarea"),
      document.querySelector('div[contenteditable="true"][data-id]'),
      document.querySelector('form textarea[data-id]'),
      document.querySelector('form div[contenteditable="true"]'),
      document.querySelector('textarea[placeholder*="Message" i]'),
      document.querySelector('div[contenteditable="true"][aria-label*="Message" i]'),
    ])
  },

  findSendButton() {
    return firstVisible([
      document.querySelector('button[data-testid="send-button"]'),
      document.querySelector('button[aria-label="Send prompt"]'),
      document.querySelector('button[aria-label*="Send" i]'),
      document.querySelector('form button[type="submit"]'),
    ])
  },

  getPromptText(input) {
    if (input instanceof HTMLTextAreaElement) return input.value
    return input.innerText ?? ""
  },

  replacePrompt(input, newText) {
    if (input instanceof HTMLTextAreaElement) {
      setTextareaValue(input, newText)
    } else {
      setContentEditableText(input, newText)
    }
  },

  observeDOM(onReady) {
    return watchForComposer(this.findPromptInput.bind(this), this.findSendButton.bind(this), onReady)
  },
}
