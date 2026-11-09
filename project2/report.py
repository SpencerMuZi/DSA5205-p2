"""Generate saved-result LaTeX assets and compile the conference-style research report."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from pypdf import PdfReader

from .core import digest, write_json

TEMPLATE = Path(__file__).resolve().parent.parent / "paper"


def build():
    root = Path.cwd()
    paper = root / "paper"
    if paper.resolve() != TEMPLATE.resolve():
        paper.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATE / "main.tex", paper / "main.tex")
        shutil.copy2(TEMPLATE / "references.bib", paper / "references.bib")
        shutil.copytree(TEMPLATE / "sections", paper / "sections", dirs_exist_ok=True)
    from .paper_assets import build as assets
    assets()
    intermediate = root / "tmp/latex"
    intermediate.mkdir(parents=True, exist_ok=True)
    if shutil.which("tectonic"):
        command = ["tectonic", "--untrusted", "--keep-logs", "--outdir", str(intermediate), "main.tex"]
        result = subprocess.run(command, cwd=paper, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (intermediate / "compiler_stdout.log").write_text(result.stdout)
        print("\n".join(result.stdout.splitlines()[-5:]), flush=True)
        if result.returncode:
            raise RuntimeError("LaTeX compilation failed; inspect tmp/latex/main.log")
        compiler = subprocess.check_output(["tectonic", "--version"], text=True).strip()
    elif shutil.which("latexmk"):
        command = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", f"-outdir={intermediate}", "main.tex"]
        result = subprocess.run(command, cwd=paper, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout, flush=True)
        if result.returncode:
            raise RuntimeError("latexmk compilation failed")
        compiler = "latexmk / pdfLaTeX"
    else:
        raise RuntimeError("Install Tectonic (recommended) or latexmk + a TeX distribution; see paper/README.md")
    log = (intermediate / "main.log").read_text(errors="replace")
    bad = [line for line in log.splitlines()
           if "Overfull \\hbox" in line or "Overfull \\vbox" in line
           or "undefined references" in line or "Citation" in line and "undefined" in line]
    if bad:
        raise RuntimeError("LaTeX QA requires correction:\n" + "\n".join(bad))
    compiled = intermediate / "main.pdf"
    pdf = PdfReader(compiled)
    count = len(pdf.pages)
    if not 15 <= count <= 25:
        raise RuntimeError(f"Report length {count} is outside the assignment's 15-25 pages; adjust content/layout")
    text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    if "??" in text:
        raise RuntimeError("Unresolved cross-reference in PDF")
    out = root / "output/pdf/Group_X_Report.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(compiled, out)
    inputs = json.loads((paper / "generated/sources.json").read_text())
    for path, expected in inputs.items():
        if digest(path) != expected:
            raise RuntimeError(f"Research artifact changed during typesetting: {path}")
    write_json(root / "output/report_build.json", {
        "format": "LaTeX: two-column main paper and one-column technical supplement",
        "compiler": compiler, "pages": count, "source": "paper/main.tex",
        "output": "output/pdf/Group_X_Report.pdf", "pdf_sha256": digest(out),
        "strategy_refitted": False, "research_artifact_digests_verified": True,
        "overfull_boxes": 0, "undefined_references": 0,
        "source_digests": {str(p.relative_to(root)):digest(p) for p in sorted(paper.rglob("*.tex"))},
        "bibliography_sha256": digest(paper / "references.bib")})
    print(f"REPORT: {out.relative_to(root)} ({count} pages; LaTeX)", flush=True)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", help="Build from saved results in a separate run directory")
    args = parser.parse_args()
    if args.workspace:
        os.chdir(Path(args.workspace).resolve())
    build()
