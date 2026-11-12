# Group 33 Overleaf report

This directory contains the Group 33 manuscript, bibliography, tables, and figures. `source_manifest.json` records the source file hashes.

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

It writes `output/pdf/Group_33_Report.pdf` and `output/report_build.json` from the included assets.

## Analysis versus manuscript versions

The appendix cites commit `2e2e265ba9d007c94279225febaa15a054dff7cf` for the analysis. The manuscript's `generated/sources.json` identifies the saved result files used in the report.
