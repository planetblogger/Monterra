#!/usr/bin/python3
"""
Monterra – einheitliche Programmsymbole (Firefox, Thunderbird, Discord, Hypnotix, VacuumTube …)

  python3 werkzeuge/programmsymbole.py preview            Vorher-Nachher-Bild erzeugen, nichts ändern
  python3 werkzeuge/programmsymbole.py apply              alle Programme im Menü anpassen
  python3 werkzeuge/programmsymbole.py apply --only firefox,thunderbird
  python3 werkzeuge/programmsymbole.py apply --skip steam,code
  python3 werkzeuge/programmsymbole.py apply --new        nur Programme, die noch kein Monterra-Symbol haben
  python3 werkzeuge/programmsymbole.py restore            alles rückgängig machen

Die Firmenlogos werden nicht nachgezeichnet: Das Werkzeug nimmt das Symbol, das auf deinem
Rechner bereits angezeigt wird, und bringt es in die abgerundete Monterra-Form (gleiche Größe,
gleicher Schatten wie die übrigen Monterra-Symbole). Ergebnis: ein kleines Symbol-Theme
~/.icons/Monterra-Local, das Monterra automatisch bevorzugt. Systemdateien bleiben unberührt.
"""
import configparser
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cairo  # noqa: E402
import gi  # noqa: E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402
import monterra_iconframe as mf  # noqa: E402

HOME = Path.home()
LOCAL = HOME / ".icons" / "Monterra-Local"
MONTERRA = HOME / ".icons" / "Monterra"
BASE_THEME = "Mint-Y"     # what Monterra inherits from

DATA_DIRS = [Path(p) for p in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if p]
DATA_DIRS = [HOME / ".local/share", HOME / ".local/share/flatpak/exports/share",
             Path("/var/lib/flatpak/exports/share"), Path("/var/lib/snapd/desktop")] + DATA_DIRS

INDEX = """[Icon Theme]
Name=Monterra-Local
Comment=Programmsymbole in Monterra-Form (erzeugt von programmsymbole.py)
Hidden=true
Directories=apps/256

[apps/256]
Context=Applications
Size=256
MinSize=16
MaxSize=512
Type=Scalable
"""


def monterra_names():
    names = set()
    for d in ("apps/scalable", "categories/scalable", "places/scalable", "symbolic"):
        p = MONTERRA / d
        if p.exists():
            names |= {f.stem for f in p.iterdir()}
    return names


def menu_apps():
    seen, apps = set(), []
    for base in DATA_DIRS:
        d = base / "applications"
        try:
            if not d.is_dir():
                continue
            files = sorted(d.rglob("*.desktop"))
        except OSError:          # z. B. Ordner ohne Leserechte
            continue
        for f in files:
            if f.name in seen:
                continue
            seen.add(f.name)
            cp = configparser.RawConfigParser(strict=False, interpolation=None)
            cp.optionxform = str
            try:
                cp.read(f, encoding="utf-8")
            except Exception:
                continue
            if not cp.has_section("Desktop Entry"):
                continue
            e = cp["Desktop Entry"]
            if e.get("Type", "Application") != "Application":
                continue
            if e.get("NoDisplay", "false").lower() == "true" or e.get("Hidden", "false").lower() == "true":
                continue
            if f.name.startswith("WebApp-"):
                continue                      # handled by webapps.py
            icon = e.get("Icon", "").strip()
            if not icon or icon.startswith("/") or icon.endswith("-symbolic"):
                continue
            apps.append((e.get("Name", f.stem), icon))
    return apps


def source_icon(name):
    it = Gtk.IconTheme.new()
    it.set_custom_theme(BASE_THEME)
    for n in (name, name.lower()):
        info = it.lookup_icon(n, 256, Gtk.IconLookupFlags.FORCE_SIZE)
        if info and not info.is_symbolic():
            fn = info.get_filename()
            if mf.is_real_file(fn) and "/Monterra" not in fn:
                return fn
    return None


def select(args):
    only = skip = None
    if "--only" in args:
        only = set(args[args.index("--only") + 1].split(","))
    if "--skip" in args:
        skip = set(args[args.index("--skip") + 1].split(","))
    own = monterra_names()
    custom = LOCAL / "eigene-symbole.txt"           # mit der Symbolwerkstatt gestaltet -> nie überschreiben
    if custom.exists():
        own |= set(custom.read_text().split())
    todo, seen = [], set()
    for title, icon in menu_apps():
        if icon in seen or icon in own:
            continue
        if only and icon not in only and title.lower() not in {o.lower() for o in only}:
            continue
        if skip and (icon in skip or title.lower() in {s.lower() for s in skip}):
            continue
        src = source_icon(icon)
        if src:
            seen.add(icon)
            todo.append((title, icon, src))
    return todo


def set_inherit(enable):
    idx = MONTERRA / "index.theme"
    if not idx.exists():
        return
    t = idx.read_text()
    m = re.search(r"^Inherits=(.*)$", t, re.M)
    parts = [p for p in (m.group(1).split(",") if m else []) if p and p != "Monterra-Local"]
    if enable:
        parts.insert(0, "Monterra-Local")
    t = re.sub(r"^Inherits=.*$", "Inherits=" + ",".join(parts), t, flags=re.M)
    idx.write_text(t)


def refresh_caches():
    for d in (LOCAL, MONTERRA):
        if d.exists():
            subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(d)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def apply(args):
    todo = select(args)
    out = LOCAL / "apps" / "256"
    if "--new" in args:
        todo = [x for x in todo if not (out / f"{x[1]}.png").exists()]
        if not todo:
            print("Keine neuen Programme.")
            return
    if not todo:
        print("Keine passenden Programme gefunden.")
        return
    out.mkdir(parents=True, exist_ok=True)
    (LOCAL / "index.theme").write_text(INDEX)
    done = 0
    for title, icon, src in todo:
        try:
            mode = mf.frame(src, out / f"{icon}.png")
        except Exception as err:
            print(f"  {title:<28} übersprungen ({err.__class__.__name__}: Symbol nicht lesbar)")
            continue
        done += 1
        print(f"  {title:<28} {icon:<40} ({ {'cover': 'Form', 'round': 'Scheibe', 'fit': 'Karte'}[mode] })")
    set_inherit(True)
    refresh_caches()
    print(f"\n{done} Programmsymbole angepasst. Wirksam nach Alt+F2 → r (Cinnamon neu laden).")
    print("Rückgängig: python3 werkzeuge/programmsymbole.py restore")


def preview(args):
    todo = select(args)
    if not todo:
        print("Keine passenden Programme gefunden.")
        return
    tmp = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "monterra-preview"
    tmp.mkdir(exist_ok=True)
    cols, cell = 6, 150
    from gi.repository import Gdk, GdkPixbuf
    ok = []
    for title, icon, src in todo:
        try:
            before = GdkPixbuf.Pixbuf.new_from_file_at_scale(src, 80, 80, True)
            dst = tmp / f"{icon}.png"
            mf.frame(src, dst)
            ok.append((title, before, dst))
        except Exception as err:
            print(f"  übersprungen: {title} ({err.__class__.__name__})")
    rows = (len(ok) + cols - 1) // cols
    sheet = cairo.ImageSurface(cairo.FORMAT_ARGB32, cols * cell * 2, max(rows, 1) * 120 + 20)
    cr = cairo.Context(sheet)
    cr.set_source_rgb(0.93, 0.93, 0.94)
    cr.paint()
    for i, (title, before, dst) in enumerate(ok):
        x, y = (i % cols) * cell * 2, (i // cols) * 120 + 10
        Gdk.cairo_set_source_pixbuf(cr, before, x + 30, y + 10)
        cr.paint()
        after = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(dst), 88, 88, True)
        Gdk.cairo_set_source_pixbuf(cr, after, x + 150, y + 6)
        cr.paint()
        cr.set_source_rgb(0.3, 0.3, 0.32)
        cr.select_font_face("Sans")
        cr.set_font_size(12)
        cr.move_to(x + 30, y + 108)
        cr.show_text(title[:34])
    try:
        pics = Path(subprocess.run(["xdg-user-dir", "PICTURES"], capture_output=True, text=True).stdout.strip())
    except OSError:
        pics = None
    if not pics or not pics.is_dir():
        pics = next((p for p in (HOME / "Bilder", HOME / "Pictures") if p.is_dir()), HOME)
    target = pics / "monterra-programmsymbole-vorschau.png"
    sheet.write_to_png(str(target))
    print(f"Vorschau ({len(ok)} Programme, links vorher, rechts nachher): {target}")


def restore():
    # Menü-Einträge, denen die Symbolwerkstatt einen eigenen Symbolnamen gegeben hat, zurückstellen
    entries = LOCAL / "eigene-eintraege.txt"
    if entries.exists():
        for line in entries.read_text().splitlines():
            if "\t" not in line:
                continue
            path, icon = line.split("\t", 1)
            f = Path(path)
            if f.exists():
                txt = f.read_text(encoding="utf-8")
                f.write_text(re.sub(r"^Icon=monterra-eigen-.*$", f"Icon={icon}", txt, flags=re.M), encoding="utf-8")
    if LOCAL.exists():
        shutil.rmtree(LOCAL)
    set_inherit(False)
    refresh_caches()
    print("Programmsymbole zurückgesetzt. Wirksam nach Alt+F2 → r.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "apply":
        apply(sys.argv[2:])
    elif cmd == "preview":
        preview(sys.argv[2:])
    elif cmd == "restore":
        restore()
    else:
        print(__doc__)
