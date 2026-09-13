import { toolById } from "../data/toolDirectory";
import type { ProfileSource } from "../types/profileSources";
import { LoadingIndicator } from "./LoadingIndicator";
import { SettingsSwitch } from "./SettingsSwitch";
import { ToolIcon } from "./ToolIcon";
import styles from "./ProfileSources.module.css";

export function ProfileSources({ busy, embedded = false, error, loaded, profileId, profileName, sources, onToggle }: { busy: string; embedded?: boolean; error: string; loaded: boolean; profileId: string; profileName: string; sources: ProfileSource[]; onToggle: (profileId: string, pluginId: string, enabled: boolean) => void }) {
  if (!loaded) return error ? <p className={styles.error} role="alert">{error}</p> : <LoadingIndicator />;
  const saving = busy.startsWith(`${profileId}:`);
  return <section className={styles.sources} data-embedded={embedded}><h3>Data sources</h3>{sources.length ? <ul>{sources.map((source) => {
    const tool = toolById(source.id);
    const enabled = source.profiles[profileId] ?? true;
    return <li key={source.id}>{tool ? <ToolIcon size="small" tool={tool} /> : null}<span>{source.name}</span><SettingsSwitch checked={enabled} disabled={Boolean(busy)} label={`${source.name} for ${profileName}`} onChange={(next) => onToggle(profileId,source.id,next)} /></li>;
  })}</ul> : <p className={styles.status}>No connected sources</p>}{error ? <p className={styles.error} role="alert">{error}</p> : null}{saving ? <span className={styles.saving}>Saving…</span> : null}</section>;
}
