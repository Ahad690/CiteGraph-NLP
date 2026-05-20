import { Link } from "@tanstack/react-router";
import { Search, Database, FileSearch, Network, Trophy } from "lucide-react";
import { SectionHeader } from "./SectionHeader";

const steps = [
  { n: "01", icon: Search, title: "Input a Seed Paper", desc: "Start from a DOI, PMID, paper title, PMCID, or user-provided PDF." },
  { n: "02", icon: Database, title: "Resolve Metadata", desc: "Query scholarly APIs and merge metadata with field-level provenance." },
  { n: "03", icon: FileSearch, title: "Extract Population Evidence", desc: "Use NLP and rule-based extraction to detect population-size candidates and evidence sentences." },
  { n: "04", icon: Network, title: "Build Citation Graph", desc: "Create a directed graph of papers, studies, journals, population observations, and citation edges." },
  { n: "05", icon: Trophy, title: "Rank Probable Foundations", desc: "Rank likely foundational papers using evidence-weighted graph analytics and confidence scores." },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="relative py-24 bg-gradient-to-b from-transparent via-slate-950/40 to-transparent">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="How It Works"
          title={<>From one paper to a <span className="text-gradient-brand">research lineage map.</span></>}
          subtitle="CiteGraph-NLP follows an identifier-first, confidence-aware pipeline designed for realistic academic literature analysis."
        />

        <div className="mt-14 grid md:grid-cols-5 gap-5 relative">
          <div className="hidden md:block absolute top-12 left-[10%] right-[10%] h-px bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent" />
          {steps.map(({ n, icon: Icon, title, desc }) => (
            <div key={n} className="relative rounded-2xl border border-slate-700/40 bg-slate-900/60 backdrop-blur-xl p-5 hover:border-cyan-400/30 transition-all">
              <div className="w-12 h-12 mx-auto rounded-2xl bg-gradient-to-br from-indigo to-cyan grid place-items-center shadow-lg shadow-cyan-500/30">
                <Icon className="w-5 h-5 text-white" />
              </div>
              <div className="mt-3 text-center text-xs uppercase tracking-[0.18em] text-cyan-300">{n}</div>
              <h3 className="mt-2 text-center font-semibold text-white">{title}</h3>
              <p className="mt-2 text-center text-sm text-slate-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-14 text-center">
          <p className="text-slate-300">Start with a DOI and get a citation lineage map in minutes.</p>
          <Link to="/dashboard" className="mt-4 inline-flex bg-gradient-to-r from-indigo to-cyan text-white px-6 py-3 rounded-xl font-semibold shadow-lg shadow-cyan-500/25">
            Start Analysis
          </Link>
        </div>
      </div>
    </section>
  );
}
