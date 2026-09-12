import { backend, jsonRequest } from "../../../lib/backend";
async function forward(request: Request, context: RouteContext<"/api/automations/[...path]">) {
  const { path } = await context.params;
  return backend(`automations/${path.map(encodeURIComponent).join("/")}`, request.method === "GET" ? {} : await jsonRequest(request, request.method));
}
export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
