import { backend, jsonRequest } from "../../../../lib/backend";

export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  return backend(`incoming/${encodeURIComponent(id)}/retry`, await jsonRequest(request));
}
