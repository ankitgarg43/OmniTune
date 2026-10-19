"""Debloat engine: applies/reverts registry tweaks, removes AppX packages.

Windows-only primitives (winreg) are guarded so this module still imports on
other platforms; functions that need winreg raise RuntimeError there. The
pure helpers (catalog lookups, backup serialization, PowerShell command
building) work everywhere and are unit-tested on Linux CI.
"""
import json
import os
import subprocess
import sys

try:
    import winreg
except ImportError:  # non-Windows (CI)
    winreg = None

_HIVES = {}
if winreg is not None:
    _HIVES = {
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
        "HKCU": winreg.HKEY_CURRENT_USER,
    }

_TYPEMAP = {}
if winreg is not None:
    _TYPEMAP = {
        "dword": winreg.REG_DWORD,
        "sz": winreg.REG_SZ,
    }

_PS = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"]


# -- registry ------------------------------------------------------------
def _need_winreg():
    if winreg is None:
        raise RuntimeError("Registry access requires Windows.")


def read_value(hive, path, name):
    """Return (found, value, type_name) for a registry value."""
    _need_winreg()
    try:
        with winreg.OpenKey(_HIVES[hive], path, 0, winreg.KEY_READ) as key:
            value, regtype = winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return False, None, None
    type_name = "dword" if regtype == winreg.REG_DWORD else (
        "sz" if regtype == winreg.REG_SZ else f"other:{regtype}")
    return True, value, type_name


def write_value(hive, path, name, type_name, value):
    """Write a registry value, creating intermediate keys as needed."""
    _need_winreg()
    with winreg.CreateKeyEx(_HIVES[hive], path, 0,
                            winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, name, 0, _TYPEMAP[type_name], value)


def delete_value(hive, path, name):
    """Delete a registry value; missing values/keys are not an error."""
    _need_winreg()
    try:
        with winreg.OpenKey(_HIVES[hive], path, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass


# -- backup --------------------------------------------------------------
def backup_file():
    """Path of the JSON file holding pre-tweak registry snapshots."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "OmniTune", "debloat-backup.json")


def load_backup():
    try:
        with open(backup_file(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_backup(data):
    path = backup_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def snapshot_op(op):
    """Capture the current state of one registry op for later revert."""
    found, value, type_name = read_value(op["hive"], op["path"], op["name"])
    return {
        "hive": op["hive"],
        "path": op["path"],
        "name": op["name"],
        "existed": found,
        "value": value,
        "type": type_name,
    }


def apply_tweak(tweak, backup):
    """Apply a tweak's registry ops, snapshotting originals into *backup*."""
    _need_winreg()
    key = tweak["key"]
    if key not in backup:
        backup[key] = [snapshot_op(op) for op in tweak["ops"]]
    for op in tweak["ops"]:
        write_value(op["hive"], op["path"], op["name"], op["type"], op["value"])
    save_backup(backup)


def revert_tweak(tweak, backup):
    """Restore a tweak's snapshotted values (or delete if absent before)."""
    _need_winreg()
    key = tweak["key"]
    for snap in backup.get(key, []):
        if snap["existed"]:
            write_value(snap["hive"], snap["path"], snap["name"],
                        snap["type"], snap["value"])
        else:
            delete_value(snap["hive"], snap["path"], snap["name"])
    backup.pop(key, None)
    save_backup(backup)


def tweak_state(tweak):
    """Return 'applied', 'not-applied', 'mixed' or 'unknown' (no winreg)."""
    if winreg is None:
        return "unknown"
    matched = 0
    for op in tweak["ops"]:
        found, value, _type = read_value(op["hive"], op["path"], op["name"])
        if found and value == op["value"]:
            matched += 1
    if matched == len(tweak["ops"]):
        return "applied"
    if matched == 0:
        return "not-applied"
    return "mixed"


# -- AppX packages ---------------------------------------------------------
def build_appx_remove_ps(packages):
    """Build the PowerShell removing *packages* (prefix match, all users)."""
    blocks = []
    for pkg in packages:
        safe = pkg.replace("'", "''")
        blocks.append(
            f"Get-AppxPackage -Name '{safe}*' -AllUsers -ErrorAction SilentlyContinue"
            f" | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue"
        )
    return "; ".join(blocks)


def build_appx_query_ps(patterns):
    """Build PowerShell listing installed package names matching *patterns*."""
    blocks = []
    for pat in patterns:
        safe = pat.replace("'", "''")
        blocks.append(
            f"(Get-AppxPackage -Name '{safe}*' -ErrorAction SilentlyContinue"
            f" | Select-Object -ExpandProperty Name)"
        )
    return "; ".join(blocks)


def _run_ps(command, timeout=300):
    if sys.platform != "win32":
        raise RuntimeError("PowerShell execution requires Windows.")
    proc = subprocess.run(_PS + [command], capture_output=True,
                          timeout=timeout, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def remove_appx_packages(packages, timeout=600):
    """Remove AppX packages; returns {pkg: (ok, message)}."""
    results = {}
    for pkg in packages:
        try:
            code, _out, err = _run_ps(build_appx_remove_ps([pkg]),
                                      timeout=timeout)
            # Remove-AppxPackage is quiet on success; verify by re-querying.
            still = get_installed_appx([pkg])
            if not still:
                results[pkg] = (True, "removed")
            else:
                results[pkg] = (False, err or "package still present")
        except Exception as exc:  # noqa: BLE001 - surfaced per package
            results[pkg] = (False, str(exc))
    return results


def get_installed_appx(patterns, timeout=120):
    """Return the set of installed package names matching *patterns*."""
    code, out, _err = _run_ps(build_appx_query_ps(patterns), timeout=timeout)
    if code != 0:
        return set()
    return {line.strip() for line in out.splitlines() if line.strip()}


# -- restore point -----------------------------------------------------------
def build_restore_point_ps(description="OmniTune debloat"):
    safe = description.replace("'", "''")
    return (f"Checkpoint-Computer -Description '{safe}' "
            f"-RestorePointType 'MODIFY_SETTINGS'")


def create_restore_point(description="OmniTune debloat", timeout=600):
    """Create a system restore point. Returns (ok, message)."""
    try:
        code, _out, err = _run_ps(build_restore_point_ps(description),
                                  timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        return False, str(exc)
    if code == 0:
        return True, "Restore point created."
    return False, (err or f"Checkpoint-Computer exited with code {code}.")


# -- custom bloatware list -----------------------------------------------
def custom_apps_file():
    """Path of the JSON file holding user-added package fragments."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "OmniTune", "debloat-custom-apps.json")


def load_custom_apps():
    try:
        with open(custom_apps_file(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return [str(p) for p in data] if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_custom_apps(packages):
    path = custom_apps_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sorted(set(packages)), fh, indent=2)


# -- tweak profiles ---------------------------------------------------------
def export_profile(keys, dest_path):
    """Write selected tweak keys as a JSON profile. Returns keys written."""
    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump({"tweaks": sorted(set(keys))}, fh, indent=2)
    return len(keys)


def import_profile(src_path):
    """Read a tweak profile file. Returns [keys]."""
    with open(src_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        keys = data.get("tweaks", [])
    elif isinstance(data, list):
        keys = data
    else:
        keys = []
    return [str(k) for k in keys]


# -- AppX re-register ----------------------------------------------------------
def build_reregister_ps(packages):
    """Build PowerShell re-registering installed AppX packages (pure)."""
    blocks = []
    for pkg in packages:
        safe = pkg.replace("'", "''")
        blocks.append(
            f"$p = Get-AppxPackage -Name '{safe}*' -ErrorAction SilentlyContinue"
            f" | Select-Object -First 1; "
            f"if ($p) {{ Add-AppxPackage -Register "
            f"\"$($p.InstallLocation)\\AppXManifest.xml\" "
            f"-DisableDevelopmentMode -ErrorAction Stop; "
            f"\"OK:{safe}\" }} else {{ \"MISSING:{safe}\" }}"
        )
    return "; ".join(blocks)


def reregister_appx(packages, timeout=300):
    """Re-register installed AppX packages. Returns {pkg: (ok, message)}."""
    results = {}
    for pkg in packages:
        try:
            code, out, err = _run_ps(build_reregister_ps([pkg]),
                                     timeout=timeout)
            if f"OK:{pkg}" in out:
                results[pkg] = (True, "re-registered")
            elif f"MISSING:{pkg}" in out:
                results[pkg] = (False, "not installed")
            else:
                results[pkg] = (False, err or out or "unknown error")
        except Exception as exc:  # noqa: BLE001 - surfaced per package
            results[pkg] = (False, str(exc))
    return results
