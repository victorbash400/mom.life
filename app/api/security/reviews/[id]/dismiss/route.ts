import { backend } from "../../../../../lib/backend";

export async function POST(_: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  return backend(`security/reviews/${encodeURIComponent(id)}/dismiss`, { method: "POST" });
}
