# Changelog

## v0.3.0 — 2026-10-19

- Debloat module is functional with Win11Debloat-style coverage: 26 registry
  tweaks in 6 categories (Privacy & Telemetry, AI Features, Start/Search/
  Taskbar, File Explorer, Gaming, Lock Screen) with live applied/not-applied
  state, one-click apply/revert, and pre-change snapshots stored in
  `%LOCALAPPDATA%\OmniTune\debloat-backup.json`.
- Pre-installed AppX removal: curated list of 28 packages (safe ones
  pre-checked, risky ones opt-in), filter box, custom package entries,
  per-package result reporting. Runs in a background thread; removes for all
  users.
- Safety: one-click system restore point, plus an automatic restore point
  before applying tweaks or removing apps (skipped if one was already made
  this session). Every destructive action has a confirmation dialog.
- Catalog/engine/tests: `debloat_catalog.py` (data), `debloat_engine.py`
  (registry/AppX/restore-point logic), `tests/test_debloat.py` (catalog
  integrity, backup round-trip, PowerShell builders; registry tests run on
  Windows CI only). Clean-room reimplementation — no Win11Debloat code used.

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
