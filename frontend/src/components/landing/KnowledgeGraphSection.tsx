import { SectionHeader } from "./SectionHeader";

export function KnowledgeGraphSection() {
  const cards = [
    { t: "Node size = study population", d: "Bigger nodes carry larger N_eff." },
    { t: "Edge thickness = citation weight", d: "Stronger weighted edges glow brighter." },
    { t: "Color = confidence level", d: "Emerald, amber, rose by extraction confidence." },
    { t: "Ring = foundational candidate", d: "Probable foundations are highlighted with a ring." },
    { t: "Direction = citation lineage", d: "Edges flow from later → earlier work." },
  ];
  return (
    <section id="showcase" className="relative py-24 bg-gradient-to-b from-transparent via-slate-950/40 to-transparent">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Graph Intelligence"
          title={<>See how research papers connect <span className="text-gradient-brand">across generations.</span></>}
          subtitle="Visualize citation direction, population evidence, confidence levels, and probable foundational papers in one graph."
        />
        <div className="mt-14 grid lg:grid-cols-[1.4fr_1fr] gap-6">
          <div className="relative rounded-3xl border border-slate-700/50 bg-slate-950/60 backdrop-blur-xl p-6 overflow-hidden h-[460px]">
            <BigGraph />
            <div className="absolute top-4 left-4 flex flex-wrap gap-2 text-[10px]">
              <Tag color="cyan" label="Seed Paper" />
              <Tag color="emerald" label="High N_eff" />
              <Tag color="purple" label="Probable Foundation" />
              <Tag color="rose" label="Low Confidence" />
            </div>
            <div className="absolute bottom-4 right-4 text-[10px] uppercase tracking-[0.18em] text-slate-500">Weighted citation edge</div>
          </div>
          <div className="space-y-3">
            {cards.map((c) => (
              <div key={c.t} className="rounded-2xl border border-slate-700/40 bg-slate-900/60 backdrop-blur-xl p-5 hover:border-cyan-400/30 transition">
                <div className="font-semibold text-white">{c.t}</div>
                <div className="text-sm text-slate-400 mt-1">{c.d}</div>
              </div>
            ))}
            <div className="rounded-2xl border border-slate-700/40 bg-slate-900/60 backdrop-blur-xl p-5 grid grid-cols-2 gap-2 text-xs">
              <Legend color="#10b981" label="High confidence" />
              <Legend color="#f59e0b" label="Medium confidence" />
              <Legend color="#f43f5e" label="Low confidence" />
              <Legend color="#64748b" label="Missing data" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Tag({ color, label }: { color: string; label: string }) {
  const c: Record<string, string> = {
    cyan: "bg-cyan-400/15 text-cyan-200 border-cyan-400/30",
    emerald: "bg-emerald/15 text-emerald border-emerald/30",
    purple: "bg-purple/15 text-purple border-purple/30",
    rose: "bg-rose/15 text-rose border-rose/30",
  };
  return <span className={`px-2 py-1 rounded-full border ${c[color]}`}>{label}</span>;
}
function Legend({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2 text-slate-300">
      <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} /> {label}
    </div>
  );
}

function BigGraph() {
  type N = { id: string; x: number; y: number; r: number; kind: string; label?: string };
  const nodes: N[] = [
    { id: "seed", x: 420, y: 200, r: 22, kind: "seed", label: "Seed" },
    { id: "f1", x: 180, y: 110, r: 16, kind: "found", label: "Foundation A" },
    { id: "f2", x: 140, y: 280, r: 14, kind: "found", label: "Foundation B" },
    { id: "h1", x: 300, y: 60, r: 12, kind: "high" },
    { id: "h2", x: 600, y: 80, r: 14, kind: "high" },
    { id: "h3", x: 660, y: 230, r: 10, kind: "high" },
    { id: "m1", x: 320, y: 340, r: 10, kind: "med" },
    { id: "m2", x: 540, y: 340, r: 9, kind: "med" },
    { id: "l1", x: 220, y: 380, r: 7, kind: "low" },
    { id: "n1", x: 80, y: 200, r: 6, kind: "miss" },
    { id: "n2", x: 720, y: 380, r: 6, kind: "miss" },
  ];
  const edges: [string, string, number][] = [
    ["seed", "f1", 2.4], ["seed", "f2", 2], ["seed", "h1", 1.4], ["seed", "h2", 1.6],
    ["seed", "h3", 1.2], ["seed", "m1", 1], ["seed", "m2", 1], ["seed", "l1", 0.8],
    ["f1", "n1", 0.6], ["f2", "n1", 0.6], ["h1", "f1", 1.2], ["h2", "h3", 1],
    ["m1", "f2", 0.9], ["m2", "h3", 0.7], ["l1", "f2", 0.5], ["h3", "n2", 0.5],
  ];
  const fill = (k: string) =>
    k === "seed" ? "url(#seedG)" :
    k === "found" ? "#8b5cf6" :
    k === "high" ? "#10b981" :
    k === "med" ? "#f59e0b" :
    k === "low" ? "#f43f5e" : "#64748b";

  return (
    <svg viewBox="0 0 800 440" className="w-full h-full">
      <defs>
        <linearGradient id="seedG" x1="0" x2="1">
          <stop offset="0%" stopColor="#4f46e5" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
        <radialGradient id="glow"><stop offset="0%" stopColor="rgba(6,182,212,0.5)" /><stop offset="100%" stopColor="rgba(6,182,212,0)" /></radialGradient>
      </defs>
      {edges.map(([a, b, w], i) => {
        const na = nodes.find((n) => n.id === a)!;
        const nb = nodes.find((n) => n.id === b)!;
        return (
          <line key={i} x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
            stroke="#06b6d4" strokeOpacity={0.25 + w * 0.15} strokeWidth={w}
            strokeDasharray="6 6" className="animate-edge-flow" />
        );
      })}
      {nodes.map((n) => (
        <g key={n.id}>
          {n.kind === "seed" && <circle cx={n.x} cy={n.y} r={n.r + 18} fill="url(#glow)" />}
          {n.kind === "found" && <circle cx={n.x} cy={n.y} r={n.r + 6} fill="none" stroke="#8b5cf6" strokeOpacity={0.6} strokeWidth={1.5} />}
          {n.kind === "seed" && <circle cx={n.x} cy={n.y} r={n.r + 10} fill="none" stroke="#06b6d4" strokeOpacity={0.7} className="animate-pulse-glow" />}
          <circle cx={n.x} cy={n.y} r={n.r} fill={fill(n.kind)} />
          {n.label && <text x={n.x} y={n.y + n.r + 14} textAnchor="middle" fill="#cbd5e1" fontSize={11}>{n.label}</text>}
        </g>
      ))}
    </svg>
  );
}
