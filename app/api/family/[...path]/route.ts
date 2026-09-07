import { backend } from "../../../lib/backend";
async function forward(request: Request, context: RouteContext<"/api/family/[...path]">) {
  const { path } = await context.params;
  const headers = new Headers();
  if (request.headers.has("content-type")) headers.set("Content-Type", request.headers.get("content-type")!);
  return backend(`family/${path.map(encodeURIComponent).join("/")}`, { method: request.method, headers, body: ["GET","HEAD"].includes(request.method) ? undefined : await request.arrayBuffer() });
}
export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
