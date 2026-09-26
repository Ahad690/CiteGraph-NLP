import { createFileRoute } from "@tanstack/react-router";
import { WorkbenchLanding } from "@/components/landing/WorkbenchLanding";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "CiteGraph-NLP — Confidence-Aware Citation Lineage Analysis" },
      {
        name: "description",
        content:
          "Turn a DOI, PMID, paper title, or PDF into a confidence-aware citation knowledge graph. Explore probable foundational papers, population evidence, and research lineage.",
      },
      {
        name: "keywords",
        content:
          "citation graph, research knowledge graph, NLP literature review, citation lineage, foundational papers, biomedical NLP, study population extraction, OpenAlex, Crossref, PubMed, evidence ranking",
      },
      { property: "og:title", content: "CiteGraph-NLP — Research Graph Intelligence" },
      {
        property: "og:description",
        content:
          "Map citation lineage, extract study-scale evidence, and identify probable foundational papers with confidence-aware NLP.",
      },
      { property: "og:url", content: "/" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: "CiteGraph-NLP — Research Graph Intelligence" },
      {
        name: "twitter:description",
        content: "Confidence-aware citation lineage analysis for researchers and NLP students.",
      },
    ],
    links: [{ rel: "canonical", href: "/" }],
  }),
  component: Landing,
});

function Landing() {
  return <WorkbenchLanding />;
}
