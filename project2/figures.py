"""All charts read saved results; no refitting or model selection here."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .core import FEATURES

COLORS = {"Ridge timing": "#087f8c", "MA20 timing": "#e69b39", "SPY buy-and-hold": "#263b5e"}


def build(config):
    plt.rcParams.update({"figure.figsize": (10, 4.7), "figure.dpi": 130,
                         "font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.labelcolor": "#24344d",
                         "axes.titlesize": 14, "axes.grid": True, "grid.alpha": .18,
                         "savefig.facecolor": "white"})
    dest = Path("output/figures")
    dest.mkdir(parents=True, exist_ok=True)

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(dest / f"{name}.png", dpi=180, bbox_inches="tight")
        plt.close(fig)

    paths = {}
    for name, key in [("Ridge timing", "ridge"), ("MA20 timing", "ma20"), ("SPY buy-and-hold", "buy_hold")]:
        paths[name] = pd.read_csv(f"output/tables/test_path_{key}.csv", parse_dates=["entry_date", "exit_date"])
    fig, ax = plt.subplots()
    for name, p in paths.items():
        dates = pd.concat([p.entry_date.iloc[:1], p.exit_date], ignore_index=True)
        ax.plot(dates, np.r_[1, p.wealth], label=name, color=COLORS[name], lw=1.8)
    ax.set(title="Final holdout: wealth after transaction costs", ylabel="Growth of $1", xlabel="Holding-period exit date")
    ax.legend(frameon=False)
    save(fig, "01_wealth")

    fig, ax = plt.subplots()
    for name, p in paths.items():
        peak = np.maximum.accumulate(np.r_[1.0, p.wealth])[1:]
        ax.plot(p.exit_date, 100 * (p.wealth / peak - 1), label=name, color=COLORS[name], lw=1.2)
    ax.set(title="Drawdowns include the initial investment", ylabel="Drawdown (%)", xlabel="Exit date")
    ax.legend(frameon=False, loc="lower left")
    save(fig, "02_drawdown")

    annual = pd.read_csv("output/tables/annual_metrics.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7))
    for ax, col, title in zip(axes, ["total_return", "sharpe_rf_zero"], ["Calendar-year net return (%)", "Calendar-year Sharpe (rf = 0)"]):
        pivot = annual.pivot(index="year", columns="strategy", values=col)[list(COLORS)]
        if col == "total_return":
            pivot *= 100
        pivot.plot.bar(ax=ax, color=[COLORS[x] for x in pivot.columns], width=.8, rot=0)
        ax.axhline(0, color="#687383", lw=.7)
        ax.set(title=title, xlabel="Exit year")
        ax.legend(fontsize=8, frameon=False)
    save(fig, "03_annual")

    costs = pd.read_csv("output/tables/cost_sensitivity.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7))
    for name in COLORS:
        p = costs[costs.strategy == name]
        axes[0].plot(p.cost_bps, 100 * p.cagr, "o-", color=COLORS[name], label=name)
        axes[1].plot(p.cost_bps, p.sharpe_rf_zero, "o-", color=COLORS[name], label=name)
    axes[0].set(title="Cost sensitivity: CAGR", xlabel="Single-side cost (basis points)", ylabel="CAGR (%)")
    axes[1].set(title="Cost sensitivity: Sharpe", xlabel="Single-side cost (basis points)")
    axes[0].legend(frameon=False, fontsize=8)
    save(fig, "04_costs")

    grid = pd.read_csv("output/tables/validation_grid.csv")
    fig, ax = plt.subplots()
    ax.plot(grid.alpha, grid.sharpe_rf_zero, "o-", color=COLORS["Ridge timing"])
    for _, r in grid.iterrows():
        ax.annotate(f"{r.sharpe_rf_zero:.3f}", (r.alpha, r.sharpe_rf_zero), xytext=(0, 9), textcoords="offset points", ha="center")
    ax.set(xscale="log", title="Validation only: pre-declared four-candidate grid", xlabel="Ridge alpha (log scale)", ylabel="Net Sharpe (5 bps, rf = 0)")
    ax.margins(y=.3)
    save(fig, "05_validation")

    fig, ax = plt.subplots()
    for name in ["Ridge timing", "MA20 timing"]:
        p = paths[name].set_index("exit_date")
        monthly = p.weight.resample("ME").mean()
        ax.plot(monthly.index, monthly * 100, label=name, color=COLORS[name])
    ax.set(title="Monthly average equity exposure", ylabel="Days invested (%)", xlabel="Month", ylim=(-5, 105))
    ax.legend(frameon=False)
    save(fig, "06_exposure")

    fits = pd.read_csv("output/tables/test_fit_audit.csv", parse_dates=["fit_date"])
    fig, ax = plt.subplots()
    for feature in FEATURES:
        ax.plot(fits.fit_date, fits[f"coef_{feature}"] * 10000, label=feature)
    ax.axhline(0, color="#687383", lw=.7)
    ax.set(title="Monthly Ridge coefficients on standardized features", ylabel="Predicted return per 1 SD (bps)", xlabel="Fit date")
    ax.legend(ncol=3, frameon=False, fontsize=8)
    save(fig, "07_coefficients")

    pred = pd.read_csv("output/tables/test_predictions.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7))
    axes[0].scatter(pred.prediction * 100, pred.target * 100, s=6, alpha=.3, color=COLORS["Ridge timing"])
    axes[0].axhline(0, color="#687383", lw=.7)
    axes[0].axvline(0, color="#687383", lw=.7)
    axes[0].set(title="Forecasts versus realized returns", xlabel="Predicted return (%)", ylabel="Realized holding return (%)")
    axes[1].hist(pred.prediction * 10000, bins=35, color=COLORS["Ridge timing"], alpha=.85)
    axes[1].axvline(0, color="#263b5e", lw=1)
    axes[1].set(title="Distribution of return forecasts", xlabel="Predicted return (bps)", ylabel="Observations")
    save(fig, "08_predictions")

    # Fully chronological, scaled by actual calendar dates.
    fig, ax = plt.subplots(figsize=(10, 3.5))
    spans = [("Initial training / development", "2010-01-01", "2018-12-31", "#263b5e"),
             ("Forward validation", "2019-01-01", "2021-12-31", "#e69b39"),
             ("Final holdout", "2022-01-01", "2025-12-31", "#087f8c")]
    for i, (name, start, end, color) in enumerate(spans):
        left, right = mdates.date2num(pd.Timestamp(start)), mdates.date2num(pd.Timestamp(end))
        ax.barh(i, right - left, left=left, color=color, height=.55)
    ax.set_yticks(range(3), [s[0] for s in spans])
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.invert_yaxis()
    ax.set(title="Frozen chronology; monthly refits use 1,260 mature observations", xlabel="Calendar year")
    save(fig, "09_protocol")
