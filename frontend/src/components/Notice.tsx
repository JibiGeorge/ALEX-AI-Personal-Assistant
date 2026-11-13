interface NoticeProps {
  kind: "error" | "success";
  children: string;
  onDismiss: () => void;
}

export function Notice({ kind, children, onDismiss }: NoticeProps) {
  return (
    <div className={`notice notice-${kind}`} role={kind === "error" ? "alert" : "status"}>
      <span>{children}</span>
      <button aria-label="Dismiss notification" onClick={onDismiss} type="button">
        ×
      </button>
    </div>
  );
}
