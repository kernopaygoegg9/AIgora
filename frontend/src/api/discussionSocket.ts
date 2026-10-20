// One WebSocket per discussion (`/ws/discussion`, proxied by Vite in dev).
// Not frozen: ticket 03 may extend it. Typical use:
//
//   const store = useDiscussionStore()
//   store.reset()
//   const socket = openDiscussionSocket((msg) => store.applyMessage(msg))
//   socket.start(question, settings)
//   socket.interject('...'); socket.stop()
import type { ClientMessage, ServerMessage, StartSettings } from '../contracts/messages'

export const DISCUSSION_SOCKET_PATH = '/ws/discussion'

export interface DiscussionSocket {
  start(question: string, settings: StartSettings, fromDiscussionId?: string | null): void
  interject(text: string): void
  stop(): void
  close(): void
}

export function discussionSocketUrl(loc: Location = window.location): string {
  const scheme = loc.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${scheme}//${loc.host}${DISCUSSION_SOCKET_PATH}`
}

export function openDiscussionSocket(
  onMessage: (message: ServerMessage) => void,
  onClose?: (event: CloseEvent) => void,
): DiscussionSocket {
  const ws = new WebSocket(discussionSocketUrl())
  const queue: string[] = []

  ws.addEventListener('open', () => {
    for (const data of queue.splice(0)) ws.send(data)
  })
  ws.addEventListener('message', (event) => {
    onMessage(JSON.parse(String(event.data)) as ServerMessage)
  })
  if (onClose) ws.addEventListener('close', onClose)

  function send(message: ClientMessage) {
    const data = JSON.stringify(message)
    if (ws.readyState === WebSocket.OPEN) ws.send(data)
    else queue.push(data)
  }

  return {
    start: (question, settings, fromDiscussionId = null) =>
      send({ type: 'start', question, settings, from_discussion_id: fromDiscussionId }),
    interject: (text) => send({ type: 'interject', text }),
    stop: () => send({ type: 'stop' }),
    close: () => ws.close(),
  }
}
