import { getConfidenceLevel, formatConfidence } from "@/lib/formatters";

interface Props {
  score?: number | null;
  showValue?: boolean;
}

export function ConfidenceBadge({ score, showValue = true }: Props) {
  const lvl = getConfidenceLevel(score);
  const conf = {
    high: { label: "High", bg: "rgba(16,185,129,0.12)", text: "#34d399", border: "rgba(16,185,129,0.35)" },
    medium: { label: "Medium", bg: "rgba(245,158,11,0.12)", text: "#fbbf24", border: "rgba(245,158,11,0.35)" },
    low: { label: "Low", bg: "rgba(244,63,94,0.12)", text: "#fb7185", border: "rgba(244,63,94,0.35)" },
    missing: { label: "Missing", bg: "rgba(148,163,184,0.1)", text: "#94a3b8", border: "rgba(148,163,184,0.25)" },
  }[lvl];

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold"
      style={{ backgroundColor: conf.bg, color: conf.text, border: `1px solid ${conf.border}` }}
    >
      {conf.label}
      {showValue && score != null && <span className="opacity-75 font-mono">{formatConfidence(score)}</span>}
    </span>
  );
}
