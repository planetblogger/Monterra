#!/usr/bin/env python3
"""
Monterra-Cursor – clean X11 cursor theme (original drawings; hand outlines from
Phosphor Icons, MIT). Renders every cursor at high resolution, downsamples to the nominal
sizes and packs them with xcursorgen. Aliases are written as real copies (no symlinks),
so the theme survives any unzip tool.
"""
import io
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
HAND_DIR = HERE.parent / "third_party" / "phosphor-cursor"

UNIT = 32                 # design grid
HI = 512                  # hi-res render size for the 32-unit box (16x)
SIZES = [24, 32, 48, 64, 96]
NAME = "Monterra-Cursor"

BLACK, WHITE = "#1C1C1E", "#FFFFFF"
BLUE, RED, GREEN = "#0A84FF", "#FF3B30", "#30D158"

# ----------------------------------------------------------------- geometry
ARROW = "M5 3 L5 23.6 L9.7 19.3 L12.9 26.7 L16.3 25.2 L13.2 18 L19.6 18 Z"
DOUBLE = "M4 16 L10 10.2 V13.9 H22 V10.2 L28 16 L22 21.8 V18.1 H10 V21.8 Z"
SPLIT_L = "M3.5 16 L9 10.8 V14.2 H13 V17.8 H9 V21.2 Z"
SPLIT_R = "M28.5 16 L23 10.8 V14.2 H19 V17.8 H23 V21.2 Z"
SPLIT_BAR = "M14.6 6.5 H17.4 V25.5 H14.6 Z"
MOVE_H = "M3.5 16 L8.5 11.2 V14.4 H23.5 V11.2 L28.5 16 L23.5 20.8 V17.6 H8.5 V20.8 Z"
IBEAM = ("M12.2 5.6 C14.6 5.6 16 6.4 16 8.4 C16 6.4 17.4 5.6 19.8 5.6 M16 8.4 V23.6 "
         "M12.2 26.4 C14.6 26.4 16 25.6 16 23.6 C16 25.6 17.4 26.4 19.8 26.4 M13.4 16 H18.6")
CROSS = "M16 5 V27 M5 16 H27"
PLUS_CELL = "M13 6 H19 V13 H26 V19 H19 V26 H13 V19 H6 V13 H13 Z"


def dark_shape(paths, transform="", stroke_w=2.2, line=False, line_w=1.6):
    """Black shape with white outline (filled polygons or stroked lines)."""
    t = f' transform="{transform}"' if transform else ""
    if line:
        under = "".join(f'<path d="{p}" fill="none" stroke="{WHITE}" stroke-width="{line_w + 2.2}" '
                        f'stroke-linecap="round" stroke-linejoin="round"/>' for p in paths)
        over = "".join(f'<path d="{p}" fill="none" stroke="{BLACK}" stroke-width="{line_w}" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>' for p in paths)
    else:
        under = "".join(f'<path d="{p}" fill="{WHITE}" stroke="{WHITE}" stroke-width="{stroke_w}" '
                        f'stroke-linejoin="round"/>' for p in paths)
        over = "".join(f'<path d="{p}" fill="{BLACK}"/>' for p in paths)
    return f"<g{t}>{under}{over}</g>"


def badge(kind, cx=21.5, cy=21.5, r=5.6):
    ring = f'<circle cx="{cx}" cy="{cy}" r="{r + 1}" fill="{WHITE}"/>'
    if kind == "help":
        return (ring + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{BLUE}"/>'
                f'<g transform="translate({cx} {cy})"><path d="M-2.1 -1.7 C-2.1 -3.9 -0.9 -4.1 0.1 -4.1 '
                f'C1.6 -4.1 2.3 -3.1 2.3 -2 C2.3 -0.6 0.6 -0.3 0.1 0.7 L0.1 1.2" fill="none" stroke="{WHITE}" '
                f'stroke-width="1.45" stroke-linecap="round"/><circle cx="0.1" cy="3.3" r="0.95" fill="{WHITE}"/></g>')
    if kind == "no":
        return (ring + f'<circle cx="{cx}" cy="{cy}" r="{r - 0.9}" fill="none" stroke="{RED}" stroke-width="1.9"/>'
                f'<path d="M{cx - 3.2} {cy - 3.2} L{cx + 3.2} {cy + 3.2}" stroke="{RED}" stroke-width="1.9"/>')
    if kind == "copy":
        return (ring + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{GREEN}"/>'
                f'<path d="M{cx} {cy - 3} V{cy + 3} M{cx - 3} {cy} H{cx + 3}" stroke="{WHITE}" '
                f'stroke-width="1.7" stroke-linecap="round"/>')
    if kind == "alias":
        return (ring + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{BLACK}"/>'
                f'<path d="M{cx - 2.6} {cy + 2.8} C{cx - 2.6} {cy - 0.6} {cx - 1} {cy - 1.8} {cx + 2} {cy - 1.8}" '
                f'fill="none" stroke="{WHITE}" stroke-width="1.4" stroke-linecap="round"/>'
                f'<path d="M{cx + 0.6} {cy - 4} L{cx + 3.3} {cy - 1.8} L{cx + 0.6} {cy + 0.4} Z" fill="{WHITE}"/>')
    if kind == "menu":
        x, y = cx - 4.5, cy - 4.2
        return (f'<rect x="{x - 1}" y="{y - 1}" width="11" height="10.4" rx="2.4" fill="{WHITE}"/>'
                f'<rect x="{x}" y="{y}" width="9" height="8.4" rx="1.6" fill="{BLACK}"/>'
                + "".join(f'<rect x="{x + 1.8}" y="{y + 1.7 + i * 2}" width="5.4" height="0.9" rx=".45" '
                          f'fill="{WHITE}"/>' for i in range(3)))
    raise ValueError(kind)


def spinner(cx, cy, r, angle, w=2.6):
    circ = 2 * math.pi * r
    arc = circ * 0.28
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{WHITE}" stroke-width="{w + 2}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#C7C7CC" stroke-width="{w}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{BLUE}" stroke-width="{w}" '
            f'stroke-linecap="round" stroke-dasharray="{arc:.3f} {circ:.3f}" '
            f'transform="rotate({angle - 90} {cx} {cy})"/>')


def magnifier(sign):
    inner = '<path d="M10.2 13 H15.8" stroke="#1C1C1E" stroke-width="1.6" stroke-linecap="round"/>'
    if sign == "+":
        inner += '<path d="M13 10.2 V15.8" stroke="#1C1C1E" stroke-width="1.6" stroke-linecap="round"/>'
    return (f'<path d="M17.6 17.6 L25.5 25.5" stroke="{WHITE}" stroke-width="5.6" stroke-linecap="round"/>'
            f'<path d="M17.6 17.6 L25.5 25.5" stroke="{BLACK}" stroke-width="3.2" stroke-linecap="round"/>'
            f'<circle cx="13" cy="13" r="7.4" fill="{WHITE}" stroke="{BLACK}" stroke-width="1.6"/>' + inner)


def svg(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{HI}" height="{HI}" '
            f'viewBox="0 0 {UNIT} {UNIT}">{body}</svg>')


# ----------------------------------------------------------------- rasterising
def rasterise(svg_text):
    p = subprocess.run(["rsvg-convert", "-w", str(HI), "-h", str(HI)], input=svg_text.encode(),
                       capture_output=True, check=True)
    return np.asarray(Image.open(io.BytesIO(p.stdout)).convert("RGBA")).astype(np.float32) / 255


def hand_layer(name, box, flip=False):
    """White hand with black outline from a Phosphor outline glyph. box = (x, y, size) in units."""
    gx, gy, gs = box
    glyph = (HAND_DIR / f"{name}.svg").read_text()
    inner = glyph[glyph.index(">") + 1: glyph.rindex("</svg>")]
    s = gs / 256
    t = f"translate({gx} {gy}) scale({s})" + (" translate(256 0) scale(-1 1)" if flip else "")
    line = rasterise(svg(f'<g transform="{t}" fill="#000">{inner}</g>'))[..., 3]
    filled = ndimage.binary_fill_holes(line > 0.5)
    interior = np.clip(filled.astype(np.float32) - line, 0, 1)
    interior = ndimage.gaussian_filter(interior, 0.6)          # soften the hole edges
    alpha = np.clip(line + interior, 0, 1)
    rgb = np.zeros(line.shape + (3,), np.float32)
    white_share = np.where(alpha > 0, interior / np.maximum(alpha, 1e-6), 0)
    black = np.array([0x1C, 0x1C, 0x1E], np.float32) / 255
    rgb[:] = black
    rgb += (1 - black) * np.clip(white_share, 0, 1)[..., None]
    # thin white halo outside the outline for contrast on dark backgrounds
    halo = ndimage.binary_dilation(filled, iterations=int(HI / UNIT * 0.55)) & ~filled
    halo = ndimage.gaussian_filter(halo.astype(np.float32), 0.8)
    out = np.dstack([rgb, alpha])
    under = np.dstack([np.ones_like(rgb), halo * 0.95])
    return over(out, under)


def over(top, bottom):
    a = top[..., 3:4] + bottom[..., 3:4] * (1 - top[..., 3:4])
    rgb = (top[..., :3] * top[..., 3:4] + bottom[..., :3] * bottom[..., 3:4] * (1 - top[..., 3:4])) / np.maximum(a, 1e-6)
    return np.dstack([rgb, a])


def with_shadow(img):
    a = img[..., 3]
    k = HI / UNIT
    sh = ndimage.shift(a, (0.9 * k, 0.25 * k), order=1)
    sh = ndimage.gaussian_filter(sh, 0.9 * k) * 0.38
    shadow = np.dstack([np.zeros(a.shape + (3,), np.float32), sh])
    return over(img, shadow)


def downsample(img, size):
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").convert("RGBa")
    return im.resize((size, size), Image.LANCZOS).convert("RGBA")


# ----------------------------------------------------------------- cursor table
def frames_static(body_fn):
    return [rasterise(svg(body_fn()))]


def build_cursors():
    arrow = lambda: dark_shape([ARROW], stroke_w=2.3)  # noqa: E731
    C = {}  # name -> (frames(list of hi-res RGBA), hot(x,y) in units, delay ms)

    C["default"] = (frames_static(arrow), (5, 3), 0)
    C["right_ptr"] = (frames_static(lambda: dark_shape([ARROW], "translate(32 0) scale(-1 1)", 2.3)), (27, 3), 0)
    C["help"] = (frames_static(lambda: arrow() + badge("help")), (5, 3), 0)
    C["not-allowed"] = (frames_static(lambda: arrow() + badge("no")), (5, 3), 0)
    C["copy"] = (frames_static(lambda: arrow() + badge("copy")), (5, 3), 0)
    C["alias"] = (frames_static(lambda: arrow() + badge("alias")), (5, 3), 0)
    C["context-menu"] = (frames_static(lambda: arrow() + badge("menu")), (5, 3), 0)
    C["text"] = (frames_static(lambda: dark_shape([IBEAM], line=True, line_w=1.5)), (16, 16), 0)
    C["vertical-text"] = (frames_static(lambda: dark_shape([IBEAM], "rotate(90 16 16)", line=True, line_w=1.5)), (16, 16), 0)
    C["crosshair"] = (frames_static(lambda: dark_shape([CROSS], line=True, line_w=1.3)), (16, 16), 0)
    C["cell"] = (frames_static(lambda: f'<path d="{PLUS_CELL}" fill="{WHITE}" stroke="{BLACK}" stroke-width="1.5" '
                                       f'stroke-linejoin="round"/>'), (16, 16), 0)
    C["ew-resize"] = (frames_static(lambda: dark_shape([DOUBLE])), (16, 16), 0)
    C["ns-resize"] = (frames_static(lambda: dark_shape([DOUBLE], "rotate(90 16 16)")), (16, 16), 0)
    C["nwse-resize"] = (frames_static(lambda: dark_shape([DOUBLE], "rotate(45 16 16)")), (16, 16), 0)
    C["nesw-resize"] = (frames_static(lambda: dark_shape([DOUBLE], "rotate(-45 16 16)")), (16, 16), 0)
    C["col-resize"] = (frames_static(lambda: dark_shape([SPLIT_L, SPLIT_R, SPLIT_BAR])), (16, 16), 0)
    C["row-resize"] = (frames_static(lambda: dark_shape([SPLIT_L, SPLIT_R, SPLIT_BAR], "rotate(90 16 16)")), (16, 16), 0)
    C["move"] = (frames_static(lambda: dark_shape([MOVE_H, MOVE_H.replace("M", "M", 1)], "")
                               .replace("</g>", "</g>", 1)), (16, 16), 0)
    # proper 4-way: draw both arms, all white outlines first, then black
    four = (f'<g>{"".join(f"<path d=\"{MOVE_H}\" transform=\"rotate({a} 16 16)\" fill=\"{WHITE}\" stroke=\"{WHITE}\" stroke-width=\"2.2\" stroke-linejoin=\"round\"/>" for a in (0, 90))}'
            f'{"".join(f"<path d=\"{MOVE_H}\" transform=\"rotate({a} 16 16)\" fill=\"{BLACK}\"/>" for a in (0, 90))}</g>')
    C["move"] = ([rasterise(svg(four))], (16, 16), 0)
    C["zoom-in"] = (frames_static(lambda: magnifier("+")), (13, 13), 0)
    C["zoom-out"] = (frames_static(lambda: magnifier("-")), (13, 13), 0)

    # hands (white with black outline)
    point = hand_layer("hand-pointing", (3.2, 3.0, 26))
    ys, xs = np.nonzero(point[..., 3] > 0.5)
    top = ys.min()
    tip_x = xs[ys < top + HI / UNIT * 1.2].mean()
    C["pointer"] = ([point], (tip_x / HI * UNIT, top / HI * UNIT + 0.6), 0)
    C["grab"] = ([hand_layer("hand", (3.5, 3.5, 25))], (16, 15), 0)
    C["grabbing"] = ([hand_layer("hand-grabbing", (3.5, 4.5, 25))], (16, 16), 0)

    # animated
    n = 24
    C["wait"] = ([rasterise(svg(spinner(16, 16, 8.2, i * 360 / n, 3.2))) for i in range(n)], (16, 16), 40)
    C["progress"] = ([rasterise(svg(arrow() + spinner(21.5, 22, 4.6, i * 360 / n, 2.2))) for i in range(n)], (5, 3), 40)
    return C


ALIASES = {
    "default": ["left_ptr", "arrow", "top_left_arrow", "left_arrow", "center_ptr", "up_arrow", "draft_large",
                "draft_small", "x-cursor", "X_cursor"],
    "right_ptr": ["right_arrow"],
    "help": ["question_arrow", "whats_this", "left_ptr_help", "dnd-ask",
             "5c6cd98b3f3ebcb1f9c7f1c204630408", "d9ce0ab605698f320427677b458ad60b"],
    "not-allowed": ["crossed_circle", "circle", "forbidden", "no-drop", "dnd-no-drop", "pirate",
                    "03b6e0fcb3499374a867c041f52298f0"],
    "copy": ["dnd-copy", "1081e37283d90000800003c07f3ef6bf", "6407b0e94181790501fd1e167b474872",
             "08ffe1cb5fe6fc01f906f1c063814ccf"],
    "alias": ["link", "dnd-link", "3085a0e285430894940527032f8b26df", "640fb0e74195791501fd1ed57b41487f",
              "0876e1c15ff2fc01f906f1c363074c0f"],
    "context-menu": [],
    "text": ["xterm", "ibeam"],
    "vertical-text": [],
    "crosshair": ["cross", "tcross", "cross_reverse", "diamond_cross", "target", "dotbox", "color-picker"],
    "cell": ["plus"],
    "ew-resize": ["e-resize", "w-resize", "right_side", "left_side", "size_hor", "h_double_arrow",
                  "sb_h_double_arrow", "028006030e0e7ebffc7f7070c0600140"],
    "ns-resize": ["n-resize", "s-resize", "top_side", "bottom_side", "size_ver", "v_double_arrow",
                  "sb_v_double_arrow", "00008160000006810000408080010102"],
    "nwse-resize": ["nw-resize", "se-resize", "top_left_corner", "bottom_right_corner", "size_fdiag",
                    "c7088f0f3e6c8088236ef8e1e3e70000"],
    "nesw-resize": ["ne-resize", "sw-resize", "top_right_corner", "bottom_left_corner", "size_bdiag",
                    "fcf1c3c7cd4491d801f1e1c78f100000"],
    "col-resize": ["split_h", "14fef782d02440884392942c11205230"],
    "row-resize": ["split_v", "2870a09082c103050810ffdffffe0204"],
    "move": ["fleur", "all-scroll", "size_all", "dnd-move", "all-resize",
             "4498f0e0c1937ffe01fd06f973665830", "9081237383d90e509aa00f00170e968f"],
    "zoom-in": [],
    "zoom-out": [],
    "pointer": ["hand2", "hand1", "hand", "pointing_hand", "e29285e634086352946a0e7090d73106",
                "9d800788f1b08800ae810202380a0822"],
    "grab": ["openhand", "9141b49c8149039304290b508d208c40", "5aca4d189052212118709018842178c0"],
    "grabbing": ["closedhand", "dnd-none", "fcf21c00b30f7e3f83fe0dfd12e71cff", "208530c400c041818281048008011002"],
    "wait": ["watch"],
    "progress": ["left_ptr_watch", "half-busy", "3ecb610c1bf2410f44200f48c40d3599",
                 "00000000000000020006000e7e9ffc3f", "08e8e1c95fe2fc01f976f1e063a24ccd"],
}


def build(outdir, preview=None):
    out = Path(outdir)
    if out.exists():
        shutil.rmtree(out)
    cdir = out / "cursors"
    cdir.mkdir(parents=True)
    (out / "index.theme").write_text(
        f"[Icon Theme]\nName={NAME}\nComment=Clean cursors for Linux Mint (Monterra)\nInherits=Adwaita\n")
    (out / "cursor.theme").write_text(f"[Icon Theme]\nName={NAME}\nInherits={NAME}\n")

    cursors = build_cursors()
    previews = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, (frames, (hx, hy), delay) in cursors.items():
            cfg = []
            for fi, fr in enumerate(frames):
                fr = with_shadow(fr)
                for size in SIZES:
                    png = tmp / f"{name}-{size}-{fi:02d}.png"
                    downsample(fr, size).save(png)
                    sx = min(size - 1, round(hx / UNIT * size))
                    sy = min(size - 1, round(hy / UNIT * size))
                    cfg.append(f"{size} {sx} {sy} {png}" + (f" {delay}" if delay else ""))
                if fi == 0:
                    previews.append((name, downsample(fr, 64)))
            cfgfile = tmp / f"{name}.cfg"
            cfgfile.write_text("\n".join(cfg) + "\n")
            subprocess.run(["xcursorgen", str(cfgfile), str(cdir / name)], check=True)
            for alias in ALIASES.get(name, []):
                shutil.copy(cdir / name, cdir / alias)
    if preview:
        cols = 9
        rows = math.ceil(len(previews) / cols)
        sheet = Image.new("RGBA", (cols * 100, rows * 100), (236, 236, 236, 255))
        for i, (_n, im) in enumerate(previews):
            sheet.alpha_composite(im, ((i % cols) * 100 + 18, (i // cols) * 100 + 18))
        sheet.save(preview)
    n_files = len(list(cdir.iterdir()))
    print(f"{len(cursors)} cursors, {n_files} files incl. aliases")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
