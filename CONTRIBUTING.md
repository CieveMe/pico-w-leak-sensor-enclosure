# Contributing

Issues and pull requests that improve reproducibility, geometry checks, accessibility, or documentation are welcome.

Before changing dimensions, cite the public source or mark the value as a design assumption in `cad/parameters.json` and `docs/sources-and-assumptions.md`. Keep generated STEP/STL/GLB, manifest, validation report, and SVG dimensions tied to one source revision by running `python scripts/prepare_viewer.py`.

Run the same checks as CI from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/prepare_viewer.py
Set-Location viewer
npm ci
npm test
npm run build
```

A failed or unverified check must remain visible. Do not weaken tolerances or remove negative controls to obtain a passing report. Clearly separate digital checks from CAD-application reopening and physical fit, print, strength, RF, alarm, or waterproof tests.
