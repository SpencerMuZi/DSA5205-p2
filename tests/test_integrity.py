"""Accounting and leakage tests use synthetic fixtures, never substitute for market results."""
import numpy as np
import pandas as pd
import pytest

from project2.core import (FEATURES, account, clean_prices, eligible_training, forecast,
                           make_samples, performance, period_samples)


def fixture_prices(n=220):
    rng = np.random.default_rng(42)
    index = pd.bdate_range("2018-01-01", periods=n)
    close = 100 * np.exp(np.cumsum(rng.normal(.0003, .01, n)))
    opening = close * np.exp(rng.normal(0, .002, n))
    return pd.DataFrame({"Open": opening, "Close": close, "High": np.maximum(opening, close) * 1.01,
                         "Low": np.minimum(opening, close) * .99, "Adj Close": close,
                         "Volume": 100000, "Dividends": 0., "Stock Splits": 0.}, index=index)


def config():
    return {"training_observations": 70, "minimum_training_observations": 50, "threshold": 0.0}


def test_execution_alignment_and_dividend_entitlement():
    raw = fixture_prices()
    raw.loc[raw.index[52], "Dividends"] = 1.5
    samples = make_samples(raw)
    before = samples.loc[raw.index[50]]
    on_entry = samples.loc[raw.index[51]]
    assert before.entry_date == raw.index[51]
    assert before.exit_date == raw.index[52]
    assert before.target == pytest.approx((raw.Open.iloc[52] + 1.5) / raw.Open.iloc[51] - 1)
    assert on_entry.target == pytest.approx(raw.Open.iloc[53] / raw.Open.iloc[52] - 1)


def test_future_price_perturbation_does_not_change_past_features():
    raw = fixture_prices()
    altered = raw.copy()
    cutoff = raw.index[130]
    altered.loc[altered.index > cutoff, ["Open", "Close", "High", "Low", "Adj Close"]] *= 4
    a, b = make_samples(raw), make_samples(altered)
    pd.testing.assert_frame_equal(a.loc[:cutoff, FEATURES], b.loc[:cutoff, FEATURES])


def test_future_backward_adjustment_factor_cancels_from_features():
    raw = fixture_prices()
    altered = raw.copy()
    cutoff = raw.index[130]
    altered.loc[:cutoff, "Adj Close"] *= .8
    a, b = make_samples(raw), make_samples(altered)
    np.testing.assert_allclose(a.loc[:cutoff, FEATURES], b.loc[:cutoff, FEATURES], atol=1e-14)


def test_labels_must_have_matured_before_fit():
    samples = make_samples(fixture_prices())
    day = samples.index[100]
    train = eligible_training(samples, day, 70)
    assert len(train) == 70
    assert train.exit_date.max() <= day
    assert day not in train.index
    assert samples.index[samples.index.get_loc(day) - 1] not in train.index


def test_future_changes_cannot_change_earlier_predictions_or_scaling():
    raw = fixture_prices(260)
    cutoff = raw.index[185]
    changed = raw.copy()
    changed.loc[changed.index > cutoff, ["Open", "High", "Low", "Close", "Adj Close"]] *= 3
    a, audit_a = forecast(make_samples(raw), raw.index[100], cutoff, 1., config())
    b, audit_b = forecast(make_samples(changed), raw.index[100], cutoff, 1., config())
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(audit_a, audit_b)
    assert (pd.to_datetime(audit_a.max_label_exit) <= pd.to_datetime(audit_a.fit_date)).all()


def test_refit_scaler_uses_only_current_training_window():
    samples = make_samples(fixture_prices())
    pred, audit = forecast(samples, samples.index[80], samples.index[130], 1., config())
    for _, row in audit.iterrows():
        train = eligible_training(samples, pd.Timestamp(row.fit_date), 70)
        for feature in FEATURES:
            assert row[f"mean_{feature}"] == pytest.approx(train[feature].mean())
    assert len(audit) == pd.to_datetime(pred.decision_date).dt.to_period("M").nunique()


def test_buy_hold_initial_entry_final_exit_and_multiplicative_fees():
    p = account([.1, -.05, .02], [1, 1, 1], 5)
    assert p.turnover.sum() == 2
    assert p.wealth.iloc[-1] == pytest.approx((1 - .0005) ** 2 * 1.1 * .95 * 1.02)


def test_cash_and_switching_costs():
    p = account([.1, .5, .1], [1, 0, 1], 10)
    assert p.turnover.tolist() == [1, 1, 2]
    assert p.net_return.iloc[1] == pytest.approx(-.001)
    assert account([.1, -.5], [0, 0], 10).wealth.iloc[-1] == 1


def test_drawdown_includes_initial_capital():
    assert performance([-.1, .01])["max_drawdown"] == pytest.approx(-.1)


def test_period_boundaries_use_actual_holding_dates():
    samples = make_samples(fixture_prices())
    selected = period_samples(samples, "2018-06-01", "2018-08-31")
    assert selected.entry_date.min() >= pd.Timestamp("2018-06-01")
    assert selected.exit_date.max() <= pd.Timestamp("2018-08-31")


def test_missing_data_and_splits_fail_explicitly():
    raw = fixture_prices()
    raw.loc[raw.index[60], "Open"] = np.nan
    with pytest.raises(ValueError, match="Missing"):
        clean_prices(raw)
    raw = fixture_prices()
    raw.loc[raw.index[60], "Stock Splits"] = 2
    with pytest.raises(ValueError, match="splits"):
        clean_prices(raw)
