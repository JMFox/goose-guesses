# 🪿 GooseGuesses

Probabilistic setlist predictions for **Goose** at Amsterdam Melkweg (May 27 & 28, 2026) and Madison Square Garden (June 19 & 20, 2026).

**Live site:** [jmfox.github.io/goose-guesses](https://jmfox.github.io/goose-guesses/)

## What's in here

| Page | What it is |
|---|---|
| [`index.html`](index.html) | Landing page with all the cards |
| [`amsterdam.html`](amsterdam.html) | Both Amsterdam nights side-by-side |
| [`msg_n1.html`](msg_n1.html) | MSG Night 1 predictions |
| [`msg_n2.html`](msg_n2.html) | MSG Night 2 (Bayesian-conditioned on N1) |
| [`model.html`](model.html) | **Interactive forecasting model** with 20 tunable goose-themed parameters |
| [`methodology.html`](methodology.html) | Full math (MathJax) + parameter TL;DR |

## The model in one paragraph

For every song in the catalog we compute `p ∝ base_rate · gap_multiplier · set_position_fit · venue_aura · debut_factor · no_repeat_R`, then renormalize so the per-song probabilities sum to the expected show length (~11 for Amsterdam single sets, ~18 for MSG two-set + encore). For Night 2 shows we Bayesian-condition on Night 1's predicted plays — Goose's empirical 2-night repeat rate is **0.89%** across 105 historical pairs, so N1 songs effectively vanish from N2.

## Data

- **550 shows** from [El Goose](https://elgoose.net/) (2018-01-13 → 2026-05-22)
- **323 unique songs**
- **150 shows** in the 2024-2026 "recent" window (weighted higher in the base rate)

## Reproducing

```bash
python compute_stats.py        # builds stats.json from data/goose*.json
python predict.py              # writes predictions.json
python render_html.py          # writes index, amsterdam, msg_n1, msg_n2
python build_model_page.py     # writes model.html (interactive)
python build_methodology_page.py  # writes methodology.html
```

## Credits

- Setlist data: [El Goose](https://elgoose.net/) public v2 API
- Methodology adapted from Phish.net's [Trey's Notebook](https://phish.net/treys-notebook) and [Andrew Reed's Phish LSTM](https://github.com/andrewrreed/phish-setlist-modeling) (Brier ~0.040)
- Generated 2026-05-23
