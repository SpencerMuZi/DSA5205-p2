"""Time alignment, past-only model fitting, accounting, and evaluation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["return_1", "return_5", "return_20", "ma_gap_20", "volatility_20"]


def read_config(path="config.json"):
    config = json.loads(Path(path).read_text())
    fixed = {"ticker": "SPY", "refit": "monthly", "ma_window": 20,
             "cash_return": 0.0, "risk_free_rate": 0.0}
    for key, value in fixed.items():
        if config.get(key) != value:
            raise ValueError(f"This implementation requires {key}={value!r}; extend the code for other conventions")
    if (pd.Timestamp(config["validation_end"]) >= pd.Timestamp(config["test_start"])):
        raise ValueError("Validation and testing must be chronological and disjoint")
    return config


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol_digest(config):
    # Authorship metadata does not affect the experiment or invalidate its lock.
    research = {k: v for k, v in config.items()
                if k not in {"team_name", "team_members", "contributions"}}
    return hashlib.sha256(json.dumps(research, sort_keys=True).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def clean_prices(raw):
    """Fail on unhandled corporate actions and missing sessions; never fill prices."""
    raw = raw.copy()
    required = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]
    missing = set(required) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing vendor fields: {missing}")
    raw.index = pd.DatetimeIndex(raw.index).tz_localize(None).normalize()
    raw = raw.sort_index()
    if raw.index.has_duplicates:
        raise ValueError("Duplicate session dates; inspect source before continuing")
    if raw[required].isna().any().any():
        raise ValueError("Missing vendor observations; inspect rather than forward fill")
    if not np.isfinite(raw[required].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite vendor observations")
    if (raw[["Open", "High", "Low", "Close", "Adj Close"]] <= 0).any().any():
        raise ValueError("Non-positive prices")
    if (raw["Volume"] < 0).any() or (raw["Dividends"] < 0).any():
        raise ValueError("Negative volume or distribution")
    if (raw["Stock Splits"] != 0).any():
        raise ValueError("This SPY implementation requires no splits; extend share accounting first")
    if ((raw["Low"] > raw[["Open", "Close"]].min(axis=1) + 1e-6)
            | (raw["High"] < raw[["Open", "Close"]].max(axis=1) - 1e-6)).any():
        raise ValueError("OHLC ordering violated")
    return raw


def make_samples(raw):
    """At close t: forecast total return from open t+1 through open t+2.

    Entry on an ex-date is NOT entitled to that dividend; a position carried
    into the exit ex-date IS entitled. Credit that receivable at exit open.
    This is an ex-date reinvestment convention, not actual pay-date cash timing.
    """
    raw = clean_prices(raw)
    close = raw["Adj Close"]
    f = pd.DataFrame(index=raw.index)
    for lag in [1, 5, 20]:
        f[f"return_{lag}"] = close.pct_change(lag, fill_method=None)
    f["ma_gap_20"] = close / close.rolling(20).mean() - 1
    f["volatility_20"] = close.pct_change(fill_method=None).rolling(20).std(ddof=1)
    dates = pd.Series(raw.index, index=raw.index)
    f["entry_date"] = dates.shift(-1)
    f["exit_date"] = dates.shift(-2)
    f["entry_open"] = raw["Open"].shift(-1)
    f["exit_open"] = raw["Open"].shift(-2)
    f["exit_dividend"] = raw["Dividends"].shift(-2)
    f["target"] = (f["exit_open"] + f["exit_dividend"]) / f["entry_open"] - 1
    # Feature warm-up and the last two unobservable forward outcomes only.
    f = f.dropna()
    f.index.name = "decision_date"
    return f


def period_samples(samples, start, end):
    # Use holding dates, not the signal date, to define financial reporting years.
    return samples.loc[(samples.entry_date >= pd.Timestamp(start))
                       & (samples.exit_date <= pd.Timestamp(end))].copy()


def eligible_training(samples, decision_date, n=1260):
    # Labels that finish at today's open are known by today's close.
    return samples.loc[(samples.index < decision_date)
                       & (samples.exit_date <= decision_date)].tail(n)


def forecast(samples, start, end, alpha, config):
    period = period_samples(samples, start, end)
    if period.empty:
        raise ValueError("Empty forecast period")
    rows, audits = [], []
    previous_month = None
    model = None
    mean_forecast = None
    fit_date = None
    for date, sample in period.iterrows():
        month = date.to_period("M")
        if month != previous_month:
            train = eligible_training(samples, date, config["training_observations"])
            if len(train) < config["minimum_training_observations"]:
                raise ValueError(f"Insufficient training data at {date}: {len(train)}")
            model = make_pipeline(StandardScaler(), Ridge(alpha=alpha, solver="svd"))
            model.fit(train[FEATURES], train["target"])
            mean_forecast = float(train.target.mean())
            fit_date = date
            scaler, ridge = model.steps[0][1], model.steps[1][1]
            audit = {"fit_date": str(date.date()), "train_first_decision": str(train.index.min().date()),
                     "train_last_decision": str(train.index.max().date()),
                     "max_label_exit": str(train.exit_date.max().date()), "n_train": len(train),
                     "alpha": float(alpha), "intercept": float(ridge.intercept_)}
            for i, feature in enumerate(FEATURES):
                audit[f"mean_{feature}"] = float(scaler.mean_[i])
                audit[f"scale_{feature}"] = float(scaler.scale_[i])
                audit[f"coef_{feature}"] = float(ridge.coef_[i])
            audits.append(audit)
            previous_month = month
        prediction = float(model.predict(sample[FEATURES].to_frame().T.astype(float))[0])
        rows.append({"decision_date": date, "entry_date": sample.entry_date,
                     "exit_date": sample.exit_date, "fit_date": fit_date,
                     "target": float(sample.target), "prediction": prediction,
                     "historical_mean": mean_forecast,
                     "ridge_weight": float(prediction > config["threshold"]),
                     "ma_weight": float(sample.ma_gap_20 > 0), "buy_hold_weight": 1.0})
    return pd.DataFrame(rows), pd.DataFrame(audits)


def account(asset_returns, weights, cost_bps, liquidate=True):
    """Fees are fractions of pre-trade equity; deduct before interval returns.

    Binary positions eliminate intermediate allocation drift. Both initial entry
    and terminal liquidation are charged, including to the buy-and-hold benchmark.
    """
    r, w = np.asarray(asset_returns, float), np.asarray(weights, float)
    if len(r) != len(w) or len(w) == 0:
        raise ValueError("Returns and weights must have the same nonzero length")
    if not np.isfinite(r).all() or not np.isfinite(w).all() or not np.isin(w, [0.0, 1.0]).all():
        raise ValueError("Finite returns and binary positions required")
    if (r <= -1).any() or cost_bps < 0 or cost_bps >= 10000:
        raise ValueError("Invalid returns or costs")
    turnover = np.abs(w - np.r_[0.0, w[:-1]])
    c = cost_bps / 10000
    growth = (1 - c * turnover) * (1 + w * r)
    gross = w * r
    if liquidate:
        growth[-1] *= 1 - c * w[-1]
        turnover[-1] += w[-1]
    net = growth - 1
    return pd.DataFrame({"weight": w, "asset_return": r, "gross_return": gross,
                         "turnover": turnover, "net_return": net,
                         "wealth": np.cumprod(growth), "fee_drag": gross - net})


def performance(returns, annualization=252):
    r = np.asarray(returns, float)
    if not len(r):
        raise ValueError("Empty return series")
    growth = np.cumprod(1 + r)
    # Include initial wealth in the peak, so an immediate loss is a drawdown.
    peaks = np.maximum.accumulate(np.r_[1.0, growth])[1:]
    volatility = float(r.std(ddof=1) * np.sqrt(annualization)) if len(r) > 1 else 0.0
    mean_return = float(r.mean() * annualization)
    return {"n_intervals": len(r), "total_return": float(growth[-1] - 1),
            "cagr": float(growth[-1] ** (annualization / len(r)) - 1),
            "annualized_arithmetic_return": mean_return,
            "annualized_volatility": volatility,
            "sharpe_rf_zero": mean_return / volatility if volatility > 0 else None,
            "max_drawdown": float(np.min(growth / peaks - 1))}


def evaluate_predictions(predictions, cost_bps, config):
    results, paths = [], {}
    for name, column in [("Ridge timing", "ridge_weight"), ("MA20 timing", "ma_weight"),
                         ("SPY buy-and-hold", "buy_hold_weight")]:
        path = account(predictions.target, predictions[column], cost_bps)
        for col in ["decision_date", "entry_date", "exit_date"]:
            path[col] = predictions[col].to_numpy()
        metrics = performance(path.net_return, config["annualization"])
        metrics.update(strategy=name, cost_bps=float(cost_bps),
                       exposure=float(path.weight.mean()),
                       total_turnover=float(path.turnover.sum()),
                       annualized_turnover=float(path.turnover.mean() * config["annualization"]),
                       total_additive_fee_drag=float(path.fee_drag.sum()))
        results.append(metrics)
        paths[name] = path
    return pd.DataFrame(results), paths


def prediction_metrics(pred):
    error = np.asarray(pred.target - pred.prediction)
    base_error = np.asarray(pred.target - pred.historical_mean)
    denominator = float(base_error @ base_error)
    return {"n": len(pred), "mse": float(np.mean(error ** 2)),
            "historical_mean_mse": float(np.mean(base_error ** 2)),
            "oos_r2_vs_past_mean": 1 - float(error @ error) / denominator if denominator > 0 else None,
            "directional_accuracy": float(np.mean((pred.prediction > 0) == (pred.target > 0)))}
