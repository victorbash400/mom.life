import styles from "./OrganicPanelSurface.module.css";
import type { PanelMode } from "./MomLifeShell";

const homePath = "M180 0 C320 0 416 72 556 72 C696 72 792 0 932 0 C1031 0 1112 81 1112 180 C1112 265 1100 310 1100 359 C1100 408 1112 453 1112 538 C1112 637 1031 718 932 718 C792 718 696 646 556 646 C416 646 320 718 180 718 C81 718 0 637 0 538 C0 453 12 408 12 359 C12 310 0 265 0 180 C0 81 81 0 180 0 Z";
const focusedPath = "M88 0 C258 0 386 12 556 12 C726 12 854 0 1024 0 C1073 0 1112 39 1112 88 C1112 224 1108 291 1108 359 C1108 427 1112 494 1112 630 C1112 679 1073 718 1024 718 C854 718 726 706 556 706 C386 706 258 718 88 718 C39 718 0 679 0 630 C0 494 4 427 4 359 C4 291 0 224 0 88 C0 39 39 0 88 0 Z";

export function OrganicPanelSurface({ mode }: { mode: PanelMode }) {
  const path = mode === "home" ? homePath : focusedPath;
  const light = mode === "plugins" || mode === "simulator";
  return (
    <svg className={styles.surface} viewBox="0 0 1112 718" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="panel-fill" x1="0" y1="0" x2="1" y2="1">
          <stop className={styles.stop} offset="0" stopColor={light ? "#fff" : "#fffaf4"} stopOpacity={light ? ".97" : ".9"} />
          <stop className={styles.stop} offset=".55" stopColor={light ? "#fffdfa" : "#fff7ef"} stopOpacity={light ? ".95" : ".81"} />
          <stop className={styles.stop} offset="1" stopColor={light ? "#fffaf7" : "#fcefe8"} stopOpacity={light ? ".96" : ".86"} />
        </linearGradient>
        <filter id="panel-shadow" x="-15%" y="-15%" width="130%" height="140%">
          <feDropShadow dx="0" dy="19" stdDeviation="18" floodColor="#775144" floodOpacity=".13" />
        </filter>
      </defs>
      <path className={styles.shape}
        d={path}
        fill="url(#panel-fill)"
        stroke="#ffffff"
        strokeOpacity=".72"
        strokeWidth="2"
        filter="url(#panel-shadow)"
      />
      <path className={styles.shape}
        d={path}
        transform="translate(12 12) scale(.978417 .966574)"
        fill="none"
        stroke="#e9b8b2"
        strokeOpacity=".24"
        strokeWidth="6"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
