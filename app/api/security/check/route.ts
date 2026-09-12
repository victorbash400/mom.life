import { backend } from "../../../lib/backend";
export async function POST() { return backend("security/check", { method: "POST" }); }
