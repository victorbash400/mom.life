import { children, sarah } from "../data/dashboard";
import { backend } from "./backend";
export async function syncFamilyContext() {
  return backend("family-context", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ parent: sarah, children: children.map(({ id, name, age }) => ({ id, name, age })), source: "mom.life family profiles" }) });
}
