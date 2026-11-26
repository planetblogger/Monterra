#!/usr/bin/env python3
"""
Monterra – Größe der Fensterknöpfe (Ampel) als CSS-Block.

Der Block steht am Ende von gtk-3.0/gtk.css und gtk-4.0/gtk.css zwischen zwei
Markierungen. Cinnamons Fenstermanager (Muffin) liest für die Systemrahmen dieselbe
GTK-3-CSS-Datei – die Größe gilt also für alle Fenster.

  buttons.py GRÖSSE THEME_ORDNER…     Block in den Themes ersetzen
  GRÖSSE = Wert des Schiebereglers (14–32, gerade); der Kreis ist 2 px kleiner
  (Standard 16 → Kreis 14 px).
"""
import re
import sys
from pathlib import Path

START = "/* monterra-knoepfe: anfang */"
END = "/* monterra-knoepfe: ende */"
STANDARD = 14


def gtk3_block(n):
    scale = n / 18                             # Symbol beim Überfahren (16-px-Symbol)
    sel = ",\n".join(f"{p} button.titlebutton.{k}"
                     for p in ("headerbar", ".titlebar") for k in ("close", "minimize", "maximize"))
    # GTK zeichnet das Symbol als eigenes Bild im Knopf, Muffin direkt mit dem Knopf-Stil
    img = ",\n".join(f"{p} button.titlebutton.{k} image"
                      for p in ("headerbar", ".titlebar") for k in ("close", "minimize", "maximize"))
    ssd = ",\n".join(f".titlebar.default-decoration button.titlebutton.{k}"
                      for k in ("close", "minimize", "maximize"))
    return (f"{START}\n{sel} {{\n"
            f"  min-width: {n}px;\n  min-height: {n}px;\n"
            f"  padding: 0 {max(3, n // 4)}px;\n"
            f"  background-size: {n}px {n}px;\n}}\n"
            f"{img} {{ -gtk-icon-transform: scale({n / 15:.3f}); }}\n"
            f"{ssd} {{ -gtk-icon-transform: scale({scale:.3f}); }}\n{END}\n")


def gtk4_block(n):
    glyph = round(n * 0.62)
    sel = ",\n".join(f"windowcontrols > button.{k}" for k in ("close", "minimize", "maximize"))
    return (f"{START}\n{sel} {{\n"
            f"  min-width: {n}px;\n  min-height: {n}px;\n"
            f"  padding: 0 {max(3, n // 4)}px;\n"
            f"  background-size: {n}px {n}px;\n}}\n"
            f"windowcontrols > button > image {{ -gtk-icon-size: {glyph}px; }}\n{END}\n")


def write(css: Path, block: str):
    text = css.read_text()
    pat = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)
    text = pat.sub("", text).rstrip("\n") + "\n\n" + block
    # über eine neue Datei ersetzen: die Akzent-Themes teilen sich unveränderte Dateien
    # per Hardlink – so bleibt jede Datei eigenständig
    tmp = css.with_name(css.name + ".neu")
    tmp.write_text(text)
    tmp.replace(css)


def apply(theme_dir: Path, n: int):
    for ver, fn in (("gtk-3.0", gtk3_block), ("gtk-4.0", gtk4_block)):
        for name in ("gtk.css", "gtk-dark.css"):
            css = theme_dir / ver / name
            if css.is_file():
                write(css, fn(n))


if __name__ == "__main__":
    size = int(sys.argv[1])
    size = max(14, min(32, size - size % 2))
    for d in sys.argv[2:]:
        apply(Path(d), size - 2)
    print(size)
