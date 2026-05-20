import { GitBranch, FileSearch, Compass, ArrowRight } from "lucide-react";
import { SectionHeader } from "./SectionHeader";

const pains = [
  { icon: GitBranch, title: "Citation networks are messy", desc: "A single paper can connect to hundreds of earlier studies across multiple generations of references." },
  { icon: FileSearch, title: "Sample sizes are buried in text", desc: "Papers mention enrolled patients, randomized participants, analyzed cohorts, arms, events, and follow-ups — not all numbers mean the same thing." },
  { icon: Compass, title: "Foundational work is hard to identify", desc: "The most useful earlier paper is not always the most cited paper. Evidence strength and graph position both matter." },
];

export function ProblemSection() {
  return (
    <section className="relative py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="The Research Discovery Problem"
          title={<>Citation counts tell you what is popular.<br /><span className="text-slate-400">They do not tell you where the idea came from.</span></>}
          subtitle="Modern papers cite dozens of earlier works. Those papers cite even more. Important population evidence is buried inside abstracts, methods sections, and tables. Manually tracing the lineage is slow, incomplete, and hard to explain."
        />

        <div className="mt-14 grid md:grid-cols-3 gap-5">
          {pains.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-2xl border border-slate-700/40 bg-slate-900/60 backdrop-blur-xl p-6 hover:-translate-y-1 hover:border-cyan-400/30 hover:shadow-xl hover:shadow-cyan-500/10 transition-all duration-300">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo/30 to-cyan/30 grid place-items-center border border-cyan-400/20">
                <Icon className="w-5 h-5 text-cyan-300" />
              </div>
              <h3 className="mt-4 font-semibold text-white">{title}</h3>
              <p className="mt-2 text-sm text-slate-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-14 grid md:grid-cols-[1fr_auto_1fr] items-center gap-6">
          <div className="rounded-2xl border border-slate-700/40 bg-slate-900/40 p-6 h-64 relative overflow-hidden">
            <div className="text-xs uppercase tracking-[0.14em] text-slate-500 mb-2">Tangled references</div>
            <svg viewBox="0 0 300 200" className="w-full h-44">
              {Array.from({ length: 24 }).map((_, i) => {
                const x1 = (i * 37) % 300, y1 = (i * 53) % 200;
                const x2 = (i * 71 + 30) % 300, y2 = (i * 19 + 50) % 200;
                return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#64748b" strokeOpacity={0.4} strokeWidth={0.6} />;
              })}
              {Array.from({ length: 14 }).map((_, i) => (
                <circle key={i} cx={(i * 41) % 300} cy={(i * 67) % 200} r={3} fill="#64748b" />
              ))}
            </svg>
          </div>
          <div className="flex flex-col items-center justify-center text-center">
            <div className="rounded-full bg-gradient-to-r from-indigo to-cyan text-white text-sm font-semibold px-4 py-2 shadow-lg shadow-cyan-500/20">CiteGraph-NLP</div>
            <ArrowRight className="hidden md:block mt-3 text-cyan-300" />
          </div>
          <div className="rounded-2xl border border-cyan-400/30 bg-slate-900/60 p-6 h-64 relative overflow-hidden">
            <div className="text-xs uppercase tracking-[0.14em] text-cyan-300 mb-2">Structured lineage</div>
            <svg viewBox="0 0 300 200" className="w-full h-44">
              {[[40,100,150,60],[40,100,150,140],[150,60,260,40],[150,60,260,100],[150,140,260,150],[150,140,260,180]].map(([x1,y1,x2,y2], i) => (
                <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#06b6d4" strokeOpacity={0.6} strokeWidth={1.2} />
              ))}
              <circle cx={40} cy={100} r={8} fill="url(#g1)" />
              <circle cx={150} cy={60} r={6} fill="#8b5cf6" />
              <circle cx={150} cy={140} r={6} fill="#10b981" />
              <circle cx={260} cy={40} r={5} fill="#f59e0b" />
              <circle cx={260} cy={100} r={5} fill="#10b981" />
              <circle cx={260} cy={150} r={5} fill="#8b5cf6" />
              <circle cx={260} cy={180} r={4} fill="#f43f5e" />
              <defs>
                <linearGradient id="g1"><stop stopColor="#4f46e5" /><stop offset="1" stopColor="#06b6d4" /></linearGradient>
              </defs>
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}
