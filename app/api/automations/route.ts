import { backend, jsonRequest } from "../../lib/backend";
export async function GET() { return backend("automations"); }
export async function POST(request: Request) { return backend("automations", await jsonRequest(request)); }
