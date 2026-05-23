# -*- coding: utf-8 -*-
"""
compute_stats.py — compute empirical statistics for the Goose setlist
prediction model.

Reads per-year setlist JSON files from ./data/goose{YYYY}.json and writes
./stats.json with comprehensive song- and show-level statistics that the
downstream probabilistic model consumes.

Key conventions in the source data
----------------------------------
* `setnumber == "1"` / `"2"` / `"3"` ... = numbered set
* `setnumber == "e"` or `"e2"`            = encore
* `settype` is "Set" or "One Set" (no "Soundcheck" present)
* `isoriginal == 1`  = Goose original; `isoriginal == 0` = cover
"""
import json
import os
import statistics
from collections import Counter, defaultdict
from datetime import date as _date

# ---------------------------------------------------------------------- config
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")
YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
TODAY = "2026-05-23"

# ----------------------------------------------------------------- load + index
rows = []
for y in YEARS:
    path = os.path.join(DATA_DIR, f"goose{y}.json")
    if not os.path.exists(path):
        continue
    with open(path, encoding="utf-8") as f:
        rows += json.load(f)["data"]

# Only "Goose" artist rows; drop anything missing a showdate.
rows = [r for r in rows if (r.get("artist") or "").strip().lower() == "goose"
        and r.get("showdate")]

# Group rows by show date.
shows = defaultdict(list)
for r in rows:
    shows[r["showdate"]].append(r)
dates = sorted(shows.keys())
N_SHOWS = len(dates)

# ---------------------------------------------------------------- helpers
def _real(d):
    """Performed songs at a given show — excludes soundchecks (none observed,
    but defensive)."""
    return [x for x in shows[d] if (x.get("settype") or "").lower() != "soundcheck"]

def _songset(d):
    return set(x["songname"] for x in _real(d))

def _by_slot(d):
    """Return dict {setnumber_str: [rows sorted by position]} for one show."""
    by = defaultdict(list)
    for x in _real(d):
        by[str(x["setnumber"])].append(x)
    for k in by:
        by[k].sort(key=lambda x: x["position"])
    return by

def _slot(setnumber):
    s = str(setnumber).lower()
    if s.startswith("e"):
        return "encore"
    if s == "1":
        return "set1"
    if s == "2":
        return "set2"
    return f"set{s}"

# --------------------------------------------- canonical song-name handling
# Light hash-table for is_original lookup (per-song majority vote).
song_isoriginal_votes = defaultdict(Counter)
for r in rows:
    song_isoriginal_votes[r["songname"]][int(r.get("isoriginal", 1))] += 1
def is_original(song):
    votes = song_isoriginal_votes[song]
    return votes.most_common(1)[0][0] == 1 if votes else True

# ---------------------------------------------------------- per-song stats
ALL_SONGS = set(r["songname"] for r in rows)

career_plays = Counter()
plays_2026   = Counter()
plays_2025   = Counter()
plays_2024   = Counter()
set1_plays   = Counter()
set2_plays   = Counter()
set3_plays   = Counter()
encore_plays = Counter()
first_played = {}
last_played  = {}
opener_count    = Counter()
set1_closer_cnt = Counter()
set2_opener_cnt = Counter()
set2_closer_cnt = Counter()
encore_cnt      = Counter()

# Last-window play counts (last 50 / 20 shows by date).
last50_dates = dates[-50:] if len(dates) >= 50 else dates[:]
last20_dates = dates[-20:] if len(dates) >= 20 else dates[:]
last50_set = set(last50_dates)
last20_set = set(last20_dates)
plays_last_50 = Counter()
plays_last_20 = Counter()

# Index of show date -> index in `dates` (for gap calc).
date_to_idx = {d: i for i, d in enumerate(dates)}
last_play_idx = {}

for d in dates:
    by = _by_slot(d)
    seen_in_show = set()
    for setnum, items in by.items():
        for r in items:
            s = r["songname"]
            seen_in_show.add(s)
            if setnum == "1":   set1_plays[s] += 1
            elif setnum == "2": set2_plays[s] += 1
            elif setnum == "3": set3_plays[s] += 1
            elif str(setnum).startswith("e"): encore_plays[s] += 1
    # Per-unique-song-per-show metrics:
    for s in seen_in_show:
        career_plays[s] += 1
        last_play_idx[s] = date_to_idx[d]
        first_played.setdefault(s, d)
        last_played[s] = d
        y = d[:4]
        if y == "2024": plays_2024[s] += 1
        if y == "2025": plays_2025[s] += 1
        if y == "2026": plays_2026[s] += 1
        if d in last50_set: plays_last_50[s] += 1
        if d in last20_set: plays_last_20[s] += 1

    # set-position roles (on this show)
    if by.get("1"):
        opener_count[by["1"][0]["songname"]] += 1
        set1_closer_cnt[by["1"][-1]["songname"]] += 1
    if by.get("2"):
        set2_opener_cnt[by["2"][0]["songname"]] += 1
        set2_closer_cnt[by["2"][-1]["songname"]] += 1
    # encore — use first row of any setnumber starting with "e"
    enc_rows = []
    for k, v in by.items():
        if str(k).startswith("e"):
            enc_rows.extend(v)
    if enc_rows:
        enc_rows.sort(key=lambda x: (str(x["setnumber"]), x["position"]))
        encore_cnt[enc_rows[0]["songname"]] += 1

# gap_shows = how many shows since this song last appeared
gap_shows = {s: (N_SHOWS - 1) - i for s, i in last_play_idx.items()}

# debut flags
is_2026_debut = {s: first_played[s].startswith("2026") for s in first_played}
is_2025_debut = {s: first_played[s].startswith("2025") for s in first_played}

# Rank songs by career_plays, top 200
top200 = [s for s, _ in career_plays.most_common(200)]
song_stats = []
for s in top200:
    song_stats.append({
        "name": s,
        "is_original": is_original(s),
        "career_plays": career_plays[s],
        "plays_2024": plays_2024[s],
        "plays_2025": plays_2025[s],
        "plays_2026": plays_2026[s],
        "plays_last_50": plays_last_50[s],
        "plays_last_20": plays_last_20[s],
        "first_played_date": first_played[s],
        "last_played_date":  last_played[s],
        "gap_shows":         gap_shows[s],
        "is_2026_debut":     is_2026_debut.get(s, False),
        "is_2025_debut":     is_2025_debut.get(s, False),
        "set1_plays":        set1_plays[s],
        "set2_plays":        set2_plays[s],
        "set3_plays":        set3_plays[s],
        "encore_plays":      encore_plays[s],
        "opener_count":      opener_count[s],
        "set1_closer_count": set1_closer_cnt[s],
        "set2_opener_count": set2_opener_cnt[s],
        "set2_closer_count": set2_closer_cnt[s],
        "encore_count":      encore_cnt[s],
    })

# -------------------------------------------------------- per-show stats
def n_unique_songs(d):
    return len(_songset(d))

len_all   = [n_unique_songs(d) for d in dates]
len_last50= [n_unique_songs(d) for d in last50_dates]
len_last20= [n_unique_songs(d) for d in last20_dates]

# set-segment lengths for shows that actually have set 1 + set 2 (two-set shows)
set1_lens, set2_lens, encore_lens = [], [], []
set1_lens_50, set2_lens_50, encore_lens_50 = [], [], []
set1_lens_20, set2_lens_20, encore_lens_20 = [], [], []
for d in dates:
    by = _by_slot(d)
    has_s1 = bool(by.get("1"))
    has_s2 = bool(by.get("2"))
    if has_s1 and has_s2:
        s1l = len(by["1"]); s2l = len(by["2"])
        el = sum(len(v) for k, v in by.items() if str(k).startswith("e"))
        set1_lens.append(s1l); set2_lens.append(s2l); encore_lens.append(el)
        if d in last50_set:
            set1_lens_50.append(s1l); set2_lens_50.append(s2l); encore_lens_50.append(el)
        if d in last20_set:
            set1_lens_20.append(s1l); set2_lens_20.append(s2l); encore_lens_20.append(el)

def _safe_stdev(xs):
    return statistics.pstdev(xs) if len(xs) >= 2 else 0.0

def _mean(xs):
    return (sum(xs) / len(xs)) if xs else 0.0

show_stats = {
    "n_shows_total": N_SHOWS,
    "date_range": [dates[0], dates[-1]] if dates else [None, None],
    "avg_songs_all":      _mean(len_all),
    "avg_songs_last_50":  _mean(len_last50),
    "avg_songs_last_20":  _mean(len_last20),
    "stdev_songs_all":     _safe_stdev(len_all),
    "stdev_songs_last_50": _safe_stdev(len_last50),
    "stdev_songs_last_20": _safe_stdev(len_last20),
    "two_set_shows_n_all":    len(set1_lens),
    "two_set_shows_n_last50": len(set1_lens_50),
    "two_set_shows_n_last20": len(set1_lens_20),
    "avg_set1_len_all":       _mean(set1_lens),
    "avg_set2_len_all":       _mean(set2_lens),
    "avg_encore_len_all":     _mean(encore_lens),
    "avg_set1_len_last50":    _mean(set1_lens_50),
    "avg_set2_len_last50":    _mean(set2_lens_50),
    "avg_encore_len_last50":  _mean(encore_lens_50),
    "avg_set1_len_last20":    _mean(set1_lens_20),
    "avg_set2_len_last20":    _mean(set2_lens_20),
    "avg_encore_len_last20":  _mean(encore_lens_20),
    "stdev_set1_len_all":     _safe_stdev(set1_lens),
    "stdev_set2_len_all":     _safe_stdev(set2_lens),
    "stdev_encore_len_all":   _safe_stdev(encore_lens),
    "stdev_set1_len_last50":  _safe_stdev(set1_lens_50),
    "stdev_set2_len_last50":  _safe_stdev(set2_lens_50),
    "stdev_encore_len_last50":_safe_stdev(encore_lens_50),
    "min_show_songs":     min(len_all) if len_all else 0,
    "max_show_songs":     max(len_all) if len_all else 0,
    "min_set1_len_all":       min(set1_lens) if set1_lens else 0,
    "max_set1_len_all":       max(set1_lens) if set1_lens else 0,
    "min_set2_len_all":       min(set2_lens) if set2_lens else 0,
    "max_set2_len_all":       max(set2_lens) if set2_lens else 0,
    "min_encore_len_all":     min(encore_lens) if encore_lens else 0,
    "max_encore_len_all":     max(encore_lens) if encore_lens else 0,
    "min_set1_len_last50":    min(set1_lens_50) if set1_lens_50 else 0,
    "max_set1_len_last50":    max(set1_lens_50) if set1_lens_50 else 0,
    "min_set2_len_last50":    min(set2_lens_50) if set2_lens_50 else 0,
    "max_set2_len_last50":    max(set2_lens_50) if set2_lens_50 else 0,
    "min_encore_len_last50":  min(encore_lens_50) if encore_lens_50 else 0,
    "max_encore_len_last50":  max(encore_lens_50) if encore_lens_50 else 0,
}

# ------------------------------------------------ length-distribution buckets
def _histogram(xs, edges):
    h = [0] * (len(edges) + 1)
    for v in xs:
        placed = False
        for i, e in enumerate(edges):
            if v <= e:
                h[i] += 1; placed = True; break
        if not placed:
            h[-1] += 1
    return h

show_len_edges = [10, 12, 14, 16, 18, 20]
set1_edges     = [6, 8, 10, 12]
set2_edges     = [6, 8, 10, 12]
encore_edges   = [1, 2, 3]
length_hist = {
    "show_songs_edges":      show_len_edges,
    "show_songs_last50":     _histogram(len_last50, show_len_edges),
    "show_songs_last20":     _histogram(len_last20, show_len_edges),
    "show_songs_all":        _histogram(len_all, show_len_edges),
    "set1_edges":            set1_edges,
    "set1_hist_all":         _histogram(set1_lens, set1_edges),
    "set1_hist_last50":      _histogram(set1_lens_50, set1_edges),
    "set2_edges":            set2_edges,
    "set2_hist_all":         _histogram(set2_lens, set2_edges),
    "set2_hist_last50":      _histogram(set2_lens_50, set2_edges),
    "encore_edges":          encore_edges,
    "encore_hist_all":       _histogram(encore_lens, encore_edges),
    "encore_hist_last50":    _histogram(encore_lens_50, encore_edges),
}

# ---------------------------------------------------- covers
def show_has_cover(d):
    return any(int(x.get("isoriginal", 1)) == 0 for x in _real(d))
def show_n_covers(d):
    return sum(1 for x in _real(d) if int(x.get("isoriginal", 1)) == 0)

cover_shows_last50 = sum(1 for d in last50_dates if show_has_cover(d))
cover_shows_all    = sum(1 for d in dates if show_has_cover(d))
avg_covers_show_50 = _mean([show_n_covers(d) for d in last50_dates])
avg_covers_show_all = _mean([show_n_covers(d) for d in dates])

cover_counter = Counter()
for d in dates:
    for x in _real(d):
        if int(x.get("isoriginal", 1)) == 0:
            cover_counter[x["songname"]] += 1
top_covers = [{"name": s, "plays": n, "last_played": last_played.get(s),
               "plays_last_50": plays_last_50.get(s, 0)}
              for s, n in cover_counter.most_common(40)]

cover_stats = {
    "shows_with_cover_last_50":  cover_shows_last50,
    "shows_with_cover_pct_last_50": (cover_shows_last50 / len(last50_dates)) if last50_dates else 0,
    "shows_with_cover_all":      cover_shows_all,
    "shows_with_cover_pct_all":  (cover_shows_all / N_SHOWS) if N_SHOWS else 0,
    "avg_covers_per_show_last_50": avg_covers_show_50,
    "avg_covers_per_show_all":     avg_covers_show_all,
    "top_covers":                   top_covers,
}

# ---------------------------------------------------- 2-night run repeats
# Find all consecutive-night pairs at the same venue.
def _venue_key(d):
    # Use venue+city; (state) optional. Pull first row.
    if not shows[d]:
        return None
    r = shows[d][0]
    return (r.get("venuename") or "", r.get("city") or "", r.get("state") or "")

# Construct adjacency by date
from datetime import datetime, timedelta
def _dt(d):
    return datetime.strptime(d, "%Y-%m-%d")

pairs = []
for i in range(len(dates) - 1):
    d1, d2 = dates[i], dates[i + 1]
    if (_dt(d2) - _dt(d1)).days == 1:
        v1, v2 = _venue_key(d1), _venue_key(d2)
        if v1 and v1 == v2:
            pairs.append((d1, d2))

pair_details = []
overlaps = []
for d1, d2 in pairs:
    s1 = _songset(d1); s2 = _songset(d2)
    if not s1 or not s2:
        continue
    inter = s1 & s2
    rep_rate_n1to_n2 = len(inter) / len(s1)   # share of N1 songs that recur on N2
    rep_rate_n2_from_n1 = len(inter) / len(s2)
    venue = _venue_key(d1)
    overlaps.append(rep_rate_n1to_n2)
    pair_details.append({
        "night1": d1,
        "night2": d2,
        "venue":  venue[0],
        "city":   venue[1],
        "state":  venue[2],
        "n1_songs": len(s1),
        "n2_songs": len(s2),
        "shared":   len(inter),
        "repeat_rate_n1_to_n2": rep_rate_n1to_n2,
        "repeat_rate_n2_from_n1": rep_rate_n2_from_n1,
        "shared_songs": sorted(inter),
    })

two_night_repeat_rate = _mean(overlaps)
two_night_repeat_stdev = _safe_stdev(overlaps)

# Alternate framing: pooled across all 2-night runs, what's the unconditional
# P(song played on N1 is also played on N2)?  This is the more useful prior
# for the model because it weights pairs by song count rather than averaging
# already-summarised rates.
pooled_n1_total = sum(p["n1_songs"] for p in pair_details)
pooled_shared   = sum(p["shared"]   for p in pair_details)
pooled_repeat_rate = (pooled_shared / pooled_n1_total) if pooled_n1_total else 0

# Some 2-night runs of particular interest in 2026
key_runs_2026 = [p for p in pair_details if p["night1"].startswith("2026")]

run_stats = {
    "n_consecutive_pairs":      len(pair_details),
    "avg_repeat_rate_n1_to_n2": two_night_repeat_rate,
    "stdev_repeat_rate":        two_night_repeat_stdev,
    "min_repeat_rate":          min(overlaps) if overlaps else 0,
    "max_repeat_rate":          max(overlaps) if overlaps else 0,
    "pooled_repeat_rate":       pooled_repeat_rate,
    "pooled_n1_songs":          pooled_n1_total,
    "pooled_shared_songs":      pooled_shared,
    "n_pairs_with_any_repeat":  sum(1 for p in pair_details if p["shared"] > 0),
    "pairs":                    pair_details,
    "pairs_2026_only":          key_runs_2026,
}

# ---------------------------------------- set-position transition matrix (lite)
# For top 30 songs by career plays, the share of plays in each slot.
top30 = [s for s, _ in career_plays.most_common(30)]
transition_matrix = []
for s in top30:
    total = career_plays[s]
    if total == 0: continue
    transition_matrix.append({
        "song": s,
        "career_plays": total,
        "share_set1":   set1_plays[s]   / total,
        "share_set2":   set2_plays[s]   / total,
        "share_encore": encore_plays[s] / total,
        "share_opener": opener_count[s] / total,
        "share_set1_closer": set1_closer_cnt[s] / total,
        "share_set2_opener": set2_opener_cnt[s] / total,
        "share_set2_closer": set2_closer_cnt[s] / total,
    })

# ---------------------------------------- rotation rates (top-30 blend)
def _rate(sub_dates):
    c = Counter()
    for d in sub_dates:
        for s in _songset(d):
            c[s] += 1
    return {s: n / len(sub_dates) for s, n in c.items()} if sub_dates else {}

d_2026 = [d for d in dates if d.startswith("2026")]
rate_2026 = _rate(d_2026)
rate_last50 = _rate(last50_dates)
rate_last20 = _rate(last20_dates)

# Blended rate per the reference model: 55% on 2026, 45% on last 50.
all_recent_songs = set(rate_2026) | set(rate_last50)
blend = {s: 0.55 * rate_2026.get(s, 0) + 0.45 * rate_last50.get(s, 0) for s in all_recent_songs}
blend_ranked = sorted(blend.items(), key=lambda kv: -kv[1])

rotation = {
    "n_2026_shows": len(d_2026),
    "n_last50":     len(last50_dates),
    "n_last20":     len(last20_dates),
    "window_avg_unique_songs": sum(blend.values()),
    "top_50_blended": [
        {"name": s, "blended_rate": v,
         "rate_2026": rate_2026.get(s, 0),
         "rate_last50": rate_last50.get(s, 0),
         "rate_last20": rate_last20.get(s, 0)}
        for s, v in blend_ranked[:50]
    ],
}

# ---------------------------------------- bustout candidates
# Career staples (>=10 career plays) currently absent for >=15 shows.
bustouts = []
for s, gap in gap_shows.items():
    if career_plays[s] >= 10 and gap >= 15:
        bustouts.append({
            "name": s, "career_plays": career_plays[s], "gap_shows": gap,
            "last_played": last_played[s]
        })
bustouts.sort(key=lambda x: (-x["gap_shows"], -x["career_plays"]))
bustouts = bustouts[:30]

# ---------------------------------------- show list (per-show summary)
show_summary = []
for d in dates:
    by = _by_slot(d)
    r0 = shows[d][0]
    rs = _real(d)
    has_s1 = bool(by.get("1"))
    has_s2 = bool(by.get("2"))
    has_enc = any(str(k).startswith("e") for k in by)
    form = "two_set" if has_s1 and has_s2 else ("one_set" if has_s1 and not has_s2 else "other")
    show_summary.append({
        "date":     d,
        "venue":    r0.get("venuename") or "",
        "city":     r0.get("city") or "",
        "state":    r0.get("state") or "",
        "country":  r0.get("country") or "",
        "songs":    [r["songname"] for r in sorted(rs, key=lambda x: (str(x["setnumber"]), x["position"]))],
        "n_songs":  len(_songset(d)),
        "n_covers": show_n_covers(d),
        "set1_len": len(by.get("1", [])),
        "set2_len": len(by.get("2", [])),
        "encore_len": sum(len(v) for k, v in by.items() if str(k).startswith("e")),
        "form":     form,
        "has_encore": has_enc,
    })

# ---------------------------------------- 2026 debuts list
debuts_2026 = [
    {"name": s, "first_played": first_played[s], "plays_2026": plays_2026[s]}
    for s in first_played if first_played[s].startswith("2026")
]
debuts_2025 = [
    {"name": s, "first_played": first_played[s], "plays_2025": plays_2025[s], "plays_2026": plays_2026[s]}
    for s in first_played if first_played[s].startswith("2025")
]
debuts_2026.sort(key=lambda x: x["first_played"])
debuts_2025.sort(key=lambda x: x["first_played"])

# Returns / rotation-back-in: songs that DID play in 2026 but whose previous
# play was >= 100 shows earlier (effectively "returned after a long absence").
# These over-index too — the model may want to boost them.
returns_2026 = []
for s in plays_2026:
    if plays_2026[s] == 0:
        continue
    # find first 2026 show, then previous play before it
    s_dates = sorted([d for d in dates if s in _songset(d)])
    first_2026 = next((d for d in s_dates if d.startswith("2026")), None)
    if not first_2026:
        continue
    prior = [d for d in s_dates if d < first_2026]
    if not prior:
        continue  # actual debut, already in debuts_2026
    last_prior = prior[-1]
    idx_first_2026 = date_to_idx[first_2026]
    idx_last_prior = date_to_idx[last_prior]
    show_gap_at_return = idx_first_2026 - idx_last_prior - 1
    if show_gap_at_return >= 50:
        returns_2026.append({
            "name": s,
            "first_2026_play": first_2026,
            "previous_play": last_prior,
            "show_gap_at_return": show_gap_at_return,
            "plays_2026": plays_2026[s],
            "career_plays": career_plays[s],
        })
returns_2026.sort(key=lambda x: -x["show_gap_at_return"])

# ---------------------------------------- final write
out = {
    "generated_at":  TODAY,
    "data_source":   "El Goose API (v2) — https://elgoose.net/api/v2/setlists/showyear/{YYYY}.json",
    "years_loaded":  YEARS,
    "n_total_songs": len(ALL_SONGS),
    "show_stats":    show_stats,
    "length_hist":   length_hist,
    "rotation":      rotation,
    "cover_stats":   cover_stats,
    "two_night_run_stats": run_stats,
    "set_position_matrix_top30": transition_matrix,
    "bustout_candidates": bustouts,
    "debuts_2026":   debuts_2026,
    "debuts_2025":   debuts_2025,
    "returns_2026":  returns_2026,
    "songs":         song_stats,
    "shows":         show_summary,
}

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# ---------------------------------------- console summary
print(f"Wrote {OUT_FILE}")
print(f"  Total shows: {N_SHOWS}")
print(f"  Date range:  {dates[0]} -> {dates[-1]}")
print(f"  Unique songs: {len(ALL_SONGS)}")
print(f"  Avg songs/show all-time: {show_stats['avg_songs_all']:.2f} (stdev {show_stats['stdev_songs_all']:.2f})")
print(f"  Avg songs/show last 50:  {show_stats['avg_songs_last_50']:.2f} (stdev {show_stats['stdev_songs_last_50']:.2f})")
print(f"  Avg set1/set2/encore last 50 (two-set only): {show_stats['avg_set1_len_last50']:.2f} / {show_stats['avg_set2_len_last50']:.2f} / {show_stats['avg_encore_len_last50']:.2f}")
print(f"  Two-set shows: all={show_stats['two_set_shows_n_all']}, last50={show_stats['two_set_shows_n_last50']}")
print(f"  Cover-show rate last 50: {cover_stats['shows_with_cover_pct_last_50']:.1%} ({cover_shows_last50}/{len(last50_dates)})")
print(f"  Avg covers/show last 50: {avg_covers_show_50:.2f}")
print(f"  Top 10 blended rotators (recent):")
for s, v in blend_ranked[:10]:
    print(f"    {v*100:5.1f}%  {s}")
print(f"  2-night runs: n={len(pair_details)}, avg repeat rate N1-N2 = {two_night_repeat_rate:.1%} (stdev {two_night_repeat_stdev:.1%})")
print(f"  2026 debuts: {len(debuts_2026)}  (e.g., {[d['name'] for d in debuts_2026[:5]]})")
print(f"  Top 5 bustout candidates:")
for b in bustouts[:5]:
    print(f"    {b['name']}: gap {b['gap_shows']} shows, career {b['career_plays']} plays, last {b['last_played']}")
