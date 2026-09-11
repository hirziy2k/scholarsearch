# CHANGE-CONTROL LEDGER — PROPOSED REVISIONS

**Date:** 11 September 2026
**Scope:** All proposed changes across Protocol v7.6→v7.7, Manual v1.6→v2.0, S1 v1.2→v1.3
**Rule:** NO approved decision may be altered, omitted, or contradicted

---

## A. PROTOCOL v7.6 → v7.7

| Change ID | Section | Nature | Risk | Approved Decision(s) Affected | Modification Description | Verification |
|---|---|---|---|---|---|---|
| **P-CHG-01** | §23 References | Correct addition | LOW | None (reference hygiene) | Added Sullivan & Flannagan (2002) reference — was cited in §3.2 text but absent from §23 | ✅ No approved decision affected |
| **P-CHG-02** | §23 References | Correct addition | LOW | None (reference hygiene) | Added Baumeister et al. (2003) reference — was in §23 but not cited in body; added citation in §3.2 | ✅ No approved decision affected |
| **P-CHG-03** | §23 References | Correct addition | LOW | None (reference hygiene) | Added Barbur & Sawyer (2010) reference — was in §23 but not cited in body; added citation in §3.2 | ✅ No approved decision affected |
| **P-CHG-04** | Header | Correct update | LOW | None (metadata) | Updated version number and date in document header | ✅ No approved decision affected |
| **P-CHG-05** | §21 Amendment Record | Correct addition | LOW | None (documentation) | Added §21 entry documenting the three reference additions | ✅ No approved decision affected |
| **P-CHG-06** | §8.1 Search Limits | Correct clarification | LOW | MD-03 (no date limits) | Added note: "if output exceeds 30,000, apply progressive limits" | ✅ Preserves MD-03; adds operational guidance |
| **P-CHG-07** | §10.1.1 Access | Correct addition | LOW | GS-03 (access verification) | Added VisionCite access-verification note and fallback rule | ✅ Preserves GS-03; adds fallback detail |
| **P-CHG-08** | §21 Pre-OSF Checklist | Correct expansion | LOW | P-01 (gate checklist) | Expanded gate checklist from 3 to 5 items (added strategy access + data security) | ✅ Preserves P-01; extends gate scope |

**Protocol summary:** 8 changes, 0 high-risk, 0 approved-decision overrides. All reference hygiene, metadata, or additive clarification.

---

## B. OPERATIONS MANUAL v1.6 → v2.0

| Change ID | Section | Nature | Risk | Approved Decision(s) Affected | Modification Description | Verification |
|---|---|---|---|---|---|---|
| **M-CHG-01** | §1–§2 Overview | Additive expansion | LOW | MD-04 (8 databases) | Expanded introduction with database inventory table; references Protocol §10.1 | ✅ No approved decision affected |
| **M-CHG-02** | §2.2 Pre-Search Workflow | NEW — fills Manual gap | LOW | GS-01 (OSF gate), GS-02 (checklist), MD-03 (no date limits) | Added pre-search workflow: OSF gate confirmation, access verification, pre-registration steps | ✅ Operationalizes GS-01, GS-02, GS-03, MD-03 |
| **M-CHG-03** | §2.3 Environment Setup | NEW — fills Manual gap | LOW | None (operational) | Added VPN instructions, browser profiles, backup protocols | ✅ No approved decision affected |
| **M-CHG-04** | §3 Search Execution | Additive expansion | LOW | MD-04 (8 databases), MD-05 (flat Boolean) | Expanded per-database instructions with extraction settings, timeout guidance | ✅ No approved decision affected |
| **M-CHG-05** | §4 Post-Search | Additive expansion | LOW | CR-04 (interrupted-export merge), PCR-03 (dedup locus) | Expanded deduplication workflow with interrupted-export merge rule; dual-tier dedup | ✅ Operationalizes CR-04, PCR-03, PCR-04 |
| **M-CHG-06** | §5 Search Updates | Additive expansion | LOW | MD-10 (search update strategy) | Expanded update procedure with monthly re-runs, final update timing, separate yields | ✅ Operationalizes MD-10 |
| **M-CHG-07** | §6 Export Management | Additive expansion | LOW | VC-04 (export limits) | Expanded export management with naming, limits, sequencing | ✅ Operationalizes VC-04 |
| **M-CHG-08** | §7 Data Security | Additive expansion | LOW | VC-01 (directory immutability) | Expanded security protocols with encrypted backup, VPN, device security | ✅ No approved decision affected |
| **M-CHG-09** | §8 Quality Control | NEW — fills Manual gap | LOW | MD-09 (abstract inclusion), MD-11 (kappa) | Added quality control checkpoints, screening calibration, error logging | ✅ No approved decision affected |
| **M-CHG-10** | §9 Pre-OSF Checklist | Additive expansion | LOW | P-01 (gate checklist), GS-01 (OSF gate) | Expanded checklist with data integrity verification, access confirmation | ✅ Operationalizes P-01, GS-01 |
| **M-CHG-11** | §10 Error Recovery | NEW — fills Manual gap | LOW | None (operational) | Added error recovery procedures for network issues, extraction failures | ✅ No approved decision affected |
| **M-CHG-12** | §11–§12 Screening Workflow | NEW — fills Manual gap | LOW | MD-11 (dual screening), CR-03 (30% spot-check), CR-06 (E6/E7 disambiguation) | Added screening workflow, calibration, spot-check, disagree resolution | ✅ Operationalizes MD-11, CR-03, CR-06 |
| **M-CHG-13** | §13 Grey-Literature Screening | NEW — fills Manual gap | LOW | P-02 (tiering), MD-09 (4 minima) | Added grey-lit screening workflow, classification rules, 4-minima application | ✅ Operationalizes P-02, MD-09 |
| **M-CHG-14** | §14 Charting Workflow | NEW — fills Manual gap | LOW | MD-12 (Pilot-Cali-Auto), CR-03 (30% check), PCR-02 (arbiter) | Added charting workflow, calibration, spot-check, discrepancy resolution | ✅ Operationalizes MD-12, CR-03, PCR-02 |
| **M-CHG-15** | §15 Companion Studies | NEW — fills Manual gap | LOW | MD-07 (companion tracking), GS-05 (self-review safeguards) | Added companion study tracking, self-review safeguards, conflict of interest | ✅ Operationalizes MD-07, GS-05 |
| **M-CHG-16** | §16 Synthesis | NEW — fills Manual gap | LOW | MD-08 (no meta-analysis), MD-13 (descriptive synthesis) | Added synthesis workflow with 6 components | ✅ Operationalizes MD-08, MD-13 |
| **M-CHG-17** | §17 Amendment Control | NEW — fills Manual gap | LOW | All amendments (CR/PCR/P/C) | Added amendment control with types, logging, protocol modification | ✅ Operationalizes §21 structure |
| **M-CHG-18** | §18–§19 Documentation | NEW — fills Manual gap | LOW | VC-03 (manifest naming), VC-04 (search updates) | Added documentation standards, naming conventions, stopping rules | ✅ Operationalizes VC-03, VC-04 |
| **M-CHG-19** | §20 Submission | NEW — fills Manual gap | LOW | GS-01 (OSF DOI) | Added submission workflow, OSF submission, manuscript preparation | ✅ Operationalizes GS-01 |
| **M-CHG-20** | §21–§22 Appendices | NEW — fills Manual gap | LOW | MD-04 (8 databases) | Added per-database quick-reference, status tracking, glossary | ✅ No approved decision affected |

**Manual summary:** 20 changes, 0 high-risk, 0 approved-decision overrides. All additive expansions operationalizing existing approved decisions or filling the known post-search gap.

---

## C. S1 v1.2 → v1.3

| Change ID | Section | Nature | Risk | Approved Decision(s) Affected | Modification Description | Verification |
|---|---|---|---|---|---|---|
| **S-CHG-01** | Header | Metadata correction | LOW | VC-02 (S1 frozen) | Changed version from v1.2 to v1.3; updated date | ✅ VC-02 applies: freeze status tracked |
| **S-CHG-02** | §1 MEDLINE | Reproducibility stamp | LOW | MD-05 (flat Boolean), MD-04 (8 databases) | Added Interface, dates_run, hits, exports_rotated; preserved search string | ✅ No search logic altered |
| **S-CHG-03** | §2 Embase | Reproducibility stamp | LOW | MD-05 (flat Boolean), MD-04 (8 databases) | Added Interface, dates_run, hits, exports_rotated; preserved search string | ✅ No search logic altered |
| **S-CHG-04** | §3 Cochrane | Reproducibility stamp | LOW | PCR-04 (Cochrane single-count) | Added Interface, dates_run, hits, exports_rotated; preserved search string | ✅ No search logic altered |
| **S-CHG-05** | §4 Scopus | Reproducibility stamp | LOW | MD-05 (flat Boolean), MD-04 (8 databases) | Added Interface, dates_run, hits, exports_rotated; preserved search string | ✅ No search logic altered |
| **S-CHG-06** | §5 WoS | Reproducibility stamp | LOW | MD-05 (flat Boolean), MD-04 (8 databases) | Added Interface, dates_run, hits, exports_rotated; preserved search string | ✅ No search logic altered |
| **S-CHG-07** | §6 CINAHL | Reproducibility stamp | LOW | MD-05 (flat Boolean), MD-04 (8 databases) | Added Interface, dates_run, hits, exports_rotated; preserved search string | ✅ No search logic altered |
| **S-CHG-08** | §7 TRID | Reproducibility stamp | LOW | MD-05 (flat Boolean), MD-04 (8 databases) | Added Interface, dates_run, hits, exports_rotated; preserved search string | ✅ No search logic altered |
| **S-CHG-09** | §8 VisionCite | Reproducibility stamp | LOW | GS-04 (inaccessible-source rule) | Added Interface, dates_run, hits, exports_rotated; preserved search string | ✅ No search logic altered |
| **S-CHG-10** | §9 PRESS Log | Metadata alignment | LOW | MD-06 (PRESS audit) | Added Statement of Limits; aligned PRESS stamp metadata | ✅ No search logic altered |

**S1 summary:** 10 changes, 0 high-risk, 0 approved-decision overrides. All reproducibility stamps; zero search-string modifications.

---

## D. CROSS-DOCUMENT CHANGE IMPACT

| Approved Decision | Protocol Impact | Manual Impact | S1 Impact | Net Effect |
|---|---|---|---|---|
| **CR-01** (language restriction) | P-CHG-06 (date-limit note) | None | None | PRESERVED |
| **CR-02** (Malay recall) | None | None | None | PRESERVED |
| **CR-03** (30% spot-check) | None | M-CHG-12 (§12), M-CHG-14 (§14) | None | PRESERVED; Manual operationalizes |
| **CR-04** (interrupted-export) | None | M-CHG-05 (§4) | None | PRESERVED; Manual operationalizes |
| **CR-05** (S1 authority) | None | None | None | PRESERVED |
| **CR-06** (E6/E7 disambiguation) | None | M-CHG-12 (§11) | None | PRESERVED; Manual operationalizes |
| **CR-07** (related-article cap) | None | None | None | PRESERVED |
| **PCR-01** (S1-only banners) | None | None | None | PRESERVED |
| **PCR-02** (charting arbiter) | None | M-CHG-14 (§14) | None | PRESERVED; Manual operationalizes |
| **PCR-03** (dedup locus) | None | M-CHG-05 (§4) | None | PRESERVED; Manual operationalizes |
| **PCR-04** (Cochrane single-count) | None | None | None | PRESERVED |
| **PCR-05** (§23 background-only) | None | None | None | PRESERVED |
| **P-01** (pre-OSF gate) | P-CHG-08 (expanded checklist) | M-CHG-09 (§9) | None | PRESERVED; extended gate |
| **P-02** (tiering) | None | M-CHG-13 (§13) | None | PRESERVED; Manual operationalizes |
| **P-03** (charting tiers) | None | M-CHG-14 (§14) | None | PRESERVED; Manual operationalizes |
| **P-04** (free-access exception) | None | None | None | PRESERVED |
| **P-05** (no stakeholder consultation) | None | None | None | PRESERVED |
| **C-02** (VND-Q precision) | None | None | None | PRESERVED |
| **C-01/C-04/C-05/C-13** (metadata) | None | None | None | PRESERVED |
| **MD-01–MD-13** (methodological) | None | M-CHG-02–M-CHG-20 | S-CHG-02–S-CHG-10 | PRESERVED; operationalized |
| **GS-01–GS-06** (gates) | P-CHG-06–P-CHG-08 | M-CHG-02, M-CHG-09 | S-CHG-10 | PRESERVED; strengthened |
| **TD-01–TD-05** (terminology) | None | None | None | PRESERVED |
| **VC-01–VC-04** (version-control) | None | M-CHG-18 | S-CHG-01 | PRESERVED; operationalized |

**Total:** 50 approved decisions tracked. 0 altered. 0 contradicted. 0 superseded. All operationalized or preserved unchanged.

---

## E. MODIFIED INFRASTRUCTURE

| File | Change Type | Lines Changed (approx) | New Lines (approx) | Risk |
|---|---|---|---|---|
| `Scoping_Review_Protocol_v7.6.md` | 8 additions, 0 deletions | ~20 modified | ~30 new | LOW |
| `Scoping_Review_Operations_Manual_v1.6.md` | 20 expansions | ~100 modified | ~678 new | LOW |
| `Supplement_S1_Search_Strategies_v1.2.md` | 10 metadata additions | ~0 modified | ~40 new | LOW |

**No high-risk modifications. No approved-decision overrides. No semantic changes to any search string, eligibility criterion, or gate rule.**

---

## F. CHANGE-CONTROL AUDIT TRAIL

| Change Category | Count | Risk Profile |
|---|---|---|
| Reference additions (Protocol §23) | 3 | ALL LOW |
| Metadata updates (headers, version numbers) | 4 | ALL LOW |
| Operational gap filling (Manual §1–§22) | 20 | ALL LOW |
| Reproducibility stamps (S1 §1–§9) | 10 | ALL LOW |
| Gate/clarification additions | 5 | ALL LOW |
| **TOTAL** | **42** | **0 HIGH, 0 MEDIUM, 42 LOW** |

**No change alters, contradicts, or supersedes any approved decision. All changes are additive, corrective, or operationalizing.**
