# DSA5205 Project 2 — Group 33

**Regularized Market Timing with Transaction Costs: Evidence from Daily SPY Returns**

Members: **Li Chongkai, Zhang Leyao, Zhang Yikai, Ye Tiantian**. The report lists each member's contributions.

## Submission materials

- [Group 33 report — 21 pages](output/pdf/Group_33_Report.pdf).
- [Authoritative Overleaf sources](paper/main.tex), [team metadata](paper/metadata.tex), and [build instructions](paper/README.md).
- [Download the PDF, Overleaf ZIP, and code ZIP](https://github.com/SpencerMuZi/DSA5205-p2/releases/latest).
- [Compilation record](output/report_build.json) and [source-file identities](paper/source_manifest.json).

The report sources in `paper/` include the tables and vector figures. The final team presentation was submitted separately through Canvas.

For Overleaf, upload `DSA5205_Project2_Group33_Overleaf.zip`, select `main.tex`, and choose **XeLaTeX**. No Python environment or market-data download is needed to compile that archive.

## Research result

The strategy uses five trailing SPY features, monthly rolling Ridge fits, validation-only penalty selection, and a frozen cost-aware holdout. It reduces some realized risk but does **not** outperform SPY buy-and-hold on net CAGR or Sharpe.

Holding dates: 3 January 2022 opening entry through 31 December 2025 opening liquidation; 1,002 intervals. Single-side cost is **5 bps**, including entry and liquidation. Cash interest and the Sharpe reference rate are zero by assumption.

| Metric | Ridge timing | MA20 timing | SPY buy-and-hold |
|---|---:|---:|---:|
| CAGR | 6.54% | 3.69% | 11.18% |
| Annualized arithmetic return | 7.56% | 4.22% | 12.27% |
| Annualized volatility | 15.72% | 10.83% | 18.31% |
| Sharpe, rf = 0 | 0.481 | 0.389 | 0.670 |
| Maximum drawdown | -22.20% | -19.14% | -26.28% |
| Average equity exposure | 69.36% | 65.27% | 100.00% |
| Total one-way turnover | 246 | 102 | 2 |

The grid `[0.1, 1, 10, 100]` is evaluated only in validation. Alpha **1** is selected by validation net Sharpe, with ties favoring stronger shrinkage. Test prediction R-squared against the past-only historical mean is **-0.00541**. Ridge's zero-cost Sharpe is approximately **0.678**, falling to **0.481** at 5 bps.

![Holdout wealth](output/figures/01_wealth.png)

## Compile the supplied report

With XeLaTeX and BibTeX installed:

```bash
cd paper
latexmk -xelatex main.tex
```

Alternatively, use `tectonic --untrusted main.tex` in `paper/` (verified with Tectonic 0.17.0). These commands produce `paper/main.pdf`.

The Python wrapper verifies the published source and research-result fingerprints and writes the submission filename:

```bash
python -m project2.report
```

Expected output: `output/pdf/Group_33_Report.pdf` and `output/report_build.json`. The wrapper compiles the included manuscript and verifies its inputs.

## Reproduce the analysis

Python **3.12** is the tested version. From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pytest -q
python -m project2.pipeline all --workspace runs/reproduction
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. `requirements.txt` pins direct dependencies; `requirements-lock.txt` records the clean-install transitive environment.

The analysis command creates a separate workspace, downloads historical Yahoo data if no cache exists, audits exchange sessions and corporate actions, validates four penalties, locks selection, and evaluates only the selected holdout model. Results go to `runs/reproduction/output/`. Expected output includes **4,024 sessions, 64 dividend events, 0 splits, alpha=1**, and the metrics above, conditional on matching the vendor snapshot.

The manuscript appendix cites analysis commit `2e2e265ba9d007c94279225febaa15a054dff7cf`. The saved results and validation selection are included in this repository.

The report uses the recorded data snapshot. A fresh vendor download may differ after historical revisions, so run the analysis in a separate workspace as shown above.

Raw prices are excluded from Git and the code ZIP. Provenance is in [data/provenance.json](data/provenance.json). Identical-input reproduction is documented in [output/reproducibility_check.json](output/reproducibility_check.json).

## Individual research stages

Append `--workspace runs/reproduction` to use a separate run directory:

```bash
python -m project2.pipeline fetch
python -m project2.pipeline validate
python -m project2.pipeline test
python -m project2.pipeline figures
```

Within an established run, cached input is reused. `validate` locks the selected alpha before `test`; changed protocol or input fingerprints refuse to overwrite the original selection. Repeating a frozen run checks reproducibility and does not create a fresh independent holdout.

## Frozen design and accounting

- Asset: SPY, USD; daily exchange sessions, January 2010–December 2025.
- Development: 2010–2018; validation holding intervals: 2019–2021; test: 2022–2025.
- Features: adjusted returns over 1/5/20 sessions, MA20 gap, and 20-session return SD.
- Training: latest 1,260 mature labels, minimum 1,000; training-only scaling; Ridge SVD solver; monthly refits.
- Rule: forecast > 0 means SPY weight 1; otherwise cash weight 0. No leverage or shorting.
- Timing: after-close signal, next-open entry, following-open exit/rebalance.
- Costs: 5 bps main; 0/10 bps sensitivity using the same positions.
- Benchmarks: SPY buy-and-hold and a fixed MA20 rule, with common dates and costs.

```text
target[t] = (raw_open[t+2] + dividend_ex_date[t+2]) / raw_open[t+1] - 1
turnover[i] = abs(weight[i] - weight[i-1]), previous weight initially 0
growth[i] = (1 - cost * turnover[i]) * (1 + weight[i] * target[i])
growth[last] *= (1 - cost * weight[last])  # terminal liquidation
```

Entry on an ex-date earns no same-day dividend; a position carried into the exit ex-date does. The stated convention credits an ex-date receivable, abstracting from payment-date cash. No splits occur in the supported sample; unsupported splits cause explicit failure. At fit date t, training labels must satisfy `exit_date <= t`.

Fees are pre-trade-equity haircuts, not a detailed broker execution model. Annualization uses 252 intervals; drawdown includes initial capital. Annual results use continuous portfolio accounting. The constant-exposure calculation in `output/exposure_diagnostic.json` is explicitly ex post and gross, rather than an investable comparator.

## Validation and artifact map

Eleven tests cover execution/label timing, dividend entitlement, future-data perturbation, adjustment invariance, mature outcomes, past-only scaling, monthly refits, fee timing, cash positions, reporting boundaries, invalid data, and drawdown. Synthetic fixtures are used only for tests. GitHub Actions runs these checks and compiles the current Group 33 report from its included assets, without downloading market data.

| Path | Role |
|---|---|
| `paper/main.tex`, `metadata.tex`, `sections/` | Authoritative manuscript and team information |
| `paper/generated/`, `paper/figures/` | Supplied tables, numeric macros, and vector figures |
| `paper/source_manifest.json` | Original source-file identities |
| `project2/data.py`, `core.py`, `pipeline.py` | Historical data, forecasting, selection, and accounting |
| `project2/report.py` | Verified compilation of the supplied manuscript |
| `project2/package.py` | Code and standalone Overleaf ZIP packaging |
| `output/tables/` | Validation, forecasts, fit audits, returns, and costs |
| `output/report_build.json` | Current report compilation record |

This repository contains a historical backtest. Data provenance and the research assumptions are documented above and in the report.
