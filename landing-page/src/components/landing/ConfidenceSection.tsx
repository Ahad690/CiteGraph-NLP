import { AlertTriangle } from "lucide-react";
import { SectionHeader } from "./SectionHeader";

export function ConfidenceSection() {
  return (
    <section className="relative py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Built for uncertainty"
          title={<>Research data is messy. <span className="text-gradient-brand">CiteGraph-NLP makes uncertainty visible.</span></>}
          subtitle="Instead of pretending every extraction is perfect, the system labels ambiguity, tracks provenance, and assigns confidence scores to metadata, population evidence, and citation edges."
        />

        <div className="mt-14 grid lg:grid-cols-3 gap-5">
          {/* Panel 1 */}
          <div className="relative rounded-2xl border border-slate-700/40 bg-slate-900/60 backdrop-blur-xl p-6 overflow-hidden">
            <div className="text-xs uppercase tracking-[0.14em] text-cyan-300">Evidence Sentence</div>
            <p className="mt-3 text-sm leading-relaxed text-slate-200">
              “A total of <mark className="bg-emerald/20 text-emerald rounded px-1">8,500 patients</mark> were{" "}
              <mark className="bg-cyan-400/20 text-cyan-200 rounded px-1">randomized</mark>, with 4,250 assigned to treatment and 4,250 assigned to control.”
            </p>
            <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent animate-scan-line" />
            <div className="mt-4 text-xs text-slate-500">Source: Methods § Trial Design</div>
          </div>

          {/* Panel 2 */}
          <div className="rounded-2xl border border-slate-700/40 bg-slate-900/60 backdrop-blur-xl p-6">
            <div className="text-xs uppercase tracking-[0.14em] text-cyan-300">Semantic Classification</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-emerald/15 text-emerald border border-emerald/30">TOTAL_RANDOMIZED</span>
              <span className="text-xs px-2.5 py-1 rounded-full bg-emerald/15 text-emerald border border-emerald/30">Confidence: High</span>
              <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">Section: Methods</span>
              <span className="text-xs px-2.5 py-1 rounded-full bg-cyan-400/10 text-cyan-200 border border-cyan-400/30">N_eff: 8,500</span>
            </div>
            <div className="mt-5 space-y-2 text-xs">
              <Row color="emerald" label="High" range="≥ 0.75" />
              <Row color="amber" label="Medium" range="0.45 – 0.74" />
              <Row color="rose" label="Low" range="< 0.45" />
            </div>
          </div>

          {/* Panel 3 */}
          <div className="rounded-2xl border border-amber/30 bg-amber/5 backdrop-blur-xl p-6">
            <div className="flex items-center gap-2 text-amber">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-xs uppercase tracking-[0.14em]">Ambiguity Handling</span>
            </div>
            <p className="mt-3 text-sm text-slate-200 leading-relaxed">
              Multiple candidate values found. Marked ambiguous until reviewed.
            </p>
            <div className="mt-4 space-y-2 text-xs text-slate-300">
              <div className="rounded-lg bg-slate-900/60 border border-slate-700 p-2 flex justify-between"><span>"3,200 enrolled"</span><span className="text-amber">0.62</span></div>
              <div className="rounded-lg bg-slate-900/60 border border-slate-700 p-2 flex justify-between"><span>"2,850 analyzed"</span><span className="text-amber">0.58</span></div>
              <div className="rounded-lg bg-slate-900/60 border border-slate-700 p-2 flex justify-between"><span>"100 in pilot"</span><span className="text-rose">0.31</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Row({ color, label, range }: { color: "emerald" | "amber" | "rose"; label: string; range: string }) {
  const map = { emerald: "bg-emerald", amber: "bg-amber", rose: "bg-rose" };
  return (
    <div className="flex items-center gap-3 text-slate-300">
      <span className={`w-2.5 h-2.5 rounded-full ${map[color]}`} />
      <span className="font-medium">{label}</span>
      <span className="text-slate-500 ml-auto">{range}</span>
    </div>
  );
}
