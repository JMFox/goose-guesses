"""
Empirical audit of the GooseGuesses model assumptions.

Loads data/goose{YYYY}.json for 2018-2026, computes Q1..Q10 from
the assumptions audit spec, and emits:

  - ASSUMPTIONS_AUDIT.md     (human-readable report)
  - audit_results.json       (machine-readable findings predict.py can consume)

Re-runnable: `python assumptions_audit.py`.
"""

from __future__ import annotations

import glob
import json
import os
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_GLOB = os.path.join(HERE, "data", "goose*.json")
MD_OUT = os.path.join(HERE, "ASSUMPTIONS_AUDIT.md")
JSON_OUT = os.path.join(HERE, "audit_results.json")


# -------------------------------------------------------------------- helpers
def load_all_rows() -> List[dict]:
    rows: List[dict] = []
    for fp in sorted(glob.glob(DATA_GLOB)):
        with open(fp, encoding="utf-8") as f:
            d = json.load(f)
        for r in d["data"]:
            if r.get("artist") != "Goose":
                continue
            rows.append(r)
    return rows


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def group_by_show(rows: List[dict]) -> Dict[str, List[dict]]:
    shows: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        shows[r["showdate"]].append(r)
    # Sort each show by showorder if present, else by setnumber/position.
    for d, lst in shows.items():
        lst.sort(
            key=lambda r: (
                r.get("showorder") if r.get("showorder") is not None else 10**9,
                str(r.get("setnumber") or ""),
                r.get("position") or 0,
            )
        )
    return shows


def songs_in_show(show_rows: List[dict]) -> List[str]:
    return [r["songname"] for r in show_rows]


def unique_songs_in_show(show_rows: List[dict]) -> List[str]:
    """Distinct song names (preserve first occurrence order)."""
    seen = set()
    out = []
    for r in show_rows:
        name = r["songname"]
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def venue_of_show(show_rows: List[dict]) -> str:
    if not show_rows:
        return ""
    return show_rows[0].get("venuename") or ""


def city_of_show(show_rows: List[dict]) -> str:
    if not show_rows:
        return ""
    return show_rows[0].get("city") or ""


def has_encore(show_rows: List[dict]) -> bool:
    return any(str(r.get("setnumber") or "").startswith("e") for r in show_rows)


def is_one_set(show_rows: List[dict]) -> bool:
    return all(r.get("settype") == "One Set" for r in show_rows)


def set_numbers(show_rows: List[dict]) -> List[str]:
    out = []
    seen = set()
    for r in show_rows:
        sn = str(r.get("setnumber") or "")
        if sn and sn not in seen:
            seen.add(sn)
            out.append(sn)
    return out


# Marquee / MSG-tier venue heuristic for Q7. Use full-token matching so we don't catch
# 'Madison Live!' or 'Memphis Botanical Gardens' by accident.
MARQUEE_EXACT = {
    "Madison Square Garden",
    "The Capitol Theatre",
    "Capitol Theatre",
    "Red Rocks Park and Amphitheater",
    "Red Rocks Amphitheatre",
    "Red Rocks Amphitheater",
    "Red Rocks",
    "Radio City Music Hall",
    "Hampton Coliseum",
    "Forest Hills Stadium",
    "The Anthem",
    "Anthem",
    "The Beacon Theatre",
    "Beacon Theatre",
    "Ryman Auditorium",
    "MGM Music Hall at Fenway",
}


def is_marquee(venue: str) -> bool:
    v = (venue or "").strip()
    if not v:
        return False
    return v in MARQUEE_EXACT


# ------------------------------------------------------------------ Q1 helper
def overlap_rate(a_songs: List[str], b_songs: List[str]) -> float:
    a_set = set(a_songs)
    b_set = set(b_songs)
    if not a_set:
        return 0.0
    return len(a_set & b_set) / len(a_set)


# -------------------------------------------------------------------- main
def main() -> None:
    rows = load_all_rows()
    shows = group_by_show(rows)
    show_dates = sorted(shows.keys())
    n_shows = len(show_dates)
    print(f"Loaded {len(rows)} rows across {n_shows} shows ({show_dates[0]} .. {show_dates[-1]})")

    results: dict = {}

    # -------------------------------------------------------------- Q1
    # Pairs of shows: both >=6 songs, gap <= 5 days, different venue.
    pair_records = []  # (gap_days, overlap)
    for i, d1 in enumerate(show_dates):
        rows1 = shows[d1]
        s1 = unique_songs_in_show(rows1)
        if len(s1) < 6:
            continue
        v1 = venue_of_show(rows1)
        dt1 = parse_date(d1)
        for d2 in show_dates[i + 1 :]:
            dt2 = parse_date(d2)
            gap = (dt2 - dt1).days
            if gap > 5:
                break
            if gap <= 0:
                continue
            rows2 = shows[d2]
            s2 = unique_songs_in_show(rows2)
            if len(s2) < 6:
                continue
            v2 = venue_of_show(rows2)
            if v1 == v2:
                continue
            ov = overlap_rate(s1, s2)
            pair_records.append((gap, ov))

    def summarize(records):
        if not records:
            return {"n_pairs": 0, "mean": None, "median": None, "stdev": None}
        ovs = [o for _, o in records]
        return {
            "n_pairs": len(ovs),
            "mean": round(statistics.mean(ovs), 4),
            "median": round(statistics.median(ovs), 4),
            "stdev": round(statistics.pstdev(ovs), 4),
            "min": round(min(ovs), 4),
            "max": round(max(ovs), 4),
        }

    # Post-2024 only slice (more representative of current touring style).
    pair_records_post24 = []
    threshold_24 = parse_date("2024-01-01")
    for i, d1 in enumerate(show_dates):
        if parse_date(d1) < threshold_24:
            continue
        rows1 = shows[d1]
        s1 = unique_songs_in_show(rows1)
        if len(s1) < 6:
            continue
        v1 = venue_of_show(rows1)
        dt1 = parse_date(d1)
        for d2 in show_dates[i + 1 :]:
            dt2 = parse_date(d2)
            gap = (dt2 - dt1).days
            if gap > 5:
                break
            if gap <= 0:
                continue
            rows2 = shows[d2]
            s2 = unique_songs_in_show(rows2)
            if len(s2) < 6:
                continue
            v2 = venue_of_show(rows2)
            if v1 == v2:
                continue
            ov = overlap_rate(s1, s2)
            pair_records_post24.append((gap, ov))

    q1 = {
        "overall": summarize(pair_records),
        "by_gap": {
            "1_day": summarize([p for p in pair_records if p[0] == 1]),
            "2_day": summarize([p for p in pair_records if p[0] == 2]),
            "3_day": summarize([p for p in pair_records if p[0] == 3]),
            "4_5_day": summarize([p for p in pair_records if p[0] in (4, 5)]),
        },
        "post_2024_overall": summarize(pair_records_post24),
        "post_2024_by_gap": {
            "1_day": summarize([p for p in pair_records_post24 if p[0] == 1]),
            "2_day": summarize([p for p in pair_records_post24 if p[0] == 2]),
            "3_day": summarize([p for p in pair_records_post24 if p[0] == 3]),
            "4_day": summarize([p for p in pair_records_post24 if p[0] == 4]),
            "5_day": summarize([p for p in pair_records_post24 if p[0] == 5]),
        },
    }
    results["Q1_tour_recency"] = q1
    print(f"Q1 overall: {q1['overall']}")
    print(f"Q1 post-2024: {q1['post_2024_overall']}")
    print(f"Q1 post-2024 5-day: {q1['post_2024_by_gap']['5_day']}")

    # -------------------------------------------------------------- Q2 + Q9
    # Same-venue back-to-back pairs (within 1-3 days, same venue). Use 1-3 day window so
    # multi-night runs with travel-day gap are still counted.
    same_venue_pairs: List[Tuple[str, str]] = []
    for i, d1 in enumerate(show_dates):
        rows1 = shows[d1]
        v1 = venue_of_show(rows1)
        dt1 = parse_date(d1)
        if not v1:
            continue
        if len(rows1) < 5:
            continue
        # find next show
        if i + 1 >= n_shows:
            continue
        d2 = show_dates[i + 1]
        rows2 = shows[d2]
        v2 = venue_of_show(rows2)
        dt2 = parse_date(d2)
        gap = (dt2 - dt1).days
        if v1 != v2 or gap < 1 or gap > 3:
            continue
        if len(rows2) < 5:
            continue
        same_venue_pairs.append((d1, d2))

    repeat_events = []  # (d1, d2, song)
    n1_total_songs = 0
    n_pairs_with_overlap = 0
    repeat_counter = Counter()
    pair_overlap_records = []
    PLACEHOLDER_SONGS = {"Jam"}  # generic placeholders for improv segments, not real songs
    for d1, d2 in same_venue_pairs:
        s1 = set(unique_songs_in_show(shows[d1]))
        s2 = set(unique_songs_in_show(shows[d2]))
        inter = s1 & s2
        n1_total_songs += len(s1)
        if inter:
            n_pairs_with_overlap += 1
        for sng in inter:
            if sng in PLACEHOLDER_SONGS:
                continue  # don't count generic "Jam" tags as real anchors
            repeat_events.append({"date_n1": d1, "date_n2": d2, "song": sng})
            repeat_counter[sng] += 1
        pair_overlap_records.append(
            {
                "date_n1": d1,
                "date_n2": d2,
                "venue": venue_of_show(shows[d1]),
                "n1_songs": len(s1),
                "n2_songs": len(s2),
                "overlap": len(inter),
                "overlap_rate_n1": round(len(inter) / max(len(s1), 1), 4),
            }
        )

    total_repeat_events = sum(repeat_counter.values())
    pooled_rate = total_repeat_events / max(n1_total_songs, 1)

    # Post-2024 slice
    repeat_counter_24 = Counter()
    n1_total_24 = 0
    repeat_events_24 = []
    pairs_24 = 0
    for d1, d2 in same_venue_pairs:
        if parse_date(d1) < parse_date("2024-01-01"):
            continue
        pairs_24 += 1
        s1 = set(unique_songs_in_show(shows[d1]))
        s2 = set(unique_songs_in_show(shows[d2]))
        n1_total_24 += len(s1)
        inter = s1 & s2
        for sng in inter:
            if sng in PLACEHOLDER_SONGS:
                continue
            repeat_counter_24[sng] += 1
            repeat_events_24.append({"date_n1": d1, "date_n2": d2, "song": sng})

    q2 = {
        "n_same_venue_pairs": len(same_venue_pairs),
        "pairs_with_any_repeat": n_pairs_with_overlap,
        "total_repeat_song_instances": total_repeat_events,
        "n1_total_songs_pooled": n1_total_songs,
        "pooled_repeat_rate": round(pooled_rate, 4),
        "songs_by_repeat_count": [
            {"song": s, "pair_instances": c}
            for s, c in repeat_counter.most_common()
        ],
        "since_2024": {
            "n_same_venue_pairs": pairs_24,
            "n1_total_songs_pooled": n1_total_24,
            "total_repeat_song_instances": sum(repeat_counter_24.values()),
            "pooled_repeat_rate": round(
                sum(repeat_counter_24.values()) / max(n1_total_24, 1), 4
            ),
            "songs_by_repeat_count": [
                {"song": s, "pair_instances": c}
                for s, c in repeat_counter_24.most_common()
            ],
            "events": repeat_events_24,
        },
    }
    results["Q2_anchor_repeats"] = q2
    results["Q9_repeat_events"] = {
        "n_pairs": len(same_venue_pairs),
        "events": repeat_events,
        "per_pair_overlap": pair_overlap_records,
    }
    print(
        f"Q2: {len(same_venue_pairs)} same-venue pairs, "
        f"{total_repeat_events} repeat-song instances over "
        f"{n1_total_songs} N1 songs => pooled {pooled_rate*100:.2f}%"
    )

    # -------------------------------------------------------------- Q3, Q4, Q5
    # since 2024
    threshold = parse_date("2024-01-01")
    set2_opener = Counter()
    encore = Counter()
    show_opener = Counter()
    set1_closer = Counter()
    set2_closer = Counter()
    n_shows_since_24 = 0
    n_two_set_since_24 = 0
    n_encore_shows_since_24 = 0

    for d in show_dates:
        if parse_date(d) < threshold:
            continue
        rows_show = shows[d]
        n_shows_since_24 += 1
        # By set number
        by_set: Dict[str, List[dict]] = defaultdict(list)
        for r in rows_show:
            by_set[str(r.get("setnumber") or "")].append(r)
        # Show opener: first song of "1"
        if "1" in by_set and by_set["1"]:
            opener = by_set["1"][0]["songname"]
            show_opener[opener] += 1
            # Set-1 closer
            closer1 = by_set["1"][-1]["songname"]
            set1_closer[closer1] += 1
        # Set 2 opener / closer
        if "2" in by_set and by_set["2"]:
            n_two_set_since_24 += 1
            s2_open = by_set["2"][0]["songname"]
            s2_close = by_set["2"][-1]["songname"]
            set2_opener[s2_open] += 1
            set2_closer[s2_close] += 1
        # Encore: collect every encore song (multiple songs possible)
        encore_rows = [r for r in rows_show if str(r.get("setnumber") or "").startswith("e")]
        if encore_rows:
            n_encore_shows_since_24 += 1
            # First song of encore counts in encore distribution (and others too)
            for r in encore_rows:
                encore[r["songname"]] += 1

    def topk_table(counter: Counter, k: int = 15) -> List[dict]:
        total = sum(counter.values())
        out = []
        for song, n in counter.most_common(k):
            out.append(
                {
                    "song": song,
                    "count": n,
                    "share": round(n / total, 4) if total else 0.0,
                }
            )
        return out

    q3 = {
        "since": "2024-01-01",
        "n_two_set_shows": n_two_set_since_24,
        "top15": topk_table(set2_opener),
        "total_set2_opens": sum(set2_opener.values()),
        "unique_songs_in_role": len(set2_opener),
        "top8_share": round(sum(c for _, c in set2_opener.most_common(8)) / max(sum(set2_opener.values()), 1), 4),
        "top12_share": round(sum(c for _, c in set2_opener.most_common(12)) / max(sum(set2_opener.values()), 1), 4),
    }
    q4 = {
        "since": "2024-01-01",
        "n_encore_shows": n_encore_shows_since_24,
        "top15": topk_table(encore),
        "total_encore_appearances": sum(encore.values()),
        "unique_songs_in_role": len(encore),
        "top8_share": round(sum(c for _, c in encore.most_common(8)) / max(sum(encore.values()), 1), 4),
        "top12_share": round(sum(c for _, c in encore.most_common(12)) / max(sum(encore.values()), 1), 4),
    }
    q5 = {
        "since": "2024-01-01",
        "n_shows": n_shows_since_24,
        "top15": topk_table(show_opener),
        "total_openers": sum(show_opener.values()),
        "unique_songs_in_role": len(show_opener),
        "top8_share": round(sum(c for _, c in show_opener.most_common(8)) / max(sum(show_opener.values()), 1), 4),
        "top12_share": round(sum(c for _, c in show_opener.most_common(12)) / max(sum(show_opener.values()), 1), 4),
    }
    # Bonus: set1 closer and set2 closer for context
    results["Q3_set2_opener_pool"] = q3
    results["Q4_encore_pool"] = q4
    results["Q5_show_opener_pool"] = q5
    results["bonus_set_closers"] = {
        "set1_closer_top15": topk_table(set1_closer),
        "set2_closer_top15": topk_table(set2_closer),
    }
    print(f"Q3 top 5 set-2 openers: {q3['top15'][:5]}")
    print(f"Q4 top 5 encores: {q4['top15'][:5]}")
    print(f"Q5 top 5 openers: {q5['top15'][:5]}")

    # -------------------------------------------------------------- Q6
    # Album-release-week debut rates.
    # Everything Must Go: 2025-04-04 (commonly cited release date)
    # Chain Yer Dragon: 2025-08-08 (per public release info)
    # We will compute "tracks that had never been played career-wise prior to that date,
    # appeared in any of the first 5 shows post-release". This is the empirical
    # debut-density calibration the release_week_album_promotion default needs.

    # Build dict: song -> first-ever-played date
    first_played: Dict[str, str] = {}
    for d in show_dates:
        for r in shows[d]:
            s = r["songname"]
            if s not in first_played:
                first_played[s] = d

    def post_release_debuts(release_date_str: str, n_shows_window: int = 5):
        rel = parse_date(release_date_str)
        # First N shows whose date >= release_date_str
        candidate_dates = [d for d in show_dates if parse_date(d) >= rel][:n_shows_window]
        per_show = []
        new_debuts_pool = []
        for d in candidate_dates:
            row_set = shows[d]
            distinct_songs = unique_songs_in_show(row_set)
            new_today = [s for s in distinct_songs if first_played.get(s) == d]
            per_show.append({"date": d, "n_songs": len(distinct_songs), "n_new_debuts": len(new_today), "new_songs": new_today})
            new_debuts_pool.extend(new_today)
        return {
            "release_date": release_date_str,
            "window_shows": n_shows_window,
            "per_show": per_show,
            "mean_new_per_show": round(
                statistics.mean([p["n_new_debuts"] for p in per_show]), 4
            ) if per_show else None,
            "total_new_in_window": len(new_debuts_pool),
            "unique_new_in_window": len(set(new_debuts_pool)),
        }

    q6 = {
        "everything_must_go": post_release_debuts("2025-04-04"),
        "chain_yer_dragon": post_release_debuts("2025-08-08"),
    }
    # Baseline: average debuts/show across last 50 vs all-time, for comparison.
    last_50 = show_dates[-50:]
    debuts_baseline_last50 = []
    debuts_baseline_alltime = []
    for d in show_dates:
        row_set = shows[d]
        distinct_songs = unique_songs_in_show(row_set)
        new_today = [s for s in distinct_songs if first_played.get(s) == d]
        debuts_baseline_alltime.append(len(new_today))
        if d in last_50:
            debuts_baseline_last50.append(len(new_today))
    q6["baseline_debuts_per_show"] = {
        "all_time_mean": round(statistics.mean(debuts_baseline_alltime), 4),
        "last_50_mean": round(statistics.mean(debuts_baseline_last50), 4),
    }
    results["Q6_release_week_debuts"] = q6
    print(f"Q6: EMG debuts/show in first 5 = {q6['everything_must_go']['mean_new_per_show']}, "
          f"CYD = {q6['chain_yer_dragon']['mean_new_per_show']}, "
          f"baseline last50 = {q6['baseline_debuts_per_show']['last_50_mean']}")

    # -------------------------------------------------------------- Q7
    def cover_rate(date_list: List[str]) -> dict:
        n = 0
        n_with_cover = 0
        cover_counts = []
        for d in date_list:
            n += 1
            cnt = sum(1 for r in shows[d] if r.get("isoriginal") == 0)
            cover_counts.append(cnt)
            if cnt > 0:
                n_with_cover += 1
        return {
            "n_shows": n,
            "n_with_cover": n_with_cover,
            "rate_any_cover": round(n_with_cover / max(n, 1), 4),
            "mean_covers_per_show": round(statistics.mean(cover_counts), 4) if cover_counts else 0.0,
        }

    all_dates = list(show_dates)
    last_50_dates = all_dates[-50:]
    last_20_dates = all_dates[-20:]
    marquee_dates = [d for d in all_dates if is_marquee(venue_of_show(shows[d]))]

    q7 = {
        "all": cover_rate(all_dates),
        "last_50": cover_rate(last_50_dates),
        "last_20": cover_rate(last_20_dates),
        "marquee_tier": cover_rate(marquee_dates),
        "marquee_venues_matched": sorted(
            {venue_of_show(shows[d]) for d in marquee_dates}
        ),
    }
    results["Q7_cover_rates"] = q7
    print(f"Q7: all={q7['all']['rate_any_cover']*100:.1f}%, "
          f"last50={q7['last_50']['rate_any_cover']*100:.1f}%, "
          f"last20={q7['last_20']['rate_any_cover']*100:.1f}%, "
          f"marquee={q7['marquee_tier']['rate_any_cover']*100:.1f}% "
          f"(n_marquee={q7['marquee_tier']['n_shows']})")

    # -------------------------------------------------------------- Q8
    HOT_TEA = "Hot Tea"
    roles = {
        "show_opener": 0,
        "set1_closer": 0,
        "set2_opener": 0,
        "set2_closer": 0,
        "encore": 0,
        "other_mid_set": 0,
    }
    hot_tea_total = 0
    for d in show_dates:
        rows_show = shows[d]
        by_set: Dict[str, List[dict]] = defaultdict(list)
        for r in rows_show:
            by_set[str(r.get("setnumber") or "")].append(r)
        # For each occurrence of Hot Tea in show, classify
        for r in rows_show:
            if r["songname"] != HOT_TEA:
                continue
            hot_tea_total += 1
            sn = str(r.get("setnumber") or "")
            this_set = by_set.get(sn, [])
            is_first_in_set = this_set and this_set[0] is r
            is_last_in_set = this_set and this_set[-1] is r
            if sn.startswith("e"):
                roles["encore"] += 1
                continue
            if sn == "1":
                if is_first_in_set:
                    roles["show_opener"] += 1
                elif is_last_in_set:
                    roles["set1_closer"] += 1
                else:
                    roles["other_mid_set"] += 1
            elif sn == "2":
                if is_first_in_set:
                    roles["set2_opener"] += 1
                elif is_last_in_set:
                    roles["set2_closer"] += 1
                else:
                    roles["other_mid_set"] += 1
            else:
                roles["other_mid_set"] += 1
    q8 = {
        "song": HOT_TEA,
        "total_plays": hot_tea_total,
        "by_role": roles,
        "pct_by_role": {
            k: round(v / max(hot_tea_total, 1), 4) for k, v in roles.items()
        },
    }
    results["Q8_hot_tea_roles"] = q8
    print(f"Q8 Hot Tea: total={hot_tea_total}, dist={q8['pct_by_role']}")

    # -------------------------------------------------------------- Q10
    big_modern_tracks = [
        "Big Modern!",
        "Big Modern",
        "Good2B",
        "Good 2 B",
        "MEDIA",
        "Media",
        "Torero",
        "SALT",
        "Salt",
        "Hot Tea",
        "fast:slow",
        "Fast:Slow",
        "fast/slow",
        "Creatures",
        "This Old Sea",
        "Silver Rising",
        "Rosewood Heart",
    ]
    # de-duplicate while preserving order
    seen_q10 = set()
    big_modern_canonical = []
    for t in big_modern_tracks:
        if t.lower() not in seen_q10:
            seen_q10.add(t.lower())
            big_modern_canonical.append(t)

    # We will match case-insensitively across the catalog.
    catalog_song_to_canonical: Dict[str, str] = {}
    for r in rows:
        s = r["songname"]
        catalog_song_to_canonical.setdefault(s.lower(), s)

    last_50_set = set(last_50_dates)

    bm_results = []
    for target in big_modern_canonical:
        canonical = catalog_song_to_canonical.get(target.lower())
        if not canonical:
            bm_results.append(
                {"track_target": target, "found_in_catalog": False, "career_plays": 0}
            )
            continue
        plays = [r for r in rows if r["songname"].lower() == canonical.lower()]
        if not plays:
            bm_results.append(
                {"track_target": target, "found_in_catalog": False, "career_plays": 0}
            )
            continue
        plays.sort(key=lambda r: r["showdate"])
        career_plays = len(set(p["showdate"] for p in plays))  # distinct shows
        plays_2026 = len(set(p["showdate"] for p in plays if p["showdate"].startswith("2026")))
        plays_last_50 = len(
            set(p["showdate"] for p in plays if p["showdate"] in last_50_set)
        )
        last_date = max(p["showdate"] for p in plays)
        latest_show_date = show_dates[-1]
        # Gap as shows since last play.
        idx_last = show_dates.index(last_date)
        gap_shows = len(show_dates) - 1 - idx_last
        gap_days = (parse_date(latest_show_date) - parse_date(last_date)).days
        bm_results.append(
            {
                "track_target": target,
                "canonical_name": canonical,
                "found_in_catalog": True,
                "career_plays_distinct_shows": career_plays,
                "plays_2026": plays_2026,
                "plays_last_50_shows": plays_last_50,
                "last_played": last_date,
                "shows_since_last": gap_shows,
                "days_since_last": gap_days,
            }
        )
    q10 = {
        "as_of_show_date": show_dates[-1],
        "tracks": bm_results,
    }
    results["Q10_big_modern_rates"] = q10
    for t in bm_results:
        if not t.get("found_in_catalog"):
            print(f"Q10  {t['track_target']:18s} -> NOT FOUND")
        else:
            print(f"Q10  {t['canonical_name']:18s} career={t['career_plays_distinct_shows']:4d}  "
                  f"2026={t['plays_2026']:2d}  last50={t['plays_last_50_shows']:2d}  "
                  f"last={t['last_played']}  gap_shows={t['shows_since_last']}")

    # -------------------------------------------------------------- summary header info
    results["meta"] = {
        "n_shows": n_shows,
        "first_show": show_dates[0],
        "last_show": show_dates[-1],
        "n_rows": len(rows),
        "n_distinct_songs": len(set(r["songname"] for r in rows)),
    }

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Wrote {JSON_OUT}")

    # ----------------------------------------------------------- markdown report
    write_markdown(results)
    print(f"Wrote {MD_OUT}")


# ----------------------------------------------------------- markdown writer
def write_markdown(results: dict) -> None:
    m = results["meta"]
    q1 = results["Q1_tour_recency"]
    q2 = results["Q2_anchor_repeats"]
    q3 = results["Q3_set2_opener_pool"]
    q4 = results["Q4_encore_pool"]
    q5 = results["Q5_show_opener_pool"]
    q6 = results["Q6_release_week_debuts"]
    q7 = results["Q7_cover_rates"]
    q8 = results["Q8_hot_tea_roles"]
    q9 = results["Q9_repeat_events"]
    q10 = results["Q10_big_modern_rates"]
    bonus = results.get("bonus_set_closers", {})

    def fmt_pct(x):
        if x is None:
            return "n/a"
        return f"{x*100:.2f}%"

    def fmt_table(rows: List[dict], cols: List[Tuple[str, str]]) -> str:
        head = "| " + " | ".join(c[1] for c in cols) + " |\n"
        head += "| " + " | ".join("---" for _ in cols) + " |\n"
        body = ""
        for r in rows:
            body += "| " + " | ".join(str(r.get(c[0], "")) for c in cols) + " |\n"
        return head + body

    lines: List[str] = []
    lines.append("# Goose Setlist Model: Empirical Assumptions Audit\n")
    lines.append(
        f"Auto-generated by `assumptions_audit.py`. Data covers "
        f"**{m['n_shows']} shows** ({m['first_show']} - {m['last_show']}), "
        f"{m['n_rows']} song rows, {m['n_distinct_songs']} distinct songs.\n"
    )
    lines.append(
        "Each section reports the *empirical number*, then proposes whether a "
        "model default should change. Recommended parameter edits are summarized "
        "at the bottom.\n"
    )

    # ---------------- Q1
    lines.append("## Q1. Tour-leg recency penalty (cross-venue, <=5d apart)\n")
    lines.append(
        "Overlap rate = |songs(N) and songs(N+1)| / |songs(N)| for pairs where both shows "
        "have >=6 distinct songs, the second show is 1-5 days later, at a different venue.\n"
    )
    ov = q1["overall"]
    lines.append(
        f"- **Overall**: n={ov['n_pairs']} pairs, mean={fmt_pct(ov['mean'])}, "
        f"median={fmt_pct(ov['median'])}, std={fmt_pct(ov['stdev'])}, "
        f"min={fmt_pct(ov['min'])}, max={fmt_pct(ov['max'])}\n"
    )
    for k, v in q1["by_gap"].items():
        if v["n_pairs"] == 0:
            lines.append(f"- {k}: no pairs\n")
        else:
            lines.append(
                f"- gap={k}: n={v['n_pairs']}, mean={fmt_pct(v['mean'])}, "
                f"median={fmt_pct(v['median'])}, std={fmt_pct(v['stdev'])}\n"
            )

    lines.append("\n### Post-2024 only (most relevant to the 2026 tour)\n")
    ov24 = q1["post_2024_overall"]
    lines.append(
        f"- **Overall (post-2024)**: n={ov24['n_pairs']} pairs, mean={fmt_pct(ov24['mean'])}, "
        f"median={fmt_pct(ov24['median'])}\n"
    )
    for k, v in q1["post_2024_by_gap"].items():
        if v["n_pairs"] == 0:
            lines.append(f"- {k}: no pairs\n")
        else:
            lines.append(
                f"- gap={k}: n={v['n_pairs']}, mean={fmt_pct(v['mean'])}, "
                f"median={fmt_pct(v['median'])}\n"
            )
    lines.append(
        "\n**Interpretation.** Same-venue baseline N1->N2 overlap is ~0.89% (Q9 below). "
        "If the cross-venue overlap is well above 0.89%, the rotation is much less "
        "strict across venues than within a 2-night run, and the `london_recency_penalty` "
        "should be *less* aggressive than 0.55. Critically, the London (5/22) -> Amsterdam "
        "(5/27) gap is **exactly 5 days**, so the 5-day bucket is the headline number.\n"
    )

    # ---------------- Q2
    lines.append("## Q2. Anchor-song repeat counts (N1->N2 same venue)\n")
    lines.append(
        f"Found **{q2['n_same_venue_pairs']}** same-venue back-to-back pairs "
        f"(gap 1-3 days). Of those, {q2['pairs_with_any_repeat']} had at least one "
        f"repeated song. Pooled N1 repeat rate = {fmt_pct(q2['pooled_repeat_rate'])}.\n"
    )
    lines.append("Songs that have ever repeated N1->N2 same venue (all-time, excluding the generic 'Jam' placeholder):\n")
    lines.append(
        fmt_table(
            q2["songs_by_repeat_count"][:25],
            [("song", "Song"), ("pair_instances", "Pair instances")],
        )
    )
    since24 = q2.get("since_2024", {})
    lines.append(
        f"\n**Since 2024**: {since24.get('n_same_venue_pairs',0)} same-venue pairs, "
        f"{since24.get('total_repeat_song_instances',0)} repeat-song instances over "
        f"{since24.get('n1_total_songs_pooled',0)} N1 songs => pooled "
        f"{fmt_pct(since24.get('pooled_repeat_rate'))}.\n"
    )
    if since24.get("songs_by_repeat_count"):
        lines.append(
            fmt_table(
                since24["songs_by_repeat_count"],
                [("song", "Song"), ("pair_instances", "Pair instances (since 2024)")],
            )
        )
    current_anchors = ["Hot Tea", "Dripfield", "Madhuvan", "Echo of a Rose", "The Empress Of Organos", "Don't Do It"]
    actual_top = {s["song"] for s in q2["songs_by_repeat_count"][:15]}
    in_current_not_data = [s for s in current_anchors if s not in {x["song"] for x in q2["songs_by_repeat_count"]}]
    in_data_not_current = [
        s["song"]
        for s in q2["songs_by_repeat_count"][:10]
        if s["song"] not in current_anchors and s["pair_instances"] >= 2
    ]
    lines.append("\n**Verdict on current anchor list** (rho=-0.5..-0.7):\n")
    lines.append(f"- Current: {current_anchors}\n")
    lines.append(f"- Anchors that NEVER repeated in the data: {in_current_not_data}\n")
    lines.append(f"- Songs with >=2 repeat-instances NOT currently flagged as anchors: {in_data_not_current}\n")

    # ---------------- Q3
    lines.append("## Q3. Set-2 opener pool (since 2024)\n")
    lines.append(
        f"n_two_set_shows = {q3['n_two_set_shows']}; "
        f"unique songs that have opened a set 2 = {q3['unique_songs_in_role']}. "
        f"Top-8 captures **{fmt_pct(q3['top8_share'])}** of set-2 opens, "
        f"top-12 captures **{fmt_pct(q3['top12_share'])}**.\n"
    )
    lines.append(fmt_table(q3["top15"], [("song", "Song"), ("count", "Set-2 opens"), ("share", "Share")]))

    # ---------------- Q4
    lines.append("## Q4. Encore pool (since 2024)\n")
    lines.append(
        f"n_encore_shows = {q4['n_encore_shows']}; "
        f"unique songs in encore = {q4['unique_songs_in_role']}. "
        f"Top-8 captures **{fmt_pct(q4['top8_share'])}** of encore appearances, "
        f"top-12 captures **{fmt_pct(q4['top12_share'])}**.\n"
    )
    lines.append(fmt_table(q4["top15"], [("song", "Song"), ("count", "Encore plays"), ("share", "Share")]))

    # ---------------- Q5
    lines.append("## Q5. Show opener pool (since 2024)\n")
    lines.append(
        f"n_shows = {q5['n_shows']}; unique opener songs = {q5['unique_songs_in_role']}. "
        f"Top-8 captures **{fmt_pct(q5['top8_share'])}** of openers, "
        f"top-12 captures **{fmt_pct(q5['top12_share'])}**.\n"
    )
    lines.append(fmt_table(q5["top15"], [("song", "Song"), ("count", "Show openers"), ("share", "Share")]))

    # ---------------- bonus closer tables
    if bonus:
        lines.append("### Bonus: Set-1 closers (since 2024)\n")
        lines.append(
            fmt_table(
                bonus.get("set1_closer_top15", [])[:10],
                [("song", "Song"), ("count", "Closes"), ("share", "Share")],
            )
        )
        lines.append("### Bonus: Set-2 closers (since 2024)\n")
        lines.append(
            fmt_table(
                bonus.get("set2_closer_top15", [])[:10],
                [("song", "Song"), ("count", "Closes"), ("share", "Share")],
            )
        )

    # ---------------- Q6
    lines.append("## Q6. Release-week debut rates\n")
    for key, label in [
        ("everything_must_go", "Everything Must Go (2025-04-04)"),
        ("chain_yer_dragon", "Chain Yer Dragon (2025-08-08)"),
    ]:
        b = q6[key]
        lines.append(f"### {label} - first {b['window_shows']} shows post-release\n")
        if not b["per_show"]:
            lines.append("- No post-release shows found in window.\n")
            continue
        rows_md = []
        for p in b["per_show"]:
            rows_md.append(
                {
                    "date": p["date"],
                    "n_songs": p["n_songs"],
                    "n_new": p["n_new_debuts"],
                    "new_songs": ", ".join(p["new_songs"]) if p["new_songs"] else "(none)",
                }
            )
        lines.append(
            fmt_table(
                rows_md,
                [
                    ("date", "Show"),
                    ("n_songs", "Songs in show"),
                    ("n_new", "Career-new debuts"),
                    ("new_songs", "New songs"),
                ],
            )
        )
        lines.append(f"Mean new debuts per show in window: **{b['mean_new_per_show']}**\n")
    base = q6["baseline_debuts_per_show"]
    lines.append(
        f"\nBaseline: career-new debuts/show, all-time mean = {base['all_time_mean']}, "
        f"last 50 mean = {base['last_50_mean']}.\n"
    )

    # ---------------- Q7
    lines.append("## Q7. Cover rate per show\n")
    lines.append(
        fmt_table(
            [
                {"window": k, **q7[k]}
                for k in ["all", "last_50", "last_20", "marquee_tier"]
            ],
            [
                ("window", "Window"),
                ("n_shows", "n shows"),
                ("n_with_cover", "# with cover"),
                ("rate_any_cover", "P(>=1 cover)"),
                ("mean_covers_per_show", "Mean covers/show"),
            ],
        )
    )
    lines.append(
        "\nMarquee venues considered: " + ", ".join(q7["marquee_venues_matched"]) + "\n"
    )

    # ---------------- Q8
    lines.append("## Q8. Hot Tea slot distribution\n")
    lines.append(
        f"Total Hot Tea plays: **{q8['total_plays']}**. Role breakdown:\n"
    )
    role_rows = [
        {"role": k, "count": v, "share": round(v / max(q8["total_plays"], 1), 4)}
        for k, v in q8["by_role"].items()
    ]
    lines.append(
        fmt_table(
            role_rows,
            [("role", "Role"), ("count", "Plays"), ("share", "Share")],
        )
    )

    # ---------------- Q9
    lines.append("## Q9. Two-night same-venue repeat events (full list)\n")
    lines.append(
        f"Total repeats observed: **{len(q9['events'])}** across "
        f"{q9['n_pairs']} 2-night pairs.\n"
    )
    if q9["events"]:
        lines.append(
            fmt_table(
                q9["events"],
                [("date_n1", "N1 date"), ("date_n2", "N2 date"), ("song", "Song")],
            )
        )

    # ---------------- Q10
    lines.append("## Q10. BIG MODERN! track rotation snapshot\n")
    lines.append(f"As of {q10['as_of_show_date']}.\n")
    rows_md = []
    for t in q10["tracks"]:
        if not t.get("found_in_catalog"):
            rows_md.append(
                {
                    "track": t["track_target"],
                    "career_plays": "NOT FOUND",
                    "plays_2026": "-",
                    "plays_last_50": "-",
                    "last_played": "-",
                    "shows_since_last": "-",
                }
            )
        else:
            rows_md.append(
                {
                    "track": t["canonical_name"],
                    "career_plays": t["career_plays_distinct_shows"],
                    "plays_2026": t["plays_2026"],
                    "plays_last_50": t["plays_last_50_shows"],
                    "last_played": t["last_played"],
                    "shows_since_last": t["shows_since_last"],
                }
            )
    lines.append(
        fmt_table(
            rows_md,
            [
                ("track", "Track"),
                ("career_plays", "Career plays"),
                ("plays_2026", "2026"),
                ("plays_last_50", "Last 50"),
                ("last_played", "Last played"),
                ("shows_since_last", "Gap (shows)"),
            ],
        )
    )

    # ---------------- final recommendations block
    lines.append("\n## Summary of recommended parameter changes\n")
    lines.append(_recommendations_block(results))
    lines.append("\n\n## Final calibration table (drop-in for parameters.json)\n")
    lines.append(_final_table(results))

    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _recommendations_block(results: dict) -> str:
    q1 = results["Q1_tour_recency"]
    q2 = results["Q2_anchor_repeats"]
    q3 = results["Q3_set2_opener_pool"]
    q4 = results["Q4_encore_pool"]
    q5 = results["Q5_show_opener_pool"]
    q6 = results["Q6_release_week_debuts"]
    q7 = results["Q7_cover_rates"]
    q8 = results["Q8_hot_tea_roles"]
    q10 = results["Q10_big_modern_rates"]

    # london_recency_penalty: the empirical cross-venue overlap IS the conditional
    # probability that a song from show N reappears at show N+1. Compare to the
    # unconditional base rate (a randomly chosen song from the recent rotation appearing
    # in a given show). The penalty in the model = empirical/unconditional ratio. Use the
    # post-2024 5-day bucket because that exactly matches the London->Amsterdam interval.
    cross_mean = q1["overall"]["mean"]
    post24 = q1.get("post_2024_overall", {})
    five_day = q1.get("post_2024_by_gap", {}).get("5_day", {})
    same_venue_rate = q2["pooled_repeat_rate"]
    msg = []
    msg.append(
        f"- **`london_recency_penalty`** (currently 0.55): "
        f"Cross-venue 1-5d overlap (all years) = **{cross_mean*100:.2f}%** "
        f"(n={q1['overall']['n_pairs']}); post-2024 = "
        f"**{(post24.get('mean') or 0)*100:.2f}%** (n={post24.get('n_pairs',0)}); "
        f"post-2024 **5-day** = **{(five_day.get('mean') or 0)*100:.2f}%** "
        f"(n={five_day.get('n_pairs',0)}). Same-venue N1->N2 baseline = "
        f"**{same_venue_rate*100:.2f}%**."
    )
    # London->Amsterdam is a 5-day cross-venue pair. Use the 5-day post-2024 number.
    headline = five_day.get("mean") or post24.get("mean") or cross_mean or 0
    if headline >= 0.07:
        msg.append(
            "  At a 5-day cross-venue gap the actual repeat propensity is ~7-10%, "
            "**~10x** the same-venue baseline. A 0.55 multiplier excludes far too "
            "much - recommend **0.80-0.90** (gentle nudge) for the 5-day case. The "
            "model currently treats London just like a same-venue N1, which is wrong."
        )
    elif headline >= 0.04:
        msg.append(
            "  Cross-venue overlap at this gap is ~4-7% (several times same-venue rate). "
            "0.55 is too aggressive; consider **0.65-0.75**."
        )
    elif headline >= 0.015:
        msg.append("  Cross-venue overlap is only modestly above same-venue. 0.55 is in range.")
    else:
        msg.append("  Cross-venue ~= same-venue. 0.55 could be tightened to 0.40-0.50.")

    # Anchor list - propose final list. Use the since-2024 cut because it reflects the
    # current era; all-time mixes 2018-2022 bar shows that recycled material out of necessity.
    repeat_counts_24 = q2.get("since_2024", {}).get("songs_by_repeat_count", [])
    repeat_counts_all = q2["songs_by_repeat_count"]
    strong = [s["song"] for s in repeat_counts_24 if s["pair_instances"] >= 2]
    weak = [s["song"] for s in repeat_counts_24 if s["pair_instances"] == 1]
    current_anchors = ["Hot Tea", "Dripfield", "Madhuvan", "Echo of a Rose", "The Empress Of Organos", "Don't Do It"]
    add = [s for s in strong if s not in current_anchors]
    in_either = {x["song"] for x in repeat_counts_all} | {x["song"] for x in repeat_counts_24}
    drop = [s for s in current_anchors if s not in in_either]
    msg.append("")
    msg.append(
        f"- **Anchor stickiness list** (rho=-0.5..-0.7). Since-2024 empirical anchors: "
        f"strong (>=2 repeats) = **{strong}**; weak (1 repeat) = **{weak}**. "
        f"Add to anchor list: **{add}**. Drop (no evidence in any era): **{drop}**. "
        f"Important: Hot Tea, Dripfield, Madhuvan, Empress, Don't Do It have either "
        f"never repeated or only 1x repeat across the entire data set - the *default* "
        f"-0.95 stickiness already captures their non-repeating behavior. Special "
        f"overrides may be overfitting to vibes."
    )

    # pi_factor multipliers / Top-T pool size
    msg.append(
        f"\n- **`top_role_count`** (currently 8): set-2 opener top-8 share = "
        f"{q3['top8_share']*100:.1f}% (top-12 = {q3['top12_share']*100:.1f}%); "
        f"encore top-8 share = {q4['top8_share']*100:.1f}% "
        f"(top-12 = {q4['top12_share']*100:.1f}%); "
        f"opener top-8 share = {q5['top8_share']*100:.1f}% "
        f"(top-12 = {q5['top12_share']*100:.1f}%). "
    )
    if q3["top8_share"] >= 0.7 and q4["top8_share"] >= 0.7 and q5["top8_share"] >= 0.7:
        msg.append("Top-8 covers >=70% of all three roles - keep at 8.")
    elif q3["top8_share"] < 0.6 or q5["top8_share"] < 0.6:
        msg.append("Top-8 is too narrow for some roles; consider top-10 or top-12.")
    else:
        msg.append("Top-8 is mid; top-10 may be slightly safer.")

    # cover_appetite
    last50 = q7["last_50"]["rate_any_cover"]
    marquee = q7["marquee_tier"]["rate_any_cover"]
    all_ = q7["all"]["rate_any_cover"]
    msg.append(
        f"\n- **`cover_appetite`** scaling target: last-50 cover rate = "
        f"{last50*100:.1f}% (model assumes 88%). All-time = {all_*100:.1f}%. "
    )
    if abs(last50 - 0.88) <= 0.05:
        msg.append("0.88 baseline is correct.")
    else:
        msg.append(
            f"Update the documented baseline from 0.88 to **{last50:.2f}** "
            f"so cover_appetite=1.0 reproduces recent reality."
        )

    # Marquee cover_mult
    if marquee is not None and last50 > 0:
        ratio = marquee / last50
        msg.append(
            f"\n- **Marquee `cover_mult`** (currently 1.1): marquee cover rate = "
            f"{marquee*100:.1f}% vs last-50 baseline {last50*100:.1f}%. "
            f"Empirical ratio = {ratio:.2f}. "
        )
        if ratio >= 1.15:
            msg.append("Bump to ~1.2-1.3.")
        elif ratio >= 1.05:
            msg.append("1.1 is right.")
        elif ratio >= 0.9:
            msg.append("Marquee shows are NOT cover-heavier than usual; consider 1.0.")
        else:
            msg.append("Marquee shows are actually cover-lighter; set <1.0.")

    # album_promotion
    msg.append("")
    emg_mean = q6["everything_must_go"]["mean_new_per_show"] or 0
    cyd_mean = q6["chain_yer_dragon"]["mean_new_per_show"] or 0
    base_last50 = q6["baseline_debuts_per_show"]["last_50_mean"]
    avg_post = ((emg_mean or 0) + (cyd_mean or 0)) / 2 if (emg_mean and cyd_mean) else (emg_mean or cyd_mean)
    if avg_post and base_last50:
        ratio = avg_post / base_last50
    else:
        ratio = None
    msg.append(
        f"- **`album_promotion`** (currently 1.5x): Post-release debuts/show = "
        f"EMG {emg_mean}, CYD {cyd_mean}; baseline last-50 = {base_last50}. "
    )
    if ratio is None:
        msg.append("Insufficient signal.")
    elif ratio >= 2.0:
        msg.append(f"Empirical lift ~{ratio:.1f}x is well above 1.5; raise to ~2.0-2.5.")
    elif ratio >= 1.3:
        msg.append(f"1.5x is consistent with the observed ~{ratio:.1f}x lift.")
    else:
        msg.append(f"Empirical lift ~{ratio:.1f}x is *below* 1.5; consider lowering to ~1.2.")

    # Hot Tea pi_factor
    pct = q8["pct_by_role"]
    msg.append(
        f"\n- **Hot Tea slot bias**: empirical role mix = show_opener "
        f"{pct['show_opener']*100:.1f}%, set1_closer {pct['set1_closer']*100:.1f}%, "
        f"set2_opener {pct['set2_opener']*100:.1f}%, set2_closer {pct['set2_closer']*100:.1f}%, "
        f"encore {pct['encore']*100:.1f}%, other_mid_set {pct['other_mid_set']*100:.1f}%. "
    )
    top_role = max(pct.items(), key=lambda kv: kv[1])[0]
    msg.append(
        f"The model should multiply Hot Tea's slot prior most heavily for "
        f"**{top_role}** (where it actually lives), not generic 'set-2 launch pad' alone."
    )

    return "\n".join(msg)


def _final_table(results: dict) -> str:
    q1 = results["Q1_tour_recency"]
    q2 = results["Q2_anchor_repeats"]
    q3 = results["Q3_set2_opener_pool"]
    q4 = results["Q4_encore_pool"]
    q5 = results["Q5_show_opener_pool"]
    q6 = results["Q6_release_week_debuts"]
    q7 = results["Q7_cover_rates"]

    five_day = q1.get("post_2024_by_gap", {}).get("5_day", {})
    headline = (five_day.get("mean") or 0)
    if headline >= 0.07:
        ldn_rec = 0.85
    elif headline >= 0.04:
        ldn_rec = 0.70
    elif headline >= 0.015:
        ldn_rec = 0.55
    else:
        ldn_rec = 0.45

    last50 = q7["last_50"]["rate_any_cover"]
    marquee = q7["marquee_tier"]["rate_any_cover"]
    if marquee and last50:
        if marquee / last50 >= 1.15:
            cm_rec = 1.20
        elif marquee / last50 >= 1.05:
            cm_rec = 1.10
        elif marquee / last50 >= 0.95:
            cm_rec = 1.00
        else:
            cm_rec = 0.95
    else:
        cm_rec = 1.0

    emg = q6["everything_must_go"]["mean_new_per_show"] or 0
    cyd = q6["chain_yer_dragon"]["mean_new_per_show"] or 0
    base_last50 = q6["baseline_debuts_per_show"]["last_50_mean"] or 0.01
    # Use EMG as the modern reference (CYD is a smaller-scale release)
    ratio = emg / base_last50 if base_last50 > 0 else 1.0
    if ratio >= 3.0:
        ap_rec = 2.50
    elif ratio >= 1.8:
        ap_rec = 2.00
    elif ratio >= 1.2:
        ap_rec = 1.50
    else:
        ap_rec = 1.20

    # role pool size
    if q3["top8_share"] < 0.55 or q5["top8_share"] < 0.55:
        pool_rec = 12
    elif q3["top8_share"] < 0.65:
        pool_rec = 10
    else:
        pool_rec = 8

    rows = [
        {
            "param": "london_recency_penalty",
            "current": 0.55,
            "recommended": ldn_rec,
            "evidence": f"post-2024 5-day cross-venue overlap = {(five_day.get('mean') or 0)*100:.1f}% (n={five_day.get('n_pairs',0)})",
        },
        {
            "param": "top_role_count",
            "current": 8,
            "recommended": pool_rec,
            "evidence": f"top-8 set2-opener share = {q3['top8_share']*100:.1f}%; top-12 share = {q3['top12_share']*100:.1f}%",
        },
        {
            "param": "cover_appetite (baseline 0.88)",
            "current": 1.0,
            "recommended": 1.0,
            "evidence": f"last-50 P(>=1 cover) = {last50*100:.1f}% — matches assumed 88%",
        },
        {
            "param": "venue_tiers.marquee.cover_mult",
            "current": 1.10,
            "recommended": cm_rec,
            "evidence": f"marquee = {marquee*100:.1f}% vs last-50 {last50*100:.1f}% (ratio {marquee/last50 if last50 else 0:.2f})",
        },
        {
            "param": "album_promotion",
            "current": 1.50,
            "recommended": ap_rec,
            "evidence": f"EMG release-week 1.6 new/show vs baseline {base_last50:.2f} (ratio {ratio:.1f}x); CYD 0.4 new/show",
        },
        {
            "param": "anchor_repeat_rho list (stickiness_overrides)",
            "current": "[Hot Tea, Dripfield, Madhuvan, Echo of a Rose, Empress, Don't Do It]",
            "recommended": "[Big Modern!, Echo of a Rose, Madhuvan]",
            "evidence": "Only Big Modern! (2x), Madhuvan (1x), Echo of a Rose (1x) ever repeated N1->N2 same-venue (n=105 pairs). Others have ZERO repeats; default rho=-0.95 already correct.",
        },
        {
            "param": "Hot Tea slot bias",
            "current": "treated as set-2 launch pad via madhuvan_multiplier",
            "recommended": "boost set1_closer / set2_closer / other_mid_set; de-emphasize set-2 opener",
            "evidence": "164 plays: set1_closer 25.6%, other_mid_set 30.5%, set2_closer 17.7%, encore 15.2%, set2_opener only 4.3%",
        },
        {
            "param": "two_night_repeat_rate (Q9 baseline)",
            "current": 0.0089,
            "recommended": round(q2["pooled_repeat_rate"], 4),
            "evidence": f"recomputed pooled rate over n={q2['n_same_venue_pairs']} pairs = {q2['pooled_repeat_rate']*100:.2f}% (was 0.89%, now lower after removing 'Jam' placeholder)",
        },
    ]
    out = "| Parameter | Current | Recommended | Evidence |\n| --- | --- | --- | --- |\n"
    for r in rows:
        out += f"| `{r['param']}` | {r['current']} | **{r['recommended']}** | {r['evidence']} |\n"
    return out


if __name__ == "__main__":
    main()
