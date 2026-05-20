import { createFileRoute, Link, Outlet } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";

export const Route = createFileRoute("/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — CiteGraph-NLP" }] }),
  component: DashboardLayout,
});

function DashboardLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground grid place-items-center px-4">
      <div className="max-w-md text-center">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-cyan-300">
          <ArrowLeft className="w-4 h-4" /> Back to Home
        </Link>
        <h1 className="mt-6 text-3xl font-bold text-white">Dashboard placeholder</h1>
        <p className="mt-3 text-slate-400">The full citation analysis dashboard lives in a separate module.</p>
        <Outlet />
      </div>
    </div>
  );
}
