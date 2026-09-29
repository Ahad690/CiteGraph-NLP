import type { RunResult } from "@/types/api";
import { Download, FileJson, FileSpreadsheet, FileText, Network } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { downloadExport } from "@/lib/api";
import { formatNumber, getPaperById } from "@/lib/formatters";
import {
  exportCitations,
  lowConfidenceCount,
  previewCitations,
  LOW_CONFIDENCE_THRESHOLD,
  type CitationFormat,
  type CitationStyle,
} from "@/lib/cite";

const CITATION_STYLES: { key: CitationStyle; label: string }[] = [
  { key: "apa", label: "APA 7th" },
  { key: "ieee", label: "IEEE" },
];

const FORMATS = [
  {
    key: "json" as const,
    name: "JSON Report",
    desc: "Complete structured analysis result",
    ext: "JSON",
    icon: FileJson,
  },
  {
    key: "csv" as const,
    name: "CSV Tables",
    desc: "Metadata, population extraction, rankings, and paths",
    ext: "CSV",
    icon: FileSpreadsheet,
  },
  {
    key: "graphml" as const,
    name: "GraphML",
    desc: "Graph format for Gephi, NetworkX, and graph tools",
    ext: "GRAPHML",
    icon: Network,
  },
  {
    key: "markdown" as const,
    name: "Markdown Report",
    desc: "Readable report for documentation or submission",
    ext: "MD",
    icon: FileText,
  },
];

export function ExportPage({ run }: { run: RunResult }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [style, setStyle] = useState<CitationStyle>("apa");
  const [preview, setPreview] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    previewCitations(run, style)
      .then((lines) => {
        if (!cancelled) setPreview(lines);
      })
      .catch(() => {
        if (!cancelled) setPreview([]);
      });
    return () => {
      cancelled = true;
    };
  }, [run, style]);

  const handleCitation = async (format: CitationFormat) => {
    setBusy(format);
    toast.loading(`Preparing ${format.toUpperCase()}.`, { id: format });
    try {
      const { filename, body, mime } = await exportCitations(run, style, format);
      const url = URL.createObjectURL(new Blob([body], { type: mime }));
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      const low = lowConfidenceCount(run);
      toast.success(`${format.toUpperCase()} downloaded`, {
        id: format,
        description: low
          ? `${low} citation${low === 1 ? "" : "s"} marked as low confidence.`
          : undefined,
      });
    } catch (err) {
      toast.error("Citation export failed", {
        id: format,
        description: (err as Error).message,
      });
    } finally {
      setBusy(null);
    }
  };

  const handleDownload = async (format: (typeof FORMATS)[number]["key"]) => {
    setBusy(format);
    toast.loading(`Preparing ${format.toUpperCase()}…`, { id: format });
    try {
      await downloadExport(run.run_id, format);
      toast.success(`${format.toUpperCase()} downloaded`, { id: format });
    } catch (err) {
      toast.error(`Export endpoint not available yet`, {
        id: format,
        description: (err as Error).message,
      });
    } finally {
      setBusy(null);
    }
  };

  const seed = getPaperById(run.papers, run.seed_paper_id);
  const top = run.ranked_foundational_papers[0];
  const topPaper = top ? getPaperById(run.papers, top.paper_id) : null;
  const resolved = run.population_resolutions.filter((r) => r.status === "resolved").length;

  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 gap-4">
        {FORMATS.map((f) => {
          const Icon = f.icon;
          return (
            <div
              key={f.key}
              className="glass rounded-2xl p-5 hover:border-border-strong transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="h-11 w-11 rounded-xl gradient-brand-soft border border-border-strong grid place-items-center">
                  <Icon className="h-5 w-5 text-cyan" />
                </div>
                <span className="px-2 py-0.5 rounded-md bg-surface-strong border border-border text-[10px] font-mono font-semibold text-text-muted">
                  {f.ext}
                </span>
              </div>
              <div className="mt-4">
                <div className="font-semibold text-text-primary">{f.name}</div>
                <div className="text-xs text-text-muted mt-1">{f.desc}</div>
              </div>
              <button
                onClick={() => handleDownload(f.key)}
                disabled={busy === f.key}
                className="mt-4 w-full h-10 rounded-xl gradient-brand text-white text-sm font-semibold flex items-center justify-center gap-2 hover:opacity-95 disabled:opacity-60"
              >
                <Download className="h-4 w-4" />
                {busy === f.key ? "Preparing…" : "Download"}
              </button>
            </div>
          );
        })}
      </div>

      <div className="glass rounded-2xl p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
          <h3 className="text-base font-semibold text-text-primary">Citations</h3>
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-border overflow-hidden">
              {CITATION_STYLES.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setStyle(s.key)}
                  className={`px-3 py-1 text-xs font-semibold transition-colors ${
                    style === s.key
                      ? "bg-signal text-white"
                      : "bg-surface-strong text-text-muted hover:text-text-primary"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => handleCitation("bibtex")}
              disabled={busy === "bibtex"}
              className="h-8 px-3 rounded-lg gradient-brand text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-60"
            >
              <FileText className="h-3.5 w-3.5" />
              {busy === "bibtex" ? "Preparing…" : "BibTeX"}
            </button>
            <button
              onClick={() => handleCitation("ris")}
              disabled={busy === "ris"}
              className="h-8 px-3 rounded-lg border border-border-strong text-xs font-semibold text-text-primary flex items-center gap-1.5 disabled:opacity-60"
            >
              <FileText className="h-3.5 w-3.5" />
              {busy === "ris" ? "Preparing…" : "RIS"}
            </button>
          </div>
        </div>
        <p className="text-xs text-text-muted mb-3">
          Styled with CSL. Papers linked to the seed below{" "}
          {Math.round(LOW_CONFIDENCE_THRESHOLD * 100)}% confidence are marked in the file.
        </p>
        {preview.length === 0 ? (
          <div className="text-xs text-text-muted">No citations to preview.</div>
        ) : (
          <ol className="space-y-2 max-h-64 overflow-y-auto">
            {preview.slice(0, 12).map((line, i) => (
              <li key={i} className="text-xs text-text-secondary leading-relaxed">
                {line}
              </li>
            ))}
            {preview.length > 12 && (
              <li className="text-xs text-text-muted">
                + {preview.length - 12} more in the downloaded file
              </li>
            )}
          </ol>
        )}
      </div>

      <div className="glass rounded-2xl p-5 lg:p-6">
        <h3 className="text-base font-semibold text-text-primary mb-4">Report preview</h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="rounded-xl bg-surface-strong/40 border border-border p-4">
            <div className="label-tiny mb-2">Seed paper</div>
            <div className="text-sm font-semibold text-text-primary">{seed?.title || "—"}</div>
            <div className="text-xs text-text-muted mt-1">
              {seed?.year} · {seed?.journal}
            </div>
          </div>
          <div className="rounded-xl bg-surface-strong/40 border border-border p-4">
            <div className="label-tiny mb-2">Top probable foundational paper</div>
            <div className="text-sm font-semibold text-text-primary">{topPaper?.title || "—"}</div>
            <div className="text-xs text-text-muted mt-1">
              Score {top ? `${Math.round(top.score * 100)}%` : "—"}
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <Mini label="Papers" value={formatNumber(run.papers.length)} />
          <Mini label="Edges" value={formatNumber(run.citation_edges.length)} />
          <Mini label="Resolved population" value={formatNumber(resolved)} />
          <Mini
            label="Dataset evidence"
            value={formatNumber(run.technical_evidence.filter((item) => item.value != null).length)}
          />
          <Mini label="Warnings" value={formatNumber(run.warnings.length)} />
        </div>
        <div className="mt-5 text-xs text-text-muted px-3 py-2 rounded-lg bg-surface-strong/40 border border-border">
          <span className="font-semibold text-text-secondary">Limitations: </span>
          Citation coverage depends on available public metadata. Clinical populations and technical
          dataset counts are separate; technical counts do not weight rankings.
        </div>
      </div>
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-surface-strong/40 border border-border px-3 py-2.5">
      <div className="label-tiny">{label}</div>
      <div className="text-lg font-bold text-text-primary mt-0.5">{value}</div>
    </div>
  );
}
