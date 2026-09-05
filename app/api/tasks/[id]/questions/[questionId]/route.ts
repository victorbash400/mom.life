import { backend, jsonRequest } from "../../../../../lib/backend";
export async function POST(request: Request, context: RouteContext<"/api/tasks/[id]/questions/[questionId]">) { const { id, questionId } = await context.params; return backend(`tasks/${encodeURIComponent(id)}/questions/${encodeURIComponent(questionId)}`, await jsonRequest(request)); }
