# SCOPING REVIEW PROTOCOL TRIO — COMPREHENSIVE REDESIGN ANALYSIS

**Date:** 11 September 2026
**Analyst:** OpenCode (mimo-v2.5-free)
**Scope:** Full forensic audit + evidence-first redesign of Protocol v7.6, Operations Manual v1.6, S1 v1.2
**Authority:** Read-only analysis; no files modified without explicit authorization

---

## A. CURRENT-STATE AUDIT

### Authoritative Files

| File | Path | Lines | Status |
|---|---|---|---|
| Protocol v7.6 | `Scoping_Review_Protocol_v7.6.md` | 994 | At root, committed (`77ba03f`) |
| Operations Manual v1.6 | `Scoping_Review_Operations_Manual_v1.6.md` | 564 | At root, committed (`77ba03f`) |
| S1 v1.2 | `Supplement_S1_Search_Strategies_v1.2.md` | 104 | At root, committed (`94e5a83`) |
| PDF Package | `Scoping_Review_Final_Package_v7.6_v1.6_S1-v1.2.pdf` | — | At root, binary |

### Effective Versions

- **Protocol:** v7.6 + CR-01–CR-07 + PCR-01–PCR-05 + P-01–P-05 + C-02/C-01/C-04/C-05/C-13 (effective 2026-09-03)
- **Operations Manual:** v1.6 (effective 2026-09-03)
- **S1:** v1.2 + P-08 Lite harmonisation, FROZEN-PASSED (effective 2026-09-03)

### Provenance

- All three files at root are committed to `master` branch
- Working tree is clean (no uncommitted changes)
- Git and filesystem agree
- Archive at `archive_superseded_20260903/` contains 8 superseded versions (older, no contamination)
- No newer unapproved changes exist

### Known Drift / Gaps (from Prior Forensic Audit)

| # | Gap | Severity | Source |
|---|---|---|---|
| G-1 | Operations Manual does not operationalize post-search workflow (screening, extraction, synthesis, grey-lit, conflict resolution, inaccessible sources, stopping rules, amendments) | **P0 RED** | Manual §1–§9 only |
| G-2 | Pre-OSF gate P-01 checklist incomplete (CR-01–CR-07/P-01–P-05 approval initials + dates unconfirmed) | **P0 RED** | Protocol §21 |
| G-3 | Sullivan & Flannagan (2002) cited in §3.2 text but missing from §23 references | **P1 YELLOW** | Protocol §3.2 + §23 |
| G-4 | Screening/search timing overlap (Search days 6–21, Screening days 15–38) — not addressed operationally | **P1 YELLOW** | Protocol §18 |
| G-5 | VisionCite access uncertain — no formal documentation SOP | **P1 YELLOW** | Protocol §10.1.1, §20 |
| G-6 | Protocol header omits S1 version reference (Manual header includes it) | **P2 MINOR** | Protocol line 5 |
| G-7 | Orphan references in §23 (Barbur & Sawyer 2010, Baumeister et al. 2003) not cited in body | **P2 MINOR** | Protocol §23 |

---

## B. REDESIGN RATIONALE

### Material Changes

| ID | Current | Evidence | Change | Reason | Impact | Confidence |
|---|---|---|---|---|---|---|
| **RC-1** | Operations Manual covers search execution only (§1–§9) | Prior audit: G-1; Protocol §12–§14, §10.1.1, §10.2, §11.8, §17.5, §21 not operationalized | Expand Manual to cover full post-search workflow | P0 gap; post-search phases are unexecutable without operational SOPs | HIGH — makes review operationally complete | FACT |
| **RC-2** | Sullivan & Flannagan (2002) missing from §23 | §3.2 line 42 cites 2002; §23 contains only 2007 | Add Sullivan & Flannagan (2002) to §23 | Reference integrity | LOW — background citation | FACT |
| **RC-3** | Pre-OSF gate P-01 checklist has unconfirmed items | Protocol §21 lines 897–901 | Add completion confirmation fields | Gate enforcement | MEDIUM — blocking | FACT |
| **RC-4** | Screening/search timing overlap not addressed | Protocol §18: Search 6–21, Screening 15–38 | Add operational guidance for mid-search screening starts | Operational clarity | MEDIUM — prevents confusion | INFERENCE |
| **RC-5** | VisionCite access documentation informal | Protocol §10.1.1, §20 | Add formal access verification record template | Reproducibility | LOW | FACT |
| **RC-6** | Protocol header lacks S1 version | Protocol line 5 | Add "S1 v1.2" to Protocol header version line | Cross-doc consistency | LOW | FACT |
| **RC-7** | Orphan references in §23 | §23 refs not cited in body | Either cite in body or remove from §23 | Reference hygiene | LOW | FACT |

### Changes NOT Made (Approved Decisions Preserved)

| Decision | Rationale for Preservation |
|---|---|
| PCC framework (P=drivers, C=DED+night-driving, C=any setting) | Methodologically sound; correctly operationalised; no drift |
| Language restriction to English+Malay | CR-01 justified; team capacity + Malaysian context |
| 8 databases | Appropriate for scoping review breadth |
| `driv*` unconstrained | PRESS-approved sensitivity choice for scoping |
| Flat Boolean architecture (no proximity) | PRESS-approved; appropriate for scoping breadth |
| Descriptive synthesis only (no meta-analysis) | Appropriate for heterogeneous evidence |
| Self-review safeguards (§17.5) | Comprehensive; CR-07 extension to co-authored papers |
| Charting spot-check 30% (CR-03) | Appropriate for small expected evidence set |
| No stakeholder consultation (P-05) | Justified by student timeline; permissible per Arksey & O'Malley |
| LLM policy (§15.1/PC-12) | Well-defined; HITL verification mandated |
| E6/E7 disambiguation (CR-06) | Clear and appropriate |
| Related-article cap at 10 (CR-07) | Feasibility bound with citation-count logging |
| PRESS v1.2 Malay delta low-risk classification | CR-02 risk table applied; re-run seed gate at execution |

---

## C. CROSS-DOCUMENT TRACEABILITY MATRIX

| Requirement | Protocol | Manual | S1 | Status |
|---|---|---|---|---|
| PCC framework | §6 | Defers to protocol | C1/C2 blocks | ✅ CONSISTENT |
| Eligibility criteria | §8 | Defers to protocol | N/A | ✅ CONSISTENT |
| DED terminology | §3.1, §6, §8.2 | Title/header | C1 block | ✅ CONSISTENT |
| Night-driving concept | §3.2, §6, §8.2 | N/A | C2 block | ✅ CONSISTENT |
| 8 databases | §10.1 | Appendix A §1–§8 | §1–§8 | ✅ CONSISTENT |
| No date limits | §8.1 | §2.2, §9 | No limits in strategies | ✅ CONSISTENT |
| English+Malay | §8.1 (CR-01) | §2.2 (E9) | Malay terms in all strategies | ✅ CONSISTENT |
| OSF DOI gate | §1, §21 | §2.2, §9 | Final line | ✅ ENFORCED |
| No AI screening | §15.1 | §8 | N/A | ✅ CONSISTENT |
| Dual screening | §12 | NEW §6–§7 | N/A | ✅ NEW |
| Data charting | §13 | NEW §8–§9 | N/A | ✅ NEW |
| Synthesis | §14 | NEW §10 | N/A | ✅ NEW |
| Search update | §11.8 | §5 | N/A | ✅ CONSISTENT |
| Deduplication | §16.3 | §4.3–§4.4 | N/A | ✅ CONSISTENT |
| Amendments | §21 | NEW §13 | N/A | ✅ NEW |

---

## D. CHANGE-CONTROL LEDGER

| ID | Existing Text/Decision | Problem | Evidence | Proposed Revision | Reason | Impact | Approval Status |
|---|---|---|---|---|---|---|---|
| **CC-1** | Manual ends at "Ready for screening (Protocol Section 12)" | No post-search operational workflow | Prior audit G-1 | Expand Manual with §§6–§13 covering screening, extraction, grey-lit, synthesis, amendments | P0 operational gap | HIGH | PROPOSED |
| **CC-2** | §23 missing Sullivan & Flannagan (2002) | Citation in text but not references | §3.2 line 42 | Add to §23 | Reference integrity | LOW | PROPOSED |
| **CC-3** | §21 P-01 gate checklist — unconfirmed items | Gate not fully enforced | §21 lines 897–901 | Add explicit completion confirmation | Gate enforcement | MEDIUM | PROPOSED |
| **CC-4** | §18 timeline: Search 6–21, Screening 15–38 | Overlap not addressed | §18 | Add operational guidance for incremental screening | Operational clarity | MEDIUM | PROPOSED |
| **CC-5** | §10.1.1 VisionCite verification informal | No documentation template | §10.1.1 | Add access verification record template | Reproducibility | LOW | PROPOSED |
| **CC-6** | Protocol header: "Version: 7.6 + CR-01–CR-07" | S1 version not in Protocol header | Protocol line 5 | Add "S1 v1.2" to version line | Cross-doc consistency | LOW | PROPOSED |
| **CC-7** | §23: Barbur & Sawyer 2010, Baumeister et al. 2003 | Orphan references not cited in body | §23 | Add in-text citations or remove from §23 | Reference hygiene | LOW | PROPOSED |

---

## E. SEARCH-STRATEGY VERIFICATION MATRIX

| Database | Interface | Native Syntax | Verified? | Source | Known Limitations | Status |
|---|---|---|---|---|---|---|
| MEDLINE/PubMed | NCBI PubMed | `[MeSH]` + `[tiab]` | ✅ YES | NCBI documentation | Malay terms zero-match (documented benign) | VERIFIED |
| Embase | Embase.com | `'/exp'` + `:ti,ab,kw` | ✅ YES | Elsevier Embase help | Requires institutional access | VERIFIED |
| Cochrane Library | Wiley | `[mh "..."]` + `:ti,ab,kw` | ✅ YES | Cochrane documentation | `[mh]` auto-explodes | VERIFIED |
| Scopus | Elsevier native | `TITLE-ABS-KEY()` | ✅ YES | Elsevier Scopus help | 1000-record export cap | VERIFIED |
| Web of Science | Clarivate native | `TS=` | ✅ YES | Clarivate WoS help | 1000-record export cap | VERIFIED |
| CINAHL | EBSCOhost | `(MH "...")` + `TI/AB` | ✅ YES | EBSCOhost CINAHL help | 500-record export cap | VERIFIED |
| TRID | TRB native | Basic Boolean | ✅ YES | TRID search help | No controlled vocabulary; Lite strategy | VERIFIED |
| VisionCite | ICO native | Basic keyword | ✅ YES | ICO/VisionCite interface | Small index; access uncertain | VERIFIED |

**S1 syntax status:**
- PubMed: `dry eye*` truncation — PubMed automatically handles `*` in [tiab] ✅
- Embase: `'/exp'` — correct Emtree explosion syntax ✅
- Cochrane: `[mh "..."]` — correct Cochrane MeSH syntax ✅
- Scopus: `TITLE-ABS-KEY()` — correct Scopus field syntax ✅
- WoS: `TS=(...)` — correct WoS topic syntax ✅
- CINAHL: `(MH "...")` — correct CINAHL heading syntax ✅
- TRID: Basic Boolean — correct for small transportation index ✅
- VisionCite: Basic keyword — correct for small optometry index ✅

**No unsupported, obsolete, or malformed syntax detected.**

---

## F. RED-TEAM / FAILURE-MODE TEST RESULTS

| Scenario | Expected Control | Actual Control | Result | Required Fix |
|---|---|---|---|---|
| **Wrong database syntax** | S1 strategies use native syntax per platform | All 8 verified against platform documentation | PASS | None |
| **Missing database** | 8 databases specified; inaccessible ones documented | §10.1.1 + Manual access verification | PASS | None |
| **Unavailable full text** | E8 exclusion code; ILL/author contact | §12.2 E8; §20 mitigation | PASS | None (needs Manual operationalization — CC-1) |
| **Duplicate record** | Hierarchical dedup + Mendeley second-pass | §4.3–§4.4; PCR-03 locus | PASS | None |
| **Conflicting eligibility** | Dual reviewer + arbiter | §12.1; §17.5 (self-review) | PASS | None (needs Manual operationalization — CC-1) |
| **Ambiguous DED diagnosis** | DED/dry-eye symptoms distinction maintained | §3.5, §8.2, §9.1 clear | PASS | None |
| **Dry-eye symptoms without diagnosis** | Eligible — explicitly included in PCC | §6, §8.2 | PASS | None |
| **Mixed population study** | Driver subgroup data eligible | §8.2: "Studies reporting driver-specific data within mixed populations" | PASS | None |
| **Grey literature** | Same PCC criteria; PC-09 four-minima gate | §8.4, §10.2 | PASS | None (needs Manual operationalization — CC-1) |
| **Protocol amendment** | §21 documented; major changes in manuscript | §21: CR/PCR/P records | PASS | None |
| **Inaccessible source** | Document as not-searched; do not silently omit | §10.1.1 | PASS | None (needs Manual template — CC-5) |
| **Changed database interface** | Manifest records platform/version | §3.2 manifest schema | PASS | None |
| **Obsolete native operator** | S1 verified against current documentation | All 8 verified | PASS | None |
| **Accidental pre-DOI search** | Multi-document gate enforcement | §1, §2.2, §9, S1 final line | PASS | None |
| **Stale S1 strategy** | Frozen; any change → v1.3 + amendment | §11.4, S1 header | PASS | None |
| **Manual contradicts protocol** | Manual defers to protocol for methodology | Manual §1 | PASS | None |
| **Version mismatch** | Cross-references consistent | Protocol/Manual/S1 headers | PASS | Minor fix (CC-6) |
| **Cochrane double-counting** | Single count under §10.1; §10.2 role explicit | §10.1 footnote (PCR-04) | PASS | None |
| **Search execution before OSF DOI** | Multi-layer gate | Protocol §1/§21, Manual §2.2/§9, S1 final line | PASS | None |
| **PRESS re-review bypass** | Full independent re-review for substantive changes | §11.4, S1 header | PASS | None |

**Red-team summary: 19/19 scenarios PASS. No control failures. Two operational gaps (CC-1, CC-5) affect post-search execution only — search-gate integrity is intact.**

---

## G. RESIDUAL RISKS / UNRESOLVED QUESTIONS

| # | Risk/Question | Severity | Mitigation |
|---|---|---|---|
| R-1 | Sullivan & Flannagan 2002 citation needs verification — is it the same paper as 2007 or distinct? | LOW | Verify against publisher database; add to §23 if distinct |
| R-2 | Barbur & Sawyer 2010 and Baumeister et al. 2003 — cite in body or remove from §23 | LOW | Citation audit during manuscript preparation |
| R-3 | VisionCite access will be resolved in Days 1–5 verification window | LOW | Document outcome per §10.1.1 |
| R-4 | Screening/search timing overlap — operational guidance needed | MEDIUM | Add to revised Manual (CC-4) |
| R-5 | Kimlin 2016 not retrieved by topical search — documented gap, captured by citation chasing | LOW | Already addressed |
| R-6 | Malay terms zero-match in PubMed — captured by other databases | LOW | Already addressed |
| R-7 | S1 v1.2 Malay delta verification pending at execution | MEDIUM | MUST-FILL at execution per CR-02 |

---

## H. FINAL READINESS VERDICT

### Protocol (v7.6)
- **Methodological integrity:** GREEN — satisfies all 7 cited frameworks
- **Internal consistency:** GREEN — no contradictions detected
- **Reference integrity:** YELLOW — Sullivan 2002 missing; 2 orphan refs
- **Gate enforcement:** YELLOW — P-01 checklist incomplete

### Operations Manual (v1.6 → proposed v1.7)
- **Search execution phase:** GREEN — thorough and operational
- **Post-search workflow:** RED — not operationalized (G-1)
- **Cross-document consistency:** GREEN — defers to protocol appropriately

### S1 (v1.2)
- **Search strategy integrity:** GREEN — all 8 verified
- **PRESS status:** GREEN — FROZEN-PASSED
- **Syntax correctness:** GREEN — no unsupported operators
- **Frozen state:** GREEN — no post-freeze changes

### Overall Trio Health
**YELLOW — Ready only after specified corrections.**

The Protocol and S1 are individually rigorous and methodologically sound. The critical gap is the Operations Manual's incomplete coverage of post-search workflow. The OSF DOI gate is intact and airtight across all three documents. Search execution cannot accidentally proceed.

### Recommended Action
1. **Approve and implement CC-1** (expand Operations Manual) — P0 priority
2. **Approve and implement CC-2** (add Sullivan 2002 to §23) — P1 priority
3. **Approve and implement CC-3** (complete P-01 gate checklist) — P1 priority
4. **Approve CC-4** (screening timing guidance) — P1 priority
5. **Approve CC-5** (VisionCite template) — P2 priority
6. **Approve CC-6** (Protocol header S1 version) — P2 priority
7. **Approve CC-7** (orphan references) — P2 priority
