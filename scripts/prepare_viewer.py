"""Rebuild the current baseline and prepare version-matched viewer assets."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def run(*args):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, check=True)

if __name__ == "__main__":
    print("Building baseline CAD exports and digital validation...")
    run("cad/build.py", "--output", "artifacts/baseline")
    print("Copying manifest-selected files into viewer public assets...")
    run("scripts/sync_viewer_artifacts.py")
    print("Generating dimensions from parameters and the baseline manifest...")
    run("scripts/generate_dimensions.py", "--copy-to-viewer")
