export function AuthSurface() {
  const outline = "M110 16 C198 8 246 35 300 35 C354 35 402 8 490 16 C551 22 584 66 584 128 C584 216 570 273 575 346 C580 423 590 488 578 558 C568 616 527 645 466 642 C393 639 355 623 300 623 C245 623 207 639 134 642 C73 645 32 616 22 558 C10 488 20 423 25 346 C30 273 16 216 16 128 C16 66 49 22 110 16 Z";
  return <svg viewBox="0 0 600 660" preserveAspectRatio="none" aria-hidden="true" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", overflow: "visible", pointerEvents: "none" }}>
    <defs><linearGradient id="auth-fill" x2="1" y2="1"><stop stopColor="#fffaf4" stopOpacity=".94" /><stop offset="1" stopColor="#fcefe8" stopOpacity=".9" /></linearGradient><filter id="auth-shadow" x="-20%" y="-15%" width="140%" height="145%"><feDropShadow dy="16" stdDeviation="18" floodColor="#775144" floodOpacity=".13" /></filter></defs>
    <path d={outline} fill="url(#auth-fill)" stroke="#fffaf5" strokeWidth="2" filter="url(#auth-shadow)" />
    <path d={outline} transform="translate(9 10) scale(.97)" fill="none" stroke="#e9b8b2" strokeOpacity=".3" strokeWidth="5" vectorEffect="non-scaling-stroke" />
  </svg>;
}
