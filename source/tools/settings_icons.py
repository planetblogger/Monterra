#!/usr/bin/env python3
"""
Monterra – colourful tile icons for Cinnamon's "System Settings" (cs-* icons).
Colored squircle with a white glyph. Glyphs: Phosphor Icons (MIT), see third_party/phosphor/LICENSE.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
GLYPH_DIR = HERE.parent / "third_party" / "phosphor"

# system colors
C = {
    "blue": "#0A84FF", "indigo": "#5E5CE6", "purple": "#AF52DE", "pink": "#FF375F",
    "red": "#FF453A", "orange": "#FF9F0A", "yellow": "#FFCC00", "green": "#30D158",
    "teal": "#30B0C7", "cyan": "#32ADE6", "brown": "#A2845E", "gray": "#8E8E93",
    "graphite": "#3A3A3C",
}

# icon name -> (color, glyph, transform-extra)
SETTINGS = {
    # Appearance
    "cs-backgrounds":          ("cyan",     "image", ""),
    "cs-themes":               ("graphite", "circle-half", ""),
    "cs-fonts":                ("gray",     "text-aa", ""),
    "cs-desktop":              ("blue",     "desktop", ""),
    "cs-desklets":             ("yellow",   "note", ""),
    "cs-desktop-effects":      ("purple",   "sparkle", ""),
    "cs-applets":              ("blue",     "squares-four", ""),
    "cs-extensions":           ("purple",   "puzzle-piece", ""),
    "cs-panel":                ("graphite", "sidebar-simple", "rotate"),
    "cs-screensaver":          ("teal",     "monitor-play", ""),
    "cs-cat-appearance":       ("purple",   "paint-brush", ""),
    # Preferences
    "cs-general":              ("gray",     "gear", ""),
    "cs-windows":              ("blue",     "app-window", ""),
    "cs-tiling":               ("indigo",   "layout", ""),
    "cs-workspaces":           ("indigo",   "cards", ""),
    "cs-overview":             ("indigo",   "corners-out", ""),
    "cs-gestures":             ("indigo",   "hand-swipe-right", ""),
    "cs-actions":              ("indigo",   "magic-wand", ""),
    "cs-notifications":        ("red",      "bell", ""),
    "cs-default-applications": ("teal",     "list-checks", ""),
    "cs-startup-programs":     ("green",    "rocket-launch", ""),
    "cs-date-time":            ("gray",     "clock", ""),
    "cs-language":             ("blue",     "globe", ""),
    "cs-region":               ("blue",     "globe-hemisphere-west", ""),
    "cs-input-method":         ("orange",   "translate", ""),
    "cs-privacy":              ("blue",     "hand", ""),
    "cs-universal-access":     ("blue",     "person-arms-spread", ""),
    "cs-user":                 ("blue",     "user-circle", ""),
    "cs-online-accounts":      ("blue",     "at", ""),
    "cs-cat-prefs":            ("gray",     "sliders-horizontal", ""),
    # Hardware
    "cs-display":              ("blue",     "monitor", ""),
    "cs-screen":               ("blue",     "frame-corners", ""),
    "cs-nightlight":           ("orange",   "sun-horizon", ""),
    "cs-color":                ("orange",   "palette", ""),
    "cs-sound":                ("pink",     "speaker-high", ""),
    "cs-power":                ("green",    "battery-charging", ""),
    "cs-keyboard":             ("gray",     "keyboard", ""),
    "cs-mouse":                ("gray",     "mouse-simple", ""),
    "cs-tablet":               ("gray",     "pen-nib", ""),
    "cs-printer":              ("gray",     "printer", ""),
    "cs-bluetooth":            ("blue",     "bluetooth", ""),
    "cs-network":              ("blue",     "wifi-high", ""),
    "cs-thunderbolt":          ("orange",   "lightning", ""),
    "cs-cat-hardware":         ("gray",     "cpu", ""),
    # Administration
    "cs-details":              ("gray",     "info", ""),
    "cs-drivers":              ("green",    "graphics-card", ""),
    "cs-firewall":             ("red",      "wall", ""),
    "cs-login":                ("graphite", "lock-key", ""),
    "cs-sources":              ("brown",    "package", ""),
    "cs-user-accounts":        ("blue",     "users-three", ""),
    "cs-cat-admin":            ("gray",     "shield-check", ""),
}

SQUIRCLE = ("M32 5 C50.5 5 59 6.8 59 32 C59 57.2 50.5 59 32 59 "
            "C13.5 59 5 57.2 5 32 C5 6.8 13.5 5 32 5 Z")


def _mix(hexcol, other, t):
    a = [int(hexcol[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def glyph_body(name):
    svg = (GLYPH_DIR / f"{name}-fill.svg").read_text()
    return re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)


def icon_svg(color_key, glyph, extra=""):
    base = C[color_key]
    top = _mix(base, "#FFFFFF", 0.18)
    bottom = _mix(base, "#000000", 0.06)
    rim = _mix(base, "#000000", 0.18)
    size = 34                       # glyph box in px (of 64)
    s = size / 256
    off = (64 - size) / 2
    rot = ' rotate(-90 128 128)' if extra == "rotate" else ""
    glyph_color = "#FFFFFF"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>
  <filter id="sh" x="-20%" y="-20%" width="140%" height="150%">
    <feDropShadow dx="0" dy="1" stdDeviation="1.1" flood-color="#000" flood-opacity="0.28"/></filter>
</defs>
<path filter="url(#sh)" d="{SQUIRCLE}" fill="url(#g)" stroke="{rim}" stroke-opacity=".35" stroke-width=".6"/>
<g transform="translate({off} {off}) scale({s:.5f}){rot}" fill="{glyph_color}">{glyph_body(glyph)}</g>
</svg>
'''


def build(outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for name, (col, glyph, extra) in SETTINGS.items():
        (out / f"{name}.svg").write_text(icon_svg(col, glyph, extra))
    return len(SETTINGS)


def vendor_glyphs(phosphor_fill_dir, license_file):
    """Copy only the glyphs we use (plus license) into third_party/phosphor."""
    import shutil
    GLYPH_DIR.mkdir(parents=True, exist_ok=True)
    for _c, glyph, _e in SETTINGS.values():
        shutil.copy(Path(phosphor_fill_dir) / f"{glyph}-fill.svg", GLYPH_DIR)
    shutil.copy(license_file, GLYPH_DIR / "LICENSE")


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "--vendor":
        vendor_glyphs(sys.argv[2], sys.argv[3])
    else:
        print(build(sys.argv[1]), "settings icons")
