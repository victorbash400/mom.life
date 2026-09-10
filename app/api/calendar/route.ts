import { backend, jsonRequest } from "../../lib/backend";

export async function GET() { return backend("calendar"); }
export async function PATCH(request: Request) { return backend("calendar/preferences", await jsonRequest(request, "PATCH")); }
