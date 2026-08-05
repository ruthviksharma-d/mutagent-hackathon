import type { SiteAdapter } from "./types"
import { watchForComposer } from "./observe"
import { firstVisible, setContentEditableText } from "@/utils/dom"

/**
 * Claude (claude.ai). The composer is a ProseMirror contenteditable div.
 * ProseMirror's class name (".ProseMirror") has been stable across
 * Claude's UI revisions, but selectors still fall back to generic
 * contenteditable + role/aria-label matches in case that changes.
 */
export const claudeAdapter: SiteAdapter = {
  siteName: "Claude",

  findPromptInput() {
    return firstVisible([
      document.querySelector('div[contenteditable="true"].ProseMirror'),
      document.querySelector('div[aria-label*="prompt" i][contenteditable="true"]'),
      document.querySelector('div[contenteditable="true"][role="textbox"]'),
      document.querySelector('fieldset div[contenteditable="true"]'),
      document.querySelector('div[contenteditable="true"]'),
    ])
  },

  findSendButton() {
    return firstVisible([
      document.querySelector('button[aria-label="Send Message"]'),
      document.querySelector('button[aria-label="Send message"]'),
      document.querySelector('button[aria-label*="Send" i]'),
      document.querySelector('button[type="submit"]'),
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
