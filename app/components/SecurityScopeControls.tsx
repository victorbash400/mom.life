import type { SecuritySettings } from "../types/security";
import { SettingsRow } from "./SettingsRow";
type Policy = Pick<SecuritySettings, "sources" | "child_ids" | "depth" | "review_mode" | "channel">;
export function SecurityScopeControls({ policy, onChange, childrenProfiles, disabled }: { policy: Policy; onChange: (value: Policy) => void; childrenProfiles: { id: string; name: string }[]; disabled: boolean }) {
  return <>
    <SettingsRow title="Review frequency" control={<select aria-label="Review frequency" disabled={disabled} value={policy.review_mode} onChange={(e) => onChange({ ...policy, review_mode: e.target.value as Policy["review_mode"] })}><option value="incoming">When information arrives</option><option value="manual">Only when I check</option></select>} />
    <SettingsRow title="Sources" control={<select aria-label="Safety sources" disabled={disabled} value={policy.sources[0] ?? ""} onChange={(e) => onChange({ ...policy, sources: e.target.value ? [e.target.value] : [] })}><option value="">All incoming sources</option><option value="upload">Uploaded files</option><option value="whatsapp">WhatsApp</option><option value="email">Email</option></select>} />
    <SettingsRow title="Children" control={<select aria-label="Safety child scope" disabled={disabled} value={policy.child_ids[0] ?? ""} onChange={(e) => onChange({ ...policy, child_ids: e.target.value ? [e.target.value] : [] })}><option value="">Whole family</option>{childrenProfiles.map((child) => <option key={child.id} value={child.id}>{child.name}</option>)}</select>} />
    <SettingsRow title="Review depth" control={<select aria-label="Safety review depth" disabled={disabled} value={policy.depth} onChange={(e) => onChange({ ...policy, depth: e.target.value as Policy["depth"] })}><option value="item">Current item</option><option value="recent">Item + 10 recent matching items</option></select>} />
    <SettingsRow title="Alert channel" control={<select aria-label="Safety alert channel" disabled value="in_app"><option value="in_app">In-app Safety alerts</option></select>} />
  </>;
}
