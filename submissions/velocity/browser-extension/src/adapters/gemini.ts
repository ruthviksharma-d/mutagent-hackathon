import type { SiteAdapter } from "./types"
import { watchForComposer } from "./observe"
import { firstVisible, setContentEditableText } from "@/utils/dom"

/**
 * Gemini (gemini.google.com). The composer is a Quill-based rich-text
 * editor: <rich-textarea> wrapping a contenteditable ".ql-editor" div.
 */
export const geminiAdapter: SiteAdapter = {
  siteName: "Gemini",

  findPromptInput() {
    return firstVisible([
      document.querySelector("rich-textarea .ql-editor"),
      document.querySelector('div[contenteditable="true"][aria-label*="Prompt" i]'),
      document.querySelector('div[contenteditable="true"][role="textbox"]'),
      document.querySelector('div[contenteditable="true"]'),
    ])
  },

  findSendButton() {
    return firstVisible([
      document.querySelector('button[aria-label="Send message"]'),
      document.querySelector('button.send-button'),
      document.querySelector('button[aria-label*="Send" i]'),
      document.querySelector('button[mattooltip*="Send" i]'),
    ])
  },

  getPromptText(input) {
    return input.innerText ?? ""
  },

  replacePrompt(input, newText) {
    setContentEditableText(input, newText)
  },

  observeDOM(onReady) {
    return watchForComposer(this.findPromptInput.bind(this), this.findSendButton.bind(this), onReady)
  },
}
