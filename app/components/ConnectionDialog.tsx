"use client";
import { useEffect, useRef } from "react";
import type { ToolDefinition } from "../data/toolDirectory";
import { ToolIcon } from "./ToolIcon";
import styles from "./ConnectionDialog.module.css";
export function ConnectionDialog({ tool, onCancel, onConnect }: { tool?: ToolDefinition; onCancel: () => void; onConnect: (id: string) => void }) { const ref = useRef<HTMLDialogElement>(null); useEffect(() => { if (tool && !ref.current?.open) ref.current?.showModal(); else if (!tool && ref.current?.open) ref.current.close(); }, [tool]); return <dialog className={styles.dialog} onCancel={onCancel} ref={ref}>{tool ? <section><header><ToolIcon tool={tool} /><span><h2>Connect {tool.name}</h2><p>{tool.description}</p></span></header><h3>mom.life will be able to</h3><ul>{tool.permissions.map((permission) => <li key={permission}>{permission}</li>)}</ul><footer><button onClick={onCancel} type="button">Cancel</button><button onClick={() => onConnect(tool.id)} type="button">Connect</button></footer></section> : null}</dialog>; }
