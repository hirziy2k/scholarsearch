# Scoping Review Protocol v7.6 — Flowcharts (Mermaid source)

## Fig 1 — Protocol Overview
```mermaid
flowchart TD
  A["1 OSF REGISTRATION (Day 0/1)<br/>Pre-register v7.6 BEFORE any search | DOI | PC-05"] --> B
  B["2 QUESTION + PCC + ELIGIBILITY<br/>DED/dry-eye x night-driving x drivers | E1-E9"] --> C
  C["3 SEARCH (S1 v1.2)<br/>8 DBs: PubMed Embase Scopus WoS CINAHL TRID Cochrane VisionCite + grey lit"] --> D
  D["4 MENDELEY MASTER LIBRARY<br/>01_Search > 02_Grey > 03_Deduplicated (PCR-03)"] --> E
  E["5 STUDY SELECTION (dual)<br/>INCLUDE/EXCLUDE/UNCERTAIN | 10% kappa gate + final kappa (PC-13)"] --> F
  F["6 FULL-TEXT + E1-E9 + E6/E7<br/>Dual full-text | E6 dupl vs E7 companion | arbiter"] --> G
  G["7 CHARTING<br/>2 pilot + 3 calibration (PC-14) | single + 30% spot-check (CR-03)"] --> H
  H["8 SYNTHESIS + PRISMA-ScR REPORT<br/>Numeric | evidence map | thematic | no double-count"]
```

## Fig 2 — PRISMA-ScR Selection Flow (template)
```mermaid
flowchart TD
  A["IDENTIFICATION — Records identified<br/>Databases n=___ | Grey n=___ | Other n=___"] --> B
  B["IDENTIFICATION — Deduplicated<br/>Removed n=___ | Mendeley 03_Deduplicated = master | To screen n=___"] --> C
  C["SCREENING — Title/abstract (dual Rayyan/Covidence)<br/>Screened n=___ > Excluded n=___ | INCLUDE+UNCERTAIN n=___"] --> D
  D["ELIGIBILITY — Full-text assessed (dual)<br/>Retrieved n=___ (E8 = notretrievable) | Assessed n=___"] --> E
  E["ELIGIBILITY — Excluded E1-E9<br/>E1 no DED | E2 no night-driving | E3 pop | E4 design | E5 abstr | E6 dupl | E7 companion | E8 | E9"] --> F
  F["INCLUDED — Studies vs reports<br/>Studies n=___ | Reports n=___ | Companions flagged not counted (WPJ primary; thesis companion)"]
```

## Fig 3 — Operational Screening Workflow (§12/16/17)
```mermaid
flowchart TD
  A["A IMPORT + TAG (Mendeley)<br/>01_Search per-DB + 02_Grey | tag type"] --> B
  B["B DEDUP auto + manual<br/>Auto-merge | manual authors/N/dates/site | log pairs"] --> C
  C["C EXPORT TO RAYYAN/COVIDENCE<br/>Master 03_Deduplicated > screening tool"] --> D
  D{"D CALIBRATION GATE 10% kappa<br/>OK? No-retrain / Yes-proceed"} --> E
  E["E DUAL TITLE/ABSTRACT<br/>INCLUDE/EXCLUDE/UNCERTAIN | disagree>discuss>3rd"] --> F
  F["F FULL-TEXT RETRIEVAL + DUAL ASSESS<br/>E8 if unretrievable | dual + E1-E9"] --> G
  G["G E6 vs E7 (CR-06)<br/>Identical>E6 | same-data diff-analysis>E7 | borderline>arbiter"] --> H
  H["H SELF-REVIEW SAFEGUARDS (CR-07)<br/>Thesis/WPJ/Woi x2: identical criteria + 2nd verify + disclose"] --> I
  I["I CHART + FILE<br/>04_Screened E1-E9 > 05_Charted Primary vs Companion > 06_Manuscript"]
```

PNGs: `fig1_protocol_overview.png`, `fig2_prisma_scr_flow.png`, `fig3_operational_workflow.png`
Generator: `generate_flowcharts.py` (matplotlib, no external deps)
