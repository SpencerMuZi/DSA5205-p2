"""Capture actual stage commands/output for an honest, reproducible walkthrough."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    output = Path("output/video")
    output.mkdir(parents=True, exist_ok=True)
    commands = [["-m", "pytest", "-q"], ["-m", "project2.pipeline", "fetch"],
                ["-m", "project2.pipeline", "validate"], ["-m", "project2.pipeline", "test"],
                ["-m", "project2.pipeline", "figures"], ["-m", "project2.report"]]
    records = []
    env = dict(os.environ, MPLCONFIGDIR=str(Path('.cache/matplotlib').resolve()),
               XDG_CACHE_HOME=str(Path('.cache').resolve()))
    for command in commands:
        started = time.monotonic()
        result = subprocess.run([sys.executable, *command], text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, env=env)
        record = {"command": "python " + " ".join(command), "returncode": result.returncode,
                  "elapsed_seconds": round(time.monotonic() - started, 3), "stdout": result.stdout}
        records.append(record)
        print(record["command"] + "\n" + result.stdout, flush=True)
        if result.returncode:
            raise RuntimeError("Walkthrough stage failed")
    (output / "demo_steps.json").write_text(json.dumps(records, indent=2) + "\n")
    (output / "demo_run.log").write_text("\n\n".join(r["command"] + "\n" + r["stdout"] for r in records))


if __name__ == "__main__":
    main()
