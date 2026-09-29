import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getRun, saveActiveRunId } from "@/lib/api";
import type { RunPayload, RunStatusPayload } from "@/types/api";
import { deriveStatus } from "@/lib/runNormalization";

const POLL_STATUSES = new Set(["pending", "running", "processing", "started"]);

/** Used when the server does not say. Matches the previous hardcoded value. */
const DEFAULT_POLL_MS = 2000;

/**
 * The interval the server asked for, if it said.
 *
 * A run that is still resolving takes seconds to minutes, and the server knows
 * its own load better than the browser does. A hardcoded 2 seconds means a slow
 * run is polled 90 times a minute for nothing, and a client cannot tell a busy
 * server from an idle one. AnswerThis returns `retry_after_ms` with its job
 * state for the same reason.
 *
 * Anything implausible is ignored rather than obeyed: a server that returns 0
 * would produce a request loop, and a negative value is meaningless. The
 * fallback keeps the old behaviour, so an older backend that predates the field
 * polls exactly as it did before.
 */
function serverPollMs(payload: RunPayload | undefined): number {
  if (!payload || !("run_id" in payload)) return DEFAULT_POLL_MS;
  const candidate = (payload as RunStatusPayload).retry_after_ms;
  if (typeof candidate !== "number" || !Number.isFinite(candidate)) {
    return DEFAULT_POLL_MS;
  }
  if (candidate < 250 || candidate > 60_000) return DEFAULT_POLL_MS;
  return candidate;
}

export function useRun(runId: string | null | undefined) {
  const [poll, setPoll] = useState(false);

  const query = useQuery<RunPayload>({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId as string) as Promise<RunPayload>,
    enabled: !!runId,
    refetchInterval: (q) => {
      const data = q.state.data as RunPayload | undefined;
      const status = data ? deriveStatus(data) : undefined;
      return status && POLL_STATUSES.has(status) ? serverPollMs(data) : false;
    },
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (runId) saveActiveRunId(runId);
  }, [runId]);

  return query;
}
