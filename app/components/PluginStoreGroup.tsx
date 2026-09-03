import { Check, Plus } from "lucide-react";
import type { ToolDefinition, ToolGroup } from "../data/toolDirectory";
import { ToolIcon } from "./ToolIcon";
import styles from "./PluginStoreGroup.module.css";
export function PluginStoreGroup({ connectedIds, group, onAdd, tools }: { connectedIds: string[]; group: ToolGroup; onAdd: (tool: ToolDefinition) => void; tools: ToolDefinition[] }) { if (!tools.length) return null; return <section className={styles.group}><h2>{group}</h2><ul>{tools.map((tool) => { const connected = connectedIds.includes(tool.id); return <li key={tool.id}><ToolIcon tool={tool} /><span><strong>{tool.name}</strong><small>{tool.description}</small></span><button aria-label={connected ? `${tool.name} connected` : `Add ${tool.name}`} disabled={connected} onClick={() => onAdd(tool)} type="button">{connected ? <Check /> : <Plus />}</button></li>; })}</ul></section>; }
