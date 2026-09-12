import { backend, jsonRequest } from "../../lib/backend";
export async function GET() { return backend("tasks"); }
export async function POST(request: Request) { return backend("tasks", await jsonRequest(request)); }
