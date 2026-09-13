import styles from "./LoadingIndicator.module.css";

export function LoadingIndicator({ className = "", fullScreen = false }: { className?: string; fullScreen?: boolean }) {
  return <div aria-live="polite" className={`${styles.indicator} ${className}`} data-full-screen={fullScreen} role="status"><span>Loading</span></div>;
}
