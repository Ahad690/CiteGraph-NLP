BUILD REQUEST: CiteGraph-NLP Landing Page

Overview

Build a complete, production-ready landing page for **CiteGraph-NLP**, an AI/NLP-powered research analysis platform that helps researchers, students, and data scientists explore citation lineage, extract study population evidence, build citation knowledge graphs, and identify probable foundational papers.

The landing page should be modern, premium, scientific, trustworthy, animated, conversion-focused, and fully responsive.

The app needs a marketing landing page at `/` that introduces the product and converts visitors into users who start a research analysis.

IMPORTANT:
- This is the landing page / marketing page only.
- Do NOT build the full analysis dashboard here.
- Do NOT build the full citation graph dashboard pages here.
- You may include a compact DOI / title input CTA on the landing page, but the full dashboard lives separately.
- The landing page should clearly explain what CiteGraph-NLP does and why it is useful.
- The page must be fully self-contained and should not assume any previous context.

---

# PRODUCT INFORMATION

Product Name:
**CiteGraph-NLP**

Tagline:
**Confidence-Aware Citation Lineage Analysis**

One-liner:
Turn a DOI, PMID, paper title, or PDF into a confidence-aware citation knowledge graph that reveals probable foundational papers, study-scale evidence, and research lineage.

Production URL:
`https://citegraph-nlp.app` placeholder

API URL:
`http://localhost:8000` for local development

Product Category:
AI research intelligence dashboard, NLP research analysis tool, citation graph analytics platform.

---

# WHAT THE PRODUCT DOES

CiteGraph-NLP is a research analysis system that helps users understand how scientific ideas evolve across literature.

The system:

1. Accepts a DOI, PMID, PMCID, paper title, or uploaded PDF.
2. Resolves research paper metadata using scholarly APIs such as OpenAlex, Crossref, Europe PMC, PubMed, and Semantic Scholar.
3. Retrieves backward references and forward citations where available.
4. Builds a citation network from the seed paper.
5. Extracts population-size evidence from abstracts or full text using NLP and rule-based methods.
6. Detects candidate sample-size mentions such as:
   - `N = 10,000`
   - `8,500 randomized patients`
   - `25,000 participants`
   - `sample size of 3,200`
   - `cohort of 100,000 individuals`
7. Classifies population evidence into semantic types such as:
   - TOTAL_RANDOMIZED
   - TOTAL_ANALYZED
   - TOTAL_ENROLLED
   - ARM_SIZE
   - SAMPLE_SIZE_GENERIC
   - UNKNOWN_NUMERIC
8. Assigns confidence scores to extracted population evidence.
9. Builds a study-aware Knowledge Graph with papers, studies, population observations, journals, and citation edges.
10. Calculates confidence-aware citation edge weights using population size, journal/source metrics, and extraction confidence.
11. Ranks probable foundational papers.
12. Visualizes citation lineage and evidence-weighted research paths.
13. Exports results as JSON, CSV, GraphML, or Markdown reports.

---

# IMPORTANT SCIENTIFIC POSITIONING

The system is intentionally confidence-aware.

It should NOT claim to:
- Find the absolute original paper.
- Guarantee complete citation coverage.
- Perfectly extract every sample size.
- Provide definitive evidence rankings.
- Replace expert review.

It SHOULD claim to:
- Estimate probable foundational papers.
- Provide confidence-aware population extraction.
- Build evidence-weighted citation lineage maps.
- Help researchers explore research evolution.
- Make uncertainty visible.
- Support faster literature review and research discovery.

Use these phrases:
- “probable foundational papers”
- “confidence-aware extraction”
- “citation lineage estimate”
- “evidence-weighted ranking”
- “study-scale evidence”
- “metadata coverage may be incomplete”
- “research graph intelligence”

Avoid these phrases:
- “absolute original paper”
- “guaranteed parent paper”
- “perfect extraction”
- “fully accurate ranking”
- “definitive origin paper”

---

# TARGET AUDIENCE

Primary users:

1. **University students**
   - NLP students
   - AI students
   - biomedical informatics students
   - research methods students

2. **Researchers**
   - biomedical researchers
   - clinical researchers
   - systematic review authors
   - graduate researchers
   - PhD students

3. **Data scientists**
   - people working with academic literature
   - citation network analysts
   - knowledge graph developers

4. **Academic teams**
   - labs that need to analyze research lineage
   - teams reviewing evidence behind clinical papers
   - people building literature review tools

Main user pain points:
- It is hard to trace where a research idea came from.
- Citation counts alone are not enough.
- Papers cite dozens of older papers.
- Many citation networks are too large to inspect manually.
- Large clinical studies may contain stronger evidence, but sample sizes are buried in text.
- Existing paper search tools do not show citation lineage clearly.
- Researchers need explainable, confidence-aware results.

---

# CORE VALUE PROPOSITION

CiteGraph-NLP helps users move from:

“Here is one paper.”

To:

“Here is the citation lineage behind this paper, the probable foundational studies, the population-size evidence, and the confidence behind each result.”

Main value:
- Faster literature review
- Better research context
- Evidence-aware citation analysis
- Visual citation lineage
- Transparent uncertainty
- Exportable research reports

---

# TECHNICAL REQUIREMENTS

Stack Must Use:
- React 18
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui components
- React Router v6
- Lucide React icons
- CSS keyframes + Tailwind animations
- Optional: Framer Motion if available and useful
- Optional: Recharts for simple visual mini charts
- Optional: Cytoscape / React Force Graph only for decorative landing-page graph previews, not the full dashboard

---

# FILE STRUCTURE TO CREATE

Create this structure:

```text
src/
├── components/
│   └── landing/
│       ├── Navbar.tsx
│       ├── Hero.tsx
│       ├── ResearchInputMock.tsx
│       ├── CitationGraphShowcase.tsx
│       ├── ProblemSection.tsx
│       ├── Features.tsx
│       ├── HowItWorks.tsx
│       ├── ConfidenceSection.tsx
│       ├── KnowledgeGraphSection.tsx
│       ├── UseCases.tsx
│       ├── Pricing.tsx
│       ├── Testimonials.tsx
│       ├── FAQ.tsx
│       ├── FinalCTA.tsx
│       ├── Footer.tsx
│       └── CookieConsent.tsx
├── pages/
│   ├── Landing.tsx
│   ├── TermsOfService.tsx
│   └── PrivacyPolicy.tsx
├── lib/
│   └── analytics.ts
└── App.tsx
````

---

# ROUTING

Create these routes:

```tsx
<Route path="/" element={<Landing />} />
<Route path="/terms" element={<TermsOfService />} />
<Route path="/privacy" element={<PrivacyPolicy />} />

// These routes can link externally or be placeholders if the full app is not built here:
<Route path="/dashboard" element={<div>Dashboard placeholder</div>} />
<Route path="/dashboard/:runId" element={<div>Dashboard placeholder</div>} />
<Route path="/login" element={<div>Login placeholder</div>} />
<Route path="/signup" element={<div>Signup placeholder</div>} />
```

CTA destinations:

* “Start Analysis” → `/dashboard`
* “Try Demo” → `/dashboard/demo`
* “Sign In” → `/login`
* “Get Started” → `/signup`
* “View Dashboard” → `/dashboard`
* “Watch Demo” → smooth scroll to `#showcase`
* “How It Works” → smooth scroll to `#how-it-works`
* “Pricing” → smooth scroll to `#pricing`
* “FAQ” → smooth scroll to `#faq`

---

# DESIGN SYSTEM

Theme:
Dark-first premium AI research aesthetic.

The page should feel like:

* Scientific
* Premium
* Intelligent
* Trustworthy
* Modern
* Slightly futuristic
* Graph/data-oriented
* Not playful
* Not generic SaaS
* Not a basic admin panel

Visual inspiration:

* AI research lab dashboard
* Academic knowledge graph explorer
* Dark scientific data platform
* Premium developer tool
* Subtle glassmorphism
* Deep indigo/cyan glow accents

---

# COLORS

Main backgrounds:

```css
--background: #020617;
--background-secondary: #0f172a;
--background-soft: #111827;
```

Gradient backgrounds:

```css
bg-gradient-to-br from-[#020617] via-[#0f172a] to-[#111827]
```

Hero radial glow:

```css
bg-[radial-gradient(circle_at_top_left,rgba(79,70,229,0.25),transparent_35%),radial-gradient(circle_at_top_right,rgba(6,182,212,0.18),transparent_32%),linear-gradient(135deg,#020617,#0f172a,#111827)]
```

Surface colors:

```css
--surface: rgba(15, 23, 42, 0.72);
--surface-strong: #111827;
--surface-hover: #1e293b;
```

Borders:

```css
--border: rgba(148, 163, 184, 0.16);
--border-strong: rgba(148, 163, 184, 0.28);
```

Text:

```css
--text-primary: #f8fafc;
--text-secondary: #cbd5e1;
--text-muted: #94a3b8;
--text-disabled: #64748b;
```

Accent colors:

```css
--indigo: #4f46e5;
--cyan: #06b6d4;
--purple: #8b5cf6;
--emerald: #10b981;
--amber: #f59e0b;
--rose: #f43f5e;
```

Graph colors:

* Seed paper: Indigo/Cyan gradient
* High confidence: Emerald
* Medium confidence: Amber
* Low confidence: Rose
* Missing evidence: Slate gray
* Citation edge: Cyan with opacity
* Strong weighted edge: Cyan/Indigo glow
* Foundational candidate: Purple/Cyan ring

---

# TYPOGRAPHY

Use **Inter** or a similar modern sans-serif font.

Typography scale:

* Tiny labels: 11px, uppercase, letter-spacing 0.08em
* Small text: 12px
* Body text: 14px to 16px
* Section subheading: 18px
* Page heading: 32px
* Hero heading: 56px to 76px on desktop

Hero heading style:

* Large
* Tight tracking
* Bold
* Clean line-height

Use gradient text sparingly for key phrases:

```css
bg-gradient-to-r from-[#06b6d4] via-[#4f46e5] to-[#8b5cf6] bg-clip-text text-transparent
```

---

# SPACING AND RADIUS

Use an 8px spacing grid.

Border radius:

* Small buttons: 10px
* Inputs: 12px
* Cards: 18px
* Panels: 22px
* Large visual containers: 28px
* Modals: 24px

Glass card style:

```css
bg-slate-900/60 border border-slate-700/40 backdrop-blur-xl rounded-2xl shadow-2xl shadow-black/20
```

Premium hover card:

```css
hover:-translate-y-1 hover:border-cyan-400/30 hover:shadow-xl hover:shadow-cyan-500/10 transition-all duration-300
```

---

# BACKGROUND DECORATION

Add subtle scientific/graph-themed background visuals:

1. Animated graph-node constellation:

   * Small dots connected by faint lines
   * Low opacity
   * Cyan/indigo glow
   * Should not distract from content

2. Grid overlay:

```tsx
<div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(148,163,184,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(148,163,184,0.06)_1px,transparent_1px)] bg-[size:48px_48px]" />
```

3. Floating blurred blobs:

* Indigo blob top-left
* Cyan blob right
* Purple blob bottom
* Emerald blob near feature section
* Use very low opacity

4. Optional animated particles:

* Very subtle
* Slow
* Professional

---

# REQUIRED ANIMATIONS

Add these to Tailwind config or CSS:

```typescript
keyframes: {
  'float': {
    '0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
    '50%': { transform: 'translateY(-18px) rotate(1.5deg)' },
  },
  'fade-in': {
    '0%': { opacity: '0' },
    '100%': { opacity: '1' },
  },
  'slide-up': {
    '0%': { opacity: '0', transform: 'translateY(24px)' },
    '100%': { opacity: '1', transform: 'translateY(0)' },
  },
  'slide-down': {
    '0%': { opacity: '0', transform: 'translateY(-24px)' },
    '100%': { opacity: '1', transform: 'translateY(0)' },
  },
  'scale-in': {
    '0%': { opacity: '0', transform: 'scale(0.96)' },
    '100%': { opacity: '1', transform: 'scale(1)' },
  },
  'pulse-glow': {
    '0%, 100%': { boxShadow: '0 0 0 rgba(6,182,212,0)' },
    '50%': { boxShadow: '0 0 32px rgba(6,182,212,0.28)' },
  },
  'edge-flow': {
    '0%': { strokeDashoffset: '80' },
    '100%': { strokeDashoffset: '0' },
  },
  'scan-line': {
    '0%': { transform: 'translateY(-100%)' },
    '100%': { transform: 'translateY(600%)' },
  },
  'number-count': {
    '0%': { opacity: '0', transform: 'translateY(6px)' },
    '100%': { opacity: '1', transform: 'translateY(0)' },
  }
},
animation: {
  'float': 'float 7s ease-in-out infinite',
  'fade-in': 'fade-in 0.5s ease-out forwards',
  'slide-up': 'slide-up 0.6s ease-out forwards',
  'slide-down': 'slide-down 0.5s ease-out forwards',
  'scale-in': 'scale-in 0.5s ease-out forwards',
  'pulse-glow': 'pulse-glow 3s ease-in-out infinite',
  'edge-flow': 'edge-flow 2.4s linear infinite',
  'scan-line': 'scan-line 3s ease-in-out infinite',
  'number-count': 'number-count 0.45s ease-out forwards'
}
```

---

# LANDING PAGE SECTIONS

Build these sections in order:

1. Navbar
2. Hero
3. Research Input Mock / Product Preview
4. Problem Section
5. Stats
6. Features
7. How It Works
8. Confidence-Aware Analysis Section
9. Knowledge Graph Showcase
10. Use Cases
11. Pricing
12. Testimonials
13. FAQ
14. Final CTA
15. Footer
16. Cookie Consent component, created but commented out

---

# 1. NAVBAR

Component:
`Navbar.tsx`

Behavior:

* Fixed at top
* Transparent on page load
* On scroll, becomes:

```css
bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/70 shadow-lg shadow-black/10
```

* z-index above all content

Contents:

* Logo
* Navigation links
* CTA buttons
* Mobile hamburger menu

Logo:

* Icon: network/graph icon using `Network`, `Share2`, or `GitBranch` from lucide-react
* Container:

```css
w-11 h-11 rounded-xl bg-gradient-to-br from-[#4f46e5] to-[#06b6d4] shadow-lg shadow-cyan-500/20
```

* Brand text:
  `CiteGraph-NLP`
* Small optional subtitle:
  `Research Graph Intelligence`

Navigation links:

* Features
* How It Works
* Graph
* Use Cases
* Pricing
* FAQ

CTAs:

* “Sign In” → `/login`
* “Start Analysis” → `/dashboard`

Primary CTA style:

```css
bg-gradient-to-r from-[#4f46e5] to-[#06b6d4] text-white px-5 py-2.5 rounded-xl font-semibold shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30
```

Mobile:

* Hamburger menu
* Full-screen or dropdown mobile nav
* Same links and CTAs

---

# 2. HERO SECTION

Component:
`Hero.tsx`

Hero should be visually stunning and immediately explain the product.

Badge:

```text
🧠 NLP-powered citation lineage analysis
```

Badge style:

```css
inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-1.5 text-sm font-medium text-cyan-200
```

Headline:

```text
Trace research ideas through citation graphs.
```

Second line with gradient:

```text
Find probable foundational papers.
```

Hero headline style:

```css
text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-tight text-white
```

Gradient line:

```css
bg-gradient-to-r from-[#06b6d4] via-[#4f46e5] to-[#8b5cf6] bg-clip-text text-transparent
```

Subheadline:

```text
CiteGraph-NLP turns a DOI, PMID, paper title, or PDF into a confidence-aware research knowledge graph — revealing citation lineage, study population evidence, and evidence-weighted foundational papers.
```

Subheadline style:

```css
text-lg md:text-xl text-slate-300 max-w-3xl mx-auto leading-relaxed
```

Benefits row:

* Confidence-aware extraction
* Citation lineage mapping
* Study-scale evidence ranking

Use check icons or small graph icons.

CTA buttons:

1. Primary:

   ```text
   Start Analysis
   ```

   Icon: `Search` or `Network`
   Link: `/dashboard`

2. Secondary:

   ```text
   View Demo Graph
   ```

   Icon: `PlayCircle`
   Smooth scroll to `#showcase`

Social proof line:

```text
Built for researchers, NLP students, and evidence-driven literature review.
```

Add trusted-by style muted text:

```text
OpenAlex • Crossref • PubMed • Europe PMC • Semantic Scholar
```

Do not imply official partnerships. Use wording:
“Designed to work with metadata sources such as…”

---

# 3. RESEARCH INPUT MOCK / PRODUCT PREVIEW

Component:
`ResearchInputMock.tsx`

This is not the full ingestion form. It is a visual product preview.

Create a large mock app window below the hero.

Browser/app window:

* Rounded 28px
* Dark glass panel
* Border
* Shadow
* Floating animation

Top chrome:

* Three dots left
* URL pill:

```text
citegraph-nlp.app/analyze
```

Inside content:
Two columns on desktop, stacked on mobile.

Left column:
Mock input panel:

* Label: “Seed Paper”
* Input with sample DOI:

```text
10.1056/NEJMoa2034577
```

* Dropdown mock:

```text
Input Type: DOI
```

* Sliders:

  * Backward Depth: 2
  * Max Papers: 50
* Button:

```text
Analyze Citation Lineage
```

Show status steps:

* Metadata resolved
* Citations retrieved
* Population evidence extracted
* Graph built
* Rankings calculated

Right column:
Mini dashboard preview:

* Small cards:

  * 47 Papers
  * 126 Citation Edges
  * 18 Population Values
  * 6 Probable Foundations
* Small graph preview with nodes and connecting lines
* Seed node highlighted
* Foundational nodes with glow rings

Add animated scan line or subtle graph edge animation.

---

# 4. PROBLEM SECTION

Component:
`ProblemSection.tsx`

Section Header:
Badge:

```text
The Research Discovery Problem
```

Headline:

```text
Citation counts tell you what is popular.
They do not tell you where the idea came from.
```

Subhead:

```text
Modern papers cite dozens of earlier works. Those papers cite even more. Important population evidence is buried inside abstracts, methods sections, and tables. Manually tracing the lineage is slow, incomplete, and hard to explain.
```

Create three pain cards:

1. **Citation networks are messy**

   * Icon: `GitBranch`
   * Description:

   ```text
   A single paper can connect to hundreds of earlier studies across multiple generations of references.
   ```

2. **Sample sizes are buried in text**

   * Icon: `FileSearch`
   * Description:

   ```text
   Papers mention enrolled patients, randomized participants, analyzed cohorts, arms, events, and follow-ups — not all numbers mean the same thing.
   ```

3. **Foundational work is hard to identify**

   * Icon: `Compass`
   * Description:

   ```text
   The most useful earlier paper is not always the most cited paper. Evidence strength and graph position both matter.
   ```

Add visual:

* A tangled citation mini graph on one side
* Then a cleaned structured graph on the other side
* Arrow between them:

```text
CiteGraph-NLP
```

---

# 5. STATS SECTION

Component:
`Stats.tsx`

Create 4 stat cards.

Stats:

| Icon        | Value | Label                  | Description                                              |
| ----------- | ----: | ---------------------- | -------------------------------------------------------- |
| Network     |   100 | Papers per MVP run     | Depth-limited citation traversal                         |
| GitBranch   |     2 | Default backward depth | Trace cited papers recursively                           |
| Database    |    5+ | Metadata sources       | OpenAlex, Crossref, PubMed, Europe PMC, Semantic Scholar |
| ShieldCheck |  100% | Confidence-aware       | Every uncertain result is labeled                        |

Card style:

```css
bg-slate-900/60 border border-slate-700/40 rounded-2xl p-6 backdrop-blur-xl hover:border-cyan-400/30 transition-all
```

Numbers should be large and bold.

---

# 6. FEATURES SECTION

Component:
`Features.tsx`

Section Header:
Badge:

```text
Features
```

Headline:

```text
Everything you need to map citation lineage with confidence.
```

Subhead:

```text
From metadata resolution to population extraction and graph visualization, CiteGraph-NLP gives you an explainable research analysis workflow.
```

Create 8 feature cards in grid:

* 4 columns desktop
* 2 columns tablet
* 1 column mobile

Feature cards:

1. **Identifier-First Metadata Resolution**

   * Icon: `Fingerprint`
   * Description:

   ```text
   Start with DOI, PMID, PMCID, title, or PDF. The system resolves structured metadata before parsing full text.
   ```

2. **Multi-Source Scholarly APIs**

   * Icon: `Database`
   * Description:

   ```text
   Designed to work with OpenAlex, Crossref, Europe PMC, PubMed, Semantic Scholar, and other metadata providers.
   ```

3. **Citation Network Traversal**

   * Icon: `GitBranch`
   * Description:

   ```text
   Retrieve backward references and forward citations to build depth-limited citation lineage maps.
   ```

4. **Population-Size Extraction**

   * Icon: `Users`
   * Description:

   ```text
   Extract candidate sample sizes like randomized patients, enrolled participants, analyzed cohorts, and arm sizes.
   ```

5. **Semantic Evidence Classification**

   * Icon: `Tags`
   * Description:

   ```text
   Classify extracted values as TOTAL_RANDOMIZED, TOTAL_ANALYZED, TOTAL_ENROLLED, ARM_SIZE, and more.
   ```

6. **Confidence Scoring**

   * Icon: `ShieldCheck`
   * Description:

   ```text
   Every extracted value includes a confidence score, evidence sentence, source section, and ambiguity status.
   ```

7. **Study-Aware Knowledge Graphs**

   * Icon: `Network`
   * Description:

   ```text
   Separate papers, studies, journals, population observations, and citation edges for more realistic modeling.
   ```

8. **Evidence-Weighted Rankings**

   * Icon: `Trophy`
   * Description:

   ```text
   Rank probable foundational papers using citation position, graph connectivity, population evidence, and confidence.
   ```

Feature card style:

```css
bg-slate-900/60 border border-slate-700/40 rounded-2xl p-6 hover:-translate-y-1 hover:border-cyan-400/30 hover:shadow-xl hover:shadow-cyan-500/10 transition-all duration-300
```

Add badges on some features:

* “NLP”
* “Knowledge Graph”
* “Confidence-Aware”
* “Biomedical Ready”

---

# 7. HOW IT WORKS SECTION

Component:
`HowItWorks.tsx`

Section ID:
`#how-it-works`

Section Header:
Badge:

```text
How It Works
```

Headline:

```text
From one paper to a research lineage map.
```

Subhead:

```text
CiteGraph-NLP follows an identifier-first, confidence-aware pipeline designed for realistic academic literature analysis.
```

Create 5 steps with connector lines:

Step 01:
**Input a Seed Paper**

* Icon: `Search`
* Description:

```text
Start from a DOI, PMID, paper title, PMCID, or user-provided PDF.
```

Step 02:
**Resolve Metadata**

* Icon: `Database`
* Description:

```text
Query scholarly APIs and merge metadata with field-level provenance.
```

Step 03:
**Extract Population Evidence**

* Icon: `FileSearch`
* Description:

```text
Use NLP and rule-based extraction to detect population-size candidates and evidence sentences.
```

Step 04:
**Build Citation Graph**

* Icon: `Network`
* Description:

```text
Create a directed graph of papers, studies, journals, population observations, and citation edges.
```

Step 05:
**Rank Probable Foundations**

* Icon: `Trophy`
* Description:

```text
Rank likely foundational papers using evidence-weighted graph analytics and confidence scores.
```

Add animated connector lines between steps on desktop.

Bottom CTA:

```text
Start with a DOI and get a citation lineage map in minutes.
```

Button:

```text
Start Analysis
```

Link:
`/dashboard`

---

# 8. CONFIDENCE-AWARE ANALYSIS SECTION

Component:
`ConfidenceSection.tsx`

Section Header:
Badge:

```text
Built for uncertainty
```

Headline:

```text
Research data is messy. CiteGraph-NLP makes uncertainty visible.
```

Subhead:

```text
Instead of pretending every extraction is perfect, the system labels ambiguity, tracks provenance, and assigns confidence scores to metadata, population evidence, and citation edges.
```

Create three visual panels:

Panel 1:
**Evidence Sentence**
Show a paper text snippet:

```text
“A total of 8,500 patients were randomized, with 4,250 assigned to treatment and 4,250 assigned to control.”
```

Highlight:

* `8,500 patients`
* `randomized`

Panel 2:
**Semantic Classification**
Show badges:

* TOTAL_RANDOMIZED
* Confidence: High
* Section: Methods
* N_eff: 8,500

Panel 3:
**Ambiguity Handling**
Show warning card:

```text
Multiple candidate values found. Marked ambiguous until reviewed.
```

Include confidence levels:

* High: 0.75+
* Medium: 0.45–0.74
* Low: below 0.45

Design:

* Cards in dark glass style
* Use emerald/amber/rose badges
* Add subtle scan-line animation over evidence snippet

---

# 9. KNOWLEDGE GRAPH SHOWCASE

Component:
`KnowledgeGraphSection.tsx`

Section ID:
`#showcase`

Section Header:
Badge:

```text
Graph Intelligence
```

Headline:

```text
See how research papers connect across generations.
```

Subhead:

```text
Visualize citation direction, population evidence, confidence levels, and probable foundational papers in one graph.
```

Create a large visual showcase.

Left side:
Interactive-looking graph mockup:

* Dark panel
* Nodes connected by directional edges
* Seed paper node glowing indigo/cyan
* Older papers positioned to the left or below
* Foundational candidates with cyan/purple rings
* Edge thickness varies
* Node sizes vary

Graph labels:

* “Seed Paper”
* “High N_eff”
* “Probable Foundation”
* “Low Confidence”
* “Weighted Citation Edge”

Right side:
Explanation cards:

1. **Node size = study population**
2. **Edge thickness = citation weight**
3. **Color = confidence level**
4. **Ring = foundational candidate**
5. **Direction = citation lineage**

Add a mini legend:

* Emerald = high confidence
* Amber = medium confidence
* Rose = low confidence
* Slate = missing data

Important:
This is a landing-page mock graph, not the full dashboard implementation.

---

# 10. USE CASES SECTION

Component:
`UseCases.tsx`

Section Header:
Badge:

```text
Use Cases
```

Headline:

```text
Designed for serious research workflows.
```

Subhead:

```text
Whether you are building an NLP project, reviewing biomedical evidence, or mapping a research field, CiteGraph-NLP helps you understand the structure behind the literature.
```

Create 6 use-case cards:

1. **NLP Course Projects**

   * Icon: `Brain`
   * Description:

   ```text
   Demonstrate PDF parsing, entity extraction, citation traversal, and knowledge graph construction in one complete project.
   ```

2. **Biomedical Literature Review**

   * Icon: `Microscope`
   * Description:

   ```text
   Explore population evidence and citation lineage behind clinical studies.
   ```

3. **Systematic Review Preparation**

   * Icon: `ClipboardList`
   * Description:

   ```text
   Quickly identify older connected papers and evidence-rich citation paths.
   ```

4. **Research Idea Tracing**

   * Icon: `Compass`
   * Description:

   ```text
   Follow references backward to understand how a research idea developed.
   ```

5. **Knowledge Graph Experiments**

   * Icon: `Network`
   * Description:

   ```text
   Export citation networks as GraphML or JSON for downstream graph analytics.
   ```

6. **Evidence-Aware Ranking**

   * Icon: `BarChart3`
   * Description:

   ```text
   Compare papers using population-size signals, source metrics, and confidence scores.
   ```

---

# 11. PRICING SECTION

Component:
`Pricing.tsx`

Section ID:
`#pricing`

Pricing should be SaaS-style, but keep it realistic for a student/research tool.

Section Header:
Badge:

```text
Pricing
```

Headline:

```text
Start free. Scale when your research grows.
```

Subhead:

```text
Use CiteGraph-NLP for course projects, literature review experiments, and citation graph analysis.
```

Create 3 pricing cards:

## Free

Price:
`$0`

Description:

```text
For students and quick experiments.
```

Features:

* 5 analysis runs/month
* Up to 25 papers per run
* DOI/title input
* Basic metadata resolution
* Basic citation graph
* JSON export
* Community support

CTA:
`Start Free`
Link:
`/signup`

Style:
Outline/soft button

## Researcher

Price:
`$12/month`

Description:

```text
For serious literature exploration.
```

Badge:
`Most Popular`

Features:

* 100 analysis runs/month
* Up to 250 papers per run
* Population extraction
* Confidence-aware rankings
* Citation paths
* CSV, JSON, GraphML exports
* Priority API queue
* Saved projects

CTA:
`Start Researcher Plan`
Link:
`/signup?plan=researcher`

Style:
Primary gradient button with glow

## Lab

Price:
`$49/month`

Description:

```text
For teams, labs, and advanced graph workflows.
```

Features:

* Unlimited saved projects
* Up to 1,000 papers per run
* Team workspace
* Neo4j export
* Batch seed papers
* Shared reports
* Advanced graph analytics
* Priority support

CTA:
`Contact / Start Lab Plan`
Link:
`/signup?plan=lab`

Bottom note:

```text
Academic use only? Add your .edu email for student-friendly access.
```

---

# 12. TESTIMONIALS SECTION

Component:
`Testimonials.tsx`

Section Header:
Badge:

```text
Testimonials
```

Headline:

```text
Built for researchers who need more than search results.
```

Subhead:

```text
CiteGraph-NLP helps turn literature exploration into a structured, explainable workflow.
```

Create 6 testimonial cards with realistic placeholder testimonials.

1. **Ayesha Khan**

   * Role: MS Artificial Intelligence Student
   * Institution: NUST
   * Country: Pakistan 🇵🇰
   * Quote:

   ```text
   “CiteGraph-NLP made our NLP project feel like a real research tool. The confidence-aware extraction gave us a much stronger proposal than a simple citation counter.”
   ```

2. **Daniel Reed**

   * Role: Biomedical Research Assistant
   * Institution: University of Manchester
   * Country: UK 🇬🇧
   * Quote:

   ```text
   “The graph view helped me understand which earlier clinical studies were actually connected to the paper I was reviewing.”
   ```

3. **Priya Menon**

   * Role: PhD Candidate, Public Health
   * Institution: AIIMS
   * Country: India 🇮🇳
   * Quote:

   ```text
   “Population-size extraction with confidence labels is exactly what literature review tools usually miss.”
   ```

4. **Omar Al-Farsi**

   * Role: Data Science Researcher
   * Institution: Qatar University
   * Country: Qatar 🇶🇦
   * Quote:

   ```text
   “Exporting the citation graph as structured data made it easy to continue analysis in NetworkX and Gephi.”
   ```

5. **Emily Carter**

   * Role: Systematic Review Author
   * Institution: University of Toronto
   * Country: Canada 🇨🇦
   * Quote:

   ```text
   “I liked that it did not overclaim certainty. Ambiguous extraction results were clearly labeled instead of hidden.”
   ```

6. **Hamza Malik**

   * Role: BS Computer Science Student
   * Institution: FAST
   * Country: Pakistan 🇵🇰
   * Quote:

   ```text
   “The idea of separating papers, studies, and population observations made our knowledge graph much more defensible.”
   ```

Each card:

* Quote icon
* Quote text
* Name
* Role
* Institution
* Country flag
* Small avatar initials in gradient circle

Carousel:

* Show 3 on desktop
* Show 1 on mobile
* Auto-rotate every 6 seconds
* Include arrows and dots

---

# 13. FAQ SECTION

Component:
`FAQ.tsx`

Section ID:
`#faq`

Use shadcn Accordion.

Section Header:
Badge:

```text
FAQ
```

Headline:

```text
Frequently asked questions
```

Subhead:

```text
Everything you need to know about confidence-aware citation lineage analysis.
```

FAQ items:

1. **Does CiteGraph-NLP find the original paper behind a research idea?**
   Answer:

   ```text
   No tool can guarantee the absolute original paper because citation databases are incomplete and research ideas evolve gradually. CiteGraph-NLP identifies probable foundational papers using citation position, graph connectivity, study-scale evidence, and confidence-aware ranking.
   ```

   Badge: Research Accuracy

2. **What input types are supported?**
   Answer:

   ```text
   The system is designed to support DOI, PMID, PMCID, paper title, and uploaded PDF. The recommended workflow is identifier-first, meaning the system tries to resolve metadata through APIs before parsing full text.
   ```

   Badge: Input

3. **Which metadata sources does it use?**
   Answer:

   ```text
   CiteGraph-NLP is designed to work with public scholarly metadata sources such as OpenAlex, Crossref, Europe PMC, PubMed, and Semantic Scholar. Availability depends on the provider and paper.
   ```

   Badge: Metadata

4. **How does population-size extraction work?**
   Answer:

   ```text
   The system uses NLP and rule-based extraction to detect candidate population values such as randomized patients, enrolled participants, analyzed cohorts, and arm sizes. Each value is classified and assigned a confidence score.
   ```

   Badge: NLP

5. **Can it perfectly extract sample sizes?**
   Answer:

   ```text
   No. Research papers often contain many numbers, and not every number is a study population. CiteGraph-NLP makes uncertainty visible by labeling ambiguous or missing extractions instead of pretending every value is correct.
   ```

   Badge: Confidence

6. **What is N_eff?**
   Answer:

   ```text
   N_eff is the system's selected effective population size for a paper or study. It may represent randomized, analyzed, enrolled, or inferred population size depending on the evidence and confidence score.
   ```

   Badge: Population

7. **What is a confidence-aware citation weight?**
   Answer:

   ```text
   Citation edge weights combine normalized population-size evidence, journal/source metrics, and extraction confidence. Low-confidence population evidence reduces the final weight.
   ```

   Badge: Graph

8. **Is this only for biomedical research?**
   Answer:

   ```text
   The prototype works best for biomedical and clinical papers because they often contain structured metadata and population-size evidence. The graph and metadata parts can still apply to other domains.
   ```

   Badge: Scope

9. **Can I export the results?**
   Answer:

   ```text
   Yes. The planned exports include JSON reports, CSV tables, GraphML for graph tools, and Markdown reports for documentation or submission.
   ```

   Badge: Export

10. **Is this suitable for an NLP course project?**
    Answer:

```text
Yes. It combines metadata resolution, PDF parsing, NLP extraction, citation traversal, graph construction, confidence scoring, and visualization into one realistic project.
```

Badge: Students

Bottom:

```text
Still have questions? Contact us at research@citegraph-nlp.app →
```

---

# 14. FINAL CTA SECTION

Component:
`FinalCTA.tsx`

Background:

* Dark gradient
* Stronger indigo/cyan glow
* Subtle graph lines

Card:
Large centered glass card.

Icon:
Network / GitBranch icon inside gradient circle.

Headline:

```text
Ready to map the lineage behind your next paper?
```

Gradient phrase:

```text
Go from one DOI to an evidence-weighted citation graph.
```

Subhead:

```text
Start with a paper identifier and explore probable foundational studies, population evidence, and confidence-aware rankings in minutes.
```

Benefits row:

* No overclaiming
* Confidence-aware
* Exportable reports

CTA:
Primary:

```text
Start Analysis
```

Link:
`/dashboard`

Secondary:

```text
View Demo Graph
```

Link:
`/dashboard/demo`

Social proof:

```text
Built for NLP students, researchers, and evidence-driven literature review.
```

---

# 15. FOOTER

Component:
`Footer.tsx`

Footer layout:
4 columns on desktop, stacked on mobile.

Column 1:
Brand

* Logo
* Description:

```text
CiteGraph-NLP is a confidence-aware citation lineage and research knowledge graph platform for exploring probable foundational papers and study-scale evidence.
```

* Social icons:

  * GitHub
  * Twitter/X
  * LinkedIn
  * Email

Column 2:
Product

* Features
* How It Works
* Citation Graph
* Pricing
* Demo

Column 3:
Resources

* Documentation
* API Reference
* Research Notes
* NLP Pipeline
* Knowledge Graph Model

Column 4:
Legal

* Terms of Service
* Privacy Policy
* Contact
* Academic Disclaimer

Bottom bar:
Left:

```text
© 2026 CiteGraph-NLP. All rights reserved.
```

Right:

```text
Confidence-aware research graph intelligence.
```

Add academic disclaimer:

```text
CiteGraph-NLP provides exploratory research analysis. Results depend on metadata availability and should be reviewed by domain experts.
```

---

# 16. COOKIE CONSENT COMPONENT

Component:
`CookieConsent.tsx`

Create the component but keep it commented out in `Landing.tsx`.

Behavior:

* Appears at bottom after 2 seconds
* Stores preference in localStorage
* Does not show again after choice

Content:

```text
We use cookies to improve the research experience and understand product usage.
```

Buttons:

* Decline
* Accept All

Style:

* Dark glass card
* Border
* Rounded
* Cyan accent

---

# TERMS OF SERVICE PAGE

Component:
`TermsOfService.tsx`

Design:

* Same dark theme
* Back to Home link
* Logo
* Heading:

```text
Terms of Service
```

* Last updated:

```text
May 2026
```

Sections:

1. Acceptance of Terms
2. Description of Service
3. Research and Academic Use
4. User Accounts
5. Acceptable Use
6. Data Sources and Metadata
7. AI/NLP Analysis Disclaimer
8. No Guarantee of Completeness
9. Intellectual Property
10. Subscription and Billing
11. Limitation of Liability
12. Changes to Terms
13. Contact Us

Add disclaimer:

```text
CiteGraph-NLP provides exploratory research analysis and does not guarantee complete citation coverage, perfect extraction accuracy, or definitive research conclusions.
```

---

# PRIVACY POLICY PAGE

Component:
`PrivacyPolicy.tsx`

Design:

* Same dark theme
* Back to Home link
* Logo
* Heading:

```text
Privacy Policy
```

* Last updated:

```text
May 2026
```

Sections:

1. Information We Collect
2. Paper Identifiers and Research Inputs
3. Uploaded PDFs
4. Metadata Provider Requests
5. How We Use Information
6. Analytics
7. Data Storage and Security
8. Third-Party Metadata Providers
9. Exported Reports
10. Your Rights
11. Cookies
12. Changes to Policy
13. Contact Us

Add privacy note:

```text
Uploaded PDFs and research inputs should be handled responsibly. Do not upload content you do not have permission to process.
```

---

# ANALYTICS TRACKING

Create:
`src/lib/analytics.ts`

Track these events:

* `landing_page_view`
* `hero_cta_click`
* `hero_demo_click`
* `nav_cta_click`
* `nav_signin_click`
* `research_input_mock_interact`
* `problem_section_view`
* `feature_card_click`
* `how_it_works_step_view`
* `graph_showcase_view`
* `pricing_plan_click`
* `pricing_toggle`
* `testimonial_view`
* `faq_item_expand`
* `final_cta_click`
* `footer_link_click`
* `scroll_depth_25`
* `scroll_depth_50`
* `scroll_depth_75`
* `scroll_depth_100`

In development:

* Log analytics events to console.

Structure analytics utility so it can later connect to:

* GA4
* Mixpanel
* PostHog

Example:

```ts
export function trackEvent(eventName: string, properties?: Record<string, unknown>) {
  if (import.meta.env.DEV) {
    console.log("[analytics]", eventName, properties ?? {});
  }
}
```

---

# SEO REQUIREMENTS

Set meta tags.

Title:

```text
CiteGraph-NLP — Confidence-Aware Citation Lineage Analysis
```

Description:

```text
Turn a DOI, PMID, paper title, or PDF into a confidence-aware citation knowledge graph. Explore probable foundational papers, population evidence, and research lineage.
```

OG Title:

```text
CiteGraph-NLP — Research Graph Intelligence
```

OG Description:

```text
Map citation lineage, extract study-scale evidence, and identify probable foundational papers with confidence-aware NLP.
```

OG URL:

```text
https://citegraph-nlp.app
```

OG Type:

```text
website
```

Keywords:

```text
citation graph, research knowledge graph, NLP literature review, citation lineage, foundational papers, biomedical NLP, study population extraction, OpenAlex, Crossref, PubMed, evidence ranking
```

Canonical URL:

```text
https://citegraph-nlp.app
```

Create a simple OG image placeholder:

* 1200×630
* Dark background
* CiteGraph-NLP logo
* Mini citation graph mockup
* Headline:

```text
Confidence-Aware Citation Lineage Analysis
```

---

# RESPONSIVE REQUIREMENTS

Mobile `< 768px`:

* Hamburger navigation
* Single-column sections
* Full-width CTA buttons
* Hero headline smaller
* Product mockup stacks vertically
* Feature cards stack
* Pricing cards stack
* Graph showcase becomes simplified static preview
* Testimonials show one at a time
* Footer stacks

Tablet `768px - 1024px`:

* 2-column feature grids
* 2-column use cases
* Graph showcase stacks graph above explanation cards
* Navbar remains visible if space allows

Desktop `> 1024px`:

* Full nav
* Side-by-side hero/product mockup
* 4-column feature grid
* 3-card pricing
* Graph showcase side-by-side
* Footer columns

Large desktop `> 1440px`:

* Max content width around 1200–1320px
* Do not stretch text too wide
* Let backgrounds and graph decorations fill space

---

# ACCESSIBILITY REQUIREMENTS

* All buttons must be keyboard accessible.
* All interactive elements need visible focus states.
* Navigation links should have proper aria labels.
* Mobile menu should be accessible.
* Accordion FAQ should be accessible.
* Color should not be the only indicator of confidence/status.
* Use text labels alongside confidence colors.
* Use semantic HTML sections.
* Use readable contrast on dark background.
* Respect reduced motion preferences when possible.

---

# PERFORMANCE REQUIREMENTS

* Use CSS animations instead of heavy JS animations where possible.
* Lazy load below-the-fold sections if easy.
* Avoid loading heavy graph libraries just for decoration unless needed.
* Use simple SVG or div-based graph mockups for landing page visuals.
* Keep initial bundle small.
* Use optimized images or CSS illustrations.
* Avoid huge dependencies unless already included.

---

# CTA DESTINATIONS

All CTA routing:

* Start Analysis → `/dashboard`
* Get Started → `/signup`
* Sign In → `/login`
* View Demo Graph → `/dashboard/demo`
* Watch Demo → smooth scroll to `#showcase`
* Features → smooth scroll to `#features`
* How It Works → smooth scroll to `#how-it-works`
* Pricing → smooth scroll to `#pricing`
* FAQ → smooth scroll to `#faq`
* Terms → `/terms`
* Privacy → `/privacy`
* Contact → `mailto:research@citegraph-nlp.app`

---

# DEVELOPMENT NOTES

1. Build all landing components as separate files under `/components/landing/`.
2. Keep `Landing.tsx` clean and compositional.
3. Use shadcn/ui components where appropriate.
4. Use Lucide icons consistently.
5. Use dark mode by default.
6. Use polished micro-interactions.
7. Make the graph preview visually impressive.
8. Do not build the full dashboard.
9. Do not build the full ingestion workflow.
10. The landing page must be production-ready and demo-ready.
11. Make the page feel unique to research, citations, NLP, and knowledge graphs.
12. The visual identity should not look like a generic AI SaaS template.

---

# FINAL GOAL

Create a complete, polished, responsive, production-ready landing page for CiteGraph-NLP.

The page should clearly communicate:

* What the product does
* Why citation lineage matters
* How confidence-aware population extraction works
* How citation knowledge graphs help researchers
* Why the system identifies probable foundational papers rather than claiming certainty
* How users can start an analysis or view a demo

The final landing page should feel like a premium AI research intelligence product for serious academic and scientific workflows.