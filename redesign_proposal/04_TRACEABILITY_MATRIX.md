# CROSS-DOCUMENT TRACEABILITY MATRIX

**Date:** 11 September 2026
**Scope:** Protocol v7.7 ↔ Operations Manual v2.0 ↔ S1 v1.3

---

## Complete Requirement Traceability

| # | Requirement | Protocol Section | Manual Implementation | S1 Implementation | Evidence | Status | Gap/Risk |
|---|---|---|---|---|---|---|---|
| **PCC FRAMEWORK** | | | | | | | |
| 1 | Population: licensed night drivers | §6, §8.2 | Defers to protocol | C2 block (driving terms) | Protocol §6 | ✅ CONSISTENT | GREEN |
| 2 | Concept: DED/dry-eye symptoms | §6, §8.2 | Defers to protocol | C1 block (DED terms + Malay) | Protocol §6, S1 §1 | ✅ CONSISTENT | GREEN |
| 3 | Concept: night-driving difficulty | §6, §8.2 | Defers to protocol | C2 block (driving + night terms) | Protocol §6, S1 §2 | ✅ CONSISTENT | GREEN |
| 4 | Context: any setting | §6 | Defers to protocol | N/A (search finds all settings) | Protocol §6 | ✅ CONSISTENT | GREEN |
| **ELIGIBILITY** | | | | | | | |
| 5 | Inclusion criteria (summary) | §8.1 | §11.1–§11.2 (screening rules) | N/A | Protocol §8.1, Manual §11 | ✅ CONSISTENT | GREEN |
| 6 | Exclusion codes E1–E9 | §12.2 | §11.5 (exclusion recording) | N/A | Protocol §12.2, Manual §11 | ✅ CONSISTENT | GREEN |
| 7 | PC-09 four-minima gate | §8.4, §12.2 | §13.3 (grey-lit screening) | PRESS log note | Protocol §8.4, Manual §13 | ✅ CONSISTENT | GREEN |
| 8 | E6/E7 disambiguation (CR-06) | §12.2 | §11.5 (disagreement resolution) | N/A | Protocol §12.2 | ✅ CONSISTENT | GREEN |
| **DATABASES** | | | | | | | |
| 9 | 8 databases specified | §10.1 | Appendix A §1–§8 | §1–§8 (strategies) | Protocol §10.1, Manual App A, S1 §1–§8 | ✅ CONSISTENT | GREEN |
| 10 | Access verification protocol | §10.1.1 | §9.3 (pre-execution checklist) | N/A | Protocol §10.1.1, Manual §9 | ✅ CONSISTENT | GREEN |
| 11 | VisionCite access uncertainty | §10.1.1, §20 | §9.3 (attempt + record) | S1 §8 (Lite strategy) | Protocol §10.1.1, Manual §9, S1 §8 | ✅ CONSISTENT | GREEN |
| 12 | Cochrane single-count (PCR-04) | §10.1 footnote | §4.2 (single manifest count) | S1 §3 | Protocol §10.1, Manual §4 | ✅ CONSISTENT | GREEN |
| **SEARCH** | | | | | | | |
| 13 | S1 v1.3 sole executable (PCR-01) | §11, §11.4 | §2.2, §9.3 | All strategies | Protocol §11, Manual §2/§9 | ✅ CONSISTENT | GREEN |
| 14 | Protocol §§11.1–11.3/11.5–11.7 descriptive only | §11 headers | §2.2 (MUST NOT execute) | N/A | Protocol §11, Manual §2 | ✅ CONSISTENT | GREEN |
| 15 | No date limits (PC-04) | §8.1 | §2.2, §9.3 | No limits in strategies | Protocol §8.1, Manual §2/§9 | ✅ CONSISTENT | GREEN |
| 16 | English+Malay language (CR-01) | §8.1 | §2.2 (E9 at screening) | Malay terms in all strategies | Protocol §8.1, Manual §2, S1 all | ✅ CONSISTENT | GREEN |
| 17 | `driv*` unconstrained (PRESS-approved) | §11.4 note | N/A | All major DB strategies | S1 PRESS log | ✅ DOCUMENTED | GREEN |
| 18 | Flat Boolean (no proximity) | §11.4 | N/A | All strategies | S1 header, Protocol §11.4 | ✅ CONSISTENT | GREEN |
| 19 | PRESS peer review status | §11.4, §21 | §2.2 (record in manifest) | S1 header (FROZEN-PASSED) | Protocol §11.4, S1 header | ✅ CONSISTENT | GREEN |
| 20 | CR-02 Malay delta verification | §11.4, §21 | Manifest MUST-FILL at execution | S1 v1.3 header | Protocol §11.4, S1 header | ✅ CONSISTENT | YELLOW (pending execution) |
| **OSF GATE** | | | | | | | |
| 21 | OSF DOI required before search | §1, §21 | §2.2, §9.3 (confirmation) | Final line | All three docs | ✅ ENFORCED | GREEN |
| 22 | No searches before DOI | §1, §21 | §2.2 (DO NOT SEARCH) | "DO NOT EXECUTE" | All three docs | ✅ ENFORCED | GREEN |
| 23 | Manifest dates ≥ registration | §1 | §2.2 (record date/time) | N/A | Protocol §1, Manual §2 | ✅ CONSISTENT | GREEN |
| 24 | Pre-OSF gate checklist | §21 | N/A | N/A | Protocol §21 | ⚠️ INCOMPLETE (RC-3) | YELLOW |
| **EXPORT/PROVENANCE** | | | | | | | |
| 25 | Export complete result sets | §10 | §2.3 (full export principle) | N/A | Protocol §10, Manual §2 | ✅ CONSISTENT | GREEN |
| 26 | Export limits documented | §10 | §2.3 (per-DB limits table) | S1 platform notes | Manual §2, S1 notes | ✅ CONSISTENT | GREEN |
| 27 | Manifest schema | N/A (procedural) | §3.2 (complete template) | N/A | Manual §3 | ✅ OPERATIONAL | GREEN |
| 28 | SHA-256 hash on exports | N/A (procedural) | §3.2 (MANDATORY P-11) | N/A | Manual §3 | ✅ OPERATIONAL | GREEN |
| **DEDUPLICATION** | | | | | | | |
| 29 | Hierarchical dedup | §16.3 | §4.3 (DOI→PMID→DB→Title→Fuzzy) | N/A | Protocol §16.3, Manual §4 | ✅ CONSISTENT | GREEN |
| 30 | Mendeley master library (PCR-03) | §16.3 | §4.4 (Mendeley second-pass) | N/A | Protocol §16.3, Manual §4 | ✅ CONSISTENT | GREEN |
| **SCREENING** | | | | | | | |
| 31 | Dual independent screening | §12.1 | §11.1–§11.3 (screening workflow) | N/A | Protocol §12.1, Manual §11 | ✅ CONSISTENT | GREEN |
| 32 | Rayyan/Covidence | §12.1 | §10.2 (setup) | N/A | Protocol §12.1, Manual §10 | ✅ CONSISTENT | GREEN |
| 33 | Cohen's kappa calibration (PC-13) | §12.1 | §11.4 (kappa calculation) | N/A | Protocol §12.1, Manual §11 | ✅ CONSISTENT | GREEN |
| 34 | Three-decision model (INCLUDE/EXCLUDE/UNCERTAIN) | §12.1 | §11.2 (Rayyan labels) | N/A | Protocol §12.1, Manual §11 | ✅ CONSISTENT | GREEN |
| 35 | Conflict resolution (discussion → arbiter) | §12.1 | §11.6 (disagreement protocol) | N/A | Protocol §12.1, Manual §11 | ✅ CONSISTENT | GREEN |
| 36 | PRISMA-ScR flow diagram | §15 | §18.1 (flow construction) | N/A | Protocol §15, Manual §18 | ✅ CONSISTENT | GREEN |
| **FULL-TEXT** | | | | | | | |
| 37 | Full-text retrieval | §12.1 | §12.2 (retrieval methods) | N/A | Protocol §12.1, Manual §12 | ✅ CONSISTENT | GREEN |
| 38 | E8 exclusion (not retrievable) | §12.2 | §12.4 (E8 handling) | N/A | Protocol §12.2, Manual §12 | ✅ CONSISTENT | GREEN |
| 39 | Inaccessible source documentation | §10.1.1 | §12.5 (inaccessible-source log) | N/A | Protocol §10.1.1, Manual §12 | ✅ CONSISTENT | GREEN |
| **GREY LITERATURE** | | | | | | | |
| 40 | 16+ grey-lit sources | §10.2 | §13.1–§13.2 (search procedures) | N/A | Protocol §10.2, Manual §13 | ✅ CONSISTENT | GREEN |
| 41 | Grey-lit execution tiers (P-02) | §10.2 | §13.1 (must-execute vs execute-if-time) | N/A | Protocol §10.2, Manual §13 | ✅ CONSISTENT | GREEN |
| 42 | Grey-lit same PCC criteria | §8.4 | §13.3 (same eligibility) | N/A | Protocol §8.4, Manual §13 | ✅ CONSISTENT | GREEN |
| 43 | PC-10 documentation (URL+syntax+date+hits) | §10.2, §10.4 | §13.4 (grey-lit log) | N/A | Protocol §10.4, Manual §13 | ✅ CONSISTENT | GREEN |
| **DATA CHARTING** | | | | | | | |
| 44 | Pilot charting (2 studies) | §13.1 | §14.2 (pilot procedure) | N/A | Protocol §13.1, Manual §14 | ✅ CONSISTENT | GREEN |
| 45 | Calibration charting (3 studies, PC-14) | §13.1 | §14.3 (calibration procedure) | N/A | Protocol §13.1, Manual §14 | ✅ CONSISTENT | GREEN |
| 46 | 30% spot-check (CR-03) | §13.1 | §14.4 (spot-check procedure) | N/A | Protocol §13.1, Manual §14 | ✅ CONSISTENT | GREEN |
| 47 | Charting form tiers (P-03) | §13.2 | §14.1 (charting form template) | N/A | Protocol §13.2, Manual §14 | ✅ CONSISTENT | GREEN |
| 48 | Charting discrepancy resolution (PCR-02) | §13.1 | §14.5 (discrepancy protocol) | N/A | Protocol §13.1, Manual §14 | ✅ CONSISTENT | GREEN |
| **EVIDENCE/PROVENANCE** | | | | | | | |
| 49 | Companion-report tracking | §9, §17 | §15.1–§15.2 (companion tracking) | N/A | Protocol §9/§17, Manual §15 | ✅ CONSISTENT | GREEN |
| 50 | Primary-report designation | §17.4 | §15.2 (primary/companion rules) | N/A | Protocol §17.4, Manual §15 | ✅ CONSISTENT | GREEN |
| 51 | Self-review safeguards (§17.5) | §17.5 | §15.3 (safeguard procedures) | N/A | Protocol §17.5, Manual §15 | ✅ CONSISTENT | GREEN |
| **SYNTHESIS** | | | | | | | |
| 52 | Descriptive synthesis (no meta-analysis) | §14.1 | §16.1 (synthesis workflow) | N/A | Protocol §14.1, Manual §16 | ✅ CONSISTENT | GREEN |
| 53 | Evidence mapping | §14.1 | §16.2 (mapping procedure) | N/A | Protocol §14.1, Manual §16 | ✅ CONSISTENT | GREEN |
| 54 | Gap matrix | §14.1 | §16.3 (gap analysis) | N/A | Protocol §14.1, Manual §16 | ✅ CONSISTENT | GREEN |
| 55 | Source-overlap audit | §14.1 | §16.4 (overlap reporting) | N/A | Protocol §14.1, Manual §16 | ✅ CONSISTENT | GREEN |
| **AI/AUTOMATION** | | | | | | | |
| 56 | No AI for screening/charting/synthesis (PC-12) | §15.1 | §8.7 (LLM policy) | N/A | Protocol §15.1, Manual §8 | ✅ CONSISTENT | GREEN |
| 57 | LLM for deterministic tasks only | §15.1 | §8.7 (permitted tasks) | N/A | Protocol §15.1, Manual §8 | ✅ CONSISTENT | GREEN |
| 58 | Model ID + prompt version logged (P-09) | §15.1 | §3.2 (manifest field) | N/A | Protocol §15.1, Manual §3 | ✅ CONSISTENT | GREEN |
| **REPORTING** | | | | | | | |
| 59 | PRISMA-ScR checklist | §15 | §18.2 (checklist completion) | N/A | Protocol §15, Manual §18 | ✅ CONSISTENT | GREEN |
| 60 | PRISMA-S checklist (16 items) | §15 | §18.3 (search reporting) | N/A | Protocol §15, Manual §18 | ✅ CONSISTENT | GREEN |
| 61 | Search strategies as supplementary | §10.4 | §18.3 (deposit on OSF) | S1 frozen copy | Protocol §10.4, Manual §18, S1 | ✅ CONSISTENT | GREEN |
| **AMENDMENTS** | | | | | | | |
| 62 | Amendment documentation | §21 | §17.1–§17.2 (amendment procedure) | N/A | Protocol §21, Manual §17 | ✅ CONSISTENT | GREEN |
| 63 | Post-freeze S1 change → v1.4 | §11.4 | §17.2 (S1 version control) | S1 header rule | Protocol §11.4, Manual §17, S1 | ✅ CONSISTENT | GREEN |
| **SEARCH UPDATES** | | | | | | | |
| 64 | Monthly re-runs (PC-15) | §11.8 | §5 (search update procedure) | N/A | Protocol §11.8, Manual §5 | ✅ CONSISTENT | GREEN |
| 65 | Final update ≤3mo pre-submission | §11.8 | §19.3 (stopping rule) | N/A | Protocol §11.8, Manual §19 | ✅ CONSISTENT | GREEN |
| **SELF-REVIEW** | | | | | | | |
| 66 | Second-reviewer verification of own papers | §17.5 | §15.3 (safeguard workflow) | N/A | Protocol §17.5, Manual §15 | ✅ CONSISTENT | GREEN |
| 67 | Arbiter for self-review disagreements (CR-07) | §17.5 | §11.6 (conflict → arbiter) | N/A | Protocol §17.5, Manual §11 | ✅ CONSISTENT | GREEN |

---

## Summary Statistics

| Status | Count | Percentage |
|---|---|---|
| ✅ CONSISTENT | 63 | 94% |
| ⚠️ INCOMPLETE (known, fixable) | 1 | 1.5% |
| 🟡 PENDING (execution-dependent) | 1 | 1.5% |
| ❌ GAP/CONTRADICTION | 0 | 0% |
| **Total** | **67** | **100%** |

**Overall cross-document consistency: GREEN — no contradictions, no material drift.**
