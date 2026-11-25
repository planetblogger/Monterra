#!/usr/bin/env python3
"""
Monterra symbolic icons – slim status icons for Cinnamon's panel applets
(sound, network, power, printers, removable drives, notifications, user, …) and Nemo's sidebar.

All shapes are *filled* paths (GTK/St recolour symbolic icons by fill only).
Generic glyphs come from Phosphor Icons (MIT, third_party/phosphor-symbolic); volume, Wi-Fi,
cellular and battery indicators are drawn here so their level steps look consistent.
Every icon is written as <name>-symbolic.svg and xsi-<name>-symbolic.svg (Cinnamon ≥ 6 uses xsi-).
"""
import math
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GDIR = HERE.parent / "third_party" / "phosphor-symbolic"
FG = "#bebebe"          # conventional symbolic colour, replaced by GTK/St at runtime
DIM = 0.3


def svg(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
            f'<g fill="{FG}">{body}</g></svg>\n')


def ph(name, weight="regular", box=(0, 0, 16), extra=""):
    """Phosphor glyph scaled into box=(x, y, size)."""
    fname = f"{name}.svg" if weight == "regular" else f"{name}-{weight}.svg"
    text = (GDIR / weight / fname).read_text()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", text, re.S).group(1)
    inner = re.sub(r'\sfill="[^"]*"', "", inner)
    x, y, s = box
    return f'<g transform="translate({x} {y}) scale({s / 256:.6f}){extra}">{inner}</g>'


def ring_sector(cx, cy, r0, r1, a0, a1, opacity=1.0):
    """Filled annular sector, angles in degrees (0 = right, 90 = down)."""
    def p(r, a):
        return cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))
    if r0 <= 0.01:
        (x1, y1), (x2, y2) = p(r1, a0), p(r1, a1)
        d = f"M{cx:.3f} {cy:.3f} L{x1:.3f} {y1:.3f} A{r1} {r1} 0 0 1 {x2:.3f} {y2:.3f} Z"
    else:
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p(r1, a0), p(r1, a1), p(r0, a1), p(r0, a0)
        d = (f"M{x1:.3f} {y1:.3f} A{r1} {r1} 0 0 1 {x2:.3f} {y2:.3f} "
             f"L{x3:.3f} {y3:.3f} A{r0} {r0} 0 0 0 {x4:.3f} {y4:.3f} Z")
    return f'<path d="{d}" opacity="{opacity}"/>'


def slash(opacity=1.0):
    return (f'<path d="M2.2 1.2 L14.8 13.8 L13.8 14.8 L1.2 2.2 Z" opacity="{opacity}"/>')


# --------------------------------------------------------------- custom indicators
def wifi(level, dim_all=False):
    cx, cy = 8, 13.6
    parts = []
    radii = [(0, 2.6), (4.1, 5.8), (7.3, 9.0), (10.5, 12.2)]
    for i, (r0, r1) in enumerate(radii):
        on = (i < level) and not dim_all
        parts.append(ring_sector(cx, cy, r0, r1, 225, 315, 1 if on else DIM))
    return svg("".join(parts))


def cellular(level):
    bars = []
    for i in range(4):
        h = 3.5 + i * 3.2
        x = 1.5 + i * 3.6
        bars.append(f'<rect x="{x}" y="{14 - h}" width="2.4" height="{h}" rx="0.8" '
                    f'opacity="{1 if i < level else DIM}"/>')
    return svg("".join(bars))


def speaker(waves, muted=False):
    body = '<path d="M1.5 6 H4.2 L8 2.6 V13.4 L4.2 10 H1.5 Z"/>'
    if muted:
        x = ('<path d="M10.2 5.6 L11 4.8 L12.9 6.7 L14.8 4.8 L15.6 5.6 L13.7 7.5 L15.6 9.4 L14.8 10.2 '
             'L12.9 8.3 L11 10.2 L10.2 9.4 L12.1 7.5 Z" transform="translate(0 0.5)"/>')
        return svg(body + x)
    arcs = "".join(ring_sector(7.4, 8, r0, r1, -45, 45, 1 if i < waves else 0)
                   for i, (r0, r1) in enumerate([(2.2, 3.5), (4.6, 5.9), (7.0, 8.3)]))
    return svg(body + arcs)


def battery(pct, charging=False, charged=False, missing=False):
    outline = ('<path fill-rule="evenodd" d="M2.8 4 H12.2 A1.8 1.8 0 0 1 14 5.8 V10.2 A1.8 1.8 0 0 1 12.2 12 '
               'H2.8 A1.8 1.8 0 0 1 1 10.2 V5.8 A1.8 1.8 0 0 1 2.8 4 Z M2.9 5 A0.9 0.9 0 0 0 2 5.9 V10.1 '
               'A0.9 0.9 0 0 0 2.9 11 H12.1 A0.9 0.9 0 0 0 13 10.1 V5.9 A0.9 0.9 0 0 0 12.1 5 Z"/>'
               '<path d="M14.6 6.5 H15 A0.5 0.5 0 0 1 15.5 7 V9 A0.5 0.5 0 0 1 15 9.5 H14.6 Z"/>')
    if missing:
        q = ('<path d="M6.6 6.9 C6.6 6.1 7.1 5.7 7.6 5.7 C8.3 5.7 8.7 6.1 8.7 6.7 C8.7 7.6 7.8 7.6 7.8 8.6 '
             'L7.2 8.6 C7.2 7.4 8.1 7.3 8.1 6.7 C8.1 6.4 7.9 6.3 7.6 6.3 C7.3 6.3 7.2 6.5 7.2 6.9 Z"/>'
             '<circle cx="7.5" cy="9.7" r=".5"/>')
        return svg(outline + q)
    w = max(0.0, 10.0 * pct / 100)
    lvl = ""
    if w > 0.25:
        op = 0.45 if charging else 1
        lvl = f'<rect x="2.6" y="5.6" width="{w:.2f}" height="4.8" rx="0.6" opacity="{op}"/>'
    bolt = ""
    if charging or charged:
        bolt = '<path d="M8.6 4.6 L5.4 8.6 H7.4 L6.6 11.4 L9.8 7.3 H7.8 Z"/>'
        if charged:
            lvl = f'<rect x="2.6" y="5.6" width="10" height="4.8" rx="0.6" opacity="0.45"/>'
    return svg(outline + lvl + bolt)


# --------------------------------------------------------------- icon table
def build_table():
    T = {}
    P = lambda name, w="regular", box=(0, 0, 16), extra="": svg(ph(name, w, box, extra))  # noqa: E731

    # sound
    T["audio-volume-muted"] = speaker(0, muted=True)
    T["audio-volume-low"] = speaker(1)
    T["audio-volume-medium"] = speaker(2)
    T["audio-volume-high"] = speaker(3)
    T["audio-volume-overamplified"] = speaker(3)
    for lvl in ("low", "medium", "high"):
        T[f"microphone-sensitivity-{lvl}"] = P("microphone")
    T["microphone-sensitivity-muted"] = P("microphone-slash")
    T["audio-input-microphone"] = P("microphone")
    T["audio-x-generic"] = P("music-note")
    T["media-playback-start"] = P("play", "fill")
    T["media-playback-pause"] = P("pause", "fill")
    T["media-playback-stop"] = P("stop", "fill")
    T["media-skip-forward"] = P("skip-forward", "fill")
    T["media-skip-backward"] = P("skip-back", "fill")
    T["media-playlist-repeat"] = P("repeat")
    T["media-playlist-repeat-song"] = P("repeat-once")
    T["media-playlist-shuffle"] = P("shuffle")
    T["media-playlist-consecutive"] = P("list-numbers")

    # network
    for i, s in enumerate(["none", "weak", "ok", "good", "excellent"]):
        T[f"network-wireless-signal-{s}"] = wifi(i)
        T[f"network-wireless-signal-{s}-secure"] = wifi(i)
        T[f"network-cellular-signal-{s}"] = cellular(i)
    T["network-wireless"] = wifi(4)
    T["network-wireless-connected"] = wifi(4)
    T["network-wireless-acquiring"] = wifi(2, dim_all=True)
    T["network-wireless-no-route"] = wifi(0)
    T["network-wireless-offline"] = wifi(0)
    T["network-wireless-disabled"] = wifi(0)
    T["network-cellular-acquiring"] = cellular(0)
    T["network-cellular-connected"] = cellular(4)
    T["network-cellular-no-route"] = cellular(0)
    T["network-wired"] = P("network")
    T["network-wired-acquiring"] = svg(f'<g opacity="{DIM + 0.2}">{ph("network")}</g>')
    T["network-wired-no-route"] = P("network-slash")
    T["network-wired-disconnected"] = P("network-slash")
    T["network-offline"] = P("network-slash")
    T["network-error"] = P("network-x")
    T["network-vpn"] = P("lock-key")
    T["network-vpn-acquiring"] = svg(f'<g opacity="{DIM + 0.2}">{ph("lock-key")}</g>')
    T["network-transmit-receive"] = P("arrows-down-up")
    T["network-workgroup"] = P("users-three")
    T["network-server"] = P("hard-drives")
    T["airplane-mode"] = P("airplane-tilt") if (GDIR / "regular" / "airplane-tilt.svg").exists() else P("globe")

    # power
    for n in range(0, 101, 10):
        T[f"battery-level-{n}"] = battery(n)
        T[f"battery-level-{n}-charging"] = battery(n, charging=True)
    T["battery-level-100-charged"] = battery(100, charged=True)
    for name, pct in (("full", 100), ("good", 70), ("low", 30), ("caution", 10), ("empty", 0)):
        T[f"battery-{name}"] = battery(pct)
        T[f"battery-{name}-charging"] = battery(pct, charging=True)
    T["battery-full-charged"] = battery(100, charged=True)
    T["battery-missing"] = battery(0, missing=True)
    T["ac-adapter"] = P("plug")
    T["display-brightness"] = P("sun")
    T["keyboard-brightness"] = P("keyboard")

    # printers
    T["printer"] = P("printer")
    T["printer-printing"] = svg(ph("printer") + '<circle cx="12.6" cy="12.6" r="2.4"/>')
    T["printer-warning"] = svg(ph("printer", box=(0, 0, 13.5)) + ph("warning", "fill", (7.5, 7.5, 8.5)))
    T["printer-error"] = svg(ph("printer", box=(0, 0, 13.5)) + ph("x-circle", "fill", (7.5, 7.5, 8.5)))
    T["emblem-documents"] = P("files")
    T["emblem-system"] = P("gear")
    T["run"] = P("play")
    T["edit-delete"] = P("trash")

    # removable drives / places (also used by Nemo's sidebar)
    T["media-removable"] = P("hard-drive")
    T["drive-removable-media"] = P("hard-drive")
    T["drive-removable-media-usb"] = P("usb")
    T["drive-harddisk"] = P("hard-drives")
    T["drive-harddisk-usb"] = P("usb")
    T["drive-optical"] = P("disc")
    T["media-optical"] = P("disc")
    T["media-flash"] = P("sd-card") if (GDIR / "regular" / "sd-card.svg").exists() else P("hard-drive")
    T["media-eject"] = P("eject")
    T["computer"] = P("desktop")
    T["user-home"] = P("house")
    T["user-desktop"] = P("desktop")
    T["folder"] = P("folder-simple")
    T["folder-open"] = P("folder-open")
    T["folder-documents"] = P("file-text")
    T["folder-download"] = P("download-simple")
    T["folder-music"] = P("music-notes")
    T["folder-pictures"] = P("image")
    T["folder-videos"] = P("film-strip")
    T["folder-publicshare"] = P("share-network")
    T["folder-templates"] = P("squares-four")
    T["folder-remote"] = P("globe")
    T["user-bookmarks"] = P("bookmark-simple")
    T["starred"] = P("star", "fill")
    T["non-starred"] = P("star")
    T["user-favorites"] = P("star")
    T["unfavorite"] = P("star")
    T["user-trash"] = P("trash")
    T["user-trash-full"] = P("trash", "fill")
    T["document-open-recent"] = P("clock-counter-clockwise")
    T["edit-clear"] = P("broom")
    T["document-open"] = P("folder-open")

    # notifications applet (bell)
    T["empty-notif"] = P("bell-simple")
    T["normal-notif"] = svg(ph("bell-simple") + '<circle cx="12.6" cy="3.4" r="2.6"/>')
    T["low-notif"] = svg(ph("bell-simple") + '<circle cx="12.6" cy="3.4" r="2.6" opacity=".6"/>')
    T["critical-notif"] = P("bell-ringing", "fill")
    T["alt-critical-notif"] = P("bell-ringing")
    T["notification-disabled"] = P("bell-slash")

    # user / session / misc applets
    T["avatar-default"] = P("user-circle")
    T["lock-screen"] = P("lock")
    T["log-out"] = P("sign-out")
    T["shutdown"] = P("power")
    T["system-shutdown"] = P("power")
    T["switch-user"] = P("users")
    T["system-lock-screen"] = P("lock")
    T["system-log-out"] = P("sign-out")
    T["system-switch-user"] = P("users")
    T["system-suspend"] = P("moon")
    T["system-reboot"] = P("arrow-clockwise") if (GDIR / "regular" / "arrow-clockwise.svg").exists() else P("power")
    T["preferences"] = P("gear-six")
    T["accessibility"] = P("person-arms-spread")
    T["night-light"] = P("moon")
    T["night-light-disabled"] = svg(ph("moon") + slash())
    T["inhibit"] = P("coffee")
    T["inhibit-active"] = P("coffee", "fill")
    T["inhibit-notification"] = P("bell-simple")
    T["inhibit-notification-active"] = P("bell-slash")
    T["dialog-warning"] = P("warning")
    T["x-office-calendar"] = P("calendar-blank")
    T["display"] = P("monitor")
    T["video-display"] = P("monitor")
    T["view-grid"] = P("squares-four")
    T["cpu"] = P("cpu")
    T["document-edit"] = P("pencil-simple")
    T["edit-find"] = P("magnifying-glass")
    T["document-properties"] = P("info")
    T["go-jump"] = P("arrow-bend-up-right")
    T["go-up"] = P("caret-up")
    T["go-down"] = P("caret-down")
    T["go-next"] = P("caret-right")
    T["go-previous"] = P("caret-left")
    T["list-add"] = P("plus")
    T["list-remove"] = P("minus")
    T["window-close"] = P("x")
    T["users"] = P("users")
    return T


INDEX_ADD = """
[symbolic]
Context=Status
Size=16
MinSize=8
MaxSize=512
Type=Scalable
"""


def build(theme_dir):
    out = Path(theme_dir) / "symbolic"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    table = build_table()
    for name, content in table.items():
        (out / f"{name}-symbolic.svg").write_text(content)
        (out / f"xsi-{name}-symbolic.svg").write_text(content)
    idx = Path(theme_dir) / "index.theme"
    t = idx.read_text()
    if "[symbolic]" not in t:
        t = re.sub(r"^Directories=(.*)$", lambda m: f"Directories={m.group(1)},symbolic", t, count=1, flags=re.M)
        t += INDEX_ADD
        idx.write_text(t)
    return len(table)


def vendor(assets_dir, license_file):
    """Copy every Phosphor glyph referenced in build_table() into third_party/phosphor-symbolic."""
    src = Path(assets_dir)
    names = set(re.findall(r'(?:P|ph)\("([a-z0-9-]+)"(?:, "(fill)")?', Path(__file__).read_text()))
    for name, weight in names:
        w = weight or "regular"
        fn = f"{name}.svg" if w == "regular" else f"{name}-{w}.svg"
        (GDIR / w).mkdir(parents=True, exist_ok=True)
        if (src / w / fn).exists():
            shutil.copy(src / w / fn, GDIR / w / fn)
    for opt in ("airplane-tilt", "sd-card", "arrow-clockwise"):
        if (src / "regular" / f"{opt}.svg").exists():
            shutil.copy(src / "regular" / f"{opt}.svg", GDIR / "regular")
    shutil.copy(license_file, GDIR / "LICENSE")


if __name__ == "__main__":
    if sys.argv[1] == "--vendor":
        vendor(sys.argv[2], sys.argv[3])
    else:
        print(build(sys.argv[1]), "symbolic icons (x2 incl. xsi- names)")
