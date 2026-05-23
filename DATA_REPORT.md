# Goose Setlist Data — DATA_REPORT

*Generated 2026-05-23. Source: El Goose public API (`https://elgoose.net/api/v2/setlists/showyear/{YYYY}.json`), filtered client-side for `artist == "Goose"`. Output: `stats.json` (564 KB).*

---

## 1. Pull summary

| Year | Shows | Songs (rows) |
|---:|---:|---:|
| 2018 | 59  | 536  |
| 2019 | 81  | 958  |
| 2020 | 47  | 463  |
| 2021 | 45  | 580  |
| 2022 | 85  | 1006 |
| 2023 | 83  | 1004 |
| 2024 | 70  | 968  |
| 2025 | 62  | 795  |
| 2026 | 18  | 244  |
| **Total** | **550** | **6,554** |

- **Date range:** 2018-01-13 → 2026-05-22 (London Electric Brixton).
- **Unique songs in catalogue (over the window):** 323.
- **Shows in the 2024–2026 window:** **150** — matches the reference agent's claim exactly.
- Per-year files written to `data/goose{YYYY}.json` (the format `build_pages.py` expects).

The El Goose v2 API does not honour `artist=Goose` as a query parameter on the year endpoint, so the full per-year dump was downloaded and filtered client-side. The v1 endpoint at `setlists?artist=Goose&year=...` returns a generic schema with `showdate=null`, so v2 is the correct source.

---

## 2. Reference cross-check

| Reference claim | Computed | Status |
|---|---|---|
| 150 shows in 2024–2026 window | 150 | match |
| Avg ~12.9 songs/show recent | 12.54 (last 50) | within 3% — match |
| ~88% of shows have a cover | 88.0% (44/50, last 50) | match exactly |
| Give It Time 30% top rotator | 29.7% | match |
| Animal 27% | 27.0% | match |
| Hungersite 27% | 26.6% | match |
| Your Direction 25% | 25.2% | match |
| So Ready 24% | 24.3% | match |
| 2026 debuts listed: 7 songs | 3 true debuts; the other 4 are *returns after long absence*, not debuts | clarified |

The reference's "2026 debuts" list conflated true debuts (first-ever play) with **rotation returns** (songs that had played in earlier years and were rotated back in 2026 after a long gap). The corrected breakdown:

- **True 2026 debuts (3):** Good2B, Cortez The Killer, Hey Joe.
- **2026 returns after a ≥50-show absence (14):** Kung Fu Fighting (466-show gap), Movin' Out (325), One More Saturday Night (300), U.S. Blues (175), It Burns Within (117), Cantaloupe Island (97), Arise (86), Atlantic City (85), Not Alone (83), Peggy-O (78), True Love Waits (53), Doc Brown (51), Lead the Way (51), Caution (50).

Both lists are exposed as `debuts_2026` and `returns_2026` in `stats.json` for the model to over-index appropriately.

---

## 3. Top 30 songs by blended rotation rate (55% × 2026, 45% × last 50)

| # | Blended | 2026 | Last 50 | Song |
|---:|---:|---:|---:|---|
| 1  | 29.7% | 28% | 32% | Give It Time |
| 2  | 27.0% | 28% | 26% | Animal |
| 3  | 26.6% | 22% | 32% | Hungersite |
| 4  | 25.2% | 28% | 22% | Your Direction |
| 5  | 24.3% | 28% | 20% | So Ready |
| 6  | 23.9% | 22% | 26% | Big Modern! |
| 7  | 23.9% | 22% | 26% | Thatch |
| 8  | 23.0% | 22% | 24% | Rockdale |
| 9  | 23.0% | 22% | 24% | Dustin Hoffman |
| 10 | 21.2% | 22% | 20% | Creatures |
| 11 | 21.2% | 22% | 20% | Arcadia |
| 12 | 21.2% | 22% | 20% | Jed Stone |
| 13 | 20.3% | 22% | 18% | Madalena |
| 14 | 20.3% | 22% | 18% | Echo of a Rose |
| 15 | 20.3% | 22% | 18% | Madhuvan |
| 16 | 20.0% | 17% | 24% | Silver Rising |
| 17 | 19.4% | 22% | 16% | Borne |
| 18 | 19.1% | 17% | 22% | Hot Tea |
| 19 | 18.2% | 17% | 20% | Royal |
| 20 | 18.2% | 17% | 20% | Flodown |
| 21 | 17.3% | 17% | 18% | Dripfield |
| 22 | 17.3% | 17% | 18% | The Empress Of Organos |
| 23 | 17.3% | 17% | 18% | Hot Love & The Lazy Poet |
| 24 | 16.4% | 17% | 16% | Drive |
| 25 | 16.4% | 17% | 16% | MEDIA |
| 26 | 16.4% | 17% | 16% | Atlas Dogs |
| 27 | 16.4% | 17% | 16% | Arrow |
| 28 | 15.8% | 22% |  8% | Good2B |
| 29 | 15.5% | 17% | 14% | Pancakes |
| 30 | 15.5% | 17% | 14% | Yeti |

Window-sum (Σ blended) = **12.97 songs** — this is the expected number of unique songs in a draw from the rotation distribution and matches the empirical 12.54 ± 3.47 songs/show from the last 50.

---

## 4. Top 10 covers (career plays)

| # | Plays | Last played | Last 50 | Song (original artist) |
|---:|---:|---|---:|---|
| 1 | 44 | 2026-04-23 | 6 | Shama Lama Ding Dong (Otis Day and The Knights) |
| 2 | 43 | 2026-05-22 | 3 | Turn On Your Love Light (Bobby "Blue" Bland) |
| 3 | 41 | 2026-04-15 | 1 | The Way It Is (Bruce Hornsby) |
| 4 | 41 | 2026-05-07 | 3 | Electric Avenue (Eddy Grant) |
| 5 | 33 | 2025-09-14 | 1 | Atlas (The Wood Brothers) |
| 6 | 33 | 2026-04-10 | 4 | Don't Do It (The Band) |
| 7 | 30 | 2026-04-21 | 2 | Mississippi Half-Step Uptown Toodeloo (Grateful Dead) |
| 8 | 30 | 2026-04-14 | 2 | Green River (CCR) |
| 9 | 30 | 2026-04-12 | 4 | Fish In The Sea (Fat Freddy's Drop) |
| 10 | 29 | 2022-12-18 | 0 | Disco Inferno (The Trammps) — **bustout candidate** |

---

## 5. Consecutive-night repeat rate (the critical Bayesian prior)

**n = 105 two-night same-venue pairs across 2018–2026.**

| Metric | Value |
|---|---|
| Pooled repeat rate (Σ shared / Σ N1 songs) | **0.89%** (12 / 1350) |
| Mean of per-pair repeat rates | 0.80% |
| Stdev of per-pair repeat rates | 2.5% |
| Pairs with ≥1 repeated song | 11 of 105 (10.5%) |
| Max single-pair overlap | 2 songs (2025-05-27/28 Masonic) |
| **2026 pairs (n=4): Fort Lauderdale 4/14–15, St. Augustine 4/18–19, NOLA 4/21–22, Cabo 5/8–9** | **0 / 0 / 0 / 0 shared songs** |

**Interpretation:** Goose's no-repeat-across-consecutive-nights-at-the-same-venue policy is **extremely strict**. The empirical prior is:

> P(song S on N2 | S on N1, same-venue 2-night run) ≈ 1% (with 95% CI roughly [0.4%, 1.5%] under a Beta-Binomial posterior).

The model should treat this as a **near-zero conditional repeat probability**, far below any rotation-rate prior. For non-consecutive 2-night runs (e.g., the 4/12 Orlando → 4/14 Fort Lauderdale gap of 1 off-night) the constraint is weaker, but those aren't included in the 105-pair sample.

---

## 6. Show length distribution

### Avg unique songs/show

| Window | Mean | Stdev | Min | Max |
|---|---:|---:|---:|---:|
| All shows (n=550) | 11.57 | 3.80 | 1 | 27 |
| Last 50 | **12.54** | 3.47 | 6 | 26 |
| Last 20 | 13.30 | 2.66 | 9 | 19 |

### Two-set show segment lengths (last 50, n=39)

| Segment | Mean | Stdev | Min | Max |
|---|---:|---:|---:|---:|
| Set 1 | 7.77 | 1.74 | 4 | 12 |
| Set 2 | 5.44 | 1.50 | 2 | 9 |
| Encore | 1.08 | 0.42 | 0 | 2 |

### Show-length histogram (last 50, bucket = ≤ edge)

| ≤10 | ≤12 | ≤14 | ≤16 | ≤18 | ≤20 | >20 |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 9 | 17 | 10 | 3 | 1 | 0 |

≈75% of recent shows land in the 11–16 songs range, with a long left tail (single-set / festival sets) and a thin right tail (marquee NYE/MSG-style nights).

---

## 7. Bustout candidates (career staples on the longest current gaps)

These are songs with **≥10 career plays** that have been absent for **≥15 shows**, sorted by gap.

| # | Song | Gap (shows) | Career plays | Last played |
|---:|---|---:|---:|---|
| 1 | Feeling Hot Hot Hot | 417 | 14 | 2019-12-06 |
| 2 | Me and Julio Down By The Schoolyard | 281 | 21 | 2022-06-12 |
| 3 | Ghostbusters Rap | 250 | 20 | 2022-10-14 |
| 4 | Disco Inferno | 235 | 29 | 2022-12-18 |
| 5 | Crosseyed & Painless | 235 | 28 | 2022-12-18 |
| 6 | The Star-Spangled Banner | 184 | 12 | 2023-07-04 |
| 7 | Andale | 152 | 18 | 2024-01-30 |
| 8 | Whoever's In New England | 142 | 11 | 2024-02-29 |
| 9 | Tumble in the Wind | 133 | 30 | 2024-04-12 |
| 10 | Black Magic Woman | 133 | 13 | 2024-04-12 |

Full top-30 list in `stats.json → bustout_candidates`.

The reference's claim about **White Lights (31-show gap)** and **Indian River (25-show gap)** is consistent — neither is in the top 10 above because longer-dormant covers (Disco Inferno, Crosseyed & Painless, Feeling Hot Hot Hot) take precedence purely by gap size. The model can re-weight by genre/originality preference when picking bustouts.

---

## 8. Per-song deliverable in stats.json

The `songs[]` array contains the **top 200 songs by career plays**, each with these fields the prediction model can consume directly:

```
name, is_original, career_plays,
plays_2024, plays_2025, plays_2026,
plays_last_50, plays_last_20,
first_played_date, last_played_date, gap_shows,
is_2026_debut, is_2025_debut,
set1_plays, set2_plays, set3_plays, encore_plays,
opener_count, set1_closer_count, set2_opener_count,
set2_closer_count, encore_count
```

This lets the model compute per-song probabilities conditioned on slot (set 1 opener vs. set 2 closer vs. encore) without re-parsing raw data.

---

## 9. Set-position transition matrix (top 30 by career plays)

`stats.json → set_position_matrix_top30` gives, for each of the top-30 most-played songs, the share of its career plays that landed in each role:

```
share_set1, share_set2, share_encore,
share_opener, share_set1_closer,
share_set2_opener, share_set2_closer
```

Example (Hungersite): 41/40/0 set-1/set-2/encore plays → 50% set 1 / 49% set 2 — but as a slot-specific role it's a strong **set-2 opener** (15 set-2-opens / 82 career plays = 18%), confirming the reference's "set-2 launch pad" classification.

---

## 10. Data quality issues observed

1. **HTML entities in venue names.** Several venues come back with `&amp;` (`"BRYAC Black Rock &amp; Tackle"`, `"North Charleston Coliseum &amp; Performing Arts Center"`). Not problematic for the model but cosmetic — downstream HTML renderers should pass through, not double-encode.
2. **Non-ASCII characters in legacy footnotes.** Some 2018-era rows have mojibake (`Pi�a Colada`, `Götterdämmerung`-style); the prediction model doesn't read footnotes, but anyone surfacing them in UI needs to handle Latin-1 corruption.
3. **Soundcheck rows: absent.** The defensive filter for `settype != Soundcheck` is in place but didn't fire — El Goose's data either doesn't tag Goose soundchecks, or they're filtered upstream.
4. **2018-era shows occasionally have only `setnumber=1` for what was clearly a two-set night.** This means early-career segment-length means are noisier than recent. Mitigation: the model uses `last_50` and `last_20` windows where structure is consistent.
5. **`settype == "One Set"`** is used for festival/short sets (189 rows). These don't have a `2` setnumber and therefore aren't included in the two-set segment-length statistics; they're still in the show-length distribution.
6. **Movin' Out punctuation variants.** Only `"Movin' Out (Anthony's Song)"` appears; the reference's reference to bare `"Movin' Out"` was just a casual reference.
7. **Cover/original consistency.** All 323 unique songs have a deterministic `isoriginal` value (no song appears as both original and cover across rows); the majority-vote logic is defensive but unnecessary in practice.

---

## 11. Files produced

| Path | Purpose |
|---|---|
| `data/goose{2018..2026}.json` | Raw per-year setlist data (Goose-only), `{"data": [...]}` schema matching `ref/build_pages.py`. |
| `compute_stats.py` | The script that builds `stats.json`. Re-runnable. |
| `stats.json` | 564 KB machine-readable dataset for the prediction model. Schema in §8 and inline in the file. |
| `DATA_REPORT.md` | This document. |

---

## 12. How to refresh

```
cd C:\Users\jon.fox\Documents\goose
# (1) pull data — only needed if there are new shows
for y in 2018 2019 2020 2021 2022 2023 2024 2025 2026; do
  curl -s "https://elgoose.net/api/v2/setlists/showyear/$y.json" -o "data/year_$y.json"
done
# then filter (see compute_stats.py for the artist filter pattern)

# (2) recompute
python compute_stats.py
```

The script is fully deterministic and idempotent given the same input.
