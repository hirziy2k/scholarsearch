# SCOPING REVIEW OPERATIONS MANUAL

## Dry Eye Disease, Dry-Eye Symptoms, and Night-Driving Difficulty Among Drivers

**Protocol Reference:** Scoping_Review_Protocol_v7.0.md (v7.5 S1 v1.1 PRESS-passed; cleared for OSF)
**Version:** 1.5
**Date:** September 2026
**Status:** Pre-registration — DO NOT EXECUTE SEARCHES until OSF DOI issued (PC-05)

---

### Purpose

This manual defines the operational workflow for executing the scoping review search. It separates **infrastructure execution** from **methodological protocol**. The protocol dictates the science; this manual dictates the infrastructure.

**This document is not a substitute for the protocol.** All methodological decisions (eligibility criteria, search strategy, screening process, synthesis approach) are defined in `Scoping_Review_Protocol_v7.0.md` v7.5 (S1 v1.1 PRESS-passed; cleared for OSF).

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
    ├── extraction/                 # Completed charting CSVs
    └── reports/                    # Final tables, figures, PRISMA flow
```

### Rules

| Directory | Rule |
|---|---|
| `raw/` | **IMMUTABLE.** Never modify, overwrite, or delete files after download. |
| `manifests/` | **APPEND-ONLY.** New manifests are added; existing manifests are never edited. |
| `processed/` | **DERIVED.** Files here are generated from raw + manifest. Original source traceable. |
| `logs/` | **APPEND-ONLY.** Ingestion events are recorded chronologically. |

---

## 2. RemoteXs Extraction — Standard Operating Procedure

### 2.1 Access Route

```
UKM PTSL → eResources@PTSL → RemoteXs → [Database]
```

**Authentication:** Interactive, user-executed. No automated login. No credential storage.

### 2.2 Pre-Export Checklist

Before each database search:

- [ ] Navigate to eResources@PTSL via RemoteXs
- [ ] Confirm authenticated session is active
- [ ] Open target database
- [ ] Verify search interface is accessible
- [ ] Confirm OSF DOI issued — DO NOT SEARCH if no DOI (PC-05 gate)
- [ ] Confirm database access verified (PC-07); if inaccessible record as not-searched
- [ ] Enter approved search string (from Protocol Section 11 + Supplement S1 v1.1, including controlled vocab per PC-02/PC-03)
- [ ] Apply only protocol-approved filters/limits — NO date limits (PC-04)
- [ ] Record the **exact search string** used (copy verbatim) + Search Strategy Version (S1 v1.1)
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
| Protocol Version | 7.3 |
| Search Strategy ID | [e.g., Section 11.4 Master + S1 v1.1 PubMed] |
| Search Strategy Version | [e.g., S1 v1.1, PRESS date + initials] |
| Review Stage (PC-15/PC-17) | [Primary search / Update search N] |

## Execution

| Field | Value |
|---|---|
| Search Date | [YYYY-MM-DD] |
| Search Time | [HH:MM] |
| Time Zone | [e.g., GMT+8] |
| Executed By | [Name/initials] |

## Search Parameters

| Field | Value |
|---|---|
| Exact Search String | [Copy verbatim from database] |
| Fields Searched | [e.g., Title/Abstract/MeSH, Emtree, MH headings] |
| Filters/Limits Applied | [e.g., English, Malay, Human — NO date limits per PC-04] |
| Date Range (Applied Limits) | [None — record Database Coverage + Execution Date] |
| Database Coverage | [e.g., MEDLINE 1946–present; Embase 1947–present] |
| Language Limits | [e.g., English, Malay] |

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
| SHA-256 Hash | [Optional — for integrity verification] |

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
| 5 | Title similarity | Fuzzy match (Levenshtein distance > 90%) — manual review required |

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
2. **Save partial export** — keep the incomplete file in `raw/` with `_partial` suffix
3. **Resume** — continue export in next session
4. **Merge** — combine partial and complete exports into single raw file
5. **Update manifest** — document the interruption and recovery

Example:
```
scopus_2026-09-03_v1-batch1_partial.ris  (interrupted)
scopus_2026-09-03_v1-batch1_complete.ris (resumed and completed)
scopus_2026-09-03_v1-batch1.ris          (merged final)
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
| LLM/AI screening, eligibility, charting, synthesis | Protocol §15.1 (PC-12) — human judgement only; deterministic parsing/dedup/hashing/DOI-batch only |

---

## 9. Checklist — Complete Search Execution

### Per Database

- [ ] Confirm OSF DOI issued (PC-05 gate) + database access verified per §10.1.1 (PC-07); record accessible/inaccessible + reason
- [ ] Navigate to database via RemoteXs
- [ ] Execute approved search string (Protocol §11 + S1 v1.1 incl. controlled vocab)
- [ ] Apply protocol-approved filters (NO date limits per PC-04)
- [ ] Record exact search string + Strategy Version (S1 v1.1)
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
- [ ] Citation chasing completed (backward=all; forward=all via batch DOI; related=top-10 by citations; PC-08)
- [ ] All raw files in `raw/` with manifests
- [ ] All manifests in `manifests/`
- [ ] Ingestion QC passed
- [ ] Deduplication completed
- [ ] Records imported to Mendeley
- [ ] Ready for screening (Protocol Section 12)

---

## Appendix A: Database-Specific Export Instructions

### A.1 PubMed/MEDLINE

1. Run search in PubMed
2. Click "Save" → "All results on this page" or "All results"
3. Format: "NBIB" (or "MEDLINE")
4. Save to `raw/pubmed/`
5. File naming: `pubmed_ded_nightdriving_[YYYY-MM-DD].nbib`

### A.2 Scopus

1. Run search in Scopus
2. Click "Export" → "RIS" (or "CSV")
3. Select "All available" or "Selection" (if >1000, batch by year)
4. Save to `raw/scopus/`
5. File naming: `scopus_ded_nightdriving_[YYYY-MM-DD]_[batch].ris`

### A.3 Web of Science

1. Run search in Web of Science
2. Click "Export" → "Other file formats"
3. Format: "Plain text file" (Record Content: "Full Record and Cited References")
4. Save to `raw/web-of-science/`
5. File naming: `wos_ded_nightdriving_[YYYY-MM-DD]_[batch].txt`

### A.4 Embase

1. Run search in Embase
2. Click "Export" → "RIS" (or "CSV")
3. Select all results (or batch if >500)
4. Save to `raw/embase/`
5. File naming: `embase_ded_nightdriving_[YYYY-MM-DD]_[batch].ris`

### A.5 CINAHL

1. Run search in CINAHL (via EBSCOhost)
2. Click "Share" → "Add to folder" → "Export"
3. Format: "RIS"
4. Save to `raw/cinahl/`
5. File naming: `cinahl_ded_nightdriving_[YYYY-MM-DD]_[batch].ris`

### A.6 TRID

1. Run search in TRID (via EBSCOhost or ProQuest)
2. Export as RIS or CSV
3. Save to `raw/trid/`
4. File naming: `trid_ded_nightdriving_[YYYY-MM-DD].ris`

### A.7 VisionCite

1. Run search in VisionCite (if accessible)
2. Export as RIS or CSV
3. Save to `raw/visioncite/`
4. File naming: `visioncite_ded_nightdriving_[YYYY-MM-DD].ris`

---

## Appendix B: Manifest Example

```markdown
# SEARCH MANIFEST

## Identification

| Field | Value |
|---|---|
| Database | PubMed/MEDLINE |
| Provider/Platform | NCBI PubMed |
| Access Route | Free access (no RemoteXs required) |
| Protocol Version | 7.3 |
| Search Strategy ID | Section 11.4 Master + S1 v1.1 PubMed |
| Search Strategy Version | S1 v1.1, PRESS [date + initials] |
| Review Stage | Primary search |

## Execution

| Field | Value |
|---|---|
| Search Date | 2026-09-03 |
| Search Time | 14:30 |
| Time Zone | GMT+8 |
| Executed By | PJW |

## Search Parameters

| Field | Value |
|---|---|
| Exact Search String | (("dry eye"[tiab] OR "Dry Eye Syndromes"[MeSH] OR ...) AND ("night driving"[tiab] OR "Automobile Driving"[MeSH] OR ...) AND ("driver"[tiab] OR ...)) |
| Fields Searched | Title/Abstract/MeSH |
| Filters/Limits Applied | English, Malay, Human — NO date limits (PC-04) |
| Date Range (Applied Limits) | None — MEDLINE 1946–present, searched 2026-09-03 |
| Language Limits | English, Malay |

## Results

| Field | Value |
|---|---|
| Total Results Displayed | 47 |
| Records Exported | 47 |
| Export Complete? | YES |
| Export Limitation | None (PubMed allows up to 10,000) |
| Batch Strategy | Single batch |

## Export File

| Field | Value |
|---|---|
| Filename | pubmed_ded_nightdriving_2026-09-03.nbib |
| Format | NBIB |
| File Size | 156 KB |
| Record Count (verified) | 47 |
| SHA-256 Hash | a1b2c3d4e5f6... |

## Notes

No issues. Search returned 47 results; all exported in single batch.

---

**Manifest generated by:** PJW
**Manifest date:** 2026-09-03
```

---

**End of Operations Manual**
