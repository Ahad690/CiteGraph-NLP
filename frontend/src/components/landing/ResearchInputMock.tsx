import { useEffect, useState } from "react";
import { Database, FileSearch, Network, Sparkles, Trophy, Check } from "lucide-react";

const steps = [
  { icon: Database, label: "Metadata resolved" },
  { icon: Network, label: "Citations retrieved" },
  { icon: FileSearch, label: "Population evidence extracted" },
  { icon: Sparkles, label: "Graph built" },
  { icon: Trophy, label: "Rankings calculated" },
];

const stats = [
  { value: "47", label: "Papers" },
  { value: "126", label: "Citation Edges" },
  { value: "18", label: "Population Values" },
  { value: "6", label: "Probable Foundations" },
];

export function ResearchInputMock() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setActive((a) => (a + 1) % (steps.length + 1)), 1200);
    return () => clearInterval(t);
  }, []);

  return (
    <section className="relative -mt-4 md:-mt-8 pb-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="relative rounded-[28px] border border-slate-700/50 bg-slate-900/70 backdrop-blur-xl shadow-2xl shadow-black/40 overflow-hidden animate-float">
          {/* chrome */}
          <div className="flex items-center gap-2 px-5 py-3 border-b border-slate-800/80 bg-slate-950/60">
            <div className="flex gap-1.5">
              <span className="w-3 h-3 rounded-full bg-rose/70" />
              <span className="w-3 h-3 rounded-full bg-amber/70" />
              <span className="w-3 h-3 rounded-full bg-emerald/70" />
            </div>
            <div className="mx-auto text-xs text-slate-400 bg-slate-800/60 rounded-full px-4 py-1 border border-slate-700/60">
              citegraph-nlp.app/analyze
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-0">
            {/* left */}
            <div className="p-6 md:p-8 border-b lg:border-b-0 lg:border-r border-slate-800/70">
              <div className="text-[11px] uppercase tracking-[0.14em] text-slate-400">Seed Paper</div>
              <div className="mt-2 rounded-xl border border-slate-700/70 bg-slate-950/50 px-4 py-3 font-mono text-sm text-cyan-200">
                10.1056/NEJMoa2034577
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-slate-400 mb-1">Input Type</div>
                  <div className="rounded-lg border border-slate-700/70 bg-slate-950/50 px-3 py-2 text-sm">DOI</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400 mb-1">Backward Depth</div>
                  <div className="rounded-lg border border-slate-700/70 bg-slate-950/50 px-3 py-2 text-sm flex items-center justify-between">
                    <span>2</span>
                    <div className="flex-1 mx-3 h-1 rounded-full bg-slate-800 relative">
                      <div className="absolute inset-y-0 left-0 w-1/2 rounded-full bg-gradient-to-r from-indigo to-cyan" />
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-3">
                <div className="text-xs text-slate-400 mb-1">Max Papers</div>
                <div className="rounded-lg border border-slate-700/70 bg-slate-950/50 px-3 py-2 text-sm flex items-center justify-between">
                  <span>50</span>
                  <div className="flex-1 mx-3 h-1 rounded-full bg-slate-800 relative">
                    <div className="absolute inset-y-0 left-0 w-2/3 rounded-full bg-gradient-to-r from-indigo to-cyan" />
                  </div>
                </div>
              </div>

              <button className="mt-5 w-full bg-gradient-to-r from-indigo to-cyan text-white font-semibold py-3 rounded-xl shadow-lg shadow-cyan-500/20">
                Analyze Citation Lineage
              </button>

              <div className="mt-6 space-y-2">
                {steps.map((s, i) => {
                  const done = i < active;
                  const Icon = s.icon;
                  return (
                    <div
                      key={s.label}
                      className={`flex items-center gap-3 text-sm rounded-lg px-3 py-2 border transition-all ${
                        done
                          ? "border-emerald/30 bg-emerald/10 text-emerald"
                          : i === active
                          ? "border-cyan-400/30 bg-cyan-400/10 text-cyan-200"
                          : "border-slate-800 text-slate-500"
                      }`}
                    >
                      {done ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                      {s.label}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* right */}
            <div className="relative p-6 md:p-8 bg-gradient-to-br from-slate-950/40 to-slate-900/30">
              <div className="grid grid-cols-2 gap-3">
                {stats.map((s) => (
                  <div key={s.label} className="rounded-xl border border-slate-700/60 bg-slate-900/60 p-4">
                    <div className="text-2xl font-bold text-white animate-number-count">{s.value}</div>
                    <div className="text-xs text-slate-400 mt-1">{s.label}</div>
                  </div>
                ))}
              </div>

              <div className="mt-5 relative h-72 rounded-xl border border-slate-700/60 bg-slate-950/60 overflow-hidden">
                <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent animate-scan-line" />
                <MiniGraph />
                <div className="absolute bottom-3 left-3 flex flex-wrap gap-2 text-[10px]">
                  <span className="px-2 py-1 rounded-full bg-emerald/15 text-emerald border border-emerald/30">High N_eff</span>
                  <span className="px-2 py-1 rounded-full bg-purple/15 text-purple border border-purple/30">Foundational</span>
                  <span className="px-2 py-1 rounded-full bg-cyan-400/15 text-cyan-300 border border-cyan-400/30">Seed</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function MiniGraph() {
  // node positions
  const nodes = [
    { id: "seed", x: 200, y: 130, r: 14, kind: "seed" },
    { id: "a", x: 80, y: 60, r: 10, kind: "found" },
    { id: "b", x: 60, y: 200, r: 8, kind: "med" },
    { id: "c", x: 320, y: 70, r: 12, kind: "found" },
    { id: "d", x: 350, y: 220, r: 9, kind: "high" },
    { id: "e", x: 160, y: 240, r: 7, kind: "low" },
    { id: "f", x: 260, y: 30, r: 8, kind: "med" },
  ];
  const edges = [
    ["seed", "a"], ["seed", "b"], ["seed", "c"], ["seed", "d"], ["seed", "e"], ["seed", "f"],
    ["a", "b"], ["c", "f"], ["d", "e"],
  ];
  const fill = (k: string) =>
    k === "seed" ? "url(#seedGrad)" :
    k === "found" ? "#8b5cf6" :
    k === "high" ? "#10b981" :
    k === "med" ? "#f59e0b" :
    k === "low" ? "#f43f5e" : "#64748b";

  return (
    <svg viewBox="0 0 400 280" className="w-full h-full">
      <defs>
        <linearGradient id="seedGrad" x1="0" x2="1">
          <stop offset="0%" stopColor="#4f46e5" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      {edges.map(([a, b], i) => {
        const na = nodes.find((n) => n.id === a)!;
        const nb = nodes.find((n) => n.id === b)!;
        return (
          <line
            key={i}
            x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
            stroke="#06b6d4"
            strokeOpacity={0.35}
            strokeWidth={a === "seed" ? 1.6 : 0.8}
            strokeDasharray="6 6"
            className="animate-edge-flow"
          />
        );
      })}
      {nodes.map((n) => (
        <g key={n.id}>
          {n.kind === "found" && (
            <circle cx={n.x} cy={n.y} r={n.r + 6} fill="none" stroke="#8b5cf6" strokeOpacity={0.5} />
          )}
          {n.kind === "seed" && (
            <circle cx={n.x} cy={n.y} r={n.r + 8} fill="none" stroke="#06b6d4" strokeOpacity={0.6} className="animate-pulse-glow" />
          )}
          <circle cx={n.x} cy={n.y} r={n.r} fill={fill(n.kind)} />
        </g>
      ))}
    </svg>
  );
}
