# SCOPING REVIEW OPERATIONS MANUAL

## Dry Eye Disease, Dry-Eye Symptoms, and Night-Driving Difficulty Among Drivers

**Protocol Reference:** Scoping_Review_Protocol_v7.6.md (v7.6 S1 v1.2 Malay arm; CR-02 to CR-07)
**Version:** 2.0
**Date:** September 2026
**Status:** Pre-registration — DO NOT EXECUTE SEARCHES until OSF DOI issued (PC-05)

---

### Purpose

This manual defines the operational workflow for executing every phase of the scoping review — from search execution through screening, data charting, synthesis, and final reporting. It separates **infrastructure execution** from **methodological protocol**. The protocol dictates the science; this manual dictates the infrastructure.

**This document is not a substitute for the protocol.** All methodological decisions (eligibility criteria, search strategy, screening process, synthesis approach) are defined in `Scoping_Review_Protocol_v7.6.md` (S1 v1.2 Malay arm; CR-02 to CR-07).

### Scope of This Manual

| Phase | Protocol Reference | Manual Section |
|---|---|---|
| Search execution | Protocol §10, §11 | §1–§9, Appendix A, Appendix B |
| Screening setup | Protocol §12 | §10 |
| Title/abstract screening | Protocol §12 | §11 |
| Full-text screening | Protocol §12 | §12 |
| Grey-literature screening | Protocol §12, §8.4 | §13 |
| Data charting/extraction | Protocol §13 | §14 |
| Evidence/provenance capture | Protocol §9, §17 | §15 |
| Synthesis and mapping | Protocol §14 | §16 |
| Deviations and amendments | Protocol §21 | §17 |
| Final reporting and audit trail | Protocol §14, §15 | §18 |
| Stopping rules and quality gates | Protocol §12, §13, §15.1 | §19 |

---

## 1. Directory Architecture

```
research/
└── scoping-review/
    ├── searches/
    │   ├── raw/                    # Immutable vault — only untouched original exports
    │   │   ├── pubmed/
    │   │   ├── embase/
    │   │   ├── scopus/
    │   │   ├── web-of-science/
    │   │   ├── cinahl/
    │   │   ├── trid/
    │   │   ├── cochrane/
    │   │   └── visioncite/
    │   ├── manifests/              # Metadata ledger — one manifest per export
    │   ├── processed/              # Staging ground — deduplicated records ready for screening
    │   └── logs/                   # Ingestion logs — timestamps, errors, QC results
    ├── screening/                  # Rayyan/Covidence export files
    │   ├── title-abstract/         # T/A screening decisions + kappa outputs
    │   ├── full-text/              # Full-text screening decisions + exclusion codes
    │   └── logs/                   # Screening audit trail (calibration, conflicts, resolutions)
    ├── extraction/                 # Completed charting CSVs
    │   ├── charting-form/          # Template + version history
    │   ├── calibration/            # Pilot + calibration outputs
    │   └── logs/                   # Charting audit trail (discrepancies, clarifications, arbiter decisions)
    └── reports/                    # Final tables, figures, PRISMA flow
        ├── prisma-scR/             # PRISMA-ScR flow diagram source
        ├── tables/                 # Evidence map, gap matrix, characteristics tables
        └── supplementary/          # Search strategies, excluded-studies table, PRISMA-S checklist
```

### Rules

| Directory | Rule |
|---|---|
| `raw/` | **IMMUTABLE.** Never modify, overwrite, or delete files after download. |
| `manifests/` | **APPEND-ONLY.** New manifests are added; existing manifests are never edited. |
| `processed/` | **DERIVED.** Files here are generated from raw + manifest. Original source traceable. |
| `logs/` | **APPEND-ONLY.** Ingestion/screening/charting events are recorded chronologically. |
| `screening/` | **VERSIONED.** Each screening round produces a dated export; prior exports are retained. |
| `extraction/` | **VERSIONED.** Charting form versions are preserved; each calibration round is logged. |
| `reports/` | **DERIVED.** All outputs traceable to extraction + screening logs. |

---

## 2. RemoteXs Extraction — Standard Operating Procedure

### 2.1 Access Route

```
UKM PTSL → eResources@PTSL → RemoteXs → [Database]
```

**Authentication:** Interactive, user-executed. No automated login. No credential storage.

### 2.2 Pre-Export Checklist

Before each database search:

- [ ] Navigate to eResources@PTSL via RemoteXs (EXCEPTION (P-04): PubMed/MEDLINE is free access via NCBI — no RemoteXs required)
- [ ] Confirm authenticated session is active (where RemoteXs route applies)
- [ ] Open target database
- [ ] Verify search interface is accessible
- [ ] Confirm OSF DOI issued — DO NOT SEARCH if no DOI (PC-05 gate)
- [ ] Confirm database access verified (PC-07); if inaccessible record as not-searched
- [ ] Enter approved search string from Supplement S1 v1.2 ONLY — Protocol §11 blocks are descriptive and MUST NOT be executed (P-04/PCR-01), including controlled vocab per PC-02/PC-03
- [ ] Apply only protocol-approved filters/limits — NO date limits (PC-04); NO language or Human filters at search — language enforced at screening via E9 (P-05)
- [ ] Record the **exact search string** used (copy verbatim) + Search Strategy Version (S1 v1.2)
- [ ] Record the **total result count** displayed by the database
- [ ] Record the **date and time** of search execution (must be ≥ OSF registration date)

### 2.3 Export Procedure

#### Complete Export Principle

**EXPORT THE FULL SEARCH RESULT SET.**

Do not:
- Pre-screen records during export
- Remove "obviously irrelevant" records
- Export only highly cited papers
- Export only apparently eligible studies
- Export only records with full text

Formal eligibility determination occurs during screening (Protocol Section 12).

#### Handling Export Limits

| Database | Typical Export Limit | Workaround |
|---|---|---|
| Scopus | 1000 records per export | Sort by year; export in batches (e.g., 2010–2015, 2016–2020, 2021–2026) |
| Web of Science | 1000 records per export | Use "Create Citation Report" or batch by year |
| Embase | 500 records per export | Export in batches by year or relevance rank |
| PubMed | 10,000 records (NBIB format) | Usually sufficient; use "Send to" → "File" |
| CINAHL | 500 records per export | Export in batches by year |
| TRID | Varies | Export all available; document if partial |
| Cochrane (CENTRAL/CDSR) | Varies by Wiley export | Export as RIS; batch if needed; document if partial |
| VisionCite | Unknown | Document limit if encountered |

**If partial export is required:**

1. Record: total results, export limit, number exported, number not exported
2. Document the batch strategy (e.g., "Exported 2010–2015: 487 records; 2016–2020: 512 records; 2021–2026: 301 records")
3. Preserve all batch files in `raw/[database]/`
4. Generate one manifest per batch, or one manifest covering all batches (note: multi-batch)

### 2.4 Post-Export Checklist

- [ ] Export file saved to `raw/[database]/`
- [ ] Filename follows naming convention (see Section 3)
- [ ] Manifest generated (see Section 3)
- [ ] Export count matches expected count (or discrepancy documented)
- [ ] Raw file is unmodified

---

## 3. Provenance Manifest Schema

Every manual export requires a manifest. The manifest is the metadata ledger linking each raw export to its execution context.

### 3.1 Manifest Naming Convention

```
[database]_[YYYY-MM-DD]_[search-version].manifest.md
```

Examples:
```
pubmed_2026-09-03_v1.manifest.md
scopus_2026-09-03_v1-batch1.manifest.md
scopus_2026-09-03_v1-batch2.manifest.md
```

### 3.2 Manifest Template

```markdown
# SEARCH MANIFEST

## Identification

| Field | Value |
|---|---|
| Database | [e.g., PubMed/MEDLINE] |
| Provider/Platform | [e.g., PubMed via NCBI] |
| Access Route | UKM PTSL → eResources@PTSL → RemoteXs → [Database] |
| Protocol Version | 7.6 |
| Search Strategy ID | [e.g., Section 11.4 Master + S1 v1.2 PubMed] |
| Search Strategy Version | [e.g., S1 v1.2, PRESS date + initials; Malay delta verification: reviewer initials + date] |
| Model Assistance (P-09) | [pure-code / model-assisted: mistral:7b-instruct ID 6577803aa9a0 + prompt version; prompt file + per-batch diff retained in logs/] |
| Review Stage (PC-15/PC-17) | [Primary search / Update search N] |

## Execution

| Field | Value |
|---|---|
| Search Date | [YYYY-MM-DD] |
| Search Time | [HH:MM] |
| Time Zone | [e.g., GMT+8] |
| Executed By | [Name/initials — Lead Reviewer executes searches] |

## Search Parameters

| Field | Value |
|---|---|
| Exact Search String | [Copy verbatim from database] |
| Fields Searched | [e.g., Title/Abstract/MeSH, Emtree, MH headings] |
| Filters/Limits Applied | [e.g., none — NO date limits per PC-04; NO language/Human filters at search; language enforced at screening via E9 (P-05)] |
| Date Range (Applied Limits) | [None — record Database Coverage + Execution Date] |
| Database Coverage | [e.g., MEDLINE 1946–present; Embase 1947–present] |
| Language Limits | [e.g., None at search — English + Malay enforced at screening via E9 (P-05)] |

## Results

| Field | Value |
|---|---|
| Total Results Displayed | [Number] |
| Records Exported | [Number] |
| Export Complete? | YES / NO (if NO, explain) |
| Export Limitation | [e.g., Scopus 1000-record cap] |
| Batch Strategy | [e.g., Sorted by year; 3 batches] |

## Export File

| Field | Value |
|---|---|
| Filename | [e.g., pubmed_ded_nightdriving_2026-09-03.nbib] |
| Format | [e.g., RIS, CSV, NBIB, BibTeX] |
| File Size | [e.g., 2.3 MB] |
| Record Count (verified) | [Number — count records in file] |
| SHA-256 Hash | [MANDATORY (P-11) — integrity verification required] |

## Notes

[Any additional notes, e.g., "Search returned 847 results; Scopus cap required 2-batch export"]

---

**Manifest generated by:** [Name/initials]
**Manifest date:** [YYYY-MM-DD]
```

### 3.3 Manifest for Multi-Batch Exports

If a database requires batched export (e.g., Scopus with 1000-record cap), generate one manifest per batch, OR one combined manifest covering all batches. If combined, document each batch separately within the same manifest:

```markdown
## Batch Details

| Batch | Year Range | Records Exported | Filename |
|---|---|---|---|
| 1 | 2000–2015 | 487 | scopus_2000-2015.ris |
| 2 | 2016–2020 | 512 | scopus_2016-2020.ris |
| 3 | 2021–2026 | 301 | scopus_2021-2026.ris |
| **Total** | | **1300** | |

**Total results displayed:** 1300
**Export limit per batch:** 1000
**All records exported:** YES
```

---

## 4. File Ingestion — Local Pipeline Handoff

### 4.1 Ingestion Trigger

When a new RIS/CSV file appears in `raw/[database]/`:

1. **Detect** — file exists in `raw/` directory
2. **Validate** — file format is correct (RIS, CSV, NBIB, BibTeX)
3. **Manifest check** — corresponding manifest exists in `manifests/`
4. **Record count** — count records in file; compare to manifest
5. **Hash** — calculate SHA-256 hash of raw file (integrity verification)
6. **Parse** — extract metadata fields (author, year, title, DOI, abstract, database source)
7. **Normalize** — standardize metadata fields across databases
8. **Tag** — attach database provenance tag to each record
9. **Store** — save processed records to `processed/`
10. **Log** — record ingestion event in `logs/`

### 4.2 Ingestion Log Entry

```markdown
## Ingestion Log

| Field | Value |
|---|---|
| Timestamp | [YYYY-MM-DD HH:MM:SS] |
| Source File | [filename] |
| Database | [database name] |
| Manifest | [manifest filename] |
| Records Parsed | [number] |
| Records Valid | [number] |
| Records Malformed | [number] |
| Hash (SHA-256) | [hash] |
| Status | SUCCESS / PARTIAL / FAILED |
| Errors | [if any] |
```

### 4.3 Deduplication

Deduplication occurs **after all database exports have been ingested.**

**Hierarchical matching strategy:**

| Priority | Field | Match Criterion |
|---|---|---|
| 1 | DOI | Exact match (case-insensitive) |
| 2 | PMID | Exact match |
| 3 | Database ID | Exact match (Scopus EID, WoS accession number, etc.) |
| 4 | Title + Author + Year | Normalized title (lowercase, punctuation removed) + first author surname + publication year |
| 5 | Title similarity | Fuzzy match (Levenshtein distance > 90%) — manual review required. Normalisation/tokeniser (P-10): lowercase + punctuation-strip + whitespace-collapse; tokeniser/disclosure logged in methods; threshold + version recorded per dedup run |

**Output:** Deduplicated record set in `processed/` with:
- Original database provenance preserved
- Duplicate-group ID assigned
- Canonical record identified
- Duplicate records flagged (not deleted)

### 4.4 Mendeley Import

After deduplication:

1. Export processed records from `processed/` to RIS format
2. Import into Mendeley under `SR_DED_NightDriving/01_Search_Results/[database]/`
3. Run Mendeley's built-in duplicate detection (second-pass verification)
4. Proceed to screening workflow (Protocol Section 12)

---

## 5. Search Update / Re-Run Procedure

If the same database is searched again (e.g., monthly update):

1. **Do NOT overwrite** the previous export
2. Create new export file with new date: `[database]_[YYYY-MM-DD]_[version].ris`
3. Generate new manifest: `[database]_[YYYY-MM-DD]_[version].manifest.md`
4. Ingest as new batch alongside previous exports
5. Deduplicate across all exports (including previous)
6. Record search update in PRISMA-ScR flow diagram

---

## 6. Interrupted Export Recovery

If manual export is interrupted mid-process:

1. **Document** — record what was exported, what was not
2. **Save partial export** — keep the incomplete file in `raw/` with `_partial` suffix (immutable; never overwrite or delete)
3. **Resume** — continue export in next session into a `_complete` file
4. **Merge (logged, non-destructive)** — combine parts via scripted concatenation into a `_merged` file; BOTH source parts are retained in `raw/` (CR-04 audit amendment 2026-09-03: merging in place into a single file would violate the immutable-vault rule)
5. **Update manifest** — document the interruption and recovery: record filenames + SHA-256 of the `_partial`, `_complete`, and `_merged` files plus the merge method

Example:
```
scopus_2026-09-03_v1-batch1_partial.ris  (interrupted — RETAINED)
scopus_2026-09-03_v1-batch1_complete.ris (resumed and completed — RETAINED)
scopus_2026-09-03_v1-batch1_merged.ris   (derived merged file — logged in manifest)
```

---

## 7. Quality Control Checks

### 7.1 Pre-Ingestion QC

| Check | Action | Pass Criteria |
|---|---|---|
| File exists | Verify `raw/[database]/[filename]` exists | File present |
| Format valid | Open file; verify RIS/CSV structure | Parseable without errors |
| Record count | Count records in file | Matches manifest (±0) |
| Manifest exists | Verify corresponding manifest in `manifests/` | Manifest present |
| Hash match | Calculate SHA-256; compare to manifest (if recorded) | Hash matches |

### 7.2 Post-Ingestion QC

| Check | Action | Pass Criteria |
|---|---|---|
| All records parsed | Count records in `processed/` | Matches raw count |
| Metadata complete | Check required fields (author, year, title, DOI) | >95% complete |
| Provenance tagged | Verify database source tag on every record | 100% tagged |
| No data loss | Compare raw vs processed record count | Count matches |

### 7.3 Export Completeness QC

| Check | Action | Pass Criteria |
|---|---|---|
| Result count vs export count | Compare database display count to export count | Match (or discrepancy documented) |
| Batch completeness | Verify all batches exported | All batches present |
| No silent truncation | Check last record in file is complete | Final record has all fields |

---

## 8. Security Boundaries

### Absolute Rules

| Rule | Enforcement |
|---|---|
| No automated database login | Authentication is interactive, user-executed |
| No credential storage | Credentials never enter project files, code, or logs |
| No session token extraction | Cookies/tokens are never captured or transferred |
| No scraping | Databases are accessed only through official interfaces |
| No bot-detection evasion | Respect provider rate limits and anti-automation controls |
| No protocol modification | Directory structure and manifests do not alter the review methodology |

### Permitted Automation

| Permitted | Context |
|---|---|
| Local file detection | Monitoring `raw/` for new files |
| RIS/CSV parsing | Extracting metadata from downloaded files |
| Deduplication | Identifying duplicate records across databases |
| Hash calculation | Verifying file integrity |
| Manifest generation | Creating structured metadata for exports |
| Ingestion logging | Recording processing events |

### Prohibited Automation

| Prohibited | Reason |
|---|---|
| Direct database access | Violates provider terms of service |
| Cookie extraction | Violates security framework |
| Session hijacking | Violates authentication boundary |
| Bulk PDF download | Violates provider restrictions |
| CAPTCHA bypass | Violates anti-automation controls |
| LLM/AI screening, eligibility, charting, synthesis | Protocol §15.1 (PC-12) — human judgement only; deterministic parsing/dedup/hashing/DOI-batch only; where LLM assists parsing, versioned prompt file + per-batch diff retained, manifest Model Assistance field completed (P-09) |

---

## 9. Checklist — Complete Search Execution

### Per Database

- [ ] Confirm OSF DOI issued (PC-05 gate) + database access verified per §10.1.1 (PC-07); record accessible/inaccessible + reason
- [ ] Navigate to database via RemoteXs
- [ ] Execute approved search string (Supplement S1 v1.2 ONLY incl. controlled vocab — Protocol §11 MUST NOT be executed per P-04/PCR-01)
- [ ] Apply protocol-approved filters (NO date limits per PC-04)
- [ ] Record exact search string + Strategy Version (S1 v1.2)
- [ ] Record total result count
- [ ] Record date/time (must be ≥ OSF registration date)
- [ ] Export complete result set (or document batch strategy)
- [ ] Save to `raw/[database]/`
- [ ] Generate manifest in `manifests/`
- [ ] Verify export count matches result count
- [ ] Verify raw file is unmodified

### After All Databases

- [ ] All 8 databases searched (or explicitly recorded as not-searched with reason per §10.1.1)
- [ ] Access verification log complete (Days 1–5 outcomes per database)
- [ ] All grey-literature sources searched with URL + exact syntax + sections + date + hits reviewed (PC-10)
- [ ] Citation chasing completed (backward=all; forward=all via batch DOI; related=top-10 highest-cited with count source + date recorded per CR-07; PC-08)
- [ ] All raw files in `raw/` with manifests
- [ ] All manifests in `manifests/`
- [ ] Ingestion QC passed
- [ ] Deduplication completed
- [ ] Records imported to Mendeley
- [ ] Ready for screening (Protocol Section 12)

---

## 10. Screening Setup and Configuration

*Protocol reference: §12 (Study Selection); §15.1 (AI/Automation Policy)*

This section covers the technical setup for screening before any screening decisions are made.

### 10.1 Platform Selection

Use **Rayyan** (rayyan.ai) or **Covidence** for all screening. The platform must support:

- Dual independent reviewer mode
- Blinding between reviewers (reviewers cannot see each other's decisions)
- Conflict detection and resolution workflow
- Export of screening decisions in CSV format
- Inter-rater reliability calculation (Cohen's kappa)

**Platform decision:** Record the chosen platform in the first screening log entry. Once screening begins, do not switch platforms mid-review.

### 10.2 Rayyan Configuration (if Rayyan selected)

1. **Create project:** Name = `SR_DED_NightDriving_Screening`
2. **Import records:** Upload the deduplicated RIS/CSV from `processed/` (Protocol §12 — after deduplication)
3. **Configure reviewers:**
   - Add Lead Reviewer as administrator
   - Add Second Reviewer as collaborator
   - Enable blinding: both reviewers' decisions hidden until both have screened each record
4. **Define inclusion/exclusion criteria:** Enter the PCC eligibility criteria from Protocol §6 and §8 as Rayyan labels
5. **Set up exclusion reason labels:** Map Protocol §12.2 exclusion codes (E1–E9) as Rayyan labels:
   - `E1_No_DED`
   - `E2_No_NightDriving`
   - `E3_WrongPopulation`
   - `E4_WrongDesign`
   - `E5_InsufficientData`
   - `E6_Duplicate`
   - `E7_CompanionReport`
   - `E8_FullTextUnavailable`
   - `E9_Other`
6. **Enable methodological note field:** For `E9_Other`, require free-text specification

### 10.3 Covidence Configuration (if Covidence selected)

1. **Create review:** Name = `SR_DED_NightDriving`
2. **Import records:** Upload deduplicated records from `processed/`
3. **Configure screening:** Enable title/abstract screening with two independent reviewers
4. **Set exclusion reasons:** Map E1–E9 codes to Covidence exclusion reason fields
5. **Enable full-text screening stage:** Configure as Phase 2 with same dual-reviewer setup

### 10.4 Record Tagging Before Screening

Before screening begins, every record in the screening platform must carry:

| Tag | Purpose | Source |
|---|---|---|
| Database of origin | Provenance tracking | Ingestion pipeline provenance tag |
| Deduplication group ID | Duplicate/companion identification | Deduplication output |
| Companion-report flag | Prevent double-counting (Protocol §17) | Companion-report detection (Protocol §9.3) |
| Publication type | Grey-literature branch tracking (Protocol §15, PRISMA-ScR adaptations) | Metadata extraction |

### 10.5 Screening Directory Structure

```
screening/
├── title-abstract/
│   ├── [platform]_ta_export_[YYYY-MM-DD].csv    # Platform export of T/A decisions
│   ├── ta_calibration_round_[N]_[YYYY-MM-DD].csv # Calibration sample decisions
│   └── ta_kappa_report_[YYYY-MM-DD].txt          # Cohen's kappa output
├── full-text/
│   ├── ft_retrieval_log_[YYYY-MM-DD].csv         # Full-text retrieval attempts
│   ├── ft_screening_export_[YYYY-MM-DD].csv      # Platform export of FT decisions
│   └── ft_exclusion_table_[YYYY-MM-DD].csv       # Excluded studies with E1–E9 codes
├── grey-literature/
│   └── gl_screening_export_[YYYY-MM-DD].csv      # Grey-literature screening decisions
└── logs/
    ├── screening_audit_trail_[YYYY-MM-DD].md     # Chronological screening log
    ├── conflict_resolution_log_[YYYY-MM-DD].md   # Disagreement records
    └── arbiter_decisions_[YYYY-MM-DD].md          # Arbiter rulings
```

---

## 11. Title/Abstract Screening

*Protocol reference: §12.1 (Phase 1: Title and Abstract Screening); §12.2 (Exclusion Reasons); §12.3 (Documentation); §15.1 (AI/Automation Policy — PC-12)*

### 11.1 Pre-Screening Preparation

Before any screening decisions:

1. **Deduplication complete:** All database exports deduplicated per §4.3; deduplicated record set in `processed/`
2. **Mendeley import complete:** Records imported to `03_Deduplicated/` per §4.4
3. **Screening platform configured:** Per §10 (Rayyan or Covidence)
4. **Records tagged:** Database provenance, dedup group ID, companion-report flag, publication type per §10.4
5. **Exclusion codes loaded:** E1–E9 labels per §10.2/10.3
6. **Eligibility criteria accessible:** Both reviewers have Protocol §6 (PCC Framework) and §8 (Eligibility Criteria) open during screening

### 11.2 Calibration Phase

**Purpose:** Establish inter-rater reliability before full screening (Protocol §12.1).

**Step 1: Select calibration sample**

- Draw a **10% random sample** of the deduplicated record set (Protocol §12.1)
- Use a random number generator seeded with a documented seed for reproducibility
- Record the seed, sample size, and selection timestamp in `screening/logs/screening_audit_trail_[YYYY-MM-DD].md`

**Step 2: Independent dual screening of calibration sample**

- Both reviewers independently screen the 10% sample
- Each record receives one decision: **INCLUDE**, **EXCLUDE**, or **UNCERTAIN**
- Blinding is active: reviewers cannot see each other's decisions
- No discussion between reviewers during this phase

**Step 3: Calculate calibration kappa**

- Export both reviewers' decisions from Rayyan/Covidence
- Calculate Cohen's kappa for the calibration sample
- Record kappa value, number of agreements, number of disagreements, and decision distribution in `screening/title-abstract/ta_calibration_round_1_[YYYY-MM-DD].csv`

**Step 4: Calibration gate assessment**

| Kappa Value | Interpretation | Action |
|---|---|---|
| ≥ 0.80 | Strong agreement | Proceed to full screening |
| 0.60–0.79 | Moderate agreement | Discuss disagreements; re-calibrate on 10% new sample; recalculate kappa |
| < 0.60 | Weak agreement | Pause; re-read Protocol §8 together; discuss 10 borderline cases; re-calibrate on 20% new sample; if kappa remains < 0.60, consult arbiter |

**Step 5: Calibration discussion**

- After kappa is calculated, both reviewers discuss ALL disagreements in the calibration sample
- Document calibration discussion outcomes in `screening/logs/screening_audit_trail_[YYYY-MM-DD].md`:
  - Cases where inclusion/exclusion criteria were misapplied
  - Ambiguous eligibility operationalised
  - Clarifications to be applied in full screening
- Update the screening decision guide (if created) with clarified interpretations

**Step 6: Record calibration completion**

- Record: calibration date, sample size, kappa value, number of disagreements, resolution outcomes
- Calibration gate must pass BEFORE full screening begins

### 11.3 Full Title/Abstract Screening

**Phase: Dual independent screening**

1. Both reviewers independently screen ALL remaining records (100% minus calibration sample)
2. Each record receives: **INCLUDE**, **EXCLUDE**, or **UNCERTAIN**
3. Exclusion decisions require an exclusion code (E1–E9 per Protocol §12.2):
   - `E1` — No DED/dry-eye measure
   - `E2` — No night-driving or low-light driving measure
   - `E3` — Wrong population (non-drivers only)
   - `E4` — Wrong study design (review, editorial, commentary, case report)
   - `E5` — Conference abstract without sufficient data (PC-09 four-minima gate)
   - `E6` — Duplicate publication (Protocol §17.1)
   - `E7` — Companion report (Protocol §17.1)
   - `E8` — Full text not retrievable
   - `E9` — Other (specify in free text)
4. `UNCERTAIN` records are carried forward to full-text screening (§14) — do not exclude at T/A stage if there is any doubt
5. Blinding remains active until both reviewers have screened every record

### 11.4 Conflict Detection and Resolution

**After both reviewers complete screening:**

1. **Export decisions** from Rayyan/Covidence to CSV: `screening/title-abstract/ta_export_[YYYY-MM-DD].csv`
   - Columns: Record ID, Author_Year, Title, Reviewer_1_decision, Reviewer_2_decision, Reviewer_1_exclusion_code, Reviewer_2_exclusion_code
2. **Identify conflicts:** Records where Reviewer_1 ≠ Reviewer_2
3. **Conflict resolution process (Protocol §12.1):**
   - **First attempt:** Discussion between reviewers. Both reviewers re-examine the record together against Protocol §8 eligibility criteria. Reach consensus.
   - **If consensus fails:** Third reviewer (arbiter) makes the final decision. Arbiter's decision is binding.
4. **Log all conflicts** in `screening/logs/conflict_resolution_log_[YYYY-MM-DD].md`:

```markdown
## Conflict Resolution Log

| Record ID | Author_Year | R1 Decision | R2 Decision | R1 Code | R2 Code | Resolution | Resolved By | Date |
|---|---|---|---|---|---|---|---|---|
| [ID] | [Author Year] | INCLUDE | EXCLUDE | — | E2 | EXCLUDE (E2) — no night-driving measure in abstract; full text confirms | Arbiter | YYYY-MM-DD |
```

5. **Final screening set:** Records with consensus INCLUDE or consensus EXCLUDE. UNCERTAIN records resolved via full-text screening (§14).

### 11.5 Final Inter-Rater Reliability

**After all conflicts are resolved:**

1. Calculate Cohen's kappa for the ENTIRE title/abstract screening phase (Protocol §12.1, PC-13)
2. Use the resolved decisions (post-conflict-resolution) as the final dataset
3. Report both:
   - **Calibration kappa** (10% sample, pre-discussion)
   - **Final kappa** (full screening, post-resolution)
4. Record in `screening/title-abstract/ta_kappa_report_[YYYY-MM-DD].txt`:
   - Kappa value, 95% CI, number of records, agreement percentage, decision distribution
5. Kappa results are reported in the final manuscript per Protocol §12.3

### 11.6 Screening Audit Trail

Every screening event is logged chronologically in `screening/logs/screening_audit_trail_[YYYY-MM-DD].md`:

```markdown
## Screening Audit Trail — Title/Abstract Phase

| Date | Event | Reviewer(s) | Records | Notes |
|---|---|---|---|---|
| YYYY-MM-DD | Calibration sample selected | Lead | [N] records (10% sample) | Seed: [value] |
| YYYY-MM-DD | Calibration screening completed | Both | [N] records | R1: [N] incl, [N] excl, [N] uncert; R2: [N] incl, [N] excl, [N] uncert |
| YYYY-MM-DD | Calibration kappa calculated | Lead | [N] records | κ = [value] |
| YYYY-MM-DD | Calibration gate passed | Both | — | κ ≥ 0.80; proceeding to full screening |
| YYYY-MM-DD | Full screening round 1 started | Both | [N] remaining records | Blinding active |
| YYYY-MM-DD | Full screening round 1 completed | Both | [N] records | R1: [N] incl, [N] excl, [N] uncert; R2: [N] incl, [N] excl, [N] uncert |
| YYYY-MM-DD | Conflicts identified | Lead | [N] conflicts | [N] INCLUDE/EXCLUDE disagreements |
| YYYY-MM-DD | Conflict resolution completed | Both + Arbiter | [N] conflicts | [N] by discussion, [N] by arbiter |
| YYYY-MM-DD | Final kappa calculated | Lead | [N] total records | κ = [value] |
```

### 11.7 Self-Review Safeguards for T/A Screening

*Protocol reference: §17.5 (Self-Review Safeguards); CR-07*

Because the Lead Reviewer is an author of the thesis (Wan Din 2026), the draft manuscript (WPJ), and co-author of Woi et al. (2025a) and Woi et al. (2025b):

1. These reports are screened using the **exact same criteria** as all other records (Protocol §17.5 Rule 1)
2. The Second Reviewer **independently** screens these reports and **verifies all screening decisions** on them (Protocol §17.5 Rule 2)
3. Any disagreement on these reports goes to the **arbiter**, not to Lead Reviewer discretion (Protocol §17.5 Rule 6)
4. The relationship between these reports is **explicitly disclosed** in the final manuscript (Protocol §17.5 Rule 3)

### 11.8 PRISMA-ScR Flow Update (T/A Phase)

After T/A screening is complete, update the PRISMA-ScR flow diagram:

| Flow Node | Count | Source |
|---|---|---|
| Records identified from database searching | [N] | Sum of all database exports |
| Records identified from grey-literature searching | [N] | Sum of all grey-literature searches |
| Records removed before screening (duplicates) | [N] | Deduplication output (§4.3) |
| Records screened (title/abstract) | [N] | Post-dedup record count |
| Records excluded (title/abstract) | [N] | Consensus EXCLUDE decisions |
| Records per exclusion code (E1–E9) | [N] per code | Exclusion code tallies |

Store flow diagram source in `reports/prisma-scR/`.

---

## 12. Full-Text Screening

*Protocol reference: §12.1 (Phase 2: Full-Text Screening); §12.2 (Exclusion Reasons); §12.3 (Documentation)*

### 12.1 Full-Text Retrieval

**Step 1: Identify records requiring full text**

All records with a final decision of **INCLUDE** or **UNCERTAIN** from T/A screening proceed to full-text retrieval.

**Step 2: Retrieval process**

For each record:

1. Check DOI availability in the record metadata
2. Attempt retrieval via:
   - Institutional access (UKM PTSL / eResources@PTSL)
   - RemoteXs (if database access route applies)
   - Open access repositories (PubMed Central, Unpaywall, institutional repositories)
   - Author contact (if other methods fail — up to two email attempts per Protocol §10.3)
3. Record retrieval outcome

**Step 3: Retrieval log**

Log all retrieval attempts in `screening/full-text/ft_retrieval_log_[YYYY-MM-DD].csv`:

| Field | Value |
|---|---|
| Record ID | [Sequential ID] |
| Author_Year | [First author, year] |
| DOI | [DOI if available] |
| Retrieval method | [Institutional / Open access / Author contact / Interlibrary loan] |
| Retrieval successful? | YES / NO |
| Full-text file location | [File path or "not retrievable"] |
| Number of retrieval attempts | [N] |
| Date of final attempt | [YYYY-MM-DD] |

**Step 4: Handling non-retrievable full texts**

If full text cannot be retrieved after two attempts (including author contact):

- Assign exclusion code **E8** (Full text not retrievable — Protocol §12.2)
- Document the retrieval attempts in the exclusion table
- Report in the PRISMA-ScR flow diagram under "Reports assessed for eligibility" → "Reports excluded" with E8 as the reason
- Report in the final manuscript limitations (Protocol §20)

### 12.2 Full-Text Assessment

**Dual independent assessment:**

1. Both reviewers independently assess all retrieved full texts against Protocol §8 eligibility criteria
2. Each record receives a final decision: **INCLUDE** or **EXCLUDE**
3. **EXCLUDE** decisions require an exclusion code (E1–E9 per Protocol §12.2)
4. **No discussion** between reviewers until both have assessed all records

**Key eligibility checks at full-text stage (Protocol §8):**

| Check | Criterion | Protocol Reference |
|---|---|---|
| Population | Licensed drivers who drive at night or in low-light conditions | §8.2 (Population) |
| Concept — DED | DED diagnosis, dry-eye symptoms, subclinical dry-eye, tear film instability, or visual function in DED context | §8.2 (Concept — DED/Dry-Eye) |
| Concept — Night driving | Night-driving difficulty by any method (self-report, simulator, on-road, naturalistic, crash data) | §8.2 (Concept — Night-Driving) |
| Study design | Original research (cross-sectional, cohort, case-control, RCT, quasi-experimental, mixed-methods, simulator, on-road, naturalistic) | §8.1 |
| Language | English or Malay | §8.1 (CR-01) |
| Data availability | Reports original data (not a review, editorial, commentary) | §8.3 |

### 12.3 Exclusion Documentation

**Exclusion table:**

Produce a table of all excluded studies with reasons in `screening/full-text/ft_exclusion_table_[YYYY-MM-DD].csv`:

| Field | Value |
|---|---|
| Record ID | [Sequential ID] |
| Author_Year | [First author, year] |
| Journal/Source | [Journal name or source] |
| Exclusion code | [E1–E9] |
| Exclusion reason (free text) | [Specific reason, e.g., "Study assessed general driving performance without night/low-light conditions"] |
| Screened by | [Both / Arbiter] |

This table is reported as supplementary material per Protocol §12.3.

### 12.4 Conflict Resolution (Full-Text)

Same process as T/A screening (§11.4):

1. Identify records where reviewers disagree
2. Discussion first; consensus sought
3. If consensus fails: arbiter decides (binding)
4. Log in `screening/logs/conflict_resolution_log_[YYYY-MM-DD].md`

### 12.5 Companion-Report and Duplicate Handling at Full-Text Stage

*Protocol reference: §17 (Duplicate / Companion-Report Handling); §9.3 (Double-Counting Prevention Rule)*

At full-text review, the following determinations are made:

**Duplicate detection (Protocol §17.2):**

- If two reports are identical or near-identical (e.g., thesis chapter published as journal article), keep the most complete/authoritative version
- Assign exclusion code **E6** to the duplicate
- Primary selection priority (Protocol §9.3): (1) intended for peer-reviewed publication, (2) most focused relevance, (3) most complete dataset, (4) most recent

**Companion-report detection (Protocol §17.1, §17.3):**

- If two reports share the same dataset but present different analyses, designate one as **primary** and flag the other(s) as **companion(s)**
- Assign exclusion code **E7** to companion reports
- Record the companion relationship in the charting form (§16)
- Only the primary report is counted in numerical synthesis (Protocol §9.3, §17.4)

**Self-review safeguard records (Protocol §17.5):**

- When E6 or E7 is applied to the thesis (Wan Din 2026), draft manuscript (WPJ), or Woi et al. papers, the Second Reviewer must **independently verify** the determination
- Arbiter resolves any disagreement on these records

### 12.6 Final Screening Set

After full-text screening and conflict resolution:

1. **Included studies:** Records with consensus INCLUDE → proceed to data charting (§14)
2. **Excluded studies:** Records with consensus EXCLUDE → documented in exclusion table (§12.3)
3. **Companion reports:** Records flagged as E7 → recorded in charting form but not counted as independent evidence

### 12.7 PRISMA-ScR Flow Update (Full-Text Phase)

| Flow Node | Count | Source |
|---|---|---|
| Reports sought for retrieval | [N] | INCLUDE + UNCERTAIN from T/A screening |
| Reports not retrieved | [N] | Retrieval log — E8 exclusions |
| Reports assessed for eligibility | [N] | Retrieved full texts |
| Reports excluded — E1 | [N] | Exclusion table |
| Reports excluded — E2 | [N] | Exclusion table |
| Reports excluded — E3 | [N] | Exclusion table |
| Reports excluded — E4 | [N] | Exclusion table |
| Reports excluded — E5 | [N] | Exclusion table |
| Reports excluded — E6 | [N] | Exclusion table |
| Reports excluded — E7 | [N] | Exclusion table |
| Reports excluded — E8 | [N] | Exclusion table |
| Reports excluded — E9 | [N] | Exclusion table |
| **Studies included in review** | [N] | Final included set |

Separate peer-reviewed and grey-literature sources in the flow diagram per Protocol §15 (PRISMA-ScR adaptations for grey literature).

---

## 13. Grey-Literature Screening and Handling

*Protocol reference: §8.4 (Grey-Literature Inclusion Criteria); §12.1 (Phase 3: Grey-Literature Screening); §10.2 (Grey-Literature Sources); §10.4 (Search Documentation — PC-10)*

### 13.1 Grey-Literature Source Tracking

Before screening begins, maintain a grey-literature source tracking log:

| Source | Type | Searched? | Date Searched | Exact Search Terms/Syntax | Sections/URLs Navigated | Results Count | Hits Reviewed | PC-10 Compliant? |
|---|---|---|---|---|---|---|---|---|
| ProQuest Dissertations & Theses Global | Theses | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| OpenDOAR | Institutional repos | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| OSF Preprints | Preprints | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| medRxiv | Preprints (medical) | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| bioRxiv | Preprints (biological) | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| SSRN | Preprints (social science) | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| WHO IRIS | Institutional reports | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| NHTSA Traffic Safety Facts | Institutional reports | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| Transport for NSW | Institutional reports | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| Conference abstracts (ARVO/BCLA/AAOS) | Conference proceedings | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| Epistemonikos | Existing reviews + linked studies | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| PROSPERO | Protocol registry | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| NMRR | Malaysian register | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| MyJurnal / MyCite | Malaysian index | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| e-Rep (UKM) | UKM repository | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| ptsldigital (UKM) | UKM digital library | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| MyTO | Malaysian thesis portal | YES/NO | [date] | [exact syntax] | [specific URL] | [N] | [N] | YES/NO |
| Author contact | Unpublished manuscripts | YES/NO | [date] | N/A — direct contact | N/A | [N] contacted | [N] responses | YES/NO |

**Execution tiers (Protocol §10.2, P-02):**

- **Must-execute:** ProQuest, OpenDOAR, OSF Preprints, medRxiv, WHO IRIS, NHTSA, MyJurnal/MyCite, e-Rep, ptsldigital, MyTO, NMRR, PROSPERO, Epistemonikos, author contact
- **Execute-if-time:** bioRxiv, SSRN, Transport for NSW, conference abstracts (ARVO/BCLA/AAOS)
- Any unexecuted source is logged as not-searched with reason per Protocol §10.1.1

### 13.2 Grey-Literature Screening Process

Grey-literature records are screened using the **same two-phase process** as peer-reviewed sources (Protocol §12.1):

**Phase 1 — Title/Abstract screening:**

1. Import grey-literature records into the screening platform alongside database records
2. Tag with publication type (thesis, preprint, conference, institutional report, unpublished manuscript)
3. Screen against the same PCC eligibility criteria (Protocol §6, §8)
4. Apply the same exclusion codes (E1–E9)
5. No preferential treatment given to any source type (Protocol §12.1)

**Phase 2 — Full-text screening:**

1. Retrieve full texts of INCLUDE and UNCERTAIN grey-literature records
2. Assess against the same eligibility criteria
3. Document exclusions with E1–E9 codes
4. Same conflict resolution process (§11.4 / §12.4)

### 13.3 Conference Abstract Four-Minima Gate (PC-09)

Conference abstracts are subject to an additional eligibility gate. To be included, a conference abstract must meet ALL four minima (Protocol §8.3):

| Minimum | Requirement | Evidence |
|---|---|---|
| 1. Sample size | N reported | Numeric value in abstract |
| 2. DED/dry-eye measure | Defined instrument or diagnostic criterion | Named in abstract |
| 3. Night-driving outcome | Defined outcome measure | Named in abstract |
| 4. Study design | Explicit design stated | Cross-sectional, cohort, etc. named in abstract |

Conference abstracts failing ANY minimum are excluded under **E5** (Conference abstract without sufficient data — Protocol §12.2).

### 13.4 Theses and Dissertations

- Screened with identical criteria as journal articles (Protocol §12.1)
- If thesis findings have been published in a peer-reviewed journal and the journal article is more complete, the thesis may be excluded under **E6** (duplicate) or **E7** (companion) depending on content overlap
- The thesis/dissertation relationship to any published article must be explicitly documented (Protocol §17.3)
- Wan Din (2026) thesis is handled per Protocol §17.3, §17.4, §17.5 (self-review safeguards)

### 13.5 Grey-Literature PRISMA-ScR Branch

The PRISMA-ScR flow diagram includes a separate branch for grey-literature sources (Protocol §15):

| Flow Node | Count | Source Type |
|---|---|---|
| Grey-literature records identified | [N] | Sum across all grey-literature sources |
| Grey-literature records screened (T/A) | [N] | Post-dedup grey records |
| Grey-literature records excluded (T/A) | [N] | With E1–E9 breakdown |
| Grey-literature full texts sought | [N] | INCLUDE + UNCERTAIN from T/A |
| Grey-literature full texts not retrieved | [N] | E8 exclusions |
| Grey-literature assessed for eligibility | [N] | Retrieved full texts |
| Grey-literature excluded | [N] | With E1–E9 breakdown |
| **Grey-literature studies included** | [N] | Final grey set |

---

## 14. Data Charting / Extraction

*Protocol reference: §13 (Data Charting); §15.1 (AI/Automation Policy — PC-12); §17 (Duplicate / Companion-Report Handling)*

### 14.1 Charting Preparation

Before charting begins:

1. **Included studies confirmed:** Final included study set from §12.6
2. **Charting form prepared:** Template based on Protocol §13.2 (see §14.3 below)
3. **Charting form versioned:** Record form version and date in `extraction/charting-form/charting_form_v[N]_[YYYY-MM-DD].md`
4. **Study reports gathered:** Full texts of all included studies (primary + companion reports) assembled in a reference-accessible location

### 14.2 Charting Process

Per Protocol §13.1 — three-step process:

**Step 1: Pilot charting (2 studies)**

1. Two reviewers independently extract data from **two included studies** using the charting form
2. Studies for pilot: select one study with a simpler design (e.g., cross-sectional survey) and one with a more complex design (e.g., simulator study) to test form breadth
3. Compare extracted data field-by-field
4. Identify discrepancies, ambiguities, and form gaps
5. Resolve disagreements by discussion
6. Refine charting form definitions and options as needed
7. Record pilot charting outcomes in `extraction/calibration/pilot_charting_[YYYY-MM-DD].md`

**Step 2: Calibration charting (next 3 studies — PC-14)**

1. Two reviewers independently extract data from **three additional studies** (2 pilot + 3 calibration = 5 total per Protocol §13.1)
2. Calculate inter-rater agreement on key fields (study design, DED assessment type, night-driving assessment type, main association, effect size)
3. Finalise charting form definitions
4. Record calibration outcomes in `extraction/calibration/calibration_charting_[YYYY-MM-DD].md`:
   - Agreement rate per field
   - Fields with highest disagreement
   - Form refinements made
   - Final form version

**Step 3: Single-reviewer charting with spot-checks**

1. One reviewer (Lead) charts **all remaining studies** using the finalised form
2. Second reviewer independently charts **30% of remaining studies** randomly selected (CR-03 audit uplift: raised from 20% given small expected evidence set)
3. Spot-check selection: use documented random seed; record selected study IDs
4. Discrepancies resolved by discussion; charting form clarified if needed
5. Unresolved charting disputes → arbiter (PCR-02)
6. Log all form clarifications in `extraction/logs/charting_form_clarifications_[YYYY-MM-DD].md`

### 14.3 Data Charting Form Template

*Protocol reference: §13.2 (Data Charting Form); P-03 (charting tiers)*

**Charting tiers (P-03 — all fields remain available; tiers govern reviewer effort):**

- **Must-chart:** Study identification, Publication type/status, Study design/setting, Population (N enrolled/analysed, age, gender), DED assessment type + instrument, Night-driving assessment type + instrument, Main association + effect size + direction, Companion-report tracking, DOI
- **Optional (chart only if reported, else N/A):** Driving experience/frequency, vehicle type, instrument validation metrics, clinical DED measures, simulator/on-road protocol detail, intermediate visual methods, qualitative themes, DED severity distribution, covariates

| Field | Type | Definition / Options |
|---|---|---|
| **Study identification** | | |
| Study ID | Auto-generated | Sequential identifier |
| Report ID | Auto-generated | Sequential identifier (distinguishes reports from studies) |
| Author_Year | Text | First author and publication year |
| Journal / Source | Text | Full journal name or source (e.g., "ProQuest Dissertations") |
| Country | Categorical | Country where study was conducted |
| Year of publication | Numeric | Publication year |
| **Publication type and status** | | |
| Publication type | Categorical | Peer-reviewed journal article, Thesis/dissertation, Preprint, Conference proceedings/abstract, Institutional report, Unpublished manuscript, Other grey literature |
| Publication status | Categorical | Published, Unpublished, Under review, Preprint, Thesis |
| Peer-reviewed? | Categorical | Yes, No |
| Evidence type | Categorical | Primary research, Secondary synthesis, Contextual/background |
| **Study design and setting** | | |
| Study design | Categorical | Cross-sectional, Cohort (prospective/retrospective), Case-control, RCT, Quasi-experimental, Mixed-methods, Simulator, On-road, Naturalistic |
| Setting | Categorical | Clinical, Community, Laboratory, Simulator, Online survey, Mixed |
| **Population** | | |
| Sample size (total) | Numeric | Total participants enrolled |
| Sample size (analysed) | Numeric | Participants included in analysis |
| Age: mean (SD) | Text | Mean age with standard deviation |
| Age: range | Text | Minimum–maximum age |
| Gender: % female | Numeric | Percentage of female participants |
| Driving experience | Text | Years of driving, kilometres driven, or other metric |
| Night-driving frequency | Text | How often participants drive at night |
| Vehicle type | Text | Car, motorcycle, truck, other |
| **DED/dry-eye assessment** | | |
| DED definition used | Categorical | TFOS DEWS II, TFOS DEWS III, ADES, Clinical diagnosis, Symptom-based, Not stated |
| DED diagnostic criteria | Text | Specific criteria applied (if reported) |
| DED assessment type | Categorical | Questionnaire only, Clinical tests only, Combined, Not stated |
| Dry-eye symptom instrument | Text | OSDI, SPEED, DEQ, CLDEQ, IDEEL, NEI-VFQ, Custom (specify), Other (specify) |
| Dry-eye symptom instrument validated? | Categorical | Yes (cite validation study + log numeric metrics where reported, e.g., CVI/α) (P-03), No, Not stated |
| Clinical DED measures | Text | TBUT, NIBUT, Schirmer, Osmolarity, Corneal staining, Meibography, Other (specify) |
| DED severity distribution | Text | Mild/moderate/severe breakdown (if reported) |
| **Night-driving assessment** | | |
| Night-driving definition | Text | How the study defines "night driving" or "low-light driving" |
| Night-driving assessment type | Categorical | Self-report questionnaire, Driving simulator, On-road test, Naturalistic driving, Crash data, Combined, Other (specify) |
| Night-driving instrument | Text | VND-Q, VND-Q-M, NDQ, LLQ, Custom (specify), Other (specify) |
| Night-driving instrument validated? | Categorical | Yes (cite validation study + log numeric metrics where reported, e.g., CVI/α) (P-03), No, Not stated |
| Simulator type (if applicable) | Text | Platform name, visual environment, scenario details |
| On-road protocol (if applicable) | Text | Route, time of day, lighting conditions |
| **Intermediate visual measures** | | |
| Contrast sensitivity measured? | Categorical | Yes, No |
| Contrast sensitivity method | Text | Pelli-Robson, CSV-1000, other (specify) |
| HOAs measured? | Categorical | Yes, No |
| HOAs method | Text | Wavefront aberrometer (specify model) |
| Glare sensitivity measured? | Categorical | Yes, No |
| Glare sensitivity method | Text | Glare tester (specify model), other |
| Visual acuity measured? | Categorical | Yes, No |
| Visual acuity type | Text | Photopic, mesopic, scotopic |
| Other visual measures | Text | Any additional visual function tests |
| **Key findings** | | |
| Main association reported | Text | Primary finding regarding DED/dry-eye and night driving |
| Effect size | Text | OR, β, r, d, RR, with 95% CI and p-value |
| Direction of association | Categorical | Positive (more DED → more difficulty), Negative, No association, Mixed |
| Covariates adjusted for | Text | Variables included in multivariate models |
| Qualitative findings/themes (PC-19) | Text | Patient lived-experience themes (night-driving difficulty, glare disability, visual fatigue) if mixed-methods/qualitative component; else N/A |
| **Quality characterisation (descriptive, not exclusionary — PC-11)** | | |
| Instrument validation status | Categorical | All validated, Some validated, None validated |
| Confounding control | Categorical | Adjusted for key confounders, Unadjusted, Not applicable |
| Design adequacy note | Text | Reviewer note on sample/design fit (uses raw N from Population fields; no fixed n≥50 threshold) |
| **Companion-report tracking (PC-11)** | | |
| Companion report? | Categorical | Yes, No |
| Relationship to other reports (incl. companion IDs) | Text | Overlap description + companion Report IDs (e.g., "Same dataset as Wan Din 2026; companion R-014") |
| **Source** | | |
| DOI | Text | Digital Object Identifier |
| Full-text available | Categorical | Yes, No |

### 14.4 Charting Form Version Control

| Version | Date | Changes | Approved By |
|---|---|---|---|
| v1.0 | [date] | Initial form from Protocol §13.2 | Both reviewers |
| v1.1 | [date] | Refinements from pilot charting (2 studies) | Both reviewers |
| v1.2 | [date] | Refinements from calibration charting (3 studies) | Both reviewers |
| v[N] | [date] | [Description of changes] | Both reviewers |

Store all versions in `extraction/charting-form/`. Do not delete prior versions.

### 14.5 Discrepancy Resolution

**During pilot/calibration:**

- Both reviewers compare extracted data field-by-field
- Discrepancies discussed; form refined
- Unresolved → arbiter

**During spot-checks (30%):**

- Lead charts all; Second Reviewer charts 30% independently
- Compare spot-checked records field-by-field
- Discrepancies discussed; form clarified if needed
- Unresolved → arbiter (PCR-02)

**Discrepancy log:**

Record in `extraction/logs/discrepancy_log_[YYYY-MM-DD].md`:

```markdown
## Charting Discrepancy Log

| Record ID | Author_Year | Field | R1 Value | R2 Value | Resolution | Resolved By | Date |
|---|---|---|---|---|---|---|---|
| [ID] | [Author Year] | [Field name] | [Value] | [Value] | [How resolved] | [Reviewer / Arbiter] | YYYY-MM-DD |
```

### 14.6 Charting Output

After all charting is complete:

1. **Master charting CSV:** `extraction/charting_data_[YYYY-MM-DD].csv` — all fields for all included studies
2. **Primary-report subset:** Filter to primary reports only (exclude companion-flagged records) for numerical synthesis
3. **Companion-report table:** Separate table listing all companion reports and their relationships (Protocol §17)
4. **Spot-check agreement report:** `extraction/calibration/spot_check_agreement_[YYYY-MM-DD].md` — agreement rate, discrepancies, resolutions

### 14.7 Self-Review Safeguards for Charting

*Protocol reference: §17.5*

When charting the thesis (Wan Din 2026), draft manuscript (WPJ), or Woi et al. papers:

1. Second Reviewer **independently verifies** all charting decisions on these reports
2. Any disagreement goes to the **arbiter**
3. Charting decisions are **transparently reported**

### 14.8 AI/Automation Prohibition for Charting

*Protocol reference: §15.1 (PC-12)*

**No generative AI or LLM is used for data charting.** All extraction decisions are made by human reviewers. The local LLM pipeline (mistral:7b-instruct, model ID 6577803aa9a0) is authorized ONLY for deterministic infrastructure tasks (RIS parsing, deduplication, hashing, DOI batch retrieval) — NOT for charting or clinical/methodological judgement.

---

## 15. Evidence and Provenance Capture

*Protocol reference: §9 (Evidence Sources and Their Relationship); §17 (Duplicate / Companion-Report Handling); §17.4 (Primary Report Determination); §17.5 (Self-Review Safeguards)*

### 15.1 Companion-Report Tracking

**Purpose:** Ensure transparent reporting of which reports originate from the same study/dataset and prevent double-counting (Protocol §9.3, §17.1).

**Companion-report log:**

Maintain in `extraction/logs/companion_report_log_[YYYY-MM-DD].md`:

| Primary Report ID | Companion Report ID | Study/Dataset | Relationship | Primary Designation Rationale | Self-Review Safeguard Applied? |
|---|---|---|---|---|---|
| [R-XXX — e.g., WPJ draft manuscript] | [R-YYY — e.g., Wan Din 2026 thesis] | [Same dataset, n=373] | [Companion — same dataset, same analysis] | [WPJ intended for publication; focused on DED-night-driving] | YES — Second Reviewer verified (§17.5) |

### 15.2 Primary Report Designation

*Protocol reference: §17.4 (Primary Report Determination: Draft Manuscript vs Thesis)*

**Applied to this review (Protocol §17.4):**

| Report | Designation | Rationale |
|---|---|---|
| Draft Manuscript (WPJ, unpublished) | **PRIMARY REPORT** | Intended for peer-reviewed publication; focused on DED-night-driving relationship; authored by Lead Reviewer |
| Wan Din (2026) thesis | **COMPANION REPORT** | Same dataset (n=373), same variables, same analysis, same findings; not counted as independent evidence |

**Primary report selection criteria (Protocol §9.3, in order of priority):**

1. Intended for peer-reviewed publication
2. Most focused relevance to the DED-night-driving relationship
3. Most complete dataset
4. Most recent publication date

**Double-counting prevention rule (Protocol §9.3):** Where multiple reports originate from the same study or dataset, only one primary report is included in the numerical evidence synthesis. Companion reports are recorded in the charting form but flagged as "companion to [primary report]" and not counted as independent evidence.

### 15.3 Source-Overlap Audit Table

*Protocol reference: §14.1 (Source-overlap audit)*

Produce a source-overlap audit table for the final manuscript:

| Study | Primary Report | Companion Report(s) | Dataset | Overlap Description | Counted in Numerical Synthesis? |
|---|---|---|---|---|---|
| [Study name] | [Report ID] | [Report ID(s)] | [n; variables] | [Description of relationship] | YES (primary) / NO (companion) |

This table is reported in the main manuscript per Protocol §14.2.

### 15.4 Evidence Provenance Chain

Every included study must have a complete provenance chain from raw export to charting:

```
Raw export (raw/[database]/)
  → Manifest (manifests/)
    → Ingestion log (logs/)
      → Deduplication output (processed/)
        → Screening decision (screening/)
          → Full-text retrieval (screening/full-text/)
            → Final eligibility (screening/full-text/)
              → Charting decision (extraction/)
                → Evidence map entry (reports/)
```

**Audit rule:** At any point in the chain, a reviewer must be able to trace any charting entry back to the original raw export and manifest.

### 15.5 Co-Authored Paper Extension

*Protocol reference: §17.5 Rule 6 (CR-07)*

Rules 1–5 of §15.5 apply identically to Woi et al. (2025a) and Woi et al. (2025b):

1. Eligibility criteria applied identically
2. Second Reviewer independently screens and charts these papers
3. Lead-reviewer co-authorship transparently disclosed
4. No inflation of evidence
5. PRISMA-ScR flow reports these at appropriate stages
6. Any disagreement on these reports → **arbiter**, not Lead Reviewer discretion

---

## 16. Synthesis and Mapping

*Protocol reference: §14 (Data Synthesis and Presentation); §13.2 (Charting form fields for synthesis inputs)*

### 16.1 Synthesis Inputs

All synthesis is derived from the charting data (§14.6). No new data extraction occurs during synthesis.

**Input files:**

| File | Location | Content |
|---|---|---|
| Master charting CSV | `extraction/charting_data_[YYYY-MM-DD].csv` | All charted fields for all included studies |
| Primary-report subset | Derived from master charting CSV | Primary reports only (companion-flagged excluded) |
| Companion-report table | `extraction/logs/companion_report_log_[YYYY-MM-DD].md` | Study relationships |
| Exclusion table | `screening/full-text/ft_exclusion_table_[YYYY-MM-DD].csv` | Excluded studies with reasons |

### 16.2 Descriptive Numerical Summary

*Protocol reference: §14.1(1)*

Produce frequency counts and summaries:

| Dimension | Output | Format |
|---|---|---|
| Study design distribution | Count of cross-sectional, cohort, case-control, RCT, simulator, on-road, naturalistic, mixed-methods | Table + bar chart |
| Population characteristics | Age ranges, gender distribution, sample sizes, geographic regions | Table |
| DED assessment methods | Count by type (questionnaire only, clinical only, combined), instrument frequency | Table |
| Night-driving assessment methods | Count by type (self-report, simulator, on-road, naturalistic, crash data), instrument frequency | Table |
| Geographic distribution | Count by country/region | Table |
| Publication type distribution | Count by peer-reviewed, thesis, preprint, conference, institutional, unpublished | Table |
| Language distribution | Count by English, Malay | Table |
| Era stratification | Count by pre-2007, 2007–2017, 2018–present (Protocol §8.1 date-range note) | Table |
| Effect size summary | Range of reported effect sizes (OR, β, r, d, RR) with direction | Table |

**No meta-analysis is planned** (Protocol §14.1). The evidence is too heterogeneous for quantitative pooling; the review objective is mapping, not estimation.

### 16.3 Evidence Map Construction

*Protocol reference: §14.1(2)*

Construct cross-tabulation tables:

**Evidence Map 1: Study Design × DED Assessment Type**

| | Questionnaire Only | Clinical Tests Only | Combined | Not Stated | Total |
|---|---|---|---|---|---|
| Cross-sectional | [N] | [N] | [N] | [N] | [N] |
| Cohort | [N] | [N] | [N] | [N] | [N] |
| Case-control | [N] | [N] | [N] | [N] | [N] |
| RCT | [N] | [N] | [N] | [N] | [N] |
| Simulator | [N] | [N] | [N] | [N] | [N] |
| On-road | [N] | [N] | [N] | [N] | [N] |
| Naturalistic | [N] | [N] | [N] | [N] | [N] |
| Mixed-methods | [N] | [N] | [N] | [N] | [N] |
| **Total** | [N] | [N] | [N] | [N] | [N] |

**Evidence Map 2: Night-Driving Measure × Geographic Region**

| | Asia | Europe | North America | Oceania | Africa | South America | Multi/Other | Total |
|---|---|---|---|---|---|---|---|---|
| Self-report | [N] | [N] | [N] | [N] | [N] | [N] | [N] | [N] |
| Simulator | [N] | [N] | [N] | [N] | [N] | [N] | [N] | [N] |
| On-road | [N] | [N] | [N] | [N] | [N] | [N] | [N] | [N] |
| Naturalistic | [N] | [N] | [N] | [N] | [N] | [N] | [N] | [N] |
| Crash data | [N] | [N] | [N] | [N] | [N] | [N] | [N] | [N] |
| Combined | [N] | [N] | [N] | [N] | [N] | [N] | [N] | [N] |
| **Total** | [N] | [N] | [N] | [N] | [N] | [N] | [N] | [N] |

**Evidence Map 3: DED Assessment × Night-Driving Measure**

| | Self-report Questionnaire | Driving Simulator | On-road Test | Naturalistic Driving | Crash Data | Combined | Total |
|---|---|---|---|---|---|---|---|
| Questionnaire only | [N] | [N] | [N] | [N] | [N] | [N] | [N] |
| Clinical tests only | [N] | [N] | [N] | [N] | [N] | [N] | [N] |
| Combined | [N] | [N] | [N] | [N] | [N] | [N] | [N] |
| Not stated | [N] | [N] | [N] | [N] | [N] | [N] | [N] |
| **Total** | [N] | [N] | [N] | [N] | [N] | [N] | [N] |

### 16.4 Gap Matrix

*Protocol reference: §14.1(4)*

Identify cells in the evidence map where no or thin evidence exists:

| Gap Dimension | Description | Evidence Status | Priority for Future Research |
|---|---|---|---|
| [e.g., RCT design] | [No RCTs identified] | [Empty cell] | [High — would strengthen causal inference] |
| [e.g., On-road studies in Asia] | [Only simulator studies from Asia] | [Thin — 1–2 studies] | [Moderate — cultural driving context matters] |
| [e.g., Objective DED + naturalistic driving] | [No studies combining clinical DED measures with naturalistic driving data] | [Empty cell] | [High — real-world validity] |
| [e.g., Longitudinal cohort] | [Only cross-sectional designs identified] | [Thin] | [High — temporal relationship unknown] |
| [e.g., Elderly drivers (>65)] | [Limited age-range data] | [Thin] | [Moderate — age-related DED prevalence higher] |

### 16.5 Thematic Synthesis

*Protocol reference: §14.1(3)*

Group studies by approach and synthesise narratively:

**Theme 1: Self-report only studies**
- Studies using questionnaire-based measures of both DED and night-driving
- Summary of findings, instruments used, effect directions
- Strengths and limitations of self-report approach

**Theme 2: Clinical DED + driving studies**
- Studies combining clinical DED measures (TBUT, NIBUT, Schirmer) with driving outcomes
- Summary of findings, clinical measures used, effect sizes
- Strengths and limitations of clinical approach

**Theme 3: Simulator studies**
- Studies using driving simulators to assess DED-related driving performance
- Summary of simulator protocols, findings, ecological validity
- Strengths and limitations of simulator approach

**Theme 4: On-road and naturalistic studies**
- Studies using real-world driving assessment
- Summary of findings, driving protocols, safety considerations
- Strengths and limitations of on-road approach

**Theme 5: Intermediate visual function studies**
- Studies examining contrast sensitivity, HOAs, glare, tear film stability in the context of DED and driving
- Summary of visual function measures, their relationship to driving outcomes
- Integration with DED-night-driving evidence

**Theme 6: Mixed-methods and qualitative studies**
- Studies with qualitative components on patient lived experience of night-driving difficulty
- Summary of themes (if applicable — Protocol §13.2, PC-19)

### 16.6 Quality Characterisation

*Protocol reference: §14.1(5); Protocol §13.2 (quality characterisation fields); PC-11*

Descriptive quality characterisation (not exclusionary):

| Quality Dimension | Output |
|---|---|
| Instrument validation status | Count of studies with all validated, some validated, or no validated instruments |
| Confounding control | Count of studies with adjusted, unadjusted, or not applicable analyses |
| Design adequacy note | Reviewer observations on sample/design fit (uses raw N; no fixed threshold) |

### 16.7 Source-Overlap Audit in Synthesis

*Protocol reference: §14.1(6)*

- Report which reports are companion publications from the same study/dataset
- Include the source-overlap audit table (§15.3) in the main manuscript
- Ensure companion reports are not counted as independent evidence in any synthesis output
- The PRISMA-ScR flow diagram reflects the companion-report relationship

### 16.8 Synthesis Output Files

| Output | Location | Format |
|---|---|---|
| Evidence map tables | `reports/tables/` | CSV + formatted table for manuscript |
| Gap matrix | `reports/tables/` | CSV + formatted table for manuscript |
| Thematic synthesis narrative | Main manuscript draft | Prose |
| Quality characterisation table | `reports/tables/` | CSV + formatted table for manuscript |
| Source-overlap audit table | `reports/tables/` | CSV + formatted table for manuscript |
| Characteristics of included studies table | `reports/tables/` | CSV + formatted table for manuscript |
| Geographic distribution table | `reports/tables/` | CSV + formatted table for manuscript |
| Instrument frequency table | `reports/tables/` | CSV + formatted table for manuscript |

---

## 17. Deviations and Amendments

*Protocol reference: §21 (Amendments)*

### 17.1 Deviation Logging

Any deviation from the protocol or operations manual — whether intentional or discovered post hoc — must be logged.

**Deviation log location:** `reports/deviations/deviation_log_[YYYY-MM-DD].md`

**Deviation log template:**

```markdown
## Deviation Log

| ID | Date Discovered | Section Affected | Deviation Description | Impact Assessment | Corrective Action | Protocol Amendment Required? | Amendment Status |
|---|---|---|---|---|---|---|---|
| D-001 | YYYY-MM-DD | [Protocol §X / Manual §X] | [Description] | [Low/Medium/High] | [Action taken] | YES/NO | [Pending/Approved/Registered] |
```

### 17.2 Amendment Process

*Protocol reference: §21*

**Step 1: Document the amendment**

- Record the amendment in the deviation log (§17.1)
- Specify: what is changing, why, which protocol section is affected, whether it is major or minor

**Step 2: Classify the amendment**

| Amendment Type | Definition | Examples | Approval Required |
|---|---|---|---|
| Documentation-only | No change to eligibility, search strings, databases, or synthesis | Language justification, logging rules, clarification text | Internal documentation; no OSF re-registration |
| Minor | Small operational change that does not alter the review's scope or conclusions | Charting form field addition, spot-check percentage adjustment | Internal documentation; record in amendment log |
| Major | Change to eligibility criteria, search strategy, databases, synthesis approach, or study design | Adding/removing a database, changing PCC criteria, adding meta-analysis | Formal protocol amendment; OSF re-registration; reported in final manuscript |

**Step 3: Approve the amendment**

- Minor/documentation-only: Lead Reviewer + Second Reviewer approval
- Major: Lead Reviewer + Second Reviewer + Arbiter (if needed) approval
- Record approval in the amendment log with initials and date

**Step 4: Register on OSF (major amendments only)**

- Upload amended protocol to OSF with new version number
- Update protocol version in all manifests
- Record OSF DOI of amended protocol

**Step 5: Update operations manual (if applicable)**

- If the amendment affects operational procedures, update the relevant manual section
- Record the manual version change

### 17.3 Version Control

| Document | Current Version | Amendment History |
|---|---|---|
| Protocol | v7.6 + CR-01–CR-07, PCR-01–PCR-05, P-01–P-05, C-02, C-01/C-04/C-05/C-13 | Protocol §21 amendment records |
| Operations Manual | v2.0 | New version — covers search through synthesis |
| Search Strategy | S1 v1.2 (Malay arm) | PRESS peer-reviewed; CR-02 Malay delta |
| Charting Form | v[N] | Version history in §14.4 |

### 17.4 Amendment Record for This Manual

This Operations Manual (v2.0) is a new document extending the scope of the v1.6 Manual to cover post-search phases. It does not amend the Protocol. All methodological content is traced to Protocol sections.

---

## 18. Final Reporting and Audit Trail

*Protocol reference: §14.2 (Presentation); §15 (Reporting Guidelines); §12.3 (Documentation); PRISMA-ScR (Tricco et al. 2018); PRISMA-S (Rethlefsen et al. 2021)*

### 18.1 PRISMA-ScR Flow Diagram

*Protocol reference: §12.3; §14.2; §15*

Construct the PRISMA-ScR flow diagram per the PRISMA-ScR extension (Tricco et al. 2018). The diagram must document the selection process at each stage.

**Flow diagram source files:** `reports/prisma-scR/`

**Required flow nodes:**

```
Identification
  ├── Records identified from database searching (N = ...)
  │     └── PubMed (N = ...) | Embase (N = ...) | Scopus (N = ...) | WoS (N = ...) | CINAHL (N = ...) | TRID (N = ...) | Cochrane (N = ...) | VisionCite (N = ...)
  ├── Records identified from grey-literature searching (N = ...)
  │     └── Theses (N = ...) | Preprints (N = ...) | Conference abstracts (N = ...) | Institutional reports (N = ...) | Unpublished manuscripts (N = ...) | Other (N = ...)
  └── Records removed before screening (N = ...)
        └── Duplicates removed (N = ...)

Screening
  ├── Records screened — title/abstract (N = ...)
  │     └── Records excluded (N = ...) [with E1–E9 breakdown]
  ├── Reports sought for retrieval (N = ...)
  │     └── Reports not retrieved (N = ...) [E8]
  └── Reports assessed for eligibility (N = ...)
        └── Reports excluded (N = ...) [with E1–E9 breakdown]

Included
  ├── Studies included in review (N = ...)
  │     └── Included in synthesis (N = ...)
  └── Reports contributing to included studies (N = ...)
        └── Primary reports (N = ...) | Companion reports (N = ...)
```

**Grey-literature separate branch:** Per Protocol §15, the flow diagram includes a separate branch for grey-literature sources with counts at each stage.

**Update search records:** Per Protocol §11.8, report primary vs update yields separately in the flow diagram.

### 18.2 PRISMA-S Checklist (Search Reporting)

*Protocol reference: §14.2; PRISMA-S (Rethlefsen et al. 2021)*

Complete the PRISMA-S checklist (16 items) for the search methods:

| PRISMA-S Item | Description | Location in Manuscript |
|---|---|---|
| 1 | Data sources | Methods — Information Sources |
| 2 | Date range | Methods — Information Sources |
| 3 | Database details | Methods — Information Sources |
| 4 | Full search strategy | Supplementary material + OSF (P-02) |
| 5 | Search limits | Methods — Search Strategy |
| 6 | Search update | Methods — Search Strategy (§11.8) |
| 7 | Total results | Results — Search Results |
| 8 | Deduplication method | Methods — Data Processing |
| 9 | Screening process | Methods — Study Selection |
| 10 | Full-text retrieval | Methods — Study Selection |
| 11 | Inclusion criteria | Methods — Eligibility Criteria |
| 12 | Exclusion criteria | Methods — Eligibility Criteria |
| 13 | Included studies | Results — Characteristics of Studies |
| 14 | Search strategy deposit | Supplementary material + OSF |
| 15 | Search peer review | Methods — Search Strategy (if PRESS conducted) |
| 16 | Conflicts of interest | COI statement |

Store completed checklist in `reports/supplementary/prisma_s_checklist_[YYYY-MM-DD].pdf` and on OSF.

### 18.3 Supplementary Materials

*Protocol reference: §14.2*

| Supplementary Item | Content | Format | Location |
|---|---|---|---|
| Search strategies | Complete S1 v1.2 search strings for all 8 databases + grey-literature search terms | PDF | `reports/supplementary/` + OSF |
| Excluded studies table | All excluded studies with exclusion codes and reasons | CSV + PDF | `screening/full-text/ft_exclusion_table_[YYYY-MM-DD].csv` + `reports/supplementary/` |
| Complete charting data | Master charting CSV | CSV | `extraction/charting_data_[YYYY-MM-DD].csv` + OSF |
| PRISMA-ScR checklist | Completed checklist | PDF | `reports/supplementary/` + OSF (P-01) |
| PRISMA-S checklist | Completed checklist (16 items) | PDF | `reports/supplementary/` + OSF (P-02) |
| Companion-report table | Study relationships and primary designations | CSV | `reports/tables/` |
| Source-overlap audit | Transparent reporting of overlapping reports | Table | Main manuscript |
| Screening kappa report | Calibration and final kappa values | TXT/CSV | `screening/title-abstract/` |
| Grey-literature source log | PC-10 documentation for all grey-literature sources | CSV/MD | `screening/grey-literature/` |

### 18.4 Audit Trail Completeness

Before manuscript submission, verify the following audit trail is complete:

| Audit Point | Check | Location |
|---|---|---|
| All database searches documented | Manifests exist for all 8 databases (or recorded as not-searched) | `manifests/` |
| Grey-literature searches documented | PC-10 log complete with source + syntax + URL + sections + date + hits reviewed | `screening/grey-literature/` |
| Citation chasing documented | Backward, forward, related, author searches logged | `searches/logs/` |
| Deduplication documented | Dedup method, threshold, version recorded | `logs/` |
| T/A screening kappa reported | Calibration kappa + final kappa | `screening/title-abstract/` |
| Full-text exclusions documented | E1–E9 codes for all excluded studies | `screening/full-text/` |
| Companion-report relationships documented | Primary/companion designations in charting form | `extraction/` |
| Self-review safeguards documented | Second Reviewer verification of thesis, draft manuscript, Woi papers | `screening/logs/` |
| Charting form versions preserved | All versions retained | `extraction/charting-form/` |
| Charting discrepancies logged | Spot-check agreement documented | `extraction/logs/` |
| Amendments logged | All deviations/amendments recorded | `reports/deviations/` |
| PRISMA-ScR flow complete | All nodes populated with counts | `reports/prisma-scR/` |
| PRISMA-S checklist complete | 16 items addressed | `reports/supplementary/` |

### 18.5 OSF Deposit

Per Protocol §1 (PC-01) and §14.2:

| Item | OSF Deposit |
|---|---|
| Protocol | Protocol PDF + DOI |
| Search strategies | S1 v1.2 PDF (all 8 databases) |
| PRISMA-ScR checklist | Completed checklist PDF |
| PRISMA-S checklist | Completed checklist PDF |
| Charting data | Master charting CSV |
| Search manifests | Manifest files (or summary) |

---

## 19. Stopping Rules and Quality Gates

*Protocol reference: §12 (Study Selection); §13 (Data Charting); §15.1 (AI/Automation Policy — PC-12)*

### 19.1 Pre-Search Gates (Search Cannot Begin Until All Pass)

| Gate | Requirement | Protocol Reference | Status |
|---|---|---|---|
| G-01 | OSF DOI issued | PC-05, §1 | [ ] PASS / [ ] FAIL |
| G-02 | Database access verified for all 8 databases (or recorded as not-searched) | PC-07, §10.1.1 | [ ] PASS / [ ] FAIL |
| G-03 | CR-01–CR-07 + P-01–P-05 approval recorded | §21 | [ ] PASS / [ ] FAIL |
| G-04 | CR-02 second-reviewer verification in manifest Strategy Version | §11.5 | [ ] PASS / [ ] FAIL |
| G-05 | Reviewer 2 named in §19.1 CRediT | §19.1 | [ ] PASS / [ ] FAIL |
| G-06 | S1 v1.2 frozen and PRESS-verified | §11.4 | [ ] PASS / [ ] FAIL |

### 19.2 Pre-Screening Gates (Screening Cannot Begin Until All Pass)

| Gate | Requirement | Protocol Reference | Status |
|---|---|---|---|
| G-07 | All database exports ingested | Manual §4 | [ ] PASS / [ ] FAIL |
| G-08 | Deduplication completed | Manual §4.3 | [ ] PASS / [ ] FAIL |
| G-09 | Pre-ingestion QC passed | Manual §7.1 | [ ] PASS / [ ] FAIL |
| G-10 | Post-ingestion QC passed | Manual §7.2 | [ ] PASS / [ ] FAIL |
| G-11 | Mendeley import completed | Manual §4.4 | [ ] PASS / [ ] FAIL |
| G-12 | Screening platform configured | Manual §10 | [ ] PASS / [ ] FAIL |
| G-13 | Calibration kappa ≥ 0.80 (or re-calibrated) | Protocol §12.1, Manual §11.2 | [ ] PASS / [ ] FAIL |

### 19.3 Pre-Charting Gates (Charting Cannot Begin Until All Pass)

| Gate | Requirement | Protocol Reference | Status |
|---|---|---|---|
| G-14 | T/A screening completed | Protocol §12.1 | [ ] PASS / [ ] FAIL |
| G-15 | All T/A conflicts resolved | Manual §11.4 | [ ] PASS / [ ] FAIL |
| G-16 | Final T/A kappa calculated and reported | Protocol §12.1, PC-13 | [ ] PASS / [ ] FAIL |
| G-17 | Full-text screening completed | Protocol §12.1 | [ ] PASS / [ ] FAIL |
| G-18 | All full-text conflicts resolved | Manual §12.4 | [ ] PASS / [ ] FAIL |
| G-19 | Final included study set confirmed | Manual §12.6 | [ ] PASS / [ ] FAIL |
| G-20 | Charting form pilot completed (2 studies) | Protocol §13.1 | [ ] PASS / [ ] FAIL |
| G-21 | Charting form calibration completed (3 studies; PC-14) | Protocol §13.1 | [ ] PASS / [ ] FAIL |

### 19.4 Pre-Synthesis Gates (Synthesis Cannot Begin Until All Pass)

| Gate | Requirement | Protocol Reference | Status |
|---|---|---|---|
| G-22 | Charting completed for all included studies | Protocol §13.1 | [ ] PASS / [ ] FAIL |
| G-23 | Spot-check (30%) completed; agreement acceptable | Protocol §13.1, CR-03 | [ ] PASS / [ ] FAIL |
| G-24 | All charting discrepancies resolved | Manual §14.5 | [ ] PASS / [ ] FAIL |
| G-25 | Charting form clarifications logged | PCR-02 | [ ] PASS / [ ] FAIL |
| G-26 | Master charting CSV produced | Manual §14.6 | [ ] PASS / [ ] FAIL |
| G-27 | Companion-report log complete | Protocol §17 | [ ] PASS / [ ] FAIL |

### 19.5 Pre-Submission Gates (Manuscript Cannot Be Submitted Until All Pass)

| Gate | Requirement | Protocol Reference | Status |
|---|---|---|---|
| G-28 | PRISMA-ScR flow diagram complete | Protocol §12.3, §14.2 | [ ] PASS / [ ] FAIL |
| G-29 | PRISMA-S checklist complete (16 items) | Protocol §14.2 | [ ] PASS / [ ] FAIL |
| G-30 | All supplementary materials prepared | Protocol §14.2 | [ ] PASS / [ ] FAIL |
| G-31 | Source-overlap audit table complete | Protocol §14.1(6) | [ ] PASS / [ ] FAIL |
| G-32 | Self-review safeguards documented | Protocol §17.5 | [ ] PASS / [ ] FAIL |
| G-33 | Final search update completed (≤3 months pre-submission) | Protocol §11.8 | [ ] PASS / [ ] FAIL |
| G-34 | All deviations/amendments logged | Protocol §21 | [ ] PASS / [ ] FAIL |
| G-35 | Audit trail completeness verified | Manual §18.4 | [ ] PASS / [ ] FAIL |
| G-36 | OSF deposit complete | Protocol §1, §14.2 | [ ] PASS / [ ] FAIL |
| G-37 | Conflict of interest statement included | Protocol §19.3 | [ ] PASS / [ ] FAIL |
| G-38 | CRediT statement included | Protocol §19.1 | [ ] PASS / [ ] FAIL |

### 19.6 Quality Gate Enforcement

**No phase may begin until all gates for that phase pass.** If any gate fails:

1. **Document the failure** in the deviation log (§17.1)
2. **Identify the root cause**
3. **Implement corrective action**
4. **Re-assess the gate** after corrective action
5. **Record re-assessment outcome** in the deviation log

**Exception:** If a gate failure is due to a protocol-level issue (e.g., eligibility criteria ambiguity), a formal protocol amendment (§17.2) must be completed before the gate can be re-assessed.

### 19.7 AI/Automation Quality Gate

*Protocol reference: §15.1 (PC-12)*

At each phase transition, confirm that **no generative AI or LLM** was used for:

- Title/abstract screening decisions
- Full-text eligibility decisions
- Data charting/extraction
- Thematic synthesis
- Quality assessment judgements

**Permitted automation (deterministic only):**

| Task | Tool | Verification |
|---|---|---|
| RIS/CSV metadata parsing | Local LLM (mistral:7b-instruct) or pure code | 100% human verification; prompt file + diff in logs |
| Exact-match deduplication | Local pipeline | Manual review of fuzzy matches (Priority 5) |
| SHA-256 hashing | Pure code | Automated — integrity check |
| Batch DOI retrieval | Local LLM or API | 100% human verification per batch |
| File detection, manifest generation, ingestion logging | Pure code | Automated — no clinical judgement involved |

**Gate check:** Before each phase transition, review the Model Assistance field in all manifests (§3.2) to confirm no prohibited automation was used.

---

**End of Operations Manual**
