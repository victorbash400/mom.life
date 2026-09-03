import styles from "./FamilyAvatar.module.css";

interface FamilyAvatarProps {
  name: string;
  position: string;
  size?: "small" | "large";
}

export function FamilyAvatar({ name, position, size = "small" }: FamilyAvatarProps) {
  return (
    <span
      className={styles.avatar}
      data-size={size}
      role="img"
      aria-label={`${name}'s profile`}
      style={{ backgroundPosition: position }}
    />
  );
}
