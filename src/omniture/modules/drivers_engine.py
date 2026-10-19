"""Drivers engine: hardware scan plus driver updates via Windows Update.

Feature set modeled on Snappy Driver Installer / SDI (GPL-3.0, gtumanyan):
https://github.com/gtumanyan/SDI
Clean-room reimplementation - no SDI code is used.

v0.4.0 scope (phased, per project plan):
  * Hardware inventory via Get-PnpDevice (friendly name, class, status,
    problem code) with on-demand driver details (version/date/provider).
  * Driver updates discovered and installed through the Windows Update
    Agent API (shared with the Updates module).
Roadmap: SDI-style offline driverpacks / torrent index support.
"""
import json
import subprocess
import sys

from . import updates_engine

_PS = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"]

_SCAN_PS = (
    "Get-PnpDevice | "
    "Select-Object FriendlyName, InstanceId, Class, Status, Problem, Present | "
    "ConvertTo-Json -Depth 2 -Compress"
)

_DETAIL_KEYS = {
    "driver_version": "DEVPKEY_Device_DriverVersion",
    "driver_date": "DEVPKEY_Device_DriverDate",
    "driver_provider": "DEVPKEY_Device_DriverProvider",
    "driver_desc": "DEVPKEY_Device_DriverDesc",
    "manufacturer": "DEVPKEY_Device_Manufacturer",
}


def _run_ps(command, timeout=180):
    if sys.platform != "win32":
        raise RuntimeError("Hardware scan requires Windows.")
    proc = subprocess.run(_PS + [command], capture_output=True,
                          timeout=timeout, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or
                           f"PowerShell exited with code {proc.returncode}.")
    return proc.stdout


def parse_devices(json_text):
    """Parse Get-PnpDevice JSON into a list of device dicts (pure)."""
    text = (json_text or "").strip()
    if not text:
        return []
    data = json.loads(text)
    if isinstance(data, dict):
        data = [data]
    devices = []
    for item in data:
        devices.append({
            "name": item.get("FriendlyName") or "(unknown device)",
            "instance_id": item.get("InstanceId") or "",
            "class": item.get("Class") or "",
            "status": item.get("Status") or "",
            "problem": item.get("Problem"),
            "present": bool(item.get("Present", True)),
        })
    return devices


def problem_devices(devices):
    """Return devices whose status indicates a driver problem (pure)."""
    out = []
    for dev in devices:
        status = (dev.get("status") or "").upper()
        if status != "OK":
            out.append(dev)
    return out


def problem_name(code):
    """Short meaning of a CM_PROB_* problem code (pure helper)."""
    names = {
        1: "Not configured correctly",
        10: "Cannot start",
        12: "Not enough resources",
        18: "Reinstall drivers",
        22: "Disabled",
        24: "Not present / unplugged",
        28: "Drivers not installed",
        31: "Device not working properly",
        39: "Driver missing or corrupted",
        45: "Not connected",
    }
    if code is None:
        return ""
    return names.get(int(code), f"Problem code {code}")


def scan_devices():
    """Enumerate PnP devices on this machine."""
    return parse_devices(_run_ps(_SCAN_PS, timeout=180))


def build_device_detail_ps(instance_id):
    """PowerShell fetching driver details for one device (pure builder)."""
    safe = instance_id.replace("'", "''")
    selects = ", ".join(
        f"@{{n='{label}';e={{(Get-PnpDeviceProperty -InstanceId '{safe}' "
        f"-KeyName '{key}' -ErrorAction SilentlyContinue).Data}}}}"
        for label, key in _DETAIL_KEYS.items()
    )
    return (f"Get-PnpDevice -InstanceId '{safe}' -ErrorAction SilentlyContinue"
            f" | Select-Object {selects} | ConvertTo-Json -Compress")


def device_details(instance_id):
    """Return driver version/date/provider for one device."""
    out = _run_ps(build_device_detail_ps(instance_id), timeout=60)
    try:
        data = json.loads(out.strip() or "{}")
    except ValueError:
        data = {}
    if isinstance(data, list):
        data = data[0] if data else {}
    details = {}
    for label in _DETAIL_KEYS:
        value = data.get(label) or ""
        if label == "driver_date" and isinstance(value, dict):
            # PowerShell serializes DateTime as {value, DateTime}.
            value = value.get("DateTime") or value.get("value") or ""
        details[label] = value
    return details


def check_driver_updates():
    """Find driver updates via Windows Update (WUA, drivers only)."""
    return updates_engine.check_updates(drivers_only=True)


def install_driver_updates(update_ids, log=None):
    """Install driver updates found via Windows Update."""
    return updates_engine.install_updates(
        update_ids, log=log,
        criteria=updates_engine.build_search_criteria(drivers_only=True,
                                                      include_hidden=True))


# -- pnputil: local INF install / driver export ----------------------------------
def build_add_driver_command(folder):
    """Build the pnputil command installing all INFs under *folder* (pure)."""
    return ["pnputil.exe", "/add-driver", folder + r"\*.inf",
            "/subdirs", "/install"]


def build_export_driver_command(folder):
    """Build the pnputil command exporting drivers to *folder* (pure)."""
    return ["pnputil.exe", "/export-driver", "*", folder]


def _run_cmd(argv, timeout=1800):
    if sys.platform != "win32":
        raise RuntimeError("pnputil.exe requires Windows.")
    proc = subprocess.run(argv, capture_output=True, timeout=timeout,
                          text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def install_inf_folder(folder, log=None, timeout=1800):
    """Install every driver INF under *folder* via pnputil."""
    code, out, err = _run_cmd(build_add_driver_command(folder),
                              timeout=timeout)
    summary = out or err or f"pnputil exited with code {code}."
    if log:
        for line in summary.splitlines()[-8:]:
            log(line.strip())
    return code == 0, summary


def export_drivers(folder, log=None, timeout=1800):
    """Export installed third-party drivers to *folder* via pnputil."""
    code, out, err = _run_cmd(build_export_driver_command(folder),
                              timeout=timeout)
    summary = out or err or f"pnputil exited with code {code}."
    if log:
        for line in summary.splitlines()[-8:]:
            log(line.strip())
    return code == 0, summary
