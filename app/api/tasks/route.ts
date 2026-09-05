import { backend, jsonRequest } from "../../lib/backend";
import { syncFamilyContext } from "../../lib/familyContext";
export async function GET() { return backend("tasks"); }
export async function POST(request: Request) { const context = await syncFamilyContext(); if (!context.ok) return context; return backend("tasks", await jsonRequest(request)); }
