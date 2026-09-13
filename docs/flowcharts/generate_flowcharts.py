"""Generate 3 scoping review protocol flowcharts as PNGs (matplotlib only)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

CHARCOAL = "#1A1A1A"; BONE = "#FAFAF8"; ACCENT = "#E8C547"
BLUE = "#DCE9F7"; GREEN = "#DFF2E1"; YELLOW = "#FFF3C4"; GREY = "#EDEDED"; PINK = "#F8DCDA"

def draw(ax, boxes, arrows, title, subtitle=""):
    ax.set_xlim(0, 10); ax.set_ylim(0, len(boxes)*1.6 + 1.5)
    ax.invert_yaxis(); ax.axis("off")
    ax.set_facecolor(BONE)
    ax.figure.patch.set_facecolor(BONE)
    ax.text(5, 0.5, title, ha="center", va="center", fontsize=13, weight="bold", color=CHARCOAL)
    if subtitle:
        ax.text(5, 1.0, subtitle, ha="center", va="center", fontsize=8, style="italic", color="#555555")
    y0 = 1.8
    pos = {}
    for i, (label, sub, color, kind) in enumerate(boxes):
        y = y0 + i*1.6
        x = 5; w = 7.6; h = 1.15
        pos[i] = (x, y)
        style = "round,pad=0.08,rounding_size=0.25" if kind != "diamond" else "round,pad=0.08,rounding_size=0.15"
        box = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle=style, facecolor=color, edgecolor=CHARCOAL, linewidth=1.2)
        ax.add_patch(box)
        ax.text(x, y-0.12, label, ha="center", va="center", fontsize=8.5, weight="bold", color=CHARCOAL, wrap=True)
        if sub:
            ax.text(x, y+0.32, sub, ha="center", va="center", fontsize=6.8, color="#333333", wrap=True)
    for a, b, lbl in arrows:
        x1, y1 = pos[a]; x2, y2 = pos[b]
        arr = FancyArrowPatch((x1, y1+0.575), (x2, y2-0.575), arrowstyle="-|>", color=CHARCOAL, linewidth=1.3, mutation_scale=12, shrinkA=0, shrinkB=0)
        ax.add_patch(arr)
        if lbl:
            ax.text(7.1, (y1+y2)/2, lbl, fontsize=6.5, color="#555555", va="center")
    plt.tight_layout()

# --- Fig 1: Protocol methods overview (JBI / Arksey & O'Malley tailored) ---
fig1_boxes = [
    ("1  OSF REGISTRATION (Day 0/1)", "Pre-register v7.6 BEFORE any search  |  DOI issued  |  PC-05", YELLOW, "box"),
    ("2  QUESTION + PCC + ELIGIBILITY", "DED/dry-eye x night-driving x drivers  |  E1-E9 defined", BLUE, "box"),
    ("3  SEARCH  (S1 v1.2 executables)", "8 DBs: PubMed Embase Scopus WoS CINAHL TRID Cochrane VisionCite + grey lit", BLUE, "box"),
    ("4  MENDELEY MASTER LIBRARY", "01_Search  >  02_Grey  >  03_Deduplicated (staging > master, PCR-03)", GREY, "box"),
    ("5  STUDY SELECTION (dual)", "Title/abs: INCLUDE / EXCLUDE / UNCERTAIN  |  10% kappa gate + final kappa (PC-13)", GREEN, "box"),
    ("6  FULL-TEXT + E1-E9 + E6/E7 RULE", "Dual full-text  |  E6 duplicate vs E7 companion  |  arbiter for borderline", GREEN, "box"),
    ("7  CHARTING (pilot > calibration > single)", "2 pilot + 3 calibration (PC-14)  |  single + 30% spot-check (CR-03)", PINK, "box"),
    ("8  SYNTHESIS + PRISMA-ScR REPORT", "Numeric summary  |  evidence map  |  thematic  |  companions not double-counted", ACCENT, "box"),
]
fig1_arrows = [(i, i+1, "") for i in range(7)]
fig, ax = plt.subplots(figsize=(10, 13))
draw(ax, fig1_boxes, fig1_arrows, "Fig 1 — Scoping Review Protocol Overview (v7.6)",
     "DED + dry-eye symptoms x night-driving difficulty  |  Arksey & O'Malley / Levac / JBI / PRISMA-ScR + PRISMA-S")
fig.savefig("flowcharts/fig1_protocol_overview.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# --- Fig 2: PRISMA-ScR selection flow template ---
fig2_boxes = [
    ("IDENTIFICATION — Records identified", "Databases n=___  |  Grey lit n=___  |  Other (citation fwd) n=___", BLUE, "box"),
    ("IDENTIFICATION — Deduplicated", "Duplicates removed n=___  |  Mendeley 03_Deduplicated = master  |  Records to screen n=___", GREY, "box"),
    ("SCREENING — Title / abstract (dual, Rayyan/Covidence)", "Screened n=___  >  Excluded n=___  |  INCLUDE+UNCERTAIN n=___  |  kappa calib + final", GREEN, "box"),
    ("ELIGIBILITY — Full-text assessed (dual)", "Retrieved n=___ (E8 = not retrievable)  |  Assessed n=___", GREEN, "box"),
    ("ELIGIBILITY — Excluded with reasons E1-E9", "E1 no DED | E2 no night-driving | E3 pop | E4 design | E5 abstr | E6 dupl | E7 companion | E8 | E9", PINK, "box"),
    ("INCLUDED — Studies vs reports", "Studies n=___  |  Reports n=___  |  Companions flagged, not counted (WPJ primary; thesis companion)", ACCENT, "box"),
]
fig2_arrows = [(i, i+1, "") for i in range(5)]
fig, ax = plt.subplots(figsize=(10, 10.5))
draw(ax, fig2_boxes, fig2_arrows, "Fig 2 — PRISMA-ScR Study Selection Flow (template for Fig.1 of manuscript)",
     "Fill n=___ after screening  |  companions recorded but excluded from numerical synthesis (S17)")
fig.savefig("flowcharts/fig2_prisma_scr_flow.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# --- Fig 3: Operational screening workflow ---
fig3_boxes = [
    ("A  IMPORT + TAG (Mendeley)", "01_Search per-DB folders + 02_Grey  |  tag: peer-reviewed / thesis / preprint / conf / report / unpub", BLUE, "box"),
    ("B  DEDUP (auto + manual)", "Auto-merge identical metadata  |  manual: authors/N/dates/site  |  log pairs; flag companions", GREY, "box"),
    ("C  EXPORT TO RAYYAN / COVIDENCE", "Master 03_Deduplicated > screening tool  |  Mendeley NOT used for screening", YELLOW, "box"),
    ("D  CALIBRATION GATE (10% kappa)", "Dual screen 10% sample  |  kappa OK? No > retrain; Yes > full screening", YELLOW, "diamond"),
    ("E  DUAL TITLE/ABSTRACT SCREEN", "INCLUDE / EXCLUDE / UNCERTAIN each record  |  disagree > discuss > 3rd reviewer", GREEN, "box"),
    ("F  FULL-TEXT RETRIEVAL + DUAL ASSESS", "Retrieve all INCLUDE+UNCERTAIN  |  E8 if unretrievable  |  dual INCLUDE/EXCLUDE + E1-E9", GREEN, "box"),
    ("G  E6 vs E7 ADJUDICATION (CR-06)", "Identical content > E6 exclude dupl  |  same data/diff analysis > E7 companion  |  borderline > arbiter", PINK, "box"),
    ("H  SELF-REVIEW SAFEGUARDS (CR-07)", "Thesis/WPJ/Woi x2: identical criteria + 2nd-reviewer verify + disclose + no inflation", PINK, "box"),
    ("I  CHART + FILE IN MENDELEY", "04_Screened (E1-E9 folders) > 05_Charted Primary vs Companion_Flagged > 06_Manuscript refs", ACCENT, "box"),
]
fig3_arrows = [(i, i+1, "") for i in range(8)]
fig, ax = plt.subplots(figsize=(10, 14.5))
draw(ax, fig3_boxes, fig3_arrows, "Fig 3 — Operational Screening Workflow (SS12 / 16 / 17)",
     "Mendeley = library only  |  Rayyan/Covidence = screening  |  Excel/Sheets = charting")
fig.savefig("flowcharts/fig3_operational_workflow.png", dpi=200, bbox_inches="tight")
plt.close(fig)

print("OK: 3 PNGs written to flowcharts/")
