import { useEffect, useState } from "react";
import { Quote, ChevronLeft, ChevronRight } from "lucide-react";
import { SectionHeader } from "./SectionHeader";

const items = [
  { name: "Ayesha Khan", role: "MS Artificial Intelligence Student", inst: "NUST", flag: "🇵🇰", q: "CiteGraph-NLP made our NLP project feel like a real research tool. The confidence-aware extraction gave us a much stronger proposal than a simple citation counter." },
  { name: "Daniel Reed", role: "Biomedical Research Assistant", inst: "University of Manchester", flag: "🇬🇧", q: "The graph view helped me understand which earlier clinical studies were actually connected to the paper I was reviewing." },
  { name: "Priya Menon", role: "PhD Candidate, Public Health", inst: "AIIMS", flag: "🇮🇳", q: "Population-size extraction with confidence labels is exactly what literature review tools usually miss." },
  { name: "Omar Al-Farsi", role: "Data Science Researcher", inst: "Qatar University", flag: "🇶🇦", q: "Exporting the citation graph as structured data made it easy to continue analysis in NetworkX and Gephi." },
  { name: "Emily Carter", role: "Systematic Review Author", inst: "University of Toronto", flag: "🇨🇦", q: "I liked that it did not overclaim certainty. Ambiguous extraction results were clearly labeled instead of hidden." },
  { name: "Hamza Malik", role: "BS Computer Science Student", inst: "FAST", flag: "🇵🇰", q: "The idea of separating papers, studies, and population observations made our knowledge graph much more defensible." },
];

export function Testimonials() {
  const [idx, setIdx] = useState(0);
  const pages = Math.ceil(items.length / 3);
  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % pages), 6000);
    return () => clearInterval(t);
  }, [pages]);

  return (
    <section className="relative py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Testimonials"
          title={<>Built for researchers who need <span className="text-gradient-brand">more than search results.</span></>}
          subtitle="CiteGraph-NLP helps turn literature exploration into a structured, explainable workflow."
        />

        {/* desktop */}
        <div className="mt-14 hidden md:block overflow-hidden">
          <div className="flex transition-transform duration-700" style={{ transform: `translateX(-${idx * 100}%)` }}>
            {Array.from({ length: pages }).map((_, p) => (
              <div key={p} className="min-w-full grid grid-cols-3 gap-5">
                {items.slice(p * 3, p * 3 + 3).map((t) => (
                  <Card key={t.name} t={t} />
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* mobile */}
        <div className="mt-14 md:hidden">
          <Card t={items[idx % items.length]} />
        </div>

        <div className="mt-8 flex items-center justify-center gap-3">
          <button onClick={() => setIdx((i) => (i - 1 + pages) % pages)} className="p-2 rounded-full border border-slate-700 text-slate-300 hover:border-cyan-400/40">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <div className="flex gap-1.5">
            {Array.from({ length: pages }).map((_, i) => (
              <button key={i} onClick={() => setIdx(i)} className={`w-2 h-2 rounded-full transition ${i === idx ? "bg-cyan-400 w-6" : "bg-slate-700"}`} />
            ))}
          </div>
          <button onClick={() => setIdx((i) => (i + 1) % pages)} className="p-2 rounded-full border border-slate-700 text-slate-300 hover:border-cyan-400/40">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </section>
  );
}

function Card({ t }: { t: typeof items[0] }) {
  const initials = t.name.split(" ").map((n) => n[0]).slice(0, 2).join("");
  return (
    <div className="rounded-2xl border border-slate-700/40 bg-slate-900/60 backdrop-blur-xl p-6 hover:border-cyan-400/30 transition h-full flex flex-col">
      <Quote className="w-6 h-6 text-cyan-400/60" />
      <p className="mt-4 text-slate-200 leading-relaxed flex-1">{t.q}</p>
      <div className="mt-6 flex items-center gap-3 pt-4 border-t border-slate-800">
        <div className="w-11 h-11 rounded-full bg-gradient-to-br from-indigo to-cyan grid place-items-center text-white font-semibold text-sm">
          {initials}
        </div>
        <div className="text-sm">
          <div className="font-semibold text-white">{t.name} <span className="ml-1">{t.flag}</span></div>
          <div className="text-slate-400">{t.role} · {t.inst}</div>
        </div>
      </div>
    </div>
  );
}
