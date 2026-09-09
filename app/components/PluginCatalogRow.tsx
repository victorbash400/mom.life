import type { ToolDefinition, ToolState } from "../data/toolDirectory";
import { ToolIcon } from "./ToolIcon";
import styles from "./PluginCatalogRow.module.css";

export function PluginCatalogRow({ busy, onAdd, state, tool }: { busy: boolean; onAdd: () => void; state?: ToolState; tool: ToolDefinition }) {
  const installed = Boolean(state?.installed);
  const available = state?.connection_supported !== false;
  return <li className={styles.row}><ToolIcon tool={tool} /><span><strong>{tool.name}</strong><small>{tool.description}</small></span><button disabled={busy || installed || !available} onClick={onAdd} title={!available ? state?.setup_message || tool.setup : undefined} type="button">{installed ? "Added" : available ? "Add" : "Unavailable"}</button></li>;
}
