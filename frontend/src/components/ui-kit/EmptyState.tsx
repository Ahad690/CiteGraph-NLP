import { Link } from "@tanstack/react-router";
import { Inbox, ArrowRight } from "lucide-react";
import type { ReactNode } from "react";

interface Props {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: { label: string; to: string };
}

export function EmptyState({ title, description, icon, action }: Props) {
  return (
    <div className="glass rounded-3xl p-12 text-center">
      <div className="mx-auto h-14 w-14 rounded-2xl gradient-brand-soft border border-border-strong grid place-items-center mb-4">
        {icon || <Inbox className="h-6 w-6 text-cyan" />}
      </div>
      <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
      {description && <p className="text-sm text-text-muted mt-2 max-w-md mx-auto">{description}</p>}
      {action && (
        <Link
          to={action.to}
          className="inline-flex items-center gap-2 mt-6 px-5 h-10 rounded-xl gradient-brand text-white text-sm font-semibold hover:opacity-95"
        >
          {action.label}
          <ArrowRight className="h-4 w-4" />
        </Link>
      )}
    </div>
  );
}
