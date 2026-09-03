import type { ToolDefinition } from "../data/toolDirectory";
import styles from "./ToolIcon.module.css";
export function ToolIcon({ tool, size = "regular" }: { tool: ToolDefinition; size?: "small" | "regular" }) { const Icon = tool.icon; return <span className={styles.icon} data-size={size} style={{ "--tool-color": tool.color } as React.CSSProperties}><Icon aria-hidden="true" /></span>; }
