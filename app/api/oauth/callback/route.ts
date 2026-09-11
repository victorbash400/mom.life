import { backend } from "../../../lib/backend";
export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  if (!code || !state || url.searchParams.has("error")) return new Response("Authorization was not completed. Return to mom.life and connect again.", { status: 400 });
  const result = await backend("oauth/callback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code, state }) });
  if (!result.ok) return result;
  return new Response("<!doctype html><html><head><meta charset=\"utf-8\"><title>Connection complete</title></head><body><p>Connected. You can close this tab.</p><script>window.opener?.postMessage({type:'mom-life-plugin-connected'},window.location.origin);window.close()</script></body></html>", { headers: { "Content-Type": "text/html; charset=utf-8" } });
}
