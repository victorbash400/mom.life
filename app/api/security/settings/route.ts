import { backend, jsonRequest } from "../../../lib/backend";

export async function PATCH(request: Request) { return backend("security/settings", await jsonRequest(request, "PATCH")); }
