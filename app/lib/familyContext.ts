import { backend } from "./backend";
export async function syncFamilyContext() {
  const response = await backend("family");
  if (!response.ok) return response;
  const family = await response.json();
  return backend("family-context", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ parent: family.parent, children: family.children }) });
}
