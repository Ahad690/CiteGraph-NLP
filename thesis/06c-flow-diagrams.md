# Chapter 6 (continued): Reading Participant-Flow Diagrams

## 6.14 A computer-vision reader for CONSORT flow diagrams

### 6.14.1 Why read the diagram

The weakest measured result in this chapter is semantic typing: of ten
correctly extracted population sizes, only six were labelled with the right
stage (Section 6.4.3). Telling randomised from enrolled from analysed from
surface patterns in an abstract is hard, because abstracts use the words
loosely and often state one number for several stages.

Most randomised trials report the same numbers a second time, in a form that
removes the ambiguity. The CONSORT statement asks every trial to publish a
participant-flow diagram showing how many people were assessed for
eligibility, randomised, allocated to each arm, followed up and analysed
[schulz2010consort]. In that diagram each count sits in a box, and the box's
position in the flow states which stage it counts. Reading the stage from the
layout, rather than guessing it from wording, is a computer-vision problem, and
this section describes a reader for it and measures it against the text method
on the same papers.

Coverage was measured before any code was written. Of 60 open-access
randomised trials from Europe PMC (2015 to 2024), 37 (62%) had a figure whose
caption identifies it as a flow diagram; a second sample of 60 had 42 (70%).
Every one of these images is retrievable from NCBI's public PMC Article
Datasets bucket, the supported route for bulk reuse of open-access figures.

### 6.14.2 Method

The reader, `src/citegraph/vision/flow_diagram.py`, has six stages.

1. **Text recognition.** RapidOCR, an ONNX export of the PP-OCR pipeline
   [du2020ppocr], returns each text line with its position. It is a fixed
   classifier rather than a generative model, so it cannot produce a number
   that is not in the image, which matters when the numbers are the output.
   Lines it is unsure of that contain a digit are cropped, enlarged three times
   and recognised again without re-running detection. PMC stores figures at
   about 700 pixels wide, where a four-arm diagram's text is 10 to 12 pixels
   tall; this step turned "Anaal s((a4)" back into "Analysed (n=4)" in 57 ms.
2. **Box detection.** Connector arrows touch the boxes they join, so the ink of
   a whole flow chart is usually one connected shape, and each box's interior
   is a hole in it. OpenCV finds those holes after adaptive thresholding, which
   treats square, rounded and elliptical boxes alike and keeps boxes separate
   even when an arrow runs into them.
3. **Regions.** Each text line joins the smallest box around its centre. Lines
   outside every box are clustered by proximity, because some diagrams draw no
   boxes at all.
4. **Counts.** Each count is paired with its label, in either of the two styles
   diagrams use: "Analysed (n = 35)", where the label precedes the count, and
   "96 Patients assessed for eligibility", where it follows.
5. **Stages.** Labels are classified with CONSORT vocabulary. Exclusion terms
   take precedence, so "Excluded from analysis (n = 3)" is not an analysed
   count, and every count inside a box that opens with an exclusion is treated
   as one of its listed reasons.
6. **Layout.** A count whose own label names no stage takes one from the side
   banner in its row or a heading directly above it. Arms in the same row are
   summed unless one box already states their total, the analysis row must lie
   below the allocated arms, and when no randomised count is printed the
   allocation row supplies it.

Figure 6.1 shows the reasoning on one diagram whose analysis boxes contain
nothing but "N = 85".

![**Figure 6.1** The reader on a development diagram from F1000Research
(doi:10.12688/f1000research.147840.3, CC BY 4.0). Grey outlines are every box
the detector found; coloured outlines are the boxes whose counts were used,
tagged with the stage assigned. The arms say only "Control" and "Video" and
the analysis boxes only "N = 85": their stages come from the side banners, and
the randomised total of 178 from summing the allocation row, because the
"Randomized" heading carries no count.](figures/flow_reader_example.png){width=78%}

### 6.14.3 Evaluation protocol

The reader was evaluated in three sets, and the order in which things were
done is part of the result, so it is recorded in the commit history.

| Set | Diagrams | Role | Seen by the designer before scoring? |
|--------------------|---------:|---------------------------------|------------------------|
| Development | 10 | rules written against these | yes |
| Second development | 27 | first held-out, then demoted | yes, during annotation |
| Held-out | 42 | the only basis for the decision | no |

The answer key records, for each diagram, the screened, enrolled, randomised
and analysed counts it states, with stages it leaves genuinely ambiguous marked
unscored rather than guessed. It was written by reading each image before any
reader code existed and committed at that point (commit `0aa6294`). Section
6.14.7 reports a blind second reading of it.

The 27 diagrams first intended as a test set were annotated by the same person
who then built the reader, so their result cannot count as held out. They were
used as a second development set instead, and four general fixes came from
their errors. Three further misses were deliberately left unfixed, because
fixing them would have meant special-casing single diagrams, one of them a
figure that misspells "analysis" as "amalysis".

The reader was then frozen (commit `b12ce13`). Only afterwards were 42 new
diagrams collected from the next page of the same search, sharing no paper
with the first set, and their answer key was written and committed
(`eb0e25a`) before the reader was run on any of them. The decision rule was
stated in `scripts/evaluate_flow_diagrams.py` before that run: the reader ships
only if, on held-out diagrams, it is right on at least 15 percentage points
more of the stated enrolled, randomised and analysed counts than the text
method, the difference holds under an exact McNemar test at p < 0.05, and it
reports nothing for most figures that are not participant flows.

The text method is the one the pipeline already uses: the pattern extractor of
Section 4.10 over the same paper's abstract, taking the first candidate of each
semantic type. Only stages a diagram states are scored, because an abstract
saying "91 patients were enrolled" is not wrong merely because the diagram
folds enrolment into randomisation. A lenient score is also reported, crediting
the text method whenever the right number appears among its candidates under
any label, which separates "not in the abstract" from "found but mislabelled".

### 6.14.4 Results

On the held-out set, counting the enrolled, randomised and analysed stages the
diagrams state:

| Method | Correct | 95% Wilson interval |
|--------|--------:|--------------------|
| Diagram reader | 61 / 69 (88%) | [0.79, 0.94] |
| Text method, stage-typed | 2 / 69 (3%) | [0.01, 0.10] |
| Text method, right number under any label | 26 / 69 (38%) | |

Of the 61 disagreements between the two methods, the reader was right in 60
and the text method in one (exact McNemar p < 0.0001). The reader reported
nothing for both held-out figures that were not participant flows, and for all
four such figures across the development sets. The rule is met.

| Stage (held-out) | Reader | Text method |
|------------------|-------:|------------:|
| Screened | 25 / 31 (81%) | 2 / 31 (6%) |
| Enrolled | 5 / 6 (83%) | 1 / 6 (17%) |
| Randomised | 35 / 37 (95%) | 0 / 37 (0%) |
| Analysed | 21 / 26 (81%) | 1 / 26 (4%) |

The development sets agree: 18 of 18 on the first, and 50 of 53 on the second
after its fixes (45 of 53 before them). The held-out figure is the lower of the
three, which is the expected direction and the reason it is the one reported
as the result.

The lenient line is the more useful comparison for understanding the text
method. The right number is present in the abstract for 38% of stated counts,
yet correctly typed for 3%, so most of the gap is the typing problem of Section
6.4.3 rather than missing information. The rest is that abstracts often state
only one or two of the four counts a diagram gives.

### 6.14.5 How it fails

Seven of the eight held-out misses on the scored stages are abstentions: the
reader reported nothing rather than a wrong number. In a tool meant to surface
uncertainty, that is the preferable way to fail. The one wrong value summed two
of three arms of an analysis row. Most misses trace to layouts the development
sets did not contain:

- a label above a bare number, with no "n =" ("Number randomised" over "43");
- "Number of patient analyzed = 12", an equals sign without "n";
- the count written before its label inside a box, "N=64 included in the
  analysis";
- stage words outside the CONSORT vocabulary, such as "Inclusion (N = 76)" and
  a randomisation box labelled only "Random:".

Each is a straightforward rule to add, but adding them now would repeat the
problem this protocol was designed to avoid: they were found by looking at the
held-out set, so their effect would have to be measured on another one.

### 6.14.6 Cost, scope and limits

Box detection takes about 10 ms; text recognition is the cost, a median of
4.9 s and at most 11 s per diagram on the development machine, with no GPU. That
is too slow to run for every trial in a 100-paper graph, so the reader is not
part of a run. The dashboard offers it on a trial's detail panel, the server
reads one diagram at a time in a worker thread so the API stays responsive, and
the result is stored with the run so a diagram is never read twice. Its counts
are shown beside the abstract extraction, not substituted for it, so a run's
edge weights and rankings remain the ones it was computed with. Feeding
diagram counts into the weighting is the natural next step, once the choice
between a diagram and an abstract that disagree has a principled rule.

The limits are specific:

- **Open access only.** The reader depends on open-access figures; about two
  thirds of the sampled open-access trials had a detectable diagram, and
  closed-access trials have none available.
- **The answer keys were written by the AI assistant used to build the system,**
  by reading each image. A blind second reading by two other models (Section
  6.14.7) found no number in them that the image contradicts, but no human has
  checked them, and the disagreements were settled by the assistant that wrote
  the keys. Section 3.5.4's concern about single-annotator gold standards
  therefore still applies, in a narrower form.
- **Units.** Cluster trials randomise clinics or schools and analyse people.
  The reader reports what each box says and does not reconcile units, so its
  randomised and analysed counts for such a trial can refer to different
  things, exactly as the diagram does.
- **Scale of the evidence.** 42 held-out diagrams give 69 scored decision
  counts. The interval on the reader's accuracy is correspondingly wide, from
  79% to 94%, though it does not approach the text method's.

### 6.14.7 A second, blind reading of the answer keys

Every answer key above was written by one annotator, the AI assistant that
built the reader, so a second reading was obtained from models of a different
family. Each figure went to the second reader in a new conversation with the
written stage definitions and nothing else: no key, no notes and no reader
output (`scripts/second_annotator.py`). Qwen read 40 figures before reaching
its daily limit and ChatGPT read the remaining 38; one figure returned no
answer in three attempts. The readings are pooled below and kept apart in the
evidence files.

| Second reader | Figures | Stage values | Agreed with the key |
|---------------|--------:|-------------:|--------------------:|
| Qwen | 40 | 153 | 135 (88%) |
| ChatGPT | 38 | 148 | 140 (95%) |
| Both | 78 | 301 | 275 (91%) |

Each of the 26 disagreements was settled by looking at the image, and none
showed a number in the key that the figure contradicts. Ten were the second
reader's errors. In two figures Qwen reported counts that appear nowhere in the
image, 145, 100 and 98 for a diagram that prints 67, 60 and 60; in one it
answered nothing although the upload had succeeded; and ChatGPT once added
educators and students into a single total. The other sixteen are cases the
definitions do not settle, and they recur in four forms: a top box that names a
cohort without saying it was screened, a flow that ends at an assessment or
follow-up rather than a stage labelled analysed, a cluster trial that
randomises centres and counts people, and repeated analysis rows, where the
definition's "first-listed analysis" gives 224 and the key took the final row,
213. Those four forms, not misread numbers, are where the key needs a firmer
rule.

Setting the sixteen aside as unscored moves the reader's held-out result from
61 of 69 to 59 of 67, with the text method right on 2 in both, and the second
development set from 50 of 53 to 49 of 52. The conclusion of Section 6.14.4
does not change. The result is still reported on the original key, because that
key was committed before the reader saw the figures.

Two limits apply. The disagreements were settled by the annotator who wrote the
key, so the adjudication is not independent; every decision is listed with its
reason in `thesis/evidence/flow_diagrams/adjudication.json`, 26 entries a
reviewer can check against the images. And the second reader is itself a
model, one that invented plausible counts for 2 of the 78 figures, so agreement
with it is evidence about the key rather than a substitute for a human check.
