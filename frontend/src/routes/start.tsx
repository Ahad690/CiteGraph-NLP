import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { getActiveRunId, startRun } from "@/lib/api";
import { Sparkles, ArrowRight, Loader2, Sliders, FileText, Globe, Key, AlertCircle } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/start")({
  component: Index,
});

function Index() {
  const navigate = useNavigate();
  const [runId, setRunId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  // Form states
  const [queryType, setQueryType] = useState<"doi" | "pmid" | "pmcid" | "title" | "url">("doi");
  const [value, setValue] = useState("");
  const [backwardDepth, setBackwardDepth] = useState(2);
  const [forwardDepth, setForwardDepth] = useState(1);
  const [maxTotalPapers, setMaxTotalPapers] = useState(100);
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setRunId(getActiveRunId());
    setReady(true);
  }, []);

  if (!ready) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) {
      setError("Please enter a search value");
      return;
    }
    setError(null);
    setLoading(true);
    
    try {
      const response = await startRun({
        query_type: queryType,
        value: value.trim(),
        backward_depth: backwardDepth,
        forward_depth: forwardDepth,
        max_total_papers: maxTotalPapers,
      });
      
      toast.success("Citation lineage analysis started successfully!");
      // Redirect to the dashboard for this run
      navigate({
        to: "/dashboard/$runId",
        params: { runId: response.run_id },
      });
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An error occurred starting the analysis");
      toast.error(err.message || "Failed to start analysis");
    } finally {
      setLoading(false);
    }
  };

  const getPlaceholder = () => {
    switch (queryType) {
      case "doi":
        return "e.g. 10.1016/j.cell.2023.01.001";
      case "pmid":
        return "e.g. 34567890 (NCBI PubMed ID)";
      case "pmcid":
        return "e.g. PMC8012345 (PubMed Central ID)";
      case "title":
        return "e.g. Attention Is All You Need";
      case "url":
        return "e.g. https://pubmed.ncbi.nlm.nih.gov/34567890/";
    }
  };

  const getHelpText = () => {
    switch (queryType) {
      case "doi":
        return "Digital Object Identifier starting with 10.";
      case "pmid":
        return "PubMed identifier (numeric)";
      case "pmcid":
        return "PubMed Central identifier (starts with PMC)";
      case "title":
        return "Exact paper title or major keywords (min 5 chars)";
      case "url":
        return "Link to NCBI PubMed, PMC, or DOI redirector page";
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 md:py-20 relative overflow-hidden bg-background">
      {/* Dynamic blurred glow background effects */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-[350px] h-[350px] rounded-full bg-indigo/10 blur-[80px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-[300px] h-[300px] rounded-full bg-cyan/8 blur-[80px] pointer-events-none" />

      <div className="w-full max-w-2xl relative z-10 animate-fade-in">
        {/* Header Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex h-12 w-12 rounded-2xl gradient-brand items-center justify-center glow-indigo mb-4">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-text-primary">
            CiteGraph<span className="text-cyan font-medium">-NLP</span>
          </h1>
          <p className="text-sm text-text-muted mt-2 max-w-md mx-auto leading-relaxed">
            Confidence-aware citation lineage and study-scale research analysis. Map the graph of your research.
          </p>
        </div>

        {/* Main interactive form card */}
        <div className="glass rounded-3xl p-6 md:p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Query Type Tabs */}
            <div>
              <label className="block text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
                Select Input Identifier Type
              </label>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 bg-surface-strong/60 p-1.5 rounded-2xl border border-border/80">
                {(["doi", "pmid", "pmcid", "title", "url"] as const).map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => {
                      setQueryType(type);
                      setError(null);
                    }}
                    className={`py-2 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all duration-150 cursor-pointer ${
                      queryType === type
                        ? "bg-surface-hover text-text-primary border border-border/60 shadow-[0_0_12px_rgba(79,70,229,0.2)]"
                        : "text-text-muted hover:text-text-secondary"
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            {/* Main input field */}
            <div className="space-y-2">
              <label htmlFor="value" className="block text-xs font-semibold text-text-muted uppercase tracking-wider">
                Seed Identifier Value
              </label>
              <div className="relative">
                <input
                  id="value"
                  type="text"
                  value={value}
                  onChange={(e) => {
                    setValue(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder={getPlaceholder()}
                  disabled={loading}
                  className={`w-full px-4 py-3.5 pl-11 rounded-2xl bg-surface-strong/60 border text-sm text-text-primary placeholder:text-text-disabled outline-none transition-all duration-200 ${
                    error ? "border-rose focus:ring-1 focus:ring-rose/40" : "border-border/80 focus:border-border-strong focus:ring-1 focus:ring-indigo/40"
                  }`}
                />
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-text-muted">
                  {queryType === "url" ? <Globe className="h-4.5 w-4.5" /> : queryType === "title" ? <FileText className="h-4.5 w-4.5" /> : <Key className="h-4.5 w-4.5" />}
                </div>
              </div>
              <p className="text-[11px] text-text-muted pl-1">{getHelpText()}</p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="flex items-start gap-2 text-xs text-rose bg-rose/10 border border-rose/20 rounded-xl p-3">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Advanced toggle */}
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 text-xs font-semibold text-text-secondary hover:text-text-primary transition-colors focus:outline-none cursor-pointer"
              >
                <Sliders className={`h-4 w-4 transition-transform duration-250 ${showAdvanced ? "rotate-90 text-cyan" : "text-text-muted"}`} />
                <span>Configure Graph Parameters & Depth</span>
              </button>

              {/* Advanced Panel */}
              {showAdvanced && (
                <div className="mt-4 p-5 rounded-2xl bg-surface-strong/40 border border-border/80 space-y-5 transition-all">
                  {/* Backward Depth */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="font-semibold text-text-secondary">Backward Lineage Depth (References)</span>
                      <span className="font-mono text-cyan">{backwardDepth} levels</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="3"
                      value={backwardDepth}
                      onChange={(e) => setBackwardDepth(parseInt(e.target.value))}
                      className="w-full accent-indigo cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-text-muted">
                      <span>0 (Seed only)</span>
                      <span>1 (Direct references)</span>
                      <span>2 (Recommend)</span>
                      <span>3 (Deep search)</span>
                    </div>
                  </div>

                  {/* Forward Depth */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="font-semibold text-text-secondary">Forward Lineage Depth (Citations)</span>
                      <span className="font-mono text-cyan">{forwardDepth} levels</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      value={forwardDepth}
                      onChange={(e) => setForwardDepth(parseInt(e.target.value))}
                      className="w-full accent-indigo cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-text-muted">
                      <span>0 (No citations)</span>
                      <span>1 (Direct citations)</span>
                      <span>2 (Secondary citations)</span>
                    </div>
                  </div>

                  {/* Max Papers Limit */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="font-semibold text-text-secondary">Maximum Graph Size (Total Papers)</span>
                      <span className="font-mono text-cyan">{maxTotalPapers} papers</span>
                    </div>
                    <input
                      type="range"
                      min="10"
                      max="200"
                      step="10"
                      value={maxTotalPapers}
                      onChange={(e) => setMaxTotalPapers(parseInt(e.target.value))}
                      className="w-full accent-indigo cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-text-muted">
                      <span>10 papers</span>
                      <span>100 (Default)</span>
                      <span>200 papers</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Action button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full inline-flex items-center justify-center gap-2 h-12 rounded-2xl gradient-brand text-white text-sm font-semibold hover:opacity-95 shadow-lg shadow-indigo/25 disabled:opacity-50 transition-all cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Initializing Citation Pipeline...
                </>
              ) : (
                <>
                  Analyze Citation Lineage
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick shortcuts / demo / active run access */}
          <div className="mt-6 pt-5 border-t border-border/60 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            {runId ? (
              <Link
                to="/dashboard/$runId"
                params={{ runId }}
                className="text-indigo hover:text-cyan font-semibold flex items-center gap-1 transition-colors"
              >
                Return to active run ({runId.slice(0, 8)})
                <ArrowRight className="h-3 w-3" />
              </Link>
            ) : (
              <span className="text-text-muted">No analysis currently active</span>
            )}
            <Link
              to="/dashboard/$runId"
              params={{ runId: "demo_run_001" }}
              className="text-text-secondary hover:text-text-primary font-semibold flex items-center gap-1 transition-colors bg-surface-hover/30 hover:bg-surface-hover/70 px-3 py-1.5 rounded-lg border border-border"
            >
              Explore Demo Workspace
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
