"""Pure-logic disk scanner (no Qt): walks a directory tree and aggregates sizes.

Node shape (plain dicts, easy to test and serialize):
    {
        "name": str, "path": str, "size": int (bytes, subtree total),
        "is_dir": bool, "children": [node],
        "files": int (files in subtree), "dirs": int (subdirs in subtree),
        "error": str (optional, when a directory could not be read),
    }
Symlinks are never followed (avoids cycles). Unreadable entries are skipped
and recorded rather than aborting the scan.
"""
import heapq
import itertools
import os


def format_size(num_bytes):
    """Human-readable size, e.g. 1536 -> '1.5 KB'."""
    n = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024 or unit == "PB":
            if unit == "B":
                return "%d B" % n
            return "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f %s" % (n, "PB")


class _ScanCancelled(Exception):
    pass


def scan_path(root, progress_cb=None, cancel_check=None):
    """Scan ``root`` iteratively. Returns the top node.

    progress_cb(files_done, current_dir) is called periodically.
    cancel_check() is polled; if it returns True the scan aborts cleanly.
    """
    root = os.path.abspath(root)
    top = {
        "name": os.path.basename(root) or root,
        "path": root,
        "size": 0,
        "is_dir": True,
        "children": [],
        "files": 0,
        "dirs": 0,
    }
    try:
        first = os.scandir(root)
    except OSError as exc:
        top["error"] = str(exc)
        return top

    stack = [(top, first)]
    done = 0
    try:
        while stack:
            node, it = stack[-1]
            try:
                entry = next(it)
            except StopIteration:
                it.close()
                stack.pop()
                if stack:
                    parent = stack[-1][0]
                    parent["size"] += node["size"]
                    parent["dirs"] += 1 + node["dirs"]
                    parent["files"] += node["files"]
                continue
            except OSError:
                continue
            if cancel_check and cancel_check():
                raise _ScanCancelled()
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    child = {
                        "name": entry.name,
                        "path": entry.path,
                        "size": 0,
                        "is_dir": True,
                        "children": [],
                        "files": 0,
                        "dirs": 0,
                    }
                    node["children"].append(child)
                    try:
                        stack.append((child, os.scandir(entry.path)))
                    except OSError as exc:
                        child["error"] = str(exc)
                elif entry.is_file(follow_symlinks=False):
                    try:
                        size = entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        size = 0
                    node["children"].append(
                        {
                            "name": entry.name,
                            "path": entry.path,
                            "size": size,
                            "is_dir": False,
                        }
                    )
                    node["size"] += size
                    node["files"] += 1
                    done += 1
                    if progress_cb and done % 500 == 0:
                        progress_cb(done, node["path"])
            except OSError:
                continue
    except _ScanCancelled:
        top["cancelled"] = True
    finally:
        for _, it in stack:
            try:
                it.close()
            except OSError:
                pass
    if progress_cb:
        progress_cb(done, root)
    return top


def largest_files(node, n=100):
    """Return the n largest files in the tree as [(size, node), ...] desc."""
    counter = itertools.count()
    best = []  # heap of (size, counter, node)
    stack = [node]
    while stack:
        current = stack.pop()
        for child in current.get("children", []):
            if child["is_dir"]:
                stack.append(child)
            else:
                item = (child["size"], next(counter), child)
                if len(best) < n:
                    heapq.heappush(best, item)
                elif child["size"] > best[0][0]:
                    heapq.heapreplace(best, item)
    best.sort(key=lambda t: t[0], reverse=True)
    return [(size, node_) for size, _, node_ in best]
