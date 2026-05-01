import type { StreamEvent } from "../types/chat";

export function createChatSocket(
  conversationId: string,
  onEvent: (event: StreamEvent) => void,
  onError?: (error: Event) => void,
): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(
    `${protocol}//${window.location.host}/api/v1/chat/ws/${conversationId}`,
  );

  ws.onmessage = (event) => {
    const data: StreamEvent = JSON.parse(event.data);
    onEvent(data);
  };

  ws.onerror = (event) => {
    onError?.(event);
  };

  return ws;
}
