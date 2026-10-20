// Global discussion store. HOT FILE: created empty by ticket 01; ticket 02
// fills in the WebSocket event handling, after which it is frozen.
import { defineStore } from 'pinia'

export const useDiscussionStore = defineStore('discussion', {
  state: () => ({}),
})
