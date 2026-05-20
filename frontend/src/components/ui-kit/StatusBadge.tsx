import type { RunStatus } from "@/types/api";

interface Props {
  status: RunStatus | string;
  small?: boolean;
}

const MAP: Record<string, { label: string; bg: string; text: string; ring: string }> = {
  completed: { label: "Completed", bg: "rgba(16,185,129,0.12)", text: "#34d399", ring: "rgba(16,185,129,0.35)" },
  failed: { label: "Failed", bg: "rgba(244,63,94,0.12)", text: "#fb7185", ring: "rgba(244,63,94,0.35)" },
  running: { label: "Running", bg: "rgba(245,158,11,0.12)", text: "#fbbf24", ring: "rgba(245,158,11,0.35)" },
  processing: { label: "Processing", bg: "rgba(245,158,11,0.12)", text: "#fbbf24", ring: "rgba(245,158,11,0.35)" },
  started: { label: "Started", bg: "rgba(245,158,11,0.12)", text: "#fbbf24", ring: "rgba(245,158,11,0.35)" },
  pending: { label: "Pending", bg: "rgba(148,163,184,0.12)", text: "#cbd5e1", ring: "rgba(148,163,184,0.3)" },
};

export function StatusBadge({ status, small }: Props) {
  const conf = MAP[status] || MAP.pending;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold ${small ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-[11px]"}`}
      style={{ backgroundColor: conf.bg, color: conf.text, border: `1px solid ${conf.ring}` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: conf.text }} />
      {conf.label}
    </span>
  );
}
