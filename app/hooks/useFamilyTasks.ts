"use client";
import { useEffect, useRef, useState } from "react";
import { subscribeFamilyEvents } from "../lib/familyEvents";
import { useFamily } from "../components/FamilyProvider";
import type { FamilyTask } from "../types/goals";
export type { FamilyTask } from "../types/goals";

const taskCache = new Map<string, FamilyTask[]>();

export function useFamilyTasks() {
  const { family } = useFamily();
  const revisionRef = useRef(0);
  const connectedOnce = useRef(false);
  const [tasks, setTasks] = useState<FamilyTask[]>(() => taskCache.get(family.id) ?? []);
  const [loaded, setLoaded] = useState(() => taskCache.has(family.id));
  const [error, setError] = useState<string>();
  useEffect(() => {
    let active = true;
    let refreshing = false;
    let pending = false;
    async function refresh() {
      pending = true;
      if (refreshing) return;
      refreshing = true;
      try {
        do {
          pending = false;
          const revision = revisionRef.current;
          try {
            const response = await fetch("/api/tasks", { cache: "no-store" });
            const payload = await response.json();
            if (!response.ok || !Array.isArray(payload)) throw new Error(payload.error || "Could not load tasks.");
            if (active && revision === revisionRef.current) { taskCache.set(family.id, payload); setTasks(payload); setError(undefined); }
          } catch (cause) { if (active) setError(cause instanceof Error ? cause.message : "Could not load tasks."); }
          finally { if (active) setLoaded(true); }
        } while (active && pending);
      } finally { refreshing = false; }
    }
    const unsubscribe = subscribeFamilyEvents({
      onEvent: (event) => { if (event.type === "goals_changed") void refresh(); },
      onConnection: (connected) => {
        if (!active) return;
        if (!connected) return setError("Live task updates are disconnected. Reconnecting…");
        if (connectedOnce.current) void refresh();
        connectedOnce.current = true;
      },
    });
    void refresh();
    return () => { active = false; unsubscribe(); };
  }, [family.id]);
  function replace(next: FamilyTask[]) { taskCache.set(family.id, next); return next; }
  function accept(task: FamilyTask) { revisionRef.current++; setTasks((current) => replace([task, ...current.filter((item) => item.id !== task.id)])); }
  async function createTask(childId: string, text: string) { accept(await requestTask("/api/tasks", "POST", { child_id: childId, text })); }
  async function setTaskStatus(id: string, status: FamilyTask["status"]) { accept(await requestTask(`/api/tasks/${id}`, "PATCH", { status })); }
  async function deleteTask(id: string) { await requestTask(`/api/tasks/${id}`, "DELETE"); revisionRef.current++; setTasks((current) => replace(current.filter((item) => item.id !== id))); }
  async function reviseTask(id: string, instruction: string) { accept(await requestTask(`/api/tasks/${id}/revise`, "POST", { instruction })); }
  async function answerQuestion(id: string, questionId: string, answer: string) { accept(await requestTask(`/api/tasks/${id}/questions/${questionId}`, "POST", { answer })); }
  return { createTask, deleteTask, error, loaded, setTaskStatus, tasks, reviseTask, answerQuestion };
}
async function requestTask(path: string, method: string, body?: object) {
  const response = await fetch(path, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  if (response.status === 204) return;
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || payload.detail || "Could not save task.");
  return payload;
}
