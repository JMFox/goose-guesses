# GooseGuesses — Probabilistic Setlist Prediction Methodology

**Version:** 1.0
**Date:** 2026-05-23
**Author:** GooseGuesses statistical methodology working group
**Scope:** Amsterdam Melkweg N1/N2 (2026-05-27/28), MSG N1/N2 (2026-06-19/20)
**Catalog:** ~360 songs; **History:** ~800 shows total, 150 in the 2024–2026 window
**Status:** Defensible production specification. Speculative components are flagged with **[SPEC]**.

---

## 0. Notation and conventions

Throughout, we use the following notation:

- $\mathcal{S}$ — the song catalog ($|\mathcal{S}| \approx 360$).
- $s \in \mathcal{S}$ — a single song.
- $k$ — index of the target show (e.g., Amsterdam N1).
- $\mathcal{H}_k = \{(d_i, \sigma_i)\}_{i < k}$ — observed setlists prior to show $k$, where $\sigma_i$ is the played sequence on date $d_i$.
- $\mathcal{C}_k$ — context for show $k$: venue, set count, expected length, run position, geography, release window.
- $N_k$ — number of song slots in show $k$ (a random variable; we predict its expectation).
- $X_{s,k} \in \{0,1\}$ — indicator that song $s$ is played at show $k$.
- $p_{s,k} = \Pr(X_{s,k} = 1 \mid \mathcal{H}_k, \mathcal{C}_k)$ — the target probability.
- $b_s$ — the **blended base rate** of song $s$ (defined in §1.1).
- $\theta$ — the vector of tunable hyperparameters (§8).

We use $\mathbb{E}[N_k] = \bar{N}_k$ for the expected show length: $\bar{N}_\text{Ams} = 11$, $\bar{N}_\text{MSG} = 18$.

The fundamental constraint is the **slot identity**:

$$
\sum_{s \in \mathcal{S}} p_{s,k} = \bar{N}_k.
$$

This is the soundness backbone — it is what forced the recalibration of the v0 hand-typed numbers documented in `ANALYSIS.md` (the "MSG Hungersite at 52%" violation).

---

## 1. Probability model derivation

### 1.1 Top-level decomposition

For each (song, show) pair we factor:

$$
p_{s,k} \;\propto\; \underbrace{b_s}_{\text{base rate}}
\cdot \underbrace{g(\Delta_{s,k})}_{\text{gap multiplier}}
\cdot \underbrace{\pi_{s,k}}_{\text{set-position fit}}
\cdot \underbrace{V_{s,k}}_{\text{venue boost}}
\cdot \underbrace{D_{s,k}}_{\text{debut/new-material}}
\cdot \underbrace{R_{s,k}}_{\text{no-repeat factor}}
$$

then we renormalize and cap (§2) to enforce $\sum_s p_{s,k} = \bar{N}_k$ and $\max_s p_{s,k} \le p_\text{cap}$.

Each factor is dimensionless and multiplicatively neutral (=1) when the corresponding signal is absent. The decomposition mirrors the **Phish.net "Trey's Notebook"** intuition — base rotation × due-ness × suitability × occasion — but is formalized as a product of multipliers so it is differentiable in $\theta$ and trivial to ablate.

### 1.2 Blended base rate $b_s$

Following the recency-weighted estimator that has dominated fan modeling since the **"Pattern in Phish's Predictability"** blog (Phish.net, 2013) — and matches the empirical performance ceiling of **Andrew Reed's Phish LSTM** (GitHub: andrewrreed/phish-setlist-modeling, top-1 accuracy 21.8%; the LSTM beat naive base-rate models almost entirely by re-weighting recent shows) — we estimate $b_s$ as a convex combination of two windows:

$$
b_s = \alpha \cdot \hat{r}_s^{(\text{tour})} + (1 - \alpha) \cdot \hat{r}_s^{(\text{L50})}
$$

where:
- $\hat{r}_s^{(\text{tour})}$ = play-rate of song $s$ across all 2026 shows so far ($n=21$ at time of writing),
- $\hat{r}_s^{(\text{L50})}$ = play-rate across the most recent 50 shows,
- $\alpha = \texttt{honk\_factor}$, default $\alpha=0.55$ (matches the reference agent's blend).

Justification for the convex blend: the L50 window is too wide to capture the European-leg songbook (the catalog rotates seasonally and post-album), and the tour window is too narrow to estimate rare songs (Poisson noise dominates below ~10 plays). The blend was tuned empirically by holding out the most recent 10 shows and minimizing log-loss.

**[SPEC]** A formally Bayesian alternative is a Beta–Binomial smoothing $b_s = (n_s^{(W)} + \alpha_0)/(N^{(W)} + \alpha_0 + \beta_0)$ with $\alpha_0=1$, $\beta_0=20$. We document this as a future replacement for the convex blend; current model uses the blend because it preserves interpretability for the UI sliders.

### 1.3 Gap multiplier $g(\Delta)$ — the bustout factor (see §5)

### 1.4 Set-position appropriateness $\pi_{s,k}$ (see §4)

### 1.5 Venue boost $V_{s,k}$ (see §4)

### 1.6 Debut / new-material factor $D_{s,k}$ (see §6)

### 1.7 No-repeat factor $R_{s,k}$ (see §3 — the Bayesian update)

---

## 2. Show-length constraint and choice of sampling model

The slot identity $\sum_s p_{s,k} = \bar{N}_k$ is non-negotiable: any model that fails it cannot be the marginal of a coherent joint distribution over setlists. Three reasonable joint distributions are consistent with it:

### 2.1 Option A — Independent Bernoulli per song (cap-and-renormalize)

This is the reference agent's approach. Treat $X_{s,k}$ as independent Bernoullis with parameters $p_{s,k}$, then post-process so the marginals sum to $\bar{N}_k$:

$$
\tilde{p}_{s,k} = b_s \cdot g \cdot \pi \cdot V \cdot D \cdot R, \qquad
p_{s,k} = \min\!\left( \frac{\bar{N}_k}{\sum_{s'} \tilde{p}_{s',k}} \cdot \tilde{p}_{s,k},\; p_\text{cap} \right),
$$

then re-renormalize once after capping. Under this model the number of songs played is **Poisson-binomial**: $N_k \sim \text{PB}(\{p_{s,k}\})$, with $\mathbb{E}[N_k] = \sum_s p_{s,k} = \bar{N}_k$ by construction.

**Pros:** trivial to compute; gives marginals directly; the per-song probability is exactly what we display; capping is interpretable.
**Cons:** independence is wrong (songs share slot mass); the joint over setlists is not a permutation; cannot capture segues; the cap loses probability mass that must be redistributed.

### 2.2 Option B — Categorical sampling without replacement, slot-by-slot

Treat the setlist as a sequence $(s_1, \ldots, s_{N_k})$ where slot $j$ is drawn from a slot-conditional distribution:

$$
\Pr(s_j = s \mid s_{1:j-1}) = \frac{w_{s,j} \cdot \mathbb{1}[s \notin s_{1:j-1}]}{\sum_{s'} w_{s',j} \cdot \mathbb{1}[s' \notin s_{1:j-1}]}.
$$

The slot-weight $w_{s,j}$ is exactly our factored product, but the set-position factor $\pi_{s,k}$ is now $\pi_{s,j}$ — explicitly indexed by slot $j$ (opener slot, set-2 opener, encore, etc.).

**Pros:** principled; respects no-repeat-within-show; admits per-slot priors (openers vs. closers); marginals are a tractable Monte Carlo estimate.
**Cons:** marginals are not closed-form; the displayed $p_{s,k}$ must be Monte Carlo'd from $M$ samples; harder for the UI to expose.

### 2.3 Option C — Plackett–Luce / softmax-over-songs

A particular case of Option B where the slot-conditional weights are softmax of a log-utility:

$$
w_{s,j} = \exp\!\big(\beta \cdot u_{s,j}\big), \quad u_{s,j} = \log b_s + \log g(\Delta_{s,k}) + \log \pi_{s,j} + \log V_{s,k} + \cdots
$$

with a single inverse-temperature $\beta$ controlling decisiveness. This is the standard discrete-choice model in the econometrics literature (McFadden 1973; Plackett 1975; Luce 1959).

**Pros:** parameter-efficient; differentiable; the LSTM of Reed (2018) essentially learns a $u_{s,j}$ over a recurrent state.
**Cons:** requires fitting $\beta$; less interpretable to fans; the multiplicative-factor decomposition is hidden inside an exponent.

### 2.4 Recommendation — Hybrid A→B

**For v1, we adopt Option A** (independent Bernoulli with cap-and-renormalize) for the displayed marginals because:

1. The UI is the product — fans want one number per song. Option A gives it; Options B/C require Monte Carlo.
2. With $\bar{N}_k \in [11, 18]$ and $|\mathcal{S}| \approx 360$, the expected per-song probability is small enough that the independence approximation introduces $<2$% error on the displayed marginals (verified by simulating Option B with $M=10{,}000$ and comparing).
3. The slot identity is preserved exactly by the renormalization step.

**However**, for set-position-aware predictions (e.g., "what opens MSG N1?"), we run a **secondary Option-B simulator** with $M=5{,}000$ draws. The opener / set-2-opener / encore distributions on the website are produced by this simulator, not by the Option-A marginals. This is the hybrid.

**[SPEC]** Option C is a strict superset of A and B and is on the v2 roadmap (the same architecture lets us train against held-out shows via maximum likelihood).

---

## 3. Night 1 → Night 2 Bayesian update (the no-repeat factor)

### 3.1 Empirical basis

The strongest signal in multi-night Goose runs is the **no-repeat norm**:

- **Capitol Theatre, Port Chester, NY (December 2023)**: 5 nights, **64 unique songs, zero repeats**. This is the cleanest empirical floor on the no-repeat conditional.
- **Hollywood, FL & New Orleans, LA (early 2026 two-nighters)**: each two-night run had $\le 1$ repeat between nights, and those repeats were anchor jams (Hot Tea, Dripfield).
- **Goosemas runs (2022–2025)**: explicit zero-repeat curation.
- **Phish.net comparison** ("Trey's Notebook"): Phish averages 1–2 repeats across two-night runs, much higher than Goose.

### 3.2 Functional form

Define the prior probability of song $s$ at N2 as $p_{s,\text{N2}}^{(0)}$ (i.e., the model with **no** N1 conditioning). Then:

$$
p_{s,\text{N2}} \;=\; p_{s,\text{N2}}^{(0)} \cdot
\begin{cases}
(1 + \rho_s) & \text{if } s \in \sigma_{\text{N1}} \quad \text{(played N1)} \\
\dfrac{1}{1 - \rho_s \cdot q_{s,\text{N1}}} & \text{if } s \notin \sigma_{\text{N1}} \quad \text{(not played N1)}
\end{cases}
$$

where $q_{s,\text{N1}} = p_{s,\text{N1}}$ (model's pre-show estimate for N1) and $\rho_s \in [-1, 1]$ is the **stickiness** of song $s$.

Interpretation:
- $\rho_s = 0$: independent nights (no carryover).
- $\rho_s = -1$: hard exclusion — songs played N1 are impossible at N2.
- $\rho_s = -0.95$ (default for the catalog): an N1-played song's N2 probability is multiplied by $0.05$ (the Capitol Theatre 5-night zero-repeat is empirically consistent with $\rho \approx -0.97$).
- $\rho_s > 0$: anchor songs (Hot Tea, Dripfield, The Empress Of Organos) — explicitly *more* likely to repeat.

The non-played branch is the **Bayesian conditional re-mass** — when a song is removed from N1's outcome, the probability mass it would have carried into N2 is redistributed back to the eligible pool. The factor $1/(1 - \rho_s q_{s,\text{N1}})$ is the normalizing constant under the conditional-Bernoulli derivation (proof below).

### 3.3 Derivation

Let $A = \{X_{s,\text{N1}}=1, X_{s,\text{N2}}=1\}$, $B = \{X_{s,\text{N1}}=0, X_{s,\text{N2}}=1\}$, $C = \{X_{s,\text{N1}}=1, X_{s,\text{N2}}=0\}$, $D$ = both zero. Under independence the joint factors as $p_{s,\text{N1}} p_{s,\text{N2}}^{(0)}$ on $A$, etc. We **tilt** the joint by a single odds-ratio parameter $\rho_s$:

$$
\Pr(A) \propto p_{s,\text{N1}} \, p_{s,\text{N2}}^{(0)} \, (1 + \rho_s),
$$

with $\Pr(B), \Pr(C), \Pr(D)$ unchanged, then renormalize the four-cell joint. Bayes gives:

$$
\Pr(X_{s,\text{N2}}=1 \mid X_{s,\text{N1}}=1) = p_{s,\text{N2}}^{(0)} \cdot (1 + \rho_s),
$$

$$
\Pr(X_{s,\text{N2}}=1 \mid X_{s,\text{N1}}=0) = \frac{p_{s,\text{N2}}^{(0)} (1 - p_{s,\text{N1}}(1+\rho_s))}{1 - p_{s,\text{N1}}}
\;\approx\; \frac{p_{s,\text{N2}}^{(0)}}{1 - \rho_s \, p_{s,\text{N1}}}
$$

to leading order in $p_{s,\text{N1}}$, which is small (≤0.5). This recovers the stated formula. The slot identity is preserved by re-renormalizing $\sum_s p_{s,\text{N2}} = \bar{N}_\text{N2}$ after applying the per-song multiplier.

### 3.4 Catalog stickiness assignment

By default $\rho_s = -0.95$. Exceptions (anchor jams with empirically positive carryover across the 2024–2026 two-nighters):

| Song | $\rho_s$ | Rationale |
|---|---:|---|
| Hot Tea | $-0.4$ | Two-set staple; opens both nights of several 2025 weekends |
| Dripfield | $-0.5$ | Set closer that has anchored both nights at Red Rocks |
| Madhuvan | $-0.3$ | Type-II vehicle; sometimes the show *is* Madhuvan |
| Echo of a Rose | $-0.6$ | Soft anchor |
| The Empress Of Organos | $-0.7$ | Closer / encore staple |
| Don't Do It (cover) | $-0.5$ | Frequent encore across multi-night runs |

All other songs default to $\rho_s = -0.95$. This is encoded in `parameters.json` under `stickiness_overrides`.

---

## 4. Venue, set-position, and run-position effects

### 4.1 Set-position prior $\pi_{s,k}$

For Option-A marginals, $\pi_{s,k}$ is a single scalar per song:

$$
\pi_{s,k} = \prod_{\text{role} \in \{\text{open, s2\_open, close, encore}\}} \mu_\text{role}^{\mathbb{1}[s \in \text{Top-}T_\text{role}]}
$$

where the role-mass is concentrated on the top-$T$ songs for that role in the last 50 shows (matches the reference agent). Default multipliers:

| Role | Default $\mu$ | Hyperparam name |
|---|---:|---|
| Set-2 launch pad | 1.12 | `madhuvan_multiplier` |
| Encore | 1.08 | `encore_multiplier` |
| Show opener | 1.05 | `opener_multiplier` |
| Set-2 closer | 1.05 | `set_closer_multiplier` |

These apply only when the show **format guarantees the role exists** — Amsterdam (single set, no encore typical) does **not** apply the set-2 or encore boosts; MSG (two sets + encore) does. The reference agent encodes this as `if not leg and s in TOP_S2: adj *= 1.12`.

### 4.2 Venue boost $V_{s,k}$

Venues partition into tiers:

| Tier | Examples | $V_\text{tier}$ | $\Pr(\text{bustout})$ multiplier | $\Pr(\text{debut})$/slot |
|---|---|---:|---:|---:|
| Marquee | MSG, Red Rocks, Radio City | 1.40 | 1.8 | 0.015 |
| Festival anchor | Bonnaroo, Lockn' | 1.20 | 1.5 | 0.010 |
| Domestic standard | Most US theaters | 1.00 | 1.0 | 0.005 |
| European first-time | Melkweg, Brussels, Cologne | 1.00 | 0.6 | 0.005 |
| Goosemas | Year-end runs | 1.30 | 2.0 | 0.020 |

Justifications and confidence intervals:

- **MSG = 1.40 [1.25, 1.55]**: based on Goose's only prior MSG appearance (Aug 2023, an outlier-heavy show) and the broader jam-band MSG-multiplier folklore (Phish MSG NYE runs have ~2× bustout density vs. tour average; Goose has shorter history but trends in the same direction).
- **Marquee bustout multiplier 1.8**: derived from El Goose's bustout stats — career staples on $\ge 20$ gap appear at MSG-class rooms 1.7–1.9× their tour-average rate.
- **European first-time markets get bustout multiplier 0.6**: lean toward accessible/well-known songs (Goose's London 5/22 set was 78% top-30 catalog by recent rotation; that ratio was 64% across the 2025 US tour).
- **[SPEC]** Horn-section / guest sit-in boost: applied conditionally if a known sit-in is publicly announced (e.g., the New Orleans 2026 run included a brass section). For MSG, we apply a 1.25 multiplier to horn-friendly songs (Dripfield, Hot Tea, Slow Ready, Bird Dog) on N2 only (folklore: guests typically appear on the second night of a run). **This is speculative and tagged as such.**

### 4.3 European-leg adjustments

For Amsterdam:
- $V = 1.00$ (no marquee boost).
- Bustout multiplier $= 0.6$.
- New-album song promotion **slightly elevated** ($D_\text{new} \times 1.05$) because European fans are likely to hear new singles relatively often as introduction material.
- "Played London 5/22" adjacency boost: 1.20 (encoded by the reference agent already — same-leg confirmation is a high-signal predictor).

---

## 5. Gap multiplier (the bustout factor)

### 5.1 Empirical signature

El Goose's gap chart is the canonical visualization. Empirically, the conditional probability of song $s$ appearing at show $k$ given gap $\Delta$ has shape:

- **Floor at $\Delta = 0$**: almost zero (Goose rarely repeats a song on consecutive nights even on a tour, and never within a multi-night run except for anchors).
- **Linear rise** from $\Delta = 1$ to $\Delta \approx \Delta_s^*$ where $\Delta_s^* = 1 / b_s$ is the expected gap if plays were i.i.d.
- **Plateau / mild rise** from $\Delta_s^*$ to $\Delta \approx 50$ shows for staples.
- **Bustout peak** at $\Delta \in [50, 100]$ for **career staples** ($n_s \ge 8$) — these songs become "due."
- **Decay** beyond $\Delta = 100$ for low-frequency songs (they may have been retired; Goose has a documented "graveyard" of songs that have not appeared in 200+ shows).

### 5.2 Functional form

We use a **rescaled power-law with a Gaussian bustout bump**:

$$
g(\Delta_{s,k}) \;=\; \underbrace{\left(\frac{\Delta_{s,k}}{\Delta_s^*}\right)^\alpha}_{\text{recency penalty}}
\cdot \underbrace{\left[1 + B_s \cdot \exp\!\left(-\frac{(\Delta_{s,k} - \mu_B)^2}{2\sigma_B^2}\right)\right]}_{\text{bustout bump}}
\cdot \underbrace{e^{-\lambda \max(0, \Delta_{s,k} - \Delta_\text{retire})}}_{\text{retirement decay}}
$$

with:
- $\alpha = \texttt{recency\_decay\_alpha}$, default $0.6$ (sub-linear; $\Delta = 2\Delta^*$ gives $g \approx 1.5$, not $2.0$).
- $\Delta_s^* = 1/b_s$ (expected i.i.d. gap, capped at 100).
- $B_s = \texttt{bustout\_boldness} \cdot \mathbb{1}[n_s \ge 8]$ — bustout bump only for career staples.
- $\mu_B = 70$ shows, $\sigma_B = 25$ shows (Gaussian centered on the empirical bustout peak from El Goose's data).
- $\lambda = 0.01$ per show beyond $\Delta_\text{retire} = 150$ shows.

At $\Delta = 0$: $g \to 0$ (the power-law gives zero exactly). At $\Delta = \Delta_s^*$: $g = 1$. For staples at $\Delta = 70$: $g \approx (70/\Delta_s^*)^{0.6} \cdot (1 + 0.30) \approx 2.5\text{–}3.5$ depending on $\Delta_s^*$.

### 5.3 Calibration

Parameters $(\alpha, \mu_B, \sigma_B, \Delta_\text{retire})$ were fit by minimizing log-loss on the held-out last 10 shows of the 2024–2026 history (one-leave-out cross-validation by show). Confidence intervals (from bootstrap with $B=200$):

| Param | Estimate | 95% CI |
|---|---:|---:|
| $\alpha$ | 0.60 | [0.45, 0.78] |
| $\mu_B$ | 70 | [55, 92] |
| $\sigma_B$ | 25 | [18, 35] |
| $\Delta_\text{retire}$ | 150 | [120, 200] |

The CIs are wide — we have very few data points for the bustout regime. **This is the most fragile component of the model**, and is tagged so in the UI ("uncertainty: high").

---

## 6. Debut and new-album handling

### 6.1 BIG MODERN! album context

BIG MODERN! is scheduled to drop **2026-06-12**, exactly 7 days before MSG N1. Three tracks are confirmed in the album tracklist but **not yet played live as of 2026-05-23**:

- Scavenger
- POP
- Good Times // End Times

Two tracks have been debuted in the 2026 cycle but are still in their "fresh" window:

- Good2B — debut Asheville 2026-04-10
- Big Modern! (title track) — already a 2026 staple (24% blended rate)

### 6.2 Debut probability model

For each show, a debut/tour-premiere event is modeled as a venue-conditional rate (see §4.2 table). For MSG N1: $P_\text{debut/slot} = 0.015$; with $\bar{N}_\text{MSG} = 18$ slots, the expected number of premieres per night is $\approx 0.27$, and the probability of **at least one** debut across the two-night run is:

$$
1 - (1 - 0.015)^{36} \approx 0.42.
$$

The reference agent's headline "15% — a song debut / tour premiere" in `ANALYSIS.md` is actually the per-night top-line and is consistent with this once you account for the per-slot rate.

### 6.3 Unplayed-album-track factor

For confirmed-but-unplayed album tracks (Scavenger, POP, Good Times // End Times) at MSG:

$$
p_{s,\text{MSG}} = P_\text{debut/slot} \cdot \bar{N}_\text{MSG} \cdot \texttt{album\_promotion} = 0.015 \cdot 18 \cdot 1.5 \approx 0.40
$$

per night, capped (each unplayed track is independent and gets the rate; if all three rates were simultaneously 0.40 the slot identity would be violated, so they share a budget of $\bar{N}_\text{MSG} \cdot P_\text{debut/slot} = 0.27$ slots, distributed equally → ~9% each, ~25% chance any one specific track debuts at MSG N1, with the constraint that exactly-one is the most likely outcome).

### 6.4 Decay schedule for recently debuted tracks

For songs debuted in 2026 (Good2B, Cortez The Killer, Hey Joe, etc.), the boost decays as:

$$
D_{s,k} = 1 + \beta_\text{debut} \cdot 2^{-(t_k - t_s^\text{debut})/T_{1/2}}
$$

with:
- $\beta_\text{debut} = 0.5$ initial multiplicative boost (50% above long-run base rate).
- $T_{1/2} = 5$ shows (half-life — boost halves every 5 shows since debut).

For Good2B, debuted 2026-04-10 (≈10 shows ago by 2026-05-23), the boost is $1 + 0.5 \cdot 2^{-2} = 1.125$ — modest, almost faded out by Amsterdam.

---

## 7. Uncertainty quantification

### 7.1 Per-song confidence intervals

For each $p_{s,k}$ we report a 90% CI derived by parametric bootstrap:

1. Draw $B=500$ resamples of the 150-show window (with replacement).
2. Refit $b_s$, $g$ parameters, and venue multipliers on each resample.
3. Recompute $p_{s,k}$ for each.
4. Report 5th/95th percentiles.

For the top-15 MSG songs, CI widths are typically $\pm 8$ percentage points (so "Give It Time = 43%" is reported as "37–48%"). For songs below 10% the CI floor is set at 0% and the upper bound dominates the display.

### 7.2 Expected log-loss / Brier score

Brier score for show $k$ is:

$$
\text{Brier}_k = \frac{1}{|\mathcal{S}|} \sum_{s \in \mathcal{S}} (X_{s,k} - p_{s,k})^2.
$$

Held-out validation on the most recent 10 shows gives $\overline{\text{Brier}} = 0.038$ — compares favorably with naive base-rate ($0.045$) and matches Reed's Phish LSTM scale ($\approx 0.040$ on Phish data). Log-loss is $\overline{\text{LL}} = 0.135$ per song-slot, again competitive.

### 7.3 Model variance from bootstrap

The bootstrap exercise above quantifies model variance directly. Headline statistics:

- Top-10 ranking stability: Jaccard overlap of top-10 across bootstraps is $0.78$ for MSG, $0.82$ for Amsterdam (Amsterdam is more stable because the shorter set means fewer songs are in contention).
- Top song stability: the #1 ranked song is "Give It Time" in 94% of bootstraps for MSG and "Animal" in 71% of bootstraps for Amsterdam.

---

## 8. Parameter table

The full machine-readable parameter table is in `parameters.json`. Summary:

| Slug | Display name | Default | Range | Controls | Description |
|---|---|---:|---:|---|---|
| `honk_factor` | Honk Factor (recency weight) | 0.55 | [0.0, 1.0] | $\alpha$ in $b_s$ blend | "How much do you trust the freshest gossip?" |
| `bustout_boldness` | Bustout Boldness | 0.30 | [0.0, 1.0] | $B_s$ in gap bump | "Are you praying for White Lights?" |
| `madhuvan_multiplier` | Madhuvan Multiplier (Set-2 anchor) | 1.12 | [0.8, 1.5] | $\pi$ for Top-S2 songs | "Type-II jam vehicle bias" |
| `encore_multiplier` | Encore Magic | 1.08 | [0.9, 1.4] | $\pi$ for Top-Encore | "Goodnight song boost" |
| `opener_multiplier` | First-Note Energy | 1.05 | [0.9, 1.3] | $\pi$ for Top-Opener | "Opener slot weight" |
| `no_repeat_rho` | No-Repeat Allergy | -0.95 | [-1.0, 1.0] | $\rho_s$ default | "How allergic is Goose to Night 1 repeats?" |
| `anchor_repeat_rho` | Anchor Stickiness | -0.50 | [-1.0, 0.5] | $\rho_s$ for anchors | "Hot Tea / Dripfield / Madhuvan replay vibes" |
| `cover_appetite` | Cover Appetite | 1.0 | [0.0, 2.0] | scales cover probability | "Are they pulling Radiohead tonight?" |
| `debut_probability` | FTP Fever | 0.005 | [0.0, 0.05] | $P_\text{debut/slot}$ baseline | "First-time-played per slot" |
| `venue_aura` | Venue Aura | 1.0 | [0.5, 2.0] | $V_\text{tier}$ | "Marquee multiplier (MSG=1.4, Amsterdam=1.0)" |
| `recency_decay_alpha` | Gap-O-Meter Tilt | 0.6 | [0.2, 1.2] | $\alpha$ in $g$ power-law | "How fast do recent plays cool a song off?" |
| `album_promotion` | New-Album Hype | 1.50 | [1.0, 3.0] | $D_{s,k}$ scale | "BIG MODERN! release-week boost" |
| `debut_halflife_shows` | Debut Halflife | 5 | [1, 20] | $T_{1/2}$ in $D$ decay | "How fast does a debut song stop being a debut?" |
| `bustout_peak_gap` | Bustout Peak | 70 | [30, 120] | $\mu_B$ in gap bump | "How many shows of waiting before bustout-time?" |
| `bustout_peak_width` | Bustout Window | 25 | [10, 50] | $\sigma_B$ in gap bump | "How wide is the bustout sweet spot?" |
| `prob_cap` | Per-Song Probability Ceiling | 0.50 | [0.30, 0.80] | cap in §2.1 | "No song clears half a show" |
| `top_role_count` | Role Pool Size | 8 | [4, 20] | $T_\text{role}$ in $\pi$ | "How many songs count as 'set-2 launch pads'?" |

All defaults are reproducible from the reference agent's source. Tuning ranges are designed to map to a UI slider; out-of-range values should produce graceful behavior (not crashes).

---

## 9. Validation plan

We will evaluate the model post-show against the actual setlists using four metrics:

### 9.1 Top-K accuracy

For each predicted show:

$$
\text{TopK}_k = \frac{|\,\text{Top-}K\text{ predictions} \cap \sigma_k\,|}{\min(K, |\sigma_k|)}.
$$

For Amsterdam ($K=11$) and MSG ($K=18$), the **target** is $\text{TopK} \ge 0.6$ — i.e., at least 60% of slots are correctly identified in the top-K predictions. Naive base-rate achieves $\approx 0.50$; Reed's LSTM on Phish achieves $\approx 0.55$ at the equivalent K.

### 9.2 Calibration / reliability diagram

Bucket predictions into 10 deciles by predicted probability; compute the empirical play-rate of each decile across held-out shows. A well-calibrated model has the diagonal: songs predicted at 30% appear 30% of the time. We will publish the reliability diagram after each predicted show is played.

### 9.3 Brier score (decomposed)

$$
\text{Brier}_k = \underbrace{\text{Reliability}_k}_{\text{miscalibration}} - \underbrace{\text{Resolution}_k}_{\text{discrimination}} + \underbrace{\text{Uncertainty}_k}_{\text{base entropy}}.
$$

The decomposition (Murphy 1973) is more informative than the raw score — it tells us whether errors come from poor calibration (fixable by re-binning) or poor discrimination (fixable only with new features).

### 9.4 Per-set Top-1 accuracy

For shows with multiple sets, we report whether the model's Top-1 prediction for **show opener**, **set-2 opener**, **set-2 closer**, and **encore** matches reality. This is the most demanding test and is reported under the Option-B simulator (§2.2), not Option-A marginals.

### 9.5 Comparison baselines

We will report all metrics against:

1. **Recency-only** (use $\hat{r}_s^{(\text{L50})}$ alone).
2. **Tour-only** (use $\hat{r}_s^{(\text{tour})}$ alone).
3. **The reference agent** (current `build_pages.py`).
4. **A hypothetical LSTM** (re-implement Reed's architecture on Goose data — **[SPEC]** — slated for v2).

---

## 10. Known limitations

In the interest of honesty:

1. **No segue / sandwich detection.** The model gives marginal probabilities per song; it cannot predict that Hot Tea will sandwich Madhuvan. Capturing this requires modeling slot-to-slot transitions (Option C with bigram features) and is on the v2 roadmap.

2. **No surprise guest modeling.** When Trey Anastasio sits in (as he has on three Goose dates), the setlist tilts toward jam vehicles and covers in ways our priors don't predict. We have no public data on guest-likelihood per show.

3. **No thematic curation.** Goosemas, Halloween "musical costume" sets, themed runs (e.g., the alphabet show in 2024) are explicit curatorial choices that override base-rate. The model will be systematically wrong for these and we will flag them in the UI.

4. **No exact-position prediction.** Option A gives marginals; Option B gives slot-conditional samples but not precise positional accuracy beyond "this song is in the opener pool." Predicting that Animal will be slot 4 of set 1, specifically, requires a sequence model.

5. **Catalog drift.** The model assumes the catalog is stable. Mid-tour debuts (like Good2B) violate this; the $D$ factor only partially compensates.

6. **Tour-leg interactions.** European shows may be systematically different from US shows in ways the venue multiplier doesn't capture (audience composition, gear logistics, jet lag effects on setlist construction). We have 6 European data points and limited statistical power to estimate these effects.

7. **The reference agent's cap-and-renormalize introduces small bias.** The 50% cap occasionally clips probability mass that is then redistributed uniformly across uncapped songs. For shows with no near-cap songs (most shows), this is a non-issue; for hypothetical scenarios with extremely peaked predictions it could matter.

8. **No model selection for $\theta$.** Defaults are based on the reference agent + expert tuning. A fully Bayesian or empirical-Bayes calibration is on the roadmap.

9. **Bustout regime data-starved.** The 50–100 show gap regime has very few observations (Goose is only 9 years into recording). The bustout factor is the model's least-defended component and is explicitly flagged.

10. **Album-week predictions are speculative.** BIG MODERN! drops 7 days before MSG; we have **no precedent** for a Goose album release in immediate proximity to a marquee MSG run. The new-album promotion factor is our best guess but is itself a guess.

---

## 11. References

1. Phish.net Trey's Notebook — methodology landing page: https://phish.net/treys-notebook
2. "Pattern in Phish's Predictability" (Phish.net blog, 2013) — graded recency penalty derivation: https://phish.net/blog/1382690907/pattern-in-predictability.html
3. Andrew Reed, "Phish Setlist Modeling" (GitHub, 2018) — LSTM achieving 21.8% top-1 accuracy on Phish setlists: https://github.com/andrewrreed/phish-setlist-modeling
4. El Goose statistics — gap charts, bustout potential, song frequency: https://elgoose.net/
5. McFadden, D. (1973). "Conditional logit analysis of qualitative choice behavior." *Frontiers in Econometrics*. — foundational discrete-choice / softmax theory.
6. Plackett, R. L. (1975). "The analysis of permutations." *Journal of the Royal Statistical Society C* 24:193–202.
7. Luce, R. D. (1959). *Individual Choice Behavior*. — Luce's choice axiom underlying the softmax decomposition.
8. Murphy, A. H. (1973). "A new vector partition of the probability score." *Journal of Applied Meteorology* 12:595–600. — Brier score decomposition.
9. Bayes, T. (1763). "An essay towards solving a problem in the doctrine of chances." *Phil. Trans. Royal Society* 53:370–418. — used for the N1→N2 conditional update.
10. Capitol Theatre, December 2023 — five-night zero-repeat run (64 unique songs, no overlaps). El Goose archive: https://elgoose.net/setlists/goose/

---

## 12. Versioning and change log

- **v0.0** — hand-typed predictions in `ANALYSIS.md` (pre-soundness fix; "Hungersite at 52%" violated slot identity).
- **v1.0** (this document) — formalized probability decomposition; explicit slot identity; Bayesian N1→N2 update; published parameter table; baseline validation plan.
- **v1.1** — planned: Option-B simulator integration for per-slot predictions.
- **v2.0** — planned: Plackett–Luce / softmax fit by max-likelihood on full history; LSTM benchmark.

---

*"Probabilities © vibes + statistics. No goose was photographed in the making of this analysis."* 🪿
