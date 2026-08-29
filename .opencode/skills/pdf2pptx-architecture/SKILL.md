---
name: pdf2pptx-architecture
description: Use when converting PDF to PowerPoint (.pptx) presentations with opencode. Covers the complete MCP-based workflow (pdf-tools + powerpoint servers) that runs through the user's OmniRoute/openCode setup: text/image/table/vector extraction, structure detection, slide layout, font/color preservation, collision handling, reflow, summary slide, and quality gates. Also folds in higher-fidelity techniques (role/theme mapping, font emulation, auto-reflow, cross-platform output, validation) as optional tiers of quality.
---

# PDF to PPTX Conversion Architecture

## Purpose & Runtime

Converts a PDF into a .pptx **entirely through opencode MCP servers** that are already
configured for this user:

| Server | Config source | Purpose |
|--------|---------------|---------|
| `pdf-tools` | project `opencode.json` (`uvx mcp-pdf`) | extract text/images/tables/vectors, detect structure, analyze layout |
| `powerpoint` | project `opencode.json` (`uvx --with mcp<2 powerpoint-mcp`) | create/manage slides, populate placeholders, animate |

Both are declared in `C:\Users\hirzi\OneDrive\Documents\Default Project\opencode.json`.
No external conversion service is required — this skill drives the two MCP servers directly.
(OmniRoute only serves the LLM itself; it has no role in file conversion.)

## Tool Inventory

### pdf-tools (analysis/extraction)
- `pdf-tools_textextraction__is_scanned_pdf` — detect image-based PDFs first
- `pdf-tools_textextraction__extract_text` (set `preserve_layout: true` for faithful ordering)
- `pdf-tools_textextraction__ocr_pdf` — required for scanned/image PDFs
- `pdf-tools_imageprocessing__extract_images` (150–300 DPI for slide quality)
- `pdf-tools_imageprocessing__extract_vector_graphics` (SVG for charts/schematics/diagrams)
- `pdf-tools_tableextraction__extract_tables`
- `pdf-tools_structuredetection__detect_structure` (chapters/sections via bookmarks+fonts)
- `pdf-tools_contentanalysis__analyze_layout` (columns, blocks, spacing)
- `pdf-tools_contentanalysis__classify_content` / `summarize_content`
- `pdf-tools_documentanalysis__extract_metadata`, `analyze_pdf_health`
- `pdf-tools_imageprocessing__pdf_to_markdown` / `structuredetection__batch_extract` (bulk)

### powerpoint (construction)
- `powerpoint_manage_presentation` — open/create/save (`create` with optional template)
- `powerpoint_add_slide_with_layout` / `manage_slide` (duplicate/delete/move)
- `powerpoint_populate_placeholder` — text with HTML/LaTeX, images, matplotlib `plot`
- `powerpoint_analyze_template` / `list_templates` — discover layouts & placeholders
- `powerpoint_add_animation` — entrance effects, progressive `by_paragraph` disclosure
- `powerpoint_add_speaker_notes` — presenter notes
- `powerpoint_slide_snapshot` — verify visual output before finishing

## Workflow (core path — always run)

1. **Analyze** — `is_scanned_pdf` → if scanned, `ocr_pdf` first. Extract `metadata`,
   `detect_structure`, `analyze_layout` to learn page count, orientation, columns, sections.
2. **Extract content per page** — text (preserve layout), images (@150–300 DPI, keep aspect),
   tables, vector graphics (SVG). Use `batch_extract`/`pdf_to_markdown` for large files.
3. **Create PPTX** — `manage_presentation(create)`; pick page size to match source
   (landscape source → landscape slides).
4. **Build slides** — map PDF pages → slides:
   - single column → one slide/page
   - multi column → split or use text boxes
   - headers/footers → capture once, apply to a master/layout
5. **Populate** — `populate_placeholder` for text (preserving bold/italic/color via HTML),
   images, plots. `add_slide_with_layout` for section breaks from `detect_structure`.
6. **Apply notes/animations** — speaker notes from page summaries; `add_animation`
   (`fade`/`fly`, `by_paragraph` for progressive bullets).
7. **Verify + save** — `slide_snapshot` per slide, confirm dimensions/readability, `save`.

## Higher-Fidelity Techniques (optional tier — from the enterprise reference)

Apply these when the output must look production-grade, not just be readable:

### Structure / Role mapping
- Use `detect_structure` chapters → section/slide groups.
- Classify span roles: `TITLE, SUBTITLE, BODY, LIST_ITEM, COLUMN_HEADER, HEADER, FOOTER,
  CAPTION`. Themes: Title Slide → `Title` layout, body → `Title+Content`, figures → `Blank`.

### Font metric emulation
- Map unavailable fonts: Helvetica→Arial, Times→Times New Roman, etc.
- After applying, recompute text-box widths via an `avg_width` ratio; placeholders auto-scale.
- Decide embed vs substitute per font; keep paper color/fill contrast.

### Collision resolution
- Detect overlapping text boxes (>20% horizontal overlap).
- Iteratively push down (max ~5 passes); split to a new slide at the slide margin.
- Never let body text overrun the footer/master region.

### Auto-reflow / resize-to-fit
- Enable PowerPoint native resize-to-fit on text frames.
- Use `manage_slide('duplicate')` when a page overflows into a second slide.

### Summary slide
- Append a final "Conversion Summary" slide: active features used, fonts substituted,
  collisions resolved, images/vectors pulled, structure detected.
- This is the audit/traceability slide; keep it human-readable with a branded header.

### Validation / quality gates
- Check text readability and no missing content (compare extracted vs placed).
- Validate images kept aspect ratio; confirm slide dimensions match source orientation.
- Validate the file opens: re-open the .pptx (`open`) and `slide_snapshot` key slides.
- For reliability at scale: treat output as passing only when every source page maps to a
  slide and no text truncates.

### Cross-platform output
- Prefer fonts available in both PowerPoint and Google Slides/Keynote (Arial/Roboto,
  Times/Roboto Serif) so the deck renders on any viewer.
- Keep spacing simple; rely on layout placeholders rather than absolute custom spacing.

## Common Challenges & Fixes

| Challenge | Fix |
|-----------|-----|
| Scanned/image PDF | `ocr_pdf` before extraction |
| Complex multi-column layout | `analyze_layout` to detect columns; use text boxes per column |
| Font substitution shifts layout | font-emulation + auto-reflow; re-check collisions |
| Very large PDF | `batch_extract`/`pdf_to_markdown` in page ranges; process sequentially |
| Vector charts lost | `extract_vector_graphics` → SVG, or render page region to raster |
| PowerPoint tool "no active presentation" | `manage_presentation('create')` / `'open'` first |
| Unknown placeholder names | `analyze_template` / `slide_snapshot` to list shapes & IDs |

## Quality Checklist (final)

- [ ] All source pages represented (no silent drops)
- [ ] Text layers present and readable (OCR handled if scanned)
- [ ] Images at 150–300 DPI, aspect ratio preserved
- [ ] Tables become real tables (not images) where possible
- [ ] Fonts substituted safely, no overlaps
- [ ] Slide dimensions match source orientation
- [ ] Summary slide appended; speaker notes present
- [ ] Output re-opens cleanly and saves

## Notes on the source reference

This `SKILL.md` is the canonical, actively-loaded skill (frontmatter `name` +
`description`; discovered automatically under `.opencode/skills/`). It merges the former
lightweight MCP guide with the best ideas from the enterprise platform reference, scoped so
everything still executes through the pdf-tools + powerpoint MCP servers configured for
this user.

The full self-hosted microservice design (FastAPI/Redis/AWS/Docker — a separate architecture,
not the MCP workflow) is retained in `reference/enterprise-platform.md` inside this skill
folder. It is a non-auto-loading reference for building a hosted service and is **not** part
of the normal opencode conversion path.
