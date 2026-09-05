# Professional Trade Decision Mathematics

## Authority and use

This file is a research mathematics detail reference. It is not a second
TrendForge build order and it cannot change product scope, public states, source
activation, evidence-family ownership, or implementation acceptance.

Authority remains:

1. `docs/fable/new_merge_PLAN_2026-07-18.md` for build sequence, stable IDs,
   public states, product scope, acceptance ceilings, and postponed/rejected
   work.
2. `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` for
   point-in-time source, outcome, calibration, and long-form domain detail
   selected by File A.
3. `docs/fable/FINAL_MERGE_PLAN.md` for the mandatory mapped product, options,
   Gamma, strike, and research-workflow addendum.
4. `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` for mapped discovery,
   M-Factor, tool, and frontend detail.

When this file conflicts with File A on scope, states, quantity, execution, or
probability presentation, File A wins. Mathematical formulas in this file are
research definitions until their owning File A requirement passes point-in-time
fixtures, adversarial tests, replay, and observed acceptance.

## Purpose

This document defines the mathematical and evidence requirements for evaluating
NSE stock and derivatives candidates. It does not promise a maximum win rate,
and it does not authorize broker execution.

The correct objective is:

> Estimate a calibrated probability for a precisely defined price path, verify
> positive expected value after realistic costs, and abstain when uncertainty,
> missing data, stale data, correlated evidence, or execution risk is too high.

An evidence-ranking score is not a probability. A high win rate is not enough
if losses, slippage, or market impact are too large.

## 1. Define the predicted event

Terms such as "bullish" and "strong stock" are not mathematical events. Every
model must define its label, trigger, target, invalidation, and time horizon.

Let:

```text
Y_t = 1  when upper target U is reached before lower invalidation L
           within horizon H after a closed trigger.
Y_t = 0  otherwise.
```

The required probability is:

```text
p_t = P(Y_t = 1 | F_t)
```

`F_t` may contain only information available at the decision timestamp.
Unclosed candles, revised disclosures not yet published, future constituents,
future expiries, and backfilled data are prohibited.

## 2. Expected value, not win rate

Let:

```text
G = realizable gain if the target succeeds
L = realizable loss if invalidation occurs
C = total spread, fees, slippage, and market-impact cost
p = calibrated probability of target before invalidation
```

For the simplified case where gain, loss, and cost are fixed:

```text
EV = pG - (1 - p)L - C
```

The more general form uses conditional payoff and cost distributions:

```text
EV =
    p * E[G | target_first]
    - (1 - p) * E[L | invalidation_first]
    - E[C]
```

This general form is preferred for validation because realized gains, losses,
slippage, impact, gaps, and partial exits are not constants.

Minimum break-even probability:

```text
p_min = (L + C) / (G + L)
```

Example:

```text
Win rate = 80%
Average win = +1R
Average loss = -5R

EV = 0.80(1R) - 0.20(5R) = -0.20R
```

The strategy loses before transaction costs despite winning 80% of trades.

Any future probability-authorized analytical decision must use conservative
probability, payoff, and cost bounds:

```text
EV_conservative =
    p_low * G_low
    - (1 - p_low) * L_high
    - C_high
```

`p_low` is a lower Bayesian credible bound or bootstrap confidence bound.
`G_low`, `L_high`, and `C_high` are conservative payoff and cost estimates. A
point estimate alone cannot authorize a probability or expected-value claim.

Current TrendForge `CONFIRMED` remains a non-executable evidence state governed
by File A. It does not require, imply, or display calibrated probability or
expected value. Probability/EV promotion belongs to future R16/R18
point-in-time validation and requires explicit File A approval.

## 3. Seconds-to-minutes price movement

At very short horizons, price movement is primarily an order-flow and liquidity
problem.

Mid-price:

```text
m_t = (Bid_t + Ask_t) / 2
```

Queue imbalance:

```text
I_t = (Q_bid - Q_ask) / (Q_bid + Q_ask)
```

Microprice:

```text
Microprice_t =
    (Ask_t * Q_bid + Bid_t * Q_ask) / (Q_bid + Q_ask)
```

A microprice above the mid-price indicates upward queue pressure. It does not
guarantee an upward trade because cancellations and new orders can change the
book before execution.

Short-horizon order-flow model:

```text
Delta m_(t,h) = lambda_h * OFI_(t,h) + epsilon_(t,h)
```

`OFI` must include:

- market-order executions;
- limit-order additions;
- limit-order cancellations;
- changes at the best bid and ask;
- preferably multiple depth levels.

Price sensitivity rises when available depth falls:

```text
lambda_h is approximately proportional to 1 / market_depth_h
```

Trade volume alone is weaker than signed order-flow imbalance because the same
volume can occur with different liquidity replenishment. Research reference:
[Cont, Kukanov and Stoikov](https://arxiv.org/abs/1011.6402).

TrendForge cannot claim this microstructure edge without verified, timestamped
order-book events. LTP, total volume, or top-five snapshots are insufficient.

## 4. Intraday stock movement

A stock's raw return must be separated from market and sector movement:

```text
r_i,t =
    alpha_i + beta_market * r_market,t
    + beta_sector * r_sector,t + epsilon_i,t
```

Residual return:

```text
r_residual =
    r_stock
    - alpha
    - beta_market * r_market
    - beta_sector * r_sector
```

The regression should use consistently defined raw or excess returns. If excess
returns are used, the same point-in-time risk-free convention applies to the
stock and factors.

A stock rising 1% while its sector rises 2% may be showing negative relative
leadership. Stock selection should prefer positive residual strength rather
than raw percentage change alone.

The beta estimates must be:

- rolling rather than permanently fixed;
- estimated from closed bars;
- shrunk toward stable priors when the sample is small;
- invalidated after corporate actions or structural regime breaks;
- accompanied by residual uncertainty.

### Time-of-day adjusted volume

Intraday volume has a strong time-of-day pattern. Compare current cumulative
volume only with equivalent timestamps:

```text
RVOL_t =
    cumulative_volume_today_at_t
    / median(cumulative_volume_at_t_on_comparable_sessions)
```

Comparable sessions should account for:

- ordinary sessions versus expiry sessions;
- event days;
- shortened or abnormal sessions;
- day of week where empirically material;
- symbol liquidity regime.

### VWAP displacement

```text
VWAP_t = Sum(P_j * V_j) / Sum(V_j)
```

Standardized displacement:

```text
Z_VWAP = (Price_t - VWAP_t) / sigma_intraday,t
```

Price above VWAP alone is weak. Stronger evidence requires agreement with:

- positive residual return;
- expanding time-adjusted volume;
- acceptable spread and depth;
- healthy sector and market breadth;
- closed-bar structure;
- no conflicting material event.

## 5. Volatility controls interpretation

Raw percentage movement is not comparable across stocks or regimes.

Conditional-volatility model:

```text
sigma_t^2 =
    omega
    + alpha * epsilon_(t-1)^2
    + beta * sigma_(t-1)^2
```

Standardized return:

```text
Z_return = (r_t - expected_return_t) / sigma_t
```

A 2% move can be exceptional for one stock and normal for another. Volatility
models should account for clustering rather than assuming constant variance.
Reference: [Engle's GARCH overview](https://www.stern.nyu.edu/rengle/GARCH101.PDF).

For intraday use, compare:

- realized variance at the same time of day;
- overnight variance separately from continuous-session variance;
- upside and downside semivariance;
- jump contribution;
- volatility-of-volatility;
- current spread and depth regime.

## 6. Target-before-stop probability

Let `X_t` be a declared arithmetic state variable, preferably log price rather
than raw price when the model assumes additive normal increments. Under the
simplified process:

```text
dX_t = mu * dt + sigma * dW_t
```

with lower barrier `a`, upper barrier `b`, and current state `x`, the
infinite-horizon probability of hitting the upper barrier before the lower
barrier is:

```text
P(tau_b < tau_a) =
    [1 - exp(-2 * mu * (x - a) / sigma^2)]
    / [1 - exp(-2 * mu * (b - a) / sigma^2)]
```

For zero drift:

```text
P(tau_b < tau_a) = (x - a) / (b - a)
```

This formula does **not** enforce the strategy horizon `H`. The finite-horizon
label requires:

```text
P(tau_b < tau_a and tau_b <= H)
```

That probability must be estimated through a finite-horizon boundary-value
solution, a validated numerical method, or point-in-time Monte Carlo/replay
that includes the probability that neither barrier is reached by `H`. The
infinite-horizon formula must never be reported as the finite-horizon
target-before-invalidation probability.

This connects entry, target, invalidation, drift, and volatility. It is only a
baseline because real stocks exhibit:

- price gaps;
- jumps;
- changing volatility;
- fat-tailed returns;
- discrete ticks;
- auction effects;
- liquidity discontinuities;
- market and sector regime shifts.

Production estimation should therefore use point-in-time empirical simulation,
regime-conditioned transition models, or survival/competing-risk models.

For example:

```text
lambda_target(t | x) = target-hit hazard
lambda_stop(t | x)   = invalidation-hit hazard
```

The model must estimate both hazards and the probability that neither barrier
is reached before horizon expiry.

## 7. Derivatives mathematics

### Forward value and basis

```text
F_0 = S_0 * exp((r - q)T)
```

Annualized basis residual:

```text
BasisResidual =
    ln(F / S) / T - (r - q)
```

A positive residual may indicate bullish carry pressure, financing effects, or
temporary demand. It is not automatically informed buying.

### Open interest

Store only observable price/OI co-movement codes:

```text
Price up, OI up     -> OI_RISE_PRICE_RISE
Price down, OI up   -> OI_RISE_PRICE_FALL
Price up, OI down   -> OI_FALL_PRICE_RISE
Price down, OI down -> OI_FALL_PRICE_FALL
```

Terms such as long buildup, short buildup, short covering, and long unwinding
are common interpretations, not observed position identity. TrendForge does
not store or present them as facts. Public OI does not reveal:

- which participant initiated the position;
- whether the trade was hedged elsewhere;
- buyer versus writer identity;
- institutional intent;
- net portfolio exposure.

### Risk-neutral option distribution

Under suitable assumptions, option prices imply:

```text
f_Q(K,T) = exp(rT) * second_derivative(C(K,T), K)

Q(S_T > K) =
    -exp(rT) * first_derivative(C(K,T), K)
```

This is a risk-neutral state-price density, not the real-world probability that
a target will be reached. Reference:
[Breeden and Litzenberger](https://scholars.duke.edu/publication/1112733).

When a smooth surface is needed, raw SVI parameterizes **total implied
variance**, not implied volatility directly:

```text
k = ln(K / F_T)

w(k,T) =
    a
    + b * [
        rho * (k - m)
        + sqrt((k - m)^2 + sigma_svi^2)
      ]

IV(k,T) = sqrt(w(k,T) / T)
```

The fitted surface must pass calendar- and butterfly-arbitrage checks before
derivatives are used. A fitted mode, tail or Delta bucket is risk-neutral and
model/quote dependent; it is not a market forecast, "crash expectation", or
physical target probability. Reference:
[Gatheral and Jacquier](https://arxiv.org/abs/1204.0646).

A simple implied lognormal range is:

```text
S_T quantile =
    S_0 * exp[
        (r - q - 0.5 * sigma_implied^2)T
        + z * sigma_implied * sqrt(T)
    ]
```

This is only a reference range. It depends on option-chain quality, interpolation,
surface consistency, rates, dividends, and model assumptions.

### Gamma

Black-Scholes gamma:

```text
Gamma =
    exp(-qT) * phi(d1)
    / (S * sigma * sqrt(T))
```

OI-weighted gamma concentration can identify strikes where convexity and
hedging sensitivity may be high. Public OI does not reveal dealer position sign,
so a computed GEX should be labeled `GEX_PROXY`, not dealer gamma exposure.

PCR, Max Pain, OI walls, IV, and GEX share the same option-chain dataset root.
They cannot be counted as independent votes.

NSE reference:
[NSE Option Chain](https://www.nseindia.com/option-chain).

## 8. Probability estimation and calibration

### Simple Bayesian outcome model

For `w` successes and `l` failures:

```text
p | data ~ Beta(alpha_0 + w, beta_0 + l)
```

Use the posterior distribution to report:

- posterior mean;
- median;
- lower credible bound;
- sample size;
- regime and horizon;
- data coverage.

### Multivariate probability model

```text
logit(p_t) =
    beta_0,regime
    + beta_price * x_price
    + beta_flow * x_flow
    + beta_derivatives * x_derivatives
    + beta_event * x_event
    + beta_risk * x_risk
```

Probability models must be calibrated separately by:

- intraday versus swing horizon;
- strategy family;
- volatility regime;
- liquidity class;
- sector;
- long and short direction;
- event and non-event sessions.

### Calibration tests

Brier score:

```text
Brier = Mean[(p_i - y_i)^2]
```

Reliability rule:

```text
Among predictions near 70%, approximately 70% should satisfy the exact label.
```

Also measure:

- calibration intercept and slope;
- expected calibration error;
- log loss;
- precision at selected coverage;
- abstention coverage;
- conditional drawdown;
- outcome counts per probability bucket.

Reference:
[Brier's original verification paper](https://journals.ametsoc.org/view/journals/mwre/78/1/1520-0493_1950_078_0001_vofeit_2_0_co_2.xml).

## 9. Correlation and false confirmation

Five indicators derived from the same price series are not five independent
confirmations.

For a research evidence vector `x` and covariance matrix `Sigma`, a
mean-variance-style experimental combination is:

```text
CombinedScore is proportional to mu_transpose * inverse(Sigma) * x
```

This equation is not the production TrendForge evidence resolver. Empirical
covariance can be singular or unstable under correlated features, small
samples, changing regimes, and missing observations. Any experiment requires
shrinkage/regularization, condition-number diagnostics, PIT estimation, and
walk-forward comparison.

Current ranking uses File A `FUS-009`: representative selection by dataset root
and correlation group, capped family support/opposition, zero for missing
families, and no renormalization. Covariance-based research cannot replace
FUS-009 without R16/R18 approval and out-of-sample evidence.

In practical scanner design, cap the contribution of each independent family:

1. Price structure
2. Relative strength
3. Participation and liquidity
4. Derivatives positioning
5. Corporate catalyst
6. Ownership or sponsorship
7. Market and sector regime
8. Risk and execution feasibility

Every feature must record:

- dataset-root ID;
- evidence-family ID;
- event-root ID where applicable;
- timestamp and source date;
- freshness state;
- authority level;
- quality status;
- whether it may contribute to ranking;
- whether it may authorize confirmation.

Correlated features may refine one family's conclusion but may not create extra
independent confirmation.

## 10. Execution feasibility and realistic costs

Before evaluating expected value:

```text
C =
    half_spread
    + exchange_and_statutory_fees
    + expected_slippage
    + expected_market_impact
```

A commonly tested empirical impact approximation is:

```text
Impact approximately =
    Y * sigma * sqrt(Q / ADV)
```

where:

```text
Q   = intended quantity
ADV = average daily volume
Y   = empirically estimated impact coefficient
```

The formula returns impact in the same return/price convention used for
`sigma`; its horizon, volatility unit, participation rate, order direction,
market phase, and calibration sample must be declared. It is a scenario model,
not a universal NSE impact constant.

TrendForge currently excludes executable quantity and broker execution.
Nevertheless, liquidity and cost feasibility must still prevent unrealistic
research conclusions.

## 11. Professional decision gate

This is a future probability-authorized `R16`/`R18` gate, not an additional
requirement for the current evidence-based `CONFIRMED` state.

A high-quality candidate requires all of the following:

1. Exact direction, closed trigger, target, invalidation, and horizon.
2. Valid symbol, session, contract, expiry, and corporate-action identity.
3. Market and sector regime alignment or an explicitly tested relative-value exception.
4. Positive residual strength rather than raw movement alone.
5. Participation beyond time-adjusted norms.
6. Closed-bar structural confirmation.
7. Independent evidence-family support without duplicate counting.
8. Derivatives evidence that supports, weakens, or conflicts with the hypothesis.
9. Fresh and authoritative catalyst data where the strategy requires it.
10. Realistic spread, slippage, liquidity, and impact assumptions.
11. Calibrated probability with sufficient comparable observations.
12. `p_low > p_min`.
13. Positive conservative expected value.
14. No surveillance, F&O-ban, stale-source, malformed-data, or conflict veto.
15. Explicit `WAIT` whenever any mandatory condition cannot be proved.

## 12. Selectivity and abstention

The highest practical accuracy normally comes from abstention:

```text
Coverage =
    number_of_actionable_candidates
    / number_of_eligible_opportunities
```

As the confidence threshold rises, coverage normally falls. Therefore every
performance report must show both accuracy and coverage.

Required performance dimensions:

- calibration;
- coverage;
- expected value after costs;
- average win and average loss;
- maximum drawdown;
- tail loss;
- turnover;
- liquidity distribution;
- regime stability;
- sample size;
- performance decay;
- unresolved or abstained cases.

High accuracy without these dimensions can represent cherry-picking or hidden
loss severity.

## 13. Backtest and validation requirements

Backtests must use:

- point-in-time source availability;
- historical symbol and constituent membership;
- delisted and failed securities;
- corporate-action adjusted prices;
- historical contract and expiry identity;
- conservative same-bar barrier ordering;
- realistic spread, fees, slippage, and impact;
- walk-forward validation;
- embargo or purging for overlapping labels;
- locked holdout periods;
- strategy-selection correction;
- versioned features, labels, models, and source contracts.

Repeatedly selecting the best result from many strategies creates backtest
overfitting. A strong in-sample result cannot be treated as live probability
without independent point-in-time validation.

## 14. Canonical TrendForge formula crosswalk

The following formulas were already owned by current TrendForge plans. They are
mirrored here for mathematical completeness, but their cited owner remains
authoritative.

### 14.1 Evidence-claim quality

Hybrid Section 16.9:

```text
q_i =
    authority_i
    * freshness_i
    * schema_i
    * completeness_i
    * scope_match_i
    * timestamp_integrity_i
```

Each component is bounded in `[0,1]`. A hard failure makes the claim
unavailable; it is not repaired by an average.

### 14.2 FUS-009 evidence strength

File A FUS-009:

```text
support_g = max(eligible supporting claims in group g)
oppose_g  = max(eligible opposing claims in group g)

S_f = max(group supports in family f)
O_f = max(group oppositions in family f)

support_strength    = 100 * sum(w_f * S_f)
opposition_strength = 100 * sum(w_f * O_f)
evidence_strength   =
    clamp(support_strength - opposition_strength, 0, 100)
```

Profile weights are non-negative, versioned, and sum to one. Missing families
remain zero and are not renormalized. This is evidence rank, not probability,
expected return, confidence, or accuracy.

### 14.3 M-Factor projection

Discovery detail:

```text
long_strength  = FUS-009 evidence_strength for bullish hypothesis
short_strength = FUS-009 evidence_strength for bearish hypothesis
m_balance      = long_strength - short_strength
rank_strength  = max(long_strength, short_strength)
```

M-Factor consumes canonical selected/suppressed claims and cannot calculate a
second hidden score.

### 14.4 PCR and futures carry

File A and Final Merge:

```text
PCR_OI     = sum(put_OI) / sum(call_OI)
PCR_volume = sum(put_volume) / sum(call_volume)

basis = futures - spot
annualized_basis_residual = ln(futures / spot) / T - (r - q)

rollover =
    next_expiry_OI / (near_expiry_OI + next_expiry_OI)
```

All calculations are expiry-scoped. A zero denominator is `UNKNOWN`, never
zero. Basis and rollover are context, not direction by themselves.

### 14.5 Put-call parity and implied forward

Final Merge:

```text
C - P = exp(-rT) * (F - K)
F_implied = K + exp(rT) * (C - P)

observed_parity_low  = call_bid - put_ask
observed_parity_high = call_ask - put_bid
theoretical_parity   = exp(-rT) * (F - K)
```

Paired quotes, timestamps, carry, exercise style, settlement style, and
contract identity must pass before parity is usable.

### 14.6 Surface skew

Final Merge:

```text
total_variance = IV^2 * T
RR25  = IV_25_call - IV_25_put
Fly25 = 0.5 * (IV_25_call + IV_25_put) - IV_ATM
```

RR25/Fly25 require liquid nodes bracketing absolute Delta 0.25, interpolation
in total variance, and no extrapolation.

### 14.7 Max pain

Final Merge:

```text
pain_at_settlement(x) =
    sum(call_OI_i * max(0, x - strike_i))
    + sum(put_OI_i * max(0, strike_i - x))

max_pain = argmin_x(pain_at_settlement(x))
```

Max pain is an expiry reference with inclusion-policy and sensitivity metadata,
not a price target.

### 14.8 Cash-Gamma concentration

Final Merge:

```text
cash_gamma_1pct_inr =
    gamma * open_interest * lot_size * spot^2 * 0.01

cash_gamma_1pct_inr_crore =
    cash_gamma_1pct_inr / 10_000_000
```

Calls and puts remain unsigned and separate. The result is modeled
hedge-notional sensitivity for a one-percent spot move, not Gamma P&L or
observed dealer positioning.

### 14.9 Corporate-action factors

File A DAT-022:

```text
split_factor    = denominator / numerator
bonus_factor    = denominator / (numerator + denominator)
dividend_factor = (pre_ex_close - cash_dividend) / pre_ex_close

TERP =
    (pre_ex_close * denominator + offer_price * numerator)
    / (denominator + numerator)

rights_factor = TERP / pre_ex_close
```

Official terms, effective date, availability time, factor version, and
same-symbol continuity must be proven. Unresolved corporate actions make
affected price features incomplete.

## 15. TrendForge interpretation

TrendForge must keep these concepts separate:

```text
Evidence availability
Evidence quality
Evidence strength
Candidate rank
Calibrated probability
Expected value
State authorization
```

The M-Factor and FUS-009 outputs are evidence-ranking mechanisms. They must not
be displayed as win probability.

A future probability display becomes defensible only after:

- immutable point-in-time outcomes;
- exact target-before-invalidation labels;
- realistic cost simulation;
- conservative same-bar handling;
- delisting and survivorship controls;
- walk-forward and holdout validation;
- Brier and reliability validation;
- minimum sample sizes by horizon and strategy;
- probability intervals;
- model and dataset versioning;
- observed behavior across multiple regimes.

Until those requirements pass, probability and expected-value fields remain
unavailable. This does not remove File A's non-probabilistic research
`CONFIRMED` state:

```text
Evidence strength: available when supported
Win probability: unavailable
Expected value: unavailable
Action state: WATCH, WAIT, CONFIRMED, or REJECT as governed by File A
```

Missing, stale, malformed, metadata-only, unofficial-only, conflicting, or
compiler-unapproved evidence cannot produce `CONFIRMED`.

## 16. Core conclusion

Professional trading decisions do not come from one indicator, a large number
of URLs, a high scanner score, or a claimed win rate.

The required chain is:

```text
Point-in-time data
-> normalized independent evidence
-> market and sector context
-> conditional price-path distribution
-> calibrated probability interval
-> target/invalidation geometry
-> realistic costs and liquidity
-> conservative expected value
-> fail-closed state decision
-> later outcome and calibration feedback
```

The strongest system is not the one that predicts every stock. It is the one
that recognizes when its evidence is insufficient and refuses to convert
uncertainty into false confidence.

## 17. Audit of the supplied 0DTE and option-flow framework

### 17.1 Overall verdict

The supplied framework contains several useful research concepts, but it is
**not correct enough to use as a scanner or trading specification**. It mixes
risk-neutral pricing, physical probability, dealer-position assumptions,
directional option buying and delta-hedged gamma trading as though they were
the same problem. It also uses unsupported win-rate claims, universal
thresholds and US-market data requirements inside an NSE/MCX system.

TrendForge adopts the defensible mathematics below and rejects the deterministic
trade claims. None of this section activates a source, creates probability UI,
changes `FUS-009`, authorizes quantity/execution, or changes the four public
states.

### 17.2 Claim-by-claim disposition

| Supplied lines | Claim | Verdict | Correct TrendForge treatment |
|---|---|---|---|
| 5-17 | Breeden-Litzenberger recovers a density from the second strike derivative of calls | **Correct with assumptions** | It recovers a discounted risk-neutral density from sufficiently smooth, arbitrage-consistent European option prices; it is not a physical forecast |
| 24-30 | Raw SVI directly parameterizes implied volatility | **Wrong** | Raw SVI parameterizes total implied variance `w(k,T)`; `IV=sqrt(w/T)` |
| 32-35 | 10-Delta put is the market crash expectation; 90-Delta call is upside euphoria | **Misleading** | These are surface coordinates. They do not identify investor intent or physical tail probability |
| 37-45 | RND tail probability is preferable to option Delta | **Partly correct, then overstated** | RND integration gives a risk-neutral terminal tail. Delta is a hedge sensitivity; neither is a calibrated real-world target probability. The claimed 15-30% edge is unsupported |
| 51-61 | ATM Black-Scholes theta becomes singular as expiry approaches | **Model-limited** | The dominant diffusion term diverges at the payoff kink in the continuous model. Full theta includes rates/dividends, quote discreteness and exercise/settlement effects |
| 63-69 | `Theta/Gamma = -S^2*sigma^2/2` is a universal constant and low ratio is better | **Wrong as a general rule** | This is only the diffusion component when carry terms vanish. The ratio has units and cannot use a universal threshold |
| 71-79 | Gamma concentrates at the strike near expiry | **Correct only as a distributional limit** | Finite quotes, ticks, settlement and nonzero time keep observed gamma finite; it is not a turning-point detector |
| 81-87 | Signed GEX and zero-GEX pin follow from public OI | **Wrong/unsupported** | Public OI has no dealer sign. Store unsigned cash-Gamma concentration; signed GEX/flip remains `SCENARIO_ONLY_NOT_OBSERVED_POSITION`, never a defended level |
| 89-95 | Front/next vega structure proves a post-expiry volatility explosion; vanna makes spot moves self-reinforcing | **Unsupported** | Vega term structure reflects event risk, variance expectations, supply/demand and risk premia. Vanna is a cross-Greek; feedback requires a proven position/sign and hedging model |
| 102-112 | Cumulative Delta equals buy-minus-sell volume times tick size; divergence gives long/short entries | **Formula wrong; signal unvalidated** | Signed trade volume is `sum(sign_i*qty_i)` with a documented aggressor classifier. Tick size is not part of share/contract Delta. Divergence is a feature requiring PIT tests, not a command |
| 114-125 | VWAP and volume-weighted variance formulas; +/-2 sigma reversal exceeds 70% | **Formulas useful; probability false** | Preserve session/price conventions and comparable time-of-day baselines. No universal reversal probability exists |
| 127-141 | Normalized `OI*Gamma` is pin probability and the largest strikes are institutional targets | **Wrong label and causal claim** | It is an unsigned concentration weight, not probability. Use actual per-strike IV/quotes; do not claim defense, target or institutional intent. The 5,000-contract cutoff is arbitrary |
| 149-161 | Use 20-25 Delta; finite difference across strikes is "real delta"; rising smile slope proves momentum | **Wrong** | The stated finite difference estimates `dC/dK`, not `dC/dS`, and is normally negative. Strike derivative maps to a discounted risk-neutral tail; fixed Delta entries and smile-slope momentum require validation |
| 163-177 | Directional option P&L is pure gamma scalp and becomes pure profit past the stated move | **Wrong/incomplete** | Gamma scalping requires an explicit delta hedge. Include theta, vega, carry, rehedging error, spread, slippage and impact. Nothing beyond a threshold is "pure profit" |
| 179-201 | A 20x option move equals terminal ITM probability; unusual block/dark-pool flow is the only exception | **Wrong mapping and unsupported exception** | A payoff multiple depends on premium, path, IV, spread and exit time. `T=0.01` is not one trading day under standard year fractions. Large prints do not reveal motive or guarantee edge |
| 205-217 | Fixed decision matrix thresholds create high-probability entries | **Rejected** | `Theta/Gamma < 0.5`, 0.5% zero-GEX distance and fixed Delta/OI thresholds are dimensionally or empirically unsupported |
| 221-230 | OPRA and five-second recomputation are required; the framework gives 80% probability | **Wrong market and unsupported probability** | OPRA consolidates US-listed option data, not NSE. TrendForge needs a permitted NSE/broker-entitled source with observed latency. No probability is displayed before R16/R18 calibration |

### 17.3 Correct derivatives

For European calls with sufficiently smooth, arbitrage-consistent prices:

```text
C(K,T) = exp(-rT) * E_Q[max(S_T - K, 0)]

first_derivative(C, K) =
    -exp(-rT) * Q(S_T > K)

second_derivative(C, K) =
    exp(-rT) * f_Q(K,T)
```

Therefore the supplied central difference:

```text
[C(K + epsilon) - C(K - epsilon)] / (2 * epsilon)
```

approximates `dC/dK`. It is **not** option Delta. Delta is `dC/dS` and requires
a spot derivative or model-consistent surface bump.

For a dividend-paying underlying, Black-Scholes-Merton satisfies:

```text
Theta
    + 0.5 * sigma^2 * S^2 * Gamma
    + (r - q) * S * Delta
    - r * V
    = 0
```

Thus:

```text
Theta / Gamma =
    -0.5 * sigma^2 * S^2
    - [(r - q) * S * Delta - r * V] / Gamma
```

The simplified constant ratio is valid only when the carry/value term vanishes.
It cannot be compared with a dimensionless threshold such as `0.5`.

### 17.4 Order-flow and level calculations

Trade-sign cumulative Delta:

```text
CumDelta_t = sum(sign_i * quantity_i)

sign_i =
    +1 for buyer-initiated trade
    -1 for seller-initiated trade
```

If the source does not publish aggressor side, the inference method and its
error rate must be stored. This trade-only measure is not full OFI. Full OFI
also includes best-quote additions, cancellations and size changes. TrendForge
cannot calculate either from LTP and aggregate volume alone.

VWAP and its volume-weighted dispersion are:

```text
VWAP_t = sum(price_i * quantity_i) / sum(quantity_i)

VWAP_variance_t =
    sum(quantity_i * (price_i - VWAP_t)^2)
    / sum(quantity_i)

VWAP_sigma_t = sqrt(VWAP_variance_t)
```

The price convention, session boundary, auction treatment and minimum effective
sample must be versioned. `VWAP +/- 2 sigma` is a location, not a reversal
probability.

Unsigned strike concentration:

```text
cash_gamma_1pct(K) =
    Gamma(K)
    * open_interest(K)
    * lot_size
    * spot^2
    * 0.01

gamma_concentration_weight(K) =
    cash_gamma_1pct(K)
    / sum_over_eligible_strikes(cash_gamma_1pct)
```

This weight is not `PinProb`. Calls and puts remain separate unless an explicit,
validated scenario defines a sign. Max pain remains a settlement-payout
reference and not an institutional target.

### 17.5 Delta-hedged gamma P&L

The local Taylor expansion is:

```text
dV =
    Delta * dS
    + 0.5 * Gamma * (dS)^2
    + Theta * dt
    + Vega * dIV
    + higher_order_terms
```

For a European option under the continuous-dividend Black-Scholes-Merton
model, calendar-time theta per year is:

```text
Theta_call =
    -S * exp(-qT) * phi(d1) * sigma / (2 * sqrt(T))
    + q * S * exp(-qT) * N(d1)
    - r * K * exp(-rT) * N(d2)

Theta_put =
    -S * exp(-qT) * phi(d1) * sigma / (2 * sqrt(T))
    - q * S * exp(-qT) * N(-d1)
    + r * K * exp(-rT) * N(-d2)
```

Here `S` is spot, `K` is strike, `T` is time to expiry in years, `r` is the
continuously compounded risk-free rate, `q` is continuous dividend yield,
`sigma` is annualized implied volatility, `N` is the standard-normal CDF and
`phi` is its density. Per-day or intraday theta must use the same model clock
and annualization convention as `T`; dividing mechanically by 365 or 252 can
be wrong. Discrete dividends, early exercise, settlement rules and non-European
contracts require the appropriate pricing model.

After explicitly delta-hedging and ignoring financing, IV changes, jumps and
costs only for the approximation:

```text
dPi_hedged approximately =
    0.5 * Gamma * (dS)^2
    + Theta * dt
```

For long gamma with `Theta < 0`, the local no-cost move threshold is:

```text
abs(dS)_break_even =
    sqrt((-2 * Theta * dt) / Gamma)
```

Under a continuous diffusion, a locally delta-hedged long option can also be
written as a realized-versus-implied variance approximation:

```text
dPi_long_delta_hedged approximately =
    0.5 * Gamma * S^2
    * (sigma_realized^2 - sigma_implied^2)
    * dt
    - spread
    - slippage
    - rehedging_cost
    - financing
    - market_impact
```

This is a local attribution, not directional option P&L and not a guaranteed
gamma-scalping profit. A positive result requires the variance captured by the
actual hedge path to exceed implied variance by enough to pay all costs.
Discrete hedging, jumps, changing IV/surface shape, vega/vanna, liquidity and
the full price path create material approximation error.

Realized P&L still depends on the full path, rehedging schedule, realized versus
implied volatility, vega/vanna, jumps, financing and transaction costs.
Directional long-option P&L is not gamma-scalping P&L.

### 17.6 Volatility risk premium as scanner context

For a common horizon `h`, a research-only variance-risk-premium proxy is:

```text
implied_variance_h =
    sigma_implied_h^2 * T_h

forecast_realized_variance_h =
    E_P[sum(r_i^2) over horizon h]

vrp_proxy_h =
    implied_variance_h - forecast_realized_variance_h
```

The implied and forecast realized variances must use the same underlying,
horizon, timestamp, annualization, trading-session and corporate-action
conventions. `ATM_IV^2 * T` is only a proxy for implied variance; it is not the
model-free variance-swap rate. The realized-variance forecast must be
point-in-time and calibrated. EWMA, GARCH and realized-volatility models are
candidate estimators, not authority.

A positive proxy does not automatically justify selling options, and a negative
proxy does not automatically justify buying them. Skew, term structure, jumps,
scheduled events, tail loss, liquidity, bid-ask spread, margin/collateral,
settlement and all trading costs remain required context. Backwardation and
contango are descriptive surface states; neither proves a coming volatility
explosion or collapse.

TrendForge may expose only calibrated descriptive states such as
`IV_RICH_CONTEXT`, `IV_CHEAP_CONTEXT` and `VRP_UNKNOWN`, using historical
point-in-time percentiles rather than a universal fixed volatility-point
threshold. This context cannot authorize state, quantity or execution and
remains subject to File A source, freshness, evidence-family and `R12/R16/R18`
validation gates.

### 17.7 Data and product decision

| Capability | TrendForge status | Reason |
|---|---|---|
| Arbitrage-checked RND/SVI research | `POSTPONE` under mapped `R12/R16/R18` | Needs synchronized liquid option quotes, forward/carry inputs, surface quality and PIT outcome validation |
| Volatility-risk-premium context | `POSTPONE` / research context | Needs a synchronized option surface, PIT realized-variance forecast, costs, calibration and tail-risk controls; it cannot automatically authorize premium sale or purchase |
| Unsigned cash-Gamma concentration | Existing mapped research detail | Public OI supports concentration, not dealer sign or pin probability |
| Signed GEX / zero-Gamma | Scenario only | Dealer-position sign is unobserved |
| Trade-sign cumulative Delta | `POSTPONE` | Requires verified tick trades and aggressor classification |
| Full OFI/microprice | `POSTPONE` | Requires timestamped order-book event data including additions/cancellations |
| VWAP dispersion | Research feature after source proof | Requires complete intraday trades/bars and versioned session conventions |
| 0DTE fixed-threshold strategy | `REJECT` as default | No universal Delta, OI, GEX-distance, theta/gamma or win-rate threshold is validated |
| Probability/EV display | Unavailable | Requires immutable PIT outcomes, costs, calibration and File A `R16/R18` approval |
| OPRA dependency | Out of NSE scope | OPRA is a US options consolidator; it cannot supply NSE contracts |

### 17.8 Primary references used for this audit

- [Breeden and Litzenberger, state-contingent claims from option prices](https://scholars.duke.edu/publication/1112733)
- [Gatheral and Jacquier, arbitrage-free SVI volatility surfaces](https://arxiv.org/abs/1204.0646)
- [Cont, Kukanov and Stoikov, price impact of order-book events](https://arxiv.org/abs/1011.6402)
- [Columbia Foundations of Financial Engineering, Black-Scholes Greeks and delta hedging](https://www.columbia.edu/~mh2078/FoundationsFE/BlackScholes.pdf)
- [Federal Reserve, Expected Stock Returns and Variance Risk Premia](https://www.federalreserve.gov/econres/feds/expected-stock-returns-and-variance-risk-premia.htm)
- [Federal Reserve, The Variance Risk Premium Around the World](https://www.federalreserve.gov/Pubs/ifdp/2011/1035/ifdp1035.htm)
- [NSE Indian Securities Market Review, open-interest definition](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/ismr_full2016.pdf)
- [Cboe DataShop, open-interest and option-analytics conventions](https://datashop.cboe.com/faqs)
- [OPRA official overview](https://www.opraplan.com/)
### 17.9 External corrected-VRP guidance review: 80-85% accepted

The externally supplied corrected VRP framework is approximately 80-85%
suitable as research guidance. It correctly removes VRP as a standalone stock
selector, directional signal, `CONFIRMED` authority, naked-option instruction,
allocation engine and win-probability claim. It also correctly requires
same-horizon implied and forecast realized variance, regime context, skew,
events, liquidity, costs, source freshness and `VRP_UNKNOWN`.

The remaining 15-20% must be corrected before implementation:

1. Remove runtime instructions to consider a volatility trade, risk a fixed
   percentage of capital, construct a tail hedge or scale position size. These
   are execution/allocation responsibilities outside TrendForge.
2. Compare non-overlapping forward-variance intervals instead of directly
   treating overlapping 7-day, 30-day and 90-day VRP observations as
   independent:

```text
forward_variance(T1,T2) =
    (T2 * implied_variance(T2) - T1 * implied_variance(T1))
    / (T2 - T1)
```

   The same transformation and horizon convention must apply to the physical
   realized-variance forecast.
3. Treat `IV_25DeltaPut - IV_ATM` as a skew proxy, not a mathematical
   decomposition of VRP. A decomposition requires strike-integral
   contributions, downside/upside semivariance or corridor variance. Sparse
   data must return `TAIL_DECOMPOSITION_UNKNOWN`.
4. Use block/stationary bootstrap or a point-in-time predictive distribution,
   not an IID bootstrap. Confidence must include option-quote, forecast-model,
   parameter and regime uncertainty.
5. Treat a two-year window, top/bottom 10% threshold, weekly HAR refit and
   three-regime split as hypotheses. Select them only through walk-forward
   stability and out-of-sample tests.
6. Treat scheduled events as event-conditioned risk premia, not data
   contamination. Compare event observations with compatible event baselines.
7. Separate VRP estimation from hedge replication. VRP can be estimated
   without delta hedging; delta hedging is an assumption of an option-based
   monetization or P&L-attribution study.
8. Do not limit stress to three-to-five standard deviations. Include observed
   historical gaps, volatility jumps, skew twists, term-structure shifts,
   spread widening, unavailable hedges and liquidity disappearance, without
   translating stress into executable quantity.
9. Require single-stock option-surface gates for forward construction,
   dividends, corporate actions, strike coverage, settlement conventions,
   non-stale two-sided quotes and liquidity. Failure returns `VRP_UNKNOWN`.
10. Keep order flow, OI and Gamma-wall views inside their correlated evidence
    families. They cannot automatically validate VRP or become independent
    confirmation votes.

Horizon and method must be visible in every descriptive output:

```text
VRP_7D_IV_RICH_CONTEXT
VRP_30D_IV_CHEAP_CONTEXT
VRP_30D_ATM_PROXY
VRP_30D_MODEL_FREE
VRP_EVENT_CONDITIONED
VRP_LOW_CONFIDENCE
VRP_UNKNOWN
```

Each output requires `as_of`, horizon, implied-variance method, physical
forecast model/version, confidence interval, source lineage, event state,
liquidity state, freshness and an explicit failure reason when unknown.

This review does not authorize implementation, strategy selection, allocation,
quantity, hedging instructions or execution. Its purpose is to preserve the
accepted guidance and make the unresolved corrections explicit for the next
independent review.

Additional primary references:

- [Cboe Volatility Index methodology](https://cdn.cboe.com/resources/indices/Volatility_Index_Methodology_Cboe_Volatility_Index.pdf)
- [Federal Reserve, daily options and macroeconomic uncertainty](https://www.federalreserve.gov/econres/ifdp/the-price-of-macroeconomic-uncertainty-evidence-from-daily-options.htm)

### 17.10 Conditional VRP research recommendation contract

This later rule supersedes only the no-recommendation wording in sections 17.6
and 17.9. All mathematical, source-quality, horizon, event, confidence,
stress, correlation and `VRP_UNKNOWN` requirements remain unchanged.

TrendForge may display research context and stress estimates and, when every
File A section 25.23 gate passes, may also display a non-executable research
proposal for:

- a defined-risk volatility or forward-variance relative-value position;
- the option legs and purpose of each leg;
- a research-only lot count calculated from user-entered scenario risk inputs;
- an explicit static or modeled dynamic hedge structure and its assumptions.

Allowed proposal states are:

```text
DEFINED_RISK_SHORT_VOL_RESEARCH
DEFINED_RISK_LONG_VOL_RESEARCH
TENOR_RELATIVE_VALUE_RESEARCH
NO_RESEARCH_PROPOSAL
```

A proposal requires compatible implied and physical variance horizons,
approved point-in-time calibration, a confidence interval that supports the
modeled premium after costs, complete instrument and chain identity, liquid
two-sided quotes, event conditioning, all-leg stress testing and a bounded-loss
structure. The quantity calculation must use stressed realizable loss per lot
and the File A section 25.23 caps. It must return null rather than defaulting
any missing value.

The proposal is hidden-inspector research, not a public state, win-probability
claim, personalized guarantee, broker quantity or order. TrendForge remains
read-only and cannot place, modify or cancel a trade.
