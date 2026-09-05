"use client";
import { useEffect, useState } from "react";
import type { FamilySkill } from "../types/goals";
import { SkillEditor } from "./SkillEditor";
import styles from "./SkillsLibrary.module.css";
export function SkillsLibrary() {
  const [skills, setSkills] = useState<FamilySkill[]>([]); const [editing, setEditing] = useState<FamilySkill | null>(); const [error, setError] = useState<string>();
  useEffect(() => { const controller = new AbortController(); fetch("/api/skills", { signal: controller.signal }).then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error); setSkills(payload.skills); }).catch((cause) => { if (!controller.signal.aborted) setError(cause.message); }); return () => controller.abort(); }, []);
  return <section className={styles.library}><header><span>Family skills</span><button onClick={() => setEditing(null)} type="button">New skill</button></header>{error ? <p role="alert">{error}</p> : null}{skills.map((skill) => <button className={styles.skill} key={skill.id} onClick={() => setEditing(skill)} type="button"><strong>{skill.name}</strong><small>{skill.description}</small></button>)}{editing !== undefined ? <SkillEditor key={editing?.id || "new"} skill={editing} onClose={() => setEditing(undefined)} onSaved={(skill) => { setSkills((current) => [...current.filter((item) => item.id !== skill.id), skill]); setEditing(undefined); }} /> : null}</section>;
}
