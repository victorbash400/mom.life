import { backend } from "../../lib/backend";
export async function GET() { return backend("chats"); }
export async function POST() { return backend("chats", { method: "POST" }); }
