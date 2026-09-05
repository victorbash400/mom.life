import { backend } from "../../../lib/backend";
export async function GET(request: Request) { return backend("tasks/events", { signal: request.signal }); }
