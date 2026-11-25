#!/usr/bin/env python3
"""
Vorschaubilder für die Bildauswahl im Installer.

usage: installer_previews.py PAKET
  -> PAKET/vorschau/auswahl/motiv-<Motiv>-<Hell|Dunkel>.png
     PAKET/vorschau/auswahl/akzent-<farbe>-<hell|dunkel>.png
     PAKET/vorschau/auswahl/motiv-keep-<Hell|Dunkel>.png
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akzente  # noqa: E402

TW, TH = 360, 203        # 16:9
SS = 3                   # Supersampling für glatte Kanten
RADIUS = 14
MOTIVE = ["Himmel", "Wueste", "Mars", "Dschungel", "Seide", "Bluete"]


def font(size, weight="Medium"):
    for p in (f"/usr/share/fonts/opentype/inter/Inter-{weight}.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def rounded(im, r=RADIUS):
    big = Image.new("L", (im.width * SS, im.height * SS), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, big.width - 1, big.height - 1), r * SS, fill=255)
    mask = big.resize(im.size, Image.LANCZOS)
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def hexc(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def svg_png(svg, size):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "i.png"
        subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), str(svg), "-o", str(out)], check=True)
        return Image.open(out).convert("RGBA").copy()


def accent_preview(pkg, name, dark):
    a = akzente.get(name)
    acc = a["dark" if dark else "light"]
    fg = a["fg"]
    W, H = TW * SS, TH * SS
    bg = "#2C2C2E" if dark else "#F2F2F4"
    card = "#3A3A3C" if dark else "#FFFFFF"
    text = "#F2F2F7" if dark else "#1D1D1F"
    sub = "#8E8E93"
    im = Image.new("RGBA", (W, H), hexc(bg))
    d = ImageDraw.Draw(im)
    s = SS
    # Ordner
    icons = pkg / "icons"
    svg = icons / a["folders"] / "places" / "scalable" / "folder.svg"
    if not svg.exists():
        svg = icons / "Monterra" / "places" / "scalable" / "folder.svg"
    fol = svg_png(svg, 92 * s)
    im.alpha_composite(fol, (22 * s, 26 * s))
    # Liste mit ausgewählter Zeile
    x0, y0 = 22 * s, 136 * s
    d.rounded_rectangle((x0, y0, x0 + 150 * s, y0 + 46 * s), 9 * s, fill=hexc(card))
    d.rounded_rectangle((x0 + 4 * s, y0 + 4 * s, x0 + 146 * s, y0 + 22 * s), 6 * s, fill=hexc(acc))
    f = font(11 * s)
    # sprachneutral: Textzeilen als Balken
    d.rounded_rectangle((x0 + 12 * s, y0 + 10 * s, x0 + 84 * s, y0 + 16 * s), 3 * s, fill=hexc(fg, 230))
    d.rounded_rectangle((x0 + 12 * s, y0 + 30 * s, x0 + 64 * s, y0 + 36 * s), 3 * s, fill=hexc(sub))
    # Schalter (an)
    sx, sy = 196 * s, 30 * s
    d.rounded_rectangle((sx, sy, sx + 52 * s, sy + 30 * s), 15 * s, fill=hexc(acc))
    d.ellipse((sx + 24 * s, sy + 2 * s, sx + 50 * s, sy + 28 * s), fill=hexc("#FFFFFF"))
    # Häkchen
    cx, cy = 264 * s, 31 * s
    d.rounded_rectangle((cx, cy, cx + 28 * s, cy + 28 * s), 7 * s, fill=hexc(acc))
    d.line((cx + 7 * s, cy + 15 * s, cx + 12 * s, cy + 20 * s, cx + 21 * s, cy + 9 * s), fill=hexc(fg), width=3 * s, joint="curve")
    # Optionsfeld
    rx, ry = 304 * s, 31 * s
    d.ellipse((rx, ry, rx + 28 * s, ry + 28 * s), fill=hexc(acc))
    d.ellipse((rx + 9 * s, ry + 9 * s, rx + 19 * s, ry + 19 * s), fill=hexc(fg))
    # Schieberegler
    ly = 92 * s
    d.rounded_rectangle((196 * s, ly, 332 * s, ly + 6 * s), 3 * s, fill=hexc("#5A5A5E" if dark else "#D1D1D6"))
    d.rounded_rectangle((196 * s, ly, 286 * s, ly + 6 * s), 3 * s, fill=hexc(acc))
    d.ellipse((276 * s, ly - 8 * s, 298 * s, ly + 14 * s), fill=hexc("#FFFFFF"), outline=hexc("#00000030"), width=s)
    # Knöpfe
    by = 140 * s
    d.rounded_rectangle((196 * s, by, 260 * s, by + 30 * s), 8 * s, fill=hexc(card), outline=hexc("#0000001A") if not dark else None)
    d.rounded_rectangle((214 * s, by + 12 * s, 242 * s, by + 18 * s), 3 * s, fill=hexc(sub))
    d.rounded_rectangle((268 * s, by, 332 * s, by + 30 * s), 8 * s, fill=hexc(acc))
    d.text((300 * s, by + 15 * s), "OK", font=font(11 * s, "SemiBold"), fill=hexc(fg), anchor="mm")
    return rounded(im.resize((TW, TH), Image.LANCZOS).convert("RGB"))


def keep_preview(dark):
    W, H = TW * SS, TH * SS
    im = Image.new("RGB", (W, H), hexc("#2C2C2E" if dark else "#E5E5EA")[:3])
    d = ImageDraw.Draw(im)
    c = hexc("#8E8E93")
    cx, cy, r = W // 2, H // 2, 34 * SS
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=4 * SS)
    d.line((cx - r * 0.7, cy + r * 0.7, cx + r * 0.7, cy - r * 0.7), fill=c, width=4 * SS)
    return rounded(im.resize((TW, TH), Image.LANCZOS))


if __name__ == "__main__":
    pkg = Path(sys.argv[1])
    out = pkg / "vorschau" / "auswahl"
    out.mkdir(parents=True, exist_ok=True)
    for m in MOTIVE:
        for v in ("Hell", "Dunkel"):
            im = Image.open(pkg / "hintergruende" / f"Monterra-{m}-{v}.jpg").convert("RGB")
            im = rounded(im.resize((TW, TH), Image.LANCZOS))
            im.save(out / f"motiv-{m}-{v}.png", optimize=True)
    for v, dark in (("Hell", False), ("Dunkel", True)):
        keep_preview(dark).save(out / f"motiv-keep-{v}.png", optimize=True)
    for n in akzente.NAMES:
        for v, dark in (("hell", False), ("dunkel", True)):
            accent_preview(pkg, n, dark).save(out / f"akzent-{n.lower()}-{v}.png", optimize=True)
    print("ok", len(list(out.iterdir())))
