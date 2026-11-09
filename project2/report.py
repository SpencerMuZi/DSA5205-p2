"""Generate a 21-page research report from frozen results, never from hand-entered returns."""
from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                               Image, PageBreak, KeepTogether)

from .core import FEATURES, read_config

NAVY = colors.HexColor("#203550")
TEAL = colors.HexColor("#087f8c")
GRAY = colors.HexColor("#526174")
WIDTH = 451


def pct(x):
    return f"{100 * float(x):.2f}%"


def build():
    config = read_config()
    metrics = pd.read_csv("output/tables/test_metrics.csv").set_index("strategy")
    grid = pd.read_csv("output/tables/validation_grid.csv")
    annual = pd.read_csv("output/tables/annual_metrics.csv")
    cost = pd.read_csv("output/tables/cost_sensitivity.csv")
    pred = json.loads(Path("output/prediction_metrics.json").read_text())
    audit = json.loads(Path("output/data_audit.json").read_text())
    manifest = json.loads(Path("output/run_manifest.json").read_text())
    selection = json.loads(Path("output/selection.json").read_text())
    diagnostic = json.loads(Path("output/exposure_diagnostic.json").read_text())
    predictions = pd.read_csv("output/tables/test_predictions.csv")
    fits = pd.read_csv("output/tables/test_fit_audit.csv")
    events = pd.read_csv("output/tables/dividend_event_checks.csv")
    ridge, bh, ma = [metrics.loc[x] for x in ["Ridge timing", "SPY buy-and-hold", "MA20 timing"]]
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCustom", fontName="Helvetica-Bold", fontSize=29, leading=34, textColor=NAVY, spaceAfter=20))
    styles.add(ParagraphStyle(name="SectionCustom", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceAfter=16))
    styles.add(ParagraphStyle(name="BodyCustom", fontName="Helvetica", fontSize=10.4, leading=15.5, textColor=NAVY, spaceAfter=10))
    styles.add(ParagraphStyle(name="SmallCustom", fontName="Helvetica", fontSize=8.5, leading=12, textColor=GRAY, spaceAfter=8))
    styles.add(ParagraphStyle(name="LabelCustom", fontName="Helvetica-Bold", fontSize=10.5, leading=15, textColor=TEAL, spaceBefore=8, spaceAfter=8))
    styles.add(ParagraphStyle(name="CodeCustom", fontName="Courier", fontSize=8.1, leading=12, textColor=NAVY, backColor=colors.HexColor("#f0f5f7"), borderPadding=7, spaceAfter=12))
    story, sections = [], []

    def p(text, kind="BodyCustom"):
        story.append(Paragraph(text, styles[kind]))

    def heading(text):
        p(text, "LabelCustom")

    def section(title):
        if story:
            story.append(PageBreak())
        sections.append(title)
        p(f"{len(sections):02d}  /  {title}", "SectionCustom")

    def table(headers, rows, widths=None):
        data = [[Paragraph(escape(str(x)), styles["SmallCustom"]) for x in headers]]
        data += [[Paragraph(escape(str(x)), styles["SmallCustom"]) for x in row] for row in rows]
        t = Table(data, colWidths=widths or [WIDTH / len(headers)] * len(headers), repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3f1f2")),
                              ("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LINEBELOW", (0, 0), (-1, 0), .7, TEAL),
                              ("LINEBELOW", (0, 1), (-1, -1), .35, colors.HexColor("#dce3e9")),
                              ("LEFTPADDING", (0, 0), (-1, -1), 7),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                              ("TOPPADDING", (0, 0), (-1, -1), 7),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        story.append(t)
        story.append(Spacer(1, 12))

    def fig(name, caption, width=WIDTH):
        from PIL import Image as PILImage
        path = Path("output/figures") / f"{name}.png"
        with PILImage.open(path) as im:
            height = width * im.height / im.width
        story.append(Image(str(path), width=width, height=height, hAlign="LEFT"))
        p(caption, "SmallCustom")

    # 1
    sections.append("Cover and abstract")
    p("DSA5205 / PROJECT 2", "LabelCustom")
    p("Regularized Market Timing<br/>with Trend and<br/>Volatility Signals", "TitleCustom")
    p("A reproducible, daily SPY research backtest", "LabelCustom")
    p("Design date: 9 November 2026 (Singapore)<br/>Historical sample: January 2010 - December 2025<br/>Final holdout: January 2022 - December 2025")
    table(["Team details", ""], [["Group / team name", config.get("team_name", "")],
          ["Full member roster", ", ".join(config.get("team_members", []))]], [145, 306])
    heading("Abstract")
    p(f"This study tests whether five trailing trend and volatility features support daily market timing. A Ridge regression is refitted monthly on the latest 1,260 observations whose outcomes are already known. Four regularization strengths are compared only during 2019-2021; alpha={selection['selected_alpha']:g} is selected before evaluating 2022-2025. Positive forecasts trigger a fully invested SPY position; non-positive forecasts trigger cash. Trades occur at the next open, with explicit dividend entitlement and transaction costs.")
    p(f"At a single-side cost of 5 basis points, the strategy earns a {pct(ridge.cagr)} compound annual growth rate (CAGR), a {ridge.sharpe_rf_zero:.3f} Sharpe ratio, and a {pct(ridge.max_drawdown)} maximum drawdown. Buy-and-hold earns {pct(bh.cagr)} CAGR and a {bh.sharpe_rf_zero:.3f} Sharpe ratio. The model does not establish superior net performance. Reduced drawdown comes with lower exposure, and frequent position switching materially reduces gross returns.")
    p("Historical research only. Team identity and contribution fields are intentionally blank at the user's request; fill them before submission.", "SmallCustom")

    # 2
    section("Research question and economic rationale")
    p("The question is whether a small, transparent combination of recent returns, distance from a moving average, and realized volatility can improve the timing of equity exposure. The investable action is deliberately simple: hold SPY or hold cash. No leverage, short sales, individual-stock selection, or live order execution is involved.")
    heading("Competing economic mechanisms")
    p("Recent positive returns may persist if information is incorporated gradually or investors adjust positions slowly. Conversely, very short-term price moves may reverse after temporary liquidity pressure. Volatility can indicate a change in the uncertainty surrounding either mechanism. These are hypotheses motivating the feature set, not causal claims proven by this experiment.")
    p("A linear model allows the data to estimate the net association of these signals with the next executable return. Correlated lookbacks make unconstrained coefficients unstable; Ridge shrinkage is a natural way to retain all five inputs while limiting coefficient magnitudes. The design does not assume that more features or greater flexibility must improve performance.")
    table(["Question", "Evidence used"], [
        ["Is prediction useful?", "Out-of-sample MSE and R-squared against a past-only historical mean."],
        ["Is it economically useful?", "Net wealth, CAGR, volatility, Sharpe, drawdown, and turnover."],
        ["Does complexity add value?", "Compare Ridge timing with a fixed MA20 timing rule."],
        ["Is lower risk just lower exposure?", "Report exposure and a clearly ex post gross diagnostic."]], [145, 306])
    heading("Pre-specified scope")
    p("Only one return model family, one five-feature specification, one zero forecast threshold, one 1,260-observation window, and one monthly refit schedule are used. The only selected hyperparameter is alpha. All four candidates and the selection criterion are declared in config.json before the initial market-data download in this implementation.")
    p("This is not an external historical preregistration. The study is designed in 2026 using a historical holdout; the market history itself may already be familiar to researchers. The purpose of the lock is to make the implemented selection procedure auditable.", "SmallCustom")

    # 3
    section("Asset, data source, and research universe")
    p("SPY is the sole traded asset and the buy-and-hold benchmark. Selecting a fixed ETF avoids reconstructing a changing stock universe or estimating returns on delisted constituents. The conclusion is specific to this asset and period; it does not establish that a stock-selection strategy would work.")
    table(["Item", "Specification"], [["Asset / currency", "SPY / US dollars"],
          ["Frequency / calendar", "Daily; XNYS exchange sessions; America/New_York session dates"],
          ["Requested range", "2010-01-01 inclusive to 2026-01-01 exclusive"],
          ["Observed history", f"{audit['raw_rows']:,} sessions, 2010-01-04 to 2025-12-31"],
          ["Source", "Yahoo Finance through yfinance; auto_adjust=False, actions=True, repair=False"],
          ["Fields", "Open, High, Low, Close, Adj Close, Volume, Dividends, Stock Splits"],
          ["Distribution", "Raw prices remain in an ignored local cache; scripts and derived results are published."]], [130, 321])
    p("Unadjusted vendor OHLC and the dedicated adjusted close are fetched together with corporate actions. Trailing feature ratios use adjusted close; simulated execution uses unadjusted opens and explicit dividend receivables. SPY has no split events in the downloaded sample. The implementation fails explicitly if a split appears, rather than silently using incorrect share accounting.")
    heading("Provenance and revisions")
    p("data/provenance.json records the retrieval timestamp, vendor options, coverage, software version, and a SHA-256 digest of the serialized local CSV. The same serialized file is used for validation and testing. Upstream price revisions or different adjustment rounding can change results after a future download; exact reproduction is conditional on matching this input hash.")
    p("Data access: https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html. Access remains subject to the source's terms. No credentials are required by the supplied historical download script.", "SmallCustom")

    # 4
    section("Data cleaning and corporate-action audit")
    table(["Check", "Observed result"], [["Expected / observed sessions", f"{audit['expected_exchange_sessions']:,} / {audit['raw_rows']:,}"],
          ["Missing / extra exchange sessions", f"{audit['missing_exchange_sessions']} / {audit['extra_exchange_sessions']}"],
          ["Duplicate dates / missing values", f"{audit['duplicate_dates']} / {audit['missing_values']}"],
          ["Dividend / split events", f"{audit['dividend_events']} / {audit['split_events']}"],
          ["Zero-volume sessions", str(audit['zero_volume_sessions'])],
          ["Feature-ready, observable outcomes", f"{audit['complete_samples']:,}; 20 warm-up rows and 2 terminal labels excluded"]], [245, 206])
    p("Dates are sorted and normalized to local session dates. The code checks finite positive prices, non-negative volumes and distributions, and valid OHLC ordering. It fails on duplicate dates, missing observations, calendar mismatch, or unhandled splits. It does not fill weekends, holidays, or missing prices. Exchange-calendar verification accounts for special closures; the five-calendar-day gap ending 2012-10-31 is not treated as missing data.")
    p("Extreme observed returns are retained. Removing crisis observations after seeing full-sample returns could distort the experiment. No full-sample winsorization, interpolation, or learned cleaning thresholds are applied.")
    heading("Dividend event examples")
    rows = []
    for _, e in events.iloc[[0, -1]].iterrows():
        rows.append([e.ex_date, f"${e.Dividends:.4f}", f"{e.vendor_close_return * 100:.4f}%", f"{e.explicit_close_total_return * 100:.4f}%"])
    table(["Ex-date", "Dividend", "Vendor adj. return", "Explicit cash return"], rows, [90, 90, 135, 136])
    p(f"The mean absolute difference between vendor adjusted-close returns and explicit close-to-close cash-dividend returns is {audit['vendor_vs_explicit_close_return_mean_absolute_difference'] * 10000:.4f} basis points; the maximum is {audit['vendor_vs_explicit_close_return_max_absolute_difference'] * 10000:.4f} basis points. These are different adjustment/reinvestment conventions and are not forced to agree at machine precision. Execution P&amp;L consistently uses explicit cash dividends.")
    p("Source artifacts: output/data_audit.json and output/tables/dividend_event_checks.csv. Because no split occurs, a representative split-event check is not applicable.", "SmallCustom")

    # 5
    section("Features and information availability")
    p("Let A(t) be the vendor adjusted close on session t. All five features are computed after that session's close. No feature uses a future return, next-day open, future volume, or a fitted full-sample statistic.")
    table(["Feature", "Definition", "Motivation"], [
        ["return_1", "A(t) / A(t-1) - 1", "Very recent continuation or reversal"],
        ["return_5", "A(t) / A(t-5) - 1", "Weekly trend"],
        ["return_20", "A(t) / A(t-20) - 1", "Approximately monthly trend"],
        ["ma_gap_20", "A(t) / mean[A(t-19), ..., A(t)] - 1", "Distance from recent trend"],
        ["volatility_20", "Sample SD of the latest 20 one-session adjusted returns", "Recent uncertainty / risk state"]], [92, 184, 175])
    heading("Scaling and adjustment timing")
    p("At each monthly refit, StandardScaler learns the mean and population standard deviation from that refit's training window only. The scaler is held fixed with the model until the next refit. A future observation never changes the scaler used by an earlier forecast. Standardized coefficients therefore refer to a one-training-standard-deviation change in a feature.")
    p("Vendor adjusted histories can be revised after future dividends. These features use ratios and return volatility rather than absolute adjusted price levels. A later corporate-action adjustment that multiplies all prices in an earlier lookback window by the same factor cancels algebraically from the ratios and returns. A test verifies this invariance. Arbitrary vendor data corrections are still possible; a frozen input snapshot remains necessary for bitwise reproduction.")
    heading("Missing values")
    p("The first 20 sessions do not have enough history to calculate all features. The final two sessions do not have fully observed forward labels. These rows are excluded mechanically. Other missing vendor fields trigger failure and require inspection rather than an automatic fill.")
    p("Implementation: project2/core.py, make_samples and forecast; regression tests in tests/test_integrity.py.", "SmallCustom")

    # 6
    section("Labels, decision time, and execution")
    p("The model predicts the return that can actually be held after the signal. Let O(t) be the unadjusted opening price and D(t) the distribution with ex-date t. For a signal formed after close t, the asset return is:")
    p("y(t) = [O(t+2) + D(t+2)] / O(t+1) - 1", "CodeCustom")
    p("A position bought at open t+1 is held through the next opening auction. It receives a dividend when t+2 is an ex-date, because it was held before that ex-date. Buying at the ex-date open does not earn that day's dividend. The code treats the dividend receivable as available and reinvestable at the ex-date exit open; actual payment-date cash timing is abstracted away.")
    first = predictions.iloc[0]
    table(["Event", "Timing", "First holdout example"], [["Calculate features and signal", "After close t", first.decision_date[:10]],
          ["Execute target position", "Open t+1", first.entry_date[:10]],
          ["Mark return / next rebalance", "Open t+2", first.exit_date[:10]],
          ["Label becomes trainable", "After open t+2", "Known by that session's close"]], [165, 140, 146])
    heading("Label maturity matters")
    p("At close t, the most recent sample whose holding period ends at open t is known. A sample whose outcome ends at open t+1 is not. Training is explicitly filtered by exit_date &lt;= decision_date, in addition to requiring an earlier signal date. This prevents the common error of shifting the prediction label forward while still fitting to outcomes that have not occurred.")
    p("Period boundaries are based on holding dates: entry must be on or after the period start and exit on or before the period end. This allows the first test signal to be formed on 2021-12-31 for entry on 2022-01-03, without assigning any 2021 holding returns to the 2022-2025 test period.")
    p("Market-on-open fills are a research approximation. Fixed cost scenarios proxy fees and slippage; no order-book depth, market impact, auction rejection, or partial fills are modeled.", "SmallCustom")

    # 7
    section("Chronological split and rolling estimation")
    fig("09_protocol", "Figure 1. The validation period chooses alpha. The final holdout evaluates only the chosen model.")
    p("The initial development period is 2010-2018. Validation uses holding intervals within 2019-2021. The final holdout uses holding intervals within 2022-2025. Rows are never randomly shuffled across time.")
    p("At the first signal and at each new decision calendar month, the model fits the latest 1,260 fully realized samples. This is an approximately five-trading-year fixed-length window, not a literal five-calendar-year interval. At least 1,000 observations are required. Between refits, weights change with the daily prediction while coefficients and scaling remain fixed.")
    p(f"The final holdout contains {manifest['test_observations']:,} opening-to-opening holding intervals and {manifest['monthly_refits']} fits. There is an initial fit on the last session of 2021, followed by a fit at the first decision session of each month in 2022-2025. Earlier test outcomes may enter later training windows only after they have occurred. This is scheduled adaptation, not renewed hyperparameter selection.")
    heading("Why no arbitrary embargo?")
    p("The one-interval labels do not overlap with the unknown future outcome once the exit-date maturity filter is applied. The implementation therefore uses the actual information-availability rule rather than adding a generic arbitrary gap. A longer-horizon or overlapping-label design would need a revised maturity/purging rule.")
    p("The complete fitted-window history is exported, including each fit date, first and last training decision, maximum training-label exit, sample count, training means/scales, and fitted coefficients. This makes the correspondence between training and testing visible.", "SmallCustom")

    # 8
    section("Model and overfitting controls")
    p("For standardized feature matrix Z and realized holding returns y, Ridge solves:")
    p("minimize  sum_i [y_i - intercept - Z_i beta]^2<br/>          + alpha * sum_j beta_j^2", "CodeCustom")
    p("The intercept is not penalized. scikit-learn Ridge with solver='svd' is fitted through a StandardScaler/Ridge pipeline. The SVD solver is deterministic for this small dense problem; no stochastic gradient descent is used. A random seed of 42 is recorded for supporting tests and reproducibility.")
    table(["Control", "Role"], [["Five pre-defined features", "Restrict degrees of freedom and avoid feature mining"],
          ["L2 shrinkage", "Stabilize correlated trend coefficients"],
          ["1,260-observation window", "Use a fixed amount of past data at every fit"],
          ["Monthly refits", "Avoid daily parameter-search opportunities"],
          ["Four alpha values only", "Limit validation search"],
          ["Frozen zero threshold", "Avoid an additional timing-rule optimization"],
          ["Final holdout", "Separate selection from evaluation"]], [155, 296])
    p("The economic story does not require individual coefficients to retain a fixed sign. A positive coefficient on a recent-return feature is consistent with conditional continuation; a negative coefficient is consistent with conditional reversal. Because the inputs are correlated, coefficients should be interpreted jointly and descriptively, not as causal effects.")
    p("Ridge's objective uses a sum of squared errors, not an average loss. Alpha therefore has the scikit-learn scaling convention and should not be copied numerically into a differently normalized objective without adjustment.")
    p("Reference: scikit-learn Ridge documentation, https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html.", "SmallCustom")

    # 9
    section("Validation and final model selection")
    fig("05_validation", "Figure 2. Four candidates are evaluated on the same forward validation path after 5 bps costs.")
    table(["Alpha", "Validation CAGR", "Net Sharpe", "Exposure"], [[f"{r.alpha:g}", pct(r.cagr), f"{r.sharpe_rf_zero:.4f}", pct(r.exposure)] for _, r in grid.iterrows()], [70, 140, 120, 121])
    p(f"The declared rule selects the highest net validation Sharpe, with ties within 1e-12 resolved in favor of larger alpha. Alpha={selection['selected_alpha']:g} is selected. Alpha=0.1 and 1 produce the same validation trading outcomes because their forecast signs coincide, even though numerical forecasts need not be identical. The tie rule is applied without reference to test results.")
    p("output/selection.json stores the selected alpha, candidate count, protocol hash, raw-data hash, and validation-grid hash before the test routine runs. The test routine checks those fingerprints and evaluates only the selected alpha. Identical frozen runs may be repeated for reproducibility; they do not generate new evidence or justify selecting a different strategy.")
    p("Validation results can be optimistic after selection, even with only four candidates. The 2019-2021 validation environment is not guaranteed to resemble the final holdout. No nested search over thresholds, feature subsets, window sizes, or model families is performed.", "SmallCustom")

    # 10
    section("Positions, costs, and benchmark fairness")
    p("The trading rule is w(t)=1 if the predicted executable return is strictly positive, otherwise w(t)=0. The moving-average baseline uses w(t)=1 if the adjusted close exceeds its trailing 20-session average. Buy-and-hold uses w(t)=1 throughout. All three start with one unit of wealth, the same first entry date, and the same final liquidation date.")
    p("All positions are either fully invested in SPY or fully in cash. No shorting, leverage, financing, or borrowing is needed. Cash interest and the risk-free return used for Sharpe are both assumed to be zero. The latter makes Sharpe a zero-rate convention, not a claim about realized excess returns over Treasury bills.")
    heading("Multiplicative fee accounting")
    p("turnover(t) = abs[w(t) - w(t-1)]<br/>growth(t) = [1 - c * turnover(t)] * [1 + w(t) * y(t)]", "CodeCustom")
    p("Cost c is a pre-trade-equity haircut: 5 bps equals 0.0005 per unit of turnover. Fees are deducted before that interval's asset return. At the final exit, another factor [1 - c * w(last)] liquidates the remaining position. Binary weights avoid intermediate portfolio-weight drift. This is an explicitly defined fee convention, not an exact broker commission schedule.")
    table(["Case", "Turnover and charge"], [["Initial buy", "0 to 1: one single-side charge"],
          ["Stay invested / stay in cash", "No transaction charge"],
          ["Move to cash", "1 to 0: one single-side charge"],
          ["Terminal liquidation", "One additional charge if still invested"],
          ["Buy-and-hold", "One initial buy and one final sell"]], [180, 271])
    p("Main results use 5 bps. The pre-declared 0 and 10 bps scenarios reprice the same frozen predictions and positions; they do not select a different model. Fixed costs approximate trading frictions and omit endogenous market impact.")

    # 11
    section("Final holdout: headline results")
    table(["Metric", "Ridge", "MA20", "Buy & hold"], [
        ["CAGR", pct(ridge.cagr), pct(ma.cagr), pct(bh.cagr)],
        ["Annual arithmetic return", pct(ridge.annualized_arithmetic_return), pct(ma.annualized_arithmetic_return), pct(bh.annualized_arithmetic_return)],
        ["Annual volatility", pct(ridge.annualized_volatility), pct(ma.annualized_volatility), pct(bh.annualized_volatility)],
        ["Sharpe (rf = 0)", f"{ridge.sharpe_rf_zero:.3f}", f"{ma.sharpe_rf_zero:.3f}", f"{bh.sharpe_rf_zero:.3f}"],
        ["Maximum drawdown", pct(ridge.max_drawdown), pct(ma.max_drawdown), pct(bh.max_drawdown)],
        ["Total net return", pct(ridge.total_return), pct(ma.total_return), pct(bh.total_return)],
        ["Average equity exposure", pct(ridge.exposure), pct(ma.exposure), pct(bh.exposure)],
        ["Total one-way turnover", f"{ridge.total_turnover:.0f}", f"{ma.total_turnover:.0f}", f"{bh.total_turnover:.0f}"]], [160, 97, 97, 97])
    p("All headline values are net of 5 bps single-side costs, including entry and liquidation. CAGR uses terminal wealth raised to 252/N, where N is the number of holding intervals. Arithmetic annualized return is 252 times the mean net interval return. Volatility is the sample standard deviation times sqrt(252), and Sharpe is the arithmetic annualized return divided by annualized volatility.")
    p(f"The Ridge timing strategy trails buy-and-hold by {(ridge.cagr - bh.cagr) * 100:.2f} percentage points of CAGR and has a lower net Sharpe. It outperforms the fixed MA20 baseline on net CAGR and Sharpe, but that comparison alone is insufficient to establish successful market timing. Buy-and-hold is the economically important passive alternative.")
    p("Maximum drawdown uses the running peak including initial wealth, so an immediate loss is counted. The reported sample is not long enough to establish a stable long-run Sharpe, and no statistical significance or positive alpha is claimed.")
    p("Source: output/tables/test_metrics.csv; exact positions and daily accounting are in test_path_*.csv.", "SmallCustom")

    # 12
    section("Cumulative wealth and economic value")
    fig("01_wealth", "Figure 3. Common-date, net wealth paths begin at $1 and include final liquidation.")
    p(f"The final wealth of the Ridge strategy is ${1 + ridge.total_return:.3f} per initial dollar, compared with ${1 + bh.total_return:.3f} for buy-and-hold and ${1 + ma.total_return:.3f} for MA20 timing. The cumulative path, rather than a single favorable year, determines the economic comparison.")
    p("The strategy reduces exposure during some intervals but also misses positive returns. Because SPY has positive average returns over the test period, holding cash has an opportunity cost. A useful timing rule would need to compensate for this missed exposure and for the extra trading costs.")
    p("Forecast quality and investment value are related but not identical. The sign rule discards forecast magnitude: a tiny positive forecast receives the same full allocation as a large positive forecast. Small changes around zero can therefore produce substantial turnover even when predictive differences are economically negligible.")
    p("These observations suggest possible future work such as cost-aware thresholds or smoother weights, but such changes are not retrofitted to this holdout. Any revised design should be selected using a separate development protocol and evaluated on genuinely new data.")

    # 13
    section("Risk and drawdown interpretation")
    fig("02_drawdown", "Figure 4. Drawdowns are based on net wealth and an initial wealth peak of one.")
    p(f"Ridge's annualized volatility is {pct(ridge.annualized_volatility)}, below buy-and-hold's {pct(bh.annualized_volatility)}. Its maximum drawdown is {pct(ridge.max_drawdown)}, compared with {pct(bh.max_drawdown)}. This is some reduction in realized risk, but the strategy still experiences a substantial equity drawdown.")
    p(f"The MA20 strategy has the lowest annual volatility, {pct(ma.annualized_volatility)}, and a maximum drawdown of {pct(ma.max_drawdown)}. It also has the lowest CAGR. This makes the trade-off visible: reducing exposure can lower risk while reducing growth, without improving risk-adjusted performance.")
    p("A single maximum-drawdown number is path dependent and sensitive to the dates chosen. It should not be interpreted as an upper bound on future losses. The plot shows whether losses are concentrated or persistent; neither a lower drawdown nor lower volatility proves that the model correctly predicts market crashes.")
    p("An exposure diagnostic later in the report compares the strategy with a constant fractional equity exposure. That diagnostic is intentionally labeled ex post because it uses the observed test-period average exposure.")

    # 14
    section("Performance by calendar year")
    fig("03_annual", "Figure 5. Annual returns and Sharpe use a continuous portfolio path; there is no artificial December liquidation.")
    rows = []
    for year in sorted(annual.year.unique()):
        part = annual[annual.year == year].set_index("strategy")
        rows.append([year, pct(part.loc["Ridge timing", "total_return"]), pct(part.loc["MA20 timing", "total_return"]), pct(part.loc["SPY buy-and-hold", "total_return"])])
    table(["Year", "Ridge net return", "MA20 net return", "Buy & hold"], rows, [60, 130, 130, 131])
    p("Ridge loses less than buy-and-hold in 2022 but trails it in the three following calendar years. The benefit in one down-market year does not translate into superior full-period growth. MA20's performance also varies considerably by year.")
    p("Annual returns are compounded realized returns, not full-period CAGR estimates. Short annual Sharpe estimates are particularly noisy. The year breakdown is descriptive and does not support selecting a strategy separately for each year after the fact.")

    # 15
    section("Transaction-cost sensitivity")
    fig("04_costs", "Figure 6. Only cost assumptions change; selected alpha and positions remain fixed.")
    rows = []
    for _, r in cost[cost.strategy == "Ridge timing"].iterrows():
        rows.append([f"{r.cost_bps:g}", pct(r.cagr), f"{r.sharpe_rf_zero:.3f}", pct(r.max_drawdown)])
    table(["Single-side bps", "Ridge CAGR", "Ridge Sharpe", "Max drawdown"], rows, [110, 110, 115, 116])
    p(f"Ridge generates {ridge.total_turnover:.0f} units of one-way turnover, approximately {ridge.annualized_turnover:.1f} per year, versus two units in total for buy-and-hold. The zero-cost Ridge Sharpe is about 0.678, close to the zero-cost buy-and-hold Sharpe of 0.672. At 5 bps, Ridge's Sharpe drops to {ridge.sharpe_rf_zero:.3f}. Gross risk-adjusted performance therefore does not survive the specified implementation costs.")
    p("These scenarios show how sensitive the conclusion is to frictions. They are not empirical estimates of auction execution costs. The main 5 bps assumption was fixed before results were observed; the 0 and 10 bps scenarios are descriptive robustness checks.")

    # 16
    section("Prediction quality versus trading quality")
    fig("08_predictions", "Figure 7. Small forecasts are compared with much noisier realized holding returns.")
    table(["Prediction metric", "Final holdout"], [["R-squared vs past-only rolling historical mean", f"{pred['oos_r2_vs_past_mean']:.5f}"],
          ["Model MSE", f"{pred['mse']:.8f}"], ["Historical-mean MSE", f"{pred['historical_mean_mse']:.8f}"],
          ["Directional accuracy", pct(pred['directional_accuracy'])]], [310, 141])
    p("The historical-mean forecast is calculated from the same mature training window at each model refit. Out-of-sample R-squared is one minus the model squared-error sum divided by the baseline squared-error sum. It is not in-sample explained variance and not a comparison with the test-period mean.")
    p("The negative R-squared means Ridge does not beat this simple mean forecast on squared error. Directional accuracy alone is insufficient: it ignores return magnitudes, the unconditional proportion of positive days, transaction costs, and the relative consequences of missed gains and avoided losses. The net portfolio comparison remains the primary economic assessment.")

    # 17
    section("Exposure and the source of risk reduction")
    fig("06_exposure", "Figure 8. Monthly exposure is the fraction of holding intervals invested in SPY.")
    p(f"Ridge is invested during {pct(ridge.exposure)} of holdout intervals. A large part of the reduction in volatility can therefore arise mechanically from spending less time in the market. Comparing only maximum drawdown with a fully invested benchmark would overstate the evidence for timing skill.")
    ex = diagnostic["gross_constant_exposure_performance"]
    table(["Gross diagnostic", "Value"], [["Constant equity fraction", pct(diagnostic['holdout_mean_exposure'])],
          ["CAGR", pct(ex['cagr'])], ["Volatility", pct(ex['annualized_volatility'])],
          ["Sharpe (rf = 0)", f"{ex['sharpe_rf_zero']:.3f}"]], [310, 141])
    p("This fractional-exposure series uses the observed test-period mean exposure and ignores rebalancing costs. It is an ex post attribution diagnostic, not a feasible pre-specified benchmark or an alternative selected strategy. It demonstrates why reduced volatility, by itself, cannot establish a timing advantage.")
    p("An investable risk-matched comparison would need to set its exposure using pre-test information or a pre-specified adaptive volatility rule. That extension is deliberately outside this minimal experiment.")

    # 18
    section("Coefficient stability and model limitations")
    fig("07_coefficients", "Figure 9. Coefficients refer to standardized features and are expressed in basis points per training SD.")
    p("The monthly coefficient paths show how the fitted conditional relation changes as the fixed window rolls forward. Changing signs and magnitudes can reflect regime changes, correlated inputs, or estimation noise. This plot is descriptive; it is not used to remove features or choose a better-looking subsample.")
    p("The model is intentionally limited to linear additive effects. It cannot express arbitrary interactions, and its binary position map ignores confidence. Predictors based on nearby lookbacks overlap strongly, so individual coefficients are not uniquely interpretable as separate economic mechanisms. Ridge reduces instability but does not create signal where none exists.")
    p("Monthly refitting makes the model reproducible and computationally light, but can leave coefficients stale during rapid changes. More frequent refitting, nonlinear models, or cost-aware thresholds could be investigated later. They would enlarge the search space and require a fresh evaluation protocol, rather than a second attempt on the present holdout.")
    p("Only one asset and one four-year holdout are studied. No claim of broad market generality, causal identification, statistically significant alpha, or readiness for real trading follows from these results.")

    # 19
    section("Reproducibility and integrity checks")
    p("Run commands from the repository root using Python 3.12. The README includes the full environment setup, independent stage commands, expected artifacts, and source mapping. The main run downloads data only when the local cache is absent.")
    p("python -m venv .venv<br/>source .venv/bin/activate<br/>python -m pip install -r requirements.txt<br/>python -m pytest -q<br/>python -m project2.pipeline all<br/>python -m project2.report", "CodeCustom")
    p("The test suite covers executable label alignment, correct ex-date entitlement, future-price perturbation, adjusted-feature scale invariance, label maturity, past-only scaling, monthly refits, initial and terminal costs, cash positions, period boundaries, invalid data, and drawdown from initial capital. Synthetic prices are used only as unit-test fixtures; all reported performance uses downloaded historical observations.")
    table(["Artifact", "Purpose"], [["config.json", "Frozen research choices and separate authorship fields"],
          ["data/provenance.json", "Source options, coverage, and raw-file digest"],
          ["output/selection.json", "Validation selection and experiment fingerprints"],
          ["test_fit_audit.csv", "Past-only training windows, scaling, and coefficients"],
          ["test_predictions.csv / test_path_*.csv", "Predictions, positions, and interval accounting"],
          ["output/run_manifest.json", "Versions, hashes, dates, and reproducible settings"]], [205, 246])
    p("A clean-install rerun should reproduce results conditional on matching input data. Exact CSV/PNG bytes may differ across numerical libraries and rendering environments. Repository results provide a comparison target; any upstream input revision must be disclosed, rather than silently overwriting the original selection lock.")

    # 20
    section("What worked, what failed, and conclusion")
    heading("What worked")
    p("The full workflow runs from historical prices to a validated model, executable positions, cost-aware accounting, and independently inspectable output tables. Training respects label maturity, feature scaling is past-only, benchmarks use common dates and identical cost conventions, and all four validation candidates are disclosed. The strategy has lower realized volatility and a smaller maximum drawdown than buy-and-hold in this sample.")
    heading("What failed")
    p("Validation performance did not carry over at the same level to the final holdout. Prediction R-squared is negative against a past-only historical mean. At the specified 5 bps cost, net CAGR and Sharpe are lower than buy-and-hold. Frequent sign changes create substantial turnover, and lower market exposure sacrifices gains in positive years. The evidence does not support claiming a robust market-timing edge.")
    heading("Assumptions limiting interpretation")
    p("Cash earns zero, the Sharpe reference rate is zero, orders fill at the next opening price, and fees are a fixed proportional haircut. Distributions are credited as ex-date receivables rather than actual payment-date cash. The single-asset sample is narrow, and the historical holdout is not an externally preregistered prospective test. Confidence intervals, multiple-testing-adjusted inference, market impact, and factor alpha are not estimated.")
    heading("Conclusion")
    p(f"For this frozen design, Ridge timing earns {pct(ridge.cagr)} net CAGR and {ridge.sharpe_rf_zero:.3f} Sharpe, compared with {pct(bh.cagr)} and {bh.sharpe_rf_zero:.3f} for buy-and-hold. The result is a transparent negative finding about net superiority, with a measurable risk/exposure trade-off. Sound process and honest interpretation are the principal research outputs.")
    heading("Future work, not tested here")
    p("A cost-aware no-trade region, smoother position sizes, a pre-specified investable risk-matched benchmark, and prospective evaluation are reasonable future questions. None is selected or reported as an improved strategy using the current test period.")

    # 21
    section("References, contributions, and submission")
    refs = [
        "DSA5205. Project 2: Design, Validate, and Analyze an Original Asset Trading Strategy. Course assignment brief, 2026. Requirements and motivating examples; the original brief is not redistributed.",
        "Chinco, A., A. D. Clark-Joseph, and M. Ye (2019). Sparse Signals in the Cross-Section of Returns. Journal of Finance 74(1), 449-492. https://doi.org/10.1111/jofi.12733. Contextual reading suggested by the assignment; this study does not reproduce its intraday design.",
        "Kelly, B. T., S. Malamud, and K. Zhou (2024). The Virtue of Complexity in Return Prediction. Journal of Finance 79(1), 459-501. https://doi.org/10.1111/jofi.13298. Contextual reading; this study uses five ordinary features rather than random Fourier features.",
        "yfinance documentation. Historical download options and corporate-action fields. https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html",
        "scikit-learn documentation. Ridge and StandardScaler. https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html and https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html",
        "exchange_calendars. Exchange-session schedules and special closures. https://github.com/gerrymanoim/exchange_calendars"
    ]
    for ref in refs:
        p(escape(ref), "SmallCustom")
    heading("Team contribution statement")
    contributions = config.get("contributions", {})
    table(["Member", "Contribution"], list(contributions.items()) or [["", ""] for _ in range(4)], [145, 306])
    p("Team fields are blank pending user-provided names and contributions. Rename Group_X_Report.pdf to the actual group number, confirm Canvas membership, and review the report before submission. The repository also includes a timed video script and walkthrough materials.")
    p("Implementation assistance disclosure: code and this report were prepared with AI assistance; market data were downloaded and the pipeline was executed. Team members should review, understand, and accurately disclose their own contributions under applicable course rules. No human authorship, participation, or completed presentation is fabricated.", "SmallCustom")

    out = Path("output/pdf/Group_X_Report.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=(595.28, 841.89), leftMargin=72, rightMargin=72,
                            topMargin=60, bottomMargin=58, title="Regularized Market Timing with Trend and Volatility Signals",
                            author=", ".join(config.get("team_members", [])), pageCompression=1)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#dce3e9"))
        canvas.line(72, 43, 523, 43)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY)
        canvas.drawString(72, 30, "DSA5205 Project 2 | Historical SPY research | Costs: 5 bps")
        canvas.drawRightString(523, 30, str(doc.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    from pypdf import PdfReader
    pages = len(PdfReader(out).pages)
    if pages != len(sections):
        raise RuntimeError(f"Report overflow: expected {len(sections)} pages, rendered {pages}; inspect and correct")
    print(f"REPORT: {out} ({pages} pages)")
    return out


if __name__ == "__main__":
    import argparse
    import os
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", help="Read saved results from a separate run directory")
    args = parser.parse_args()
    if args.workspace:
        os.chdir(Path(args.workspace).resolve())
    build()
