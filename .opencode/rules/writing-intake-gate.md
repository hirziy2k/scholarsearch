# WRITING SKILL INTAKE GATE

## Purpose

Routes writing requests to the correct pipeline based on task scale. Prevents workflow bloat for micro-edits while preserving rigor for new content.

## Routing Decision Tree

```
USER REQUEST
    │
    ├── Is this EDITING EXISTING TEXT?
    │   │
    │   ├── Does it introduce NEW claims, data, or citations?
    │   │   └── YES → HEAVY PIPELINE
    │   │
    │   └── NO (pure prose revision)
    │       │
    │       ├── Does it require reporting guideline compliance?
    │       │   └── YES → HEAVY PIPELINE
    │       │
    │       └── NO → FAST-TRACK
    │
    └── Is this DRAFTING NEW CONTENT?
        └── YES → HEAVY PIPELINE
```

## Pipeline Definitions

### HEAVY PIPELINE (Drafting net-new sections)

**Route**: K-Dense scientific-writing (scaffolding) → prose drafting → labarba/sciwrite (QA)

**Required inputs before execution**:
1. Target journal/venue: ___
2. Reporting guideline (if applicable): ___
3. Study design (if applicable): ___
4. Source evidence/protocol: ___
5. Section to draft: ___

**Agent action**:
1. Load scientific-writing SKILL.md
2. Complete intake checklist (K-Dense section)
3. Generate evidence scaffolding (manifests, claims, consistency)
4. Draft prose from scaffold
5. Load sciwrite SKILL.md
6. Run all 5 audit passes on drafted prose
7. Present revised text with severity-tagged report

### FAST-TRACK (Editing existing text)

**Route**: Direct to labarba/sciwrite (QA)

**No required inputs** — just the text to review.

**Qualifying criteria** (ALL must be true):
- Working with existing text (not generating new content)
- Requesting specific, localized changes
- No new claims, data, or citations being introduced
- No reporting guideline compliance check needed

**Agent action**:
1. Load sciwrite SKILL.md
2. Determine review mode (full-review, section-review, targeted, interactive)
3. Run applicable audit passes
4. Present revised text with severity-tagged report

## Trigger Phrases

### → HEAVY PIPELINE
- "Draft the [section] from this [protocol/data]"
- "Write the methods section"
- "Create the results section from Table X"
- "Generate the discussion"
- "Write the abstract from the completed manuscript"
- "Prepare the manuscript for submission to [journal]"

### → FAST-TRACK
- "Fix this paragraph"
- "Improve clarity"
- "Edit for conciseness"
- "Clean up this prose"
- "Review the writing quality"
- "Check for passive voice"
- "Make this more readable"
- "Polish this abstract"
- "Correct the terminology"
- "Fix translation terminology" (e.g., "change X to keterlihatan")

## Operational Constraints

1. **No bypass of FAST-TRACK for heavy tasks.** If the request introduces new claims or data, it MUST go through the heavy pipeline regardless of how small it seems.

2. **No bypass of human review for visualization.** All figures must be reviewed by a human before use.

3. **Intake gate is mandatory.** The agent must classify the request before executing any skill. No skill loads without routing.

4. **Fast-track is strictly limited.** It cannot be used for:
   - Drafting new sections
   - Adding citations
   - Restructuring arguments
   - Changing factual content
   - Any task that modifies the evidence record
