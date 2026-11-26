#!/usr/bin/env python3
"""
Monterra icon theme – original SVG icons (folders, trash, core apps).
Everything not drawn here is inherited from Mint-Y / Adwaita / hicolor.
"""
import shutil
import sys


from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/.icons/Monterra")

# --------------------------------------------------------------------- folders
FOLDER_DEFS = """<defs>
  <linearGradient id="back" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#5DB4F0"/><stop offset="1" stop-color="#3E98E2"/></linearGradient>
  <linearGradient id="front" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#92D2FB"/><stop offset="1" stop-color="#64B9F5"/></linearGradient>
  <filter id="sh" x="-20%" y="-20%" width="140%" height="150%">
    <feDropShadow dx="0" dy="1" stdDeviation="1" flood-color="#0B3A66" flood-opacity="0.25"/></filter>
</defs>"""

FOLDER_BODY = """<g filter="url(#sh)">
  <path d="M8 12.5 C8 11.1 9.1 10 10.5 10 H24.2 C25.1 10 25.9 10.4 26.4 11.1 L28.6 14 H53.5 C54.9 14 56 15.1 56 16.5 V50 H8 Z" fill="url(#back)"/>
  <rect x="6" y="19" width="52" height="35" rx="3.2" fill="url(#front)"/>
  <rect x="6.6" y="19.6" width="50.8" height="1.2" rx="0.6" fill="#FFFFFF" opacity="0.55"/>
</g>"""

EMBLEM_COLOR = "#2F86CF"

GLYPHS = {
    "home": '<path d="M32 28.5 L22.5 36.5 H25.5 V45 H30 V39.5 H34 V45 H38.5 V36.5 H41.5 Z" />',
    "desktop": '<rect x="22.5" y="29" width="19" height="12.5" rx="1.6"/><rect x="28.5" y="42.5" width="7" height="1.6" rx=".6"/>'
               '<rect x="26" y="44.2" width="12" height="1.6" rx=".8"/>',
    "documents": '<path d="M26 28 H34.5 L39 32.5 V46 C39 46.6 38.6 47 38 47 H26 C25.4 47 25 46.6 25 46 V29 C25 28.4 25.4 28 26 28 Z"/>'
                 '<g fill="#8ACFFA"><rect x="27.5" y="35" width="9" height="1.3" rx=".6"/>'
                 '<rect x="27.5" y="38.2" width="9" height="1.3" rx=".6"/><rect x="27.5" y="41.4" width="6" height="1.3" rx=".6"/></g>',
    "download": '<circle cx="32" cy="37.5" r="9"/><path d="M30.8 32 H33.2 V37.6 H36.2 L32 42.4 L27.8 37.6 H30.8 Z" fill="#8ACFFA"/>',
    "music": '<path d="M28 31.8 L39 29 V41.2 A2.8 2.3 0 1 1 37 39 V33.2 L30 35 V43.6 A2.8 2.3 0 1 1 28 41.4 Z"/>',
    "pictures": '<rect x="22.5" y="29.5" width="19" height="15" rx="2"/>'
                '<path d="M24.5 42.5 L29.5 36 L33 40 L35.5 37.5 L39.5 42.5 Z" fill="#8ACFFA"/>'
                '<circle cx="36.5" cy="33.5" r="1.7" fill="#8ACFFA"/>',
    "videos": '<rect x="22.5" y="29.5" width="19" height="15" rx="2.2"/><path d="M30 33.3 L36 37 L30 40.7 Z" fill="#8ACFFA"/>',
    "public": '<circle cx="32" cy="32.5" r="3.6"/><path d="M24.8 45 C24.8 40.6 28 38 32 38 C36 38 39.2 40.6 39.2 45 Z"/>',
    "templates": '<rect x="24" y="29" width="7" height="7" rx="1.2"/><rect x="33" y="29" width="7" height="7" rx="1.2"/>'
                 '<rect x="24" y="38" width="7" height="7" rx="1.2"/><rect x="33" y="38" width="7" height="7" rx="1.2" opacity=".5"/>',
    "remote": '<circle cx="32" cy="37" r="8.5" fill="none" stroke="currentColor" stroke-width="1.6"/>'
              '<ellipse cx="32" cy="37" rx="3.6" ry="8.5" fill="none" stroke="currentColor" stroke-width="1.4"/>'
              '<path d="M23.5 37 H40.5 M25 32.6 H39 M25 41.4 H39" stroke="currentColor" stroke-width="1.3" fill="none"/>',
    "plain": "",
}

FOLDERS = {
    "folder": "plain", "folder-open": "plain", "inode-directory": "plain", "folder-new": "plain",
    "user-home": "home", "folder-home": "home", "user-desktop": "desktop", "folder-desktop": "desktop",
    "folder-documents": "documents", "folder-download": "download", "folder-downloads": "download",
    "folder-music": "music", "folder-pictures": "pictures", "folder-images": "pictures",
    "folder-videos": "videos", "folder-video": "videos", "folder-publicshare": "public", "folder-public": "public",
    "folder-templates": "templates", "folder-remote": "remote", "network-workgroup": "remote",
}


def folder_svg(glyph):
    g = GLYPHS[glyph]
    emblem = f'<g fill="{EMBLEM_COLOR}" color="{EMBLEM_COLOR}" opacity="0.9">{g}</g>' if g else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
            f'{FOLDER_DEFS}{FOLDER_BODY}{emblem}</svg>\n')


# --------------------------------------------------------------------- trash
def trash_svg(full):
    ribs = "".join(f'<rect x="{x}" y="22" width="1.1" height="31" rx=".5" fill="#8E949C" opacity=".55"/>'
                   for x in (21, 26.3, 31.5, 36.7, 42))
    paper = ('<g><path d="M20 20 C23 12 30 13 31 17 C33 11 41 12 43 18 C45 16 48 18 46 21 H19 Z" fill="#FFFFFF" '
             'stroke="#C9CED6" stroke-width=".8"/>'
             '<path d="M24 17 L28 19 M35 15 L37 19 M41 17 L40 20" stroke="#C9CED6" stroke-width=".8"/></g>') if full else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<defs>
  <linearGradient id="can" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#D5D9DF"/><stop offset=".5" stop-color="#F4F6F8"/><stop offset="1" stop-color="#CDD2D9"/></linearGradient>
  <filter id="sh" x="-20%" y="-20%" width="140%" height="150%">
    <feDropShadow dx="0" dy="1" stdDeviation="1" flood-color="#000" flood-opacity="0.25"/></filter>
</defs>
<g filter="url(#sh)">
  <path d="M16.5 21 H47.5 L44.6 54.2 C44.5 55.8 43.2 57 41.6 57 H22.4 C20.8 57 19.5 55.8 19.4 54.2 Z" fill="url(#can)" stroke="#AEB4BC" stroke-width=".8"/>
  {ribs}
  {paper}
  <rect x="14.5" y="18.5" width="35" height="4" rx="2" fill="#E9ECF0" stroke="#AEB4BC" stroke-width=".8"/>
</g>
</svg>
'''


# --------------------------------------------------------------------- apps
def squircle(fill_defs, fill, inner, stroke="none"):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<defs>{fill_defs}
  <filter id="sh" x="-20%" y="-20%" width="140%" height="150%">
    <feDropShadow dx="0" dy="1.2" stdDeviation="1.3" flood-color="#000" flood-opacity="0.3"/></filter>
</defs>
<path filter="url(#sh)" d="M32 5 C50.5 5 59 6.8 59 32 C59 57.2 50.5 59 32 59 C13.5 59 5 57.2 5 32 C5 6.8 13.5 5 32 5 Z" fill="{fill}" stroke="{stroke}" stroke-width=".6"/>
{inner}
</svg>
'''


def grad(id_, top, bottom):
    return (f'<linearGradient id="{id_}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>')


def gear(cx, cy, r_out, r_in, teeth, color):
    import math
    pts = []
    for i in range(teeth * 4):
        a = 2 * math.pi * i / (teeth * 4)
        r = r_out if (i % 4) in (1, 2) else r_in
        pts.append(f"{cx + r * math.cos(a):.2f},{cy + r * math.sin(a):.2f}")
    return f'<polygon points="{" ".join(pts)}" fill="{color}"/>'


APPS = {}

APPS["terminal"] = (squircle(grad("g", "#3A3A3C", "#1C1C1E"), "url(#g)",
    '<rect x="10" y="10" width="44" height="44" rx="9" fill="none" stroke="#FFFFFF" stroke-opacity=".08"/>'
    '<path d="M17 22 L26 29.5 L17 37" stroke="#E8E8E8" stroke-width="3.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    '<rect x="29" y="35" width="15" height="3.2" rx="1.6" fill="#E8E8E8"/>'),
    ["utilities-terminal", "org.gnome.Terminal", "gnome-terminal", "terminal", "mate-terminal",
     "xfce4-terminal", "org.xfce.terminal", "Terminal"])

APPS["files"] = (squircle(grad("g", "#56B4F7", "#1C7FE6"), "url(#g)",
    '<path d="M16 22.5 C16 21.4 16.9 20.5 18 20.5 H27 L30 23.5 H46 C47.1 23.5 48 24.4 48 25.5 V43 C48 44.1 47.1 45 46 45 H18 C16.9 45 16 44.1 16 43 Z" fill="#FFFFFF" opacity=".95"/>'
    '<rect x="16" y="27" width="32" height="1.6" fill="#1C7FE6" opacity=".25"/>'),
    ["system-file-manager", "nemo", "org.gnome.Nautilus", "nautilus", "file-manager", "thunar", "org.xfce.thunar", "caja"])

APPS["settings"] = (squircle(grad("g", "#B8BCC3", "#7D838C"), "url(#g)",
    gear(32, 32, 19, 15.5, 12, "#4A4F57") + '<circle cx="32" cy="32" r="12" fill="#D9DCE1"/>'
    + gear(32, 32, 9.5, 7.6, 8, "#5B616A") + '<circle cx="32" cy="32" r="3.2" fill="#D9DCE1"/>'),
    ["preferences-system", "cinnamon-settings", "preferences-desktop", "org.gnome.Settings",
     "gnome-control-center", "systemsettings", "preferences-other", "csd-settings"])

APPS["editor"] = (squircle(grad("g", "#FFFFFF", "#ECECEC"), "url(#g)",
    '<g fill="#C7CBD1"><rect x="16" y="18" width="26" height="2.4" rx="1.2"/><rect x="16" y="24" width="32" height="2.4" rx="1.2"/>'
    '<rect x="16" y="30" width="29" height="2.4" rx="1.2"/><rect x="16" y="36" width="20" height="2.4" rx="1.2"/>'
    '<rect x="16" y="42" width="14" height="2.4" rx="1.2"/></g>'
    '<g transform="rotate(45 40 40)"><rect x="37" y="22" width="6" height="22" rx="1" fill="#FFB020"/>'
    '<path d="M37 44 L43 44 L40 50 Z" fill="#F2D3A0"/><path d="M39 48 L41 48 L40 50 Z" fill="#3A3A3C"/>'
    '<rect x="37" y="20" width="6" height="3.5" rx="1" fill="#FF6B6B"/></g>', "#D5D5D5"),
    ["accessories-text-editor", "org.x.editor", "xed", "gedit", "org.gnome.gedit", "org.gnome.TextEditor",
     "text-editor", "pluma", "mousepad", "org.xfce.mousepad"])

APPS["software"] = (squircle(grad("g", "#3AA0FF", "#0A63E0"), "url(#g)",
    '<path d="M20 25 H44 L42.3 47 C42.2 48.1 41.3 49 40.2 49 H23.8 C22.7 49 21.8 48.1 21.7 47 Z" fill="#FFFFFF"/>'
    '<path d="M26.5 28 V23 C26.5 19.5 29 17 32 17 C35 17 37.5 19.5 37.5 23 V28" stroke="#FFFFFF" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
    '<circle cx="26.5" cy="28.5" r="1.6" fill="#0A63E0"/><circle cx="37.5" cy="28.5" r="1.6" fill="#0A63E0"/>'),
    ["mintinstall", "system-software-install", "org.gnome.Software", "gnome-software", "software-store",
     "softwarecenter", "applications-other"])

APPS["update"] = (squircle(grad("g", "#5AC8FA", "#1A8CE8"), "url(#g)",
    '<path d="M42.5 27 A12 12 0 1 0 44 34" stroke="#FFFFFF" stroke-width="3.6" fill="none" stroke-linecap="round"/>'
    '<path d="M45.5 18.5 L45.8 29.4 L35.2 27.6 Z" fill="#FFFFFF"/>'),
    ["mintupdate", "system-software-update", "software-update-available", "update-manager", "mintupdate-checking"])

APPS["calculator"] = (squircle(grad("g", "#4A4A4E", "#2A2A2D"), "url(#g)",
    '<rect x="15" y="15" width="15" height="15" rx="4" fill="#8E8E93"/><rect x="34" y="15" width="15" height="15" rx="4" fill="#8E8E93"/>'
    '<rect x="15" y="34" width="15" height="15" rx="4" fill="#8E8E93"/><rect x="34" y="34" width="15" height="15" rx="4" fill="#FF9F0A"/>'
    '<g stroke="#FFFFFF" stroke-width="2.4" stroke-linecap="round"><path d="M18.5 22.5 H26.5 M22.5 18.5 V26.5"/>'
    '<path d="M37.5 22.5 H45.5"/><path d="M19.2 38.2 L25.8 44.8 M25.8 38.2 L19.2 44.8"/>'
    '<path d="M37.5 39.5 H45.5 M37.5 43.5 H45.5"/></g>'),
    ["accessories-calculator", "org.gnome.Calculator", "gnome-calculator", "calc", "galculator", "mate-calc"])

APPS["monitor"] = (squircle(grad("g", "#2C2C2E", "#141416"), "url(#g)",
    '<g stroke="#FFFFFF" stroke-opacity=".12" stroke-width="1"><path d="M13 22 H51 M13 32 H51 M13 42 H51"/></g>'
    '<path d="M13 40 L20 40 L24 30 L29 44 L34 22 L39 38 L43 33 L51 33" stroke="#30D158" stroke-width="2.6" '
    'fill="none" stroke-linejoin="round" stroke-linecap="round"/>'),
    ["utilities-system-monitor", "org.gnome.SystemMonitor", "gnome-system-monitor", "mate-system-monitor",
     "xfce4-taskmanager", "org.xfce.taskmanager"])

APPS["viewer"] = (squircle(grad("g", "#FFFFFF", "#EDEDED"), "url(#g)",
    '<rect x="13" y="16" width="38" height="32" rx="4" fill="#5AC8FA"/>'
    '<path d="M13 41 L23 30 L31 38 L37 32 L51 44 V44 C51 46.2 49.2 48 47 48 H17 C14.8 48 13 46.2 13 44 Z" fill="#34C759"/>'
    '<circle cx="41" cy="24" r="3.6" fill="#FFD60A"/>', "#D5D5D5"),
    ["org.x.viewer", "xviewer", "eog", "org.gnome.eog", "image-viewer", "org.gnome.Loupe", "shotwell",
     "ristretto", "org.xfce.ristretto", "multimedia-photo-viewer"])

APPS["reader"] = (squircle(grad("g", "#FF6B5E", "#E0352B"), "url(#g)",
    '<path d="M20 14 H36 L44 22 V48 C44 49.1 43.1 50 42 50 H20 C18.9 50 18 49.1 18 48 V16 C18 14.9 18.9 14 20 14 Z" fill="#FFFFFF"/>'
    '<path d="M36 14 V20 C36 21.1 36.9 22 38 22 H44 Z" fill="#FFC9C4"/>'
    '<g fill="#E0352B" opacity=".55"><rect x="22" y="28" width="18" height="2" rx="1"/><rect x="22" y="33" width="18" height="2" rx="1"/>'
    '<rect x="22" y="38" width="12" height="2" rx="1"/></g>'),
    ["xreader", "org.x.reader", "evince", "org.gnome.Evince", "atril", "accessories-document-viewer",
     "x-office-document-viewer", "document-viewer", "org.gnome.Papers"])

APPS["archive"] = (squircle(grad("g", "#D9B27C", "#B88A4E"), "url(#g)",
    '<rect x="15" y="20" width="34" height="27" rx="3" fill="#F3DDB8"/><rect x="13.5" y="16" width="37" height="7" rx="2" fill="#E8C994"/>'
    '<g fill="#7A5A30"><rect x="30" y="16" width="4" height="3"/><rect x="30" y="21" width="4" height="3"/>'
    '<rect x="30" y="26" width="4" height="3"/><rect x="28.5" y="31" width="7" height="8" rx="1.5"/></g>'),
    ["org.gnome.FileRoller", "file-roller", "engrampa", "xarchiver", "ark", "utilities-file-archiver", "package-x-generic"])

APPS["screenshot"] = (squircle(grad("g", "#8E8E93", "#5A5A5F"), "url(#g)",
    '<path d="M16 24 C16 22.3 17.3 21 19 21 H24 L26.5 17.5 H37.5 L40 21 H45 C46.7 21 48 22.3 48 24 V44 C48 45.7 46.7 47 45 47 H19 C17.3 47 16 45.7 16 44 Z" fill="#F2F2F2"/>'
    '<circle cx="32" cy="34" r="8.5" fill="#3A3A3C"/><circle cx="32" cy="34" r="5.5" fill="#5E5E63"/>'
    '<circle cx="30" cy="32" r="1.6" fill="#FFFFFF" opacity=".7"/>'),
    ["org.gnome.Screenshot", "gnome-screenshot", "applets-screenshooter", "accessories-screenshot", "mate-screenshot"])



INDEX = """[Icon Theme]
Name=Monterra
Comment=Clean icons for Cinnamon – folders, trash and core apps; everything else from Mint-Y
Inherits=Monterra-Local,Mint-Y,Adwaita,hicolor
Example=folder
DisplayDepth=32

Directories=places/scalable,apps/scalable,categories/scalable

[places/scalable]
Context=Places
Size=64
MinSize=8
MaxSize=512
Type=Scalable

[categories/scalable]
Context=Categories
Size=64
MinSize=8
MaxSize=512
Type=Scalable

[apps/scalable]
Context=Applications
Size=64
MinSize=8
MaxSize=512
Type=Scalable
"""


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    places = OUT / "places" / "scalable"
    apps = OUT / "apps" / "scalable"
    places.mkdir(parents=True)
    apps.mkdir(parents=True)
    (OUT / "index.theme").write_text(INDEX)

    for name, glyph in FOLDERS.items():
        (places / f"{name}.svg").write_text(folder_svg(glyph))
    for name in ("user-trash", "trashcan_empty"):
        (places / f"{name}.svg").write_text(trash_svg(False))
    for name in ("user-trash-full", "trashcan_full"):
        (places / f"{name}.svg").write_text(trash_svg(True))
    n = 0
    for key, (svg, names) in APPS.items():
        if not svg:
            continue
        for nm in names:
            (apps / f"{nm}.svg").write_text(svg)
            n += 1
    import settings_icons
    import symbolic
    # generic web-app icons (Monterra style; brand logos are framed separately by monterra-webapps.py)
    WEB = {
        "webapp-manager":           ("blue",     "globe-hemisphere-west"),
        "monterra-webapp-default":  ("blue",     "globe-hemisphere-west"),
        "monterra-webapp-router":   ("teal",     "wifi-high"),
        "modem":                    ("teal",     "wifi-high"),
        "network-wireless-hotspot": ("teal",     "wifi-high"),
        "monterra-webapp-nas":      ("graphite", "hard-drives"),
        "monterra-webapp-smarthome":("orange",   "lightbulb"),
        "monterra-webapp-ai":       ("purple",   "magic-wand"),
    }
    for nm, (col, gl) in WEB.items():
        (apps / f"{nm}.svg").write_text(settings_icons.icon_svg(col, gl))
    ns = settings_icons.build(OUT / "categories" / "scalable")
    nsym = symbolic.build(OUT)
    print(f"symbolic: {nsym}")
    print(f"icons: {len(FOLDERS) + 4} places, {n} app entries, {ns} settings icons")


if __name__ == "__main__":
    build()
