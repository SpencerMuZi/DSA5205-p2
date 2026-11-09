"""CLI: fetch -> validate and lock -> evaluate selected model -> build figures."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys

import numpy as np
import pandas as pd

from .core import (digest, evaluate_predictions, forecast, make_samples, performance,
                   prediction_metrics, protocol_digest, read_config, write_json)
from .data import audit, fetch, load


def setup():
    for folder in ["output/tables", "output/figures", "output/pdf", "output/video", "data/raw"]:
        Path(folder).mkdir(parents=True, exist_ok=True)


def validate(samples, config):
    lock_path = Path("output/selection.json")
    fingerprint = {"protocol_sha256": protocol_digest(config), "raw_sha256": digest("data/raw/spy_daily.csv")}
    if lock_path.exists():
        old = json.loads(lock_path.read_text())
        if any(old[k] != v for k, v in fingerprint.items()):
            raise RuntimeError("Protocol/data changed after selection. Use a separate output directory/run; do not overwrite the original experiment.")
    records, all_audits = [], []
    for alpha in config["alphas"]:
        pred, fit_audit = forecast(samples, config["validation_start"], config["validation_end"], alpha, config)
        metrics, _ = evaluate_predictions(pred, config["main_cost_bps"], config)
        row = metrics.loc[metrics.strategy == "Ridge timing"].iloc[0].to_dict()
        row.update(alpha=alpha, **prediction_metrics(pred))
        records.append(row)
        pred.to_csv(f"output/tables/validation_predictions_alpha_{alpha:g}.csv", index=False)
        all_audits.append(fit_audit)
    table = pd.DataFrame(records)
    sharpe = table.sharpe_rf_zero.fillna(-np.inf)
    candidates = table.loc[sharpe >= sharpe.max() - 1e-12]
    if not np.isfinite(sharpe.max()):
        raise RuntimeError("All validation portfolios have undefined Sharpe; inspect before selecting")
    selected = float(candidates.alpha.max())
    table.to_csv("output/tables/validation_grid.csv", index=False)
    pd.concat(all_audits).to_csv("output/tables/validation_fit_audit.csv", index=False)
    lock = {**fingerprint, "selected_alpha": selected, "candidate_count": len(table),
            "selection_rule": config["selection"],
            "validation_grid_sha256": digest("output/tables/validation_grid.csv"),
            "test_performance_used_for_selection": False,
            "note": "Protocol set before this implementation's first data download; not an external historical preregistration."}
    write_json(lock_path, lock)
    print("VALIDATION (4 candidates; costs applied):\n" + table[["alpha", "cagr", "sharpe_rf_zero", "exposure"]].to_string(index=False), flush=True)
    print(f"LOCKED alpha={selected:g}; no other alpha evaluated on the final holdout", flush=True)
    return lock


def test(samples, config):
    lock = json.loads(Path("output/selection.json").read_text())
    if (lock["protocol_sha256"] != protocol_digest(config)
            or lock["raw_sha256"] != digest("data/raw/spy_daily.csv")):
        raise RuntimeError("Selection fingerprint mismatch")
    if digest("output/tables/validation_grid.csv") != lock["validation_grid_sha256"]:
        raise RuntimeError("Validation table changed after selection")
    pred, fit_audit = forecast(samples, config["test_start"], config["test_end"], lock["selected_alpha"], config)
    pred.to_csv("output/tables/test_predictions.csv", index=False)
    fit_audit.to_csv("output/tables/test_fit_audit.csv", index=False)
    if not (pd.to_datetime(fit_audit.max_label_exit) <= pd.to_datetime(fit_audit.fit_date)).all():
        raise AssertionError("Training label leakage")
    metrics, paths = evaluate_predictions(pred, config["main_cost_bps"], config)
    metrics.to_csv("output/tables/test_metrics.csv", index=False)
    for name, path in paths.items():
        key = {"Ridge timing": "ridge", "MA20 timing": "ma20", "SPY buy-and-hold": "buy_hold"}[name]
        path.to_csv(f"output/tables/test_path_{key}.csv", index=False)
    sensitivity = []
    for cost in config["sensitivity_cost_bps"]:
        rows, _ = evaluate_predictions(pred, cost, config)
        sensitivity.append(rows)
    pd.concat(sensitivity).to_csv("output/tables/cost_sensitivity.csv", index=False)
    annual = []
    for name, path in paths.items():
        # Continuous portfolio accounting; no artificial liquidation each December.
        for year, part in path.groupby(pd.to_datetime(path.exit_date).dt.year):
            annual.append({"strategy": name, "year": int(year),
                           **performance(part.net_return, config["annualization"]),
                           "exposure": float(part.weight.mean()), "turnover": float(part.turnover.sum())})
    pd.DataFrame(annual).to_csv("output/tables/annual_metrics.csv", index=False)
    exposure = float(pred.ridge_weight.mean())
    # Diagnostic only: exposure estimated on the holdout, NOT an investable baseline.
    matched = performance(exposure * pred.target, config["annualization"])
    write_json("output/prediction_metrics.json", prediction_metrics(pred))
    write_json("output/exposure_diagnostic.json", {"holdout_mean_exposure": exposure,
               "gross_constant_exposure_performance": matched,
               "warning": "Ex post gross diagnostic, not an investable strategy or tuned alternative."})
    versions = {}
    for name in ["numpy", "pandas", "scikit-learn", "matplotlib", "yfinance", "reportlab", "exchange-calendars", "pytest"]:
        versions[name] = importlib.metadata.version(name)
    write_json("output/run_manifest.json", {"python": platform.python_version(), "packages": versions,
               "platform": platform.platform(), "seed": config["seed"],
               "config": config, "protocol_sha256": protocol_digest(config),
               "raw_sha256": digest("data/raw/spy_daily.csv"),
               "test_first_decision": str(pred.decision_date.min().date()),
               "test_first_entry": str(pred.entry_date.min().date()),
               "test_last_exit": str(pred.exit_date.max().date()),
               "test_observations": len(pred), "monthly_refits": len(fit_audit),
               "test_predictions_sha256": digest("output/tables/test_predictions.csv"),
               "test_metrics_sha256": digest("output/tables/test_metrics.csv"),
               "cash_and_risk_free_rates": 0.0,
               "repeat_run_policy": "Identical frozen pipeline may be rerun for reproducibility; no holdout-driven redesign."})
    print("TEST (selected model only):\n" + metrics[["strategy", "cagr", "annualized_volatility", "sharpe_rf_zero", "max_drawdown", "exposure"]].to_string(index=False), flush=True)
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["fetch", "validate", "test", "figures", "all"])
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--workspace", help="Separate run directory; preserve the published experiment and lock")
    parser.add_argument("--refresh", action="store_true", help="Refresh raw cache; fails lock if upstream data changed")
    args = parser.parse_args()
    config = read_config(args.config)
    if args.workspace:
        workspace = Path(args.workspace).resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        os.chdir(workspace)
        write_json("config.json", config)
    np.random.seed(config["seed"])
    setup()
    if args.command in {"fetch", "all"}:
        fetch(config, args.refresh)
    if args.command in {"validate", "test", "all"}:
        raw = load()
        result = audit(raw)
        print(f"AUDIT: {result['raw_rows']} sessions, {result['dividend_events']} dividend events, {result['split_events']} splits", flush=True)
        samples = make_samples(raw)
        if args.command in {"validate", "all"}:
            validate(samples, config)
        if args.command in {"test", "all"}:
            test(samples, config)
    if args.command in {"figures", "all"}:
        from .figures import build
        build(config)
        print("FIGURES: output/figures", flush=True)


if __name__ == "__main__":
    main()
