"use client";
import { useCallback, useEffect, useState } from "react";
export type FamilyTask = { id: string; family_id: string; child_id: string; text: string; status: "active" | "paused" | "completed"; created_at: string; updated_at: string };
export function useFamilyTasks() {
  const [tasks, setTasks] = useState<FamilyTask[]>([]); const [loaded, setLoaded] = useState(false); const [error, setError] = useState<string>();
  const refresh = useCallback(async () => { try { const response = await fetch("/api/tasks", { cache: "no-store" }); const payload = await response.json() as FamilyTask[] | { error?: string }; if (!response.ok || !Array.isArray(payload)) throw new Error(!Array.isArray(payload) && payload.error || "Could not load tasks."); setTasks(payload); setError(undefined); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load tasks."); } finally { setLoaded(true); } }, []);
  useEffect(() => { const frame = window.requestAnimationFrame(() => { void refresh(); }); return () => window.cancelAnimationFrame(frame); }, [refresh]);
  async function createTask(childId: string, text: string) { const task = await requestTask("/api/tasks", "POST", { family_id: "sarah-family", child_id: childId, text }); setTasks((current) => [task, ...current]); }
  async function setTaskStatus(id: string, status: FamilyTask["status"]) { const task = await requestTask(`/api/tasks/${id}`, "PATCH", { status }); setTasks((current) => current.map((item) => item.id === id ? task : item)); }
  async function deleteTask(id: string) { const response = await fetch(`/api/tasks/${id}`, { method: "DELETE" }); if (!response.ok) throw new Error("Could not delete task."); setTasks((current) => current.filter((item) => item.id !== id)); }
  return { createTask, deleteTask, error, loaded, setTaskStatus, tasks };
}
async function requestTask(path: string, method: "POST" | "PATCH", body: Record<string, string>) { const response = await fetch(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); const payload = await response.json() as FamilyTask | { error?: string }; if (!response.ok) throw new Error("error" in payload && payload.error || "Could not save task."); return payload as FamilyTask; }
