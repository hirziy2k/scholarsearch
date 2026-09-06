# Malaysian Diploma in Opticianry — Full Document Harvest: Findings and Sources
**Comprehensive line-by-line extraction — 2 September 2026**
**Research/extraction only. Master Markdown not modified.**

> Base knowledge: Master Markdown `Malaysian Diploma in Opticianry - Master Regulatory & OBE Reference 2026.md` + deep-search gap audit + verbatim OCR. This harvest retrieves and reads the underlying source documents.

---

## 1. METHODOLOGY

- **Fetch:** `webfetch` on official domains `mqa.gov.my`, `www2.mqa.gov.my`, `hq.moh.gov.my/moc`, `lom.agc.gov.my`, `mqr`, plus `infosihat.moh.gov.my`. HTTP 200 verified. Direct PDF fetch via `ilims/upload/portal/akta/outputp/...` after decrypting `json-subsid` tokens.
- **Reading:** Text PDFs via `pdf-tools_textextraction__extract_text` inline=true (page-by-page). Scanned/image PDFs flagged, OCR via `pytesseract 5.4.0` at 300-400 dpi `--psm 6` (MOC-02 p8-9 verified, others partial). Scanned reprints (Act 469) remain unread beyond recitals.
- **Classification:** CURRENT / CURRENT GUIDANCE / MANDATORY / PROFESSIONAL / LEGAL / SUPERSEDED / DRAFT / ARCHIVED / PUBLIC-BUT-UNLINKED / UNVERIFIED. Hierarchy applied: Legislation/Gazette > MQA > MOC/MOH > MQR > other official.
- **Coverage:** 42 unique relevant documents (14 MQA + 8 MOC + 8 legal + 11 circulars + 1 MQR). 38 retrieved 200 OK. 34 fully examined page-by-page. 4 scanned/image-only partially examined.

---

## 2. MASTER DOCUMENT INVENTORY — COMPLETE

### MQA Core (7)

| ID | Authority | Document | Edition/Version | Pub Date | Effective | Status | Supersedes | DIO | URL |
|---|---|---|---|---|---|---|---|---|---|
| MQF-01 | MQA | Malaysian Qualifications Framework (MQF) Second Edition (2024) | 2nd Ed 2024 | 2024 | 1 Aug 2024 (Pek 5/2024) 2-yr transition | CURRENT | 2nd Ed 2017 | Direct L4 | https://www.mqa.gov.my/new/document/2024/new/MQF%20(2024).pdf (portal https://www.mqa.gov.my/new/mqf.cfm) 981,833B 50pp |
| MQF-02 | MQA | MQF Revised TVET L6 & MPU 19112025 | Addendum | 19 Nov 2025 | 19 Nov 2025 | Current supplement | - | Indirect articulation | https://www.mqa.gov.my/new/document/mqf/2025/MQF2ndedrevisedTVETL6&MPU19112025.pdf 370,325B |
| COPPA-01 | MQA | Code of Practice for Programme Accreditation (COPPA) Edition 2 | 2nd Ed 2017 updated Nov 2018 (verso 2019→2017) | 14 Jun 2021 update | 1 Apr 2018 (Pek 5/2017) | CURRENT | 1st Ed 2008 | Direct 7 Areas | https://www2.mqa.gov.my/qad/v2/2021/June/COPPA%202nd%20Ed%20110621.pdf 1,979,327B 132pp |
| COPPA-02 | MQA | Guidelines for Evaluation of Standards for COPPA + Rubrik 3C | Oct 2024 guideline + Pek Bil.4/2024 2 Jul 2024 | 2 Jul 2024 | 2 Jul 2024 | Current | - | Direct rubric | https://www2.mqa.gov.my/qad/v2/document/2024/Oct/Guidelines%20for%20Evaluation%20COPPA.pdf ; https://www.mqa.gov.my/new/document/2024/Pekeliling%20MQA%20Bil.%204_2024.pdf 223,565B |
| PS-MHS-01 | MQA | Programme Standards: Medical and Health Sciences | 2nd Ed 2016 (July 2019 PDF) | July 2019 | 1 Dec 2016 (Pek 2/2016) | CURRENT | 1st Ed 2013 | Direct benchmark | https://www2.mqa.gov.my/QAD/garispanduan/2019/July/PS%20Medical%20BI.pdf 2,283,668B 161pp + SP MHS - July 2019.pdf 2,381,533B |
| SUP-01 | MQA | Standards for Undergraduate Programme | 1st Ed 2025 | 27 Mar 2025 | 27 Mar 2025 (Pek 5/2025) | CURRENT | - | Direct (where PS silent) | https://www2.mqa.gov.my/qad/v2/pekeliling/2025/Standards%20for%20Undergraduate%20Programme%20V15_removed%20(1).pdf 906,850B 60pp |
| MQR-01 | MQA | Malaysian Qualifications Register | Current DB | 2026 | ongoing | Current | - | Verification | https://www.mqa.gov.my/mqr/ |

### MQA Guidelines to Good Practices (7)

| ID | Document | Version | Pub / Effective | Status | URL | Pages | DIO |
|---|---|---|---|---|---|---|---|
| GGP-AOSL | GGP: Assessment of Student Learning | 2nd Ed 2023 | 27 Dec 2023 (Surat 9/2023) 30 Nov 2023 effective | Current | https://www2.mqa.gov.my/qad/v2/2024/DOKUMEN%20GGP%20AOSL%209223%20FINAL%20V3.pdf 4,079,963B | 127pp | Direct |
| GGP-PDD | GGP: Programme Development and Delivery | 2nd Ed 2023 | Dec 2023 (Surat 8/2023) 30 Nov 2023 | Current | https://www2.mqa.gov.my/qad/v2/2023/Dec/GGP%20PDD%202023.pdf 5,877,843B | 96pp | Direct |
| GIVC | Guidelines for Industrial Verification of Curriculum | 2024 | 27 Feb 2024 (Pek 1/2024) | Current | https://www2.mqa.gov.my/qad/v2/2024/Final%20GIVC%20For%20Circulation%20Feb%202024.pdf 3,293,940B | 51pp | Direct |
| GWBL | Guidelines on Work-Based Learning | 2026 Ed | 7 Aug 2026 (Pek 3/2026) supersedes 2019 | CURRENT | https://www2.mqa.gov.my/qad/v2/2026/Aug/GWBL%202026.pdf 2,218,116B | 59pp | Direct WBL |
| GVBE | Guidelines on Values-Based Education | 2026 | 9 Jan 2026 (Surat 2/2026) | Current | https://www2.mqa.gov.my/qad/v2/2026/Guidelines%20on%20Values-Based%20Education%20(GVBE).pdf 3,284,647B | 143pp | Direct VBE |
| ABC | Guidelines on Academic Bank of Credit | 2026 | 23 Jun 2026 (Pek 2/2026) | Current | https://www2.mqa.gov.my/qad/v2/document/2026/%5BFINAL%5D%20MQA_Guidelines%20on%20the%20Academic%20Bank%20of%20Credit%20(ABC).pdf 875,365B | - | Indirect |
| IQAF-01/02 | Institutional Quality Audit Framework + Evaluation Guidelines | Edisi 2025 + 2026 Ed | 17 Dec 2025 (Pek 8/2025) + 28 Apr 2026 (Surat 6/2026) | Current (2025 superseded) | https://www2.mqa.gov.my/qad/v2/garispanduan/2025/IQAF_Edisi_2025.pdf 2,070,799B + .../2026/May/GUIDELINES...IQAF%202026.pdf 1,339,078B | - | Indirect institutional |

### MOC / MOH (8)

| ID | Document | Version | Pub Date | Status | URL | Type/Pages | DIO |
|---|---|---|---|---|---|---|---|
| MOC-01 | Code of Practice for Programme Accreditation Optometry/Opticianry Diploma V2.1 | V2.1 Jan 2025 | Jan 2025 (endorsed 10 May 2022) | CURRENT supersedes 2022 | https://hq.moh.gov.my/moc/wp-content/uploads/2025/01/NEW-Program-Standard-Vs-2.1-2025.pdf 2,487,805B | Text 225pp | MASTER |
| MOC-02 | Lampiran A Student Entry Requirement (New) | New Sep 2025 | Sep 2025 (Ricoh 2025-08-06) | CURRENT supersedes App p63 | https://hq.moh.gov.my/moc/wp-content/uploads/2025/09/Lampiran-A-pindaan-kelayakan-masuk-program-Optom-DIO.pdf 1,277,393B | **Scanned 9pp** (OCR) | Direct entry |
| MOC-03 | Guidelines for Implementation of Curriculum Changes | Oct 2024 | Oct 2024 | Current | https://hq.moh.gov.my/moc/wp-content/uploads/2024/10/Guidelines-For-The-Implementation-Of-Curriculum-Changes-Revision-In-OptometryOpticianry-Program-In-Higher-Education-Provider-PPT.pdf 1,440,555B | Scanned 5pp | Direct |
| MOC-04 | PQA Handbook for Optician Latest Version 2025 | Apr 2025 | Apr 2025 | Current | https://hq.moh.gov.my/moc/wp-content/uploads/2025/04/HANDBOOK-PQA-LATEST-VERSION-2025.pdf 337,401B | Text 15pp | Direct |
| MOC-05 | Candidate Handbook for Clinical Attachment | 2022 | 2022 | Current | https://hq.moh.gov.my/moc/wp-content/uploads/2022/03/Candidate-Handbook-for-Clinical-attachment.pdf 351,071B | Text 7pp | Indirect |
| MOC-06 | Code of Practice for Optometrist & Opticians BM | Jan 2024 | Jan 2024 | Current | https://hq.moh.gov.my/moc/wp-content/uploads/2024/01/CODE-OF-PRACTICE-FOR-OPTOMETRIST-AND-OPTICIANS-BM.pdf 1,538,060B | Scanned 11pp | Indirect ethics |
| MOC-07 | Online Sale Guidelines (GP PENJUALAN ONLINE) | Jun 2025 | Jun 2025 | Current | https://hq.moh.gov.my/moc/wp-content/uploads/2025/06/GP-PENJUALAN-ONLINE.pdf 247,830B | Text 6pp | Indirect |
| MOC-08 | Private Facilities Guidelines (GP FASILITI) | Jul 2024 | Jul 2024 | Current | https://hq.moh.gov.my/moc/wp-content/uploads/2024/07/GP-FASILITI-DAN-SERVIS-OPTOMETRI-SWASTA.pdf 270,061B | Text 12pp | Indirect facilities |

### Legal (8)

| ID | Document | P.U. No. | Pub / Made | Status | URL |
|---|---|---|---|---|---|
| LAW-01 | Optical Act 1991 Act 469 | Act 469 | 1991 (reprint 1 Jun 2017) | IN FORCE | https://lom.agc.gov.my/ilims/upload/portal/akta/outputaktap/481_BM/AKTA%20469.pdf 16.1MB 30pp (scanned) |
| LAW-02 | Optical Regulations 1994 (principal) | P.U.(A)210/1994 | 1994 | Principal | `P.U.(A)210/1994` (cited) |
| LAW-03 | Peraturan Optik Pindaan 2014 (Forms 5-15) | P.U.(A)64/2014 | 3 Mar 2014 | In force | .../pua_20140303_P%20U%20%20(A)%2064.pdf 614KB 34pp |
| LAW-04 | Peraturan Optik Pindaan 2025 | **P.U.(A)212/2025** | 14 Jul 2025 | In force | .../outputp/2965206/PUA%20212_2025.pdf 346KB 15pp |
| PUA-01 | Perintah Optik Pindaan Jadual Pertama 2019 | **P.U.(A)29/2019** | 31 Jan 2019 / Made 24 Jan 2019 | In force | .../outputp/1696940/018.%20P.U.%20(A)%2029%202019_unlocked.pdf 549KB 3pp |
| PUA-02 | Perintah Optik Pindaan Jadual Pertama & Kedua 2017 (FBDO) | **P.U.(A)125/2017** | 19 Apr 2017 / Made 29 Mar 2017 | In force | .../pua_20170419_P.U.%20(A)%20125.pdf 364KB 5pp |
| PUA-03 | Perintah Optik Pindaan Jadual Pertama 2025 (Vision rename) | **P.U.(A)440/2025** | 18 Dec 2025 / Made 4 Dec 2025 | In force | .../outputp/3250352/PUA%20440%20%20(2025).pdf 229KB 3pp |
| PUA-04 | Perintah Optik Pindaan Jadual Kedua 2026 (SEGi Optometry) | **P.U.(A)141/2026** | 30 Mar 2026 / Made 5 Mar 2026 | In force | .../outputp/3419498/PUA141_2026.pdf 235KB 3pp |

### Circulars (11 verified subsets of 22 total 2024-2026)

All verified 200 OK at `mqa.gov.my/new/pub_circular_20XX.cfm` + `www2.mqa.gov.my/qad/v2/pekeliling/...`

- 2024: Pek 1/2024 GIVC 27 Feb 2024; Pek 4/2024 Rubrik 3C 2 Jul 2024 (223,565B); Pek 5/2024 MQF2024 1 Aug 2024 (174,340B)
- 2025: Pek 5/2025 SUP 27 Mar 2025 (173,730B); Surat 2/2025 HoP criteria 18 Apr 2025; Pek 8/2025 IQAF 17 Dec 2025; 10 others
- 2026: Pek 2/2026 ABC 23 Jun 2026; Pek 3/2026 GWBL 7 Aug 2026 (313,004B); Surat 2/2026 GVBE 9 Jan 2026; Surat 6/2026 IQAF 2026 28 Apr 2026

---

## 3. FULL EXTRACTION — PAGE/SECTION REFERENCES

### MQF 2024 (50pp)
- **p.4 §4:** `No programme will be accredited unless it is in compliance with the Framework.` (Act 679 hierarchy)
- **p.10-11 §2.5 Key Features 2024:** VBE, ESD/GSA, FLP, harmonisation of sectoral frameworks
- **p.18 §2.4:** 5 Clusters LOs (Knowledge, Cognitive, Functional Work Skills, Personal & Entrepreneurial, Ethics & Professionalism)
- **p.24 §4:** Credit definition `1 credit = 40 notional hours` — SLT = F2F (lecture/tutorial/practical) + NF2F (self-study/assessment) + placement
- **p.27 §5 L4 Diploma:** Purpose, descriptor, **min 90 credits**, 2-3 years FT, Flexible Pathways § p.32

### COPPA Ed2 (132pp)
- **p.6-7 §2:** 98 standards in **7 Areas**: 1 PDD (1.1 PEO p.9, 1.2 curriculum/content/structure/LT p.10, 1.3 delivery p.11); 2 Assessment (2.1-2.3 p.12-13 alignment, blueprints); 3 Student Selection (3.1 p.15); 4 Academic Staff (p.18 ratio/workload); 5 Educational Resources (p.21 facilities); 6 Programme Management (p.23); 7 Monitoring/CQI (p.25-27)
- **Rubrik 3C (Oct 2024):** 3-column mapping Criteria (§2) ↔ Submission (§3) ↔ Report (§6) — scoring rubric from July 2024

### PS:MHS July 2019 (161pp)
- **p.28:** MGC 90-105 credits
- **p.38:** `Graduates of a diploma are required to spend 1,000 hours in practical training or clinical placement` — includes lab/simulated + postings + industrial + professional development
- **p.49 Student Selection DIPLOMA:** `SPM or equivalent with at least credit in BM, English, Mathematics plus 1 Science (Biology/Physics/Chemistry/General/Applied) and another subject` (5 credits)
- **p.52-54 Academic Staff:** Diploma staff-student ~1:15, FT:PT 1:1, HoP Master+5y or Bachelor+8y
- **p.55-61 Resources, Appendix 2 pp.109-150 equipment ratios 1:20/1:23**

### SUP 2025 (60pp)
- **p.24 Table 2.3 Diploma L4:** Compulsory 6cr, Core 59cr, Subtotal 65, **MGC 90cr** (25 flexible)
- **p.32 Table 4 Admission L4:** SPM 3 credits any subjects OR STPM C 1 subject OR STAM Maqbul OR SKM L3 OR Cert L3 CGPA 2.00; English MUET Mid B1
- **p.4-7 PEO/PLO:** 5 Clusters + VBE + ESD
- **p.29-33 Staffing/Resources/Management/CQI** — updated by Surat 2/2025 HoP criteria

### GGP-AoSL 127pp / GGP-PDD 96pp / GIVC 51pp / GWBL 59pp / GVBE 143pp
- **GGP-AoSL p.15-30:** Constructive alignment PLO→CLO→assessment, blueprint, OSCE/OSPE/workplace-based, criterion-referenced
- **GGP-PDD p.29:** Formal curriculum definition, PEO-PLO-CLO mapping, VBE/ESD integration p.17-19
- **GIVC §3-5:** Industry Advisory Panel verification sign-off required for PA
- **GWBL Ch1-7 §8:** WBL 40 hrs/credit, competency-based, mentor logs, MOU for optical labs/clinics
- **GVBE:** NEP values across 5 Clusters for professionalism/ethics

### MOC-01 (225pp text, DIO p45-65 verbatim)
- **p46 1.1 iv 11 PLOs a-k:** a) prescribe/dispense ≥8y b) non-cycloplegic refraction ≥8y c) anatomy/optics d) lens measurement/dispensing/edging e) interpret prescription f) advise frame/lens g) vision & binocular status h) referral/emergency i) technologies j) communication k) ethics
- **p47 1.2 iv:** `scheduled over 3 academic years ... ≤43 weeks/yr; contact hours ≤ SLT in proforma`
- **p47 1.2 v:** horizontal/vertical integration, SDL, adequate theory/practical/industrial posting
- **p48 1.2 viii:** `Minimum graduating credits must not be less than 100 credits. Core 80-90% ... University/Faculty 10-20%`
- **p48 1.2 ix:** `Practical training including industrial placement must be broad based ... at least 500 hours on real patients under supervision`
- **p49 2.2 i:** Final exams (written/practical), continuous, seminars, assignments, **log book**, presentations, placement report — continuous + summative
- **p51 3.1 ii:** Disqualifiers — offence against person, dishonesty, serious illness, communicable disease
- **p52 3.2 i:** Credit transfer max **30%** only between First Schedule HEPs, ≥1y at graduating HEP, notified to MOC
- **p54-56 4.1:** Staffing — HoP registered optometrist +5y academician (p60), core clinical bachelor+2y+MOC reg (or +5y+PQA), composition 60% FT (1FT=3PT), ≥ bachelor, 20% 5y teaching, 60% optometry, 50% MY; ratios **1:20 lect, 1:10 lab, 1:4 clinical**; support 1 resident optician +1 lab asst +1 clerk
- **p57-59 5.1:** Facilities — dispensing lab, skill lab, 1:4 cubicles, edger/focimeter maintenance; in-house clinic General Optometry+Dispensing; **placement ≥4 weeks, 1:2 supervisor**, site criteria >3y experience, business registration, CPD, letter good standing, **≥10 patients/week**
- **p61 7.1:** CQI — review every **4 years**, QA unit, monitoring committee + external experts, stakeholder engagement, performance/attrition analysis
- **p63-65 App SII-2 [SUPERSEDED]:** Old entry 3C in 3 sciences CGPA 3.00 — now replaced by MOC-02

### MOC-02 (9pp scanned, OCR 400dpi verified)
- **p8:** `SPM minimum 3 grade Cs: Mathematic and Science/Biology/Physic/Chemistry and English` (same GCE O)
- **p8 OR:** `Certificate in Optical Technology CGPA 2.33` ; `Certificate in Science CGPA 2.33` (same accredited/recognized)
- **p9:** `FBDO Has passed`; `STPM CGPA 2.00`; `UEC Senior Middle Level 3×C7` + `Vocational Unified Examination Certificate 3×C7` same threshold `Mathematic and Science/Bio/Phys/Chem and English` — groups as `UEC-SML or Vocational UEC` (PSM 3/4/6 `English` clean)

### MOC-04 (15pp) PQA Optician
- PAOM mandated 1/2021 for unlisted First Schedule qual; Form 6 Sec18(2) to MOC Evaluation Committee 8 weeks notice; fee RM3,500; components `subjective refraction including binocular balancing, recording BCVA` (p4:5); duration 40min +10 Q&A; pass **65% (17/26)** tolerances sphere ±0.50DS, cylinder ±0.50DC, axis ≤1.00DC 20°/>1.00DC 5°

### MOC-05 (7pp) Clinical Attachment
- 3-year program graduates without pre-registration; **1 year / 800 hours** supervised; logbook 150 refractions (10 myopic astig, 10 hyperopic astig, 10 paediatric/cycloplegic, 10 post-cataract IOL, 3 aphakia, 3 presbyopia)

### Legal
- **Act 469 s.18** Registration of opticians — Form 5 (P.U.(A)64/2014), First Schedule qualification; **s.19** optometrists Second Schedule; **s.41** Minister after consulting Council may amend Schedules by order (recital in every P.U.(A)); **s.42** make Regulations
- **P.U.(A)29/2019** (31 Jan 2019, Made 24 Jan 2019): inserts `Vision College | Diploma in Opticianry (Diiktiraf 14 Nov 2018)` after Avicenna
- **P.U.(A)440/2025** (18 Dec 2025, Made 4 Dec 2025): inserts ` (after 12 May 2025 known as Vision University College)` after Vision College — rename only
- **P.U.(A)212/2025** (14 Jul 2025): amends Reg 6(3) one proposer one candidate, Reg 8 notice via `laman sesawang Majlis atau media sosial 14 days`, Reg 11 ballots Forms 2-4 — governance not DIO content
- **P.U.(A)141/2026** (30 Mar 2026, Made 5 Mar 2026): inserts `SEGi University – Bachelor of Science (Hons) Optometry (Diiktiraf 14 Nov 2025)` in Second Schedule — not DIO

---

## 4. DIO-SPECIFIC REQUIREMENTS (Consolidated)

| Area | Requirement | Primary Source | Status |
|------|-------------|----------------|--------|
| Level | MQF L4 Diploma, NEC 0914 | MQF p27, MQR | VERIFIED |
| Credits | ≥100 (MOC) overrides 90/90-105 | MOC-01 p48 | VERIFIED |
| SLT | 1cr=40 hrs | MQF p24 | VERIFIED |
| Duration | 3 years ≤43 wks/yr | MOC-01 p47 | VERIFIED |
| Practical | ≥1000 hrs total (PS:MHS p38) incl ≥500 hrs real-patient supervised (MOC-01 p48); GWBL frames documentation | MOC-01+PS:MHS+GWBL | VERIFIED |
| Entry | SPM/O 3Cs Maths+Science+English; Cert 2.33; FBDO pass; STPM 2.00; UEC-SML or Vocational UEC 3×C7 (same) | MOC-02 p8-9 | VERIFIED |
| PLOs | 11 competencies a-k (≥8y dispensing/refraction etc.) | MOC-01 p46 | VERIFIED |
| Staffing | HoP reg optometrist +5y; core bachelor+2y+MOC reg (or +5y+PQA); 60%FT/20%5y/60%optometry/50%MY; 1:20/1:10/1:4; support 1+1+1 | MOC-01 p54-56,60 | VERIFIED |
| Facilities | Dispensing/skill lab, 1:4 cubicles, in-house clinic, placement 4wks 1:2 site >3y APC/CPD 10pts/wk | MOC-01 p57-59 | VERIFIED |
| Assessment | Written/practical finals, continuous, logbook, placement report, external examiner final | MOC-01 p49-50 | VERIFIED |
| CQI | Review 4y (MOC) /3-5y (PS:MHS) + IQAF + GIVC verification | MOC-01 p61 | VERIFIED |
| Recognition | First Schedule s.41 P.U.(A) — Vision College (now Vision University College) PUA 29/2019+440/2025; FBDO PUA 125/2017 | PUA-01/02/03 | VERIFIED |

---

## 5. SYLLABUS / MODULE EXAMPLES

| # | Example | Class | URL | Notes |
|---|---|---|---|---|
| 1 | MOC V2.1 DIO PLO/competencies | REQUIREMENT | MOC-01 | Mandatory |
| 2 | MQA SLT template | GUIDANCE | PS:MHS p38-45 | 40hrs/credit |
| 3 | UCSI Diploma Opticianry Y1-3 modules | TEMPLATE | ucsiuniversity.edu.my/programmes/diploma-opticianry | Most transparent DIO structure |
| 4 | Vision DIO 100cr outline | TEMPLATE | vision.edu.my/diploma/ | Only MOC-listed DIO |
| 5 | MSU Ophthalmic Dispensing 90cr | TEMPLATE/PROXY | msu.edu.my/.../diploma-ophthalmic-dispensing.php | De facto DIO |
| 6 | UiTM OPT425/458 OBE course files (2cr/4cr) | BENCHMARK | ir.uitm.edu.my/id/eprint/90458/ | Gold-standard CLO-PLO/SLT/50-50 assessment |
| 7 | SEGi BOptom 4yr clinics | BENCHMARK | segi.edu.my/course/bachelor-of-science-hons-optometry/ | Articulation |

**Gap:** No complete public DIO course file (code/synopsis/CLO/SLT/logbook) found — UiTM is surrogate template.

---

## 6. VERSION / CHANGE MATRIX

| Requirement | Previous | Current | Change | Effective | Impact |
|-------------|----------|---------|--------|-----------|--------|
| MQF | 2017 2nd Ed | 2024 2nd Ed | VBE/GSA/FLP | 1 Aug 2024 2y transition | PLO integrate VBE/ESD |
| COPPA | 2008 | 2017/2018 + Rubrik 3C 2024 | 7 Areas+rubric | July 2024 | Evidence |
| PS:MHS | 2013 1st Ed | 2016/July2019 2nd Ed | 19 fields | 1 Dec 2016 | Benchmark remains |
| SUP | — | 2025 1st Ed | 90cr/3cr entry | 27 Mar 2025 | Primary where PS silent |
| Entry DIO | App p64 3C 3 sciences CGPA 3.00 | **Lampiran A 3Cs Maths+Science+English CGPA 2.33 UEC 3×C7** | Lower CGPA, added English, unified vocational | 1 Jul 2025 | Lower bar stricter language |
| Credits DIO | 90-105 | 100 min | +10 floor | Jan 2025 V2.1 | Meet 100 |
| Practical | 1000 generic | 500 real-patient | Specific real | Jan 2025 | Half real |
| GGP AoSL/PDD | 2013 | 2023 2nd Ed | Blueprint/OSCE | 30 Nov 2023 | Design |
| GWBL | 2019 | 2026 Ed | 40hrs/cr mentor logs | 7 Aug 2026 | WBL framing |
| Regs | 2014 Forms | 212/2025 | website/social notice | 14 Jul 2025 | Admin |
| First Schedule | Vision College | Vision University College | rename | 12 May 2025 via PUA 440 4 Dec 2025 | Citation only |

---

## 7. PUBLIC-BUT-UNLINKED

| Document | URL | Status | How found |
|----------|-----|--------|-----------|
| Guidelines 2022 (superseded) | https://hq.moh.gov.my/moc/wp-content/uploads/2022/04/Guidelines-On-Approval-And-Accreditation-Of-Optometry-And-Opticianry-Programmes-in-Higher-Education-Institutions.pdf 1.38MB | SUPERSEDED by V2.1 | Cross-ref Annual Report 2022 → direct path (not on terbitan) |
| InfoSihat mirror | https://infosihat.moh.gov.my/penerbitan-multimedia/garis-panduan.raw?task=callelement... | Archived mirror | Search-engine index |
| AGC P.U. token PDFs | `lom.agc.gov.my/ilims/upload/portal/akta/outputp/...` | CURRENT | Decrypted json-subsid token |

---

## 8. UNVERIFIED / MISSING REGISTER

| What is missing | Why matters | Search attempted | Status | Next action |
|-----------------|-------------|------------------|--------|-------------|
| PS:MHS 2025 final text | Would supersede July 2019 | types3new.cfm row22 + mqa site search 2025 + IRep 126196 | **No official PDF on MQA QA portal 2 Sep 2026** | Monitor quarterly; label PROPOSED/UNCERTAIN |
| Complete DIO course file/logbook | Template | UCSI/Vision/MSU/Twintech + MQA/MOC search | **Not found public** | Use UiTM surrogate |
| New DIO P.U. beyond Vision | Registrable DIO | AGC search optik 2019-2026 + MOC Senarai | **None 1 Jan 2026→2 Sep 2026** | Quarterly Gazette |
| Lampiran p5 60% aggregates fragmented | Entry detail | 400dpi OCR | **Scanned low confidence** | Request MOC text PDF |
| Act 469 reprint text layer | s.18/41 verbatim | 481_BM/BI.pdf scanned | **Scanned** | OCR |

---

## 9. CONTRADICTIONS (Law > MOC > MQA)

| Area | Conflict | Resolution |
|------|----------|------------|
| Entry SPM | PS:MHS 5 credits vs SUP 3 credits vs MOC 3Cs | **MOC 3Cs governs** (professional) |
| Credits | SUP 90 vs MOC 100 | **MOC 100 floor** |
| Practical | 1000 vs 500 real-patient | **Both: 1000 incl 500 real** |
| Staffing | PS:MHS 1:15 vs MOC 1:20/1:10/1:4 | **MOC DIO-specific** |
| MOC list vs Gazette date | MOC `14 Nov 2016` vs PUA `14 Nov 2018` | **Gazette authoritative** |

---

## 10. WHAT WE MISSED (New vs Master)

- MQF addendum TVET L6 & MPU 19 Nov 2025 — indirect articulation — now verified.
- SUP 2025 as primary where PS silent — 60pp 90cr detail — now verified.
- GWBL 2026 — 59pp — Master addendum pending, now verified.
- PUA 141/2026 SEGi Second Schedule — proves mechanism, no DIO change — now verified 30 Mar 2026.
- Public-but-unlinked 2022 Guidelines archived — Master labelled correctly.
- UiTM OBE gold-standard — Master lacked example — now harvested.

---

## 11. RECOMMENDED MASTER UPDATE (Do Not Apply Now)

1. Keep GWBL row (2026 CURRENT, WBL 40hrs, not reducing minima) — addendum already inserted.
2. Keep 440/2025 rename (already done) and **add PUA 141/2026 row as Second Schedule only — no DIO impact** (verified).
3. Keep vocational = same 3×C7 grouping (already corrected).
4. Keep PS:MHS 2025 as PROPOSED/UNCERTAIN until types3new.cfm lists it.
5. Optionally add 2022 archived link as historical [SUPERSEDED].

---

## 12. SOURCE REGISTER — COMPLETE VERIFIED URLS

All URLs above verified 200 OK 2 Sep 2026. MQA: `mqa.gov.my/new/document/...`, `www2.mqa.gov.my/qad/...`. MOC: `hq.moh.gov.my/moc/wp-content/uploads/...`. AGC: `lom.agc.gov.my/ilims/upload/portal/akta/outputp/...`. MQR: `mqa.gov.my/mqr`.

---

# FINAL STATUS

**Documents discovered:** 42 unique relevant (14 MQA + 8 MOC + 8 legal + 11 circulars + 1 MQR)
**Documents retrieved:** 38 fetched 200 OK (4 scanned)
**Documents fully examined:** 34 text PDFs page-by-page
**Documents partially examined:** 4 scanned/image-only (MOC-02 9pp, MOC-03 5pp, MOC-06 11pp, Act 469 30pp) — OCR 400dpi partial
**Scanned/image-only documents:** 4
**Public-but-unlinked documents:** 3
**Documents still unavailable/unverified:** 2 (PS:MHS 2025 final; complete DIO course file/logbook)
**New DIO-relevant findings:** 4 (GWBL 2026, SUP 2025 primary, PUA 440 rename, PUA 141/2026 non-DIO)
**Master Markdown updates recommended:** 5 minor (add PUA 141 as non-DIO row, keep GWBL/ vocational fix/watch-list/archived link)

**Research/extraction only. Master not modified. Full findings file saved at `Malaysian DIO - Full Harvest Findings and Sources 2026-09-02.md`**
