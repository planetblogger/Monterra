#!/usr/bin/python3
"""
Monterra – Symbole für Web-Apps (Linux Mint "Web-Apps" / webapp-manager)

  python3 werkzeuge/webapps.py apply      Symbole aller Web-Apps im Monterra-Stil setzen
  python3 werkzeuge/webapps.py apply --new   nur neue oder geänderte Web-Apps
  python3 werkzeuge/webapps.py restore    ursprüngliche Starter und Symbole wiederherstellen
  python3 werkzeuge/webapps.py frame BILD AUSGABE.png [cover|fit]
                                         ein beliebiges Bild in die Monterra-Form bringen

Was "apply" macht:
  * Eigene Logo-Bilder (Icon=/pfad/zum/bild.png) werden in die abgerundete Monterra-Form
    gebracht (gleiche Größe, gleicher Schatten wie die übrigen Monterra-Symbole).
  * Symbole aus dem Theme (z. B. web-reddit) werden ebenso eingerahmt.
  * Web-Apps ohne eigenes Logo bekommen passende Monterra-Symbole:
    NAS, Router, Smart Home, KI-Bild – oder die Monterra-Weltkugel.
  * Die Originale bleiben unverändert; die bisherigen Starter werden gesichert.
Nur der eigene Benutzer ist betroffen, es ist kein sudo nötig.
"""
import configparser
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gi
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402
from monterra_iconframe import frame  # noqa: E402

HOME = Path.home()
APPS = HOME / ".local/share/applications"
ICON_DIR = HOME / ".local/share/icons/hicolor/256x256/apps"
STATE = HOME / ".local/share/monterra-webapps"
BACKUP = STATE / "backup"

# Web-Apps ohne eigenes Logo -> Monterra-Symbol (Prüfung auf Name und Adresse)
GENERIC_RULES = [
    (r"synology\s*ds|diskstation|\bnas\b|:5000|:5001|:65001", "monterra-webapp-nas"),
    (r"router|rt\d{3,4}|fritz|192\.168\.\d+\.1(:|/|$)", "monterra-webapp-router"),
    (r"deconz|phoscon|zigbee|home.?assistant|hue|smart.?home", "monterra-webapp-smarthome"),
    (r"magnific|freepik|midjourney|leonardo|ideogram|krea|firefly", "monterra-webapp-ai"),
]
GENERIC_THEME_ICONS = {"webapp-manager", "web-browser", "modem", "applications-internet",
                       "imagemagick", "", None}

# ---------------------------------------------------------------- desktop files
def read_desktop(p):
    cp = configparser.RawConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    cp.read(p, encoding="utf-8")
    return cp["Desktop Entry"] if cp.has_section("Desktop Entry") else {}


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "webapp"


def current_icon_theme():
    try:
        from gi.repository import Gio
        return Gio.Settings.new("org.cinnamon.desktop.interface").get_string("icon-theme")
    except Exception:
        return "Monterra"


def theme_icon_file(name):
    """Look an icon name up in the current theme (falls back to Mint-Y)."""
    for theme in (None, "Mint-Y"):
        it = Gtk.IconTheme.new()
        it.set_custom_theme(theme or current_icon_theme())
        info = it.lookup_icon(name, 256, Gtk.IconLookupFlags.FORCE_SIZE)
        fn = info.get_filename() if info else None
        if fn and os.path.isfile(fn) and "/Monterra" not in fn:
            return fn
    return None


def set_icon(path, icon):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^Icon=.*$", f"Icon={icon}", text, flags=re.M)
    text = re.sub(r'XAPP_FORCE_GTKWINDOW_ICON="[^"]*"', f'XAPP_FORCE_GTKWINDOW_ICON="{icon}"', text)
    path.write_text(text, encoding="utf-8")


def apply(only_new=False):
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP.mkdir(parents=True, exist_ok=True)
    files = sorted(APPS.glob("WebApp-*.desktop"))
    if not files:
        print("Keine Web-Apps gefunden (~/.local/share/applications/WebApp-*.desktop).")
        return
    done = 0
    for p in files:
        bak = BACKUP / p.name
        cur_icon = read_desktop(p).get("Icon", "")
        already = cur_icon.startswith("monterra-webapp")
        if only_new and already:
            continue
        if not bak.exists() or not already:
            shutil.copy2(p, bak)                   # new or changed in the Web-App manager
        done += 1
        e = read_desktop(bak)                      # always start from the original
        name = e.get("Name", p.stem)
        url = e.get("X-WebApp-URL", "")
        icon = e.get("Icon", "")
        hay = f"{name} {url}".lower()
        new = None
        if icon.startswith("/") and Path(icon).exists():
            out = ICON_DIR / f"monterra-webapp-{slug(name)}.png"
            frame(icon, out)
            new = out.stem
            how = "Logo eingerahmt"
        elif icon and icon not in GENERIC_THEME_ICONS and theme_icon_file(icon):
            out = ICON_DIR / f"monterra-webapp-{slug(name)}.png"
            frame(theme_icon_file(icon), out)
            new = out.stem
            how = f"Theme-Symbol '{icon}' eingerahmt"
        if new is None:
            new = next((ic for rx, ic in GENERIC_RULES if re.search(rx, hay)), "monterra-webapp-default")
            how = "Monterra-Symbol"
        shutil.copy2(bak, p)
        set_icon(p, new)
        print(f"  {name:<22} → {new:<36} ({how})")
    subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(ICON_DIR.parent.parent)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["update-desktop-database", str(APPS)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if only_new and not done:
        return 0
    print("\nFertig. Das Menü aktualisiert sich nach wenigen Sekunden; im Panel ggf. Cinnamon neu laden (Alt+F2, r).")
    print("Rückgängig: python3 werkzeuge/webapps.py restore")


def restore():
    if not BACKUP.exists():
        print("Keine Sicherung gefunden – es wurde noch nichts geändert.")
        return
    for bak in BACKUP.glob("*.desktop"):
        target = APPS / bak.name
        if target.exists():
            shutil.copy2(bak, target)
            print("  wiederhergestellt:", bak.name)
    for f in ICON_DIR.glob("monterra-webapp-*.png"):
        f.unlink()
    shutil.rmtree(STATE)
    subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(ICON_DIR.parent.parent)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Ursprüngliche Web-App-Symbole wiederhergestellt.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "apply":
        apply(only_new="--new" in sys.argv)
    elif cmd == "restore":
        restore()
    elif cmd == "frame" and len(sys.argv) >= 4:
        frame(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "auto")
        print("geschrieben:", sys.argv[3])
    else:
        print(__doc__)
