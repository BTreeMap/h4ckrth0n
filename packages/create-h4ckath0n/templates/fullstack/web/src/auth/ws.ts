import { getOrMintToken } from "./token";

/**
 * Create an authenticated WebSocket connection.
 * Sends auth token as first message frame instead of query string.
 * Never put tokens in WebSocket URL query params.
 */
export async function createAuthWebSocket(
  url: string,
  onMessage?: (data: unknown) => void,
): Promise<WebSocket> {
  const token = await getOrMintToken("ws");
  const ws = new WebSocket(url);

  ws.addEventListener("open", () => {
    ws.send(JSON.stringify({ type: "auth", token }));
  });

  if (onMessage) {
    ws.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data as string);
        onMessage(data);
      } catch {
        onMessage(event.data);
      }
    });
  }

  return ws;
}

/**
 * Send a re-auth message on an existing WebSocket when token is renewed.
 */
export async function sendReauth(ws: WebSocket): Promise<void> {
  if (ws.readyState !== WebSocket.OPEN) return;
  const token = await getOrMintToken("ws");
  ws.send(JSON.stringify({ type: "auth", token }));
}
