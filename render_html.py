"""Render psychedelic, goose-y HTML prediction pages.

Outputs:
  index.html          — landing page with cards
  amsterdam.html      — both Amsterdam nights side-by-side
  msg_n1.html         — MSG Night 1
  msg_n2.html         — MSG Night 2 (Bayesian-conditioned on N1)
  model.html          — interactive math + tunable forecasting model
  methodology.html    — full LaTeX-rendered methodology

All pages share visual identity:
  - Animated radial-gradient psychedelic backgrounds
  - SVG goose silhouettes, mandalas, halos
  - Monoton + Righteous + Poppins typography
  - Assumption box AT TOP of every prediction page
"""
import json, html
from pathlib import Path

ROOT = Path(__file__).parent
predictions = json.load(open(ROOT / "predictions.json", encoding="utf-8"))
parameters = json.load(open(ROOT / "parameters.json", encoding="utf-8"))
stats = json.load(open(ROOT / "stats.json", encoding="utf-8"))


# ───────────────────────────────────────────────────────────────────── styles
SHARED_CSS = """
:root{
  --bg0:#0a0a2e; --bg1:#070719; --ink:#f6ecff; --muted:#bba7e0;
  --pink:#ff2d95; --cyan:#00f0ff; --lime:#aaff00; --orange:#ff7b00;
  --purple:#b14aed; --gold:#ffae00; --leaf:#5be8a0;
}
*{box-sizing:border-box} html{scroll-behavior:smooth}
body{margin:0; min-height:100vh; color:var(--ink); font-family:'Poppins',system-ui,sans-serif;
  background:var(--bg1); overflow-x:hidden; line-height:1.55; font-weight:300;
  letter-spacing:0.01em;}

/* Animated psychedelic background */
body::before{content:''; position:fixed; inset:-25%; z-index:-2;
  background:
    radial-gradient(38% 38% at 20% 28%, rgba(255,45,149,.55), transparent 62%),
    radial-gradient(42% 42% at 82% 18%, rgba(0,240,255,.40), transparent 62%),
    radial-gradient(48% 48% at 72% 82%, rgba(177,74,237,.55), transparent 62%),
    radial-gradient(40% 40% at 24% 78%, rgba(255,123,0,.40), transparent 62%),
    radial-gradient(30% 30% at 50% 50%, rgba(170,255,0,.15), transparent 62%),
    radial-gradient(60% 60% at 50% 50%, #2d0a4e, #07071f 78%);
  animation: drift 28s ease-in-out infinite alternate;
  filter:blur(80px) saturate(140%);
}
@keyframes drift{
  0%{transform:translate(-3%,-2%) scale(1.15) rotate(0deg); filter:blur(80px) saturate(140%) hue-rotate(0deg)}
  100%{transform:translate(3%,2%) scale(1.32) rotate(10deg); filter:blur(80px) saturate(140%) hue-rotate(55deg)}}
.grain{position:fixed; inset:0; z-index:-1; width:100%; height:100%; opacity:.10; mix-blend-mode:overlay; pointer-events:none}

.wrap{max-width:980px; margin:0 auto; padding:28px 22px 80px}

/* Hero */
header.hero{position:relative; text-align:center; padding:48px 12px 28px}
.halo{position:absolute; top:-10px; left:50%; transform:translateX(-50%); width:320px; height:320px; border-radius:50%;
  background:conic-gradient(from 0deg,#ff2d95,#ff7b00,#aaff00,#00f0ff,#b14aed,#ff2d95);
  filter:blur(3px) saturate(180%); opacity:.45; z-index:0;
  -webkit-mask:radial-gradient(closest-side,transparent 58%,#000 60%,#000 78%,transparent 80%);
          mask:radial-gradient(closest-side,transparent 58%,#000 60%,#000 78%,transparent 80%);
  animation:spin 26s linear infinite}
.halo.two{width:220px;height:220px;animation:spin 17s linear infinite reverse;opacity:.5}
@keyframes spin{to{transform:translateX(-50%) rotate(360deg)}}

.goose-art{position:relative; z-index:1; width:140px; height:140px; margin:0 auto;
  filter:drop-shadow(0 8px 24px rgba(0,0,0,.5)); animation:bob 4.6s ease-in-out infinite}
@keyframes bob{0%,100%{transform:translateY(0) rotate(-4deg)}50%{transform:translateY(-12px) rotate(4deg)}}

.kicker{position:relative; z-index:1; margin:18px 0 4px; letter-spacing:.55em; text-transform:uppercase;
  font-size:.74rem; color:var(--muted); font-weight:500}
h1{position:relative; z-index:1; font-family:'Monoton',cursive; font-weight:400; margin:.1em 0;
  font-size:clamp(2.3rem,7vw,4.4rem); line-height:1.02;
  background:linear-gradient(90deg,#ff2d95,#00f0ff,#aaff00,#ff7b00,#b14aed,#ff2d95);
  background-size:300% 100%;
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; color:transparent;
  filter:drop-shadow(0 0 22px rgba(255,45,149,.4)); animation:flow 9s linear infinite}
@keyframes flow{to{background-position:300% 0}}
.venue{position:relative; z-index:1; font-family:'Righteous',sans-serif;
  font-size:clamp(1.15rem,3.4vw,1.8rem); margin-top:8px}
.dates{position:relative; z-index:1; color:var(--muted); margin-top:4px; font-weight:300}
.format{position:relative; z-index:1; display:inline-block; margin-top:18px; padding:8px 18px; border-radius:999px;
  font-size:.84rem; font-weight:500;
  background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.18); backdrop-filter:blur(6px)}

/* Nav */
nav{display:flex; gap:10px; justify-content:center; flex-wrap:wrap; margin:14px 0 30px}
nav a{color:var(--ink); text-decoration:none; font-size:.86rem; font-weight:500; padding:9px 18px;
  border-radius:999px; border:1px solid rgba(255,255,255,.18); background:rgba(255,255,255,.05); transition:.25s}
nav a:hover{background:rgba(255,45,149,.25); border-color:#ff2d95; transform:translateY(-2px)}
nav a.active{background:linear-gradient(90deg,#ff2d95,#b14aed); border-color:transparent}

/* Assumption box — at TOP */
.assume{margin:6px 0 22px; border-radius:20px; padding:24px 26px;
  background:linear-gradient(135deg,rgba(177,74,237,.16),rgba(255,45,149,.10));
  border:1px solid rgba(177,74,237,.42); backdrop-filter:blur(10px);
  box-shadow:0 8px 30px rgba(0,0,0,.25)}
.assume h3{margin:0 0 14px; font-family:'Righteous',sans-serif; font-size:1.18rem; color:#fff;
  display:flex; gap:10px; align-items:center}
.assume h3 .icon{font-size:1.4rem}
.assume ol{margin:0; padding-left:20px; color:var(--ink); font-size:.94rem; font-weight:300}
.assume li{margin:8px 0}
.assume li strong, .assume li b{color:#ffd6f1; font-weight:600}
.assume .cov{margin-top:16px; font-size:.86rem; color:var(--muted);
  border-top:1px dashed rgba(255,255,255,.22); padding-top:12px}
.assume .cov strong{color:#7ef9ff}

/* Section labels */
.seclabel{font-family:'Righteous',sans-serif; font-size:1.2rem; margin:38px 4px 14px;
  display:flex; align-items:center; gap:12px; color:#fff}
.seclabel::after{content:''; flex:1; height:1px; background:linear-gradient(90deg,rgba(255,255,255,.5),transparent)}

/* Song list */
ol.list,ul.list{list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:11px}
.song{display:flex; gap:14px; align-items:flex-start; padding:14px 18px; border-radius:18px;
  background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.10);
  backdrop-filter:blur(8px); transition:transform .2s, border-color .2s, background .2s;
  opacity:0; transform:translateY(14px); animation:rise .5s ease forwards;
  animation-delay:calc(var(--i)*55ms)}
@keyframes rise{to{opacity:1; transform:translateY(0)}}
.song:hover{transform:translateY(-3px) scale(1.012); background:rgba(255,255,255,.09); border-color:rgba(255,45,149,.55)}
.rank{flex:0 0 38px; height:38px; display:grid; place-items:center; font-weight:700;
  font-family:'Righteous',sans-serif; border-radius:11px; font-size:1rem;
  background:rgba(255,255,255,.09); border:1px solid rgba(255,255,255,.14)}
.body{flex:1; min-width:0}
.meta{display:flex; justify-content:space-between; align-items:baseline; gap:10px}
.name{font-weight:500; font-size:1.06rem; text-shadow:0 0 14px rgba(255,255,255,.14)}
.pct{font-family:'Righteous',sans-serif; font-size:1.05rem; white-space:nowrap;
  background:linear-gradient(90deg,var(--c1),var(--c2));
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; color:transparent}
.track{margin:8px 0 7px; height:12px; border-radius:999px;
  background:rgba(255,255,255,.08); overflow:hidden}
.fill{display:block; height:100%; width:0; border-radius:inherit;
  background:linear-gradient(90deg,var(--c1),var(--c2)); background-size:220% 100%;
  box-shadow:0 0 18px var(--c2);
  animation:grow 1.3s cubic-bezier(.2,.85,.25,1) forwards, shimmer 3.4s linear infinite;
  animation-delay:calc(var(--i)*55ms + .15s), 0s}
@keyframes grow{to{width:calc(var(--p)*1%)}}
@keyframes shimmer{to{background-position:220% 0}}
.why{margin:0; font-size:.83rem; color:var(--muted); font-weight:300}

.blaze{--c1:#ff2d95;--c2:#ffae00}
.hot{--c1:#ff2d95;--c2:#b14aed}
.warm{--c1:#8b5cff;--c2:#00d0ff}
.cool{--c1:#00f0ff;--c2:#3a7bff}

.song.wild{border-style:dashed; border-color:rgba(170,255,0,.4); background:rgba(170,255,0,.05)}
.song.wild .rank{background:rgba(170,255,0,.12); border-color:rgba(170,255,0,.3)}

/* Note callout */
.note{margin:18px 0; padding:16px 20px; border-radius:14px; font-size:.92rem; color:var(--ink);
  background:rgba(0,240,255,.07); border:1px solid rgba(0,240,255,.22); backdrop-filter:blur(6px)}
.note b{color:#7ef9ff}

/* Footer */
footer{margin-top:60px; text-align:center; color:var(--muted); font-size:.78rem; font-weight:300}
footer a{color:#ff8ac4}

/* Index cards */
.cards{display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:20px; margin:14px 0}
.card{position:relative; overflow:hidden; border-radius:24px; padding:32px 26px; text-decoration:none;
  color:var(--ink); border:1px solid rgba(255,255,255,.16); background:rgba(255,255,255,.05);
  backdrop-filter:blur(8px); transition:.3s; display:flex; flex-direction:column; gap:6px; min-height:240px}
.card:hover{transform:translateY(-7px); border-color:#ff2d95;
  box-shadow:0 20px 55px rgba(177,74,237,.4)}
.card .cgoose{font-size:60px; line-height:1}
.card h2{font-family:'Righteous',sans-serif; margin:8px 0 0; font-size:1.6rem}
.card .csub{color:var(--muted); font-size:.88rem}
.card .cgo{margin-top:auto; font-weight:600; font-size:.86rem; color:#ff8ac4}
.card::after{content:''; position:absolute; inset:auto -40% -60% auto; width:280px; height:280px;
  border-radius:50%; filter:blur(45px); opacity:.55; transition:.3s}
.card.ams::after{background:radial-gradient(circle,#00f0ff,transparent 70%)}
.card.msg::after{background:radial-gradient(circle,#ff2d95,transparent 70%)}
.card.math::after{background:radial-gradient(circle,#aaff00,transparent 70%)}
.card.meth::after{background:radial-gradient(circle,#b14aed,transparent 70%)}

/* Two-column comparison */
.twocol{display:grid; grid-template-columns:1fr 1fr; gap:24px; margin-top:18px}
@media(max-width:760px){.twocol{grid-template-columns:1fr}}

/* Stats grid */
.statgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:12px 0 20px}
.statgrid .stat{padding:14px 16px; border-radius:14px; background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.10)}
.statgrid .stat .num{font-family:'Righteous',sans-serif; font-size:1.4rem; color:#fff;
  background:linear-gradient(90deg,#ff2d95,#ffae00);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent}
.statgrid .stat .lbl{color:var(--muted); font-size:.78rem; margin-top:4px}

/* Image strip */
.imgstrip{display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:18px 0;
  border-radius:16px; overflow:hidden}
.imgstrip > div{aspect-ratio:1/1; background-size:cover; background-position:center;
  filter:saturate(1.3) hue-rotate(-10deg); position:relative}
.imgstrip > div::after{content:''; position:absolute; inset:0;
  background:linear-gradient(180deg, transparent 30%, rgba(7,7,31,.7));
  mix-blend-mode:multiply}

/* ───────────────────── MOBILE-FIRST RESPONSIVE OVERRIDES ───────────────────── */
@media (max-width: 640px){
  .wrap{padding:14px 12px 60px}
  header.hero{padding:30px 4px 18px}
  .goose-art{width:110px; height:110px}
  .halo{width:230px; height:230px}
  .halo.two{width:160px; height:160px}
  .kicker{letter-spacing:.35em; font-size:.66rem; margin:12px 0 2px}
  h1{font-size:clamp(1.9rem, 11vw, 3rem) !important; line-height:1.05}
  .venue{font-size:1rem}
  .dates{font-size:.85rem}
  .format{font-size:.74rem; padding:6px 12px}
  nav{gap:6px; margin:8px -4px 20px; overflow-x:auto; flex-wrap:nowrap;
    -webkit-overflow-scrolling:touch; padding:4px}
  nav a{font-size:.78rem; padding:7px 12px; white-space:nowrap; flex:0 0 auto}
  .assume{padding:18px 16px; border-radius:14px}
  .assume h3{font-size:1rem; flex-wrap:wrap; gap:6px}
  .assume h3 > span:last-child{margin-left:0 !important; width:100%; font-size:.7rem !important}
  .assume ol{font-size:.86rem; padding-left:18px}
  .assume li{margin:6px 0}
  .assume .cov{font-size:.78rem}
  .seclabel{font-size:1.05rem; margin:24px 2px 10px}
  .song{padding:11px 12px; gap:10px; border-radius:14px}
  .rank{flex:0 0 32px; height:32px; font-size:.88rem}
  .name{font-size:.95rem}
  .pct{font-size:.95rem}
  .why{font-size:.76rem; line-height:1.45}
  .track{height:9px}
  .note{padding:12px 14px; font-size:.84rem; border-radius:12px}
  .cards{grid-template-columns:1fr; gap:14px}
  .card{padding:24px 18px; min-height:auto}
  .card .cgoose{font-size:46px}
  .card h2{font-size:1.3rem}
  .statgrid{grid-template-columns:repeat(2, 1fr); gap:8px}
  .statgrid .stat{padding:11px 12px}
  .statgrid .stat .num{font-size:1.15rem}
  .statgrid .stat .lbl{font-size:.7rem}
  .twocol{grid-template-columns:1fr; gap:20px}
  .imgstrip{grid-template-columns:1fr 1fr; gap:8px}
  .imgstrip > div:nth-child(3){display:none}
}

/* Always allow long names to wrap so they don't blow out the layout */
.song .meta{flex-wrap:wrap}
.song .name{word-break:break-word; overflow-wrap:anywhere}
"""

GRAIN = """<svg class="grain" xmlns="http://www.w3.org/2000/svg"><defs>
  <filter id="liquid"><feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="2" seed="7" result="n">
    <animate attributeName="baseFrequency" values="0.010;0.020;0.010" dur="20s" repeatCount="indefinite"/></feTurbulence>
    <feColorMatrix in="n" type="saturate" values="0"/></filter></defs>
  <rect width="100%" height="100%" filter="url(#liquid)"/></svg>"""

# Inline SVG goose silhouettes
GOOSE_SVG = '''<svg class="goose-art" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="goose-grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#ff2d95"/>
      <stop offset="50%" stop-color="#b14aed"/>
      <stop offset="100%" stop-color="#00f0ff"/>
    </linearGradient>
    <radialGradient id="eye-grad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#fff"/>
      <stop offset="60%" stop-color="#aaff00"/>
      <stop offset="100%" stop-color="#0a0a2e"/>
    </radialGradient>
  </defs>
  <!-- Goose body -->
  <ellipse cx="105" cy="120" rx="55" ry="42" fill="url(#goose-grad)" opacity="0.85"/>
  <!-- Neck -->
  <path d="M 80 90 Q 60 55, 75 30 Q 85 18, 100 22 Q 115 26, 115 45 Q 115 70, 100 90 Z"
        fill="url(#goose-grad)" opacity="0.9"/>
  <!-- Head -->
  <ellipse cx="100" cy="28" rx="22" ry="18" fill="url(#goose-grad)"/>
  <!-- Beak (orange) -->
  <path d="M 78 28 L 60 32 L 78 36 Z" fill="#ff7b00"/>
  <!-- Eye (psychedelic) -->
  <circle cx="105" cy="26" r="6" fill="url(#eye-grad)"/>
  <circle cx="105" cy="26" r="2.2" fill="#0a0a2e"/>
  <!-- Tail -->
  <path d="M 155 115 Q 178 105 182 130 Q 165 130 155 125 Z" fill="url(#goose-grad)" opacity="0.85"/>
  <!-- Wing -->
  <ellipse cx="115" cy="118" rx="28" ry="18" fill="rgba(255,255,255,0.15)"/>
  <ellipse cx="115" cy="118" rx="22" ry="14" fill="url(#goose-grad)" opacity="0.5"/>
</svg>'''

LIBERTY_SVG = '''<svg class="goose-art" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="lib-grad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#aaff00"/><stop offset="100%" stop-color="#00f0ff"/>
  </linearGradient></defs>
  <!-- Crown spikes -->
  <g fill="url(#lib-grad)" opacity="0.9">
  <polygon points="100,8 105,38 95,38"/>
  <polygon points="78,18 86,42 70,40"/>
  <polygon points="122,18 130,40 114,42"/>
  <polygon points="58,32 76,48 56,52"/>
  <polygon points="142,32 144,52 124,48"/>
  </g>
  <!-- Face/head -->
  <ellipse cx="100" cy="62" rx="32" ry="36" fill="url(#lib-grad)" opacity="0.85"/>
  <!-- Eye -->
  <circle cx="92" cy="58" r="3" fill="#0a0a2e"/>
  <circle cx="108" cy="58" r="3" fill="#0a0a2e"/>
  <!-- Torch arm -->
  <path d="M 130 105 L 160 50 L 155 45 Q 170 35 175 50 L 145 110 Z" fill="url(#lib-grad)" opacity="0.8"/>
  <!-- Flame -->
  <path d="M 168 40 Q 174 25 170 12 Q 165 22 162 30 Q 158 20 156 32 Q 155 38 163 48 Z" fill="#ff7b00"/>
  <path d="M 166 38 Q 170 30 168 22 Q 165 28 164 32 Q 162 38 165 44 Z" fill="#ffae00"/>
  <!-- Body/robe -->
  <path d="M 70 100 L 60 180 L 140 180 L 130 100 Z" fill="url(#lib-grad)" opacity="0.7"/>
</svg>'''

TULIP_SVG = '''<svg class="goose-art" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="tulip-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ff2d95"/><stop offset="100%" stop-color="#ff7b00"/>
    </linearGradient>
    <linearGradient id="stem-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#5be8a0"/><stop offset="100%" stop-color="#0a8a4e"/>
    </linearGradient>
  </defs>
  <!-- Stem -->
  <path d="M 98 100 Q 96 150 100 190 L 102 190 Q 104 150 102 100 Z" fill="url(#stem-grad)"/>
  <!-- Leaves -->
  <path d="M 100 130 Q 60 130 50 100 Q 75 115 100 130 Z" fill="url(#stem-grad)" opacity="0.85"/>
  <path d="M 100 145 Q 145 145 155 115 Q 130 130 100 145 Z" fill="url(#stem-grad)" opacity="0.8"/>
  <!-- Petals -->
  <path d="M 80 50 Q 70 30 80 15 Q 95 5 100 25 Q 95 40 88 70 L 80 70 Z" fill="url(#tulip-grad)"/>
  <path d="M 120 50 Q 130 30 120 15 Q 105 5 100 25 Q 105 40 112 70 L 120 70 Z" fill="url(#tulip-grad)"/>
  <path d="M 80 70 Q 80 100 100 105 Q 120 100 120 70 Q 115 80 100 78 Q 85 80 80 70 Z" fill="url(#tulip-grad)" opacity="0.95"/>
  <!-- Highlight -->
  <ellipse cx="92" cy="40" rx="6" ry="14" fill="#ffd6f1" opacity="0.6"/>
</svg>'''

MATH_SVG = '''<svg class="goose-art" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="m-g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#aaff00"/><stop offset="100%" stop-color="#00f0ff"/>
  </linearGradient></defs>
  <circle cx="100" cy="100" r="80" fill="none" stroke="url(#m-g)" stroke-width="2" opacity="0.6"/>
  <circle cx="100" cy="100" r="60" fill="none" stroke="url(#m-g)" stroke-width="1.5" opacity="0.5"/>
  <circle cx="100" cy="100" r="40" fill="none" stroke="url(#m-g)" stroke-width="1" opacity="0.4"/>
  <!-- Sigma -->
  <text x="100" y="125" font-family="Georgia" font-size="80" fill="url(#m-g)" text-anchor="middle" font-style="italic">Σ</text>
  <!-- Floating equations -->
  <text x="40" y="40" font-family="Georgia" font-size="14" fill="#ff8ac4" opacity="0.7">p(s)</text>
  <text x="150" y="60" font-family="Georgia" font-size="14" fill="#7ef9ff" opacity="0.7">≈ b·g·π</text>
  <text x="30" y="170" font-family="Georgia" font-size="14" fill="#ffae00" opacity="0.7">ρ = -0.95</text>
  <text x="135" y="175" font-family="Georgia" font-size="14" fill="#aaff00" opacity="0.7">P̂</text>
</svg>'''


# Psychedelic SVG mandalas — used as "nice pictures" alongside Unsplash photos
def mandala(seed, hue1, hue2, hue3):
    """Generate a unique psychedelic mandala based on seed."""
    import math
    rays = 12 + (seed % 6)
    inner_r = 40 + (seed * 3 % 30)
    paths = []
    for i in range(rays):
        a = i * 360 / rays
        x1 = 100 + inner_r * math.cos(math.radians(a))
        y1 = 100 + inner_r * math.sin(math.radians(a))
        x2 = 100 + 95 * math.cos(math.radians(a + 360 / rays / 2))
        y2 = 100 + 95 * math.sin(math.radians(a + 360 / rays / 2))
        x3 = 100 + 95 * math.cos(math.radians(a - 360 / rays / 2))
        y3 = 100 + 95 * math.sin(math.radians(a - 360 / rays / 2))
        paths.append(f'<path d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f} L{x3:.1f} {y3:.1f} Z" fill="url(#mg{seed})" opacity="0.65"/>')
    return f'''<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">
  <defs>
    <linearGradient id="mg{seed}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{hue1}"/>
      <stop offset="50%" stop-color="{hue2}"/>
      <stop offset="100%" stop-color="{hue3}"/>
    </linearGradient>
    <radialGradient id="mc{seed}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{hue2}" stop-opacity="0.9"/>
      <stop offset="80%" stop-color="{hue1}" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="{hue3}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="200" height="200" fill="#0a0a2e"/>
  <circle cx="100" cy="100" r="100" fill="url(#mc{seed})"/>
  {''.join(paths)}
  <circle cx="100" cy="100" r="{inner_r-5}" fill="{hue3}" opacity="0.45"/>
  <circle cx="100" cy="100" r="{inner_r-15}" fill="{hue1}" opacity="0.6"/>
  <circle cx="100" cy="100" r="6" fill="#fff"/>
</svg>'''


# Curated Unsplash photo URLs (small, fast-loading). Each works as an HTTP fetch.
PHOTOS_AMS = [
    "https://images.unsplash.com/photo-1534351450181-ea9f78427fe8?w=600&q=70&auto=format",  # Amsterdam canal
    "https://images.unsplash.com/photo-1576924542622-772abdd06ee2?w=600&q=70&auto=format",  # Amsterdam houses
    "https://images.unsplash.com/photo-1612521564730-62e533aff7ba?w=600&q=70&auto=format",  # tulip field
]
PHOTOS_MSG = [
    "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=600&q=70&auto=format",  # NYC skyline
    "https://images.unsplash.com/photo-1518391846015-55a9cc003b25?w=600&q=70&auto=format",  # NYC at night
    "https://images.unsplash.com/photo-1485871981521-5b1fd3805eee?w=600&q=70&auto=format",  # Empire State / lights
]
PHOTOS_HOME = [
    "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=600&q=70&auto=format",  # concert lights
    "https://images.unsplash.com/photo-1429962714451-bb934ecdc4ec?w=600&q=70&auto=format",  # crowd silhouette
    "https://images.unsplash.com/photo-1574391884720-bbc049ec09ad?w=600&q=70&auto=format",  # psychedelic neon
]


def image_strip(photos, mandala_seeds, hues):
    """Build a 3-column image strip mixing photos and mandalas."""
    items = []
    for i in range(3):
        photo = photos[i] if i < len(photos) else ""
        seed, h1, h2, h3 = mandala_seeds[i], *hues[i]
        # Photo background + mandala SVG overlay (multiply blend)
        mand = mandala(seed, h1, h2, h3)
        items.append(f'''<div style="position:relative;aspect-ratio:1/1;background-size:cover;background-position:center;background-image:url('{photo}'),linear-gradient(135deg,{h1},{h3});filter:saturate(1.4) contrast(1.05);border-radius:14px;overflow:hidden">
          <div style="position:absolute;inset:0;mix-blend-mode:overlay;opacity:0.7">{mand}</div>
          <div style="position:absolute;inset:0;background:radial-gradient(circle at 30% 70%,rgba(255,45,149,.3),transparent 60%),linear-gradient(180deg,transparent 40%,rgba(7,7,31,.7));pointer-events:none"></div>
        </div>''')
    return f'<div class="imgstrip">{"".join(items)}</div>'

# Goose-y header art swapper
def show_art(show_id):
    if show_id.startswith("ams"):
        return TULIP_SVG
    if show_id.startswith("msg"):
        return LIBERTY_SVG
    return GOOSE_SVG


# ─────────────────────────────────────────────────────────── HTML construction
def tier(p):
    if p >= 40: return "blaze"
    if p >= 25: return "hot"
    if p >= 15: return "warm"
    return "cool"


def song_row_html(song, n):
    p = song["pct"]
    return f'''    <li class="song {tier(p)}" style="--p:{p};--i:{n}">
      <span class="rank">{song["rank"]}</span>
      <div class="body">
        <div class="meta"><span class="name">{html.escape(song["name"])}</span><span class="pct">{p}%</span></div>
        <div class="track"><span class="fill"></span></div>
        <p class="why">{html.escape(song["rationale"])}</p>
      </div>
    </li>'''


def wild_row_html(label, p, why, n=0):
    return f'''    <li class="song wild {tier(p)}" style="--p:{p};--i:{n}">
      <span class="rank">✨</span>
      <div class="body">
        <div class="meta"><span class="name">{html.escape(label)}</span><span class="pct">{p}%</span></div>
        <div class="track"><span class="fill"></span></div>
        <p class="why">{html.escape(why)}</p>
      </div>
    </li>'''


def head(title):
    return f'''  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} – GooseGuesses</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Monoton&family=Poppins:wght@300;400;500;600;700&family=Righteous&display=swap" rel="stylesheet">
  <style>
{SHARED_CSS}
  </style>'''


NAV_TEMPLATE = '''<nav>
      <a href="index.html"%s>🏠 Home</a>
      <a href="amsterdam.html"%s>🇳🇱 Amsterdam</a>
      <a href="msg_n1.html"%s>🗽 MSG N1</a>
      <a href="msg_n2.html"%s>🗽 MSG N2</a>
      <a href="model.html"%s>🧮 Model</a>
      <a href="methodology.html"%s>📜 Math</a>
    </nav>'''


def nav(active):
    cls = lambda key: ' class="active"' if key == active else ""
    return NAV_TEMPLATE % (
        cls("home"),
        cls("ams"),
        cls("msg1"),
        cls("msg2"),
        cls("model"),
        cls("meth"),
    )


def assumption_box(show, predictions):
    """Fan-friendly explanation: what data we used and how we crunched it."""
    e = predictions["empirical"]
    listed = show["listed_total_songs"]
    target = show["expected_length"]
    is_euro = show["tier"] == "european_first_time"
    is_n2 = show.get("conditioning_on")
    n_2026 = stats["rotation"]["n_2026_shows"]

    items = [
        f'<li><b>We pulled every Goose setlist back to 2018</b> — {predictions["n_shows_in_data"]} shows, {stats["n_total_songs"]} unique songs — from <a href="https://elgoose.net/" style="color:#7ef9ff">El Goose</a> (the band\'s setlist archive). The {n_2026} shows from 2026 carry more weight than older data because the rotation has changed since <em>Everything Must Go</em> and <em>Chain Yer Dragon</em>.</li>',
        f'<li><b>Each song\'s starting point is "how often does it show up?"</b> — counted across the 2026 tour and the last 50 shows combined. Heaviest rotators (Give It Time, Animal, Hungersite) hit ~30% of recent shows. That\'s the per-song baseline.</li>',
    ]

    if is_euro:
        items.append(
            f'<li><b>The "Tour Variety Engine" cuts in hard.</b> Goose rotates — the empirical cross-venue 5-day overlap rate is just 9.6% (n=61). So songs played at <b>London 5/22</b> (Animal, Your Direction, So Ready, Big Modern!, Creatures, Turn On Your Love Light, etc.) get a steep down-weight for Amsterdam. They <em>just</em> played them.</li>'
        )
    else:
        items.append(
            f'<li><b>MSG is the big stage.</b> We bumped up odds for "set-2 launch pad" jams (Hungersite, Thatch, Madhuvan), encore staples (Arcadia, Empress of Organos), and reserved real probability for a cover, a deep-catalog bustout, and Stuart Bogie\'s horns (they showed up at MSG 2025 — bet on a return).</li>'
        )

    if is_n2:
        items.append(
            f'<li><b>Goose almost never repeats songs across back-to-back nights.</b> We measured this from {predictions["empirical"]["two_night_n_pairs"]} historical 2-night pairs since 2018 — only <b>{predictions["empirical"]["two_night_repeat_rate"]*100:.2f}%</b> of N1 songs come back on N2. So Night 2 picks fade hard for anything we expect on Night 1.</li>'
        )

    if "msg" in show["id"]:
        items.append(
            f'<li><b>BIG MODERN! drops June 12 — seven days before MSG N1.</b> Songs already debuted from the album (Good2B, MEDIA, Torero, SALT) get a release-week boost (calibrated against <em>Everything Must Go</em>\'s 4.4× lift). Real shot at a live debut of one of the unplayed album tracks too (Scavenger, POP, Good Times // End Times, fast:slow).</li>'
        )
    else:
        items.append(
            f'<li><b>New rotation songs get a bump</b> — Good2B is the main one for 2026. <em>Cortez The Killer</em> and <em>Hey Joe</em> were one-offs at Viva El Gonzo with Jim James and Cory Wong sitting in — they\'re NOT in standalone rotation, so we explicitly suppress them.</li>'
        )

    items.append(
        f'<li><b>The percentages sum to the show\'s length.</b> A {"single set" if is_euro else "two sets + encore"} show is ~{target} slots total — and the probabilities you see all together describe how that {target}-song pie gets sliced. No song can clear {"40%" if is_euro else "50%"} because Goose\'s catalog is too deep for any one song to be a true "lock".</li>'
    )

    body = "\n        ".join(items)

    return f'''    <section class="assume">
      <h3><span class="icon">📐</span>How we got these numbers <span style="color:var(--muted);font-size:.85rem;font-weight:300;margin-left:auto">(plain English)</span></h3>
      <ol>
        {body}
      </ol>
      <div class="cov"><strong>One thing to remember:</strong> the deep catalog matters. Even the #1 pick sits well under 50% because ~60% of every Goose show\'s slots come from outside the top two dozen rotators. <b>Treat these as relative odds — ranking matters more than the exact %.</b> For the full math, see the <a href="methodology.html" style="color:#aaff00">Methodology page</a>.</div>
    </section>'''


def wildcards_block(show, predictions):
    """Cover / bustout / debut wildcards."""
    e = predictions["empirical"]
    is_euro = show["tier"] == "european_first_time"

    rows = []

    # Cover
    if is_euro:
        p_cov = int(round(100 * show["p_cover"] * 0.55))
        rows.append(
            wild_row_html(
                "A non-Goose cover",
                p_cov,
                f"{int(100*e['cover_show_rate_last_50'])}% of recent shows feature a cover · European single-set fits one less often",
                len(rows),
            )
        )
    else:
        p_cov_run = int(round(100 * (1 - (1 - show["p_cover"]) ** 2.2)))
        rows.append(
            wild_row_html(
                "≥ 1 cover this night",
                int(round(100 * show["p_cover"])),
                f"{int(100*e['cover_show_rate_last_50'])}% of recent shows feature a cover; MSG marquee tier multiplies that",
                len(rows),
            )
        )

    # Bustouts
    bo_names = " / ".join(b["name"] for b in show["bustouts"][:3])
    bo_pct = int(round(100 * show["p_bustout"]))
    rows.append(
        wild_row_html(
            f"Big bustout: {bo_names}",
            min(bo_pct, 45),
            f"Career staples on long gaps · MSG marquee multiplies bustout odds 1.8×" if not is_euro else "European safety dampens bustout odds 0.6×",
            len(rows),
        )
    )

    # Debut
    p_debut = int(round(100 * show["p_debut_per_slot"] * show["expected_length"]))
    rows.append(
        wild_row_html(
            "A song debut / tour premiere",
            min(p_debut, 60),
            "BIG MODERN! drops June 12 — unplayed album tracks have high MSG debut odds" if "msg" in show["id"] else "Lower in single-set Euro market, but possible",
            len(rows),
        )
    )

    return "\n".join(rows)


def show_page(show_id, active_nav, art_svg):
    """Render a single show prediction page."""
    show = predictions["shows"][show_id]
    title = show["name"]
    fmt_label = (
        "Two sets + encore · ~18 songs/night" if show["format"] == "two_set_encore"
        else "Single set · ~11 songs · European leg"
    )

    is_n2 = show.get("conditioning_on")
    n2_note = ""
    if is_n2:
        excluded = show.get("n1_predicted_plays") or []
        excl_html = "<br>".join(
            ", ".join(html.escape(s) for s in excluded[i:i+8])
            for i in range(0, len(excluded), 8)
        )
        n2_note = f'''
      <div class="note"><b>Bayesian conditioning.</b> Empirical 2-night same-venue repeat rate is <b>{predictions["empirical"]["two_night_repeat_rate"]*100:.2f}%</b> (n={predictions["empirical"]["two_night_n_pairs"]} pairs since 2018). Songs predicted for Night 1 are down-weighted by ρ = -0.95 — their probability becomes ~5% of base. Excluded N1 candidates:<br><span style="color:var(--muted);font-size:.85rem">{excl_html}</span></div>'''

    songs_html = "\n".join(song_row_html(s, i) for i, s in enumerate(show["songs"][:30]))
    wildcards_html = wildcards_block(show, predictions)
    assume_html = assumption_box(show, predictions)

    # Show-specific image strip
    if show_id.startswith("ams"):
        photos = PHOTOS_AMS
        hues = [("#00f0ff", "#b14aed", "#ff2d95"), ("#aaff00", "#00f0ff", "#3a7bff"), ("#ff7b00", "#ff2d95", "#b14aed")]
    else:
        photos = PHOTOS_MSG
        hues = [("#ff2d95", "#ffae00", "#b14aed"), ("#aaff00", "#00f0ff", "#ff2d95"), ("#ff7b00", "#b14aed", "#00f0ff")]
    strip = image_strip(photos, [3, 7, 11], hues)

    body = f'''
{assume_html}
    {strip}
    <div class="note"><b>Format:</b> {fmt_label}. <b>Venue tier:</b> {show["tier"].replace("_", " ")} (V={show["venue_V"]}). These probabilities are <em>per-night</em> marginal estimates from the model.</div>
{n2_note}
    <div class="seclabel">🎯 Most likely songs (per-night odds)</div>
    <ol class="list">
{songs_html}
    </ol>
    <div class="seclabel">✨ Wildcards &amp; near-locks</div>
    <ul class="list">
{wildcards_html}
    </ul>'''

    return PAGE_TPL.format(
        head=head(title),
        grain=GRAIN,
        nav=nav(active_nav),
        art=art_svg,
        kicker="GooseGuesses · Setlist Oracle",
        h1=html.escape(title),
        venue=html.escape(show["venue"]),
        dates=html.escape(show["date"]),
        format=html.escape(fmt_label),
        body=body,
    )


PAGE_TPL = '''<!DOCTYPE html>
<html lang="en"><head>
{head}
</head>
<body>
{grain}
<div class="wrap">
  <header class="hero">
    <div class="halo"></div><div class="halo two"></div>
    {art}
    <div class="kicker">{kicker}</div>
    <h1>{h1}</h1>
    <div class="venue">{venue}</div>
    <div class="dates">{dates}</div>
    <div class="format">{format}</div>
  </header>
  {nav}
{body}
  <footer><p>Probabilities are model estimates derived from setlist history — read them as <em>relative odds</em>.<br>
    Source: <a href="https://elgoose.net/setlists/goose/">El Goose</a> database (550 shows, 2018–2026) · current through London 5/22/26.<br>
    Methodology: <a href="methodology.html">GooseGuesses v1.0</a>. Art is generated CSS + SVG — no goose was photographed. 🪿</p></footer>
</div>
</body></html>'''


def amsterdam_page():
    """Two-up Amsterdam page (N1 + N2 side by side)."""
    n1 = predictions["shows"]["ams_n1"]
    n2 = predictions["shows"]["ams_n2"]

    def column(show, label):
        rows = "\n".join(song_row_html(s, i) for i, s in enumerate(show["songs"][:22]))
        wilds = wildcards_block(show, predictions)
        cond_note = ""
        if show.get("conditioning_on"):
            cond_note = f'<div class="note" style="margin-top:8px"><b>Conditioned on N1.</b> Songs that almost certainly played 5/27 are down-weighted by ρ = -0.95.</div>'
        return f'''
      <div>
        <div class="seclabel">{label}</div>
{cond_note}
        <ol class="list">
{rows}
        </ol>
        <div class="seclabel">✨ Wildcards</div>
        <ul class="list">
{wilds}
        </ul>
      </div>'''

    strip = image_strip(
        PHOTOS_AMS,
        [3, 7, 11],
        [("#00f0ff", "#b14aed", "#ff2d95"), ("#aaff00", "#00f0ff", "#3a7bff"), ("#ff7b00", "#ff2d95", "#b14aed")],
    )
    body = f'''
{assumption_box(n1, predictions)}
    {strip}
    <div class="note"><b>Format:</b> Single set · ~11 songs · European leg debut at Melkweg. The two nights won't repeat each other (empirical 2-night repeat rate {predictions["empirical"]["two_night_repeat_rate"]*100:.2f}%) — N2 is the Bayesian-conditioned posterior given N1 plays.</div>
    <div class="twocol">
{column(n1, "🌙 Night 1 — May 27")}
{column(n2, "🌙 Night 2 — May 28")}
    </div>'''

    return PAGE_TPL.format(
        head=head("Amsterdam — Melkweg"),
        grain=GRAIN,
        nav=nav("ams"),
        art=TULIP_SVG,
        kicker="GooseGuesses · Setlist Oracle",
        h1="Amsterdam",
        venue="Melkweg · Amsterdam, NL",
        dates="May 27 &amp; 28, 2026",
        format="Two-night run · single set each · European leg",
        body=body,
    )


def index_page():
    e = predictions["empirical"]
    cards = '''<div class="cards">
      <a class="card ams" href="amsterdam.html">
        <div class="cgoose">🪿</div>
        <h2>Amsterdam</h2>
        <div class="csub">Melkweg · May 27 &amp; 28</div>
        <div class="csub">Two single-set nights · European leg debut</div>
        <div class="cgo">See predictions →</div>
      </a>
      <a class="card msg" href="msg_n1.html">
        <div class="cgoose">🗽</div>
        <h2>MSG Night 1</h2>
        <div class="csub">Madison Square Garden · June 19</div>
        <div class="csub">Two sets + encore · ~18 songs</div>
        <div class="cgo">See predictions →</div>
      </a>
      <a class="card msg" href="msg_n2.html">
        <div class="cgoose">🗽</div>
        <h2>MSG Night 2</h2>
        <div class="csub">Madison Square Garden · June 20</div>
        <div class="csub">Bayesian-conditioned on N1</div>
        <div class="cgo">See predictions →</div>
      </a>
      <a class="card math" href="model.html">
        <div class="cgoose">🧮</div>
        <h2>The Model</h2>
        <div class="csub">Tune the parameters · live forecast</div>
        <div class="csub">Honk Factor, Madhuvan Multiplier, Bustout Boldness</div>
        <div class="cgo">Open the Goose Oracle →</div>
      </a>
      <a class="card meth" href="methodology.html">
        <div class="cgoose">📜</div>
        <h2>Methodology</h2>
        <div class="csub">Full math · references · validation</div>
        <div class="csub">Bayesian conditioning, slot identity, gap multiplier</div>
        <div class="cgo">Read the proofs →</div>
      </a>
    </div>'''

    stat_grid = f'''<div class="statgrid">
      <div class="stat"><div class="num">{predictions["n_shows_in_data"]}</div><div class="lbl">Goose shows analyzed (since 2018)</div></div>
      <div class="stat"><div class="num">{stats["n_total_songs"]}</div><div class="lbl">Unique songs in the catalog</div></div>
      <div class="stat"><div class="num">{e["avg_songs_last_50"]:.1f}</div><div class="lbl">Avg songs / show (last 50)</div></div>
      <div class="stat"><div class="num">{e["two_night_repeat_rate"]*100:.2f}%</div><div class="lbl">2-night same-venue repeat rate</div></div>
      <div class="stat"><div class="num">{e["cover_show_rate_last_50"]*100:.0f}%</div><div class="lbl">Shows w/ ≥1 cover</div></div>
      <div class="stat"><div class="num">~30%</div><div class="lbl">Top rotator (Give It Time)</div></div>
    </div>'''

    intro = f'''<section class="assume">
      <h3><span class="icon">🪿</span>What this is</h3>
      <ol>
        <li><strong>GooseGuesses</strong> is a probabilistic setlist prediction system for Goose's Amsterdam Melkweg (5/27-28) and Madison Square Garden (6/19-20) shows in 2026.</li>
        <li>It is built on <strong>{predictions["n_shows_in_data"]} shows of historical data</strong> from El Goose (2018-2026), a methodology adapted from Phish.net's Trey's Notebook + Andrew Reed's LSTM, and a multiplicative factor model that's renormalized to satisfy the show-length slot identity.</li>
        <li><strong>Numbers are relative odds, not point forecasts.</strong> Goose rotates a deep catalog — the heaviest rotators appear in only ~30% of shows — so ranking matters far more than the precise %.</li>
        <li>The <a href="model.html"><strong>Model page</strong></a> lets you tune every parameter (Honk Factor, Madhuvan Multiplier, Bustout Boldness, etc.) and watch the predictions update live.</li>
      </ol>
    </section>'''

    strip = image_strip(
        PHOTOS_HOME,
        [2, 9, 14],
        [("#ff2d95", "#ffae00", "#b14aed"), ("#aaff00", "#00f0ff", "#3a7bff"), ("#b14aed", "#ff2d95", "#00f0ff")],
    )
    body = intro + strip + cards + stat_grid

    return PAGE_TPL.format(
        head=head("GooseGuesses"),
        grain=GRAIN,
        nav=nav("home"),
        art=GOOSE_SVG,
        kicker="Setlist Oracle · Spring/Summer 2026",
        h1="GooseGuesses",
        venue="Probabilistic setlist predictions",
        dates="May 27, 28 (Amsterdam) · June 19, 20 (MSG)",
        format="550 shows · 323 songs · 20 tunable parameters",
        body=body,
    )


# Write the static show pages
def main():
    pages = {
        "index.html": index_page(),
        "amsterdam.html": amsterdam_page(),
        "msg_n1.html": show_page("msg_n1", "msg1", LIBERTY_SVG),
        "msg_n2.html": show_page("msg_n2", "msg2", LIBERTY_SVG),
    }
    for fn, content in pages.items():
        out = ROOT / fn
        out.write_text(content, encoding="utf-8")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
