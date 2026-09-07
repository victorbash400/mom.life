"use client";
import { useFamily } from "../components/FamilyProvider";
import { useEffect, useRef, useState } from "react";
import type { FamilyTask } from "../types/goals";
export type { FamilyTask } from "../types/goals";

export function useFamilyTasks() {
  const { family } = useFamily();
  const revisionRef = useRef(0);
  const [tasks, setTasks] = useState<FamilyTask[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string>();
  useEffect(() => {
    let active = true;
    async function refresh() {
      const revision = ++revisionRef.current;
      try {
        const response = await fetch("/api/tasks", { cache: "no-store" });
        const payload = await response.json();
        if (!response.ok || !Array.isArray(payload)) throw new Error(payload.error || "Could not load tasks.");
        if (active && revision === revisionRef.current) { setTasks(payload); setError(undefined); }
      } catch (cause) { if (active) setError(cause instanceof Error ? cause.message : "Could not load tasks."); }
      finally { if (active) setLoaded(true); }
    }
    const events = new EventSource("/api/tasks/events");
    events.onmessage = () => { void refresh(); };
    events.onerror = () => { if (active) setError("Live task updates are disconnected. Reconnecting…"); };
    void refresh();
    return () => { active = false; events.close(); };
  }, []);
  function accept(task: FamilyTask) { revisionRef.current++; setTasks((current) => [task, ...current.filter((item) => item.id !== task.id)]); }
  async function createTask(childId: string, text: string) { accept(await requestTask("/api/tasks", "POST", { family_id: family.id, child_id: childId, text })); }
  async function setTaskStatus(id: string, status: FamilyTask["status"]) { accept(await requestTask(`/api/tasks/${id}`, "PATCH", { status })); }
  async function deleteTask(id: string) { await requestTask(`/api/tasks/${id}`, "DELETE"); revisionRef.current++; setTasks((current) => current.filter((item) => item.id !== id)); }
  async function reviseTask(id: string, instruction: string) { accept(await requestTask(`/api/tasks/${id}/revise`, "POST", { instruction })); }
  async function answerQuestion(id: string, questionId: string, answer: string, approved: boolean) { accept(await requestTask(`/api/tasks/${id}/questions/${questionId}`, "POST", { answer, approved })); }
  return { createTask, deleteTask, error, loaded, setTaskStatus, tasks, reviseTask, answerQuestion };
}
async function requestTask(path: string, method: string, body?: object) {
  const response = await fetch(path, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  if (response.status === 204) return;
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || payload.detail || "Could not save task.");
  return payload;
}
