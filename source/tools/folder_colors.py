#!/usr/bin/env python3
"""
Monterra folder colours for Nemo's "folder-color-switcher".

Every colour is a tiny icon theme (Monterra-<Colour>) that only contains the
recoloured folder icons and inherits everything else from Monterra. A JSON file
in /usr/share/folder-color-switcher/colors.d/ registers them with Nemo.
"""
import colorsys
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import icons  # noqa: E402

# reference palette of the default (blue) Monterra folder
BLUE_REF = {"front_top": "#92D2FB", "front_bot": "#64B9F5", "back_top": "#5DB4F0",
            "back_bot": "#3E98E2", "emblem": "#2F86CF", "hilite": "#8ACFFA", "shadow": "#0B3A66"}

# (menu label – must be a colour name folder-color-switcher translates, theme suffix, base colour)
COLOURS = [
    ("Red",    "Red",      "#FF6B63"),
    ("Orange", "Orange",   "#FFA53A"),
    ("Yellow", "Yellow",   "#FFD23F"),
    ("Green",  "Green",    "#4CD372"),
    ("Teal",   "Mint",     "#2FD3C9"),
    ("Cyan",   "Cyan",     "#3BBFD6"),
    ("Blue",   None,       "#64B9F5"),   # default Monterra
    ("Navy",   "Indigo",   "#6B7BEF"),
    ("Purple", "Purple",   "#C27BEA"),
    ("Pink",   "Pink",     "#FF7EB0"),
    ("Brown",  "Brown",    "#BC9B72"),
    ("Grey",   "Graphite", "#A4A5AB"),
]

OFFSETS = {"front_top": +0.10, "front_bot": 0.0, "back_top": -0.035, "back_bot": -0.11,
           "emblem": -0.19, "hilite": +0.08, "shadow": -0.45}


def _hex2hls(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def _hls2hex(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def palette(base):
    h, l, s = _hex2hls(base)
    pal = {}
    for key, dl in OFFSETS.items():
        ss = s * (0.9 if dl > 0 else 1.0)
        if key == "shadow":
            pal[key] = _hls2hex(h, 0.22, min(s, 0.8))
        else:
            pal[key] = _hls2hex(h, l + dl, ss)
    return pal


def recolour(svg, pal):
    for key, ref in BLUE_REF.items():
        svg = svg.replace(ref, pal[key])
    return svg.replace(icons.EMBLEM_COLOR, pal["emblem"])


INDEX = """[Icon Theme]
Name=Monterra-{suffix}
Comment=Monterra with {suffix} folders (used by Nemo's folder colour switcher)
Inherits=Monterra,Mint-Y,Adwaita,hicolor
Example=folder
Directories=places/scalable

[places/scalable]
Context=Places
Size=64
MinSize=8
MaxSize=512
Type=Scalable
"""


def build(icons_root, json_out):
    root = Path(icons_root)
    entries = []
    for label, suffix, base in COLOURS:
        if suffix is None:
            entries.append({"name": label, "color": base, "theme": "Monterra"})
            continue
        pal = palette(base)
        theme = root / f"Monterra-{suffix}"
        if theme.exists():
            shutil.rmtree(theme)
        places = theme / "places" / "scalable"
        places.mkdir(parents=True)
        (theme / "index.theme").write_text(INDEX.format(suffix=suffix))
        for name, glyph in icons.FOLDERS.items():
            (places / f"{name}.svg").write_text(recolour(icons.folder_svg(glyph), pal))
        entries.append({"name": label, "color": base, "theme": f"Monterra-{suffix}"})
    data = {"styles": [{"name": "Monterra", "icon-themes": entries}]}
    Path(json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(json_out).write_text(json.dumps(data, indent=2) + "\n")
    print(f"{len(entries) - 1} colour themes + {json_out}")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
