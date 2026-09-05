import { backend, jsonRequest } from "../../lib/backend";
export async function PUT(request: Request) { return backend("family-context", await jsonRequest(request,"PUT")); }
