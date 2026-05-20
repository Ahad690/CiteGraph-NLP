import { Fingerprint, Database, GitBranch, Users, Tags, ShieldCheck, Network, Trophy } from "lucide-react";
import { SectionHeader } from "./SectionHeader";

const features = [
  { icon: Fingerprint, title: "Identifier-First Metadata Resolution", badge: "Metadata", desc: "Start with DOI, PMID, PMCID, title, or PDF. The system resolves structured metadata before parsing full text." },
  { icon: Database, title: "Multi-Source Scholarly APIs", badge: "Coverage", desc: "Designed to work with OpenAlex, Crossref, Europe PMC, PubMed, Semantic Scholar, and other metadata providers." },
  { icon: GitBranch, title: "Citation Network Traversal", badge: "Knowledge Graph", desc: "Retrieve backward references and forward citations to build depth-limited citation lineage maps." },
  { icon: Users, title: "Population-Size Extraction", badge: "NLP", desc: "Extract candidate sample sizes like randomized patients, enrolled participants, analyzed cohorts, and arm sizes." },
  { icon: Tags, title: "Semantic Evidence Classification", badge: "NLP", desc: "Classify extracted values as TOTAL_RANDOMIZED, TOTAL_ANALYZED, TOTAL_ENROLLED, ARM_SIZE, and more." },
  { icon: ShieldCheck, title: "Confidence Scoring", badge: "Confidence-Aware", desc: "Every extracted value includes a confidence score, evidence sentence, source section, and ambiguity status." },
  { icon: Network, title: "Study-Aware Knowledge Graphs", badge: "Biomedical Ready", desc: "Separate papers, studies, journals, population observations, and citation edges for more realistic modeling." },
  { icon: Trophy, title: "Evidence-Weighted Rankings", badge: "Ranking", desc: "Rank probable foundational papers using citation position, graph connectivity, population evidence, and confidence." },
];

export function Features() {
  return (
    <section id="features" className="relative py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Features"
          title={<>Everything you need to map citation lineage <span className="text-gradient-brand">with confidence.</span></>}
          subtitle="From metadata resolution to population extraction and graph visualization, CiteGraph-NLP gives you an explainable research analysis workflow."
        />
        <div className="mt-14 grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {features.map(({ icon: Icon, title, badge, desc }) => (
            <div key={title} className="bg-slate-900/60 border border-slate-700/40 rounded-2xl p-6 hover:-translate-y-1 hover:border-cyan-400/30 hover:shadow-xl hover:shadow-cyan-500/10 transition-all duration-300">
              <div className="flex items-start justify-between">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo/30 to-cyan/30 grid place-items-center border border-cyan-400/20">
                  <Icon className="w-5 h-5 text-cyan-300" />
                </div>
                <span className="text-[10px] uppercase tracking-[0.14em] text-cyan-200 bg-cyan-400/10 border border-cyan-400/20 rounded-full px-2 py-0.5">{badge}</span>
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
