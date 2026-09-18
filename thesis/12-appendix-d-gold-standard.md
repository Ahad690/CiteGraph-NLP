# Appendix D — Gold Standard Annotations

The complete annotated set used in Chapter 6. Each label was assigned by
reading the abstract retrieved through the same providers the pipeline
uses; the supporting sentence is quoted so every label is auditable.

`n_eff` is the total number of human subjects the paper's primary analysis
rests on, as stated in the abstract. A dash means no human study
population is stated and the correct behaviour is to extract nothing.

## D.1 Summary

| # | DOI | Design | Gold n_eff | Predicted | Match |
|--:|-----|--------|-----------:|----------:|:-----:|
| 1 | `10.1056/nejmoa2034577` | rct | 43548 | 43548 | ok |
| 2 | `10.1056/nejmoa2035389` | rct | 30420 | 30420 | ok |
| 3 | `10.1056/nejmoa1911303` | rct | 4744 | 4744 | ok |
| 4 | `10.1056/nejmoa1812389` | rct | 17160 | 17160 | ok |
| 5 | `10.1016/s0140-6736(20)31604-4` | rct | 1077 | 1077 | ok |
| 6 | `10.1056/nejmoa2002032` | cohort | 1099 | 1099 | ok |
| 7 | `10.1016/s0140-6736(20)30183-5` | case_series | 41 | 41 | ok |
| 8 | `10.1001/jama.2020.1585` | case_series | 138 | 36 | **miss** |
| 9 | `10.1056/nejmoa2001316` | epidemiological | 425 | 425 | ok |
| 10 | `10.1016/s2213-2600(20)30079-5` | cohort | 52 | 52 | ok |
| 11 | `10.1016/s1473-3099(20)30243-7` | modelling | 1334 | 1334 | ok |
| 12 | `10.1056/nejmoa2001017` | virus_characterisation | — | — | ok |
| 13 | `10.1038/s41586-020-2012-7` | virus_characterisation | — | — | ok |
| 14 | `10.1136/bmj.m1328` | systematic_review | — | 27 | **miss** |
| 15 | `10.1038/s41577-020-0311-8` | review | — | — | ok |
| 16 | `10.1164/rccm.201908-1581st` | guideline | — | — | ok |
| 17 | `10.1056/nejmra2026131` | review | — | — | ok |
| 18 | `10.1038/s41586-021-03819-2` | computational | — | — | ok |
| 19 | `10.1038/nature14539` | review | — | — | ok |
| 20 | `10.1145/3065386` | computational | — | — | ok |

## D.2 Annotations with supporting evidence

### D.2.1 `10.1056/nejmoa2034577`

- **Design:** rct
- **Gold n_eff:** 43548
- **Gold semantic type:** TOTAL_RANDOMIZED
- **Supporting evidence:** A total of 43,548 participants underwent randomization, of whom 43,448 received injections.

### D.2.2 `10.1056/nejmoa2035389`

- **Design:** rct
- **Gold n_eff:** 30420
- **Gold semantic type:** TOTAL_ENROLLED
- **Supporting evidence:** The trial enrolled 30,420 volunteers who were randomly assigned in a 1:1 ratio.

### D.2.3 `10.1056/nejmoa1911303`

- **Design:** rct
- **Gold n_eff:** 4744
- **Gold semantic type:** TOTAL_RANDOMIZED
- **Supporting evidence:** we randomly assigned 4744 patients with New York Heart Association class II, III, or IV heart failure

### D.2.4 `10.1056/nejmoa1812389`

- **Design:** rct
- **Gold n_eff:** 17160
- **Gold semantic type:** TOTAL_ANALYZED
- **Supporting evidence:** We evaluated 17,160 patients, including 10,186 without atherosclerotic cardiovascular disease.

### D.2.5 `10.1016/s0140-6736(20)31604-4`

- **Design:** rct
- **Gold n_eff:** 1077
- **Gold semantic type:** TOTAL_ENROLLED
- **Supporting evidence:** 1077 participants were enrolled and assigned to receive either ChAdOx1 nCoV-19 (n=543) or MenACWY (n=534)

### D.2.6 `10.1056/nejmoa2002032`

- **Design:** cohort
- **Gold n_eff:** 1099
- **Gold semantic type:** TOTAL_ANALYZED
- **Supporting evidence:** We extracted data regarding 1099 patients with laboratory-confirmed Covid-19 from 552 hospitals.

### D.2.7 `10.1016/s0140-6736(20)30183-5`

- **Design:** case_series
- **Gold n_eff:** 41
- **Gold semantic type:** TOTAL_ANALYZED
- **Supporting evidence:** By Jan 2, 2020, 41 admitted hospital patients had been identified as having laboratory-confirmed 2019-nCoV infection.

### D.2.8 `10.1001/jama.2020.1585`

- **Design:** case_series
- **Gold n_eff:** 138
- **Gold semantic type:** TOTAL_ANALYZED
- **Supporting evidence:** Retrospective, single-center case series of the 138 consecutive hospitalized patients with confirmed NCIP.

### D.2.9 `10.1056/nejmoa2001316`

- **Design:** epidemiological
- **Gold n_eff:** 425
- **Gold semantic type:** TOTAL_ANALYZED
- **Supporting evidence:** We analyzed data on the first 425 confirmed cases in Wuhan.

### D.2.10 `10.1016/s2213-2600(20)30079-5`

- **Design:** cohort
- **Gold n_eff:** 52
- **Gold semantic type:** TOTAL_ENROLLED
- **Supporting evidence:** we enrolled 52 critically ill adult patients with SARS-CoV-2 pneumonia.

### D.2.11 `10.1016/s1473-3099(20)30243-7`

- **Design:** modelling
- **Gold n_eff:** 1334
- **Gold semantic type:** SAMPLE_SIZE_GENERIC
- **Supporting evidence:** We also estimated the case fatality ratio from individual line-list data on 1334 cases identified outside of mainland China.

### D.2.12 `10.1056/nejmoa2001017`

- **Design:** virus_characterisation
- **Gold n_eff:** none (negative case)
- **Gold semantic type:** n/a
- **Supporting evidence:** Abstract describes isolation of a novel betacoronavirus; no study population size is stated.

### D.2.13 `10.1038/s41586-020-2012-7`

- **Design:** virus_characterisation
- **Gold n_eff:** none (negative case)
- **Gold semantic type:** n/a
- **Supporting evidence:** HARD NEGATIVE: '2,794 laboratory-confirmed infections including 80 deaths' is an epidemic tally, not this study's sample.

### D.2.14 `10.1136/bmj.m1328`

- **Design:** systematic_review
- **Gold n_eff:** none (negative case)
- **Gold semantic type:** n/a
- **Supporting evidence:** HARD NEGATIVE: a systematic review of prediction models; its units are studies, not patients.

### D.2.15 `10.1038/s41577-020-0311-8`

- **Design:** review
- **Gold n_eff:** none (negative case)
- **Gold semantic type:** n/a
- **Supporting evidence:** Narrative review of COVID-19 immunology; no study population.

### D.2.16 `10.1164/rccm.201908-1581st`

- **Design:** guideline
- **Gold n_eff:** none (negative case)
- **Gold semantic type:** n/a
- **Supporting evidence:** Clinical practice guideline; no study population.

### D.2.17 `10.1056/nejmra2026131`

- **Design:** review
- **Gold n_eff:** none (negative case)
- **Gold semantic type:** n/a
- **Supporting evidence:** Review article on cytokine storm; no study population.

### D.2.18 `10.1038/s41586-021-03819-2`

- **Design:** computational
- **Gold n_eff:** none (negative case)
- **Gold semantic type:** n/a
- **Supporting evidence:** HARD NEGATIVE: protein-structure prediction; CASP14 target counts are not human subjects.

### D.2.19 `10.1038/nature14539`

- **Design:** review
- **Gold n_eff:** none (negative case)
- **Gold semantic type:** n/a
- **Supporting evidence:** Review of deep learning; no study population.

### D.2.20 `10.1145/3065386`

- **Design:** computational
- **Gold n_eff:** none (negative case)
- **Gold semantic type:** n/a
- **Supporting evidence:** HARD NEGATIVE: '1.2 million high-resolution images' is a dataset size, not a human study population.
