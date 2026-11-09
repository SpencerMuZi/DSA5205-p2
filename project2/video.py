"""Build a narrated draft from actual recorded outputs (macOS say + bundled FFmpeg).

This is disclosed synthetic narration over result charts and actual command logs,
not a recording of team members or a claim of live screen capture.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import textwrap

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from .core import write_json


def chapters():
    from pypdf import PdfReader
    report_path = Path('output/pdf/Group_33_Report.pdf')
    if not report_path.exists():
        report_path = Path('output/pdf/Group_X_Report.pdf')
    page_count = len(PdfReader(report_path).pages)
    metrics = pd.read_csv("output/tables/test_metrics.csv").set_index("strategy")
    ridge, bh, ma = [metrics.loc[n] for n in ["Ridge timing", "SPY buy-and-hold", "MA20 timing"]]
    pred = json.loads(Path("output/prediction_metrics.json").read_text())
    audit = json.loads(Path("output/data_audit.json").read_text())
    selected = json.loads(Path("output/selection.json").read_text())["selected_alpha"]
    records = []

    def add(title, points, narration, figure=None, log_index=None):
        records.append(dict(title=title, points=points, narration=narration,
                            figure=figure, log_index=log_index))

    add("Regularized SPY market timing", ["Five past-only features", "One return model; four alpha values", "Final holdout: 2022-2025", "Synthetic narration; actual research results"],
        "This walkthrough presents a historical research project on daily SPY market timing. It covers the economic hypothesis, data construction, time alignment, training, validation, executable positions, and final out of sample results after trading costs. The narration is synthetic, and the charts and command outputs come from an executed research pipeline. It does not represent a presentation by named team members. The central finding is modest: the selected Ridge model reduces some realized risk but does not beat buy and hold on net compound growth or net Sharpe. That negative result is retained. The purpose is to demonstrate a complete and auditable research process, rather than to manufacture a successful trading strategy.")
    add("Economic story and competing mechanisms", ["Trend may continue", "Short-term moves may reverse", "Volatility describes uncertainty", "These are hypotheses, not causal findings"],
        "The economic hypothesis begins with two competing mechanisms. Recent returns might continue when information is incorporated gradually or investors adjust positions slowly. Short moves might instead reverse after temporary liquidity pressure. Recent volatility can describe a different market state, changing the reliability of either pattern. We therefore combine several return lookbacks, a moving average gap, and realized volatility. A regularized linear model estimates their joint relationship with the next executable return. This is deliberately a small model. It does not assume that a nonlinear model, a large feature set, or an elaborate neural network must help. The economic mechanisms motivate the experiment, but the backtest cannot identify them causally.")
    add("Actual data-build command", ["Local cache shown on reproducibility rerun", "Original fetch: Yahoo Finance via yfinance"],
        "The repository provides separate commands for data, validation, testing, figures, and the report. This screen shows actual captured output from the data command. The original run downloaded SPY daily prices and corporate actions from Yahoo Finance using yfinance. The demonstrated rerun uses that frozen local cache, so it is explicitly labeled cache rather than pretending to perform a new download. Prices are requested from January twenty ten through December twenty twenty five. The download uses unadjusted OHLC, a separate adjusted close, and dividend and split events. A provenance file records the source options and the SHA two fifty six digest of the serialized input used by every following stage.", log_index=1)
    add("Data integrity before modeling", [f"{audit['raw_rows']:,} exchange sessions", "No missing or duplicate dates", "64 dividend events; no splits", "Extreme market observations retained"],
        "Data quality is checked before any model is fitted. All four thousand and twenty four observed sessions match the expected exchange calendar, including special closures. There are no duplicate session dates, missing fields, or zero volume observations. The code checks positive finite prices, nonnegative distributions, and valid high and low ordering. It does not interpolate market prices or fill weekends. Sixty four dividend events and no split events are observed. Extreme market returns are retained rather than removed after inspecting the full sample. A five calendar day gap in twenty twelve is consistent with the exchange schedule. The code would fail explicitly on a calendar mismatch or an unsupported split.")
    add("Five features known at the close", ["Returns over 1, 5, and 20 sessions", "Adjusted close / MA20 minus one", "20-session realized volatility", "Scaler fitted on the training window only"],
        "The five features are the one session return, five session return, twenty session return, the adjusted close divided by its twenty session average minus one, and the standard deviation of the latest twenty adjusted returns. Every input is available after the signal session closes. The first twenty rows are warm up observations, not trading opportunities with invented history. Scaling is fitted only on the current training window and then applied forward with the fitted model. Absolute backward adjusted price levels are never predictors. A common later adjustment factor cancels from these ratios and return statistics. A unit test verifies this property, although arbitrary future vendor corrections can still change a downloaded history.")
    add("A forecast must match an executable return", ["Signal: after close t", "Entry: open t+1", "Exit / next rebalance: open t+2", "Train only after the label has matured"],
        "A critical design choice is matching the prediction label to a return the strategy could actually earn. The signal is calculated after the close of session t. Trading takes place at the next session's open, and the holding interval ends at the following open. The label is therefore an open to open return, not a close to close return. Training samples are included only when their exit date is already known by the current decision close. This excludes the most recent immature labels even if their feature rows already exist. The maturity filter is checked in the model audit and tested by perturbing future prices and confirming that past predictions remain unchanged.")
    add("Dividend entitlement is explicit", ["Entry on an ex-date: no same-day entitlement", "Carry into an exit ex-date: entitled", "Credit ex-date receivable at exit", "Do not double-count adjusted prices and cash"],
        "Dividend accounting requires care because adjusted prices and explicit cash flows should not be mixed inconsistently. Execution uses raw opening prices. A position bought on an ex dividend date does not receive that day's dividend. A position carried from the previous session into the exit ex dividend date does receive it. The holding return therefore adds the exit date distribution to the exit opening price before dividing by the entry opening price. This research convention credits the dividend receivable at the ex date opening, abstracting from the actual payment date. Feature returns use vendor adjusted close, but execution profits use explicit distributions. The report documents the small difference between vendor adjustment and explicit cash return conventions.")
    add("Frozen chronological design", ["Development: 2010-2018", "Validation: 2019-2021", "Final holdout: 2022-2025", "Monthly refits; latest 1,260 mature labels"],
        "The chronological split separates development, selection, and final evaluation. The initial development history runs from twenty ten through twenty eighteen. The forward validation period is twenty nineteen through twenty twenty one. The final holdout is twenty twenty two through twenty twenty five. At each new decision month, the model is refitted on the latest twelve hundred and sixty realized training outcomes. It requires at least one thousand observations. The first test signal is formed at the end of twenty twenty one for entry at the first opening session of twenty twenty two. Earlier test outcomes may later enter training after they occur, but alpha, the features, the window, and the trading rule remain fixed.", figure="09_protocol")
    add("Ridge and overfitting control", ["StandardScaler + Ridge, SVD solver", "L2 penalty stabilizes correlated inputs", "Alpha grid: 0.1, 1, 10, 100", "No threshold or feature-subset search"],
        "Ridge regression minimizes squared return errors plus alpha times the sum of squared coefficients. The intercept is not penalized. Standardization makes the penalty comparable across differently scaled features. The implementation uses the deterministic singular value decomposition solver through a scikit learn pipeline. The only selected hyperparameter is alpha, with four values fixed before the initial download: zero point one, one, ten, and one hundred. There is no search over dozens of indicators, alternative thresholds, or model families. Restricting that search is an important overfitting control. Regularization can reduce estimation instability, but it cannot guarantee that noisy market features contain a useful predictive signal.")
    add("Actual validation output and selection", [f"Selected alpha: {selected:g}", "Criterion: validation net Sharpe at 5 bps", "Ties choose stronger shrinkage"],
        "This screen shows actual validation command output for all four candidates. Each model is fitted forward through time, converted into positions, and assessed after five basis point costs. The declared criterion is highest validation net Sharpe, and ties within numerical tolerance choose the larger penalty. Alpha zero point one and alpha one produce the same validation trading outcomes because their prediction signs coincide. Alpha one is therefore selected. The selection file records protocol, input, and validation table hashes before final testing. Only the selected alpha is evaluated on the holdout. The validation Sharpe is above one point two, but this attractive selected result is not treated as a forecast of future performance.", log_index=2)
    add("From forecasts to positions and fees", ["Forecast > 0: fully invested", "Otherwise: cash; interest assumed zero", "5 bps per unit of one-way turnover", "Entry and final exit charged to every strategy"],
        "The position map is intentionally simple. A strictly positive predicted return produces a full SPY position; otherwise the strategy holds cash. There is no leverage or short selling. Cash interest is zero by assumption. Every change between cash and SPY creates one unit of one way turnover. The cost is a five basis point fraction of pretrade equity and is deducted before that interval's asset return. Initial entry and final liquidation are included. Buy and hold pays one initial purchase charge and one final sale charge. The moving average baseline uses identical timing and fees. Costs are multiplicative, so the code does not accidentally charge a sale after the relevant interval has already earned returns.")
    add("Actual final holdout output", ["Selected model only", "Common holding dates and cost conventions"],
        f"The final test uses the selected model and contains one thousand and two holding intervals. This is actual command output rather than a hand entered performance table. After five basis point single side costs, Ridge compound annual growth is {ridge.cagr * 100:.2f} percent, annualized volatility is {ridge.annualized_volatility * 100:.2f} percent, and Sharpe is {ridge.sharpe_rf_zero:.3f}. Buy and hold compound growth is {bh.cagr * 100:.2f} percent with Sharpe {bh.sharpe_rf_zero:.3f}. The moving average baseline grows at {ma.cagr * 100:.2f} percent. We retain these results even though the model does not win. There is no second holdout pass used to choose a more flattering model or a different set of features.", log_index=3)
    add("Cumulative wealth: growth sacrificed", ["Every strategy starts at one dollar", "Common final liquidation", "Reduced exposure has an opportunity cost"],
        f"The cumulative wealth plot shows the economic result over the full holdout, including all fees. One initial dollar becomes approximately {1 + ridge.total_return:.3f} dollars under Ridge and {1 + bh.total_return:.3f} dollars under buy and hold. The timing strategy avoids some negative intervals but also misses gains. SPY's average return is positive during this period, so moving into cash has an opportunity cost. The binary position rule also discards forecast magnitude. A tiny positive forecast receives the same full investment as a large positive forecast. Small forecast changes near zero can therefore trigger trades whose costs are substantial relative to the expected signal. This helps explain why prediction and trading value must be evaluated separately.", figure="01_wealth")
    add("Drawdown: a trade-off, not a victory", [f"Ridge maximum drawdown: {ridge.max_drawdown * 100:.2f}%", f"Buy-and-hold drawdown: {bh.max_drawdown * 100:.2f}%", "Initial capital included in running peak"],
        "The drawdown plot provides a risk perspective. Ridge has a smaller full period maximum drawdown than buy and hold, but still experiences a substantial loss from a prior peak. Its lower realized volatility is partly consistent with holding less equity. The moving average rule has lower volatility still, together with lower compound growth. Drawdown is path dependent: a smaller observed drawdown is not a guarantee about the next crisis and not proof of crash prediction. The accounting includes initial wealth in the running peak, so an immediate loss is counted correctly. The report therefore describes a risk and growth trade off, rather than presenting the lower drawdown as sufficient evidence of a superior strategy.", figure="02_drawdown")
    add("Annual results reveal instability", ["Ridge loses less in 2022", "Buy-and-hold leads in 2023-2025", "No annual strategy switching after the fact"],
        "The year by year breakdown shows where the aggregate result comes from. Ridge loses less than buy and hold during twenty twenty two, but trails buy and hold in each of the following three years. The benefit in the down year does not compensate for the missed gains and trading costs across the complete holdout. Annual results use a continuous portfolio path. There is no artificial liquidation and repurchase each December, and costs remain assigned to the intervals when they occur. Short annual Sharpe estimates are noisy. The year table is descriptive; it is not a license to choose the winner for each year after seeing what happened.", figure="03_annual")
    add("Costs explain much of the gap", ["Same frozen positions at 0, 5, and 10 bps", "246 one-way turnover units", "Gross Sharpe near benchmark; net Sharpe lower"],
        "The sensitivity plot changes only the cost assumption, holding predictions and positions fixed. Ridge generates two hundred and forty six units of total one way turnover, compared with two for buy and hold. At zero cost, its Sharpe is approximately zero point six seven eight, close to buy and hold's zero point six seven two. Five basis point costs lower Ridge Sharpe to about zero point four eight one. At ten basis points it falls further. These are scenarios rather than empirical measurements of auction costs. The main assumption was chosen in advance. The result illustrates why a seemingly competitive gross strategy can fail once realistic implementation frictions are even approximately represented.", figure="04_costs")
    add("Prediction quality and exposure", [f"OOS R-squared: {pred['oos_r2_vs_past_mean']:.5f}", f"Equity exposure: {ridge.exposure * 100:.2f}%", "Historical-mean forecast uses past data only"],
        "Prediction error is compared with a historical mean estimated from the same mature rolling training window. Out of sample R squared is negative, so Ridge does not beat that simple forecast on squared error. Directional accuracy is close to fifty one percent, but accuracy ignores return magnitude and costs. Ridge is invested for about sixty nine percent of holding intervals, which helps explain lower volatility. The report includes an ex post constant exposure diagnostic to illustrate that point. Because its exposure is calculated from the holdout, it is clearly labeled a diagnostic, not an investable benchmark. Neither reduced exposure nor a slightly better hit rate establishes economically valuable timing skill.", figure="08_predictions")
    add("Actual integrity-test output", ["Future price perturbation", "Mature labels and past-only scaling", "Dividend entitlement and fee timing"],
        "This screen shows actual test output from the repository. The tests use synthetic fixtures only to verify code behavior; reported strategy returns always use downloaded market observations. Tests perturb future prices and confirm that earlier features, fitted scaling, and predictions remain unchanged. Other tests check label maturity, dividend entitlement, monthly refitting, initial and final transaction fees, all cash positions, calendar boundaries, and drawdown from starting capital. Synthetic data are never substituted when a download fails. A separate clean environment check installs the declared dependencies and reruns the frozen analysis on the same local input snapshot. Reproduction is conditional on matching that snapshot because vendor histories can be revised.", log_index=0)
    add("Reproduce and inspect the artifacts", ["README: exact commands and expected outputs", "Fit audits, predictions, and portfolio paths", f"Group 33 LaTeX report: {page_count} pages", "Raw market-data cache excluded from Git"],
        f"The repository contains exact setup and run commands, pinned package versions, the frozen configuration, input provenance, the validation selection file, model fit audits, predictions, and portfolio accounting tables. The {page_count} page Group 33 report is compiled from the authors' supplied Overleaf sources. The walkthrough log records the original research commands actually executed and their exit codes. The report has a separate compilation manifest. Team details and contribution statements are maintained in the manuscript metadata. The raw vendor price cache is excluded from Git, so a clean checkout downloads its own copy or uses an authorized matching local snapshot. If upstream data change, the stored lock refuses to overwrite the original experiment silently. A revised input requires a separately disclosed run.")
    add("Conclusion and honest next steps", ["No robust net outperformance established", "Lower risk comes with lower exposure", "Cost-aware redesign requires new evaluation", "Synthetic walkthrough is a review draft"],
        "The final conclusion is that this small Ridge timing design does not establish net superiority over buy and hold. It has lower realized exposure and some reduction in drawdown, but lower net growth and Sharpe under the declared cost assumption. Prediction R squared is negative, and turnover is a major source of drag. The useful output is a complete, transparent experiment with explicit timing and honest interpretation. Future work could examine a no trade region, smoother position sizes, or a pre specified risk matched benchmark, but those ideas have not been optimized on this holdout. Before submission, the team should review the code and report, confirm its identity and contribution information, and decide how to present these findings in its own reviewed video.")
    return records


def fonts():
    import matplotlib
    root = Path(matplotlib.get_data_path()) / "fonts/ttf"
    return (ImageFont.truetype(str(root / "DejaVuSans-Bold.ttf"), 37),
            ImageFont.truetype(str(root / "DejaVuSans.ttf"), 27),
            ImageFont.truetype(str(root / "DejaVuSansMono.ttf"), 18),
            ImageFont.truetype(str(root / "DejaVuSans.ttf"), 17))


def render_frame(chapter, number, logs, dest):
    titlefont, bodyfont, codefont, smallfont = fonts()
    im = Image.new("RGB", (1280, 720), "#f7fafc")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1280, 12), fill="#087f8c")
    d.text((55, 36), f"DSA5205 PROJECT 2   /   {number:02d}", font=smallfont, fill="#087f8c")
    titlelines = textwrap.wrap(chapter["title"], width=48)
    y = 70
    for line in titlelines:
        d.text((55, y), line, font=titlefont, fill="#203550")
        y += 46
    if chapter["figure"]:
        chart = Image.open(f"output/figures/{chapter['figure']}.png").convert("RGB")
        chart.thumbnail((1155, 435))
        im.paste(chart, ((1280-chart.width)//2, y + 12))
        line = "  |  ".join(chapter["points"])
        for j, text in enumerate(textwrap.wrap(line, width=105)):
            d.text((55, 592 + j*24), text, font=smallfont, fill="#203550")
    elif chapter["log_index"] is not None:
        record = logs[chapter["log_index"]]
        d.rounded_rectangle((45, y + 10, 1235, 565), 12, fill="#13243a")
        logtext = "$ " + record["command"] + "\n\n" + record["stdout"].strip()
        logtext = logtext.replace(" [100%]", "")
        for i, text in enumerate(logtext.splitlines()[:18]):
            # Long pytest progress line is cosmetic, not numerical output.
            if len(text) > 105 and "passed" not in text and set(text.strip()) <= set(". []0123456789%"):
                text = "..........."
            d.text((62, y + 28 + i*23), text[:106], font=codefont, fill="#d9f1f4")
        d.text((55, 586), "Actual captured output; data fetch rerun uses frozen cache.", font=smallfont, fill="#526174")
    else:
        y += 34
        for point in chapter["points"]:
            lines = textwrap.wrap(point, width=69)
            d.ellipse((58, y+11, 68, y+21), fill="#087f8c")
            for line in lines:
                d.text((92, y), line, font=bodyfont, fill="#203550")
                y += 39
            y += 28
    d.line((55, 666, 1225, 666), fill="#cbd5df", width=1)
    d.text((55, 681), "Historical data only  |  Disclosed synthetic narration  |  Review draft", font=smallfont, fill="#526174")
    im.save(dest)


def audio_duration(path, ffmpeg):
    info = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", info)
    if not match:
        raise RuntimeError(f"Cannot read audio duration: {info}")
    h, m, s = map(float, match.groups())
    return h*3600 + m*60 + s


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true", help="Requires installed macOS say voice Samantha")
    args = parser.parse_args()
    records = chapters()
    dest = Path("output/video")
    dest.mkdir(parents=True, exist_ok=True)
    work = Path("tmp/video")
    work.mkdir(parents=True, exist_ok=True)
    logs = json.loads((dest / "demo_steps.json").read_text())
    script = ["# Video walkthrough script", "", "Disclosed synthetic-narration draft using actual recorded command outputs and results. Group 33 identity and contributions are maintained in the report metadata.", ""]
    for i, rec in enumerate(records, 1):
        script.extend([f"## {i:02d}. {rec['title']}", "", rec["narration"], ""])
        render_frame(rec, i, logs, work / f"frame-{i:02d}.png")
        (work / f"narration-{i:02d}.txt").write_text(rec["narration"])
    (dest / "walkthrough_script.md").write_text("\n".join(script))
    write_json(dest / "chapters.json", records)
    words = sum(len(x["narration"].split()) for x in records)
    print(f"VIDEO SCRIPT: {len(records)} chapters, {words} words; approximate narration {words/130:.1f} minutes", flush=True)
    if not args.render:
        return
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    total, segments, times = 0., [], []
    for i, rec in enumerate(records, 1):
        audio = work / f"audio-{i:02d}.aiff"
        subprocess.run(["say", "-v", "Samantha", "-r", "130", "-f", str(work / f"narration-{i:02d}.txt"), "-o", str(audio)], check=True)
        seconds = audio_duration(audio, ffmpeg) + 1.5
        segment = work / f"segment-{i:02d}.mp4"
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "10",
                        "-i", str(work / f"frame-{i:02d}.png"), "-i", str(audio), "-t", f"{seconds:.3f}",
                        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "24",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k", "-af", "apad=pad_dur=1.5", str(segment)], check=True)
        times.append({"chapter": i, "title": rec["title"], "start_seconds": round(total, 2), "duration_seconds": round(seconds, 2)})
        total += seconds
        segments.append(segment)
        print(f"RENDERED {i:02d}/{len(records)}: {seconds:.1f}s; total {total/60:.1f}min", flush=True)
    listing = work / "concat.txt"
    listing.write_text("\n".join(f"file '{p.name}'" for p in segments) + "\n")
    out = dest / "Strategy_A_Walkthrough.mp4"
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    actual = audio_duration(out, ffmpeg)
    if not 900 <= actual <= 1500:
        raise RuntimeError(f"Video duration {actual:.2f}s is outside 15-25 minutes")
    write_json(dest / "video_manifest.json", {"duration_seconds": actual, "duration_minutes": actual/60,
               "resolution": "1280x720", "fps": 10, "audio": "AAC mono, synthetic macOS Samantha voice, 130 wpm",
               "word_count": words, "chapters": times,
               "disclosure": "Synthetic narration over charts and captured real stage outputs; not team-member narration or a live screen recording.",
               "status": "Review draft; identity and contribution fields not supplied."})
    print(f"VIDEO: {out} ({actual/60:.2f} min)", flush=True)


if __name__ == "__main__":
    main()
