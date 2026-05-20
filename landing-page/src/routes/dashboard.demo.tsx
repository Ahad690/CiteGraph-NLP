import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/dashboard/demo")({
  head: () => ({ meta: [{ title: "Demo — CiteGraph-NLP" }] }),
  component: () => <div className="mt-6 text-cyan-300">Demo graph placeholder</div>,
});
