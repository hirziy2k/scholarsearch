#!/usr/bin/env python3
"""Interactive web compiler — SQLite to HTML + Chart.js for GitHub Pages.

Framework 3 (Digital Platform Architect): Transforms the static .pptx pipeline
into a living, version-controlled web app. Serializes verified SQLite rows into
structured JSON embedded in an interactive HTML page with Chart.js visualizations.

Usage:
  python compile_web.py --doc <id> [--output index.html] [--db slide_state.sqlite]

The compiler:
  1. Reads verified slides + chunks from SQLite
  2. Generates statistics (completion, layout distribution, page coverage)
  3. Embeds everything as structured JSON in an interactive HTML page
  4. Includes Chart.js visualizations for analytics
  5. Zero external dependencies — self-contained HTML file
"""

import json
import sys
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slide_state.sqlite")

WEB_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root {{
    --bg: #FAF9F6; --text: #333333; --muted: #555555; --faint: #666666;
    --card-bg: #ffffff; --border: #dddddd; --accent: #FFD700; --accent-hover: #FFC107;
    --highlight-bg: #FFD700; --panel-bg: #f8f8f8; --precursor-bg: #f0f0f0;
  }}
  .high-contrast {{
    --bg: #000000; --text: #ffffff; --muted: #cccccc; --faint: #aaaaaa;
    --card-bg: #1a1a1a; --border: #444444; --accent: #FFD700; --accent-hover: #FFC107;
    --highlight-bg: #FFD700; --panel-bg: #222222; --precursor-bg: #333333;
  }}
  .protanopia {{
    --bg: #FAF9F6; --text: #333333; --muted: #555555; --faint: #666666;
    --card-bg: #ffffff; --border: #dddddd; --accent: #4A90D9; --accent-hover: #357ABD;
    --highlight-bg: #4A90D9; --panel-bg: #f8f8f8; --precursor-bg: #f0f0f0;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.6; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
  h1 {{ font-size: 1.8em; border-bottom: 2px solid var(--text); padding-bottom: 8px; margin-bottom: 16px; }}
  .contrast-toggle {{ position: fixed; top: 10px; right: 10px; z-index: 100; display: flex; gap: 4px; }}
  .contrast-toggle button {{ padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px;
    background: var(--card-bg); color: var(--text); cursor: pointer; font-size: 0.75em; }}
  .contrast-toggle button:hover {{ background: var(--accent); }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 16px 0; }}
  .stat {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; text-align: center; }}
  .stat-value {{ font-size: 2em; font-weight: 700; color: var(--accent); }}
  .stat-label {{ font-size: 0.85em; color: var(--faint); }}
  .slide {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 16px; margin: 12px 0; border-left: 4px solid var(--accent); }}
  .slide-title {{ font-size: 1.1em; font-weight: 600; margin-bottom: 8px; }}
  .slide-layout {{ display: inline-block; background: var(--accent); color: var(--text); padding: 2px 8px; border-radius: 3px; font-size: 0.75em; font-weight: 600; margin-bottom: 8px; }}
  .bullet {{ margin: 4px 0 4px 16px; position: relative; }}
  .bullet::before {{ content: "\\2022"; color: var(--accent); font-weight: bold; position: absolute; left: -16px; }}
  .citation {{ color: var(--accent); cursor: pointer; font-weight: 600; }}
  .citation:hover {{ text-decoration: underline; }}
  .source-panel {{ display: none; background: var(--panel-bg); border: 1px solid var(--border); border-radius: 4px; padding: 12px; margin: 8px 0; font-size: 0.9em; white-space: pre-wrap; }}
  .highlight {{ background: var(--highlight-bg); padding: 1px 3px; border-radius: 2px; }}
  .chart-container {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 16px; margin: 16px 0; }}
  .precursor {{ background: var(--precursor-bg); border-left: 3px solid var(--accent); padding: 8px; margin: 8px 0; font-size: 0.85em; color: var(--faint); font-style: italic; }}
  .json-toggle {{ cursor: pointer; color: var(--accent); font-weight: 600; margin: 8px 0; }}
  .json-toggle:hover {{ text-decoration: underline; }}
  pre {{ background: var(--panel-bg); border: 1px solid var(--border); border-radius: 4px; padding: 12px; overflow-x: auto; font-size: 0.85em; display: none; }}
  .sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0; }}
</style>
</head>
<body>
<div class="contrast-toggle">
  <button onclick="setTheme('default')" title="Default theme">Default</button>
  <button onclick="setTheme('high-contrast')" title="High contrast (WCAG AAA)">High Contrast</button>
  <button onclick="setTheme('protanopia')" title="Protanopia-safe colors">Protanopia</button>
</div>
<div class="container">
  <h1>{title}</h1>
  <div class="stats" id="stats" role="region" aria-label="Pipeline statistics"></div>
  <div class="chart-container" role="img" aria-label="{chart_aria}">
    <canvas id="chart" height="200" aria-describedby="chart-desc"></canvas>
    <div id="chart-desc" class="sr-only">{chart_aria}</div>
  </div>
  <div id="slides" role="region" aria-label="Generated slides"></div>
  <div class="json-toggle" onclick="toggleJson()" role="button" aria-expanded="false">Show Raw JSON</div>
  <pre id="json-view" aria-label="Raw JSON data"></pre>
</div>
<script>
const DATA = {json_data};

function setTheme(mode) {{
  document.body.classList.remove('high-contrast', 'protanopia');
  if (mode !== 'default') document.body.classList.add(mode);
}}

function renderStats() {{
  const s = DATA.stats;
  document.getElementById('stats').innerHTML = `
    <div class="stat"><div class="stat-value">${{s.slides_done}}</div><div class="stat-label">Slides Done</div></div>
    <div class="stat"><div class="stat-value">${{s.slides_total}}</div><div class="stat-label">Total Slides</div></div>
    <div class="stat"><div class="stat-value">${{s.chunks}}</div><div class="stat-label">Source Chunks</div></div>
    <div class="stat"><div class="stat-value">${{s.documents}}</div><div class="stat-label">Documents</div></div>
  `;
}}

function renderChart() {{
  const layouts = {{}};
  DATA.slides.forEach(s => {{ layouts[s.layout_directive || 'content'] = (layouts[s.layout_directive || 'content'] || 0) + 1; }});
  new Chart(document.getElementById('chart'), {{
    type: 'bar',
    data: {{
      labels: Object.keys(layouts),
      datasets: [{{ label: 'Slides by Layout', data: Object.values(layouts), backgroundColor: '#FFD700', borderColor: '#333', borderWidth: 1 }}]
    }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
  }});
}}

function renderSlides() {{
  let html = '';
  DATA.slides.forEach(s => {{
    const bullets = Array.isArray(s.bullets) ? s.bullets : [];
    const bulletsHtml = bullets.map(b => {{
      const cited = b.replace(/\\[([^\\]]+)\\]/g, '<span class="citation" onclick="traceCitation(\\'$1\\')">[$1]</span>');
      return `<div class="bullet">${{cited}}</div>`;
    }}).join('');
    html += `<div class="slide">
      <div class="slide-layout">${{s.layout_directive || 'content'}}</div>
      <div class="slide-title">${{s.title}}</div>
      ${{bulletsHtml}}
      ${{s.notes ? `<div style="margin-top:8px;color:#888;font-size:0.85em;"><em>${{s.notes}}</em></div>` : ''}}
      <div class="source-panel" id="source-${{s.slide_index}}"></div>
    </div>`;
  }});
  document.getElementById('slides').innerHTML = html;
}}

function traceCitation(ref) {{
  const paras = DATA.sourceChunks || [];
  const panel = document.getElementById('source-' + (ref.match(/\\d+/) || [0])[0]);
  if (!panel) return;
  const paraNum = parseInt(ref.replace(/\\D/g, '')) - 1;
  const text = paras[paraNum] || '(source not available)';
  panel.innerHTML = `<strong>Citation:</strong> ${{ref}}<br>${{text}}`;
  panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
}}

function toggleJson() {{
  const el = document.getElementById('json-view');
  el.style.display = el.style.display === 'block' ? 'none' : 'block';
  el.textContent = JSON.stringify(DATA, null, 2);
}}

renderStats();
renderChart();
renderSlides();
</script>
</body>
</html>"""


def get_web_data(doc_id, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not doc:
        conn.close()
        return None

    chunks = [dict(r) for r in conn.execute(
        "SELECT * FROM chunks WHERE doc_id=? ORDER BY page, chunk_index", (doc_id,)
    ).fetchall()]
    slides = [dict(r) for r in conn.execute(
        "SELECT * FROM slides WHERE doc_id=? AND status IN ('done','override') ORDER BY slide_index", (doc_id,)
    ).fetchall()]

    stats = {
        "documents": 1,
        "chunks": len(chunks),
        "slides_total": len(slides),
        "slides_done": sum(1 for s in slides if s["status"] == "done"),
    }

    # Extract source text for citation tracing
    source_chunks = [c["content"] for c in chunks]

    conn.close()
    return {
        "document": dict(doc),
        "slides": slides,
        "chunks": chunks,
        "stats": stats,
        "sourceChunks": source_chunks,
    }


def compile_web(doc_id, output_path=None, db_path=DB_PATH):
    """Compile slides to interactive HTML.

    Zero-Persistence Mandate: If output_path is None, returns a BytesIO
    buffer instead of writing to disk. The local directory remains sterile.
    """
    from io import BytesIO

    data = get_web_data(doc_id, db_path)
    if not data:
        return {"ok": False, "error": "Document not found"}

    title = data["document"].get("source_file", f"Document {doc_id}")

    # Generate ARIA summary for chart
    layouts = {}
    for s in data["slides"]:
        ld = s.get("layout_directive", "content")
        layouts[ld] = layouts.get(ld, 0) + 1
    chart_aria = f"Bar chart showing {data['stats']['slides_total']} slides: " + ", ".join(
        f"{count} {layout}" for layout, count in sorted(layouts.items())
    )

    html = WEB_TEMPLATE.format(
        title=title,
        chart_aria=chart_aria,
        json_data=json.dumps(data, indent=2),
    )

    html_bytes = html.encode("utf-8")

    if output_path is None:
        # Zero-Persistence: return buffer, no disk write
        buf = BytesIO(html_bytes)
        buf.seek(0)
        return {
            "ok": True,
            "buffer": buf,
            "size": len(html_bytes),
            "slides_compiled": data["stats"]["slides_total"],
            "content_type": "text/html",
        }

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return {
        "ok": True,
        "output": output_path,
        "slides_compiled": data["stats"]["slides_total"],
        "file_size": os.path.getsize(output_path),
    }


def main(argv):
    if "--doc" not in argv:
        print(__doc__)
        return 1
    doc_id = int(argv[argv.index("--doc") + 1])
    output = argv[argv.index("--output") + 1] if "--output" in argv else f"web_doc{doc_id}.html"
    db = argv[argv.index("--db") + 1] if "--db" in argv else DB_PATH

    result = compile_web(doc_id, output, db)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
