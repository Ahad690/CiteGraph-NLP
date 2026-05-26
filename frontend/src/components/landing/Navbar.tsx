import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Network, Menu, X } from "lucide-react";
import { trackEvent } from "@/lib/analytics";

const links = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Graph", href: "#showcase" },
  { label: "Use Cases", href: "#use-cases" },
  // { label: "Pricing", href: "#pricing" },
  { label: "FAQ", href: "#faq" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/70 shadow-lg shadow-black/10"
          : "bg-transparent"
      }`}
    >
      <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 md:h-20 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo to-cyan shadow-lg shadow-cyan-500/20 grid place-items-center">
            <Network className="w-5 h-5 text-white" />
          </div>
          <div className="leading-tight">
            <div className="font-semibold text-white tracking-tight">CiteGraph-NLP</div>
            <div className="text-[11px] uppercase tracking-[0.14em] text-slate-400 hidden sm:block">
              Research Graph Intelligence
            </div>
          </div>
        </Link>

        <div className="hidden lg:flex items-center gap-8">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm text-slate-300 hover:text-white transition-colors"
            >
              {l.label}
            </a>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          <Link
            to="/login"
            onClick={() => trackEvent("nav_signin_click")}
            className="text-sm font-medium text-slate-300 hover:text-white px-3 py-2"
          >
            Sign In
          </Link>
          <Link
            to="/start"
            onClick={() => trackEvent("nav_cta_click")}
            className="bg-gradient-to-r from-indigo to-cyan text-white px-5 py-2.5 rounded-xl font-semibold shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 transition-shadow"
          >
            Start Analysis
          </Link>
        </div>

        <button
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle menu"
          className="md:hidden p-2 text-slate-200"
        >
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </nav>

      {open && (
        <div className="md:hidden border-t border-slate-800/70 bg-slate-950/95 backdrop-blur-xl">
          <div className="px-4 py-4 space-y-1">
            {links.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className="block px-3 py-2.5 rounded-lg text-slate-200 hover:bg-slate-800/60"
              >
                {l.label}
              </a>
            ))}
            <div className="pt-3 flex flex-col gap-2">
              <Link to="/login" className="px-3 py-2.5 rounded-lg text-slate-200 border border-slate-700">
                Sign In
              </Link>
              <Link
                to="/start"
                className="px-3 py-2.5 rounded-lg text-center bg-gradient-to-r from-indigo to-cyan text-white font-semibold"
              >
                Start Analysis
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
