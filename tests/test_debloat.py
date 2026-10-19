"""Tests for the Debloat module: catalog integrity, backup logic, PS builders.

Registry-touching tests are skipped off Windows; everything else runs on
Linux CI.
"""
import json
import os
import sys

import pytest

from omniture.modules import debloat_engine as engine
from omniture.modules.debloat_catalog import (
    BLOATWARE_APPS,
    CATEGORIES,
    TWEAKS,
    get_tweak,
    tweaks_by_category,
)

NEEDS_WINDOWS = pytest.mark.skipif(sys.platform != "win32",
                                   reason="Windows-only")


# -- catalog integrity ------------------------------------------------------
def test_tweak_keys_unique():
    keys = [t["key"] for t in TWEAKS]
    assert len(keys) == len(set(keys)) > 20


def test_tweak_fields_present():
    for tweak in TWEAKS:
        for field in ("key", "category", "name", "desc", "ops"):
            assert field in tweak, f"{tweak.get('key')}: missing {field}"
        assert tweak["category"] in CATEGORIES
        assert tweak["ops"], f"{tweak['key']}: no ops"


def test_tweak_ops_valid():
    for tweak in TWEAKS:
        for op in tweak["ops"]:
            assert op["hive"] in ("HKLM", "HKCU"), tweak["key"]
            assert op["type"] in ("dword", "sz"), tweak["key"]
            assert op["path"] and op["name"], tweak["key"]
            if op["type"] == "dword":
                assert isinstance(op["value"], int), tweak["key"]
            else:
                assert isinstance(op["value"], str), tweak["key"]


def test_categories_all_represented():
    grouped = tweaks_by_category()
    assert [c for c, _ in grouped] == [c for c in CATEGORIES
                                       if any(t["category"] == c
                                              for t in TWEAKS)]
    assert all(tweaks for _, tweaks in grouped)


def test_get_tweak_roundtrip():
    for tweak in TWEAKS:
        assert get_tweak(tweak["key"]) is tweak
    assert get_tweak("no-such-tweak") is None


def test_bloatware_list_sane():
    pkgs = [a["pkg"] for a in BLOATWARE_APPS]
    assert len(pkgs) == len(set(pkgs)) > 20
    for app in BLOATWARE_APPS:
        assert app["pkg"] and app["label"]
        assert isinstance(app["default"], bool)
    # never suggest removing the Store or core shell pieces
    lowered = [p.lower() for p in pkgs]
    assert not any("windowsstore" in p for p in lowered)


# -- backup serialization (pure) ----------------------------------------------
def test_backup_save_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    data = {"telemetry": [{"hive": "HKLM", "path": "p", "name": "n",
                           "existed": True, "value": 1, "type": "dword"}]}
    engine.save_backup(data)
    assert engine.load_backup() == data


def test_load_backup_missing_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert engine.load_backup() == {}


def test_load_backup_corrupt_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = engine.backup_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    assert engine.load_backup() == {}


# -- PowerShell builders (pure) -------------------------------------------------
def test_build_appx_remove_ps():
    cmd = engine.build_appx_remove_ps(
        ["Microsoft.BingNews", "SpotifyAB.SpotifyMusic"])
    assert "Microsoft.BingNews*" in cmd
    assert "SpotifyAB.SpotifyMusic*" in cmd
    assert "Remove-AppxPackage -AllUsers" in cmd
    assert "-NonInteractive" not in cmd  # flags belong to the runner


def test_build_appx_remove_ps_escapes_quotes():
    cmd = engine.build_appx_remove_ps(["O'Brien.App"])
    assert "O''Brien.App" in cmd


def test_build_appx_query_ps():
    cmd = engine.build_appx_query_ps(["Microsoft.BingNews"])
    assert "Get-AppxPackage" in cmd
    assert "Microsoft.BingNews*" in cmd
    assert "Select-Object -ExpandProperty Name" in cmd


def test_build_restore_point_ps():
    cmd = engine.build_restore_point_ps()
    assert "Checkpoint-Computer" in cmd
    assert "MODIFY_SETTINGS" in cmd


def test_run_ps_requires_windows():
    if sys.platform == "win32":
        pytest.skip("Windows-only negative test")
    with pytest.raises(RuntimeError):
        engine._run_ps("Get-Date")


# -- registry engine (Windows only) ----------------------------------------------
@NEEDS_WINDOWS
def test_registry_write_read_delete_cycle():
    path = r"SOFTWARE\OmniTuneTest"
    try:
        assert engine.read_value("HKCU", path, "CycleVal")[0] is False
        engine.write_value("HKCU", path, "CycleVal", "dword", 42)
        found, value, type_name = engine.read_value("HKCU", path, "CycleVal")
        assert (found, value, type_name) == (True, 42, "dword")
        engine.delete_value("HKCU", path, "CycleVal")
        assert engine.read_value("HKCU", path, "CycleVal")[0] is False
    finally:
        import winreg
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except OSError:
            pass


@NEEDS_WINDOWS
def test_apply_revert_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    tweak = {
        "key": "__test_tweak__",
        "category": "Test",
        "name": "Test",
        "desc": "Test",
        "ops": [{"hive": "HKCU",
                 "path": r"SOFTWARE\OmniTuneTest",
                 "name": "TweakVal",
                 "type": "dword", "value": 7}],
    }
    backup = engine.load_backup()
    engine.apply_tweak(tweak, backup)
    assert engine.tweak_state(tweak) == "applied"
    engine.revert_tweak(tweak, backup)
    # value did not exist before -> deleted on revert
    assert engine.read_value("HKCU", r"SOFTWARE\OmniTuneTest",
                             "TweakVal")[0] is False
    assert "__test_tweak__" not in engine.load_backup()


# -- v0.5.0 additions ------------------------------------------------------------
def test_custom_apps_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert engine.load_custom_apps() == []
    engine.save_custom_apps(["Foo.Bar", "Baz.Qux", "Foo.Bar"])
    assert engine.load_custom_apps() == ["Baz.Qux", "Foo.Bar"]


def test_profile_export_import_roundtrip(tmp_path):
    dest = str(tmp_path / "profile.json")
    keys = ["telemetry", "copilot", "telemetry"]
    assert engine.export_profile(keys, dest) == 3
    assert engine.import_profile(dest) == ["copilot", "telemetry"]


def test_import_profile_list_shape(tmp_path):
    dest = str(tmp_path / "p.json")
    with open(dest, "w") as fh:
        fh.write('["a", "b"]')
    assert engine.import_profile(dest) == ["a", "b"]


def test_build_reregister_ps():
    cmd = engine.build_reregister_ps(["Microsoft.BingNews"])
    assert "Get-AppxPackage -Name 'Microsoft.BingNews*'" in cmd
    assert "Add-AppxPackage -Register" in cmd
    assert "AppXManifest.xml" in cmd
    assert "OK:Microsoft.BingNews" in cmd
