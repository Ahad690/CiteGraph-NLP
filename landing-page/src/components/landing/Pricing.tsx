import { Link } from "@tanstack/react-router";
import { Check } from "lucide-react";
import { SectionHeader } from "./SectionHeader";
import { trackEvent } from "@/lib/analytics";

const plans = [
  {
    name: "Free", price: "$0", desc: "For students and quick experiments.",
    features: ["5 analysis runs/month", "Up to 25 papers per run", "DOI/title input", "Basic metadata resolution", "Basic citation graph", "JSON export", "Community support"],
    cta: "Start Free", to: "/signup", featured: false,
  },
  {
    name: "Researcher", price: "$12", per: "/month", desc: "For serious literature exploration.",
    badge: "Most Popular",
    features: ["100 analysis runs/month", "Up to 250 papers per run", "Population extraction", "Confidence-aware rankings", "Citation paths", "CSV, JSON, GraphML exports", "Priority API queue", "Saved projects"],
    cta: "Start Researcher Plan", to: "/signup", featured: true,
  },
  {
    name: "Lab", price: "$49", per: "/month", desc: "For teams, labs, and advanced graph workflows.",
    features: ["Unlimited saved projects", "Up to 1,000 papers per run", "Team workspace", "Neo4j export", "Batch seed papers", "Shared reports", "Advanced graph analytics", "Priority support"],
    cta: "Contact / Start Lab Plan", to: "/signup", featured: false,
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="relative py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Pricing"
          title={<>Start free. <span className="text-gradient-brand">Scale when your research grows.</span></>}
          subtitle="Use CiteGraph-NLP for course projects, literature review experiments, and citation graph analysis."
        />
        <div className="mt-14 grid lg:grid-cols-3 gap-6">
          {plans.map((p) => (
            <div
              key={p.name}
              className={`relative rounded-3xl border p-7 backdrop-blur-xl transition-all ${
                p.featured
                  ? "border-cyan-400/40 bg-gradient-to-b from-slate-900/80 to-slate-900/40 shadow-2xl shadow-cyan-500/10 lg:-translate-y-3"
                  : "border-slate-700/40 bg-slate-900/60 hover:border-cyan-400/30"
              }`}
            >
              {p.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-semibold bg-gradient-to-r from-indigo to-cyan text-white shadow-lg shadow-cyan-500/30">
                  {p.badge}
                </div>
              )}
              <div className="text-sm text-cyan-300 uppercase tracking-[0.14em]">{p.name}</div>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="text-5xl font-bold text-white">{p.price}</span>
                {p.per && <span className="text-slate-400">{p.per}</span>}
              </div>
              <p className="mt-2 text-slate-400">{p.desc}</p>
              <ul className="mt-6 space-y-2.5">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-slate-200">
                    <Check className="w-4 h-4 text-emerald mt-0.5 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <Link
                to={p.to}
                onClick={() => trackEvent("pricing_plan_click", { plan: p.name })}
                className={`mt-7 block text-center px-5 py-3 rounded-xl font-semibold transition ${
                  p.featured
                    ? "bg-gradient-to-r from-indigo to-cyan text-white shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50"
                    : "border border-slate-700 text-slate-100 hover:border-cyan-400/40 hover:bg-slate-900/70"
                }`}
              >
                {p.cta}
              </Link>
            </div>
          ))}
        </div>
        <p className="mt-8 text-center text-sm text-slate-400">
          Academic use only? Add your <span className="text-cyan-300">.edu</span> email for student-friendly access.
        </p>
      </div>
    </section>
  );
}
