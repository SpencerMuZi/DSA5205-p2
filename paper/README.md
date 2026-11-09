# LaTeX research report

The main paper uses a custom two-column, Times-style conference layout with numbered equations, algorithms, booktabs tables, author-year citations, and vector figures. The detailed technical supplement is single-column. This is a course research report, not an assertion of acceptance at or affiliation with a conference.

## Build

Install [Tectonic](https://tectonic-typesetting.github.io/) or a standard TeX installation with `latexmk`. On macOS, `brew install tectonic` is one option. Tectonic downloads required TeX resources on first use, so that compile needs network access.

From the repository root, after installing the Python requirements:

```bash
python -m project2.report
```

This regenerates `paper/generated/` from saved result tables, compiles `paper/main.tex`, checks for overflow and undefined references, enforces 15-25 pages, and writes `output/pdf/Group_X_Report.pdf`. It does not fit or select a trading model.

To compile already-generated sources directly:

```bash
cd paper
tectonic main.tex
```

The result is `paper/main.pdf`. A standard TeX installation can instead use `latexmk -pdf main.tex`.

For a separate research workspace:

```bash
python -m project2.report --workspace runs/reproduction
```

The script copies the maintained TeX templates into that workspace and uses its saved results. Templates are in `sections/`, references in `references.bib`, and tables/numeric macros in `generated/*.tex`. Do not hand-edit generated numbers. Team information remains intentionally unfilled pending the user's details.
