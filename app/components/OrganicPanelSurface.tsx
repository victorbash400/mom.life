import styles from "./OrganicPanelSurface.module.css";

export function OrganicPanelSurface() {
  return (
    <svg className={styles.surface} viewBox="0 0 1112 718" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="panel-fill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#fffaf4" stopOpacity=".9" />
          <stop offset=".55" stopColor="#fff7ef" stopOpacity=".81" />
          <stop offset="1" stopColor="#fcefe8" stopOpacity=".86" />
        </linearGradient>
        <filter id="panel-shadow" x="-15%" y="-15%" width="130%" height="140%">
          <feDropShadow dx="0" dy="19" stdDeviation="18" floodColor="#775144" floodOpacity=".13" />
        </filter>
      </defs>
      <path
        d="M180 0 C320 0 416 72 556 72 C696 72 792 0 932 0 C1031 0 1112 81 1112 180 C1112 265 1100 310 1100 359 C1100 408 1112 453 1112 538 C1112 637 1031 718 932 718 C792 718 696 646 556 646 C416 646 320 718 180 718 C81 718 0 637 0 538 C0 453 12 408 12 359 C12 310 0 265 0 180 C0 81 81 0 180 0 Z"
        fill="url(#panel-fill)"
        stroke="#ffffff"
        strokeOpacity=".72"
        strokeWidth="2"
        filter="url(#panel-shadow)"
      />
      <path
        d="M91 646 C120 690 147 706 180 710 C320 710 416 638 556 638 C696 638 792 710 932 710 C965 706 992 690 1021 646"
        fill="none"
        stroke="#e9b8b2"
        strokeOpacity=".2"
        strokeWidth="15"
        strokeLinecap="round"
      />
    </svg>
  );
}
