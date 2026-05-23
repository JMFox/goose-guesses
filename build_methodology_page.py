"""Render METHODOLOGY.md to methodology.html with MathJax + psychedelic style."""
import html, json
from pathlib import Path

from render_html import SHARED_CSS, GRAIN, MATH_SVG, nav, head, PAGE_TPL

ROOT = Path(__file__).parent
md = (ROOT / "METHODOLOGY.md").read_text(encoding="utf-8")
parameters = json.load(open(ROOT / "parameters.json", encoding="utf-8"))

EXTRA_CSS = SHARED_CSS + """
.mdwrap{padding:30px 34px; border-radius:20px;
  background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.10);
  backdrop-filter:blur(8px); margin:8px 0; line-height:1.7; font-size:.95rem;
  font-weight:300}
.mdwrap h1{display:none}
.mdwrap h2{font-family:'Righteous',sans-serif; color:#fff; font-size:1.4rem;
  margin:28px 0 10px; padding-top:14px; border-top:1px dashed rgba(255,255,255,.18)}
.mdwrap h2:first-child{border-top:0; padding-top:0; margin-top:0}
.mdwrap h3{font-family:'Righteous',sans-serif; color:#ffd6f1; font-size:1.1rem;
  margin:18px 0 8px}
.mdwrap h4{color:#ffae00; font-size:1rem; margin:14px 0 6px}
.mdwrap p{margin:8px 0; color:var(--ink)}
.mdwrap ul, .mdwrap ol{padding-left:22px; margin:8px 0}
.mdwrap li{margin:5px 0}
.mdwrap code{font-family:'Courier New',monospace; padding:2px 6px; border-radius:5px;
  background:rgba(255,255,255,.08); color:#ffd6f1; font-size:.88em}
.mdwrap pre{padding:14px 18px; border-radius:10px; background:rgba(0,0,0,.4);
  border:1px solid rgba(255,255,255,.08); overflow-x:auto}
.mdwrap pre code{background:transparent; padding:0; color:#aaff00}
.mdwrap blockquote{border-left:3px solid #ff2d95; padding:6px 14px; margin:14px 0;
  background:rgba(255,45,149,.06); color:var(--muted); font-style:italic}
.mdwrap table{border-collapse:collapse; margin:14px 0; font-size:.88rem; width:100%}
.mdwrap th{text-align:left; padding:8px 12px; background:rgba(255,45,149,.18); color:#fff;
  border:1px solid rgba(255,255,255,.10); font-family:'Righteous',sans-serif; font-weight:400}
.mdwrap td{padding:7px 12px; border:1px solid rgba(255,255,255,.10); color:var(--ink)}
.mdwrap tr:nth-child(even) td{background:rgba(255,255,255,.04)}
.mdwrap a{color:#7ef9ff; text-decoration:none; border-bottom:1px solid rgba(126,249,255,.3)}
.mdwrap a:hover{color:#aaff00; border-bottom-color:#aaff00}
.mdwrap hr{border:none; border-top:1px dashed rgba(255,255,255,.25); margin:24px 0}
.mdwrap strong{color:#ffd6f1; font-weight:600}
.mdwrap em{color:#aaff00}

/* MathJax rendering tweak */
mjx-container{color:#fff !important}
.mjx-math{font-size:1.05em}
/* Make display math scrollable horizontally if wider than viewport */
mjx-container[display="true"]{overflow-x:auto !important; overflow-y:hidden !important;
  max-width:100%; padding:6px 2px; -webkit-overflow-scrolling:touch}
mjx-container[display="true"]::-webkit-scrollbar{height:6px}
mjx-container[display="true"]::-webkit-scrollbar-thumb{background:rgba(255,45,149,.4); border-radius:3px}
.mdwrap{overflow-wrap:break-word; word-wrap:break-word}

/* Parameter TL;DR table */
.param-tldr{padding:24px 28px; border-radius:20px; margin:16px 0 28px;
  background:linear-gradient(135deg,rgba(0,240,255,.10),rgba(170,255,0,.10));
  border:1px solid rgba(0,240,255,.35); backdrop-filter:blur(10px)}
.param-tldr h3{margin:0 0 6px; font-family:'Righteous',sans-serif; color:#fff;
  font-size:1.2rem; display:flex; gap:10px; align-items:center}
.param-tldr p.sub{margin:0 0 16px; color:var(--muted); font-size:.88rem}
.param-tldr table{width:100%; border-collapse:collapse; font-size:.85rem}
.param-tldr th{font-family:'Righteous',sans-serif; font-weight:400; font-size:.78rem;
  text-transform:uppercase; letter-spacing:.1em; text-align:left; color:#aaff00;
  padding:8px 10px; border-bottom:1px solid rgba(255,255,255,.12); background:transparent}
.param-tldr td{padding:9px 10px; border-bottom:1px solid rgba(255,255,255,.07);
  vertical-align:top; color:var(--ink)}
.param-tldr tr:last-child td{border-bottom:0}
.param-tldr .pname{font-family:'Righteous',sans-serif; color:#ffd6f1; font-size:.95rem}
.param-tldr .pname .sub{color:var(--muted); font-size:.72rem; font-family:inherit;
  text-transform:none; letter-spacing:0; display:block; margin-top:2px; font-weight:300}
.param-tldr .pdef{font-family:'Courier New',monospace; color:#ffae00;
  background:rgba(255,174,0,.08); padding:2px 8px; border-radius:6px; display:inline-block; font-size:.82rem}
.param-tldr .prange{color:var(--muted); font-size:.78rem; font-family:'Courier New',monospace}
.param-tldr .punc{display:inline-block; padding:2px 8px; border-radius:999px; font-size:.7rem;
  font-family:'Righteous',sans-serif; letter-spacing:.05em; text-transform:uppercase}
.param-tldr .unc-low{background:rgba(170,255,0,.15); color:#aaff00}
.param-tldr .unc-medium{background:rgba(255,174,0,.15); color:#ffd680}
.param-tldr .unc-high{background:rgba(255,45,149,.18); color:#ff8ac4}
.param-tldr .pdesc{font-size:.84rem; color:var(--ink); font-weight:300}
.param-tldr .sectag{font-family:'Righteous',sans-serif; font-size:.7rem; color:#7ef9ff;
  background:rgba(0,240,255,.10); padding:2px 7px; border-radius:5px; letter-spacing:.04em}
.param-tldr .legend{display:flex; gap:14px; flex-wrap:wrap; margin-top:14px; padding-top:12px;
  border-top:1px dashed rgba(255,255,255,.15); color:var(--muted); font-size:.78rem}

/* ──── Mobile: collapse parameter table into stacked cards, scroll math ──── */
@media (max-width: 720px){
  .mdwrap{padding:18px 16px; font-size:.92rem; border-radius:14px}
  .mdwrap h2{font-size:1.15rem; margin:18px 0 8px}
  .mdwrap h3{font-size:1rem; margin:14px 0 6px}
  .mdwrap h4{font-size:.92rem; margin:10px 0 4px}
  .mdwrap pre{padding:10px 12px; font-size:.78rem}
  .mdwrap table{font-size:.78rem; display:block; overflow-x:auto;
    -webkit-overflow-scrolling:touch}
  .mdwrap blockquote{padding:6px 10px; font-size:.86rem}
  .mdwrap ul, .mdwrap ol{padding-left:18px}

  .param-tldr{padding:18px 14px}
  .param-tldr h3{font-size:1.05rem}
  /* Convert table to stacked cards on small screens */
  .param-tldr table, .param-tldr thead, .param-tldr tbody,
  .param-tldr tr, .param-tldr td, .param-tldr th{display:block; width:100%}
  .param-tldr thead{display:none}
  .param-tldr tr{margin-bottom:14px; padding:12px 14px; border-radius:12px;
    background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.10)}
  .param-tldr td{border:0; padding:4px 0; position:relative}
  .param-tldr td:nth-child(1) .pname{font-size:1.02rem}
  .param-tldr td:nth-child(2){display:inline-block; margin-right:8px}
  .param-tldr td:nth-child(3){display:inline-block}
  .param-tldr td:nth-child(4){margin-top:6px; font-size:.84rem}
  .param-tldr td:nth-child(5){display:inline-block; margin-top:4px}
  .param-tldr .pdesc{margin-top:6px}
  .param-tldr .legend{font-size:.72rem; gap:8px}
}

@media (max-width: 480px){
  .param-tldr td:nth-child(2),
  .param-tldr td:nth-child(3),
  .param-tldr td:nth-child(5){display:inline-block; margin-right:8px}
}
"""

# ─────────────────────────────────────────────────────── parameter TL;DR table
groupings = {
    "base_rate": "Base Rate",
    "gap_factor": "Gap & Bustout",
    "set_position": "Set-Position Priors",
    "multi_night": "Multi-Night",
    "venue": "Venue & Leg",
    "debuts": "New Material",
    "wildcards": "Wildcards",
    "normalization": "Soundness",
}

rows = []
for sec_key, sec_label in groupings.items():
    sec_params = [p for p in parameters["parameters"] if p["section"] == sec_key]
    for p in sec_params:
        unc = p.get("uncertainty", "medium")
        step = p.get("step", 0.01)

        def fmt(v):
            if step >= 1: return str(int(v))
            if step >= 0.1: return f"{v:.1f}"
            return f"{v:.2f}"

        rows.append(f'''        <tr>
          <td class="pname">🪿 {html.escape(p["display_name"])}<span class="sub">{html.escape(p["subtitle"])}</span></td>
          <td><span class="sectag">{html.escape(sec_label)}</span></td>
          <td><span class="pdef">{fmt(p["default"])}</span><br><span class="prange">[{fmt(p["min"])}, {fmt(p["max"])}]</span></td>
          <td class="pdesc">{html.escape(p["description"])}</td>
          <td><span class="punc unc-{unc}">{unc}</span></td>
        </tr>''')

tldr_html = f'''
    <section class="param-tldr">
      <h3>🎚️ TL;DR — All 20 tunable parameters at a glance</h3>
      <p class="sub">Every lever you can pull on the <a href="model.html" style="color:#7ef9ff">Model page</a>. Defaults are calibrated to historical data; uncertainty tags reflect how confident we are in the default.</p>
      <table>
        <thead><tr>
          <th>Parameter</th>
          <th>Section</th>
          <th>Default · Range</th>
          <th>What it does (Goose-y)</th>
          <th>Conf.</th>
        </tr></thead>
        <tbody>
{chr(10).join(rows)}
        </tbody>
      </table>
      <div class="legend">
        <span><span class="punc unc-low">low</span> = well-calibrated from data</span>
        <span><span class="punc unc-medium">medium</span> = empirical but speculative</span>
        <span><span class="punc unc-high">high</span> = expert prior, no data</span>
        <span style="margin-left:auto">{len(parameters["parameters"])} parameters · {len(parameters["stickiness_overrides"])} song overrides · {len(parameters["venue_tiers"])} venue tiers</span>
      </div>
    </section>
'''


# ─────────────────────────────────────────────────────────────────── page body
body = f'''
    <section class="assume">
      <h3><span class="icon">📜</span>Read the proofs</h3>
      <ol>
        <li>This is the full GooseGuesses methodology spec (v1.0, 4,465 words). It defines the multiplicative-factor probability model, the show-length slot identity, the Bayesian Night-1 → Night-2 update, the gap multiplier, debut handling, validation plan, and known limitations.</li>
        <li>All formulas render in LaTeX via MathJax. The corresponding interactive controls live on the <a href="model.html">Model page</a>.</li>
        <li>References cited: Trey's Notebook (Phish.net), Andrew Reed's Phish LSTM (Brier ~0.040), "Pattern in Phish's Predictability" (Phish.net 2013), McFadden 1973 discrete choice, Plackett 1975, Luce 1959, Murphy 1973 Brier decomposition.</li>
      </ol>
    </section>
    {tldr_html}
    <div class="mdwrap" id="md"></div>
'''

# ─────────────────────────────────── client-side: protect math, then markdown
extra_head = '''
  <script>window.MathJax = {tex:{inlineMath:[['$','$']], displayMath:[['$$','$$']], processEscapes:true}, options: {skipHtmlTags:['script','noscript','style','textarea']}};</script>
  <script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
'''

# Embed the MD as a JS string. Double the backslashes for JS string literal.
md_escaped = (md
              .replace("\\", "\\\\")
              .replace("`", "\\`")
              .replace("${", "\\${"))

# IMPORTANT: protect $...$ and $$...$$ from marked.js so it doesn't mangle
# underscores or backslashes inside LaTeX. We replace each math block with a
# unique placeholder before parsing, then substitute back after.
render_script = f'''
<script>
const MD = `{md_escaped}`;

function protectMath(src) {{
  const blocks = [];
  // Display math: $$...$$ (greedy is fine since the source has no nested $$)
  src = src.replace(/\\$\\$([\\s\\S]+?)\\$\\$/g, (m, inner) => {{
    blocks.push('$$' + inner + '$$');
    return `\\u0001MATHBLOCK${{blocks.length-1}}\\u0001`;
  }});
  // Inline math: $...$ (avoid matching $ next to digits which is rare here)
  src = src.replace(/\\$([^\\$\\n]+?)\\$/g, (m, inner) => {{
    blocks.push('$' + inner + '$');
    return `\\u0001MATHINLINE${{blocks.length-1}}\\u0001`;
  }});
  return [src, blocks];
}}

function restoreMath(html, blocks) {{
  return html.replace(/\\u0001MATH(BLOCK|INLINE)(\\d+)\\u0001/g, (m, kind, idx) => blocks[parseInt(idx, 10)]);
}}

window.addEventListener('DOMContentLoaded', () => {{
  const el = document.getElementById('md');
  marked.setOptions({{breaks:false, gfm:true, mangle:false, headerIds:true}});
  const [protectedSrc, blocks] = protectMath(MD);
  const rawHtml = marked.parse(protectedSrc);
  el.innerHTML = restoreMath(rawHtml, blocks);
  if (window.MathJax && MathJax.typesetPromise){{
    MathJax.typesetPromise([el]).catch(e => console.error('MathJax error', e));
  }} else {{
    // MathJax may not have loaded yet (async). Try again on a small delay.
    setTimeout(() => {{
      if (window.MathJax && MathJax.typesetPromise){{
        MathJax.typesetPromise([el]).catch(e => console.error('MathJax error', e));
      }}
    }}, 800);
  }}
}});
</script>
'''

page_html = PAGE_TPL.format(
    head=head("Methodology").replace(SHARED_CSS, EXTRA_CSS) + extra_head,
    grain=GRAIN,
    nav=nav("meth"),
    art=MATH_SVG,
    kicker="GooseGuesses · Methodology v1.0",
    h1="The Math",
    venue="Defensible probabilistic setlist prediction",
    dates="May 23, 2026",
    format="4,465 words · 12 sections · 20-parameter table · MathJax rendered",
    body=body,
) + render_script + "</body></html>"

(ROOT / "methodology.html").write_text(page_html, encoding="utf-8")
print("wrote methodology.html")
