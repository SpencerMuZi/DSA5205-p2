"""Build a submission ZIP from reviewed, Git-tracked source and derived artifacts."""
from pathlib import Path
import subprocess
import zipfile


def main():
    names = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    dest = Path("output/package/DSA5205_Project2_Code.zip")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            if not name:
                continue
            path = Path(name)
            if path.is_symlink() or name.startswith(("data/raw/", ".venv/", ".git/", "runs/", "tmp/")):
                raise RuntimeError(f"Unexpected sensitive/temporary path in Git index: {name}")
            archive.write(path, arcname="DSA5205-p2/" + name)
    print(f"PACKAGE: {dest} ({dest.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
