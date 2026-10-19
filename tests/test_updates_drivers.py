"""Tests for the Updates and Drivers engines (pure helpers only).

COM (WUA) and PowerShell execution are Windows-only; only the pure,
platform-independent helpers are exercised here.
"""
import sys

import pytest

from omniture.modules import drivers_engine as drv
from omniture.modules import updates_engine as upd


# -- updates_engine pure helpers ----------------------------------------------
def test_build_search_criteria_default():
    assert upd.build_search_criteria() == "IsInstalled=0 and IsHidden=0"


def test_build_search_criteria_drivers():
    assert upd.build_search_criteria(drivers_only=True) == \
        "IsInstalled=0 and IsHidden=0 and Type='Driver'"


def test_build_search_criteria_include_hidden():
    assert upd.build_search_criteria(include_hidden=True) == "IsInstalled=0"


def test_kb_string_empty():
    assert upd.kb_string(None) == ""


def test_kb_string_formats():
    class FakeColl:
        Count = 2

        def Item(self, i):
            return ["1234567", "7654321"][i]

    assert upd.kb_string(FakeColl()) == "KB1234567, KB7654321"


def test_category_names_empty():
    assert upd.category_names(None) == []


def test_category_names_formats():
    class FakeCat:
        def __init__(self, name):
            self.Name = name

    class FakeColl:
        Count = 2

        def Item(self, i):
            return [FakeCat("Drivers"), FakeCat("Software")][i]

    assert upd.category_names(FakeColl()) == ["Drivers", "Software"]


def test_update_to_dict_no_com():
    assert upd.update_to_dict(None)["title"] == ""
    assert upd.update_to_dict(None)["update_id"] == ""


def test_result_name_known_and_unknown():
    assert upd.result_name(2) == "Succeeded"
    assert upd.result_name(4) == "Failed"
    assert "999" in upd.result_name(999)


def test_com_available_false_off_windows():
    if sys.platform == "win32":
        pytest.skip("Windows-only positive check")
    assert upd.com_available() is False


def test_check_updates_requires_windows():
    if sys.platform == "win32":
        pytest.skip("Windows-only negative test")
    with pytest.raises(RuntimeError):
        upd.check_updates()


# -- drivers_engine pure helpers -------------------------------------------------
def test_parse_devices_empty():
    assert drv.parse_devices("") == []
    assert drv.parse_devices("  ") == []


def test_parse_devices_single_object():
    js = ('{"FriendlyName":"NVIDIA GeForce GTX 1660","InstanceId":'
          '"PCI\\\\VEN_10DE&DEV_2184","Class":"Display","Status":"OK",'
          '"Problem":0,"Present":true}')
    devs = drv.parse_devices(js)
    assert len(devs) == 1
    assert devs[0]["name"] == "NVIDIA GeForce GTX 1660"
    assert devs[0]["class"] == "Display"
    assert devs[0]["problem"] == 0


def test_parse_devices_list_and_missing_name():
    js = ('[{"FriendlyName":null,"InstanceId":"X","Class":"Net",'
          '"Status":"Error","Problem":28,"Present":true}]')
    devs = drv.parse_devices(js)
    assert devs[0]["name"] == "(unknown device)"
    assert devs[0]["status"] == "Error"


def test_problem_devices_filters_ok():
    devs = [
        {"name": "a", "status": "OK"},
        {"name": "b", "status": "Error"},
        {"name": "c", "status": "Unknown"},
        {"name": "d", "status": "ok"},  # case-insensitive
    ]
    bad = drv.problem_devices(devs)
    assert [d["name"] for d in bad] == ["b", "c"]


def test_problem_name_known_and_unknown():
    assert drv.problem_name(28) == "Drivers not installed"
    assert drv.problem_name(22) == "Disabled"
    assert drv.problem_name(None) == ""
    assert "1234" in drv.problem_name(1234)


def test_build_device_detail_ps_escapes_quotes():
    cmd = drv.build_device_detail_ps("PCI\\VEN_10DE&DEV_21'O")
    assert "21''O" in cmd
    assert "DEVPKEY_Device_DriverVersion" in cmd
    assert "ConvertTo-Json" in cmd


def test_scan_devices_requires_windows():
    if sys.platform == "win32":
        pytest.skip("Windows-only negative test")
    with pytest.raises(RuntimeError):
        drv.scan_devices()
