import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getRun, saveActiveRunId } from "@/lib/api";
import type { RunResult } from "@/types/api";

const POLL_STATUSES = new Set(["pending", "running", "processing", "started"]);

export function useRun(runId: string | null | undefined) {
  const [poll, setPoll] = useState(false);

  const query = useQuery<RunResult>({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId as string),
    enabled: !!runId,
    refetchInterval: poll ? 2000 : false,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (runId) saveActiveRunId(runId);
  }, [runId]);

  useEffect(() => {
    const status = query.data?.status;
    setPoll(!!status && POLL_STATUSES.has(status));
  }, [query.data?.status]);

  return query;
}
