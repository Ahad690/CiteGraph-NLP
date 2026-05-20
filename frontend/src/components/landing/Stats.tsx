import { Network, GitBranch, Database, ShieldCheck } from "lucide-react";

const stats = [
  { icon: Network, value: "100", label: "Papers per MVP run", desc: "Depth-limited citation traversal" },
  { icon: GitBranch, value: "2", label: "Default backward depth", desc: "Trace cited papers recursively" },
  { icon: Database, value: "5+", label: "Metadata sources", desc: "OpenAlex, Crossref, PubMed, Europe PMC, Semantic Scholar" },
  { icon: ShieldCheck, value: "100%", label: "Confidence-aware", desc: "Every uncertain result is labeled" },
];

export function Stats() {
  return (
    <section className="relative py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(({ icon: Icon, value, label, desc }) => (
          <div key={label} className="bg-slate-900/60 border border-slate-700/40 rounded-2xl p-6 backdrop-blur-xl hover:border-cyan-400/30 transition-all">
            <Icon className="w-6 h-6 text-cyan-300" />
            <div className="mt-4 text-4xl font-bold text-white">{value}</div>
            <div className="mt-1 text-sm font-medium text-slate-200">{label}</div>
            <div className="mt-1 text-xs text-slate-400">{desc}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
