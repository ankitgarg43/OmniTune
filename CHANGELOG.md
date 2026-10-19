# Changelog

## v0.2.0 — 2026-10-19

- Disk analyzer is functional: background drive scan with progress, interactive
  squarified treemap (click to drill down, hover for details), largest-files
  table, temp-folder cleanup and Recycle Bin emptying (both with confirmation).
- New TuneUp tab: runs the bundled `PC-TuneUp-v1.ps1` verbatim (7 phases:
  restore point, inventory, cleanup, winget, Windows Update, DISM/SFC,
  HTML report) with live output streaming, a View-Script button for
  transparency, and an Open-Report button afterwards. The script ships inside
  the EXE via PyInstaller `datas`.
- Pure-logic tests for the scanner and treemap layout (`tests/test_disk.py`).

## v0.1.0 — 2026-10-19

- Project scaffold: app shell with Drivers / Updates / Debloat / Disk tabs and in-app module roadmaps.
- GitHub Actions workflow: builds portable `OmniTune.exe` (PyInstaller single file, admin manifest) on every `v*` tag and attaches it to the release.
- GPL-3.0 license.
