"""Updates engine: Windows Update management via the Windows Update Agent API.

Feature set modeled on wumgr / WuMgr (GPL-3.0, DavidXanatos):
https://github.com/DavidXanatos/wumgr
Clean-room reimplementation - no wumgr code is used. This module talks to
the same underlying OS API (Microsoft.Update.Session COM) that wumgr uses.

COM access (pywin32) is Windows-only and guarded; pure helpers (search
criteria, KB extraction, result formatting) work everywhere and are tested.
"""
import sys

try:
    import pythoncom
    import win32com.client
    _HAVE_COM = True
except ImportError:  # non-Windows (CI)
    _HAVE_COM = False

# WUA search criteria. IsHidden=0 keeps hidden updates out of the main list
# (they can still be managed explicitly).
CRITERIA_ALL = "IsInstalled=0 and IsHidden=0"
CRITERIA_DRIVERS = "IsInstalled=0 and IsHidden=0 and Type='Driver'"

# IUpdateHistoryEntry / install ResultCode values.
_RESULT_NAMES = {
    0: "Not started",
    1: "In progress",
    2: "Succeeded",
    3: "Succeeded with errors",
    4: "Failed",
    5: "Aborted",
}

# IUpdateHistoryEntry Operation values.
_OPERATION_NAMES = {
    1: "Installation",
    2: "Uninstallation",
    3: "Other",
}


def _need_com():
    if not _HAVE_COM:
        raise RuntimeError("Windows Update API requires Windows + pywin32.")


def _session():
    _need_com()
    return win32com.client.Dispatch("Microsoft.Update.Session")


def build_search_criteria(drivers_only=False, include_hidden=False):
    """Build the WUA search criteria string (pure, unit-tested)."""
    parts = ["IsInstalled=0"]
    if not include_hidden:
        parts.append("IsHidden=0")
    if drivers_only:
        parts.append("Type='Driver'")
    return " and ".join(parts)


def kb_string(kb_ids):
    """Format a KBArticleIDs collection as 'KB123, KB456' (pure helper)."""
    try:
        ids = [str(kb_ids.Item(i)) for i in range(kb_ids.Count)]
    except Exception:  # noqa: BLE001 - best effort on odd collections
        return ""
    return ", ".join(f"KB{i}" for i in ids if str(i).strip())


def category_names(categories):
    """Return [names] from an ICategoryCollection (pure helper)."""
    try:
        return [str(categories.Item(i).Name)
                for i in range(categories.Count)]
    except Exception:  # noqa: BLE001
        return []


def update_to_dict(update):
    """Summarize an IUpdate COM object as a plain dict (no COM escapes)."""
    try:
        identity = update.Identity
        update_id = str(identity.UpdateID)
    except Exception:  # noqa: BLE001
        update_id = ""
    return {
        "update_id": update_id,
        "title": str(getattr(update, "Title", "")),
        "description": str(getattr(update, "Description", "")),
        "kb": kb_string(getattr(update, "KBArticleIDs", None)),
        "categories": category_names(getattr(update, "Categories", None)),
        "mandatory": bool(getattr(update, "IsMandatory", False)),
        "hidden": bool(getattr(update, "IsHidden", False)),
        "downloaded": bool(getattr(update, "IsDownloaded", False)),
    }


def _collect_updates(criteria):
    """Run a WUA search; return (updates_coll, [dict, ...])."""
    session = _session()
    searcher = session.CreateUpdateSearcher()
    result = searcher.Search(criteria)
    updates = result.Updates
    infos = [update_to_dict(updates.Item(i)) for i in range(updates.Count)]
    return updates, infos


def check_updates(drivers_only=False, include_hidden=False):
    """Search Windows Update; return [update dicts]."""
    criteria = build_search_criteria(drivers_only, include_hidden)
    _updates, infos = _collect_updates(criteria)
    return infos


def _select_by_ids(updates, wanted_ids):
    """Build an UpdateColl of the updates whose UpdateID is wanted."""
    _need_com()
    coll = win32com.client.Dispatch("Microsoft.Update.UpdateColl")
    wanted = set(wanted_ids)
    for i in range(updates.Count):
        update = updates.Item(i)
        try:
            uid = str(update.Identity.UpdateID)
        except Exception:  # noqa: BLE001
            continue
        if uid in wanted:
            coll.Add(update)
    return coll


def download_updates(update_ids, log=None, criteria=None):
    """Download the given updates. Returns (ok_count, total)."""
    criteria = criteria or build_search_criteria(include_hidden=True)
    updates, _infos = _collect_updates(criteria)
    coll = _select_by_ids(updates, update_ids)
    if coll.Count == 0:
        return 0, 0
    if log:
        log(f"Downloading {coll.Count} update(s)...")
    downloader = _session().CreateUpdateDownloader()
    downloader.Updates = coll
    result = downloader.Download()
    ok = _RESULT_NAMES.get(result.ResultCode, "?")
    if log:
        log(f"Download finished: {ok} (code {result.ResultCode}).")
    return coll.Count, coll.Count


def install_updates(update_ids, log=None, criteria=None):
    """Install the given updates. Returns (installed, reboot_required)."""
    criteria = criteria or build_search_criteria(include_hidden=True)
    updates, _infos = _collect_updates(criteria)
    coll = _select_by_ids(updates, update_ids)
    if coll.Count == 0:
        return 0, False
    if log:
        log(f"Installing {coll.Count} update(s)...")
    installer = _session().CreateUpdateInstaller()
    installer.Updates = coll
    result = installer.Install()
    name = _RESULT_NAMES.get(result.ResultCode, "?")
    reboot = bool(result.RebootRequired)
    if log:
        log(f"Install finished: {name} (code {result.ResultCode})."
            + (" Reboot required." if reboot else ""))
    return coll.Count, reboot


def set_hidden(update_ids, hide=True, log=None):
    """Hide or unhide updates. Returns count changed."""
    updates, _infos = _collect_updates(
        build_search_criteria(include_hidden=True))
    wanted = set(update_ids)
    changed = 0
    for i in range(updates.Count):
        update = updates.Item(i)
        try:
            uid = str(update.Identity.UpdateID)
        except Exception:  # noqa: BLE001
            continue
        if uid in wanted and bool(update.IsHidden) != hide:
            update.IsHidden = hide
            changed += 1
    if log:
        log(f"{'Hid' if hide else 'Unhid'} {changed} update(s).")
    return changed


def get_history(count=50):
    """Return recent Windows Update history entries as dicts."""
    _need_com()
    searcher = _session().CreateUpdateSearcher()
    entries = searcher.QueryHistory(0, count)
    out = []
    for i in range(entries.Count):
        entry = entries.Item(i)
        try:
            date = entry.Date.Format()
        except Exception:  # noqa: BLE001
            date = ""
        out.append({
            "title": str(getattr(entry, "Title", "")),
            "date": date,
            "operation": _OPERATION_NAMES.get(
                getattr(entry, "Operation", 0), "?"),
            "result": _RESULT_NAMES.get(
                getattr(entry, "ResultCode", 0), "?"),
        })
    return out


def result_name(code):
    """Human name for a WUA result code (pure helper)."""
    return _RESULT_NAMES.get(code, f"Unknown ({code})")


def com_available():
    """True when the WUA COM API can be used on this machine."""
    return _HAVE_COM and sys.platform == "win32"
