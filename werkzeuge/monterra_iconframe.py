#!/usr/bin/python3
"""Shared helper: bring any icon into the Monterra squircle shape (used by the Web-App and app tools)."""
import math
import os

import cairo
import gi
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf  # noqa: E402

SIZE = 256
SQUIRCLE = [("M", 32, 5), ("C", 50.5, 5, 59, 6.8, 59, 32), ("C", 59, 57.2, 50.5, 59, 32, 59),
            ("C", 13.5, 59, 5, 57.2, 5, 32), ("C", 5, 6.8, 13.5, 5, 32, 5)]


def _path(cr, k, grow=0.0, dy=0.0):
    def tr(x, y):
        return ((32 + (x - 32) * (1 + grow)) * k, (32 + (y - 32) * (1 + grow) + dy) * k)
    for seg in SQUIRCLE:
        if seg[0] == "M":
            cr.move_to(*tr(seg[1], seg[2]))
        else:
            cr.curve_to(*tr(seg[1], seg[2]), *tr(seg[3], seg[4]), *tr(seg[5], seg[6]))
    cr.close_path()


class _Px:
    """Fast read access to a pixbuf's pixels (get_pixels() copies the buffer on every call)."""
    def __init__(self, pb):
        self.pb = pb
        self.w, self.h = pb.get_width(), pb.get_height()
        self.rs, self.n = pb.get_rowstride(), pb.get_n_channels()
        self.has_alpha = pb.get_has_alpha()
        self.data = pb.get_pixels()

    def alpha(self, x, y):
        if not self.has_alpha:
            return 255
        return self.data[y * self.rs + x * self.n + 3]

    def rgb(self, x, y):
        o = y * self.rs + x * self.n
        return self.data[o], self.data[o + 1], self.data[o + 2]


def crop_to_content(pb):
    """Remove transparent margins, keeping the result square."""
    if not pb.get_has_alpha():
        return pb
    small = pb.scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR)
    px = _Px(small)
    xs = [x for x in range(128) if any(px.alpha(x, y) > 20 for y in range(128))]
    ys = [y for y in range(128) if any(px.alpha(x, y) > 20 for x in range(128))]
    if not xs or not ys:
        return pb
    f = pb.get_width() / 128
    x0, x1, y0, y1 = int(xs[0] * f), int((xs[-1] + 1) * f), int(ys[0] * f), int((ys[-1] + 1) * f)
    side = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    x0, y0 = max(0, cx - side // 2), max(0, cy - side // 2)
    side = max(1, min(side, pb.get_width() - x0, pb.get_height() - y0))
    return pb.new_subpixbuf(x0, y0, side, side)


def classify(pb):
    """'cover' = (rounded) square, 'round' = filled disc, 'fit' = free-form logo."""
    px = _Px(pb.scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR))
    w = h = 128
    corners = [(int(w * fx), int(h * fy)) for fx in (0.12, 0.88) for fy in (0.12, 0.88)]
    if sum(px.alpha(x, y) > 200 for x, y in corners) >= 3:
        edge = [(int(w * f), int(h * 0.04)) for f in (0.3, 0.5, 0.7)] + \
               [(int(w * f), int(h * 0.96)) for f in (0.3, 0.5, 0.7)] + \
               [(int(w * 0.04), int(h * f)) for f in (0.3, 0.5, 0.7)] + \
               [(int(w * 0.96), int(h * f)) for f in (0.3, 0.5, 0.7)]
        if sum(px.alpha(x, y) > 200 for x, y in edge) >= 10:
            return "cover"
    ring = [(int(w / 2 + math.cos(a) * w * 0.46), int(h / 2 + math.sin(a) * h * 0.46))
            for a in (i / 48 * 2 * math.pi for i in range(48))]
    outside_clear = all(px.alpha(x, y) < 60 for x, y in corners)
    if outside_clear and sum(px.alpha(x, y) > 200 for x, y in ring) >= 44:
        return "round"
    return "fit"


def ring_colour(pb):
    px = _Px(pb.scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR))
    acc, cnt = [0, 0, 0], 0
    for i in range(72):
        a = i / 72 * 2 * math.pi
        x = int(64 + math.cos(a) * 128 * 0.44)
        y = int(64 + math.sin(a) * 128 * 0.44)
        if px.alpha(x, y) > 200:
            r, g, b = px.rgb(x, y)
            acc[0] += r
            acc[1] += g
            acc[2] += b
            cnt += 1
    return tuple(v / cnt / 255 for v in acc) if cnt else (1, 1, 1)


def is_real_file(path):
    """GTK can report built-in resource icons (/org/gtk/...) that do not exist on disk."""
    return bool(path) and os.path.isfile(path)


def load(src, px=512):
    return crop_to_content(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(src), px, px, True))


def frame(src, dst, mode="auto", zoom=None, size=SIZE):
    k = size / 64
    pb = load(src)
    if mode == "auto":
        mode = classify(pb)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surf)
    for i in range(7, 0, -1):                       # soft shadow
        _path(cr, k, grow=0.004 * i, dy=0.9 + 0.12 * i)
        cr.set_source_rgba(0, 0, 0, 0.035)
        cr.fill()
    _path(cr, k)
    cr.save()
    cr.clip()
    if mode == "cover":
        z = zoom or 1.0
    elif mode == "round":
        cr.set_source_rgb(*ring_colour(pb))     # corners in the logo's edge colour …
        cr.paint()
        z = zoom or 1.12
        cr.arc(size / 2, size / 2, 54 * k * z * 0.47, 0, 2 * math.pi)
        cr.set_source_rgb(1, 1, 1)              # … and white behind cut-outs inside the disc
        cr.fill()
    else:                                           # free-form logo on a light card
        g = cairo.LinearGradient(0, 5 * k, 0, 59 * k)
        g.add_color_stop_rgb(0, 1, 1, 1)
        g.add_color_stop_rgb(1, 0.925, 0.925, 0.937)
        cr.set_source(g)
        cr.paint()
        z = zoom or 0.76
    scale = 54 * k * z / max(pb.get_width(), pb.get_height())
    w, h = pb.get_width() * scale, pb.get_height() * scale
    cr.translate(size / 2 - w / 2, size / 2 - h / 2)
    cr.scale(scale, scale)
    Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_BEST)
    cr.paint()
    cr.restore()
    _path(cr, k)
    cr.set_line_width(0.6 * k)
    cr.set_source_rgba(0, 0, 0, 0.12)
    cr.stroke()
    surf.write_to_png(str(dst))
    return mode
