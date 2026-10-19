"""Pure-logic squarified treemap layout (no Qt).

squarify(items, x, y, w, h) -> [(key, x, y, w, h), ...]
items is a list of (key, value) with value > 0. Rectangles tile the
x/y/w/h region with total area proportional to value, optimized for
squarish aspect ratios (the "squarified" algorithm).
"""


def _worst(row, side):
    total = sum(area for _, area in row)
    biggest = max(area for _, area in row)
    smallest = min(area for _, area in row)
    return max(
        (side * side * biggest) / (total * total),
        (total * total) / (side * side * smallest),
    )


def _squarify(children, x, y, w, h, out):
    # children: [(key, area)] already normalized so sum == w*h
    if not children:
        return
    if len(children) == 1:
        key, _area = children[0]
        out.append((key, x, y, w, h))
        return
    # Grow one row while the worst aspect ratio keeps improving.
    row = [children[0]]
    i = 1
    side = min(w, h)
    while i < len(children):
        if _worst(row + [children[i]], side) <= _worst(row, side):
            row.append(children[i])
            i += 1
        else:
            break
    row_area = sum(area for _, area in row)
    if w >= h:
        row_h = row_area / w
        cx = x
        for key, area in row:
            cw = area / row_h
            out.append((key, cx, y, cw, row_h))
            cx += cw
        _squarify(children[i:], x, y + row_h, w, h - row_h, out)
    else:
        col_w = row_area / h
        cy = y
        for key, area in row:
            ch = area / col_w
            out.append((key, x, cy, col_w, ch))
            cy += ch
        _squarify(children[i:], x + col_w, y, w - col_w, h, out)


def squarify(items, x, y, w, h):
    """Lay out (key, value) pairs as rectangles inside the given region."""
    children = [(key, value) for key, value in items if value > 0]
    if not children or w <= 0 or h <= 0:
        return []
    children.sort(key=lambda kv: kv[1], reverse=True)
    total = sum(value for _, value in children)
    if total <= 0:
        return []
    normalized = [(key, value * w * h / total) for key, value in children]
    out = []
    _squarify(normalized, x, y, w, h, out)
    return out
