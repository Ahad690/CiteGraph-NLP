import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Network } from "lucide-react";

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: "Privacy Policy — CiteGraph-NLP" },
      { name: "description", content: "How CiteGraph-NLP handles research inputs, uploaded PDFs, and metadata requests." },
      { property: "og:title", content: "Privacy Policy — CiteGraph-NLP" },
      { property: "og:description", content: "Learn how we collect, use, and protect your data." },
      { property: "og:url", content: "/privacy" },
    ],
    links: [{ rel: "canonical", href: "/privacy" }],
  }),
  component: PrivacyPage,
});

const sections = [
  ["Information We Collect", "We collect account information, paper identifiers you submit, and basic usage analytics."],
  ["Paper Identifiers and Research Inputs", "DOIs, PMIDs, PMCIDs, and paper titles you submit are processed to resolve metadata."],
  ["Uploaded PDFs", "Uploaded PDFs are processed for extraction. Do not upload content you do not have permission to process."],
  ["Metadata Provider Requests", "Identifiers may be sent to providers like OpenAlex, Crossref, PubMed, Europe PMC, and Semantic Scholar."],
  ["How We Use Information", "To deliver and improve the analysis pipeline and to communicate with you about your account."],
  ["Analytics", "We use privacy-respecting analytics to understand product usage."],
  ["Data Storage and Security", "We follow industry-standard practices to protect data at rest and in transit."],
  ["Third-Party Metadata Providers", "Third-party providers operate under their own terms and privacy policies."],
  ["Exported Reports", "Exported JSON, CSV, GraphML, and Markdown reports remain under your control."],
  ["Your Rights", "You may request access, correction, or deletion of your account data."],
  ["Cookies", "We use cookies for session management and analytics. See the cookie banner for choices."],
  ["Changes to Policy", "We may update this policy. Material changes will be communicated."],
  ["Contact Us", "For privacy questions, email research@citegraph-nlp.app."],
];

function PrivacyPage() {
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
            <h1 className="text-3xl font-bold text-white">Privacy Policy</h1>
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
        <div className="mt-12 rounded-2xl border border-cyan-400/30 bg-cyan-400/5 p-5 text-sm text-slate-300">
          Uploaded PDFs and research inputs should be handled responsibly. Do not upload content you do not have permission to process.
        </div>
      </div>
    </div>
  );
}
