# PDF → PPTX Conversion: Detailed Rules & Logic

## 1. PDF Assessment Rules (Preflight)

### 1.1 Font Analysis
```
FOR each font in pdf_fonts():
  IF font.embedded == false:
    ADD warning: "Font '{name}' not embedded → will substitute to {fallback}"
    SET font.fallback = match_system_font(font.name, font.weight, font.style)
  IF font.type == "Type3" OR font.type == "CID":
    ADD warning: "Complex font type {type} may not render correctly"
```

### 1.2 Text Extractability
```
text_sample = pdf_extract_text(pages="1-5")
IF text_sample.char_count < 100:
  SET requires_ocr = true
  ADD warning: "Low text extractability - enabling OCR"
ELSE:
  SET requires_ocr = false
```

### 1.3 Layout Complexity Scoring
```
complexity = 0
FOR each page in pdf_info():
  IF page.has_multi_column: complexity += 2
  IF page.has_overlapping_objects: complexity += 3
  IF page.has_vector_art: complexity += 1
  IF page.has_form_fields: complexity += 1
  IF page.rotation != 0: complexity += 1

IF complexity > 10:
  ADD warning: "High layout complexity (score: {complexity}) - expect fragmentation"
```

### 1.4 Size & Batching Decision
```
pages = pdf_info().pages
file_size_mb = pdf_info().file_size / 1024 / 1024

IF pages > 100 OR file_size_mb > 50:
  SET batch_mode = true
  SET batch_size = 25  # pages per batch
  ADD warning: "Large document - will process in batches of {batch_size}"
ELSE:
  SET batch_mode = false
```

---

## 2. Slide Planning Logic

### 2.1 Page-to-Slide Mapping
```
DEFAULT: 1 PDF page → 1 PPTX slide (preserves page numbers, headers/footers)

OPTIONAL modes (configurable):
  - "summarize": Group N pages per slide (N=2,4)
  - "extract": Only slides with significant content changes
```

### 2.2 Slide Dimensions
```
PDF uses points (1/72 inch), PPTX uses EMUs (1/914400 inch)
CONVERSION: emu = points * 12700  (since 914400/72 = 12700)

slide_width_emu  = page.media_box.width  * 12700
slide_height_emu = page.media_box.height * 12700

IF page.rotation in [90, 270]:
  SWAP width/height
  ADD transform: rotate content by -page.rotation
```

### 2.3 Content Extraction Priority (per page)
```
EXTRACTION_ORDER = [
  "background",      # Solid color or image
  "headers_footers", # Repeating elements (detected by position consistency)
  "page_numbers",    # Detect by position + pattern
  "tables",          # Structured data - highest fidelity
  "text_blocks",     # Paragraphs with font/style/position
  "images",          # Raster/vector graphics
  "shapes",          # Lines, rectangles, paths
  "annotations"      # Comments, highlights (optional)
]
```

---

## 3. Object Mapping Rules (PDF → PPTX)

### 3.1 Text Blocks
```
PDF text block → PPTX text box
  position:  (left, top) = (x * 12700, y * 12700)
  size:      (width, height) = (w * 12700, h * 12700)
  text:      concatenate spans preserving line breaks
  font:
    family:  map_font(pdf_font_name) → system_font or "Calibri"
    size:    pdf_font_size * 12700  (EMU)
    color:   pdf_rgb → hex "RRGGBB"
    bold:    pdf_font_flags & 16 != 0
    italic:  pdf_font_flags & 1 != 0
  alignment: detect from text positioning (left/center/right/justify)
  line_spacing: pdf_leading / pdf_font_size (default 1.2)

FRAGMENTATION RULE:
  IF adjacent text blocks have same font/size/color AND vertical gap < 2pt:
    MERGE into single text box
  ELSE:
    KEEP separate
```

### 3.2 Tables
```
PDF table (from pdf_extract_tables) → PPTX table
  position:  (left, top) from table bbox
  size:      auto-fit to content, max slide bounds
  rows/cols: from extracted grid
  cell text: preserve formatting per cell
  borders:   map PDF border style → PPTX border (solid/dashed/none)
  shading:   map PDF cell fill → PPTX cell fill

LIMITATION: Merged cells in PDF → may not map perfectly to PPTX merge
```

### 3.3 Images
```
PDF image (from pdf_to_markdown extract_images) → PPTX picture
  position:  (left, top) from image bbox on page
  size:      (width, height) from bbox
  source:    extracted PNG/SVG at 200 DPI (configurable)
  compression: PPTX default (no additional compression)

QUALITY RULE:
  IF image_dpi < 150: ADD warning "Low-res image on page {n}"
  IF image is vector (SVG): prefer SVG → PPTX converts to shapes
```

### 3.4 Shapes & Paths
```
PDF vector path → PPTX auto-shape or freeform
  SIMPLE rect/ellipse/line → native PPTX shape (rectangle, oval, line)
  COMPLEX path (Bezier curves) → freeform shape with path points
  fill:      PDF fill color/pattern → PPTX solid/gradient/pattern fill
  stroke:    PDF stroke color/width/dash → PPTX line format
  opacity:   PDF alpha → PPTX transparency (0-100%)

GROUPING RULE:
  IF multiple shapes overlap/connect AND share transform:
    GROUP as PPTX group shape
```

### 3.5 Backgrounds
```
PER slide:
  IF page has solid background color:
    SET slide.background.fill.solid(color)
  ELIF page has background image:
    SET slide.background.fill.picture(image_path)
  ELSE:
    INHERIT from slide master

MASTER SLIDE:
  IF same background on >80% pages:
    MOVE to slide master background
    REMOVE from individual slides
```

### 3.6 Headers/Footers/Page Numbers
```
DETECTION:
  Group elements by Y-position across pages
  IF element appears at same Y ± 5pt on >60% pages:
    CLASSIFY as header (top 15%) or footer (bottom 15%)
  IF text matches regex ^\d+$ or "Page \d+":
    CLASSIFY as page number

RECREATION:
  Add to SLIDE MASTER as placeholder shapes
  Page number → use PPTX slide number field
  Header/footer text → static text boxes on master
```

---

## 4. Coordinate Transformation

### 4.1 Origin & Units
```
PDF:  Origin bottom-left, units = points (1/72")
PPTX: Origin top-left,    units = EMUs (1/914400")

TRANSFORM:
  x_emu = x_pt * 12700
  y_emu = (page_height_pt - y_pt - height_pt) * 12700
        = (slide_height_emu - y_emu - height_emu)
```

### 4.2 Rotation Handling
```
IF page.rotation == 90:
  # Content rotated 90° CW in PDF
  # PPTX slide is portrait, content needs -90°
  FOR each element:
    new_x = y
    new_y = page_width - x - width
    new_width = height
    new_height = width
    element.rotation = -90

IF page.rotation == 270:
  new_x = page_height - y - height
  new_y = x
  new_width = height
  new_height = width
  element.rotation = 90
```

---

## 5. Font Handling Strategy

### 5.1 Font Mapping Table
```
PDF Font Family          → PPTX Fallback (Windows)    → PPTX Fallback (Mac/Linux)
---------------------------------------------------------------------------
Helvetica / Arial        → Arial                      → Helvetica / Arial
Times / Times New Roman  → Times New Roman            → Times / Times New Roman
Courier / Courier New    → Courier New                → Courier / Courier New
Symbol                   → Symbol                     → Symbol
ZapfDingbats             → Wingdings                  → ZapfDingbats
Custom/Embedded          → Extract → TTF → install?   → Substitute closest
```

### 5.2 Font Substitution Logic
```
FUNCTION map_font(pdf_font):
  # 1. Exact match on system
  IF system_has_font(pdf_font.name):
    RETURN pdf_font.name

  # 2. Family match
  family = extract_family(pdf_font.name)  # "Helvetica-Bold" → "Helvetica"
  IF system_has_font(family):
    RETURN family

  # 3. Generic family fallback
  generic = classify_generic(pdf_font)  # serif/sans-serif/monospace/cursive/fantasy
  RETURN SYSTEM_DEFAULTS[generic]

  # 4. Last resort
  RETURN "Calibri"
```

### 5.3 Font Metrics Preservation
```
CRITICAL: Font substitution changes glyph widths → text reflow
MITIGATION:
  - Set text box width = original PDF text bbox width
  - Enable "resize shape to fit text" OFF
  - Enable "wrap text in shape" ON
  - If text overflows: ADD warning "Text overflow on slide {n}, box {id}"
```

---

## 6. Conversion Status Tracking

### 6.1 Per-Slide Status Object
```python
@dataclass
class SlideStatus:
    page_number: int
    status: Literal["pending", "processing", "completed", "failed", "partial"]
    elements_planned: int
    elements_created: int
    elements_failed: List[Dict]  # {type, reason, fallback_used}
    warnings: List[str]
    processing_time_ms: int
```

### 6.2 Overall Conversion Status
```python
@dataclass
class ConversionStatus:
    pdf_path: str
    output_path: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_pages: int
    slides_completed: int
    slides_failed: int
    slides_partial: int
    total_elements: int
    elements_created: int
    elements_failed: int
    warnings: List[str]
    errors: List[str]
    batch_info: Optional[BatchInfo]  # if batched
```

### 6.3 Progress Reporting (for UI/Logging)
```
EVENTS (emitted during conversion):
  - "assessment_start"        {pages, file_size}
  - "assessment_complete"     {complexity_score, requires_ocr, warnings}
  - "extraction_start"        {total_pages}
  - "page_extracted"          {page_num, text_blocks, tables, images, shapes}
  - "slide_plan_created"      {page_num, element_count}
  - "pptx_creation_start"     {total_slides}
  - "slide_created"           {page_num, elements_added}
  - "slide_failed"            {page_num, error}
  - "save_complete"           {output_path, file_size}
  - "conversion_complete"     {status: ConversionStatus}
```

---

## 7. Error Handling & Fallback Rules

### 7.1 Element-Level Fallbacks
```
TRY creating native PPTX object
  ON failure:
    IF element is text:
      FALLBACK: render text as image (via pdf_to_markdown image extract)
      FLAG: "text_as_image"
    IF element is table:
      FALLBACK: render table as image
      FLAG: "table_as_image"
    IF element is shape:
      FALLBACK: skip, ADD warning "Shape omitted"
    IF element is image:
      FALLBACK: skip, ADD warning "Image omitted"
    RECORD in slide_status.elements_failed
```

### 7.2 Slide-Level Recovery
```
IF slide has >50% elements failed:
  MARK slide as "partial"
  ADD full-page PDF render as background image
  FLAG: "slide_fallback_full_image"
ELSE:
  MARK slide as "completed" (with warnings)
```

### 7.3 Batch Processing (Large PDFs)
```
IF batch_mode:
  FOR each batch of N pages:
    TRY convert_batch(batch)
    ON batch failure:
      IF retry_count < 2:
        RETRY with lower DPI (150 → 100)
      ELSE:
        MARK batch failed
        CONTINUE next batch
  MERGE successful batch PPTX files → final output
  ADD blank slides for failed batches with error note
```

---

## 8. Validation Rules (Post-Conversion)

### 8.1 Automated Checks
```
CHECKLIST (run after save_presentation):
  ✓ Slide count == PDF page count (or expected batch count)
  ✓ Every slide has at least one element
  ✓ No text boxes with zero width/height
  ✓ All image references resolve (files exist)
  ✓ File size < 500MB (warn if larger)
  ✓ Can open with python-pptx / libxml2 (not corrupt)
```

### 8.2 Visual Fidelity Metrics (Optional)
```
IF validation_mode == "strict":
  FOR each slide:
    Render PDF page to PNG (200 DPI)
    Render PPTX slide to PNG (via headless LibreOffice or python-pptx + cairosvg)
    COMPARE: SSIM > 0.95 → PASS
    IF SSIM < 0.95:
      ADD warning: "Visual drift on slide {n}: SSIM={score}"
```

---

## 9. Configuration Schema (config.yaml)

```yaml
conversion:
  dpi: 200                    # Image extraction DPI
  batch_size: 25              # Pages per batch (0 = no batch)
  ocr_enabled: auto           # auto/always/never
  preserve_headers_footers: true
  preserve_page_numbers: true
  font_substitution: "closest"  # closest/calibri/ask
  merge_fragmented_text: true
  group_related_shapes: true

output:
  validate: false             # Run post-conversion validation
  visual_check: false         # Requires LibreOffice headless
  compress_images: false      # Reduce PPTX size

logging:
  level: "INFO"
  progress_events: true
  save_slide_status: true     # JSON sidecar file
```

---

## 10. Implementation Checklist

### Core Pipeline
- [ ] PDF assessment (fonts, text, complexity)
- [ ] Content extraction (pdf_to_markdown)
- [ ] Slide planning (parse → SlidePlan[])
- [ ] PPTX creation (powerpoint-mcp tools)
- [ ] Save & validate

### Advanced Features
- [ ] Batch processing for >100 pages
- [ ] OCR toggle for scanned PDFs
- [ ] Font extraction & installation (optional)
- [ ] Chart detection → PPTX chart reconstruction
- [ ] Visual validation (SSIM comparison)
- [ ] Progress event streaming (for UI)

### Edge Cases
- [ ] Rotated pages (90/180/270)
- [ ] Mixed page sizes in one PDF
- [ ] PDF forms/annotations
- [ ] Encrypted PDFs (password handling)
- [ ] Right-to-left text (Arabic/Hebrew)
- [ ] Vertical text (CJK)

---

## 11. Testing Matrix

| PDF Type | Pages | Expected Result |
|----------|-------|-----------------|
| Text-native, simple | 10 | Full editable, high fidelity |
| Text-native, complex layout | 20 | Editable, some fragmentation |
| Scanned (no OCR) | 15 | Full-page images only |
| Scanned + OCR | 15 | Editable text, approximate layout |
| Mixed vector/raster | 30 | Shapes + images, good fidelity |
| Charts/tables heavy | 25 | Tables native, charts as shapes |
| 150 pages | 150 | Batched, complete |
| Encrypted | 10 | Prompt for password |
| RTL language | 10 | Text direction preserved |

---

*This specification drives the implementation in `pdf_to_pptx.py`. Each rule maps to a function or validation step.*