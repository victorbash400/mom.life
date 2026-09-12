import { backend } from "../../../lib/backend";
async function forward(request: Request, context: RouteContext<"/api/family/[...path]">) {
  const { path } = await context.params;
  const headers = new Headers();
  if (request.headers.has("content-type")) headers.set("Content-Type", request.headers.get("content-type")!);
  const query = new URL(request.url).search;
  const response = await backend(`family/${path.map(encodeURIComponent).join("/")}${query}`, { method: request.method, headers, body: ["GET","HEAD"].includes(request.method) ? undefined : await request.arrayBuffer() });
  if (request.method === "GET" && response.ok && ["photo", "avatar"].includes(path.at(-1) ?? "")) {
    response.headers.set("Cache-Control", "private, max-age=86400");
    response.headers.set("Vary", "Cookie");
  }
  return response;
}
export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
