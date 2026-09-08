import { backend } from "../../../lib/backend";

export async function DELETE(_: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  return backend(`incoming/${encodeURIComponent(id)}`, { method: "DELETE" });
}
