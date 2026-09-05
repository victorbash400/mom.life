import { backend, jsonRequest } from "../../../../lib/backend";
export async function POST(request: Request, context: RouteContext<"/api/tasks/[id]/revise">) { const { id } = await context.params; return backend(`tasks/${encodeURIComponent(id)}/revise`, await jsonRequest(request)); }
