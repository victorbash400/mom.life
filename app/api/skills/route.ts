import { backend, jsonRequest } from "../../lib/backend";
export async function GET() { return backend("skills"); }
export async function POST(request: Request) { return backend("skills", await jsonRequest(request)); }
