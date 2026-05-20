import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Network } from "lucide-react";

export const Route = createFileRoute("/terms")({
  head: () => ({
    meta: [
      { title: "Terms of Service — CiteGraph-NLP" },
      { name: "description", content: "Terms of Service for CiteGraph-NLP, the confidence-aware citation lineage analysis platform." },
      { property: "og:title", content: "Terms of Service — CiteGraph-NLP" },
      { property: "og:description", content: "Read the terms governing use of CiteGraph-NLP." },
      { property: "og:url", content: "/terms" },
    ],
    links: [{ rel: "canonical", href: "/terms" }],
  }),
  component: TermsPage,
});

const sections = [
  ["Acceptance of Terms", "By accessing CiteGraph-NLP, you agree to be bound by these Terms of Service."],
  ["Description of Service", "CiteGraph-NLP provides confidence-aware citation lineage analysis, knowledge graph construction, and population-evidence extraction for academic research."],
  ["Research and Academic Use", "The service is intended for educational, research, and academic-adjacent workflows."],
  ["User Accounts", "You are responsible for maintaining the confidentiality of your account."],
  ["Acceptable Use", "Do not use the service for unlawful purposes or to attempt to disrupt the platform."],
  ["Data Sources and Metadata", "We rely on third-party scholarly metadata providers. Coverage and accuracy depend on the upstream source."],
  ["AI/NLP Analysis Disclaimer", "Extraction is probabilistic and may miss or mislabel values. Always verify with domain experts."],
  ["No Guarantee of Completeness", "Citation networks are inherently incomplete. Results are exploratory."],
  ["Intellectual Property", "All trademarks and logos are the property of their respective owners."],
  ["Subscription and Billing", "Paid plans are billed monthly. You may cancel anytime."],
  ["Limitation of Liability", "CiteGraph-NLP is provided 'as is' without warranties of any kind."],
  ["Changes to Terms", "We may update these terms. Continued use indicates acceptance."],
  ["Contact Us", "For questions, email research@citegraph-nlp.app."],
];

function TermsPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-16">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-cyan-300">
          <ArrowLeft className="w-4 h-4" /> Back to Home
        </Link>
        <div className="mt-8 flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo to-cyan grid place-items-center shadow-lg shadow-cyan-500/20">
            <Network className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Terms of Service</h1>
            <div className="text-sm text-slate-400">Last updated: May 2026</div>
          </div>
        </div>

        <div className="mt-10 space-y-6">
          {sections.map(([t, d], i) => (
            <section key={t}>
              <h2 className="text-lg font-semibold text-white">{i + 1}. {t}</h2>
              <p className="mt-2 text-slate-300 leading-relaxed">{d}</p>
            </section>
          ))}
        </div>

        <div className="mt-12 rounded-2xl border border-amber/30 bg-amber/5 p-5 text-sm text-slate-300">
          CiteGraph-NLP provides exploratory research analysis and does not guarantee complete citation coverage, perfect extraction accuracy, or definitive research conclusions.
        </div>
      </div>
    </div>
  );
}
