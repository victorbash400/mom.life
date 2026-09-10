import { backend, jsonRequest } from "../../../lib/backend";
export async function PUT(request: Request) { return backend("simulator/health", await jsonRequest(request, "PUT")); }
