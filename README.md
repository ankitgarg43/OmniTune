# OmniTune

**One app to keep Windows healthy.** OmniTune is an open-source, all-in-one Windows maintenance toolkit with four modules:

| Module | What it does | Concept inspired by |
|---|---|---|
| Drivers | Scan hardware, check driver status, install & update drivers (incl. driver-pack support) | [Snappy Driver Installer](https://github.com/gtumanyan/SDI) (GPL-3.0) |
| Updates | Full Windows Update manager: search, install, hide/unhide, uninstall updates | [WuMgr](https://github.com/DavidXanatos/wumgr) (GPL-3.0) |
| Debloat | Remove pre-installed apps, disable telemetry, apply curated Windows tweaks — with undo | [Win11Debloat](https://github.com/Raphire/Win11Debloat) (MIT) |
| Disk | Disk usage analyzer with interactive treemap, large-file finder, duplicate detection, cleanup | [WinDirStat](https://github.com/windirstat/windirstat) (GPL-3.0) |

OmniTune is a clean rebuild: every feature is reimplemented from scratch in Python. We credit and thank the upstream projects above — no upstream code or binaries are shipped inside OmniTune.

## Status

v0.1.0 — project scaffold. The app shell runs with four module tabs; module implementations land one at a time. See [CHANGELOG.md](CHANGELOG.md) and the in-app roadmaps.

Planned build order: Disk → Debloat → Updates → Drivers.

## Requirements

- Windows 10 / 11 (64-bit)
- Python 3.10+ (3.12 recommended)
- Administrator rights (the app requests elevation at launch; every module needs it)

## Development setup (Visual Studio 2022)

1. Install [Visual Studio 2022 Community](https://visualstudio.microsoft.com/vs/community/) with the **Python development** workload.
2. Clone this repo and open the folder in VS (File → Open → Folder).
3. Create a virtual environment and install the project (VS offers this automatically, or manually):
   ```
   py -3.12 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```
4. Run it:
   ```
   python -m omniture
   ```

## Building the portable EXE

```
pip install pyinstaller
pyinstaller omniture.spec --noconfirm --clean
```

This produces a single-file `dist/OmniTune.exe` with an embedded administrator manifest (one UAC prompt at launch, no installer).

## Releases

Push a version tag and GitHub Actions builds the EXE automatically and attaches it to the GitHub release:

```
git tag v0.1.0
git push --tags
```

## Safety

OmniTune changes drivers, Windows Update state, installed apps, and files. Use at your own risk — the Debloat module always offers a restore point / undo path before applying changes.

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE). If you redistribute or modify OmniTune, keep it open source under the same license.
