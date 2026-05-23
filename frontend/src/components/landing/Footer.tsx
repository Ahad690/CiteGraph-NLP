import { Link } from "@tanstack/react-router";
import { Network, Github, Twitter, Linkedin, Mail } from "lucide-react";
import { trackEvent } from "@/lib/analytics";

export function Footer() {
  return (
    <footer className="relative border-t border-slate-800/70 bg-slate-950/80 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14">
        <div className="grid md:grid-cols-4 gap-10">
          <div>
            <Link to="/" className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo to-cyan grid place-items-center shadow-lg shadow-cyan-500/20">
                <Network className="w-5 h-5 text-white" />
              </div>
              <span className="font-semibold text-white">CiteGraph-NLP</span>
            </Link>
            <p className="mt-4 text-sm text-slate-400 leading-relaxed">
              CiteGraph-NLP is a confidence-aware citation lineage and research knowledge graph platform for exploring probable foundational papers and study-scale evidence.
            </p>
            <div className="mt-5 flex gap-3">
              {/* Social links are placeholder for the prototype — render as
                  disabled (non-link) buttons so they neither trap focus on
                  href="#" nor scroll the page back to the top.
                  Replace with real URLs and switch back to <a href=...> when
                  production accounts are available. */}
              {([["Github", Github], ["Twitter", Twitter], ["LinkedIn", Linkedin], ["Email", Mail]] as const).map(([label, Icon]) => (
                <button
                  key={label}
                  type="button"
                  disabled
                  aria-label={`${label} (coming soon)`}
                  title={`${label} link not yet available`}
                  className="w-9 h-9 rounded-lg border border-slate-800 grid place-items-center text-slate-500 cursor-not-allowed"
                >
                  <Icon className="w-4 h-4" />
                </button>
              ))}
            </div>
          </div>

          <FooterCol title="Product" items={[
            ["Features", "#features"], ["How It Works", "#how-it-works"],
            ["Citation Graph", "#showcase"], ["Pricing", "#pricing"], ["Demo", "/dashboard/demo"],
          ]} />
          <FooterCol title="Resources" items={[
            ["Documentation", "#"], ["API Reference", "#"], ["Research Notes", "#"],
            ["NLP Pipeline", "#"], ["Knowledge Graph Model", "#"],
          ]} />
          <FooterCol title="Legal" items={[
            ["Terms of Service", "/terms"], ["Privacy Policy", "/privacy"],
            ["Contact", "mailto:research@citegraph-nlp.app"], ["Academic Disclaimer", "/terms"],
          ]} />
        </div>

        <div className="mt-12 pt-6 border-t border-slate-800/70 flex flex-col md:flex-row gap-3 items-center justify-between text-xs text-slate-500">
          <div>© 2026 CiteGraph-NLP. All rights reserved.</div>
          <div>Confidence-aware research graph intelligence.</div>
        </div>
        <p className="mt-4 text-xs text-slate-500 leading-relaxed">
          CiteGraph-NLP provides exploratory research analysis. Results depend on metadata availability and should be reviewed by domain experts.
        </p>
      </div>
    </footer>
  );
}

function FooterCol({ title, items }: { title: string; items: [string, string][] }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-[0.18em] text-cyan-300">{title}</div>
      <ul className="mt-4 space-y-2.5 text-sm">
        {items.map(([label, href]) => {
          const isInternal = href.startsWith("/");
          return (
            <li key={label}>
              {isInternal ? (
                <Link to={href} onClick={() => trackEvent("footer_link_click", { label })} className="text-slate-400 hover:text-white transition">{label}</Link>
              ) : (
                <a href={href} onClick={() => trackEvent("footer_link_click", { label })} className="text-slate-400 hover:text-white transition">{label}</a>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
