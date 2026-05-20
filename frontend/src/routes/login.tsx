import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";

export const Route = createFileRoute("/login")({
  head: () => ({ meta: [{ title: "Sign In — CiteGraph-NLP" }] }),
  component: () => (
    <div className="min-h-screen bg-background grid place-items-center px-4">
      <div className="text-center">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-cyan-300">
          <ArrowLeft className="w-4 h-4" /> Back to Home
        </Link>
        <h1 className="mt-6 text-3xl font-bold text-white">Sign In placeholder</h1>
        <p className="mt-3 text-slate-400">Authentication will be wired up in the full app.</p>
      </div>
    </div>
  ),
});
