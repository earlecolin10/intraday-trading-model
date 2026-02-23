# Intraday Trading Model — Quant PM + Senior Quant Dev Spec

## A) One-page Trading Model Spec

### Objective
Build an **intraday-only US equities trade planner** that outputs executable trade candidates with:
- ticker
- setup name
- entry, stop, target
- risk-based position size
- confidence score (0–100)
- do-not-trade flags

The system is designed for **same-day exits** (flat by close), robustness, and low-leakage evaluation.

### Universe & Data Defaults
- **Universe**: NYSE/NASDAQ stocks with:
  - last close > $2
  - 20-day average dollar volume > $20M
  - excludes microcaps and known hard-to-borrow outliers (optional hard filter by market cap > $300M if available)
- **Data inputs**:
  - Minute bars (raw intraday OHLCV)
  - Daily bars (split/dividend adjusted)
  - Optional NBBO top-of-book for better spread estimates (fallback proxy if unavailable)
- **Trading session**: 09:30–16:00 ET, no extended hours for signals.

### Target Timeframe (chosen)
- **Primary bar size: 5-minute** for signal generation and execution logic.
- Why:
  1. Better noise/latency tradeoff than 1-minute for broad universe scanning.
  2. Preserves enough granularity for day-trading entries/stops.
  3. Lower false breaks than 1-minute and more opportunities than 15-minute.
- Secondary calculations:
  - 1-minute for slippage/spread proxy and opening volatility diagnostics.
  - Daily for ATR/regime/context filters.

### Market Regime Logic (trend vs chop)
Use a simple two-layer regime gate:
1. **Index regime (SPY, optional QQQ)** computed on 5-minute bars up to decision time:
   - Trend day candidate if:
     - `abs(SPY_return_09:30_to_now) >= 0.35%` and
     - `SPY_ADX_14_5m >= 18` and
     - price on same side of session VWAP for >= 70% of elapsed bars.
2. **Symbol regime**:
   - Trend-friendly if:
     - `|symbol - VWAP| / VWAP >= 0.20%` and
     - `rolling_6bar_directionality >= 0.6` (fraction of bars in same direction)
   - Chop if above fails and realized volatility high with low net displacement.

Setups are only enabled in compatible regimes.

### Candidate Setups (3)

#### Setup 1 — ORB-V (Opening Range Breakout with Relative Volume)
- Use first **15 minutes** (09:30–09:45) as opening range.
- Long trigger after 09:45 when a 5-minute bar closes above OR high by buffer and RVOL confirms.
- Best on trend regime days.

#### Setup 2 — VWAP Pullback Continuation (VWAP-PC)
- Trend continuation setup after initial impulse.
- Long when price reclaims/holds above VWAP after pullback with higher low and volume re-expansion.
- Avoid in chop regime.

#### Setup 3 — Prior-Day Liquidity Sweep Reversal (PDL-SR)
- Mean-reversion/reversal setup only in non-trend/chop or exhaustion context.
- Long when price sweeps below prior-day low and reclaims it with confirmation.
- Strict time cutoff (no new entries after 14:30 ET).

### Risk & Portfolio Controls
- **Per-trade risk**: fixed fractional, default **0.50% of equity**.
- **Max open positions**: 4.
- **Max risk deployed simultaneously**: 1.5% of equity.
- **Max daily loss hard-stop**: 1.5% of start-of-day equity (stop opening new trades; flatten discretionary entries).
- **Time exits**:
  - Hard flat all positions by 15:55 ET.
  - Setup-specific max hold time (e.g., ORB 120 min, VWAP-PC 150 min, PDL-SR 90 min).
- **Market halt filter**: stop trading if LULD/halt event seen for symbol intraday.

### Confidence Score (0–100)
- Score based on out-of-sample walk-forward performance for each setup + context bucket.
- Confidence = weighted blend of:
  1. OOS win rate stability
  2. OOS expectancy in R
  3. recent drawdown penalty
  4. sample size reliability penalty
- Low sample size or unstable recent performance compresses score toward 50.

### Do-Not-Trade Flags
Generated per symbol at decision time:
- `low_liquidity`: intraday dollar volume percentile below threshold.
- `wide_spread`: spread proxy > threshold bps.
- `excess_volatility`: intraday realized vol above setup-specific cap.
- `news_risk`: earnings day / major scheduled macro window / corporate headline blackout (if feed available).
- `borrow_or_short_restrict`: for short trades only.
- `late_session_new_entry`: after setup cutoff time.

---

## B) Locked Definitions (exact rules)

All computations use data **up to current bar close t**. Orders become active at **t+1 bar open** unless otherwise specified.

### Shared Definitions
- `OR_high`, `OR_low`: max/min of 5-minute highs/lows from 09:30:00 to 09:44:59 ET.
- `ATR_d`: 14-day ATR from adjusted daily bars, evaluated as of prior close.
- `RVOL_t`: cumulative intraday volume up to t divided by 20-day median cumulative volume profile at same minute-of-day.
- `SpreadProxy_bps_t = 10000 * (High_t - Low_t) / Close_t * k`, with `k=0.25` default as effective-spread proxy when no NBBO.
- `R_per_share = |Entry - Stop|`.
- `Qty_raw = floor((Equity * risk_frac) / R_per_share)`.
- `Qty_final = min(Qty_raw, liquidity_cap_qty, portfolio_risk_cap_qty)`.
- Long/short symmetry applies where noted.

### Setup 1: ORB-V (Long)
**Eligibility window**: 09:45–11:30 ET.

**Entry condition at bar t close**:
1. `Close_t > OR_high * (1 + 0.0005)` (5 bps breakout buffer)
2. `Volume_t >= 1.5 * median(Volume_{t-20:t-1})`
3. `RVOL_t >= 1.2`
4. Regime = trend-friendly.

**Entry price**:
- `Entry = max(OR_high*(1+0.0005), Open_{t+1})` via stop-limit logic:
  - stop trigger at `OR_high*(1+0.0005)`
  - limit cap at `trigger * (1+0.0008)` to control slippage.

**Stop loss**:
- `Stop = min(Low_t, VWAP_t, OR_high) - 0.05 * ATR_d`.
- Hard floor: if stop distance < 0.15% of entry, reject trade (too tight / noise-prone).

**Target(s)**:
- `Target1 = Entry + 1.0R`
- `Target2 = Entry + 2.0R`
- Exit plan: take 50% at T1, trail remainder by 8-EMA(5m) or exit at T2 or 15:55.

### Setup 2: VWAP Pullback Continuation (Long)
**Eligibility window**: 10:00–14:30 ET.

**Preconditions**:
1. Session impulse established: session high-to-low displacement since open >= 0.8 * ATR_d/√14.
2. Price above VWAP for >= 60% of last 10 bars.

**Entry condition at t close**:
1. Pullback touched zone `[VWAP_t - 0.05%, VWAP_t + 0.05%]` in last 3 bars.
2. Current bar closes above prior bar high (micro structure reclaim).
3. `Volume_t >= 1.2 * median(Volume_{t-20:t-1})`.

**Entry price**:
- Buy stop at `High_t + 0.02%`, active next bar, limit cap +0.06%.

**Stop loss**:
- `Stop = min(swing_low_last_5bars, VWAP_t - 0.10%, Entry - 0.6R_ref)` where `R_ref = ATR_5m_20`.

**Target(s)**:
- `Target = nearest(max(session_high, Entry + 1.8R), Entry + 1.2R minimum)`.
- If not hit by 15:30 and momentum decays (3-bar EMA slope <= 0), flatten.

### Setup 3: Prior-Day Low Sweep Reversal (Long)
**Eligibility window**: 09:50–14:30 ET.

**Context filter**:
- Not a strong trend-down day in index (`SPY_ADX_14_5m < 25` or SPY not making fresh LOD in last 3 bars).

**Entry condition at t close**:
1. Intraday low pierced prior-day low by at least 0.10% (`Low_session <= PDL*0.999`).
2. Reclaim confirmation: close back above `PDL`.
3. Reversal confirmation: bullish close and close in top 30% of bar range.
4. RVOL at event >= 1.3.

**Entry price**:
- Buy limit on mild retest: `Entry = max(PDL, Close_t - 0.03%)` during next 2 bars; otherwise marketable limit at t+3 open if still valid.

**Stop loss**:
- `Stop = session_low_after_sweep - 0.05%`.

**Target(s)**:
- `Target1 = VWAP`
- `Target2 = Entry + 1.5R` (whichever comes first for partials, then trail to VWAP fail).

### Transaction Cost / Slippage Locked Model
- Commission = 0.
- Slippage model per side:
  - Base: 2 bps for high-liquidity names.
  - Add `0.5 * SpreadProxy_bps_t`.
  - Add impact term `1.0 * sqrt(order_notional / bar_dollar_volume)` bps.
- Total round-trip cost in backtest = entry side + exit side slippage + spread proxy component.
- Sensitivity runs: base, 1.5x, 2.0x cost multipliers.

### Do-not-trade hard thresholds
- `avg_dollar_vol_20d < $20M` → block.
- `SpreadProxy_bps_t > 18 bps` → block.
- `R_per_share / Entry > 1.2%` for continuation setups → block.
- `minutes_to_close < 30` for new entries → block.
- scheduled earnings today (if feed) → block for first 30 mins and final 60 mins.

---

## C) Proposed Python Project Structure + Key Function Signatures

```text
intraday-trading-model/
  README.md
  pyproject.toml
  config/
    default.yaml
    costs.yaml
  data/
    raw/
    processed/
  src/
    __init__.py
    main.py
    universe.py
    data_ingest.py
    features.py
    regime.py
    setups/
      __init__.py
      orb_v.py
      vwap_pc.py
      pdl_sr.py
    scoring.py
    risk.py
    planner.py
    backtest/
      __init__.py
      engine.py
      fills.py
      metrics.py
      walkforward.py
    report.py
    schemas.py
  tests/
    test_features.py
    test_setups_orb.py
    test_risk.py
    test_backtest_no_lookahead.py
```

### Core dataclasses / schemas
```python
# src/schemas.py
from dataclasses import dataclass
from typing import Literal, List, Dict

@dataclass
class Bar:
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class TradePlan:
    ticker: str
    setup: Literal["ORB_V", "VWAP_PC", "PDL_SR"]
    side: Literal["LONG", "SHORT"]
    entry_type: Literal["STOP_LIMIT", "LIMIT", "MKTABLE_LIMIT"]
    entry_price: float
    stop_price: float
    target_prices: List[float]
    quantity: int
    confidence: float   # 0-100
    do_not_trade_flags: Dict[str, bool]
    created_at: str
    valid_until: str
```

### Module signatures
```python
# src/data_ingest.py
def load_minute_bars(tickers: list[str], start: str, end: str) -> dict[str, "pd.DataFrame"]: ...
def load_daily_bars(tickers: list[str], start: str, end: str) -> dict[str, "pd.DataFrame"]: ...
def clean_minute_bars(df: "pd.DataFrame") -> "pd.DataFrame": ...

# src/features.py
def build_intraday_features(min_df: "pd.DataFrame", daily_df: "pd.DataFrame") -> "pd.DataFrame": ...
def compute_opening_range(min_df: "pd.DataFrame", minutes: int = 15) -> tuple[float, float]: ...
def compute_rvol(min_df: "pd.DataFrame", hist_profiles: "pd.DataFrame") -> "pd.Series": ...

# src/regime.py
def detect_market_regime(spy_df_5m: "pd.DataFrame") -> "pd.Series": ...
def detect_symbol_regime(sym_df_5m: "pd.DataFrame") -> "pd.Series": ...

# src/setups/orb_v.py
def detect_orb_v_candidates(df_5m: "pd.DataFrame", regime: "pd.Series") -> "pd.DataFrame": ...
def build_orb_v_plan(row: "pd.Series", equity: float, cfg: dict) -> TradePlan | None: ...

# src/setups/vwap_pc.py
def detect_vwap_pc_candidates(df_5m: "pd.DataFrame", regime: "pd.Series") -> "pd.DataFrame": ...
def build_vwap_pc_plan(row: "pd.Series", equity: float, cfg: dict) -> TradePlan | None: ...

# src/setups/pdl_sr.py
def detect_pdl_sr_candidates(df_5m: "pd.DataFrame", regime: "pd.Series") -> "pd.DataFrame": ...
def build_pdl_sr_plan(row: "pd.Series", equity: float, cfg: dict) -> TradePlan | None: ...

# src/scoring.py
def compute_confidence_score(setup: str, context_key: str, oos_stats: dict) -> float: ...
def rank_trade_plans(plans: list[TradePlan]) -> list[TradePlan]: ...

# src/risk.py
def position_size(entry: float, stop: float, equity: float, risk_frac: float, liquidity_cap: int) -> int: ...
def apply_portfolio_limits(plans: list[TradePlan], current_exposure: dict, cfg: dict) -> list[TradePlan]: ...
def check_do_not_trade_flags(feature_row: "pd.Series", cfg: dict) -> dict[str, bool]: ...

# src/planner.py
def generate_trade_plans(snapshot: dict[str, "pd.DataFrame"], equity: float, cfg: dict) -> list[TradePlan]: ...

# src/backtest/engine.py
def run_backtest(plans: list[TradePlan], bars: dict[str, "pd.DataFrame"], cost_model_cfg: dict) -> "pd.DataFrame": ...

# src/backtest/walkforward.py
def walkforward_splits(start: str, end: str, train_months: int = 6, test_months: int = 1) -> list[tuple[str, str, str, str]]: ...
def run_walkforward(universe: list[str], start: str, end: str, cfg: dict) -> dict: ...

# src/backtest/metrics.py
def compute_trade_metrics(trades: "pd.DataFrame") -> dict: ...
def compute_regime_breakdown(trades: "pd.DataFrame") -> "pd.DataFrame": ...
def compute_bad_day_analysis(trades: "pd.DataFrame", pnl_daily: "pd.Series") -> dict: ...

# src/report.py
def build_report(results: dict, out_dir: str) -> None: ...
```

### Chosen minimal feature set + rationale / guarded failure mode
1. **Opening range high/low (15m)**
   - Why: captures early price discovery / institutional direction.
   - Guards against: random mid-session breakouts without context.
2. **Session VWAP and distance-to-VWAP**
   - Why: intraday value anchor widely used by execution desks.
   - Guards against: chasing overly extended moves.
3. **Prior-day high/low and close location**
   - Why: key liquidity levels where stop clusters often sit.
   - Guards against: entering reversal setups away from meaningful levels.
4. **ATR_d (14) + intraday realized vol (rolling)**
   - Why: normalize stop distance and reject unstable volatility states.
   - Guards against: stop placements too tight/wide across symbols.
5. **Relative volume (RVOL) + bar volume spike factor**
   - Why: confirms participation on breakouts/reclaims.
   - Guards against: low-liquidity false breaks.
6. **Dollar volume + spread proxy bps**
   - Why: tradability and cost realism.
   - Guards against: paper alpha that disappears after costs.
7. **Index trend filter (SPY/QQQ optional)**
   - Why: aligns single-name setups with market tape.
   - Guards against: taking continuation trades in hostile broad regime.

---

## D) Prioritized Implementation Checklist

1. **Data integrity layer first**
   - Build ingest/cleaning, timezone normalization, session filters, bad-bar handling.
   - Why first: every later module depends on trustworthy time alignment.
2. **Feature builder with strict as-of timestamps**
   - Implement OR, VWAP, PDL/PDH, ATR joins, RVOL profiles.
   - Add unit tests ensuring no future leakage.
3. **Setup detectors (no scoring yet)**
   - Code ORB-V, VWAP-PC, PDL-SR as deterministic rule engines.
   - Validate event counts and sanity checks by day.
4. **Trade planner + risk manager**
   - Entry/stop/target materialization, sizing, do-not-trade flags, portfolio limits.
5. **Execution simulator / backtest engine with costs**
   - Bar-based fill logic, stop/target precedence rules, slippage/spread model.
6. **Walk-forward framework**
   - 6M train / 1M test rolling.
   - Keep train for parameter selection only; report only concatenated OOS.
7. **Scoring/ranking layer**
   - Derive confidence from OOS stats by setup/context bucket.
8. **Robustness suite**
   - Parameter perturbation ±10–20%, cost multipliers, regime breakdown, bad-day attribution.
9. **Reporting & productionization hooks**
   - Daily candidate report JSON + metrics dashboards + audit logs.
10. **Optional ML only after baseline edge**
   - If used, monotonic/regularized models with purged time-series CV and strict feature availability constraints.

---

## 4) Backtest Design (explicit)

### Walk-forward protocol
- Date range split into rolling windows:
  - Train: 6 months
  - Test: next 1 month
  - Roll forward by 1 month
- For each fold:
  1. Fit/tune thresholds only on train.
  2. Freeze params.
  3. Generate plans and execute on test month.
- Concatenate all test folds for final OOS metrics.

### Leakage controls
- Feature timestamps as-of bar close t; orders at t+1 earliest.
- Daily features from prior fully completed day unless explicitly available pre-open.
- No using day’s full-volume totals or end-of-day high/low in live-decision features.

### Cost model
- Commission: 0.
- Slippage/spread as locked above.
- Sensitivity cases: base, 1.5x, 2.0x.

### Evaluation metrics
- **Expectancy in R** (primary).
- Win rate.
- Profit factor.
- Max drawdown (equity curve).
- Average trade duration (minutes).
- Turnover (notional/day and trades/day).
- Optional: Sharpe/Sortino on daily returns.

### Robustness checks
- Parameter sensitivity: OR window (10/15/20), RVOL threshold ±0.2, stop buffer variants.
- Regime breakdown: trend vs chop vs high-vol event days.
- “Bad days” analysis:
  - top 10 loss days contribution to total drawdown,
  - setup-wise damage,
  - whether risk caps would have mitigated.

---

## E) Example Final Output Schema (single trade candidate JSON)

```json
{
  "as_of": "2026-03-17T10:35:00-04:00",
  "ticker": "NVDA",
  "setup": "ORB_V",
  "side": "LONG",
  "regime": {
    "market": "TREND_UP",
    "symbol": "TREND"
  },
  "entry": {
    "type": "STOP_LIMIT",
    "stop_trigger": 912.45,
    "limit_price": 913.18,
    "time_in_force": "DAY",
    "valid_until": "2026-03-17T11:30:00-04:00"
  },
  "risk": {
    "stop_price": 905.90,
    "target_prices": [919.00, 925.55],
    "r_per_share": 6.55,
    "account_equity": 250000,
    "risk_fraction": 0.005,
    "recommended_quantity": 190,
    "max_portfolio_risk_check": "PASS"
  },
  "cost_assumptions": {
    "commission_per_share": 0.0,
    "expected_slippage_bps_per_side": 4.8,
    "spread_proxy_bps": 6.5
  },
  "confidence": {
    "score_0_100": 68,
    "drivers": {
      "oos_expectancy_r": 0.18,
      "oos_win_rate": 0.47,
      "sample_size": 312,
      "recent_drawdown_penalty": -6
    }
  },
  "do_not_trade_flags": {
    "low_liquidity": false,
    "wide_spread": false,
    "excess_volatility": false,
    "news_risk": false,
    "late_session_new_entry": false,
    "daily_loss_limit_hit": false
  },
  "execution_notes": [
    "Flat all remaining position by 15:55 ET.",
    "Cancel unfilled order at setup validity timeout.",
    "If partial fill < 30% by 2 bars, reduce size by 50%."
  ]
}
```

---

## Optional clarifications (answer only if you want custom tuning)
1. Are short-selling setups in scope from day one, or long-only first release?
2. Broker/execution venue constraints (IBKR, Alpaca, DAS) for order type compatibility?
3. Do you want earnings/news feed integration in v1, or start with pure price/volume-only?
4. Any symbol exclusions (biotech, leveraged ETFs, ADRs)?
5. Preferred risk budget defaults (0.25%, 0.5%, or 1.0% per trade)?
