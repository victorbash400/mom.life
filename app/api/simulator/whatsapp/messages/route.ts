import { backend, jsonRequest } from "../../../../lib/backend";
export async function POST(request: Request) { return backend("simulator/whatsapp/messages", await jsonRequest(request)); }
