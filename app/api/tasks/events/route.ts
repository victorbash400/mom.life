import { backend } from "../../../lib/backend";
export async function GET(request: Request) {
  const response = await backend("tasks/events", { signal: request.signal });
  if (response.status !== 503) return response;
  return new Response('retry: 3000\ndata: {"type":"connection_error"}\n\n', {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
  });
}
