"""Systemic guard: no standalone-file generator may ship a `<text>` element
with the engrave-red fill.

Boxes.py's own `rectangularWall(..., label=...)` / `self.text(...)` draw
part-name labels in `Color.ANNOTATIONS`, which renders identically to this
project's engrave color, `rgb(255,0,0)` (see config.ENGRAVE_COLOR). A `<text>`
fill is read by a laser driver exactly like a `<path>` stroke -- an
un-recolored label is a live "burn these words into the part" instruction,
not a harmless viewer-only caption (see LEARNINGS.md).

layout.py already re-colors labels when it re-emits sheet_*.svg
(`_LABEL_FILL_RE`/`LABEL_FILL_GRAY`), and generate_hardware.py was fixed
point-wise by passing `color=LABEL_GRAY` straight into `self.text()`. Every
OTHER standalone-file generator (drawers, lids, shell, calibration coupons)
still ships Boxes.py's raw red label untouched. Rather than trust every
current and future generator to remember its own per-call fix, this module
is the single place that rewrites the finished SVG file on disk, called once
at the tail of every standalone generate_* function.

Only `<text>` elements are touched -- a red STROKE on a `<path>` is a
genuine, intentional engrave (e.g. the faceplate's registration outline) and
must be left completely alone. Everything outside a `<text ...>` opening tag
(all `<path>` elements, the text content/labels themselves, XML declaration,
namespaces, attribute order/quoting) is preserved byte-for-byte: this module
never round-trips the file through an XML parser/serializer (which would
risk silently reordering attributes or reformatting whitespace); it only
regex-substitutes within each matched `<text ...>` opening tag.
"""

from __future__ import annotations

import re
from pathlib import Path

# Matches one <text> opening tag (self-closing or not) -- non-greedy so it
# stops at the first '>', never spanning into the element's own content or a
# neighboring tag.
_TEXT_OPEN_TAG_RE = re.compile(r"<text\b[^>]*?/?>")

# One key="value" attribute pair within an already-isolated opening tag.
_ATTR_RE = re.compile(r'([\w:-]+)="([^"]*)"')

# Boxes.py emits the label color via a `style="...fill: rgb(255,0,0)..."`
# attribute (same shape layout.py's _LABEL_FILL_RE already matches for
# re-emitted sheet labels); matched independent of that module so this file
# has no import dependency on layout.py.
_RED_FILL_IN_STYLE_RE = re.compile(r"fill:\s*rgb\(\s*255\s*,\s*0\s*,\s*0\s*\)")
_GRAY_FILL_STYLE = "fill: rgb(128,128,128)"

# Defensive second path: a future generator could plausibly emit color via a
# bare fill="..." attribute instead of a style string. No current output
# does this, but catching it costs nothing.
_GRAY_FILL_ATTR = "rgb(128,128,128)"


def _rewrite_attrs(tag: str) -> str:
    """Recolor style=/fill= attributes carrying the red engrave fill,
    leaving every other attribute (value, order, quoting) untouched."""

    def _replace(match: re.Match) -> str:
        key, value = match.group(1), match.group(2)
        if key == "style" and _RED_FILL_IN_STYLE_RE.search(value):
            value = _RED_FILL_IN_STYLE_RE.sub(_GRAY_FILL_STYLE, value)
        elif key == "fill" and value.replace(" ", "") == "rgb(255,0,0)":
            value = _GRAY_FILL_ATTR
        return f'{key}="{value}"'

    return _ATTR_RE.sub(_replace, tag)


def _ensure_data_purpose(tag: str) -> str:
    """Append data-purpose="reference-label" to the tag if it doesn't
    already carry one -- appended last, matching layout.py's own
    _emit_piece_group convention for re-emitted sheet labels."""
    if 'data-purpose="' in tag:
        return tag
    if tag.endswith("/>"):
        return f'{tag[:-2].rstrip()} data-purpose="reference-label" />'
    return f'{tag[:-1].rstrip()} data-purpose="reference-label">'


def enforce_reference_labels(svg_path: str | Path) -> bool:
    """Rewrite svg_path in place: every `<text>` element's red (255,0,0)
    fill becomes gray (128,128,128), and every `<text>` element gets
    data-purpose="reference-label" if it lacks one. `<path>` elements and
    all other content are left byte-for-byte alone.

    Idempotent (a second call on an already-fixed file is a no-op) and safe
    to call unconditionally on any generated SVG, including one with no
    `<text>` elements at all (e.g. a Ponoko coupon with strip_labels).

    Returns True if the file was modified, False if it already conformed.
    """
    path = Path(svg_path)
    original = path.read_text()
    fixed = _TEXT_OPEN_TAG_RE.sub(
        lambda m: _ensure_data_purpose(_rewrite_attrs(m.group(0))), original
    )
    if fixed == original:
        return False
    path.write_text(fixed)
    return True
