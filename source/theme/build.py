#!/usr/bin/env python3
"""
Monterra 2 – elegantes Theme für Cinnamon, gebaut auf Mint-Y (Linux Mint, GPL-3.0).

Grundsatz: Mint-Y bleibt unverändert in seiner Struktur. Monterra ändert nur
  1. die Farbpalette (Farbblöcke in _colors.scss),
  2. die Akzentfarbe – genau wie Mint seine eigenen Farbvarianten erzeugt
     (#35a854 wird ersetzt, Rasterbilder werden umgefärbt),
  3. die Eckenradien (gleiche Stellen, größere Werte),
  4. eine kleine Schicht pro Bereich (layers/*.scss), die zuletzt geladen wird.
Keine Eingriffe in den Fenstermanager, keine Erweiterungen, keine Zeicheneffekte.

  python3 build.py [MINT_THEMES_QUELLEN]
  Umgebung: MONTERRA_ACCENT=Blue|Green|…  MONTERRA_WORK=…  MONTERRA_DIST=…
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import accents  # noqa: E402
import buttons  # noqa: E402

MINT = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/mint-themes").resolve() / "src" / "Mint-Y"
ACC = accents.get(os.environ.get("MONTERRA_ACCENT", os.environ.get("MONTERRA_AKZENT", "Blue")))
WORK = Path(os.environ.get("MONTERRA_WORK", HERE / "work"))
DIST = Path(os.environ.get("MONTERRA_DIST", HERE / "dist"))
NAME = "Monterra"
MINT_ACCENT = "#35a854"

# --------------------------------------------------------------- Farbpaletten (GTK 3 / 4)
GTK_PALETTE = {
    "light": """@if $variant == 'light' {
    // Monterra hell
    $opposite:              BLACK;
    $base_color:            #FFFFFF;
    $text_color:            #1D1D1F;
    $header_bg:             #E9E9E9;
    $bg_color:              #F2F2F2;
    $borders_color:         #CFCFCF;
    $separator_color:       #E0E0E0;
    $header_bg_backdrop:    #F4F4F4;
    $header_border:         #D4D4D4;
    $header_highlight:      #F2F2F2;
    $osd_bg_color:          #3A3A3C;
    $entry_border:          #C9C9C9;
    $fg_color:              transparentize($opposite, 0.15);
    $header_entry_bg:       transparentize($base_color, 0.15);
    $header_entry_border:   transparentize($fg_color, 0.75);
    $button_bg:             #FFFFFF;
    $insensitive_bg_color:  mix($bg_color, $base_color, 40%);
    $header_button_bg:      transparentize($button_bg, 0.3);
    $header_button_border:  transparentize($fg_color, 0.8);
    $trough_color_treeview: #D9D9D9;
    $trough_color:          #DCDCDC;
    $wm_title_unfocused:    #A5A5A5;
    $wm_button_hover_bg:    #FDFDFF;
    $wm_button_active_bg:   #909092;
    $wm_icon_bg:            #404040;
    $wm_icon_unfocused_bg:  #D6D6D6;
    $wm_icon_hover_bg:      #404040;
}""",
    "dark": """@else {
    // Monterra dunkel
    $opposite:              WHITE;
    $base_color:            #1E1E1E;
    $text_color:            #E6E6E6;
    $header_bg:             #2E2E2E;
    $bg_color:              #282828;
    $borders_color:         #161616;
    $separator_color:       #383838;
    $header_bg_backdrop:    #292929;
    $header_border:         #1A1A1A;
    $header_highlight:      #3A3A3A;
    $osd_bg_color:          #2C2C2E;
    $entry_border:          #3C3C3C;
    $fg_color:              transparentize($opposite, 0.12);
    $header_entry_bg:       transparentize(white, 0.92);
    $header_entry_border:   transparentize(white, 0.9);
    $button_bg:             #454545;
    $insensitive_bg_color:  lighten($bg_color, 2%);
    $header_button_bg:      transparentize(white, 0.9);
    $header_button_border:  transparentize(black, 0.6);
    $trough_color_treeview: #3A3A3A;
    $trough_color:          #3A3A3A;
    $wm_title_unfocused:    #7A7A7A;
    $wm_button_hover_bg:    #4C4C50;
    $wm_button_active_bg:   #949498;
    $wm_icon_bg:            #909090;
    $wm_icon_unfocused_bg:  #4D4D4F;
    $wm_icon_hover_bg:      #C4C7CC;
}""",
}

GTK_VARS = {
    "$accent_color": "if($variant == 'light', {L}, {D})",
    "$selected_fg_color": "{FG}",
    "$link_color": "if($variant == 'light', {TL}, {TD})",
    "$link_visited_color": "$link_color",
    "$warning_color": "#FF9500",
    "$error_color": "#FF3B30",
    "$success_color": "#34C759",
    "$destructive_color": "#FF3B30",
    "$suggested_color": "$accent_color",
    "$question_color": "$accent_color",
}

CIN_PALETTE = {
    "light": """@if $variant == 'light' {
    // Monterra hell
    $bg_color: #F2F2F2;
    $bg_color2: darken($bg_color, 8%);
    $bg_color3: darken($bg_color, 20%);
    $bg_color4: darken($bg_color, 14%);
    $panel_bg: #F6F6F6;
    $panel_active_bg: $bg_color2;
    $borders_color: darken($bg_color, 18%);
    $separator_color: darken($bg_color, 12%);
    $text_color: #1D1D1F;
    $panel_fg: #1D1D1F;
    $fg_color: #1D1D1F;
    $noaccent_selected_fg_color: $text_color;
    $dim_color: lighten($text_color, 30%);
    $link_color: {TL};
    $osd_destructive_color: #FF3B30;
    $insensitive_fg_color: transparentize($fg_color, 0.45);
    $entry_border: #C9C9C9;
    $button_bg: $bg_color3;
    $corner_bar_highlighted: darken($borders_color, 10%);
}""",
    "dark": """@else {
    // Monterra dunkel
    $bg_color: #2A2A2C;
    $bg_color2: lighten($bg_color, 6%);
    $bg_color3: lighten($bg_color, 14%);
    $bg_color4: lighten($bg_color, 9%);
    $panel_bg: #1F1F21;
    $panel_active_bg: $bg_color3;
    $borders_color: $bg_color2;
    $separator_color: lighten($bg_color, 4%);
    $panel_fg: #F2F2F2;
    $text_color: #E6E6E6;
    $fg_color: #EDEDED;
    $noaccent_selected_fg_color: #ffffff;
    $dim_color: darken($text_color, 25%);
    $link_color: {TD};
    $osd_destructive_color: #FF453A;
    $insensitive_fg_color: transparentize($fg_color, 0.55);
    $entry_border: $borders_color;
    $button_bg: $bg_color2;
    $corner_bar_highlighted: lighten($borders_color, 10%);
}""",
}

CIN_VARS = {
    "$accent_color": "if($variant == 'light', {L}, {D})",
    "$selected_fg_color": "{FG}",
    "$radius": "8px",
    "$warning_color": "#FF9500",
    "$error_color": "#FF3B30",
    "$destructive_color": "#FF3B30",
    "$tooltip_bg_color": "if($variant == 'light', rgba(246, 246, 246, 0.97), rgba(44, 44, 46, 0.97))",
    "$tooltip_fg_color": "if($variant == 'light', #1D1D1F, #F2F2F2)",
}

# Radien: gleiche Stellen wie Mint-Y, nur etwas runder (0 bleibt 0 → verbundene Knöpfe stimmen)
GTK_RADII = {"2px": "5px", "3px": "6px", "4px": "7px", "5px": "7px", "8px": "10px"}
CIN_RADII = {"2px": "5px", "3px": "6px", "5px": "7px"}


# --------------------------------------------------------------- Akzent als Schriftfarbe
def _rgb(h):
    return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def _hex(c):
    return "#%02X%02X%02X" % tuple(round(max(0, min(1, v)) * 255) for v in c)


def _lum(c):
    return sum(w * (v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
               for w, v in zip((0.2126, 0.7152, 0.0722), c))


def _contrast(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def text_accent(colour, bg, dark):
    """Akzentfarbe so weit abdunkeln (hell) bzw. aufhellen (dunkel), dass sie als Schrift
    auf dem Fensterhintergrund lesbar ist (Kontrast ≥ 4,5 : 1)."""
    c, b = _rgb(colour), _rgb(bg)
    for _ in range(100):
        if _contrast(c, b) >= 4.5:
            break
        c = [v + (1 - v) * 0.05 for v in c] if dark else [v * 0.95 for v in c]
    return _hex(c)


TEXT_LIGHT = text_accent(ACC["light"], "#F2F2F2", False)
TEXT_DARK = text_accent(ACC["dark"], "#282828", True)


# --------------------------------------------------------------- Hilfen
def fmt(v):
    return v.format(L=ACC["light"], D=ACC["dark"], FG=ACC["fg"], TL=TEXT_LIGHT, TD=TEXT_DARK)


def fmt_braces(block):
    """nur die Platzhalter {TL}/{TD} ersetzen – die übrigen geschweiften Klammern bleiben"""
    return block.replace("{TL}", TEXT_LIGHT).replace("{TD}", TEXT_DARK)


def add_var(path: Path, line: str):
    with open(path, "a") as f:
        f.write("\n" + fmt(line) + "\n")


def set_vars(path: Path, table: dict):
    text = path.read_text()
    for var, val in table.items():
        text, n = re.subn(rf"^(\s*){re.escape(var)}:[^;\n]*;", lambda m: f"{m.group(1)}{var}: {fmt(val)};",
                          text, flags=re.M)
        if n == 0:
            raise SystemExit(f"{path}: Variable {var} nicht gefunden")
    path.write_text(text)


def set_palette(path: Path, palette: dict):
    text = path.read_text()
    light, dark = fmt_braces(palette["light"]), fmt_braces(palette["dark"])
    text, a = re.subn(r"@if \$variant == 'light' \{.*?\n\}", lambda _m: light, text, count=1, flags=re.S)
    text, b = re.subn(r"@else \{.*?\n\}", lambda _m: dark, text, count=1, flags=re.S)
    if not (a and b):
        raise SystemExit(f"{path}: Farbblöcke nicht gefunden")
    path.write_text(text)


def remap_radii(path: Path, table: dict):
    lines = []
    for line in path.read_text().splitlines(keepends=True):
        if "radius" in line:
            line = re.sub(r"\b(\d+px)\b", lambda m: table.get(m.group(1), m.group(1)), line)
        lines.append(line)
    path.write_text("".join(lines))


def replace_accent_text(root: Path, colour: str):
    for f in root.rglob("*"):
        if f.is_file() and f.suffix in (".svg", ".rc", ".css", ".scss", ".ini", "") and not f.name.endswith(".png"):
            try:
                t = f.read_text()
            except UnicodeDecodeError:
                continue
            n = re.sub(MINT_ACCENT, colour, t, flags=re.I)
            if n != t:
                f.write_text(n)


def _hsv(rgb):
    rgb = rgb.astype(float) / 255
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    s = np.where(mx > 0, d / np.maximum(mx, 1e-9), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx)
    m = d > 0
    rc = np.where(m, (mx - r) / np.maximum(d, 1e-9), 0)
    gc = np.where(m, (mx - g) / np.maximum(d, 1e-9), 0)
    bc = np.where(m, (mx - b) / np.maximum(d, 1e-9), 0)
    h = np.select([r == mx, g == mx], [bc - gc, 2 + rc - bc], 4 + gc - rc)
    h = np.where(m, (h / 6) % 1, 0)
    return h, s, mx


def recolor_png(path: Path, colour: str):
    """Mint-Grün in Rasterbildern auf die Akzentfarbe umstellen (Form und Alpha bleiben)."""
    img = Image.open(path).convert("RGBA")
    a = np.array(img)
    h, s, v = _hsv(a[..., :3])
    src = np.array([[int(MINT_ACCENT[i:i + 2], 16) for i in (1, 3, 5)]], dtype=np.uint8)
    sh, ss, sv = (x[0] for x in _hsv(src))
    tgt = np.array([[int(colour[i:i + 2], 16) for i in (1, 3, 5)]], dtype=np.uint8)
    th, ts, tv = (x[0] for x in _hsv(tgt))
    dh = np.minimum(abs(h - sh), 1 - abs(h - sh))
    mask = (a[..., 3] > 0) & (s > 0.12) & (dh < 0.09)
    if not mask.any():
        return False
    ns = np.clip(s * ts / ss, 0, 1)
    nv = np.clip(v * tv / sv, 0, 1)
    i = np.floor(th * 6).astype(int) % 6
    f = th * 6 - np.floor(th * 6)
    p, q, t = nv * (1 - ns), nv * (1 - ns * f), nv * (1 - ns * (1 - f))
    rgb = [(nv, t, p), (q, nv, p), (p, nv, t), (p, q, nv), (t, p, nv), (nv, p, q)][i]
    for c in range(3):
        a[..., c] = np.where(mask, np.round(rgb[c] * 255), a[..., c])
    Image.fromarray(a).save(path)
    return True


def sass(src: str, dst: str, cwd: Path):
    subprocess.run(["pysassc", src, dst], cwd=cwd, check=True)


def append_layer(scss: Path, layer: str):
    with open(scss, "a") as f:
        f.write(f"\n// Monterra-Schicht\n@import '{layer}';\n")


# --------------------------------------------------------------- Vorbereiten
def prepare():
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    for part in ("gtk-2.0", "gtk-3.0", "gtk-4.0", "cinnamon", "metacity-1"):
        shutil.copytree(MINT / part, WORK / part)
    for d in list(MINT.glob("libadwaita-*")) + list(MINT.glob("libadapta-*")):
        shutil.copytree(d, WORK / d.name)

    # GTK 3 / 4
    for ver, layer in (("gtk-3.0", "gtk3"), ("gtk-4.0", "gtk4")):
        s = WORK / ver / "sass"
        set_palette(s / "_colors.scss", GTK_PALETTE)
        set_vars(s / "_colors.scss", GTK_VARS)
        add_var(s / "_colors.scss", "$monterra_accent_text: if($variant == 'light', {TL}, {TD});")
        remap_radii(s / "_common.scss", GTK_RADII)
        shutil.copy(HERE / "layers" / f"_{layer}.scss", s / "_monterra.scss")
        append_layer(s / "gtk.scss", "monterra")
        append_layer(s / "gtk-dark.scss", "monterra")
        for p in (WORK / ver / "assets").glob("*.png"):
            recolor_png(p, ACC["dark"] if "-dark" in p.name else ACC["light"])
        replace_accent_text(WORK / ver / "assets", ACC["light"])
        sass("sass/gtk.scss", "gtk.css", WORK / ver)
        sass("sass/gtk-dark.scss", "gtk-dark.css", WORK / ver)

    # Cinnamon
    c = WORK / "cinnamon"
    set_palette(c / "sass" / "_colors.scss", CIN_PALETTE)
    set_vars(c / "sass" / "_colors.scss", CIN_VARS)
    add_var(c / "sass" / "_colors.scss", "$monterra_accent_text: if($variant == 'light', {TL}, {TD});")
    for f in (c / "sass").glob("_*.scss"):
        if f.name != "_colors.scss":
            remap_radii(f, CIN_RADII)
    shutil.copy(HERE / "layers" / "_cinnamon.scss", c / "sass" / "_monterra.scss")
    append_layer(c / "sass" / "cinnamon.scss", "monterra")
    append_layer(c / "sass" / "cinnamon-dark.scss", "monterra")
    replace_accent_text(c / "common-assets", ACC["light"])
    replace_accent_text(c / "light-assets", ACC["light"])
    replace_accent_text(c / "dark-assets", ACC["dark"])
    sass("sass/cinnamon.scss", "cinnamon.css", c)
    sass("sass/cinnamon-dark.scss", "cinnamon-dark.css", c)

    # GTK 2 (ältere Programme)
    g2 = WORK / "gtk-2.0"
    replace_accent_text(g2, ACC["light"])
    for p in list((g2 / "assets").glob("*.png")) + list((g2 / "assets-dark").glob("*.png")):
        recolor_png(p, ACC["light"])

    # libadwaita / libadapta: nur die Akzentfarbe
    for d in list(WORK.glob("libadwaita-*")) + list(WORK.glob("libadapta-*")):
        replace_accent_text(d, ACC["light"])


# --------------------------------------------------------------- Zusammenstellen
INDEX = """[Desktop Entry]
Type=X-GNOME-Metatheme
Name={name}
Comment=Elegantes Theme für Cinnamon (auf Basis von Mint-Y)
Encoding=UTF-8

[X-GNOME-Metatheme]
GtkTheme={name}
MetacityTheme={name}
IconTheme=Monterra
CursorTheme=Monterra-Cursor
ButtonLayout=close,minimize,maximize:
"""


def assemble(dark: bool):
    name = f"{NAME}-Dark" if dark else NAME
    variant = "dark" if dark else "light"
    dest = DIST / name
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    (dest / "index.theme").write_text(INDEX.format(name=name))

    # GTK 2 – wie Mint-Y
    g2 = dest / "gtk-2.0"
    g2.mkdir()
    shutil.copytree(WORK / "gtk-2.0" / ("assets-dark" if dark else "assets"), g2 / "assets")
    for f in (WORK / "gtk-2.0").glob("*.rc"):
        shutil.copy(f, g2)
    shutil.copy(WORK / "gtk-2.0" / ("gtkrc-dark" if dark else "gtkrc"), g2 / "gtkrc")
    if dark:
        shutil.copy(WORK / "gtk-2.0" / "menubar-toolbar-dark.rc", g2 / "menubar-toolbar.rc")

    # GTK 3 / 4 – wie Mint-Y; die dunkle Fassung nutzt gtk-dark.css als gtk.css
    for ver in ("gtk-3.0", "gtk-4.0"):
        d = dest / ver
        shutil.copytree(WORK / ver / "assets", d / "assets")
        shutil.copy(WORK / ver / ("gtk-dark.css" if dark else "gtk.css"), d / "gtk.css")
        shutil.copy(WORK / ver / "gtk-dark.css", d / "gtk-dark.css")
    buttons.apply(dest, buttons.STANDARD)

    # Fensterrahmen für andere Fenstermanager (Muffin liest die GTK-3-Datei)
    shutil.copytree(WORK / "metacity-1", dest / "metacity-1")
    xml = dest / "metacity-1" / "metacity-theme-3.xml"
    xml.write_text(xml.read_text().replace("<name>Mint-Y</name>", f"<name>{name}</name>"))

    # Cinnamon
    c = dest / "cinnamon"
    c.mkdir()
    shutil.copytree(WORK / "cinnamon" / "common-assets", c / "common-assets")
    shutil.copytree(WORK / "cinnamon" / f"{variant}-assets", c / f"{variant}-assets")
    shutil.copy(WORK / "cinnamon" / ("cinnamon-dark.css" if dark else "cinnamon.css"), c / "cinnamon.css")

    for src, dst in ((f"cinnamon-{variant}.png", c / "thumbnail.png"),
                     (f"gtk-{variant}.png", dest / "gtk-3.0" / "thumbnail.png"),
                     (f"metacity-{variant}.png", dest / "metacity-1" / "thumbnail.png")):
        if (HERE / "previews" / src).exists():
            shutil.copy(HERE / "previews" / src, dst)

    for d in list(WORK.glob("libadwaita-*")) + list(WORK.glob("libadapta-*")):
        shutil.copytree(d, dest / d.name)
    return dest


if __name__ == "__main__":
    prepare()
    for dark in (False, True):
        print("fertig:", assemble(dark))
