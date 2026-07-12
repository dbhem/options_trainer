# 📈 Options Tutor (v2)

An interactive trainer that teaches you to judge whether a stock option is a
good buy — by first valuing the **stock** (Buffett-style), then valuing the
**option** (Black-Scholes), then checking whether the two fit. Works for
**calls AND puts**.

## The five tabs
- **📚 Learn** — the concepts, plain-language first, real formulas underneath.
- **🏢 Analyze the stock** — a live-adjustable DCF + quality checks that produce a
  **reasoned directional lean** (undervalued → bullish → calls; overvalued → bearish → puts).
- **🔬 Analyze the option** — value any single option step by step (intrinsic/extrinsic,
  IV vs. historical vol, the Greeks, breakeven, payoff chart).
- **🏦 Full analysis** — the complete workflow: stock lean **married to** an option, with a
  transparent 4-check verdict.
- **🎯 Quiz** — you decide *buy or skip*; it grades your reasoning and keeps score.

---

## ⚠️ Read this first — what this is and isn't
This is an **educational tool. Not financial advice. It predicts nothing.**

Two honest truths it's built around:

1. **You can't remove uncertainty — it's the product.** Implied volatility is the
   market's *price* for uncertainty. Beyond unforeseeable macro/black-swan events
   (weather, war, shocks), ordinary surprises remain too — earnings, guidance,
   competition, sentiment. We don't delete these. We turn a vague hunch into an
   **explicit, checkable thesis** and **size the bet** for what's left.

2. **Value investing gives you a *destination*; options give you a *deadline*.**
   A cheap stock can stay cheap past your expiration. So we never "predict the
   price." We pick a **direction**, check the **move we'd need is plausible**, and
   check whether the option's **implied move is smaller than our thesis move**
   (that's the closest thing to an *edge* that exists).

---

## 🚀 How to run it (step by step, like you're 10)

1. **Get Python** (3.9+) from [python.org](https://www.python.org/downloads/).
2. **Open a terminal** and install the two helpers:
   ```
   pip install streamlit yfinance
   ```
   (`streamlit` draws the web page; `yfinance` fetches real stock data.)
3. **Go to the folder** with `options_tutor.py`:
   ```
   cd Downloads
   ```
4. **Start it:**
   ```
   streamlit run options_tutor.py
   ```
   Your browser opens automatically (or visit **http://localhost:8501**).
5. **Stop it:** press `Ctrl + C` in the terminal.

### 🌐 No internet? Still 100% functional.
Everything — every lesson, every stock, every quiz — runs on realistic
**built-in Demo data**. Live Yahoo data is a bonus. If the live feed ever hiccups
(Yahoo's free feed does, industry-wide), flip the toggle to **Demo data** and keep going.

---

## 🧠 What you'll actually learn
- Intrinsic vs. extrinsic value; why some options are "melting ice cubes"
- Implied volatility — why an option's price is really a **bet on volatility**
- All five Greeks (delta, gamma, theta, vega, rho) and what each is telling you
- Breakeven math, and why **being right on direction can still lose money**
- **DCF valuation** of the underlying — and why it's *fragile to its own assumptions*
- Business-quality checks (ROE, margins, growth, leverage) — the Buffett lens
- How to **combine** a fundamental lean with an option, for calls **and** puts
- The IV-vs-thesis "edge" check — is the option cheap or rich *for your view?*

## 🔬 A note on rigor
The Black-Scholes engine (prices, all Greeks, put-call parity, implied-vol solver)
and the DCF engine are **unit-tested against known values** before anything is
built on them. The demo numbers are illustrative, clearly labeled, and chosen to
produce a realistic spread of undervalued / fair / overvalued cases.
