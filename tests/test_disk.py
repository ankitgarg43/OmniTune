"""Pure-logic tests for the disk analyzer (no Qt, no Windows APIs)."""
import os

import pytest

from omniture.modules.disk_scanner import format_size, largest_files, scan_path
from omniture.modules.disk_treemap import squarify


def test_format_size():
    assert format_size(0) == "0 B"
    assert format_size(512) == "512 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1536) == "1.5 KB"
    assert format_size(1024 * 1024) == "1.0 MB"
    assert format_size(int(2.5 * 1024 ** 3)) == "2.5 GB"


def _make_tree(tmp_path):
    # tmp/
    #   dir_a/  file1.bin (1000 B), file2.bin (2000 B)
    #   dir_b/  sub/  file3.bin (4000 B)
    #   top.bin (500 B)
    dir_a = tmp_path / "dir_a"
    dir_a.mkdir()
    (dir_a / "file1.bin").write_bytes(b"x" * 1000)
    (dir_a / "file2.bin").write_bytes(b"x" * 2000)
    sub = tmp_path / "dir_b" / "sub"
    sub.mkdir(parents=True)
    (sub / "file3.bin").write_bytes(b"x" * 4000)
    (tmp_path / "top.bin").write_bytes(b"x" * 500)
    return tmp_path


def test_scan_aggregates_sizes(tmp_path):
    root = _make_tree(tmp_path)
    tree = scan_path(str(root))
    assert "error" not in tree
    assert tree["size"] == 7500
    assert tree["files"] == 4
    assert tree["dirs"] == 3  # dir_a, dir_b, sub
    by_name = {c["name"]: c for c in tree["children"]}
    assert by_name["dir_a"]["size"] == 3000
    assert by_name["dir_b"]["size"] == 4000
    assert by_name["top.bin"]["size"] == 500


def test_scan_missing_dir_reports_error(tmp_path):
    tree = scan_path(str(tmp_path / "nope"))
    assert tree["error"]
    assert tree["size"] == 0


def test_largest_files_order(tmp_path):
    root = _make_tree(tmp_path)
    tree = scan_path(str(root))
    top3 = largest_files(tree, 3)
    assert [size for size, _ in top3] == [4000, 2000, 1000]
    assert top3[0][1]["name"] == "file3.bin"


def test_squarify_tiles_area():
    items = [("a", 4), ("b", 3), ("c", 2), ("d", 1)]
    rects = squarify(items, 0, 0, 100, 100)
    assert len(rects) == 4
    total = sum(w * h for _, _, _, w, h in rects)
    assert total == pytest.approx(100 * 100, rel=0.01)
    for _, x, y, w, h in rects:
        assert 0 <= x <= 100 and 0 <= y <= 100
        assert x + w <= 100.5 and y + h <= 100.5
        assert w > 0 and h > 0


def test_squarify_no_overlap():
    items = [("a", 9), ("b", 7), ("c", 5), ("d", 4), ("e", 2), ("f", 1)]
    rects = squarify(items, 0, 0, 200, 100)
    boxes = [(x, y, x + w, y + h) for _, x, y, w, h in rects]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            ax1, ay1, ax2, ay2 = boxes[i]
            bx1, by1, bx2, by2 = boxes[j]
            overlap = max(0, min(ax2, bx2) - max(ax1, bx1)) * max(
                0, min(ay2, by2) - max(ay1, by1))
            assert overlap < 1e-6


def test_squarify_empty_and_zero():
    assert squarify([], 0, 0, 100, 100) == []
    assert squarify([("a", 0)], 0, 0, 100, 100) == []
    assert squarify([("a", 5)], 0, 0, 0, 100) == []


def test_squarify_single_item_fills():
    rects = squarify([("only", 42)], 10, 20, 30, 40)
    assert rects == [("only", 10, 20, 30, 40)]


# -- v0.5.0 additions: duplicates + export -------------------------------------------
def _make_dup_tree(tmp_path):
    from omniture.modules import disk_scanner as ds
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "one.bin").write_bytes(b"x" * 3000)
    (tmp_path / "b" / "two.bin").write_bytes(b"x" * 3000)  # duplicate
    (tmp_path / "b" / "three.bin").write_bytes(b"y" * 3000)  # same size, diff
    (tmp_path / "a" / "tiny.txt").write_bytes(b"hi")
    tree = ds.scan_path(str(tmp_path))
    return ds, tree


def test_find_duplicates(tmp_path):
    ds, tree = _make_dup_tree(tmp_path)
    groups = ds.find_duplicates(tree)
    assert len(groups) == 1
    assert groups[0]["size"] == 3000
    assert len(groups[0]["paths"]) == 2
    assert all(p.endswith(".bin") for p in groups[0]["paths"])


def test_find_duplicates_empty_tree():
    from omniture.modules import disk_scanner as ds
    assert ds.find_duplicates({"children": []}) == []


def test_export_csv_and_json(tmp_path):
    import csv
    import json
    ds, tree = _make_dup_tree(tmp_path)
    csv_path = str(tmp_path / "out.csv")
    json_path = str(tmp_path / "out.json")
    rows = ds.export_csv(tree, csv_path)
    assert rows == 4
    with open(csv_path, newline="") as fh:
        assert next(csv.reader(fh)) == ["path", "size_bytes"]
    size = ds.export_json(tree, json_path)
    assert size > 0
    with open(json_path) as fh:
        data = json.load(fh)
    assert data["files"] == 4


def test_iter_files_counts():
    from omniture.modules import disk_scanner as ds
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "f1"), "w").write("a")
        os.mkdir(os.path.join(d, "sub"))
        open(os.path.join(d, "sub", "f2"), "w").write("b")
        tree = ds.scan_path(d)
        assert len(list(ds.iter_files(tree))) == 2
