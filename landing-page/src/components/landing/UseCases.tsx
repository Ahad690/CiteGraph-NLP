import { Brain, Microscope, ClipboardList, Compass, Network, BarChart3 } from "lucide-react";
import { SectionHeader } from "./SectionHeader";

const items = [
  { icon: Brain, title: "NLP Course Projects", desc: "Demonstrate PDF parsing, entity extraction, citation traversal, and knowledge graph construction in one complete project." },
  { icon: Microscope, title: "Biomedical Literature Review", desc: "Explore population evidence and citation lineage behind clinical studies." },
  { icon: ClipboardList, title: "Systematic Review Preparation", desc: "Quickly identify older connected papers and evidence-rich citation paths." },
  { icon: Compass, title: "Research Idea Tracing", desc: "Follow references backward to understand how a research idea developed." },
  { icon: Network, title: "Knowledge Graph Experiments", desc: "Export citation networks as GraphML or JSON for downstream graph analytics." },
  { icon: BarChart3, title: "Evidence-Aware Ranking", desc: "Compare papers using population-size signals, source metrics, and confidence scores." },
];

export function UseCases() {
  return (
    <section id="use-cases" className="relative py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Use Cases"
          title={<>Designed for <span className="text-gradient-brand">serious research workflows.</span></>}
          subtitle="Whether you are building an NLP project, reviewing biomedical evidence, or mapping a research field, CiteGraph-NLP helps you understand the structure behind the literature."
        />
        <div className="mt-14 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-2xl border border-slate-700/40 bg-slate-900/60 backdrop-blur-xl p-6 hover:-translate-y-1 hover:border-cyan-400/30 hover:shadow-xl hover:shadow-cyan-500/10 transition-all duration-300">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo/30 to-cyan/30 grid place-items-center border border-cyan-400/20">
                <Icon className="w-5 h-5 text-cyan-300" />
              </div>
              <h3 className="mt-4 font-semibold text-white">{title}</h3>
              <p className="mt-2 text-sm text-slate-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
