#!/usr/bin/env python3
"""Build Monterra's Firefox look (userChrome.css / userContent.css)."""
import sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from titlebuttons import COLORS, BACKDROP, glyph, svg, shade

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "firefox/chrome")


def uri(s):
    return 'url("data:image/svg+xml,' + urllib.parse.quote(s.strip(), safe=" =:/',.()-") + '")'


tl = {}
for name, (fill, border, gcol) in COLORS.items():
    tl[name] = uri(svg(fill, border))
    tl[name + "-hover"] = uri(svg(fill, border, glyph(name, gcol)))
    tl[name + "-active"] = uri(svg(shade(fill, 0.82), shade(border, 0.82), glyph(name, gcol)))
fill, border, gcol = COLORS["maximize"]
tl["restore-hover"] = uri(svg(fill, border, glyph("unmaximize", gcol)))
tl["restore-active"] = uri(svg(shade(fill, 0.82), shade(border, 0.82), glyph("unmaximize", gcol)))
tl["backdrop-light"] = uri(svg(*BACKDROP["light"]))
tl["backdrop-dark"] = uri(svg(*BACKDROP["dark"]))

TEMPLATE = (Path(__file__).parent / "firefox_userChrome.template.css").read_text()
css = TEMPLATE
for k, v in tl.items():
    css = css.replace("@@" + k + "@@", v)
assert "@@" not in css, "unreplaced placeholder"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "userChrome.css").write_text(css)
(OUT / "userContent.css").write_text((Path(__file__).parent / "firefox_userContent.css").read_text())
print("written", OUT)
