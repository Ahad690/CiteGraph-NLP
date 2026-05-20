interface Props {
  role: "seed" | "cited" | "citing" | "foundational";
}

const MAP = {
  seed: { label: "Seed Paper", bg: "linear-gradient(135deg, rgba(79,70,229,0.18), rgba(6,182,212,0.18))", text: "#a5b4fc", border: "rgba(99,102,241,0.45)" },
  cited: { label: "Cited", bg: "rgba(148,163,184,0.1)", text: "#cbd5e1", border: "rgba(148,163,184,0.25)" },
  citing: { label: "Citing", bg: "rgba(148,163,184,0.1)", text: "#cbd5e1", border: "rgba(148,163,184,0.25)" },
  foundational: { label: "Foundational", bg: "rgba(139,92,246,0.14)", text: "#c4b5fd", border: "rgba(139,92,246,0.4)" },
};

export function RoleBadge({ role }: Props) {
  const c = MAP[role];
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
      style={{ background: c.bg, color: c.text, border: `1px solid ${c.border}` }}
    >
      {c.label}
    </span>
  );
}
