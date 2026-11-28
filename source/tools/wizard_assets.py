#!/usr/bin/env python3
"""Bilder für den Monterra-Assistenten (tools/wizard.py) erzeugen.

    python3 source/tools/wizard_assets.py PAKET

Schreibt nach PAKET/previews/wizard/:
  extra-*.svg              Symbole der Zusatz-Bestandteile (Monterra-Squircle + Phosphor-Glyphe)
  layout-*-light|dark.svg  schematische Bildschirme für die Layout-Auswahl
  hero-light|dark.jpg      Kopfbild der Willkommensseite (Hintergrund + Logo)
  variant-light|dark.jpg   Vorschau hell / dunkel (aus Bildschirmfotos, falls angegeben)
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

PKG = sys.argv[1]
OUT = os.path.join(PKG, "previews", "wizard")
os.makedirs(OUT, exist_ok=True)

GLYPHS = {g["n"]: g["d"] for g in json.load(open(os.path.join(PKG, "components/icon-workshop/glyphs.json")))["icons"]}
SQUIRCLE = "M32 5 C50.5 5 59 6.8 59 32 C59 57.2 50.5 59 32 59 C13.5 59 5 57.2 5 32 C5 6.8 13.5 5 32 5 Z"

# Bestandteil -> (Glyphe, Verlauf oben, Verlauf unten)
EXTRAS = {
    "font":     ("text-aa",          "#8E8E93", "#5B5B60"),
    "appicons": ("squares-four",     "#5AC8FA", "#0A84FF"),
    "auto":     ("magic-wand",       "#BF5AF2", "#7D3BD6"),
    "werkst":   ("paint-brush",      "#FF9F0A", "#F06A00"),
    "fenster":  ("cards",            "#64D2FF", "#2F8FD8"),
    "fgroesse": ("arrows-out",       "#30D158", "#1E9E45"),
    "setgrid":  ("dots-nine",        "#7C7C80", "#48484C"),
    "firefox":  ("globe",            "#FF7A45", "#E2402B"),
    "thunderb": ("envelope-simple",  "#409CFF", "#1660D8"),
    "folders":  ("folder",           "#FFD60A", "#F2A900"),
    "splash":   ("power",            "#5E5CE6", "#3634A3"),
    "login":    ("user-circle",      "#FF375F", "#C91E45"),
    # Seiten des Assistenten
    "mode-install": ("download-simple",         "#5AC8FA", "#0A84FF"),
    "mode-remove":  ("arrow-counter-clockwise", "#98989D", "#636366"),
    "done":         ("check-circle",            "#30D158", "#1E9E45"),
    "warning":      ("warning-circle",          "#FFB340", "#F07800"),
}


def extra_icon(key, glyph, top, bottom):
    d = " ".join(GLYPHS[glyph])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>
<linearGradient id="h" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
<path d="{SQUIRCLE}" fill="url(#g)"/><path d="{SQUIRCLE}" fill="url(#h)"/>
<g transform="translate(17 17) scale(0.1171875)"><path d="{d}" fill="#fff"/></g>
</svg>
'''
    open(os.path.join(OUT, f"extra-{key}.svg"), "w").write(svg)


# ------------------------------------------------------------------ Layout-Bildschirme
def layout_svg(kind, dark):
    W, H = 320, 200
    bg1, bg2 = ("#2B2B5E", "#5A2A62") if dark else ("#BFD8FF", "#6EA3F5")
    bar = "rgba(30,30,34,0.78)" if dark else "rgba(255,255,255,0.72)"
    barline = "rgba(255,255,255,0.10)" if dark else "rgba(0,0,0,0.08)"
    txt = "rgba(255,255,255,0.80)" if dark else "rgba(0,0,0,0.62)"
    win = "#2C2C2E" if dark else "#FFFFFF"
    winbar = "#3A3A3C" if dark else "#F2F2F4"
    dockbg = "rgba(60,60,66,0.72)" if dark else "rgba(255,255,255,0.55)"
    icons = ["#0A84FF", "#30D158", "#FF9F0A", "#FF375F", "#BF5AF2", "#64D2FF", "#8E8E93"]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{bg1}"/>'
         f'<stop offset="1" stop-color="{bg2}"/></linearGradient>'
         f'<clipPath id="c"><rect width="{W}" height="{H}" rx="14"/></clipPath>'
         f'<filter id="s" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="4" stdDeviation="6" flood-opacity="{0.45 if dark else 0.22}"/></filter></defs>',
         '<g clip-path="url(#c)">',
         f'<rect width="{W}" height="{H}" fill="url(#bg)"/>']
    top = kind in ("menubar-dock", "menubar-panel")
    # Fenster
    wy = 34 if top else 24
    p.append(f'<g filter="url(#s)"><rect x="62" y="{wy}" width="196" height="104" rx="9" fill="{win}"/></g>')
    p.append(f'<path d="M62 {wy + 9} a9 9 0 0 1 9 -9 h178 a9 9 0 0 1 9 9 v9 h-196 z" fill="{winbar}"/>')
    for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        p.append(f'<circle cx="{74 + i * 10}" cy="{wy + 9}" r="3.2" fill="{c}"/>')
    for i in range(4):
        p.append(f'<rect x="76" y="{wy + 30 + i * 16}" width="{150 - i * 24}" height="6" rx="3" fill="{txt}" opacity="0.25"/>')
    if top:   # Menüleiste oben: Logo + Kategorien + Uhr
        p.append(f'<rect width="{W}" height="16" fill="{bar}"/><rect y="16" width="{W}" height="1" fill="{barline}"/>')
        p.append(f'<circle cx="12" cy="8" r="4.2" fill="none" stroke="{txt}" stroke-width="1.4"/>')
        x = 24
        for w in (22, 18, 26, 20, 24):
            p.append(f'<rect x="{x}" y="6" width="{w}" height="4" rx="2" fill="{txt}"/>'); x += w + 8
        p.append(f'<rect x="{W - 36}" y="6" width="26" height="4" rx="2" fill="{txt}"/>')
    if kind in ("menubar-dock", "dock-only"):   # schwebendes Dock
        n = 7; s = 16; g = 6
        dw = n * s + (n - 1) * g + 16
        dx = (W - dw) / 2; dy = H - 30 - (24 if kind == "dock-only" else 0)
        p.append(f'<g filter="url(#s)"><rect x="{dx}" y="{dy}" width="{dw}" height="26" rx="9" fill="{dockbg}"/></g>')
        for i in range(n):
            p.append(f'<rect x="{dx + 8 + i * (s + g)}" y="{dy + 5}" width="{s}" height="{s}" rx="5" fill="{icons[i]}"/>')
    if kind in ("menubar-panel", "dock-only", "keep"):   # Panel unten über die ganze Breite
        p.append(f'<rect y="{H - 22}" width="{W}" height="22" fill="{bar}"/><rect y="{H - 22}" width="{W}" height="1" fill="{barline}"/>')
        if kind == "menubar-panel":
            n = 7; s = 14; g = 6
            x0 = (W - (n * s + (n - 1) * g)) / 2
            for i in range(n):
                p.append(f'<rect x="{x0 + i * (s + g)}" y="{H - 18}" width="{s}" height="{s}" rx="4" fill="{icons[i]}"/>')
        else:   # klassisches Mint-Panel: Menü links, Fensterliste, Uhr rechts
            p.append(f'<rect x="6" y="{H - 17}" width="12" height="12" rx="3" fill="#30D158"/>')
            for i in range(3):
                p.append(f'<rect x="{26 + i * 18}" y="{H - 17}" width="12" height="12" rx="3" fill="{icons[i]}" opacity="0.9"/>')
            p.append(f'<rect x="{W - 34}" y="{H - 13}" width="26" height="4" rx="2" fill="{txt}"/>')
    p.append('</g>')
    p.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{"rgba(255,255,255,0.12)" if dark else "rgba(0,0,0,0.10)"}"/>')
    p.append('</svg>')
    open(os.path.join(OUT, f"layout-{kind}-{'dark' if dark else 'light'}.svg"), "w").write("\n".join(p))


# ------------------------------------------------------------------ Kopfbild
def hero(dark):
    wall = os.path.join(PKG, "wallpapers", f"Monterra-{'Blossom-Dark' if dark else 'Sky-Light'}.jpg")
    W, H = 1360, 400
    im = Image.open(wall).convert("RGB")
    s = W / im.width
    im = im.resize((W, round(im.height * s)), Image.LANCZOS)
    top = (im.height - H) // 2
    im = im.crop((0, top, W, top + H))
    sys.path.insert(0, os.path.join(PKG, "source", "tools"))
    from splash import LOGO
    svg = LOGO.replace("{color}", "#FFFFFF")
    png = subprocess.run(["rsvg-convert", "-w", "220", "-h", "220"], input=svg.encode(), capture_output=True, check=True).stdout
    import io
    logo = Image.open(io.BytesIO(png)).convert("RGBA")
    sh = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    sh.putalpha(logo.split()[3].point(lambda a: int(a * 0.35)))
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    base = im.convert("RGBA")
    pos = ((W - logo.width) // 2, (H - logo.height) // 2)
    base.alpha_composite(sh, (pos[0], pos[1] + 6))
    base.alpha_composite(logo, pos)
    base.convert("RGB").save(os.path.join(OUT, f"hero-{'dark' if dark else 'light'}.jpg"), quality=90)


for k, v in EXTRAS.items():
    extra_icon(k, *v)
for kind in ("menubar-dock", "menubar-panel", "dock-only", "keep"):
    layout_svg(kind, False)
    layout_svg(kind, True)
hero(False)
hero(True)
# Vorschau hell/dunkel aus Bildschirmfotos (optional: --shots HELL DUNKEL)
if "--shots" in sys.argv:
    i = sys.argv.index("--shots")
    for v, f in (("light", sys.argv[i + 1]), ("dark", sys.argv[i + 2])):
        im = Image.open(f).convert("RGB")
        im = im.resize((640, round(im.height * 640 / im.width)), Image.LANCZOS)
        im.save(os.path.join(OUT, f"variant-{v}.jpg"), quality=90)
print("ok", OUT)
