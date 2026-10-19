# Changelog

## v0.5.0 — 2026-10-19

- **Design pass**: custom OmniTune app icon (tuning fork + gear, electric
  blue) wired into the EXE metadata and window title bar; dark theme extended
  (tree widgets, group boxes, radios/checkboxes, heading + dim label styles).
- Disk: **duplicate file detection** (size → first-MB hash → full SHA-256, in
  a background worker with progress) and **CSV/JSON scan export**.
- Debloat: custom bloatware entries now **persist between sessions**;
  **export/import tweak profiles** (JSON); **re-register AppX** packages.
- Updates: **automatic-update policy presets** (notify / download / auto /
  off via the WindowsUpdate\AU registry policy), **offline .msu install**
  (wusa.exe), and a determinate install **progress bar**.
- Drivers: **install drivers from a folder** (pnputil /add-driver /subdirs
  /install) and **export installed drivers** (pnputil /export-driver).
- TuneUp: **in-app HTML report viewer** (QTextBrowser) alongside opening the
  report externally.
- Robustness: every tab panel now implements `shutdown()`; MainWindow
  `closeEvent` stops background workers gracefully (no more
  "QThread destroyed while running" warnings).
- Tests: 53 pass, 2 skipped (Windows-only registry tests).

## v0.4.0 — 2026-10-19

- Updates module is functional (wumgr-style): check for updates via the
  Windows Update Agent API, download & install selected updates, hide/unhide
  updates, and browse install history — all in background threads with COM
  apartment handling. Reboot-required results are surfaced to the user.
- Drivers module is functional (phase 1): PnP hardware scan with
  problem-device highlighting (error/unknown status rows flagged with the
  CM_PROB meaning), on-demand driver details (version/date/provider), and
  driver updates discovered + installed through Windows Update.
- Engines: `updates_engine.py` (WUA COM via pywin32) and `drivers_engine.py`
  (Get-PnpDevice scan + WUA driver search). Pure helpers unit-tested in
  `tests/test_updates_drivers.py`. Clean-room reimplementations — no wumgr
  or SDI code used.
- Roadmap left in-app: per-update progress bars, .msu offline install,
  pnputil INF install, SDI-style offline driverpacks.

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
