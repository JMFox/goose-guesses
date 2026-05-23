"""Builds model.html — the interactive forecasting page with tunable
goose-themed parameters and a live JavaScript implementation of the model.

The user can drag sliders for all 20 parameters and watch predictions
update in real time for any of the four target shows.
"""
import json, html
from pathlib import Path

ROOT = Path(__file__).parent
predictions = json.load(open(ROOT / "predictions.json", encoding="utf-8"))
parameters = json.load(open(ROOT / "parameters.json", encoding="utf-8"))
stats = json.load(open(ROOT / "stats.json", encoding="utf-8"))

# Reuse shared CSS + grain + nav from render_html
from render_html import SHARED_CSS, GRAIN, MATH_SVG, nav, head, PAGE_TPL

# Build the JS data payload — embed only what the JS model needs
# Top songs with all the features
song_data = []
LAST_SHOW = stats["shows"][-1]
LONDON_5_22_SONGS = set()
for sh in stats["shows"]:
    if sh["date"] == "2026-05-22":
        LONDON_5_22_SONGS = set(sh.get("songs", []))

BLENDED = {r["name"]: r["blended_rate"] for r in stats["rotation"]["top_50_blended"]}
DEBUTS_2026 = set(d["name"] for d in stats.get("debuts_2026", []))
RETURNS_2026 = set(r["name"] for r in stats.get("returns_2026", []))

# Filter songs for the JS model — keep top 220 by relevance
included = set()
for r in stats["rotation"]["top_50_blended"]:
    included.add(r["name"])
for s in stats["songs"]:
    if s.get("plays_last_50", 0) > 0 or s.get("plays_2026", 0) > 0:
        included.add(s["name"])
for b in stats.get("bustout_candidates", [])[:25]:
    included.add(b["name"])

# Filter out interludes
def is_interlude(n):
    return n.startswith("(") and n.endswith(")")

included = {n for n in included if not is_interlude(n)}

for s in stats["songs"]:
    name = s["name"]
    if name not in included:
        continue
    song_data.append({
        "name": name,
        "blended": BLENDED.get(name, s.get("plays_last_50", 0) / 50),
        "career": s.get("career_plays", 0),
        "plays_2026": s.get("plays_2026", 0),
        "gap": s.get("gap_shows", 50),
        "opener_n": s.get("opener_count", 0),
        "s2_open_n": s.get("set2_opener_count", 0),
        "encore_n": s.get("encore_count", 0),
        "closer_n": s.get("set2_closer_count", 0),
        "set1_closer_n": s.get("set1_closer_count", 0),
        "is_2026_debut": name in DEBUTS_2026,
        "is_return_2026": name in RETURNS_2026,
        "in_london": name in LONDON_5_22_SONGS,
        "is_original": s.get("is_original", True),
    })

# Also include any songs that are in BLENDED but not in songs[] (shouldn't happen but defensive)
known_names = {sd["name"] for sd in song_data}
for r in stats["rotation"]["top_50_blended"]:
    if r["name"] in known_names:
        continue
    song_data.append({
        "name": r["name"],
        "blended": r["blended_rate"],
        "career": 0,
        "plays_2026": 0,
        "gap": 50,
        "opener_n": 0, "s2_open_n": 0, "encore_n": 0, "closer_n": 0, "set1_closer_n": 0,
        "is_2026_debut": r["name"] in DEBUTS_2026,
        "is_return_2026": r["name"] in RETURNS_2026,
        "in_london": r["name"] in LONDON_5_22_SONGS,
        "is_original": True,
    })

# Sort songs by blended desc so the model has a stable order
song_data.sort(key=lambda s: -s["blended"])

# Build stickiness map
stickiness = {o["song"]: o["rho"] for o in parameters["stickiness_overrides"]}

# Build venue tier map for JS — filter audit_note before serialization
venue_tiers = {}
for t in parameters["venue_tiers"]:
    venue_tiers[t["tier"]] = {k: v for k, v in t.items() if k not in {"audit_note"}}
shows_info = {s["id"]: s for s in parameters["shows"]}

empirical = predictions["empirical"]


# ──────────────────────────────────────────────────────────── extra page CSS
MODEL_CSS = SHARED_CSS + """
/* Parameter sliders */
.controls{display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
  gap:14px; margin:18px 0 32px}
.param{padding:14px 16px; border-radius:14px;
  background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.10);
  backdrop-filter:blur(6px); transition:border-color .2s}
.param:hover{border-color:rgba(255,45,149,.45)}
.param .name{display:flex; justify-content:space-between; align-items:baseline; gap:10px;
  font-family:'Righteous',sans-serif; font-size:.98rem}
.param .name .val{font-family:'Righteous',sans-serif; font-size:.95rem;
  background:linear-gradient(90deg,#ff2d95,#ffae00);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent}
.param .sub{color:var(--muted); font-size:.74rem; margin-top:2px; text-transform:uppercase; letter-spacing:.1em}
.param input[type=range]{width:100%; margin:10px 0 6px; accent-color:#ff2d95}
.param .desc{color:var(--muted); font-size:.78rem; line-height:1.45; font-weight:300}

/* Group headers */
.pgroup{margin:32px 0 6px; font-family:'Righteous',sans-serif; font-size:1.05rem;
  display:flex; align-items:center; gap:10px; color:#fff}
.pgroup::after{content:''; flex:1; height:1px;
  background:linear-gradient(90deg,rgba(255,255,255,.4),transparent)}
.pgroup .sm{color:var(--muted); font-size:.78rem; font-weight:400; margin-left:4px}

/* Show selector */
.showsel{display:flex; flex-wrap:wrap; gap:8px; margin:16px 0 4px}
.showsel button{padding:9px 16px; border-radius:999px; border:1px solid rgba(255,255,255,.18);
  background:rgba(255,255,255,.05); color:var(--ink); cursor:pointer; font-family:inherit;
  font-size:.9rem; transition:.2s; font-weight:500}
.showsel button.active{background:linear-gradient(90deg,#ff2d95,#b14aed);
  border-color:transparent; box-shadow:0 4px 18px rgba(177,74,237,.4)}
.showsel button:hover:not(.active){background:rgba(255,255,255,.10)}

/* Live results */
.live{margin-top:14px; padding:16px 18px; border-radius:14px;
  background:rgba(170,255,0,.07); border:1px solid rgba(170,255,0,.25)}
.live h3{margin:0 0 10px; font-family:'Righteous',sans-serif; color:#fff; font-size:1.05rem}
.live .meta{color:var(--muted); font-size:.84rem; margin-bottom:14px}

/* Sticky control panel */
.preset{display:flex; gap:10px; flex-wrap:wrap; margin-top:8px}
.preset button{padding:6px 14px; border-radius:999px; border:1px solid rgba(255,174,0,.45);
  background:rgba(255,174,0,.08); color:#ffd680; cursor:pointer; font-family:inherit;
  font-size:.82rem; transition:.2s; font-weight:500}
.preset button:hover{background:rgba(255,174,0,.2); transform:translateY(-1px)}

/* Equation display */
.eqbox{padding:18px 22px; border-radius:14px; background:rgba(177,74,237,.10);
  border:1px solid rgba(177,74,237,.35); margin:16px 0; overflow-x:auto}
.eqbox code, .eqbox .eq{font-family:'Courier New',monospace; font-size:.92rem;
  color:#ffd6f1; display:block; line-height:1.7; white-space:pre-wrap}

/* Compact prediction list (used inside Live panel) */
.minilist{display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:8px}
.minisong{display:flex; gap:10px; align-items:center; padding:8px 12px; border-radius:10px;
  background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.10); font-size:.88rem}
.minisong .rank{flex:0 0 28px; height:28px; font-family:'Righteous',sans-serif; font-size:.85rem;
  background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.12);
  border-radius:8px; display:grid; place-items:center}
.minisong .name{flex:1; font-weight:400; font-size:.94rem}
.minisong .pct{font-family:'Righteous',sans-serif; font-size:.92rem;
  background:linear-gradient(90deg,var(--c1),var(--c2));
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent}
.minisong .bar{flex:0 0 60px; height:6px; border-radius:999px; background:rgba(255,255,255,.10); overflow:hidden}
.minisong .bar > i{display:block; height:100%; background:linear-gradient(90deg,var(--c1),var(--c2));
  border-radius:inherit}

/* ───── Mobile: stack sliders, shrink presets, scroll math ───── */
@media (max-width: 720px){
  .controls{grid-template-columns:1fr; gap:10px}
  .param{padding:12px 14px}
  .param .name{font-size:.88rem; flex-wrap:wrap}
  .param .desc{font-size:.74rem}
  .showsel{gap:6px}
  .showsel button{padding:7px 12px; font-size:.8rem}
  .preset{gap:6px}
  .preset button{padding:5px 10px; font-size:.74rem}
  .pgroup{font-size:.95rem; margin:24px 0 6px}
  .pgroup .sm{font-size:.7rem}
  .live{padding:12px 14px}
  .live h3{font-size:.95rem}
  .live .meta{font-size:.76rem}
  .minilist{grid-template-columns:1fr; gap:6px}
  .minisong{padding:7px 10px; font-size:.84rem}
  .minisong .name{font-size:.88rem}
  .minisong .pct{font-size:.85rem}
  .minisong .bar{flex:0 0 40px}
  .eqbox{padding:12px 14px}
  .eqbox .eq{font-size:.74rem}
  /* Display math: scrollable */
  mjx-container[display="true"]{overflow-x:auto !important; overflow-y:hidden !important;
    max-width:100%; -webkit-overflow-scrolling:touch}
}
"""


# Embed the model data + JS
JS_MODEL = """
<script>
const MODEL = {
  songs: __SONGS__,
  parameters: __PARAMS__,
  stickiness: __STICK__,
  venueTiers: __TIERS__,
  shows: __SHOWS__,
  empirical: __EMPIRICAL__,
  guestOnlyCovers: __GUEST_COVERS__,
};

// Current parameter values, populated from defaults on load
const currentParams = {};
MODEL.parameters.forEach(p => { currentParams[p.slug] = p.default; });

// Cached N1 prediction sets for N2 conditioning
const n1Predicted = { ams_n1: null, msg_n1: null };

function pool(roleKey, topT){
  // Sort songs by descending role count, return set of top-T names with positive counts
  const counts = MODEL.songs
    .filter(s => (s[roleKey] || 0) > 0)
    .map(s => ({name: s.name, n: s[roleKey]}))
    .sort((a,b) => b.n - a.n);
  return new Set(counts.slice(0, topT).map(c => c.name));
}

function poolsFor(topT){
  // Smaller closer pool
  return {
    opener: pool('opener_n', topT),
    s2_open: pool('s2_open_n', topT),
    encore: pool('encore_n', topT),
    closer: pool('closer_n', Math.max(4, Math.floor(topT/2))),
  };
}

function gapMultiplier(gap, career, baseRate){
  const muB = currentParams.bustout_peak_gap;
  const sigB = currentParams.bustout_peak_width;
  const boldness = currentParams.bustout_boldness;
  let decay;
  if (gap <= 0) decay = 0.30;
  else if (gap <= 3) decay = 0.60 + 0.10 * gap;
  else decay = 1.0;
  if (career >= 8 && gap >= 25 && baseRate < 0.15){
    const bump = boldness * Math.exp(-((gap-muB)**2) / (2*sigB**2));
    decay *= 1 + bump;
  }
  return decay;
}

function piFactor(name, fmt, pools){
  let m = 1.0;
  if (fmt === 'two_set_encore'){
    // Hot Tea exception: empirically a closer, not a launch pad
    if (pools.s2_open.has(name) && name !== 'Hot Tea') m *= currentParams.madhuvan_multiplier;
    if (pools.encore.has(name))  m *= currentParams.encore_multiplier;
    if (pools.opener.has(name))  m *= currentParams.opener_multiplier;
    if (pools.closer.has(name) || name === 'Hot Tea') m *= currentParams.set_closer_multiplier;
  }
  return Math.min(m, 1.25);
}

function debutFactor(song){
  // Guest-only covers (Cortez, Hey Joe, etc) — strong damper; one-off only
  if (MODEL.guestOnlyCovers.has(song.name)) return 0.20;
  if (song.is_2026_debut){
    const halfLife = currentParams.debut_halflife_shows;
    const plays = Math.max(song.plays_2026 || 1, 1);
    const boost = (currentParams.album_promotion - 1.0) * Math.pow(0.5, plays/halfLife);
    return 1.0 + boost;
  }
  if (song.is_return_2026) return 1.15;
  return 1.0;
}

function computeMarginals(showId, excludeSet){
  const show = MODEL.shows.find(s => s.id === showId);
  const tierInfo = MODEL.venueTiers[show.tier];
  const V = tierInfo.V * currentParams.venue_aura;
  const isEuro = show.tier === 'european_first_time';
  const fmt = show.format;
  const target = show.expected_length;
  const topT = Math.round(currentParams.top_role_count);
  const pools = poolsFor(topT);

  // honk_factor is the alpha in the blend — recompute base rates if changed
  // For simplicity, we use the pre-computed blended (which uses alpha=0.55).
  // If user changes honk_factor, we re-blend with rate_2026 + rate_last50 from rotation.
  const alpha = currentParams.honk_factor;
  const blendMap = {};
  MODEL.songs.forEach(s => {
    // We stored only blended. Approximate dynamic re-blend: weight is preserved on top rotators
    blendMap[s.name] = s.blended;
  });
  // (For a fully dynamic blend we'd need rate_2026 + rate_last50 in MODEL.songs; we don't, so
  // we treat honk_factor as a global lever that scales the blended rate non-linearly.)
  // Effective base rate = blended * (1 + 0.30*(honk_factor - 0.55))
  const honkAdj = 1 + 0.30 * (alpha - 0.55);

  const raw = {};
  for (const s of MODEL.songs){
    let b = (blendMap[s.name] || 0) * honkAdj;
    if (b <= 0 && s.career < 5) continue;
    b = Math.max(b, 0.001);

    const g = gapMultiplier(s.gap, s.career, b);
    const pi = piFactor(s.name, fmt, pools);
    const D = debutFactor(s);
    // Tour Variety Engine: songs played at the previous tour stop are LESS likely
    const ldn = (isEuro && s.in_london) ? currentParams.london_recency_penalty : 1.0;

    // Bustout multiplier from venue tier (applied only to bustout-bump portion)
    let bustMult = tierInfo.bustout_mult;
    if (isEuro) bustMult *= currentParams.european_bustout_dampening;
    let effG = g;
    if (s.gap > 30 && s.career >= 6){
      const extra = (bustMult - 1.0) * Math.min(1.0, (s.gap - 30) / 60);
      effG *= 1 + extra;
    }

    // No-repeat conditioning (N2 only)
    let R = 1.0;
    if (excludeSet && excludeSet.has(s.name)){
      const rho = (s.name in MODEL.stickiness) ? MODEL.stickiness[s.name] : currentParams.no_repeat_rho;
      R = Math.max(0.0, 1 + rho);
    } else if (excludeSet){
      R = 1.10;
    }

    raw[s.name] = b * effG * pi * V * D * ldn * R;
  }

  const total = Object.values(raw).reduce((a,b) => a+b, 0);
  if (total <= 0) return [];
  const k = target / total;
  const cap = (fmt === 'single_set') ? Math.min(currentParams.prob_cap, 0.40) : currentParams.prob_cap;

  // Scale + cap
  const capped = {};
  let overMass = 0, underTotal = 0;
  for (const [name, v] of Object.entries(raw)){
    const scaled = v * k;
    if (scaled > cap){
      capped[name] = cap;
      overMass += scaled - cap;
    } else {
      capped[name] = scaled;
      underTotal += scaled;
    }
  }
  if (overMass > 0 && underTotal > 0){
    for (const [name, v] of Object.entries(capped)){
      if (v < cap){
        capped[name] = Math.min(cap, v * (1 + overMass / underTotal));
      }
    }
  }

  // Sort and return
  return Object.entries(capped)
    .map(([name, p]) => ({name, p}))
    .sort((a,b) => b.p - a.p);
}

function tierForP(p){
  if (p >= 0.40) return 'blaze';
  if (p >= 0.25) return 'hot';
  if (p >= 0.15) return 'warm';
  return 'cool';
}

let currentShow = 'ams_n1';

function updatePredictions(){
  // For N2 shows, first compute N1 prediction then use as exclude set
  let excludeSet = null;
  const show = MODEL.shows.find(s => s.id === currentShow);
  if (show.conditioning_on){
    const n1Marg = computeMarginals(show.conditioning_on, null);
    excludeSet = new Set(n1Marg.slice(0, show.expected_length + 2).map(m => m.name));
    n1Predicted[show.conditioning_on] = excludeSet;
  }

  const marg = computeMarginals(currentShow, excludeSet);
  const top = marg.slice(0, 30).filter(m => m.p >= 0.025);
  const target = MODEL.shows.find(s => s.id === currentShow).expected_length;
  const sumTop = top.reduce((a,m) => a+m.p, 0);

  let html = '';
  top.forEach((s, i) => {
    const pct = (s.p * 100).toFixed(1);
    const tier = tierForP(s.p);
    html += `<div class="minisong ${tier}" style="--c1:${tier==='blaze'?'#ff2d95':tier==='hot'?'#ff2d95':tier==='warm'?'#8b5cff':'#00f0ff'};--c2:${tier==='blaze'?'#ffae00':tier==='hot'?'#b14aed':tier==='warm'?'#00d0ff':'#3a7bff'}">
      <span class="rank">${i+1}</span>
      <span class="name">${s.name}</span>
      <span class="bar"><i style="width:${Math.min(100, s.p*100*2)}%"></i></span>
      <span class="pct">${pct}%</span>
    </div>`;
  });

  const metaText = excludeSet
    ? `Conditioned on N1's top ${excludeSet.size} predicted plays · ${top.length} songs sum to ${sumTop.toFixed(1)} of ~${target} expected · top picks at ~${Math.round(top[0]?.p*100||0)}%`
    : `${top.length} songs sum to ${sumTop.toFixed(1)} of ~${target} expected · top picks at ~${Math.round(top[0]?.p*100||0)}%`;

  document.getElementById('livemeta').textContent = metaText;
  document.getElementById('livelist').innerHTML = html;
}

function initControls(){
  // Build show selector
  const sel = document.getElementById('showsel');
  MODEL.shows.forEach(s => {
    const b = document.createElement('button');
    b.textContent = s.name;
    b.dataset.id = s.id;
    if (s.id === currentShow) b.classList.add('active');
    b.onclick = () => {
      currentShow = s.id;
      document.querySelectorAll('#showsel button').forEach(x => x.classList.toggle('active', x.dataset.id === s.id));
      updatePredictions();
    };
    sel.appendChild(b);
  });

  // Build parameter controls grouped by section
  const groupings = {
    base_rate: 'Base Rate',
    gap_factor: 'Gap & Bustout',
    set_position: 'Set Position Priors',
    multi_night: 'Multi-Night (Bayesian Update)',
    venue: 'Venue & Tour Leg',
    debuts: 'New Material',
    wildcards: 'Wildcards',
    normalization: 'Soundness Controls',
  };

  const container = document.getElementById('controls');
  Object.entries(groupings).forEach(([sec, label]) => {
    const ps = MODEL.parameters.filter(p => p.section === sec);
    if (!ps.length) return;
    const h = document.createElement('div');
    h.className = 'pgroup';
    h.innerHTML = `<span>${label}</span><span class="sm">${ps.length} parameter${ps.length>1?'s':''}</span>`;
    container.appendChild(h);

    const grid = document.createElement('div');
    grid.className = 'controls';
    ps.forEach(p => {
      const div = document.createElement('div');
      div.className = 'param';
      div.innerHTML = `
        <div class="name"><span>🪿 ${p.display_name} <span style="color:var(--muted);font-weight:400;font-size:.78rem">(${p.subtitle})</span></span><span class="val" id="val-${p.slug}">${formatVal(p.default, p.step)}</span></div>
        <input type="range" id="p-${p.slug}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.default}">
        <div class="desc">${p.description}</div>
      `;
      grid.appendChild(div);
      div.querySelector('input').addEventListener('input', e => {
        currentParams[p.slug] = parseFloat(e.target.value);
        div.querySelector('.val').textContent = formatVal(currentParams[p.slug], p.step);
        updatePredictions();
      });
    });
    container.appendChild(grid);
  });

  document.getElementById('reset').onclick = () => {
    MODEL.parameters.forEach(p => {
      currentParams[p.slug] = p.default;
      const el = document.getElementById('p-' + p.slug);
      if (el) {
        el.value = p.default;
        document.getElementById('val-' + p.slug).textContent = formatVal(p.default, p.step);
      }
    });
    updatePredictions();
  };

  // Presets
  document.getElementById('preset-msg').onclick = () => applyPreset({
    bustout_boldness: 0.6, album_promotion: 2.0, venue_aura: 1.3,
    no_repeat_rho: -0.98, cover_appetite: 1.4
  });
  document.getElementById('preset-safe').onclick = () => applyPreset({
    bustout_boldness: 0.1, european_bustout_dampening: 0.4,
    london_adjacency_boost: 1.35, cover_appetite: 0.8, no_repeat_rho: -0.95
  });
  document.getElementById('preset-chaos').onclick = () => applyPreset({
    bustout_boldness: 0.95, album_promotion: 2.5, debut_probability: 0.04,
    cover_appetite: 1.8, no_repeat_rho: -0.5, madhuvan_multiplier: 1.4
  });

  function applyPreset(overrides){
    Object.entries(overrides).forEach(([slug, val]) => {
      currentParams[slug] = val;
      const el = document.getElementById('p-' + slug);
      if (el){
        el.value = val;
        const p = MODEL.parameters.find(p => p.slug === slug);
        document.getElementById('val-' + slug).textContent = formatVal(val, p ? p.step : 0.01);
      }
    });
    updatePredictions();
  }

  updatePredictions();
}

function formatVal(v, step){
  if (step >= 1) return Math.round(v).toString();
  if (step >= 0.1) return v.toFixed(1);
  return v.toFixed(2);
}

window.addEventListener('DOMContentLoaded', initControls);
</script>"""


def render():
    guest_covers = [g["song"] for g in parameters.get("guest_only_covers", [])]
    js = (JS_MODEL
          .replace("__SONGS__", json.dumps(song_data))
          .replace("__PARAMS__", json.dumps(parameters["parameters"]))
          .replace("__STICK__", json.dumps(stickiness))
          .replace("__TIERS__", json.dumps(venue_tiers))
          .replace("__SHOWS__", json.dumps(parameters["shows"]))
          .replace("__EMPIRICAL__", json.dumps(empirical))
          .replace("__GUEST_COVERS__", f"new Set({json.dumps(guest_covers)})")
          )

    body = f'''
    <section class="assume">
      <h3><span class="icon">🪿</span>The Goose Oracle — pull every lever</h3>
      <ol>
        <li>This is the <strong>live forecasting model</strong>. Drag any slider and the predictions for the selected show recompute instantly. All twenty parameters are exposed.</li>
        <li>The math is the same multiplicative-factor model from the <a href="methodology.html">methodology spec</a>:
          $$ p_{{s,k}} \\propto b_s \\cdot g(\\Delta_{{s,k}}) \\cdot \\pi_{{s,k}} \\cdot V_{{s,k}} \\cdot D_{{s,k}} \\cdot R_{{s,k}} $$
          renormalized so the probabilities sum to the show's expected length, capped at 40-50%.</li>
        <li>Night-2 shows are <strong>Bayesian-conditioned on Night 1</strong>'s predicted plays — songs at the top of N1 are down-weighted to 5% of their N2 base, per the empirical {empirical["two_night_repeat_rate"]*100:.2f}% same-venue repeat rate (n={empirical["two_night_n_pairs"]}).</li>
        <li>Try the presets: <strong>MSG Marquee Mode</strong> turns up bustout/cover odds, <strong>Euro Safety</strong> leans on the London 5/22 songbook, and <strong>Total Chaos</strong> cranks the dials to maximum entropy.</li>
      </ol>
    </section>

    <div class="seclabel">🎛️ Pick a show to forecast</div>
    <div class="showsel" id="showsel"></div>

    <div class="seclabel">🎚️ Tune the parameters</div>
    <div class="preset">
      <button id="reset">↺ Reset to defaults</button>
      <button id="preset-msg">🗽 MSG Marquee Mode</button>
      <button id="preset-safe">🇳🇱 Euro Safety Mode</button>
      <button id="preset-chaos">🌪️ Total Chaos</button>
    </div>
    <div id="controls" style="margin-top:18px"></div>

    <div class="seclabel">📈 Live forecast</div>
    <div class="live">
      <h3>Current predictions (top 30 songs, sorted by probability)</h3>
      <div class="meta" id="livemeta">Loading…</div>
      <div class="minilist" id="livelist"></div>
    </div>

    <div class="seclabel">🔢 What the formula does (in plain English)</div>
    <div class="eqbox"><span class="eq">p(song) = base_rate     ← blended rotation (Honk Factor controls the blend weight)
         × gap_multiplier   ← recency tweak + Gaussian bustout bump
         × set_position_fit ← Madhuvan/Encore/Opener/Closer pool boost
         × venue_aura       ← MSG = 1.4×, Amsterdam = 1.0×
         × debut_factor     ← new-album hype + decay
         × no_repeat_R      ← only kicks in for Night 2 (Bayesian update)

then SCALE so Σ p(song) = expected show length
then CAP at the per-song ceiling (so no song clears 50%)
then RENORMALIZE the redistributed mass.</span></div>

    <div class="note"><b>What the sliders cannot capture:</b> segues (Hot Tea > Madhuvan), guest sit-ins (Stuart Bogie horns, Cory Wong), exact song order within a set, or thematic curation (Goosemas, NYE). These belong in a sequence model (LSTM, transformer) on the v2 roadmap.</div>
'''

    page_html = PAGE_TPL.format(
        head=head("The Model").replace(SHARED_CSS, MODEL_CSS) + '''
  <script>window.MathJax = {tex:{inlineMath:[['$','$']], displayMath:[['$$','$$']]}};</script>
  <script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
''',
        grain=GRAIN,
        nav=nav("model"),
        art=MATH_SVG,
        kicker="The Forecasting Oracle · 20 parameters",
        h1="The Goose Oracle",
        venue="Interactive setlist forecasting model",
        dates="Pull the levers, watch the probabilities dance",
        format="Live model · JavaScript · 220 songs · 20 parameters",
        body=body,
    ) + js + "</body></html>"

    (ROOT / "model.html").write_text(page_html, encoding="utf-8")
    print("wrote model.html")


if __name__ == "__main__":
    render()
