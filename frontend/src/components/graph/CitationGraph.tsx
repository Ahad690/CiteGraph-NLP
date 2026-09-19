import { useMemo, useRef, useState, useEffect, useLayoutEffect } from "react";
import type { RunResult, CitationEdge, Paper } from "@/types/api";
import { getPopulationForPaper, getConfidenceColor, truncateTitle } from "@/lib/formatters";

interface Node {
  id: string;
  paper: Paper;
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  isSeed: boolean;
  isFoundational: boolean;
}

interface Props {
  run: RunResult;
  filters: GraphFilters;
  onSelectPaper: (paper: Paper) => void;
  onSelectEdge: (edge: CitationEdge) => void;
}

export interface GraphFilters {
  minConfidence: number;
  minWeight: number;
  yearRange: [number, number];
  seedConnectedOnly: boolean;
  hideMissing: boolean;
  highConfOnly: boolean;
  highlightFoundational: boolean;
}

export function CitationGraph({ run, filters, onSelectPaper, onSelectEdge }: Props) {
  const technicalSeed = run.papers.find((paper) => paper.paper_id === run.seed_paper_id)?.research_domain === "computer_science";
  const structuralSeed = technicalSeed || run.papers.find((paper) => paper.paper_id === run.seed_paper_id)?.research_domain === "nonclinical";
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [size, setSize] = useState({ w: 800, h: 560 });
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const transformRef = useRef(transform);
  transformRef.current = transform;
  const [hoverNode, setHoverNode] = useState<string | null>(null);
  const [hoverEdge, setHoverEdge] = useState<string | null>(null);
  const [dragging, setDragging] = useState<{ id: string; offX: number; offY: number } | null>(null);
  const [panning, setPanning] = useState<{ sx: number; sy: number } | null>(null);

  // Read the true content-box size synchronously before first paint
  useLayoutEffect(() => {
    if (containerRef.current) {
      setSize({ w: containerRef.current.clientWidth, h: containerRef.current.clientHeight });
    }
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(() => {
      // clientWidth/clientHeight exclude borders — matches the area the SVG actually fills
      setSize({ w: containerRef.current!.clientWidth, h: containerRef.current!.clientHeight });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const seedConnectedSet = useMemo(() => {
    const set = new Set<string>([run.seed_paper_id]);
    let changed = true;
    while (changed) {
      changed = false;
      for (const e of run.citation_edges) {
        if (set.has(e.source_paper_id) && !set.has(e.target_paper_id)) { set.add(e.target_paper_id); changed = true; }
        if (set.has(e.target_paper_id) && !set.has(e.source_paper_id)) { set.add(e.source_paper_id); changed = true; }
      }
    }
    return set;
  }, [run]);

  const filteredPapers = useMemo(() => {
    return run.papers.filter((p) => {
      if (filters.seedConnectedOnly && !seedConnectedSet.has(p.paper_id)) return false;
      if (p.year != null && (p.year < filters.yearRange[0] || p.year > filters.yearRange[1])) return false;
      const pop = getPopulationForPaper(run, p.paper_id);
      const technical = run.technical_evidence.find((item) => item.paper_id === p.paper_id);
      if (filters.hideMissing && (technicalSeed ? technical?.value == null : pop?.n_eff == null)) return false;
      if (filters.highConfOnly && (p.metadata_confidence ?? 0) < 0.75) return false;
      return true;
    });
  }, [run, filters, seedConnectedSet, technicalSeed]);

  const filteredEdges = useMemo(() => {
    const ids = new Set(filteredPapers.map((p) => p.paper_id));
    return run.citation_edges.filter((e) =>
      ids.has(e.source_paper_id) && ids.has(e.target_paper_id) &&
      (e.confidence ?? 0) >= filters.minConfidence &&
      (e.final_weight ?? 0) >= filters.minWeight
    );
  }, [run, filteredPapers, filters.minConfidence, filters.minWeight]);

  // Initial layout (deterministic radial + light force) — runs whenever filtered papers set changes
  const [nodes, setNodes] = useState<Record<string, Node>>({});
  useEffect(() => {
    const cx = size.w / 2;
    const cy = size.h / 2;
    const seedId = run.seed_paper_id;
    const others = filteredPapers.filter((p) => p.paper_id !== seedId);
    const radius = Math.min(size.w, size.h) * 0.35;
    const next: Record<string, Node> = {};

    filteredPapers.forEach((p, i) => {
      const isSeed = p.paper_id === seedId;
      const pop = getPopulationForPaper(run, p.paper_id);
      const technical = run.technical_evidence.find((item) => item.paper_id === p.paper_id);
      const sizeVal = !structuralSeed && pop?.n_eff
        ? Math.max(14, Math.min(38, 12 + Math.log10(Math.max(10, pop.n_eff)) * 4))
        : 16;
      const color = isSeed
        ? "url(#seedGradient)"
        : structuralSeed && !technicalSeed ? "#64748b" : getConfidenceColor(technicalSeed ? technical?.value != null ? technical.confidence : undefined : pop?.n_eff != null ? pop.confidence : undefined);
      let x: number, y: number;
      if (isSeed) {
        x = cx; y = cy;
      } else {
        const idx = others.findIndex((o) => o.paper_id === p.paper_id);
        const angle = (idx / Math.max(1, others.length)) * Math.PI * 2;
        x = cx + Math.cos(angle) * radius;
        y = cy + Math.sin(angle) * radius;
      }
      const isFoundational = run.ranked_foundational_papers.some((r) => r.paper_id === p.paper_id);
      next[p.paper_id] = {
        id: p.paper_id, paper: p, x, y, vx: 0, vy: 0,
        size: sizeVal, color, isSeed, isFoundational,
      };
    });
    setNodes(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filteredPapers.map((p) => p.paper_id).join(","), size.w, size.h]);

  const screen = (px: number, py: number) => ({
    x: px * transform.k + transform.x,
    y: py * transform.k + transform.y,
  });

  const onPointerDownNode = (e: React.PointerEvent, n: Node) => {
    e.stopPropagation();
    (e.target as Element).setPointerCapture?.(e.pointerId);
    const sp = screen(n.x, n.y);
    setDragging({ id: n.id, offX: e.clientX - sp.x, offY: e.clientY - sp.y });
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (dragging) {
      const wx = (e.clientX - dragging.offX - transform.x) / transform.k;
      const wy = (e.clientY - dragging.offY - transform.y) / transform.k;
      setNodes((prev) => ({ ...prev, [dragging.id]: { ...prev[dragging.id], x: wx, y: wy } }));
    } else if (panning) {
      setTransform((t) => ({ ...t, x: t.x + (e.clientX - panning.sx), y: t.y + (e.clientY - panning.sy) }));
      setPanning({ sx: e.clientX, sy: e.clientY });
    }
  };

  const onPointerUp = () => { setDragging(null); setPanning(null); };

  // Attach wheel listener with { passive: false } so preventDefault works
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      const t = transformRef.current;
      const delta = -e.deltaY * 0.0015;
      const newK = Math.max(0.3, Math.min(3, t.k * (1 + delta)));
      const rect = containerRef.current!.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const wx = (mx - t.x) / t.k;
      const wy = (my - t.y) / t.k;
      setTransform({ k: newK, x: mx - wx * newK, y: my - wy * newK });
    };
    svg.addEventListener("wheel", handler, { passive: false });
    return () => svg.removeEventListener("wheel", handler);
  }, []);

  const fit = () => setTransform({ x: 0, y: 0, k: 1 });
  const reset = () => {
    setTransform({ x: 0, y: 0, k: 1 });
    setNodes({});
    // trigger relayout
    setSize((s) => ({ ...s }));
  };

  return (
    <div ref={containerRef} className="relative w-full h-full rounded-2xl overflow-hidden bg-[radial-gradient(circle_at_30%_20%,rgba(79,70,229,0.08),transparent_60%),radial-gradient(circle_at_80%_80%,rgba(6,182,212,0.08),transparent_60%)] border border-border">
      <svg
        ref={svgRef}
        width={size.w}
        height={size.h}
        onPointerDown={(e) => setPanning({ sx: e.clientX, sy: e.clientY })}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        style={{ display: "block", cursor: panning ? "grabbing" : "grab", touchAction: "none" }}
      >
        <defs>
          <radialGradient id="seedGradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#a5b4fc" />
            <stop offset="60%" stopColor="#4f46e5" />
            <stop offset="100%" stopColor="#06b6d4" />
          </radialGradient>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#06b6d4" opacity="0.7" />
          </marker>
        </defs>

        <g transform={`translate(${transform.x},${transform.y}) scale(${transform.k})`}>
          {filteredEdges.map((e) => {
            const s = nodes[e.source_paper_id];
            const t = nodes[e.target_paper_id];
            if (!s || !t) return null;
            const w = Math.max(0.6, (e.final_weight ?? 0.5) * 4);
            const op = Math.max(0.25, (e.confidence ?? 0.5));
            const isHover = hoverEdge === e.edge_id;
            return (
              <line
                key={e.edge_id}
                x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                stroke={isHover ? "#22d3ee" : "#06b6d4"}
                strokeWidth={isHover ? w + 1 : w}
                strokeOpacity={isHover ? 0.95 : op}
                markerEnd="url(#arrow)"
                style={{ cursor: "pointer", filter: isHover ? "drop-shadow(0 0 6px rgba(34,211,238,0.6))" : undefined }}
                onPointerEnter={() => setHoverEdge(e.edge_id)}
                onPointerLeave={() => setHoverEdge(null)}
                onClick={(ev) => { ev.stopPropagation(); onSelectEdge(e); }}
              />
            );
          })}

          {Object.values(nodes).map((n) => {
            const isHover = hoverNode === n.id;
            return (
              <g key={n.id} transform={`translate(${n.x},${n.y})`} style={{ cursor: "pointer" }}
                 onPointerDown={(e) => onPointerDownNode(e, n)}
                 onPointerEnter={() => setHoverNode(n.id)}
                 onPointerLeave={() => setHoverNode(null)}
                 onClick={(e) => { e.stopPropagation(); onSelectPaper(n.paper); }}>
                {n.isFoundational && filters.highlightFoundational && (
                  <circle r={n.size + 6} fill="none" stroke="#8b5cf6" strokeWidth={2} strokeOpacity={0.6} />
                )}
                {n.isSeed && (
                  <circle r={n.size + 10} fill="none" stroke="#22d3ee" strokeWidth={1.5} strokeOpacity={0.5}>
                    <animate attributeName="r" from={n.size + 6} to={n.size + 14} dur="2s" repeatCount="indefinite" />
                    <animate attributeName="stroke-opacity" from="0.6" to="0" dur="2s" repeatCount="indefinite" />
                  </circle>
                )}
                <circle r={n.size} fill={n.color} filter={n.isSeed || isHover ? "url(#glow)" : undefined} stroke="rgba(255,255,255,0.15)" strokeWidth={1.5} />
                <text
                  y={n.size + 14}
                  textAnchor="middle"
                  fontSize={11}
                  fill="#cbd5e1"
                  pointerEvents="none"
                  style={{ fontWeight: n.isSeed ? 700 : 500 }}
                >
                  {truncateTitle(n.paper.title, 28)}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {filteredPapers.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-text-secondary">
          No papers match these filters. Adjust the year range or reset the filters.
        </div>
      )}

      {/* Tooltip */}
      {hoverNode && nodes[hoverNode] && (() => {
        const n = nodes[hoverNode];
        const sp = screen(n.x, n.y);
        const pop = getPopulationForPaper(run, n.id);
        const technical = run.technical_evidence.find((item) => item.paper_id === n.id);
        return (
          <div className="pointer-events-none absolute glass-strong rounded-xl p-3 max-w-[280px] text-xs shadow-2xl"
               style={{ left: Math.min(size.w - 290, sp.x + 16), top: Math.max(8, sp.y - 80) }}>
            <div className="font-semibold text-text-primary leading-snug">{n.paper.title}</div>
            <div className="text-text-muted mt-1">{n.paper.year} · {n.paper.journal || "—"}</div>
            <div className="mt-2 grid grid-cols-2 gap-1 text-[11px]">
              <div className="text-text-muted">{technicalSeed ? "Dataset examples" : "Clinical N_eff"}</div>
              <div className="text-text-secondary font-mono">{structuralSeed && !technicalSeed ? "N/A" : technicalSeed ? technical?.value?.toLocaleString() ?? "—" : pop?.n_eff?.toLocaleString() ?? "—"}</div>
              <div className="text-text-muted">Confidence</div>
              <div className="text-text-secondary font-mono">{structuralSeed && !technicalSeed ? "N/A" : (technicalSeed ? technical?.confidence : pop?.confidence) != null ? `${Math.round((technicalSeed ? technical?.confidence : pop?.confidence)! * 100)}%` : "—"}</div>
            </div>
          </div>
        );
      })()}

      {/* Controls */}
      <div className="absolute top-3 right-3 flex gap-2">
        <button onClick={fit} className="h-9 px-3 rounded-lg glass border border-border text-xs font-semibold text-text-secondary hover:text-text-primary">Fit</button>
        <button onClick={reset} className="h-9 px-3 rounded-lg glass border border-border text-xs font-semibold text-text-secondary hover:text-text-primary">Reset</button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 glass rounded-xl p-3 text-[11px] space-y-1.5 max-w-[220px]">
        <div className="label-tiny mb-1">Legend</div>
        <LegendRow color="url(#seedGradient)" label="Seed paper (glow)" gradient />
        <LegendRow color="#10b981" label="High confidence" />
        <LegendRow color="#f59e0b" label="Medium confidence" />
        <LegendRow color="#f43f5e" label="Low confidence" />
        <LegendRow color="#64748b" label={technicalSeed ? "No dataset evidence" : structuralSeed ? "No comparable evidence metric" : "Missing population"} />
        <div className="text-text-muted pt-1">{structuralSeed ? "Node size fixed · Edge thickness = citation weight" : "Node size = N_eff · Edge thickness = weight"}</div>
        <div className="flex items-center gap-2 pt-1">
          <span className="h-3 w-3 rounded-full border-2 border-purple bg-transparent" />
          <span className="text-text-muted">Foundational candidate</span>
        </div>
      </div>
    </div>
  );
}

function LegendRow({ color, label, gradient }: { color: string; label: string; gradient?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-3 w-3 rounded-full" style={{ background: gradient ? "linear-gradient(135deg, #4f46e5, #06b6d4)" : color }} />
      <span className="text-text-secondary">{label}</span>
    </div>
  );
}
