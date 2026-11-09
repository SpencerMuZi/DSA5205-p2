# Group 33 Overleaf report

This directory contains the authors' supplied `DSA5205_Project2_Group33_Overleaf` sources. Its original 31 files are published unchanged, including metadata, bibliography, tables, figures, and line endings. `source_manifest.json` records their SHA-256 identities. This README and the manifest are publication support files.

The current document is **21 pages**, titled *Regularized Market Timing with Transaction Costs: Evidence from Daily SPY Returns*. The members and contribution statements are defined in `metadata.tex`.

## Overleaf

Download `DSA5205_Project2_Group33_Overleaf.zip` from the latest release, upload it as a new Overleaf project, choose `main.tex`, and select **XeLaTeX**. The ZIP has `main.tex` at its root. Tables and vector figures are included, so compiling the report does not download market data or require Python.

## Local compilation

From this directory:

```bash
latexmk -xelatex main.tex
```

Tectonic 0.17.0 is also verified:

```bash
tectonic --untrusted main.tex
```

These commands produce `main.pdf`. The repository wrapper, run from the repository root, verifies the source and frozen research-result identities before typesetting:

```bash
python -m project2.report
```

It writes `output/pdf/Group_33_Report.pdf` and `output/report_build.json`. It does not regenerate manuscript assets, retrain models, change the supplied prose, or reselect a strategy. An intentionally edited manuscript can be compiled directly; to update its recorded source identities in the wrapper, use `python -m project2.report --refresh-source-manifest`. The research-input checks remain active.

## Analysis versus manuscript versions

The appendix pins commit `2e2e265ba9d007c94279225febaa15a054dff7cf` for the original analysis. That is distinct from the current publication commit and is retained intentionally. The manuscript's `generated/sources.json` matches the saved result files in this repository.

`project2/paper_assets.py` belongs to the historical v1.1 manuscript and is not the source generator for this final Overleaf project. It is guarded against overwriting this directory. Earlier report editions remain accessible through previous Git tags and releases.
