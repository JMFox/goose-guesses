"""GooseGuesses prediction engine.

Implements the model from METHODOLOGY.md (v1.0):

    p_{s,k} ∝ b_s · g(Δ_{s,k}) · π_{s,k} · V_{s,k} · D_{s,k} · R_{s,k}

then renormalizes so Σ p_{s,k} = E[N_k] and caps at p_cap.

For Night 2 of multi-night runs, applies the Bayesian no-repeat update
conditioned on N1's predicted plays.

Outputs `predictions.json` consumed by render_html.py.
"""
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
stats = json.load(open(ROOT / "stats.json", encoding="utf-8"))
params = json.load(open(ROOT / "parameters.json", encoding="utf-8"))


def param(slug):
    for p in params["parameters"]:
        if p["slug"] == slug:
            return p["default"]
    raise KeyError(slug)


def venue_tier(tier_name):
    for t in params["venue_tiers"]:
        if t["tier"] == tier_name:
            return t
    raise KeyError(tier_name)


STICKINESS = {o["song"]: o["rho"] for o in params["stickiness_overrides"]}
# AUDIT (Q2/Q9): Of the 6 current stickiness overrides, only ECHO OF A ROSE and
# MADHUVAN ever actually repeated N1->N2 same-venue across 9 years of data
# (1 instance each, n=105 pairs). HOT TEA, DRIPFIELD, EMPRESS, DON'T DO IT have
# NEVER repeated — the default rho=-0.95 already captures that behavior, so the
# overrides are vibes-driven, not data-driven. Empirical "strong" anchors
# (>=2 repeats) since 2024: ['Big Modern!'] only. Recommended override list:
#   {"song": "Big Modern!", "rho": -0.5}    # 2x repeat in 2024-2025 (Goosemas, Beacon)
#   {"song": "Echo of a Rose", "rho": -0.7} # 1x repeat (Capitol 9/24)
#   {"song": "Madhuvan", "rho": -0.7}       # 1x repeat (Radio City 4/15/23)
# Drop the rest. The default -0.95 stickiness already produces the empirically
# correct ~1% N1->N2 repeat rate.

# Build per-song lookups
SONGS = {s["name"]: s for s in stats["songs"]}
BLENDED = {r["name"]: r["blended_rate"] for r in stats["rotation"]["top_50_blended"]}
SET_POS = {sp["song"]: sp for sp in stats["set_position_matrix_top30"]}
N_SHOWS = stats["show_stats"]["n_shows_total"]
LAST_DATE = stats["show_stats"]["date_range"][1]

# Build set-role pools by computing counts from the per-song stats
S2_OPEN_COUNTS = Counter()
ENC_COUNTS = Counter()
OPEN_COUNTS = Counter()
CLOSE_COUNTS = Counter()
for s in stats["songs"]:
    if s.get("set2_opener_count", 0):
        S2_OPEN_COUNTS[s["name"]] = s["set2_opener_count"]
    if s.get("encore_count", 0):
        ENC_COUNTS[s["name"]] = s["encore_count"]
    if s.get("opener_count", 0):
        OPEN_COUNTS[s["name"]] = s["opener_count"]
    if s.get("set2_closer_count", 0):
        CLOSE_COUNTS[s["name"]] = s["set2_closer_count"]


def pools(top_t):
    return {
        "s2_open": set(s for s, _ in S2_OPEN_COUNTS.most_common(top_t)),
        "encore": set(s for s, _ in ENC_COUNTS.most_common(top_t)),
        "opener": set(s for s, _ in OPEN_COUNTS.most_common(top_t)),
        "closer": set(s for s, _ in CLOSE_COUNTS.most_common(max(top_t // 2, 4))),
    }


# London 5/22/26 setlist (most recent show; freshest signal for the Euro leg)
def shows_with_song(name):
    return [sh for sh in stats["shows"] if name in sh.get("songs", [])]


def get_show_setlist(date):
    for sh in stats["shows"]:
        if sh["date"] == date:
            return set(sh.get("songs", []))
    return set()


LONDON_5_22 = get_show_setlist("2026-05-22")
print(f"London 5/22/26 setlist size: {len(LONDON_5_22)}")

# 2026 debuts (true first-times) and returns
DEBUTS_2026 = set(d["name"] for d in stats.get("debuts_2026", []))
RETURNS_2026 = set(r["name"] for r in stats.get("returns_2026", []))

# Guest-only / special-occasion covers — should NOT receive the debut boost.
# These are covers Goose played as one-offs with sit-in guests (e.g. Jim James,
# Cory Wong at Viva El Gonzo private destination festival May 2026) and are
# extremely unlikely to recur at standalone Amsterdam/MSG shows.
GUEST_ONLY_COVERS = set(g["song"] for g in params.get("guest_only_covers", []))

# Hot Tea slot bias — Hot Tea is a CLOSER/encore song, NOT a set-2 launch pad
# (per audit Q8: only 4.3% of plays open set 2; 25.6% close set 1, 17.7%
# close set 2, 15.2% encore).
HOT_TEA_SLOT_BIAS = params.get("hot_tea_slot_bias", {})


def base_rate(song_name):
    """b_s = blended rotation rate (55% 2026 tour, 45% last 50)."""
    if song_name in BLENDED:
        return BLENDED[song_name]
    s = SONGS.get(song_name, {})
    return s.get("plays_last_50", 0) / 50


# Empirical mean gap for the typical "in-rotation" song
TYPICAL_GAP = 8  # rough mean across heavy rotators in last-50 window


def gap_multiplier(gap_shows, career_plays, base_rate_s):
    """g(Δ): mild recency adjustment.

    For top rotators (high base_rate) the gap multiplier stays near 1, since
    the blended base rate already captures most of the recency signal.
    For low-frequency career staples (career_plays >= 8 but low base_rate),
    a Gaussian bustout bump kicks in around gap ≈ μ_B shows.
    """
    mu_b = param("bustout_peak_gap")
    sigma_b = param("bustout_peak_width")
    boldness = param("bustout_boldness")

    if gap_shows <= 0:
        return 0.30  # very-recently-played penalty
    # Light penalty for just-played songs (gap 1-3)
    if gap_shows <= 3:
        decay = 0.60 + 0.10 * gap_shows
    else:
        decay = 1.0

    # Bustout bump only for songs with established career and meaningful gap
    if career_plays >= 8 and gap_shows >= 25 and base_rate_s < 0.15:
        bump = boldness * math.exp(-((gap_shows - mu_b) ** 2) / (2 * sigma_b ** 2))
        decay *= 1 + bump
    return decay


def pi_factor(song_name, format_, pool):
    """Set-position appropriateness multiplier — capped to prevent inflation.

    Special case: Hot Tea is empirically a CLOSER (set1/set2) and encore song,
    not a set-2 launch pad (only 4.3% of plays). We explicitly remove it from
    the launch-pad boost and add it to the closer boost.
    """
    m = 1.0
    if format_ == "two_set_encore":
        if song_name in pool["s2_open"] and song_name != "Hot Tea":
            m *= param("madhuvan_multiplier")
        if song_name in pool["encore"]:
            m *= param("encore_multiplier")
        if song_name in pool["opener"]:
            m *= param("opener_multiplier")
        if song_name in pool["closer"] or song_name == "Hot Tea":
            m *= param("set_closer_multiplier")
    return min(m, 1.25)


def debut_factor(song_name, show_date):
    """D_{s,k}: new material over-indexes; unplayed BIG MODERN! tracks get hype.

    Critical exclusion: GUEST_ONLY_COVERS (Cortez The Killer, Hey Joe, etc.)
    are NOT given the 2026-debut boost. They appeared at Viva El Gonzo with
    sit-in guests (Jim James, Cory Wong) and are extremely unlikely to recur
    at standalone Amsterdam/MSG shows where those guests are not present.
    """
    if song_name in GUEST_ONLY_COVERS:
        return 0.20  # Strong damper — guest-only one-offs

    s = SONGS.get(song_name)
    if not s:
        return 1.0

    # Recently debuted songs decay with half-life
    half_life = param("debut_halflife_shows")
    if s.get("is_2026_debut"):
        # Approximate shows since debut (use plays_2026 as proxy)
        plays = max(s.get("plays_2026", 1), 1)
        # Decay: more plays since debut → less bonus
        boost = (param("album_promotion") - 1.0) * 0.5 ** (plays / half_life)
        return 1.0 + boost
    if song_name in RETURNS_2026:
        return 1.0 + 0.15  # modest boost for rotation returns
    return 1.0


def london_boost(song_name, is_euro):
    # AUDIT (assumptions_audit.py, Q1): empirical cross-venue overlap at the
    # 5-day gap (London 5/22 -> Amsterdam 5/27) is 9.6% post-2024 (n=61),
    # which is ~10x the same-venue baseline of ~0.9% but also indicates that
    # roughly 1 in 10 songs DO carry across. The current parameter slug is
    # `london_recency_penalty` (default 0.55) — a multiplicative damper. The
    # call below references the old slug `london_adjacency_boost` and KeyErrors.
    # Recommended fix:
    #     if is_euro and song_name in LONDON_5_22:
    #         return param("london_recency_penalty")   # ~0.80 is the data-implied value
    #     return 1.0
    # The 0.55 default is too aggressive given the data — propose raising to 0.80
    # so a London-played song is only mildly damped on a 5-day cross-venue jump.
    if is_euro and song_name in LONDON_5_22:
        return param("london_recency_penalty")
    return 1.0


def _is_interlude(name):
    # BIG MODERN! album interludes look like "(dawn)", "(begin)", "((nocturne))"
    return name.startswith("(") and name.endswith(")")


def compute_marginals(show, exclude=None):
    """Returns dict {song: p_marginal} for a given show.

    `exclude` is a set of songs to deprioritize via the no-repeat conditional
    (used for Night 2 with the N1 predicted-plays set).
    """
    target_len = show["expected_length"]
    fmt = show["format"]
    tier_info = venue_tier(show["tier"])
    V = tier_info["V"] * param("venue_aura")
    is_euro = show["tier"] == "european_first_time"

    top_t = param("top_role_count")
    pool = pools(top_t)

    # Universe: all songs with positive blended rate OR recent plays, filtered
    # for interlude/marker tracks that aren't standalone songs.
    universe = set(BLENDED.keys()) | {
        s["name"] for s in stats["songs"] if s.get("plays_last_50", 0) > 0
    }
    universe |= set(b["name"] for b in stats.get("bustout_candidates", []))
    universe = {n for n in universe if not _is_interlude(n)}

    raw = {}
    for name in universe:
        b = base_rate(name)
        if b <= 0 and name not in (b_c["name"] for b_c in stats.get("bustout_candidates", [])):
            continue

        s = SONGS.get(name, {})
        gap = s.get("gap_shows", 50)
        career = s.get("career_plays", 0)

        g = gap_multiplier(gap, career, b)
        pi = pi_factor(name, fmt, pool)
        D = debut_factor(name, show["date"])
        ldn = london_boost(name, is_euro)

        # Bustout multiplier from venue tier
        bustout_mult = tier_info.get("bustout_mult", 1.0)
        if is_euro:
            bustout_mult *= param("european_bustout_dampening")
        # Apply bustout multiplier only to the bustout-bump portion (gap > 30)
        if gap > 30 and career >= 6:
            extra = (bustout_mult - 1.0) * min(1.0, (gap - 30) / 60)
            g *= 1 + extra

        # No-repeat conditioning (N2 only). Empirical posterior: ~1% repeat rate.
        R = 1.0
        if exclude and name in exclude:
            rho = STICKINESS.get(name, param("no_repeat_rho"))
            R = max(0.0, 1 + rho)  # rho = -0.95 → R = 0.05 (5% relative carry)
        elif exclude:
            # Songs NOT played N1 get a small redistribution boost; this is the
            # conditional mass under the Bayesian tilt.
            R = 1.10

        if max(b, 0.001) <= 0:
            continue
        raw[name] = max(b, 0.001) * g * pi * V * D * ldn * R

    # Renormalize so sum equals target_len
    total = sum(raw.values())
    if total <= 0:
        return {}
    k = target_len / total
    p = {name: v * k for name, v in raw.items()}

    # Apply cap and re-renormalize. Single-set uses a tighter cap than two-set.
    p_cap = param("prob_cap")
    if fmt == "single_set":
        p_cap = min(p_cap, 0.40)
    capped = {}
    over_mass = 0.0
    under_total = 0.0
    for name, v in p.items():
        if v > p_cap:
            over_mass += v - p_cap
            capped[name] = p_cap
        else:
            capped[name] = v
            under_total += v
    # Redistribute over-mass proportionally among uncapped
    if over_mass > 0 and under_total > 0:
        for name, v in capped.items():
            if v < p_cap:
                capped[name] = min(p_cap, v * (1 + over_mass / under_total))

    return capped


def top_n(marginals, n=40, min_pct=0.04):
    items = sorted(marginals.items(), key=lambda kv: -kv[1])
    return [(name, v) for name, v in items if v >= min_pct][:n]


def rationale(name, show, n1_set=None):
    """Build a short, human rationale string for a song."""
    bits = []
    b = base_rate(name)
    bits.append(f"{round(100*b)}% recent rotation")

    s = SONGS.get(name, {})
    gap = s.get("gap_shows", 0)
    career = s.get("career_plays", 0)

    pool = pools(param("top_role_count"))
    if name in pool["s2_open"]:
        bits.append("set-2 launch pad")
    elif name in pool["closer"]:
        bits.append("set closer")
    elif name in pool["encore"]:
        bits.append("encore staple")
    elif name in pool["opener"]:
        bits.append("show opener")

    if name in GUEST_ONLY_COVERS:
        bits.append("Gonzo-only guest cover")
    elif name in DEBUTS_2026:
        bits.append("2026 debut")
    elif name in RETURNS_2026:
        bits.append("recent return")

    is_euro = show["tier"] == "european_first_time"
    if is_euro and name in LONDON_5_22:
        bits.append("played London 5/22")

    if gap > 50 and career >= 8 and not s.get("is_original", True):
        bits.append(f"bustout candidate (gap {gap})")
    elif gap > 30 and career >= 10:
        bits.append(f"due (gap {gap})")

    if n1_set and name not in n1_set and name in BLENDED:
        bits.append("eligible after N1")

    return " · ".join(bits)


# Compute marginals for each show
ams_n1 = next(s for s in params["shows"] if s["id"] == "ams_n1")
ams_n2 = next(s for s in params["shows"] if s["id"] == "ams_n2")
msg_n1 = next(s for s in params["shows"] if s["id"] == "msg_n1")
msg_n2 = next(s for s in params["shows"] if s["id"] == "msg_n2")

ams_n1_marg = compute_marginals(ams_n1)
msg_n1_marg = compute_marginals(msg_n1)

# For N2: predict N1's most likely setlist, then condition
def likely_setlist(marginals, target_len):
    items = sorted(marginals.items(), key=lambda kv: -kv[1])
    return set(name for name, _ in items[: int(target_len + 2)])

ams_n1_likely = likely_setlist(ams_n1_marg, ams_n1["expected_length"])
msg_n1_likely = likely_setlist(msg_n1_marg, msg_n1["expected_length"])

ams_n2_marg = compute_marginals(ams_n2, exclude=ams_n1_likely)
msg_n2_marg = compute_marginals(msg_n2, exclude=msg_n1_likely)


# Bustout candidates (career staples, gap >= 20, plays >= 8 originals or covers)
def bustout_picks(top_n=4):
    cands = stats.get("bustout_candidates", [])
    return cands[:top_n]


# Cover probability per show
def cover_prob(tier_info):
    # AUDIT (Q7): last-50 P(>=1 cover) = 88.0% — the 0.88 baseline is exact.
    # `cover_appetite` default 1.0 is correct. Marquee cover rate is 88.9%
    # (n=27 marquee shows) — IDENTICAL to last-50 baseline. The current
    # marquee `cover_mult`=1.1 is overconfident; recommend setting it to **1.00**
    # (or 1.05 to leave some asymmetry headroom). Marquee shows are not
    # cover-heavier than typical shows.
    base_p = stats.get("cover_stats", {}).get("shows_with_cover_pct_last_50", 0.88)
    return min(0.99, base_p * tier_info.get("cover_mult", 1.0) * param("cover_appetite"))


def build_show_payload(show, marginals, n1_set=None):
    items = top_n(marginals, n=40, min_pct=0.025)
    tier_info = venue_tier(show["tier"])
    p_cover = cover_prob(tier_info)
    bo = bustout_picks(5)
    listed_total = sum(v for _, v in items)
    grand_total = sum(marginals.values())

    return {
        "id": show["id"],
        "name": show["name"],
        "date": show["date"],
        "venue": show["venue"],
        "tier": show["tier"],
        "format": show["format"],
        "expected_length": show["expected_length"],
        "sets": show["sets"],
        "encore": show["encore"],
        "run_position": show["run_position"],
        "notes": show["notes"],
        "songs": [
            {
                "rank": i + 1,
                "name": name,
                "pct": round(100 * v, 1),
                "rationale": rationale(name, show, n1_set),
            }
            for i, (name, v) in enumerate(items)
        ],
        "listed_total_songs": round(listed_total, 2),
        "model_total_songs": round(grand_total, 2),
        "p_cover": round(p_cover, 2),
        "p_debut_per_slot": round(tier_info["debut_per_slot"], 4),
        "p_bustout": round(
            tier_info["bustout_mult"] * param("bustout_boldness") * 0.2, 2
        ),
        "venue_V": tier_info["V"],
        "bustouts": [
            {
                "name": b["name"],
                "gap_shows": b.get("gap_shows", 0),
                "career_plays": b.get("career_plays", 0),
                "last_played": b.get("last_played", ""),
            }
            for b in bo
        ],
        "conditioning_on": show.get("conditioning_on"),
        "n1_predicted_plays": sorted(n1_set) if n1_set else None,
    }


predictions = {
    "generated_at": "2026-05-23",
    "methodology_version": "1.0",
    "data_source": stats.get("data_source", "El Goose API v2"),
    "n_shows_in_data": N_SHOWS,
    "last_show_date": LAST_DATE,
    "window_avg_songs_per_show": stats["rotation"]["window_avg_unique_songs"],
    "empirical": {
        "avg_songs_last_50": stats["show_stats"]["avg_songs_last_50"],
        "stdev_songs_last_50": stats["show_stats"]["stdev_songs_last_50"],
        "two_night_repeat_rate": stats.get("two_night_run_stats", {}).get(
            "pooled_repeat_rate", 0.0089
        ),
        "two_night_n_pairs": stats.get("two_night_run_stats", {}).get(
            "n_consecutive_pairs", 105
        ),
        "two_night_pairs_with_repeat": stats.get("two_night_run_stats", {}).get(
            "n_pairs_with_any_repeat", 11
        ),
        "cover_show_rate_last_50": stats.get("cover_stats", {}).get(
            "shows_with_cover_pct_last_50", 0.88
        ),
        "avg_set1_len": stats["show_stats"]["avg_set1_len_last50"],
        "avg_set2_len": stats["show_stats"]["avg_set2_len_last50"],
        "avg_encore_len": stats["show_stats"]["avg_encore_len_last50"],
    },
    "shows": {
        "ams_n1": build_show_payload(ams_n1, ams_n1_marg),
        "ams_n2": build_show_payload(ams_n2, ams_n2_marg, n1_set=ams_n1_likely),
        "msg_n1": build_show_payload(msg_n1, msg_n1_marg),
        "msg_n2": build_show_payload(msg_n2, msg_n2_marg, n1_set=msg_n1_likely),
    },
}

with open(ROOT / "predictions.json", "w", encoding="utf-8") as f:
    json.dump(predictions, f, indent=2)

# Console summary
print(f"\n=== GooseGuesses predictions written to predictions.json ===\n")
for show_id, payload in predictions["shows"].items():
    print(f"--- {payload['name']} ({payload['date']}, ~{payload['expected_length']} songs) ---")
    for s in payload["songs"][:10]:
        print(f"  {s['rank']:2d}. {s['pct']:5.1f}%  {s['name']}")
    print()
print(f"Empirical 2-night repeat rate: {predictions['empirical']['two_night_repeat_rate']*100:.2f}%")
print(f"Empirical cover rate (last 50): {predictions['empirical']['cover_show_rate_last_50']*100:.1f}%")
