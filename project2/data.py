"""Explicit vendor download, local cache, provenance, and corporate-action checks."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path

import numpy as np
import pandas as pd

from .core import clean_prices, digest, make_samples, write_json


def fetch(config, refresh=False):
    path = Path("data/raw/spy_daily.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not refresh:
        print(f"CACHE: {path} sha256={digest(path)}", flush=True)
        return path
    import yfinance as yf
    yf.set_tz_cache_location(str(Path('.cache/yfinance').resolve()))
    raw = yf.download(config["ticker"], start=config["start"], end=config["end_exclusive"],
                      auto_adjust=False, actions=True, repair=False, progress=False,
                      threads=False, keepna=True, timeout=30)
    if raw.empty:
        raise RuntimeError("Yahoo returned no prices. Retry later; no synthetic data fallback is used.")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = clean_prices(raw)
    raw.index.name = "Date"
    raw.to_csv(path, float_format="%.12g")
    # Freeze and validate the serialized artifact used by every subsequent command.
    reloaded = pd.read_csv(path, index_col="Date", parse_dates=True)
    clean_prices(reloaded)
    write_json("data/provenance.json", {
        "ticker": config["ticker"], "source": "Yahoo Finance via yfinance",
        "documentation": "https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_start": config["start"], "requested_end_exclusive": config["end_exclusive"],
        "yfinance_version": importlib.metadata.version("yfinance"),
        "auto_adjust": False, "actions": True, "repair": False,
        "sha256": digest(path), "rows": len(raw),
        "first_session": str(raw.index.min().date()), "last_session": str(raw.index.max().date()),
        "raw_data_redistributed": False,
        "note": "Local research cache excluded from Git. Upstream revisions can change the hash."
    })
    print(f"FETCHED: {len(raw)} daily observations, sha256={digest(path)}", flush=True)
    return path


def load():
    return clean_prices(pd.read_csv("data/raw/spy_daily.csv", index_col="Date", parse_dates=True))


def audit(raw):
    import exchange_calendars as xcals
    calendar = xcals.get_calendar("XNYS", start=str(raw.index.min().date()), end=str(raw.index.max().date()))
    expected = calendar.sessions_in_range(raw.index.min(), raw.index.max()).tz_localize(None)
    missing_sessions = expected.difference(raw.index)
    extra_sessions = raw.index.difference(expected)
    if len(missing_sessions) or len(extra_sessions):
        raise ValueError(f"Exchange calendar mismatch: missing={list(missing_sessions)}, extra={list(extra_sessions)}")
    # Adjusted Close returns use the vendor's backward-adjustment convention.
    # Manual cash-dividend reinvestment differs slightly; report, do not force equality.
    vendor = raw["Adj Close"].pct_change(fill_method=None)
    explicit = (raw["Close"] + raw["Dividends"]) / raw["Close"].shift() - 1
    difference = (vendor - explicit).dropna()
    events = raw.loc[raw.Dividends > 0, ["Dividends"]].copy()
    events["vendor_close_return"] = vendor.reindex(events.index)
    events["explicit_close_total_return"] = explicit.reindex(events.index)
    events["return_difference"] = difference.reindex(events.index)
    events.to_csv("output/tables/dividend_event_checks.csv", index_label="ex_date")
    gap_days = raw.index.to_series().diff().dt.days
    samples = make_samples(raw)
    result = {"raw_rows": len(raw), "duplicate_dates": int(raw.index.duplicated().sum()),
              "expected_exchange_sessions": len(expected), "missing_exchange_sessions": len(missing_sessions),
              "extra_exchange_sessions": len(extra_sessions),
              "missing_values": int(raw.isna().sum().sum()),
              "zero_volume_sessions": int((raw.Volume == 0).sum()),
              "split_events": int((raw["Stock Splits"] != 0).sum()),
              "dividend_events": len(events), "maximum_calendar_gap_days": int(gap_days.max()),
              "calendar_gaps_over_4_days": [str(x.date()) for x in gap_days[gap_days > 4].index],
              "vendor_vs_explicit_close_return_mean_absolute_difference": float(difference.abs().mean()),
              "vendor_vs_explicit_close_return_max_absolute_difference": float(difference.abs().max()),
              "largest_absolute_adjusted_close_return": float(vendor.abs().max()),
              "feature_warmup_rows": 20, "terminal_forward_label_rows_excluded": 2,
              "complete_samples": len(samples),
              "first_sample": str(samples.index.min().date()),
              "last_sample": str(samples.index.max().date()),
              "calendar_note": "XNYS calendar verified using exchange-calendars; all expected sessions present, including special closures. Weekends/holidays not filled.",
              "execution_return": "Raw open-to-open plus distribution receivable on EXIT ex-date; no splits observed.",
              "adjusted_features": "Scale-invariant trailing ratios; full-history price levels never used as predictors.",
              "outliers": "Legitimate extreme market returns retained; no full-sample winsorization."}
    write_json("output/data_audit.json", result)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    samples.to_csv("data/processed/samples.csv")
    return result
