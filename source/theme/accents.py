#!/usr/bin/env python3
"""
Monterra accent colours: 13 system colours as accent (light / dark).
Names are English (Blue, Green, …); German and Spanish names are accepted too.

Helle Farben werden so weit abgedunkelt, dass weiße Schrift darauf gut lesbar
bleibt (Kontrast ≥ 3:1). Gelb bleibt gelb und bekommt dunkle Schrift.

  accent.py NAME            -> Werte als Shell-Variablen (für die Werkzeuge)
  accent.py --list          -> alle Namen
  accent.py --css NAME DATEI…  -> Firefox-/Thunderbird-CSS auf die Farbe umstellen
"""
import re
import sys

# name: (light, dark, folder icon theme)
BASE = {
    "Blue":     ("#007AFF", "#0A84FF", "Monterra"),
    "Indigo":   ("#5856D6", "#5E5CE6", "Monterra-Indigo"),
    "Purple":   ("#AF52DE", "#BF5AF2", "Monterra-Purple"),
    "Pink":     ("#FF2D55", "#FF375F", "Monterra-Pink"),
    "Red":      ("#FF3B30", "#FF453A", "Monterra-Red"),
    "Orange":   ("#FF9500", "#FF9F0A", "Monterra-Orange"),
    "Yellow":   ("#FFCC00", "#FFD60A", "Monterra-Yellow"),
    "Green":    ("#34C759", "#30D158", "Monterra-Green"),
    "Teal":     ("#30B0C7", "#40C8E0", "Monterra-Mint"),
    "Cyan":     ("#32ADE6", "#64D2FF", "Monterra-Cyan"),
    "Brown":    ("#A2845E", "#AC8E68", "Monterra-Brown"),
    "Grey":     ("#8E8E93", "#98989D", "Monterra-Graphite"),
    "Graphite": ("#636366", "#7C7C80", "Monterra-Graphite"),
}
NAMES = list(BASE)
DARK_FG = {"Yellow"}          # dark text on the accent


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _hex(c):
    return "#%02X%02X%02X" % tuple(round(max(0, min(1, v)) * 255) for v in c)


def _lum(c):
    lin = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _readable(h, max_lum=0.29):
    """darken (keeping the hue) until white text has a contrast of at least ~3:1"""
    c = _rgb(h)
    while _lum(c) > max_lum:
        c = [v * 0.97 for v in c]
    return _hex(c)


def mix(a, b, t):
    a, b = _rgb(a), _rgb(b)
    return _hex([x + (y - x) * t for x, y in zip(a, b)])


def get(name):
    name = normalize(name)
    light, dark, folders = BASE[name]
    if name in DARK_FG:
        return dict(name=name, light=mix(light, "#000000", 0.06), dark=dark, fg="#1D1D1F", folders=folders)
    return dict(name=name, light=_readable(light), dark=_readable(dark, 0.29), fg="#FFFFFF", folders=folders)


def normalize(name):
    n = name.strip().replace("ü", "ue").replace("Ü", "Ue").capitalize()
    aliases = {"Gray": "Grey",
               # Deutsch (frühere Versionen)
               "Blau": "Blue", "Lila": "Purple", "Rot": "Red", "Gelb": "Yellow", "Gruen": "Green",
               "Petrol": "Teal", "Braun": "Brown", "Grau": "Grey", "Graphit": "Graphite",
               # Español
               "Azul": "Blue", "Índigo": "Indigo", "Morado": "Purple", "Rosa": "Pink", "Rojo": "Red",
               "Naranja": "Orange", "Amarillo": "Yellow", "Verde": "Green", "Verde azulado": "Teal",
               "Verde-azulado": "Teal", "Cian": "Cyan", "Marrón": "Brown", "Marron": "Brown",
               "Gris": "Grey", "Grafito": "Graphite"}
    n = aliases.get(n, n)
    if n not in BASE:
        raise SystemExit(f"Unknown accent colour: {name}  (available: {', '.join(NAMES)})")
    return n


def rgba(h, a):
    r, g, b = (round(v * 255) for v in _rgb(h))
    return f"rgba({r}, {g}, {b}, {a})"


# The Firefox/Thunderbird styles are written for the blue accent; these are the values to replace.
def css_map(name):
    a = get(name)
    lt, dk = a["light"], a["dark"]
    return {
        "#007AFF": lt, "#0A84FF": dk,
        "#0068DA": mix(lt, "#000000", 0.12), "#0057B8": mix(lt, "#000000", 0.25),
        "#2E97FF": mix(dk, "#FFFFFF", 0.15), "#57ABFF": mix(dk, "#FFFFFF", 0.30),
        "rgba(0, 122, 255,": rgba(lt, "")[:-3] + ",", "rgba(10, 132, 255,": rgba(dk, "")[:-3] + ",",
        "--mt-accent-fg: #FFFFFF": "--mt-accent-fg: " + a["fg"],
    }


def rewrite_css(name, files):
    m = css_map(name)
    low = {k.lower(): v for k, v in m.items()}
    pat = re.compile("|".join(re.escape(k) for k in sorted(m, key=len, reverse=True)), re.I)
    for f in files:
        t = open(f, encoding="utf-8").read()
        t = pat.sub(lambda mo: low[mo.group(0).lower()], t)
        open(f, "w", encoding="utf-8").write(t)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        print(" ".join(NAMES))
    elif len(sys.argv) > 2 and sys.argv[1] == "--css":
        rewrite_css(sys.argv[2], sys.argv[3:])
    elif len(sys.argv) > 1:
        a = get(sys.argv[1])
        for k, v in a.items():
            print(f"AKZENT_{k.upper()}='{v}'")
    else:
        for n in NAMES:
            print(n, get(n))
