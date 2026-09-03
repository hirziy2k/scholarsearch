# SUPPLEMENT S1 — SEARCH STRATEGIES v1.0r2 (FROZEN FOR PRESS)

**Review:** Dry Eye Disease, Dry-Eye Symptoms, and Night-Driving Difficulty Among Drivers: A Scoping Review
**Protocol:** Scoping_Review_Protocol_v7.0.md v7.4 (PC-01 to PC-20; PC-18 resolved via PC-08)
**Strategy version:** v1.0r2 — incorporates halo*→(halo OR halos) fix; OSDI/TBUT/NIBUT + breakup variants + headlight*/headlamp*/low-light/VND-Q additions
**PRESS status:** DRAFT for formal PRESS audit — DO NOT EXECUTE until PRESS sign-off + OSF DOI
**Seed validation set (must retrieve 5/5 where indexed):** Deschamps et al. 2013; Tong et al. 2010; Wang et al. 2017; Woi et al. 2025a; Kimlin et al. 2016
**PRESS log note:** `driv*` unconstrained is an intentional sensitivity choice for scoping; high NNR accepted and documented. PC-09 four-minima gate (N + DED measure + night outcome + design) applies at screening regardless of retrieval breadth.

**Master logic (all databases):** (C1 Controlled OR C1 Free) AND (C2 Controlled OR C2 Free) AND (C3 Free, folded into C2 block below).
- C1 (Condition): Dry Eye / Keratoconjunctivitis Sicca / Tear Film / Meibomian Gland Dysfunction (+ OSDI/TBUT/NIBUT/breakup variants)
- C2/C3 (Context/Outcome): Driving / Night Vision / Glare / Mesopic Vision / Halos / Contrast Sensitivity / Headlights / VND-Q

---

## 1. MEDLINE via PubMed (NCBI)

**Syntax:** `[MeSH]` controlled, `[tiab]` free-text. No proximity.

```text
("Dry Eye Syndromes"[MeSH] OR "Keratoconjunctivitis Sicca"[MeSH] OR "Tears"[MeSH] OR "Meibomian Glands"[MeSH] OR "dry eye"[tiab] OR dry eye*[tiab] OR "keratoconjunctivitis sicca"[tiab] OR "meibomian gland dysfunction"[tiab] OR "tear film"[tiab] OR tear film*[tiab] OR "tear break up"[tiab] OR "tear breakup"[tiab] OR "tear break-up"[tiab] OR OSDI[tiab] OR TBUT[tiab] OR NIBUT[tiab])
AND
("Automobile Driving"[MeSH] OR "Dark Adaptation"[MeSH] OR "Vision, Low"[MeSH] OR "Glare"[MeSH] OR "Contrast Sensitivity"[MeSH] OR "Visual Acuity"[MeSH] OR driv*[tiab] OR "night driving"[tiab] OR "night vision"[tiab] OR glare[tiab] OR "contrast sensitivity"[tiab] OR "mesopic vision"[tiab] OR halo[tiab] OR halos[tiab] OR starburst*[tiab] OR "dark adaptation"[tiab] OR headlight*[tiab] OR headlamp*[tiab] OR "low light"[tiab] OR "VND-Q"[tiab])
```

## 2. Embase via Embase.com

**Syntax:** `'/exp'` Emtree explosion; `:ti,ab,kw` free-text.

```text
('dry eye'/exp OR 'keratoconjunctivitis sicca'/exp OR 'tear film'/exp OR 'meibomian gland dysfunction'/exp OR 'tear break up time'/exp OR 'dry eye':ti,ab,kw OR 'dry eye*':ti,ab,kw OR 'keratoconjunctivitis sicca':ti,ab,kw OR 'meibomian gland dysfunction':ti,ab,kw OR 'tear film':ti,ab,kw OR 'tear film*':ti,ab,kw OR 'tear break up':ti,ab,kw OR 'tear breakup':ti,ab,kw OR 'tear break-up':ti,ab,kw OR OSDI:ti,ab,kw OR TBUT:ti,ab,kw OR NIBUT:ti,ab,kw)
AND
('car driving'/exp OR 'night'/exp OR 'mesopic vision'/exp OR 'glare'/exp OR 'contrast sensitivity'/exp OR driv*:ti,ab,kw OR 'night driving':ti,ab,kw OR 'night vision':ti,ab,kw OR glare:ti,ab,kw OR 'contrast sensitivity':ti,ab,kw OR 'mesopic vision':ti,ab,kw OR halo:ti,ab,kw OR halos:ti,ab,kw OR starburst*:ti,ab,kw OR 'dark adaptation':ti,ab,kw OR headlight*:ti,ab,kw OR headlamp*:ti,ab,kw OR 'low light':ti,ab,kw OR 'VND-Q':ti,ab,kw)
```

## 3. Cochrane Library (CENTRAL + CDSR via Wiley)

**Syntax:** `[mh "..."]` MeSH; `:ti,ab,kw` free-text.

```text
([mh "Dry Eye Syndromes"] OR [mh "Keratoconjunctivitis Sicca"] OR [mh "Tears"] OR [mh "Meibomian Glands"] OR "dry eye":ti,ab,kw OR "dry eye*":ti,ab,kw OR "keratoconjunctivitis sicca":ti,ab,kw OR "meibomian gland dysfunction":ti,ab,kw OR "tear film":ti,ab,kw OR "tear film*":ti,ab,kw OR "tear break up":ti,ab,kw OR "tear breakup":ti,ab,kw OR "tear break-up":ti,ab,kw OR OSDI:ti,ab,kw OR TBUT:ti,ab,kw OR NIBUT:ti,ab,kw)
AND
([mh "Automobile Driving"] OR [mh "Dark Adaptation"] OR [mh "Vision, Low"] OR [mh "Glare"] OR [mh "Contrast Sensitivity"] OR [mh "Visual Acuity"] OR driv*:ti,ab,kw OR "night driving":ti,ab,kw OR "night vision":ti,ab,kw OR glare:ti,ab,kw OR "contrast sensitivity":ti,ab,kw OR "mesopic vision":ti,ab,kw OR halo:ti,ab,kw OR halos:ti,ab,kw OR starburst*:ti,ab,kw OR "dark adaptation":ti,ab,kw OR headlight*:ti,ab,kw OR headlamp*:ti,ab,kw OR "low light":ti,ab,kw OR "VND-Q":ti,ab,kw)
```

## 4. Scopus via Elsevier (Native)

**Syntax:** `TITLE-ABS-KEY()`; no controlled explosion.

```text
TITLE-ABS-KEY ( ( "dry eye*" OR "dry eye" OR "keratoconjunctivitis sicca" OR "meibomian gland dysfunction" OR "tear film*" OR "tear film" OR "tear break up" OR "tear breakup" OR "tear break-up" OR OSDI OR TBUT OR NIBUT ) AND ( driv* OR "night driving" OR "night vision" OR glare OR "contrast sensitivity" OR "mesopic vision" OR halo OR halos OR starburst* OR "dark adaptation" OR headlight* OR headlamp* OR "low light" OR "VND-Q" ) )
```

## 5. Web of Science Core Collection via Clarivate (Native)

**Syntax:** `TS=` topic search.

```text
TS=( ("dry eye*" OR "dry eye" OR "keratoconjunctivitis sicca" OR "meibomian gland dysfunction" OR "tear film*" OR "tear film" OR "tear breakup" OR "tear break up" OR "tear break-up" OR OSDI OR TBUT OR NIBUT) AND (driv* OR "night driving" OR "night vision" OR glare OR "contrast sensitivity" OR "mesopic vision" OR halo OR halos OR starburst* OR "dark adaptation" OR headlight* OR headlamp* OR "low light" OR "VND-Q") )
```

## 6. CINAHL via EBSCOhost

**Syntax:** `(MH "...")` headings; `TI/AB` free-text.

```text
((MH "Dry Eye Syndromes") OR (MH "Keratoconjunctivitis Sicca") OR (MH "Tears") OR TI "dry eye*" OR AB "dry eye*" OR TI "dry eye" OR AB "dry eye" OR TI "keratoconjunctivitis sicca" OR AB "keratoconjunctivitis sicca" OR TI "meibomian gland dysfunction" OR AB "meibomian gland dysfunction" OR TI "tear film*" OR AB "tear film*" OR TI "tear film" OR AB "tear film" OR TI "tear break up" OR AB "tear break up" OR TI "tear breakup" OR AB "tear breakup" OR TI "tear break-up" OR AB "tear break-up" OR TI OSDI OR AB OSDI OR TI TBUT OR AB TBUT OR TI NIBUT OR AB NIBUT)
AND
((MH "Automobile Driving") OR (MH "Night Vision") OR (MH "Glare") OR (MH "Contrast Sensitivity") OR TI driv* OR AB driv* OR TI "night driving" OR AB "night driving" OR TI "night vision" OR AB "night vision" OR TI glare OR AB glare OR TI "contrast sensitivity" OR AB "contrast sensitivity" OR TI "mesopic vision" OR AB "mesopic vision" OR TI halo OR AB halo OR TI halos OR AB halos OR TI starburst* OR AB starburst* OR TI "dark adaptation" OR AB "dark adaptation" OR TI headlight* OR AB headlight* OR TI headlamp* OR AB headlamp* OR TI "low light" OR AB "low light" OR TI "VND-Q" OR AB "VND-Q")
```

## 7. TRID via TRB Native ("Lite")

**Syntax:** Basic Boolean; flat structure to avoid parser timeouts.

```text
("dry eye" OR "keratoconjunctivitis sicca" OR "meibomian gland dysfunction" OR "tear film" OR OSDI OR TBUT)
AND
(driving OR "night vision" OR glare OR "contrast sensitivity" OR mesopic OR halos OR headlight OR headlamp OR "VND-Q")
```

## 8. VisionCite via ICO Native ("Lite")

**Syntax:** Basic keyword combinations.

```text
("dry eye" OR "keratoconjunctivitis" OR "meibomian" OR "tear film" OR OSDI OR TBUT)
AND
(driving OR night OR glare OR "contrast sensitivity" OR halos OR headlight OR "VND-Q")
```

---

## PRESS Unit-Test Protocol (pre-execution gate)

1. Run each string in its native interface; record date + hits + errors/timeouts.
2. Verify 5/5 seeds retrieved where indexed (note expected gaps: Kimlin 2016 validation may not co-index DED terms; Woi papers may not be in TRID/VisionCite).
3. Any syntax error, timeout, or zero-hit anomaly → string invalidated, rewritten as v1.0r3, re-tested.
4. Freeze only after PRESS sign-off; record PRESS date + reviewer initials in manifest Strategy Version.
5. No searches count as data collection until OSF DOI issued; PRESS test runs are methods validation only and must be re-run post-registration per §11.8.

**FREEZE STATUS: DRAFT v1.0r2 — PENDING PRESS + OSF DOI. DO NOT USE FOR DATA COLLECTION.**
