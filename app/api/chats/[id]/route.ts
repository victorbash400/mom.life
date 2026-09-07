import { backend } from "../../../lib/backend";
type Context = { params: Promise<{ id: string }> };
export async function GET(_: Request, context: Context) { return backend(`chats/${encodeURIComponent((await context.params).id)}`); }
export async function DELETE(_: Request, context: Context) { return backend(`chats/${encodeURIComponent((await context.params).id)}`, { method: "DELETE" }); }
