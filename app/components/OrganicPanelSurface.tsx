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
        d="M174 7 C92 12 23 72 12 150 C1 228 26 281 13 365 C-7 493 17 610 109 671 C186 722 287 714 374 702 C449 692 509 696 568 703 C660 714 741 725 832 711 C938 695 1046 669 1086 579 C1122 496 1095 396 1100 312 C1106 219 1115 144 1065 78 C1013 10 925 2 851 18 C757 38 680 79 579 79 C469 79 374 31 286 13 C247 5 210 3 174 7 Z"
        fill="url(#panel-fill)"
        stroke="#ffffff"
        strokeOpacity=".72"
        strokeWidth="2"
        filter="url(#panel-shadow)"
      />
      <path
        d="M88 650 C213 724 338 682 446 695 C579 711 690 727 823 707 C926 691 1015 657 1070 590"
        fill="none"
        stroke="#e9b8b2"
        strokeOpacity=".2"
        strokeWidth="15"
        strokeLinecap="round"
      />
    </svg>
  );
}
