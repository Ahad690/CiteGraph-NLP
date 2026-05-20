import { AlertTriangle } from "lucide-react";
import { Link } from "@tanstack/react-router";

interface Props {
  title?: string;
  message?: string;
  runId?: string | null;
  onRetry?: () => void;
}

export function ErrorState({ title = "Something went wrong", message, runId, onRetry }: Props) {
  return (
    <div className="glass rounded-3xl p-10 text-center max-w-2xl mx-auto">
      <div className="mx-auto h-14 w-14 rounded-2xl bg-rose/10 border border-rose/30 grid place-items-center mb-4">
        <AlertTriangle className="h-6 w-6 text-rose" />
      </div>
      <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
      {message && <p className="text-sm text-text-muted mt-2">{message}</p>}
      {runId && <code className="block mt-3 text-xs text-text-muted font-mono">{runId}</code>}
      <div className="mt-6 flex justify-center gap-3">
        {onRetry && (
          <button onClick={onRetry} className="px-5 h-10 rounded-xl bg-surface-strong border border-border hover:bg-surface-hover text-sm font-semibold text-text-primary">
            Retry
          </button>
        )}
        <Link to="/" className="px-5 h-10 inline-flex items-center rounded-xl gradient-brand text-white text-sm font-semibold">Back to start</Link>
      </div>
    </div>
  );
}
