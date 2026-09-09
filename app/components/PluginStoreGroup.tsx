import type { ToolDefinition, ToolGroup, ToolState } from "../data/toolDirectory";
import { PluginCatalogRow } from "./PluginCatalogRow";
import styles from "./PluginStoreGroup.module.css";
export function PluginStoreGroup({ busyId, group, onAdd, states, tools }: { busyId?: string; group: ToolGroup; onAdd: (tool: ToolDefinition) => void; states: Map<string, ToolState>; tools: ToolDefinition[] }) { if (!tools.length) return null; return <section className={styles.group}><h2>{group}</h2><ul>{tools.map((tool) => <PluginCatalogRow busy={busyId === tool.id} key={tool.id} onAdd={() => onAdd(tool)} state={states.get(tool.id)} tool={tool} />)}</ul></section>; }
