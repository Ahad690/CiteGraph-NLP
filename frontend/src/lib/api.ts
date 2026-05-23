import type { ExportFormat, RunResult } from "@/types/api";
import { mockRun } from "./mock";

/** Resolve the API base URL with environment-aware validation.
 *  In production we require a non-empty HTTPS URL — silently falling back to
 *  http://localhost would result in mixed-content failures and confusing
 *  "Failed to fetch" errors for end users. */
function resolveApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE as string | undefined;
  const isProd = import.meta.env.PROD === true;

  if (fromEnv && fromEnv.trim()) {
    const trimmed = fromEnv.trim().replace(/\/+$/, "");
    if (isProd && !trimmed.startsWith("https://")) {
      // Browsers block http→from https pages anyway; warn loudly so this isn't
      // a silent prod misconfiguration. We don't throw because some self-hosted
      // deployments intentionally use http on a private network.
      // eslint-disable-next-line no-console
      console.error(
        `[api] VITE_API_BASE=${trimmed} is not HTTPS in a production build; ` +
        `requests will be blocked by Mixed Content in browsers served over HTTPS.`,
      );
    }
    return trimmed;
  }

  if (isProd) {
    // eslint-disable-next-line no-console
    console.error(
      "[api] VITE_API_BASE is not set in this production build. " +
      "API calls will fall back to http://localhost:8000 and fail in browsers.",
    );
  }
  return "http://localhost:8000";
}

export const API_BASE = resolveApiBase();
const ACTIVE_RUN_KEY = "active_run_id";

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
  }
}

export interface StartRunParams {
  query_type: "doi" | "pmid" | "pmcid" | "title" | "url";
  value: string;
  backward_depth?: number;
  forward_depth?: number;
  max_total_papers?: number;
  pdf_path?: string | null;
}

export async function startRun(params: StartRunParams): Promise<{ run_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = typeof errorBody.detail === "string" 
      ? errorBody.detail 
      : Array.isArray(errorBody.detail)
      ? errorBody.detail.map((d: any) => d.msg).join(", ")
      : `Start analysis failed (${res.status})`;
    throw new ApiError(message, res.status);
  }
  return (await res.json()) as { run_id: string; status: string };
}

export async function getRun(runId: string): Promise<RunResult> {
  // Allow demo run to work without a backend
  if (runId === mockRun.run_id) return { ...mockRun };

  const res = await fetch(`${API_BASE}/api/runs/${encodeURIComponent(runId)}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    if (res.status === 404) throw new ApiError("Run not found", 404);
    throw new ApiError(`Request failed (${res.status})`, res.status);
  }
  return (await res.json()) as RunResult;
}

export async function downloadExport(runId: string, format: ExportFormat): Promise<void> {
  const res = await fetch(`${API_BASE}/api/runs/${encodeURIComponent(runId)}/export/${format}`);
  if (!res.ok) throw new ApiError(`Export failed (${res.status})`, res.status);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const ext = format === "markdown" ? "md" : format === "graphml" ? "graphml" : format;
  a.download = `citegraph-${runId}.${ext}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function saveActiveRunId(runId: string) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(ACTIVE_RUN_KEY, runId);
  } catch {
    /* ignore */
  }
}

export function getActiveRunId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(ACTIVE_RUN_KEY);
  } catch {
    return null;
  }
}

export function getRunIdFromRouteOrStorage(routeId?: string, queryId?: string | null): string | null {
  return routeId || queryId || getActiveRunId();
}

export function isBackendDemo(run: RunResult): boolean {
  return run.run_id === mockRun.run_id || (run as unknown as { __demo?: boolean }).__demo === true;
}
