"""
================================================================================
 OPTIONS TUTOR  v2  —  value the STOCK, then value the OPTION, then decide
================================================================================

WHAT'S NEW IN v2
    v1 taught you to value an option (Black-Scholes, the Greeks, breakeven).
    v2 adds the other half a real analyst does: valuing the UNDERLYING STOCK
    (a Buffett-style DCF + quality checks) to form a reasoned DIRECTIONAL LEAN,
    then MARRYING that lean to the option to judge if it's a good buy —
    symmetrically for CALLS *and* PUTS.

THE ONE IDEA TO HOLD ONTO
    Value investing gives you a DESTINATION (what a stock is worth).
    An option gives you a DEADLINE (it expires).
    A cheap stock can stay cheap past your expiration. So we don't "predict."
    We (1) pick a direction from fundamentals, (2) check whether the move we'd
    need is even plausible, and (3) check whether the option's implied move is
    bigger or smaller than the move our thesis implies. That last one is the
    closest thing to an edge that exists.

HONEST LIMITS (read this)
    You cannot remove uncertainty — it's the product. Implied volatility is the
    market's PRICE for it. Beyond the unforeseeable macro/black-swan events
    (weather, war, shocks), ordinary surprises remain too: earnings, guidance,
    competition, sentiment. We can't delete these. We can only turn a vague
    hunch into an explicit, checkable thesis and size our bet accordingly.
    This is an EDUCATIONAL tool. Not financial advice. It predicts nothing.

HOW TO RUN
    pip install streamlit yfinance
    streamlit run options_tutor.py
    (No internet? Everything works on built-in Demo data.)
================================================================================
"""

import math
import datetime as dt
import random

import pandas as pd
import streamlit as st

# =============================================================================
#  PART 1 — BLACK-SCHOLES ENGINE  (pure math; unit-tested vs textbook values)
# =============================================================================

SQRT2 = math.sqrt(2.0)
SQRT2PI = math.sqrt(2.0 * math.pi)


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / SQRT2))


def norm_pdf(x):
    return math.exp(-0.5 * x * x) / SQRT2PI


def _d1_d2(S, K, T, r, sigma, q):
    vt = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / vt
    return d1, d1 - vt


def bs_price(S, K, T, r, sigma, q, kind):
    """Black-Scholes fair value of a European call/put."""
    if T <= 0:
        return max(S - K, 0.0) if kind == "call" else max(K - S, 0.0)
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    dq, dr = math.exp(-q * T), math.exp(-r * T)
    if kind == "call":
        return S * dq * norm_cdf(d1) - K * dr * norm_cdf(d2)
    return K * dr * norm_cdf(-d2) - S * dq * norm_cdf(-d1)


def greeks(S, K, T, r, sigma, q, kind):
    """Sensitivities in trader-friendly units (per $1 stock, per day, per 1% IV/rate)."""
    if T <= 0 or sigma <= 0:
        d = 1.0 if (kind == "call" and S > K) else (-1.0 if (kind == "put" and S < K) else 0.0)
        return dict(delta=d, gamma=0.0, theta_day=0.0, vega_1pct=0.0, rho_1pct=0.0)
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    dq, dr = math.exp(-q * T), math.exp(-r * T)
    gamma = dq * norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * dq * norm_pdf(d1) * math.sqrt(T)
    if kind == "call":
        delta = dq * norm_cdf(d1)
        theta = (-S * dq * norm_pdf(d1) * sigma / (2 * math.sqrt(T))
                 - r * K * dr * norm_cdf(d2) + q * S * dq * norm_cdf(d1))
        rho = K * T * dr * norm_cdf(d2)
    else:
        delta = -dq * norm_cdf(-d1)
        theta = (-S * dq * norm_pdf(d1) * sigma / (2 * math.sqrt(T))
                 + r * K * dr * norm_cdf(-d2) - q * S * dq * norm_cdf(-d1))
        rho = -K * T * dr * norm_cdf(-d2)
    return dict(delta=delta, gamma=gamma, theta_day=theta / 365.0,
                vega_1pct=vega / 100.0, rho_1pct=rho / 100.0)


def implied_vol(price, S, K, T, r, q, kind, lo=1e-4, hi=5.0):
    """Solve for the volatility the market is assuming (bisection)."""
    intrinsic = max(S - K, 0.0) if kind == "call" else max(K - S, 0.0)
    if price <= intrinsic + 1e-9:
        return float("nan")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if bs_price(S, K, T, r, mid, q, kind) > price:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# =============================================================================
#  PART 2 — OPTION-LEVEL ANALYTICS
# =============================================================================

def intrinsic_value(S, K, kind):
    return max(S - K, 0.0) if kind == "call" else max(K - S, 0.0)


def moneyness_label(S, K, kind):
    if abs(S - K) / K < 0.01:
        return "At-the-money (ATM)"
    return "In-the-money (ITM)" if intrinsic_value(S, K, kind) > 0 else "Out-of-the-money (OTM)"


def breakeven_price(K, premium, kind):
    return K + premium if kind == "call" else K - premium


def prob_itm_riskneutral(S, K, T, r, sigma, q, kind):
    if T <= 0 or sigma <= 0:
        return float("nan")
    _, d2 = _d1_d2(S, K, T, r, sigma, q)
    return norm_cdf(d2) if kind == "call" else norm_cdf(-d2)


def iv_implied_move(S, iv, days):
    """The ~1-sigma move (in $) the option's IV is pricing in over `days`."""
    if iv != iv or iv <= 0:
        return float("nan")
    return S * iv * math.sqrt(days / 365.0)


def payoff_curve(K, premium, kind, S, n=61):
    lo, hi = max(0.01, S * 0.6), S * 1.4
    xs, ys = [], []
    for i in range(n):
        p = lo + (hi - lo) * i / (n - 1)
        intr = max(p - K, 0.0) if kind == "call" else max(K - p, 0.0)
        xs.append(round(p, 2)); ys.append(intr - premium)
    return pd.DataFrame({"P/L per share ($)": ys},
                        index=pd.Index(xs, name="Stock price at expiry ($)"))


def value_vs_spot_curve(K, T, r, sigma, q, kind, S, n=61):
    lo, hi = max(0.01, S * 0.7), S * 1.3
    xs, ys = [], []
    for i in range(n):
        p = lo + (hi - lo) * i / (n - 1)
        xs.append(round(p, 2)); ys.append(bs_price(p, K, T, r, sigma, q, kind))
    return pd.DataFrame({"Option value today ($)": ys},
                        index=pd.Index(xs, name="Stock price ($)"))


# =============================================================================
#  PART 3 — FUNDAMENTAL (STOCK) VALUATION  — pure math, unit-tested
# =============================================================================

def dcf_fair_value(fcf0, g_high, years, g_term, discount, net_cash, shares):
    """
    Discounted Cash Flow — the value investor's core tool.
    Project free cash flow, discount it back to today, add net cash, divide by
    shares. Returns fair value PER SHARE.  (Assumes fcf0, net_cash in same units
    as each other, e.g. $ billions; shares in the same billions.)
    """
    if discount <= g_term:
        return float("nan")
    pv, f = 0.0, fcf0
    for t in range(1, years + 1):
        f = fcf0 * (1 + g_high) ** t
        pv += f / (1 + discount) ** t
    terminal = f * (1 + g_term) / (discount - g_term)      # Gordon growth model
    pv += terminal / (1 + discount) ** years
    return (pv + net_cash) / shares


def peg_ratio(pe, earnings_growth):
    """P/E divided by growth %. <1 is often called cheap-for-growth, >2 pricey."""
    if earnings_growth is None or earnings_growth <= 0 or pe is None:
        return float("nan")
    return pe / (earnings_growth * 100.0)


def quality_score(f):
    """
    Score business QUALITY 0-100 from profitability, growth, and balance sheet.
    Buffett's lens: a wonderful business at a fair price beats a fair business
    at a wonderful price. Returns (score, bullet_list).
    """
    pts, bullets = 0, []

    def band(val, good, great, label, unit="%", higher=True):
        nonlocal pts
        if val is None or val != val:
            bullets.append(f"• {label}: n/a"); return
        v = val * 100 if unit == "%" else val
        if (v >= great) if higher else (v <= great):
            pts += 25; tag = "excellent"
        elif (v >= good) if higher else (v <= good):
            pts += 15; tag = "solid"
        else:
            pts += 5; tag = "weak"
        shown = f"{v:.1f}{unit}" if unit == "%" else f"{v:.2f}"
        bullets.append(f"• {label}: {shown} ({tag})")

    band(f.get("roe"), 15, 25, "Return on equity")
    band(f.get("net_margin"), 10, 20, "Net profit margin")
    band(f.get("rev_growth"), 5, 12, "Revenue growth")
    band(f.get("debt_to_equity"), 1.5, 0.7, "Debt / equity", unit="x", higher=False)
    return min(pts, 100), bullets


def directional_lean(f, fair_value):
    """
    Turn valuation + quality into a REASONED DIRECTIONAL LEAN (not a forecast).
    Returns dict(label, direction in {up,down,neutral}, confidence, mos, bullets).
    """
    price = f["price"]

    # ---- valuation gap (margin of safety) ----
    if f.get("is_index"):
        # value an index by its P/E vs long-run average, not a company DCF
        mos = (f["index_pe_avg"] - f["index_pe"]) / f["index_pe"]  # cheap if current PE < avg
        val_note = (f"Index P/E {f['index_pe']:.1f} vs long-run ~{f['index_pe_avg']:.1f} "
                    f"→ market looks {'cheap' if mos > 0 else 'rich'} vs history.")
    else:
        mos = (fair_value - price) / price
        val_note = f"DCF fair value ${fair_value:,.2f} vs price ${price:,.2f} → margin of safety {mos*100:+.1f}%."

    # ---- primary lean from the valuation gap ----
    if mos >= 0.25:
        label, direction = "Bullish", "up"
    elif mos >= 0.10:
        label, direction = "Lean bullish", "up"
    elif mos <= -0.25:
        label, direction = "Bearish", "down"
    elif mos <= -0.10:
        label, direction = "Lean bearish", "down"
    else:
        label, direction = "Neutral", "neutral"

    q_score, _ = quality_score(f)
    bullets = [val_note, f"Business-quality score: {q_score}/100."]

    # ---- quality nuance (Buffett-style) ----
    confidence = "moderate"
    if direction == "up" and q_score < 40:
        bullets.append("⚠️ Cheap BUT low quality — classic **value-trap** risk. Confidence capped.")
        confidence = "low"
    elif direction == "up" and q_score >= 70:
        bullets.append("High-quality AND undervalued — the strongest value setup.")
        confidence = "high"
    elif direction == "down" and q_score < 40:
        bullets.append("Overvalued AND weak quality — a firmer bearish read.")
        confidence = "high"
    elif direction == "down" and q_score >= 70:
        bullets.append("Great company, just **expensive** — Buffett would wait, not short blindly.")
        confidence = "moderate"
    if direction == "neutral":
        confidence = "low"

    # ---- crowd / sentiment (contrarian-aware, minor input) ----
    tgt = f.get("analyst_target")
    if tgt:
        crowd = (tgt - price) / price
        if (crowd > 0.05 and direction == "up") or (crowd < -0.05 and direction == "down"):
            bullets.append(f"Analyst target ${tgt:,.0f} ({crowd*100:+.0f}%) agrees with our lean.")
        elif abs(crowd) > 0.05:
            bullets.append(f"Analyst target ${tgt:,.0f} ({crowd*100:+.0f}%) leans the OTHER way — "
                           f"a value opportunity if we're right, or a warning if we're not.")

    return dict(label=label, direction=direction, confidence=confidence, mos=mos, bullets=bullets)


def analyze_full(opt, fair_value, lean):
    """
    Marry the stock lean to the option. Returns a transparent combined verdict
    that works identically for calls and puts.
    """
    S, K, kind, prem = opt["S"], opt["K"], opt["kind"], opt["market_price"]
    iv = opt["iv"]
    be = breakeven_price(K, prem, kind)
    mos = lean["mos"]

    direction_match = (kind == "call" and lean["direction"] == "up") or \
                      (kind == "put" and lean["direction"] == "down")

    if kind == "call":
        be_move = (be - S) / S
    else:
        be_move = (S - be) / S

    # Does the valuation gap (our "room") reach the option's breakeven?
    destination_clears = abs(mos) >= be_move if lean["direction"] != "neutral" else False

    # Edge: is the option's implied move smaller than our thesis move? (cheap for our view)
    ivm = iv_implied_move(S, iv, opt["dte"])          # $ 1-sigma move priced by IV
    fund_move = abs(mos) * S                           # $ gap to fair value
    if ivm == ivm and ivm > 0:
        edge_ratio = fund_move / ivm
        if edge_ratio >= 1.25:
            edge = "cheap"      # market pricing a smaller move than our thesis implies
        elif edge_ratio <= 0.8:
            edge = "rich"
        else:
            edge = "fair"
    else:
        edge_ratio, edge = float("nan"), "unknown"

    # ---- transparent scoring ----
    score = 0
    if direction_match:
        score += 2
    if destination_clears:
        score += 2
    else:
        score -= 2
    if edge == "cheap":
        score += 1
    elif edge == "rich":
        score -= 1
    if lean["confidence"] == "high":
        score += 1
    elif lean["confidence"] == "low":
        score -= 1

    recommend_buy = direction_match and (score >= 3)

    return dict(recommend_buy=recommend_buy, score=score, breakeven=be, be_move=be_move,
                direction_match=direction_match, destination_clears=destination_clears,
                iv_move=ivm, fund_move=fund_move, edge=edge, edge_ratio=edge_ratio)


# =============================================================================
#  PART 4 — BUILT-IN DEMO DATA (options + matching fundamentals) — offline-proof
# =============================================================================

RISK_FREE_DEFAULT = 0.045


def _mk_opt(ticker, name, S, K, kind, dte, iv, hv, q, scenario):
    T = dte / 365.0
    return dict(ticker=ticker, name=name, S=S, K=K, kind=kind, dte=dte, T=T,
                r=RISK_FREE_DEFAULT, q=q, iv=iv, hv=hv,
                market_price=round(bs_price(S, K, T, RISK_FREE_DEFAULT, iv, q, kind), 2),
                scenario=scenario)


DEMO_OPTIONS = [
    _mk_opt("AAPL", "Apple", 190, 195, "call", 30, 0.28, 0.24, 0.005,
            dict(dir="bull", move=0.05, horizon=20,
                 text="You think Apple rises ~5% over the next 3 weeks after earnings.")),
    _mk_opt("TSLA", "Tesla", 250, 280, "call", 14, 0.75, 0.55, 0.0,
            dict(dir="bull", move=0.06, horizon=10,
                 text="Feeling lucky: you think Tesla pops ~6% in the next week and a half.")),
    _mk_opt("TSLA", "Tesla", 250, 220, "put", 45, 0.65, 0.55, 0.0,
            dict(dir="bear", move=0.10, horizon=30,
                 text="You think Tesla is badly overvalued and falls ~10% over the next month.")),
    _mk_opt("SPY", "S&P 500 ETF", 500, 500, "put", 45, 0.18, 0.18, 0.013,
            dict(dir="bear", move=0.04, horizon=30,
                 text="You expect a ~4% market pullback over the next month and want a put.")),
    _mk_opt("KO", "Coca-Cola", 60, 55, "call", 60, 0.16, 0.18, 0.030,
            dict(dir="bull", move=0.06, horizon=45,
                 text="You think Coca-Cola grinds up ~6% over the next 6 weeks.")),
    _mk_opt("NVDA", "Nvidia", 120, 120, "call", 7, 0.55, 0.50, 0.0,
            dict(dir="bull", move=0.03, horizon=5,
                 text="You think Nvidia jumps ~3% in the next 5 days on hype.")),
    _mk_opt("PFE", "Pfizer", 27, 30, "call", 60, 0.30, 0.28, 0.06,
            dict(dir="bull", move=0.12, horizon=45,
                 text="You think beaten-down Pfizer recovers ~12% over the next 6 weeks.")),
]

# Fundamentals keyed by ticker. Numbers are ILLUSTRATIVE (demo), not live quotes.
FUNDAMENTALS = {
    "PFE": dict(ticker="PFE", name="Pfizer", price=27, shares=5.66, fcf=12, g_high=0.03,
                g_term=0.025, discount=0.080, net_cash=-40, years=10,
                pe=11, forward_pe=10, pb=1.7, roe=0.12, net_margin=0.18, rev_growth=-0.02,
                earnings_growth=0.04, debt_to_equity=0.75, beta=0.65, div_yield=0.058,
                analyst_target=32, wk52_low=25, wk52_high=39),
    "KO": dict(ticker="KO", name="Coca-Cola", price=60, shares=4.31, fcf=9.8, g_high=0.06,
               g_term=0.030, discount=0.070, net_cash=-27, years=10,
               pe=24, forward_pe=22, pb=10, roe=0.40, net_margin=0.23, rev_growth=0.05,
               earnings_growth=0.06, debt_to_equity=1.6, beta=0.60, div_yield=0.030,
               analyst_target=65, wk52_low=52, wk52_high=64),
    "AAPL": dict(ticker="AAPL", name="Apple", price=190, shares=15.3, fcf=105, g_high=0.075,
                 g_term=0.030, discount=0.085, net_cash=-30, years=10,
                 pe=29, forward_pe=27, pb=45, roe=1.50, net_margin=0.26, rev_growth=0.03,
                 earnings_growth=0.07, debt_to_equity=1.5, beta=1.25, div_yield=0.005,
                 analyst_target=205, wk52_low=164, wk52_high=199),
    "NVDA": dict(ticker="NVDA", name="Nvidia", price=120, shares=24.6, fcf=45, g_high=0.22,
                 g_term=0.035, discount=0.095, net_cash=25, years=10,
                 pe=55, forward_pe=35, pb=50, roe=1.10, net_margin=0.50, rev_growth=1.00,
                 earnings_growth=0.60, debt_to_equity=0.20, beta=1.70, div_yield=0.0003,
                 analyst_target=135, wk52_low=80, wk52_high=140),
    "TSLA": dict(ticker="TSLA", name="Tesla", price=250, shares=3.2, fcf=5, g_high=0.14,
                 g_term=0.030, discount=0.105, net_cash=20, years=10,
                 pe=65, forward_pe=55, pb=10, roe=0.15, net_margin=0.09, rev_growth=0.12,
                 earnings_growth=-0.05, debt_to_equity=0.10, beta=2.00, div_yield=0.0,
                 analyst_target=220, wk52_low=180, wk52_high=280),
    "SPY": dict(ticker="SPY", name="S&P 500 ETF", price=500, is_index=True,
                index_pe=22.0, index_pe_avg=16.5, div_yield=0.013,
                analyst_target=None),
}


def compute_fair_value(f, assumptions=None):
    """Fair value per share (DCF) using stored or user-overridden assumptions."""
    if f.get("is_index"):
        return float("nan")
    a = assumptions or {}
    return dcf_fair_value(
        f["fcf"], a.get("g_high", f["g_high"]), a.get("years", f["years"]),
        a.get("g_term", f["g_term"]), a.get("discount", f["discount"]),
        f["net_cash"], f["shares"])


# =============================================================================
#  PART 5 — LIVE DATA via yfinance (optional; every call is failure-wrapped)
# =============================================================================

def list_expirations(ticker):
    try:
        import yfinance as yf
        return list(yf.Ticker(ticker).options), None
    except ImportError:
        return [], "yfinance isn't installed. Run:  pip install yfinance"
    except Exception as e:
        return [], f"Couldn't load expirations: {e}"


def list_strikes(ticker, expiry, kind):
    try:
        import yfinance as yf
        ch = yf.Ticker(ticker).option_chain(expiry)
        tbl = ch.calls if kind == "call" else ch.puts
        return sorted(float(s) for s in tbl["strike"].tolist()), None
    except Exception as e:
        return [], f"Couldn't load strikes: {e}"


def _estimate_hv(tk):
    try:
        import numpy as np
        h = tk.history(period="3mo")
        if h.empty or len(h) < 10:
            return float("nan")
        rets = np.log(h["Close"] / h["Close"].shift(1)).dropna()
        return float(rets.std() * math.sqrt(252))
    except Exception:
        return float("nan")


def load_live_option(ticker, expiry, strike, kind, r, q):
    try:
        import yfinance as yf
    except ImportError:
        return None, "yfinance isn't installed. Run:  pip install yfinance  (or use Demo data)."
    try:
        tk = yf.Ticker(ticker)
        spot = None
        try:
            spot = float(tk.fast_info["last_price"])
        except Exception:
            h = tk.history(period="1d")
            spot = float(h["Close"].iloc[-1]) if not h.empty else None
        if not spot or spot != spot:
            return None, f"Couldn't read a current price for {ticker}."
        ch = tk.option_chain(expiry)
        tbl = ch.calls if kind == "call" else ch.puts
        row = tbl[tbl["strike"] == strike]
        if row.empty:
            return None, f"Strike {strike} not found for {ticker} {expiry}."
        row = row.iloc[0]
        bid, ask = float(row.get("bid", 0) or 0), float(row.get("ask", 0) or 0)
        price = (bid + ask) / 2 if (bid > 0 and ask > 0) else float(row.get("lastPrice", 0) or 0)
        if price <= 0:
            return None, "That contract has no usable price right now (illiquid). Try another strike."
        exp = dt.datetime.strptime(expiry, "%Y-%m-%d").date()
        dte = max((exp - dt.date.today()).days, 1)
        T = dte / 365.0
        iv = implied_vol(price, spot, strike, T, r, q, kind)
        if iv != iv:
            iv = float(row.get("impliedVolatility", 0) or 0) or float("nan")
        return dict(ticker=ticker, name=ticker, S=spot, K=strike, kind=kind, dte=dte, T=T,
                    r=r, q=q, iv=iv, hv=_estimate_hv(tk), market_price=round(price, 2),
                    scenario=None), None
    except Exception as e:
        return None, f"Live data problem: {e}. Yahoo's free feed hiccups sometimes — retry or use Demo data."


def load_live_fundamentals(ticker):
    """Best-effort live fundamentals. Missing fields degrade gracefully to n/a."""
    try:
        import yfinance as yf
    except ImportError:
        return None, "yfinance isn't installed."
    try:
        tk = yf.Ticker(ticker)
        info = {}
        try:
            info = tk.info or {}
        except Exception:
            info = {}
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not price:
            h = tk.history(period="1d")
            price = float(h["Close"].iloc[-1]) if not h.empty else None
        if not price:
            return None, f"Couldn't read a price for {ticker}."
        shares = (info.get("sharesOutstanding") or 0) / 1e9 or None
        fcf = (info.get("freeCashflow") or 0) / 1e9 or None
        total_cash = (info.get("totalCash") or 0) / 1e9
        total_debt = (info.get("totalDebt") or 0) / 1e9
        f = dict(
            ticker=ticker, name=info.get("shortName", ticker), price=float(price),
            shares=shares, fcf=fcf, net_cash=(total_cash - total_debt),
            g_high=0.06, g_term=0.030, discount=0.090, years=10,   # editable defaults
            pe=info.get("trailingPE"), forward_pe=info.get("forwardPE"),
            pb=info.get("priceToBook"), roe=info.get("returnOnEquity"),
            net_margin=info.get("profitMargins"), rev_growth=info.get("revenueGrowth"),
            earnings_growth=info.get("earningsGrowth"),
            debt_to_equity=(info.get("debtToEquity") / 100.0 if info.get("debtToEquity") else None),
            beta=info.get("beta"), div_yield=info.get("dividendYield"),
            analyst_target=info.get("targetMeanPrice"),
            wk52_low=info.get("fiftyTwoWeekLow"), wk52_high=info.get("fiftyTwoWeekHigh"),
        )
        if not f["shares"] or not f["fcf"]:
            f["_dcf_unavailable"] = True   # can't DCF without cash flow + shares
        return f, None
    except Exception as e:
        return None, f"Live fundamentals problem: {e}. Try Demo data."


# =============================================================================
#  PART 6 — OPTION-ONLY QUIZ RUBRIC (from v1; scenario-driven)
# =============================================================================

def analyze_trade(opt, scenario):
    S, K, kind, prem = opt["S"], opt["K"], opt["kind"], opt["market_price"]
    iv, hv = opt["iv"], opt.get("hv", float("nan"))
    be = breakeven_price(K, prem, kind)
    g = greeks(S, K, opt["T"], opt["r"], iv, opt["q"], kind)
    direction_match = (kind == "call" and scenario["dir"] == "bull") or \
                      (kind == "put" and scenario["dir"] == "bear")
    if kind == "call":
        target, clears = S * (1 + scenario["move"]), S * (1 + scenario["move"]) >= be
    else:
        target, clears = S * (1 - scenario["move"]), S * (1 - scenario["move"]) <= be
    iv_hv = (iv / hv) if (hv == hv and hv > 0) else float("nan")
    theta_frac = (-g["theta_day"] * scenario["horizon"] / prem) if prem > 0 else float("nan")
    score = 0
    score += 2 if direction_match else 0
    score += 2 if clears else -2
    if iv_hv == iv_hv:
        score += 1 if iv_hv < 0.90 else (-1 if iv_hv > 1.25 else 0)
    if theta_frac == theta_frac:
        score += 1 if theta_frac < 0.35 else (-1 if theta_frac > 0.60 else 0)
    return dict(recommend_buy=direction_match and score >= 3, score=score, breakeven=be,
                greeks=g, direction_match=direction_match, clears_be=clears, target=target,
                iv_hv=iv_hv, theta_frac=theta_frac)


# =============================================================================
#  PART 7 — SMALL UI HELPERS
# =============================================================================

def fmt_pct(x):
    return "—" if (x is None or x != x) else f"{x*100:.1f}%"

def fmt_usd(x):
    return "—" if (x is None or x != x) else f"${x:,.2f}"

def option_headline(opt):
    return f"**{opt['ticker']} {opt['K']:g} {opt['kind'].upper()}** — stock ${opt['S']:,.2f}, {opt['dte']}d to expiry"


def show_option_panel(opt):
    c = st.columns(4)
    c[0].metric("Stock price", fmt_usd(opt["S"])); c[1].metric("Strike", fmt_usd(opt["K"]))
    c[2].metric("Option price", fmt_usd(opt["market_price"])); c[3].metric("Days left", f"{opt['dte']}")
    c[0].metric("Type", opt["kind"].upper())
    c[1].metric("Moneyness", moneyness_label(opt["S"], opt["K"], opt["kind"]).split(" (")[0])
    c[2].metric("Implied vol", fmt_pct(opt["iv"])); c[3].metric("Hist. vol", fmt_pct(opt.get("hv", float("nan"))))
    g = greeks(opt["S"], opt["K"], opt["T"], opt["r"], opt["iv"], opt["q"], opt["kind"])
    st.dataframe(pd.DataFrame({
        "Greek": ["Delta", "Gamma", "Theta/day", "Vega/1% IV", "Rho/1% rate"],
        "Value": [f"{g['delta']:.3f}", f"{g['gamma']:.4f}", fmt_usd(g["theta_day"]),
                  fmt_usd(g["vega_1pct"]), fmt_usd(g["rho_1pct"])],
        "Plain meaning": ["$ per +$1 in stock (≈ shares held)", "how fast delta moves",
                          "$ lost per day to time", "$ per +1 IV point", "$ per +1 rate point"],
    }), hide_index=True, use_container_width=True)


def show_lean_badge(lean):
    color = {"up": "🟢", "down": "🔴", "neutral": "🟡"}[lean["direction"]]
    st.markdown(f"### {color} Directional lean: **{lean['label']}**  ·  confidence: *{lean['confidence']}*")


# =============================================================================
#  PART 8 — PAGE: LEARN
# =============================================================================

def page_learn():
    st.header("📚 Learn the basics")
    st.caption("Plain-language first, real math underneath.")

    with st.expander("1. What is an option?", expanded=True):
        st.markdown(
            "- A **call** = the right to **buy** at a set price (**strike**) before a deadline (**expiry**).\n"
            "- A **put** = the right to **sell** at the strike before expiry.\n"
            "- You pay a **premium** for that right. A call is like a **coupon**: '$5 off, expires Friday.'")

    with st.expander("2. Price = Intrinsic + Extrinsic"):
        st.markdown(
            "- **Intrinsic** = money already in the bag: `max(Stock − Strike, 0)` for a call.\n"
            "- **Extrinsic** (time value) = the price of hope; it **melts to $0 by expiry** (that melt = **theta**).\n"
            "> An all-extrinsic (out-of-the-money) option is a **melting ice cube** — it can pay off, but time fights you daily.")

    with st.expander("3. The 5 inputs (Black-Scholes)"):
        st.markdown("Stock ↑, Time ↑, Volatility ↑ all make a **call** worth **more**; a higher Strike makes it worth less.")
        st.latex(r"C = S e^{-qT} N(d_1) - K e^{-rT} N(d_2)")

    with st.expander("4. Implied Volatility — the number that matters"):
        st.markdown(
            "Four inputs are known; only **volatility** is a guess. Flip Black-Scholes around and the market price "
            "tells you the volatility being assumed — **Implied Volatility (IV)**. Buying an option really means "
            "*'I think the stock moves MORE than the market expects.'* So the value question is **IV vs. how much the "
            "stock actually moves (historical volatility).**")

    with st.expander("5. The Greeks"):
        st.markdown(
            "- **Delta** — $ per +$1 in the stock (≈ chance of finishing ITM, ≈ shares held).\n"
            "- **Gamma** — how fast delta changes.\n- **Theta** — $ lost per day to time.\n"
            "- **Vega** — $ per +1 IV point.\n- **Rho** — rate sensitivity (usually minor).")

    st.divider()
    st.subheader("The v2 additions — valuing the STOCK behind the option")

    with st.expander("6. Valuing the underlying (the Buffett / DCF lens)", expanded=True):
        st.markdown(
            "An option is a bet **on a stock**, so first ask: *what is the stock worth?* Value investors estimate "
            "**intrinsic value** with a **Discounted Cash Flow (DCF)**: project the company's free cash flow, discount it "
            "back to today's dollars, and compare to the price. If value **>** price, there's a **margin of safety** "
            "(undervalued → bullish). If value **<** price, it's rich (bearish).\n\n"
            "**Big honest caveat:** DCF is only as good as its assumptions. Change the growth rate a little and the answer "
            "swings a lot (the **Analyze the stock** tab shows this live). That fragility *is* the lesson — value is an "
            "estimate with error bars, not a fact.")
        st.latex(r"\text{Fair value} = \frac{\sum_{t=1}^{N}\frac{FCF_t}{(1+d)^t} + \frac{FCF_N(1+g_\infty)}{(d-g_\infty)(1+d)^N} + \text{net cash}}{\text{shares}}")

    with st.expander("7. ⏳ The timing tension (the whole point)", expanded=True):
        st.markdown(
            "> **Value investing gives you a destination. Options give you a deadline.**\n\n"
            "Buffett can say 'this is worth more than it trades for' and **wait years**. An option **expires** — a cheap "
            "stock can stay cheap past your expiration and your option dies worthless anyway. (Tellingly, when Buffett "
            "*has* used options he mostly **sold long-dated premium** to get paid for patience, rather than buying "
            "short-dated calls.) So we never 'predict the price.' We:\n"
            "1. Pick a **direction** from fundamentals (undervalued → calls; overvalued → puts).\n"
            "2. Check the **move we'd need** (breakeven) is even plausible within the gap to fair value.\n"
            "3. Check whether the option's **IV-implied move** is *smaller* than our thesis move → then it's **cheap for our view.** "
            "That third check is the closest thing to a real **edge**.")

    with st.expander("8. 🎯 What you can and CANNOT remove (variability honesty)"):
        st.markdown(
            "You asked to remove all variability except unforeseen macro shocks. Here's the honest scoreboard:\n\n"
            "**Can't be removed — ever:** earnings surprises, guidance changes, competition, management execution, "
            "sentiment & momentum, liquidity gaps — *plus* the macro/black-swans you named (weather, war, shocks). "
            "Volatility **is** this uncertainty, and **IV is its price**.\n\n"
            "**What we CAN do:** convert a vague hunch into an **explicit, checkable thesis** (direction + required move + "
            "pricing edge), then **size the bet** for the uncertainty that remains. That's the whole game — well-reasoned "
            "bets with an edge, not certainties.")

    st.info("Try it: **Analyze the stock** to value a company, then **Full analysis** to marry it to an option.")


# =============================================================================
#  PART 9 — PAGE: ANALYZE THE OPTION (single-option valuation, from v1)
# =============================================================================

def page_analyze_option():
    st.header("🔬 Analyze an option, step by step")
    opt = pick_option_ui("aopt")
    if opt is None:
        return
    st.divider(); st.subheader(option_headline(opt)); show_option_panel(opt)
    st.divider(); st.subheader("Step-by-step valuation — *what* and *why*")

    S, K, kind, prem = opt["S"], opt["K"], opt["kind"], opt["market_price"]
    intr = intrinsic_value(S, K, kind); extr = max(prem - intr, 0.0)
    st.markdown(f"**Step 1 — Split the premium.** You pay **{fmt_usd(prem)}**/share "
                f"(**{fmt_usd(prem*100)}**/contract): **intrinsic {fmt_usd(intr)}** + "
                f"**extrinsic {fmt_usd(extr)}** (the part that melts to $0).")
    if prem > 0:
        st.progress(min(extr / prem, 1.0), text=f"{extr/prem*100:.0f}% is extrinsic (exposed to time decay)")

    hv = opt.get("hv", float("nan"))
    st.markdown(f"**Step 2 — Implied volatility = {fmt_pct(opt['iv'])}** (what the market assumes it'll swing).")
    if hv == hv and hv > 0:
        r = opt["iv"] / hv
        v = "**rich** (paying up for vol)" if r > 1.25 else "**cheap** (vol on sale)" if r < 0.90 else "**roughly fair**"
        st.markdown(f"Historical volatility is **{fmt_pct(hv)}** → IV/HV = **{r:.2f}×**, so it looks {v}.")

    g = greeks(S, K, opt["T"], opt["r"], opt["iv"], opt["q"], kind)
    st.markdown(f"**Step 3 — Greeks.** Delta **{g['delta']:.2f}** (≈{abs(g['delta'])*100:.0f} shares); "
                f"Theta **{fmt_usd(g['theta_day'])}/day** (≈{fmt_usd(-g['theta_day']*100)}/contract/day lost to time); "
                f"Vega **{fmt_usd(g['vega_1pct'])}** per IV point.")

    be = breakeven_price(K, prem, kind)
    move = (be - S) / S if kind == "call" else (S - be) / S
    st.markdown(f"**Step 4 — Breakeven = {fmt_usd(be)}** → stock must move **{fmt_pct(move)}** just to break even.")
    st.caption(f"Model (risk-neutral) chance of finishing ITM ≈ "
               f"{fmt_pct(prob_itm_riskneutral(S, K, opt['T'], opt['r'], opt['iv'], opt['q'], kind))} — an estimate, not a promise.")

    st.divider(); st.subheader("Pictures")
    a, b = st.columns(2)
    with a:
        st.markdown("**Profit / loss at expiry**"); st.line_chart(payoff_curve(K, prem, kind, S))
    with b:
        st.markdown("**Value today vs stock price** (slope = delta)")
        st.line_chart(value_vs_spot_curve(K, opt["T"], opt["r"], opt["iv"], opt["q"], kind, S))


# =============================================================================
#  PART 10 — PAGE: ANALYZE THE STOCK (fundamentals + lean)
# =============================================================================

def render_stock_analysis(f):
    """Show DCF (with live-adjustable assumptions), quality, and the lean. Returns (fair_value, lean)."""
    if f.get("is_index"):
        st.info("This is an **index ETF** — we value it by its **P/E vs. history**, not a single-company DCF.")
        c = st.columns(3)
        c[0].metric("Index P/E", f"{f['index_pe']:.1f}")
        c[1].metric("Long-run avg P/E", f"{f['index_pe_avg']:.1f}")
        c[2].metric("Read", "Rich vs history" if f["index_pe"] > f["index_pe_avg"] else "Cheap vs history")
        lean = directional_lean(f, float("nan"))
        show_lean_badge(lean)
        for bl in lean["bullets"]:
            st.markdown(bl)
        return float("nan"), lean

    if f.get("_dcf_unavailable"):
        st.warning("Live feed didn't return free cash flow / share count, so a DCF isn't possible for this name. "
                   "The quality snapshot below still works; or switch to a Demo stock for the full DCF walkthrough.")

    st.subheader("Step 1 — Discounted Cash Flow (what's the stock worth?)")
    st.caption("Adjust the assumptions and watch fair value move — that sensitivity IS the lesson.")
    a1, a2, a3 = st.columns(3)
    g_high = a1.number_input("Growth, next 10y (%/yr)", value=float(f.get("g_high", 0.06)) * 100,
                             step=1.0, key=f"g_{f['ticker']}") / 100
    discount = a2.number_input("Discount rate (%/yr)", value=float(f.get("discount", 0.09)) * 100,
                               step=0.5, key=f"d_{f['ticker']}") / 100
    g_term = a3.number_input("Terminal growth (%/yr)", value=float(f.get("g_term", 0.03)) * 100,
                             step=0.25, key=f"gt_{f['ticker']}") / 100

    fair = compute_fair_value(f, dict(g_high=g_high, discount=discount, g_term=g_term))
    mos = (fair - f["price"]) / f["price"] if fair == fair else float("nan")
    m = st.columns(3)
    m[0].metric("DCF fair value", fmt_usd(fair))
    m[1].metric("Current price", fmt_usd(f["price"]))
    m[2].metric("Margin of safety", fmt_pct(mos),
                delta=("undervalued" if mos > 0 else "overvalued") if mos == mos else None)

    # sensitivity table
    rows = []
    for gg in sorted({round(g_high - 0.06, 4), round(g_high - 0.03, 4), g_high,
                      round(g_high + 0.03, 4), round(g_high + 0.06, 4)}):
        if gg <= -0.5:
            continue
        fv = compute_fair_value(f, dict(g_high=gg, discount=discount, g_term=g_term))
        rows.append({"Growth assumption": f"{gg*100:.0f}%/yr", "Fair value": fmt_usd(fv),
                     "vs price": fmt_pct((fv - f["price"]) / f["price"])})
    st.markdown("*Sensitivity to the growth guess:*")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.subheader("Step 2 — Quality & multiples (is it a good business at a fair price?)")
    peg = peg_ratio(f.get("pe"), f.get("earnings_growth"))
    qc = st.columns(4)
    qc[0].metric("P/E", f"{f['pe']:.0f}" if f.get("pe") else "—")
    qc[1].metric("Forward P/E", f"{f['forward_pe']:.0f}" if f.get("forward_pe") else "—")
    qc[2].metric("PEG", f"{peg:.2f}" if peg == peg else "—")
    qc[3].metric("P/B", f"{f['pb']:.1f}" if f.get("pb") else "—")
    q_score, q_bullets = quality_score(f)
    st.markdown(f"**Business-quality score: {q_score}/100**")
    st.markdown("  \n".join(q_bullets))

    st.subheader("Step 3 — The reasoned directional lean")
    lean = directional_lean(f, fair)
    show_lean_badge(lean)
    for bl in lean["bullets"]:
        st.markdown(bl)
    st.warning("⏳ **Timing caveat:** this lean is a *destination*, not a schedule. Value can take a long time to be "
               "recognized — and options expire. Direction ≠ timing.")
    return fair, lean


def page_analyze_stock():
    st.header("🏢 Analyze the stock (fundamentals)")
    f = pick_stock_ui("astock")
    if f is None:
        return
    st.divider()
    st.subheader(f"{f.get('name', f['ticker'])} ({f['ticker']}) — ${f['price']:,.2f}")
    render_stock_analysis(f)


# =============================================================================
#  PART 11 — PAGE: FULL ANALYSIS (stock lean + option, combined verdict)
# =============================================================================

def page_full_analysis():
    st.header("🏦 Full analysis — value the stock, then judge the option")
    st.caption("The complete workflow: fundamentals → directional lean → does THIS option fit? (calls & puts)")

    opt = pick_option_ui("full")
    if opt is None:
        return
    f = FUNDAMENTALS.get(opt["ticker"])
    if f is None:
        live_f, err = load_live_fundamentals(opt["ticker"])
        if err or live_f is None:
            st.warning(f"No fundamentals available for {opt['ticker']} ({err}). Try a Demo option.")
            return
        f = live_f

    st.divider()
    st.subheader(f"① The underlying: {f.get('name', f['ticker'])} ({f['ticker']})")
    fair, lean = render_stock_analysis(f)

    st.divider()
    st.subheader(f"② The option: {option_headline(opt)}")
    show_option_panel(opt)

    st.divider()
    st.subheader("③ The verdict — does the option fit the fundamentals?")
    res = analyze_full(opt, fair, lean)

    dir_word = {"up": "bullish", "down": "bearish", "neutral": "neutral"}[lean["direction"]]
    tool_word = "call (needs bullish)" if opt["kind"] == "call" else "put (needs bearish)"

    st.markdown("**Check 1 — Direction fit:** "
                f"fundamentals lean **{dir_word}**, this is a **{tool_word}** → "
                + ("✅ aligned." if res["direction_match"] else "❌ **mismatch** — the option fights the thesis."))

    if lean["direction"] != "neutral":
        st.markdown("**Check 2 — Is the needed move within reach?** "
                    f"breakeven needs a **{fmt_pct(res['be_move'])}** move; the gap to fair value is "
                    f"**{fmt_pct(abs(lean['mos']))}** → "
                    + ("✅ the valuation gap more than covers breakeven."
                       if res["destination_clears"] else
                       "❌ even reaching fair value wouldn't clear breakeven."))
    else:
        st.markdown("**Check 2 —** fundamentals are **neutral**, so there's no valuation gap to lean on here.")

    if res["edge"] != "unknown":
        edge_txt = {"cheap": "✅ the market is pricing a **smaller** move than your thesis → option looks **cheap for your view**.",
                    "fair": "➖ the market's implied move ≈ your thesis move → **fairly priced** for your view.",
                    "rich": "❌ the market is pricing a **bigger** move than your thesis → you may be **overpaying**."}[res["edge"]]
        st.markdown(f"**Check 3 — Pricing edge (IV vs your thesis):** implied 1σ move ≈ "
                    f"**{fmt_usd(res['iv_move'])}** vs your gap **{fmt_usd(res['fund_move'])}** → {edge_txt}")

    st.markdown(f"**Check 4 — Confidence:** the fundamental read is **{lean['confidence']}** confidence.")

    st.markdown("---")
    if res["recommend_buy"]:
        st.success(f"### 🟢 Framework leans: BUY this {opt['kind']}\n"
                   "Direction fits, the move is reachable, and pricing isn't against you. "
                   "Still size it for the uncertainty that can't be removed.")
    else:
        reason = ("it fights the fundamental direction" if not res["direction_match"]
                  else "the required move is a stretch and/or pricing works against you")
        st.error(f"### 🔴 Framework leans: SKIP this {opt['kind']}\n"
                 f"Main reason: {reason}.")
    st.warning("⏳ **Never forget the deadline.** This option has **%d days** left. Value convergence has no schedule — "
               "being right on the business but wrong on timing still loses. This is analysis, not prophecy." % opt["dte"])


# =============================================================================
#  PART 12 — PAGE: QUIZ (option decision, now with a fundamentals snapshot)
# =============================================================================

def _quiz_state():
    ss = st.session_state
    ss.setdefault("q_score", 0); ss.setdefault("q_total", 0); ss.setdefault("q_idx", 0)
    ss.setdefault("q_answered", False)
    if "q_order" not in ss:
        ss.q_order = list(range(len(DEMO_OPTIONS))); random.shuffle(ss.q_order)


def _quiz_grade(opt, scenario, user_buy):
    a = analyze_trade(opt, scenario)
    correct = (user_buy == a["recommend_buy"])
    st.session_state.q_total += 1
    if correct:
        st.session_state.q_score += 1
        st.success("✅ Good call — your reasoning matches the framework.")
    else:
        st.error("❌ Not the strongest choice. Here's the breakdown.")
    st.markdown(f"Framework leans: {'**BUY**' if a['recommend_buy'] else '**SKIP**'}")
    dw = "bullish" if scenario["dir"] == "bull" else "bearish"
    st.markdown(f"1. **Direction:** view is **{dw}**, option is a **{opt['kind']}** → "
                + ("✅ right tool." if a["direction_match"] else "❌ wrong tool."))
    if a["iv_hv"] == a["iv_hv"]:
        pr = ("❌ overpaying" if a["iv_hv"] > 1.25 else "✅ vol on sale" if a["iv_hv"] < 0.90 else "➖ fair")
        st.markdown(f"2. **Pricing:** IV/HV = {a['iv_hv']:.2f}× → {pr}.")
    st.markdown(f"3. **Breakeven:** need **{fmt_usd(a['breakeven'])}**, scenario points to **{fmt_usd(a['target'])}** → "
                + ("✅ clears." if a["clears_be"] else "❌ falls short (right direction can still lose)."))
    if a["theta_frac"] == a["theta_frac"]:
        th = ("❌ heavy" if a["theta_frac"] > 0.60 else "✅ mild" if a["theta_frac"] < 0.35 else "➖ moderate")
        st.markdown(f"4. **Time decay:** ~{a['theta_frac']*100:.0f}% of premium over {scenario['horizon']} days → {th}.")
    st.caption("A reasoning check, not a prediction — the goal is edge over many bets, not being right every time.")


def page_quiz():
    st.header("🎯 Quiz — should you buy it?")
    _quiz_state()
    ss = st.session_state
    st.markdown(f"**Score: {ss.q_score} / {ss.q_total}**"
                + (f"  ({ss.q_score/ss.q_total*100:.0f}%)" if ss.q_total else ""))
    opt = DEMO_OPTIONS[ss.q_order[ss.q_idx % len(ss.q_order)]]
    sc = opt["scenario"]
    st.info(f"**Scenario:** {sc['text']}")

    # fundamentals snapshot (context, not the graded part)
    f = FUNDAMENTALS.get(opt["ticker"])
    if f and not f.get("is_index"):
        fair = compute_fair_value(f)
        mos = (fair - f["price"]) / f["price"]
        tag = "undervalued" if mos > 0.10 else "overvalued" if mos < -0.10 else "roughly fair"
        st.caption(f"💡 Fundamentals hint: DCF says {f['ticker']} is **{tag}** ({mos*100:+.0f}% vs price). "
                   f"Does the option's direction agree?")
    elif f and f.get("is_index"):
        st.caption(f"💡 Fundamentals hint: index P/E {f['index_pe']:.0f} vs ~{f['index_pe_avg']:.0f} avg "
                   f"→ market looks {'rich' if f['index_pe']>f['index_pe_avg'] else 'cheap'} vs history.")

    st.subheader(option_headline(opt)); show_option_panel(opt)
    st.markdown("**Given the scenario and the numbers — BUY or SKIP?**")

    if not ss.q_answered:
        c1, c2 = st.columns(2)
        if c1.button("🟢 BUY it", use_container_width=True):
            ss.q_answered = True; ss._ans = True; st.rerun()
        if c2.button("🔴 SKIP it", use_container_width=True):
            ss.q_answered = True; ss._ans = False; st.rerun()
    else:
        _quiz_grade(opt, sc, ss.get("_ans", False))
        st.divider()
        if st.button("➡️ Next question", use_container_width=True):
            ss.q_idx += 1; ss.q_answered = False
            if ss.q_idx % len(ss.q_order) == 0:
                random.shuffle(ss.q_order)
            st.rerun()


# =============================================================================
#  PART 13 — PICKERS (option and stock; Demo + Live)
# =============================================================================

def _assumptions_expander(key):
    with st.expander("Advanced assumptions (rate & dividend)"):
        r = st.number_input("Risk-free rate (%)", value=RISK_FREE_DEFAULT * 100, step=0.25, key=f"{key}_r") / 100
        q = st.number_input("Dividend yield (%)", value=0.0, step=0.25, key=f"{key}_q") / 100
    return r, q


def pick_option_ui(key):
    src = st.radio("Data source", ["Demo data (offline)", "Live data (Yahoo)"], key=f"{key}_src", horizontal=True)
    r, q = _assumptions_expander(key)
    if src.startswith("Demo"):
        labels = [f"{o['ticker']} {o['K']:g} {o['kind'].upper()} · {o['dte']}d · IV {o['iv']*100:.0f}%"
                  for o in DEMO_OPTIONS]
        i = st.selectbox("Pick a demo option", range(len(DEMO_OPTIONS)),
                         format_func=lambda i: labels[i], key=f"{key}_demo")
        o = dict(DEMO_OPTIONS[i]); o["r"], o["q"] = r, q
        return o
    ticker = st.text_input("Ticker", value="AAPL", key=f"{key}_tkr").strip().upper()
    if not ticker:
        return None
    kind = st.radio("Call or put?", ["call", "put"], key=f"{key}_kind", horizontal=True)
    exps, err = list_expirations(ticker)
    if err:
        st.error(err); st.info("Tip: switch to **Demo data** — everything works offline."); return None
    if not exps:
        st.warning("No expirations returned."); return None
    exp = st.selectbox("Expiration", exps, key=f"{key}_exp")
    strikes, err = list_strikes(ticker, exp, kind)
    if err or not strikes:
        st.error(err or "No strikes returned."); return None
    strike = st.selectbox("Strike", strikes, index=len(strikes) // 2, key=f"{key}_strike")
    if st.button("Load option", key=f"{key}_load"):
        o, err = load_live_option(ticker, exp, strike, kind, r, q)
        if err:
            st.error(err); st.info("Tip: switch to **Demo data**."); return None
        st.session_state[f"{key}_opt"] = o
    return st.session_state.get(f"{key}_opt")


def pick_stock_ui(key):
    src = st.radio("Data source", ["Demo data (offline)", "Live data (Yahoo)"], key=f"{key}_src", horizontal=True)
    if src.startswith("Demo"):
        tickers = list(FUNDAMENTALS.keys())
        t = st.selectbox("Pick a demo stock", tickers,
                         format_func=lambda t: f"{t} — {FUNDAMENTALS[t].get('name', t)}", key=f"{key}_demo")
        return FUNDAMENTALS[t]
    ticker = st.text_input("Ticker", value="AAPL", key=f"{key}_tkr").strip().upper()
    if not ticker:
        return None
    if st.button("Load fundamentals", key=f"{key}_load"):
        f, err = load_live_fundamentals(ticker)
        if err:
            st.error(err); st.info("Tip: switch to **Demo data**."); return None
        st.session_state[f"{key}_f"] = f
    return st.session_state.get(f"{key}_f")


# =============================================================================
#  PART 14 — MAIN
# =============================================================================

def main():
    st.set_page_config(page_title="Options Tutor", page_icon="📈", layout="wide")
    st.title("📈 Options Tutor")
    st.caption("Value the stock, value the option, then decide — the honest way. Calls & puts.")

    with st.sidebar:
        st.header("Navigate")
        page = st.radio("Go to", ["📚 Learn", "🏢 Analyze the stock", "🔬 Analyze the option",
                                  "🏦 Full analysis", "🎯 Quiz"], label_visibility="collapsed")
        st.divider()
        st.markdown("**⚠️ Not financial advice.** Educational only. Predicts nothing.")
        st.caption("Live data via yfinance. Demo data always works offline.")

    if page.startswith("📚"):
        page_learn()
    elif page.startswith("🏢"):
        page_analyze_stock()
    elif page.startswith("🔬"):
        page_analyze_option()
    elif page.startswith("🏦"):
        page_full_analysis()
    else:
        page_quiz()


if __name__ == "__main__":
    main()
