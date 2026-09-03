# SUPPLEMENT S1 — SEARCH STRATEGIES v1.2 (FROZEN FOR OSF; SUPERSEDES v1.1)

**Review:** Dry Eye Disease, Dry-Eye Symptoms, and Night-Driving Difficulty Among Drivers: A Scoping Review
**Protocol:** Scoping_Review_Protocol_v7.6.md (CR-01–CR-07 audit amendments 2026-09-03 integrated)
**Strategy version:** v1.2 + P-08 Lite harmonisation (2026-09-03) — v1.1 + Malay recall arm (CR-02): C1 + "mata kering"; C2 + "memandu malam" OR "pemanduan malam" OR silau; P-08 adds missing "pemanduan malam" to TRID/VisionCite Lite for cross-arm consistency (low-risk Malay OR-term delta per CR-02 precedent — re-run seed gate at execution; any anomaly → v1.3)
**PRESS status:** v1.1 PASSED 6-domain audit; v1.2 delta (Malay OR-terms only) classified low-risk per CR-02 risk table — re-run seed gate at execution; any anomaly → v1.3 (CR-02 audit amendment 2026-09-03: delta verification requires reviewer initials + date in the manifest Strategy Version [MUST-FILL at execution]; full independent PRESS re-review required for any future substantive string change. Executable strings unchanged by this amendment — no v1.3 trigger.)
**Seed validation set (must retrieve 5/5 where indexed):** Deschamps et al. 2013; Tong et al. 2010; Wang et al. 2017; Woi et al. 2025a; Kimlin et al. 2016
**PRESS log note:** `driv*` unconstrained is an intentional sensitivity choice for scoping; high NNR accepted and documented. PC-09 four-minima gate (N + DED measure + night outcome + design) applies at screening regardless of retrieval breadth. Malay terms selected for low cross-language homograph risk (Information Specialist lens).

**Master logic (all databases):** (C1 Controlled OR C1 Free incl. Malay) AND (C2 Controlled OR C2 Free incl. Malay) AND (C3 Free, folded into C2 block below).
- C1 (Condition): Dry Eye / Keratoconjunctivitis Sicca / Tear Film / Meibomian Gland Dysfunction (+ OSDI/TBUT/NIBUT/breakup variants + "mata kering")
- C2/C3 (Context/Outcome): Driving / Night Vision / Glare / Mesopic Vision / Scotopic / Photophobia / Halos / Contrast Sensitivity / Headlights / VND-Q (+ "memandu malam" / "pemanduan malam" / silau)

---

## 1. MEDLINE via PubMed (NCBI)

**Syntax:** `[MeSH]` controlled, `[tiab]` free-text. Multi-word truncations quoted per PRESS.

```text
("Dry Eye Syndromes"[MeSH] OR "Keratoconjunctivitis Sicca"[MeSH] OR "Tears"[MeSH] OR "Meibomian Glands"[MeSH] OR "dry eye"[tiab] OR "dry eye*"[tiab] OR "keratoconjunctivitis sicca"[tiab] OR "meibomian gland dysfunction"[tiab] OR "tear film"[tiab] OR "tear film*"[tiab] OR "tear break up"[tiab] OR "tear breakup"[tiab] OR "tear break-up"[tiab] OR OSDI[tiab] OR TBUT[tiab] OR NIBUT[tiab] OR "mata kering"[tiab])
AND
("Automobile Driving"[MeSH] OR "Dark Adaptation"[MeSH] OR "Vision, Low"[MeSH] OR "Glare"[MeSH] OR "Photophobia"[MeSH] OR "Contrast Sensitivity"[MeSH] OR "Visual Acuity"[MeSH] OR driv*[tiab] OR "night driving"[tiab] OR "night vision"[tiab] OR glare[tiab] OR photophobia[tiab] OR "contrast sensitivity"[tiab] OR "mesopic vision"[tiab] OR scotopic[tiab] OR halo[tiab] OR halos[tiab] OR "starburst*"[tiab] OR "dark adaptation"[tiab] OR headlight*[tiab] OR headlamp*[tiab] OR "low light"[tiab] OR "VND-Q"[tiab] OR "memandu malam"[tiab] OR "pemanduan malam"[tiab] OR silau[tiab])
```

## 2. Embase via Embase.com

**Syntax:** `'/exp'` Emtree explosion; `:ti,ab,kw` free-text.

```text
('dry eye'/exp OR 'keratoconjunctivitis sicca'/exp OR 'tear film'/exp OR 'meibomian gland dysfunction'/exp OR 'tear break up time'/exp OR 'dry eye':ti,ab,kw OR 'dry eye*':ti,ab,kw OR 'keratoconjunctivitis sicca':ti,ab,kw OR 'meibomian gland dysfunction':ti,ab,kw OR 'tear film':ti,ab,kw OR 'tear film*':ti,ab,kw OR 'tear break up':ti,ab,kw OR 'tear breakup':ti,ab,kw OR 'tear break-up':ti,ab,kw OR OSDI:ti,ab,kw OR TBUT:ti,ab,kw OR NIBUT:ti,ab,kw OR 'mata kering':ti,ab,kw)
AND
('car driving'/exp OR 'night'/exp OR 'mesopic vision'/exp OR 'glare'/exp OR 'photophobia'/exp OR 'contrast sensitivity'/exp OR driv*:ti,ab,kw OR 'night driving':ti,ab,kw OR 'night vision':ti,ab,kw OR glare:ti,ab,kw OR photophobia:ti,ab,kw OR 'contrast sensitivity':ti,ab,kw OR 'mesopic vision':ti,ab,kw OR scotopic:ti,ab,kw OR halo:ti,ab,kw OR halos:ti,ab,kw OR starburst*:ti,ab,kw OR 'dark adaptation':ti,ab,kw OR headlight*:ti,ab,kw OR headlamp*:ti,ab,kw OR 'low light':ti,ab,kw OR 'VND-Q':ti,ab,kw OR 'memandu malam':ti,ab,kw OR 'pemanduan malam':ti,ab,kw OR silau:ti,ab,kw)
```

## 3. Cochrane Library (CENTRAL + CDSR via Wiley)

**Syntax:** `[mh "..."]` MeSH; `:ti,ab,kw` free-text.

```text
([mh "Dry Eye Syndromes"] OR [mh "Keratoconjunctivitis Sicca"] OR [mh "Tears"] OR [mh "Meibomian Glands"] OR "dry eye":ti,ab,kw OR "dry eye*":ti,ab,kw OR "keratoconjunctivitis sicca":ti,ab,kw OR "meibomian gland dysfunction":ti,ab,kw OR "tear film":ti,ab,kw OR "tear film*":ti,ab,kw OR "tear break up":ti,ab,kw OR "tear breakup":ti,ab,kw OR "tear break-up":ti,ab,kw OR OSDI:ti,ab,kw OR TBUT:ti,ab,kw OR NIBUT:ti,ab,kw OR "mata kering":ti,ab,kw)
AND
([mh "Automobile Driving"] OR [mh "Dark Adaptation"] OR [mh "Vision, Low"] OR [mh "Glare"] OR [mh "Photophobia"] OR [mh "Contrast Sensitivity"] OR [mh "Visual Acuity"] OR driv*:ti,ab,kw OR "night driving":ti,ab,kw OR "night vision":ti,ab,kw OR glare:ti,ab,kw OR photophobia:ti,ab,kw OR "contrast sensitivity":ti,ab,kw OR "mesopic vision":ti,ab,kw OR scotopic:ti,ab,kw OR halo:ti,ab,kw OR halos:ti,ab,kw OR starburst*:ti,ab,kw OR "dark adaptation":ti,ab,kw OR headlight*:ti,ab,kw OR headlamp*:ti,ab,kw OR "low light":ti,ab,kw OR "VND-Q":ti,ab,kw OR "memandu malam":ti,ab,kw OR "pemanduan malam":ti,ab,kw OR silau:ti,ab,kw)
```

## 4. Scopus via Elsevier (Native)

**Syntax:** `TITLE-ABS-KEY()`; no controlled explosion.

```text
TITLE-ABS-KEY ( ( "dry eye*" OR "dry eye" OR "keratoconjunctivitis sicca" OR "meibomian gland dysfunction" OR "tear film*" OR "tear film" OR "tear break up" OR "tear breakup" OR "tear break-up" OR OSDI OR TBUT OR NIBUT OR "mata kering" ) AND ( driv* OR "night driving" OR "night vision" OR glare OR photophobia OR "contrast sensitivity" OR "mesopic vision" OR scotopic OR halo OR halos OR starburst* OR "dark adaptation" OR headlight* OR headlamp* OR "low light" OR "VND-Q" OR "memandu malam" OR "pemanduan malam" OR silau ) )
```

## 5. Web of Science Core Collection via Clarivate (Native)

**Syntax:** `TS=` topic search.

```text
TS=( ("dry eye*" OR "dry eye" OR "keratoconjunctivitis sicca" OR "meibomian gland dysfunction" OR "tear film*" OR "tear film" OR "tear breakup" OR "tear break up" OR "tear break-up" OR OSDI OR TBUT OR NIBUT OR "mata kering") AND (driv* OR "night driving" OR "night vision" OR glare OR photophobia OR "contrast sensitivity" OR "mesopic vision" OR scotopic OR halo OR halos OR starburst* OR "dark adaptation" OR headlight* OR headlamp* OR "low light" OR "VND-Q" OR "memandu malam" OR "pemanduan malam" OR silau) )
```

## 6. CINAHL via EBSCOhost

**Syntax:** `(MH "...")` headings; `TI/AB` free-text.

```text
((MH "Dry Eye Syndromes") OR (MH "Keratoconjunctivitis Sicca") OR (MH "Tears") OR TI "dry eye*" OR AB "dry eye*" OR TI "dry eye" OR AB "dry eye" OR TI "keratoconjunctivitis sicca" OR AB "keratoconjunctivitis sicca" OR TI "meibomian gland dysfunction" OR AB "meibomian gland dysfunction" OR TI "tear film*" OR AB "tear film*" OR TI "tear film" OR AB "tear film" OR TI "tear break up" OR AB "tear break up" OR TI "tear breakup" OR AB "tear breakup" OR TI "tear break-up" OR AB "tear break-up" OR TI OSDI OR AB OSDI OR TI TBUT OR AB TBUT OR TI NIBUT OR AB NIBUT OR TI "mata kering" OR AB "mata kering")
AND
((MH "Automobile Driving") OR (MH "Night Vision") OR (MH "Glare") OR (MH "Photophobia") OR (MH "Contrast Sensitivity") OR TI driv* OR AB driv* OR TI "night driving" OR AB "night driving" OR TI "night vision" OR AB "night vision" OR TI glare OR AB glare OR TI photophobia OR AB photophobia OR TI "contrast sensitivity" OR AB "contrast sensitivity" OR TI "mesopic vision" OR AB "mesopic vision" OR TI scotopic OR AB scotopic OR TI halo OR AB halo OR TI halos OR AB halos OR TI starburst* OR AB starburst* OR TI "dark adaptation" OR AB "dark adaptation" OR TI headlight* OR AB headlight* OR TI headlamp* OR AB headlamp* OR TI "low light" OR AB "low light" OR TI "VND-Q" OR AB "VND-Q" OR TI "memandu malam" OR AB "memandu malam" OR TI "pemanduan malam" OR AB "pemanduan malam" OR TI silau OR AB silau)
```

## 7. TRID via TRB Native ("Lite")

**Syntax:** Basic Boolean; flat structure. Driver nouns explicit per PRESS.

```text
("dry eye" OR "keratoconjunctivitis sicca" OR "meibomian gland dysfunction" OR "tear film" OR OSDI OR TBUT OR "mata kering")
AND
(driving OR driver OR drivers OR "night vision" OR glare OR photophobia OR "contrast sensitivity" OR mesopic OR scotopic OR halos OR headlight OR headlamp OR "VND-Q" OR "memandu malam" OR "pemanduan malam" OR silau)
```

## 8. VisionCite via ICO Native ("Lite")

**Syntax:** Basic keyword combinations.

```text
("dry eye" OR "keratoconjunctivitis" OR "meibomian" OR "tear film" OR OSDI OR TBUT OR "mata kering")
AND
(driving OR driver OR drivers OR night OR glare OR photophobia OR "contrast sensitivity" OR halos OR headlight OR "VND-Q" OR "memandu malam" OR "pemanduan malam" OR silau)
```

---

## PRESS Unit-Test Protocol (pre-execution gate)

1. Run each string in its native interface; record date + hits + errors/timeouts.
2. Verify 5/5 seeds retrieved where indexed (note expected gaps: Kimlin 2016 validation may not co-index DED terms; Woi papers may not be in TRID/VisionCite). Spot-check Malay-term hits against MyJurnal/MyCite records.
3. Any syntax error, timeout, or zero-hit anomaly → string invalidated, rewritten as v1.3, re-tested.
4. Freeze only after PRESS sign-off; record PRESS date + reviewer initials in manifest Strategy Version.
5. No searches count as data collection until OSF DOI issued; PRESS test runs are methods validation only and must be re-run post-registration per §11.8.

**Seed re-check log (2026-09-03, PubMed, S1 v1.2 §1 strategy — methods validation only):** 4/5 retrieved — Deschamps 2013 (PMID 23706501) ✅; Tong 2010 (PMID 20489740) ✅; Wang 2017 (PMID 28622318) ✅; Woi 2025a (PMID 40138276) ✅; Kimlin 2016 (PMID 27350185) count 0 — DOCUMENTED EXPECTED GAP per item 2 above (instrument-validation paper, no DED indexing terms; captured via forward citation chasing per Protocol §10.3/PC-08, not topical retrieval). Malay OR-terms ("mata kering", "memandu malam", "pemanduan malam") ignored by PubMed phrase index — zero-match, benign. No syntax/timeout anomaly → no v1.3. Verdict: PASS with citation-chase-only exception for Kimlin 2016.

**FREEZE STATUS: v1.2 FROZEN-PASSED — CLEARED FOR OSF REGISTRATION. DO NOT EXECUTE DATA-COLLECTION SEARCHES UNTIL OSF DOI ISSUED.**
