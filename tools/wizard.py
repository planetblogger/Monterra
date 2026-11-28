#!/usr/bin/env python3
"""
Monterra – Einrichtungs-Assistent (wird von setup.sh gestartet, wenn eine grafische Oberfläche da ist).

Ein Fenster im Monterra-Stil: links die Schritte, rechts die Seiten mit Vorschaubildern.
Die Auswahl wird als Antwortdatei an „setup.sh --answers=…“ übergeben, das die eigentliche
Arbeit macht; der Assistent zeigt dabei den Fortschritt. Das Passwort (falls nötig) geht nur
über die Standardeingabe an setup.sh und wird nirgends gespeichert.

    python3 tools/wizard.py [--lang=de|en|es]
"""
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PV = os.path.join(ROOT, "previews")
WZ = os.path.join(PV, "wizard")
LOG = os.path.expanduser("~/monterra-installer.log")

# ---------------------------------------------------------------- Themes für den Assistenten selbst
# Der Assistent zeigt sich schon vor der Installation im gewählten Monterra-Look: die Themes aus
# dem Paket werden über ein temporäres Datenverzeichnis für GTK sichtbar gemacht (vor dem GTK-Import).
TMP = tempfile.mkdtemp(prefix="monterra-wizard-")
os.makedirs(os.path.join(TMP, "themes"))
os.makedirs(os.path.join(TMP, "icons"))
for ic in ("Monterra",):
    src = os.path.join(ROOT, "icons", ic)
    if os.path.isdir(src):
        os.symlink(src, os.path.join(TMP, "icons", ic))
os.environ["XDG_DATA_DIRS"] = TMP + ":" + os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango  # noqa: E402
try:
    import cairo  # noqa: E402
    SLANT, BOLD = cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
except ImportError:
    SLANT, BOLD = 0, 1

spec = importlib.util.spec_from_file_location("monterra_accent", os.path.join(HERE, "accent.py"))
accent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accent)

MOTIF_KEYS = ["sky", "desert", "mars", "jungle", "silk", "blossom"]
MOTIF_FILE = {"sky": "Sky", "desert": "Desert", "mars": "Mars", "jungle": "Jungle", "silk": "Silk", "blossom": "Blossom"}
MOTIF_ACCENT = {"sky": "blue", "desert": "orange", "mars": "red", "jungle": "green", "silk": "graphite", "blossom": "purple"}
COLOR_KEYS = ["blue", "indigo", "purple", "pink", "red", "orange", "yellow", "green", "teal", "cyan", "brown", "grey", "graphite"]
EXTRAS = [  # key, Titel, Beschreibung, braucht Passwort
    ("font", "S_L_FONT", "S_W_XD_FONT", True),
    ("appicons", "S_L_APPICONS", "S_W_XD_APPICONS", False),
    ("auto", "S_L_AUTO", "S_W_XD_AUTO", False),
    ("werkst", "S_L_WERKST", "S_W_XD_WERKST", False),
    ("fenster", "S_L_WINDOWS", "S_W_XD_WINDOWS", False),
    ("fgroesse", "S_L_WINSIZE", "S_W_XD_WINSIZE", False),
    ("setgrid", "S_L_SETGRID", "S_W_XD_SETGRID", False),
    ("firefox", "S_L_FIREFOX", "S_W_XD_FIREFOX", False),
    ("thunderb", "S_L_THUNDERBIRD", "S_W_XD_THUNDERBIRD", False),
    ("folders", "S_L_FOLDERS", "S_W_XD_FOLDERS", True),
    ("splash", "S_L_SPLASH", "S_W_XD_SPLASH", True),
    ("login", "S_L_LOGIN", "S_W_XD_LOGIN", True),
]


def theme_name(dark, color):
    name = "Monterra-Dark" if dark else "Monterra"
    if color and color != "blue":
        name += "-" + accent.normalize(color)
    return name


def ensure_theme(name):
    """Theme aus Grund-Theme + Akzent-Abweichungen zusammensetzen (nur GTK 3)."""
    dest = os.path.join(TMP, "themes", name, "gtk-3.0")
    if os.path.isdir(dest):
        return
    base = "Monterra-Dark" if name.startswith("Monterra-Dark") else "Monterra"
    col = name[len(base) + 1:] if len(name) > len(base) else ""
    layers = []
    if col:
        layers.append(os.path.join(ROOT, "themes", "accents", col, base, "gtk-3.0"))
    layers.append(os.path.join(ROOT, "themes", base, "gtk-3.0"))
    os.makedirs(os.path.join(dest, "assets"))
    for f in ("gtk.css", "gtk-dark.css"):
        for lay in layers:
            if os.path.isfile(os.path.join(lay, f)):
                os.symlink(os.path.join(lay, f), os.path.join(dest, f))
                break
    for lay in reversed(layers):           # Abweichungen überschreiben das Grund-Theme
        ad = os.path.join(lay, "assets")
        if not os.path.isdir(ad):
            continue
        for f in os.listdir(ad):
            target = os.path.join(dest, "assets", f)
            if os.path.lexists(target):
                os.remove(target)
            os.symlink(os.path.join(ad, f), target)
    with open(os.path.join(TMP, "themes", name, "index.theme"), "w") as fh:
        fh.write(f"[Desktop Entry]\nType=X-GNOME-Metatheme\nName={name}\n")


# ---------------------------------------------------------------- Texte
def load_lang(code):
    """Sprachdatei (Shell-Variablen) lesen: KEY="…" und KEY=("…" "…")."""
    path = os.path.join(HERE, "languages", f"{code}.sh")
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r'^(S_[A-Z0-9_]+)=(.*)$', line.rstrip("\n"))
        if not m:
            continue
        key, val = m.groups()
        try:
            if val.startswith("("):
                out[key] = shlex.split(val.strip()[1:-1])
            else:
                parts = shlex.split(val)
                out[key] = parts[0] if parts else ""
        except ValueError:
            continue
    return out


def para(s):
    """Texte aus den Sprachdateien: \\n\\n = Absatz, einzelnes \\n = Leerzeichen (umbricht dann sauber)."""
    s = s.replace("\\n", "\n")
    blocks = [re.sub(r"\s*\n\s*", " ", b).strip() for b in s.split("\n\n")]
    return "\n\n".join(b for b in blocks if b)


CSS = """
.mw-sidebar { padding: 22px 14px; }
.mw-sidebar.light { background-color: #ECECEF; }
.mw-sidebar.dark { background-color: #232326; }
.mw-brand { font-size: 17px; font-weight: 700; }
.mw-step { padding: 7px 10px; border-radius: 9px; }
.mw-step label { font-size: 13px; }
.mw-step.current { background-color: alpha(@theme_selected_bg_color, 0.16); }
.mw-step.current label { font-weight: 700; }
.mw-step.todo label { opacity: 0.55; }
.mw-bubble { min-width: 22px; min-height: 22px; border-radius: 11px; font-size: 11px; font-weight: 700;
             background-color: alpha(@theme_fg_color, 0.10); }
.mw-step.current .mw-bubble { background-color: @theme_selected_bg_color; color: @theme_selected_fg_color; }
.mw-step.done .mw-bubble { background-color: alpha(@theme_selected_bg_color, 0.55); color: @theme_selected_fg_color; }
.mw-title { font-size: 24px; font-weight: 800; }
.mw-desc { font-size: 13.5px; opacity: 0.78; }
.mw-card { border-radius: 14px; padding: 10px; border: 2px solid transparent;
           background-image: none; background-color: alpha(@theme_fg_color, 0.045); box-shadow: none; }
.mw-card:hover { background-color: alpha(@theme_fg_color, 0.08); }
.mw-card:checked, .mw-card:checked:hover { border-color: @theme_selected_bg_color;
           background-color: alpha(@theme_selected_bg_color, 0.12); }
.mw-card-title { font-weight: 700; font-size: 14px; }
.mw-card-desc { font-size: 12px; opacity: 0.72; }
.mw-badge { font-size: 10.5px; font-weight: 700; padding: 1px 8px; border-radius: 9px;
            background-color: @theme_selected_bg_color; color: @theme_selected_fg_color; }
.mw-swatch { border-radius: 99px; padding: 4px; border: 2px solid transparent; background-image: none;
             background-color: transparent; box-shadow: none; min-width: 0; min-height: 0; }
.mw-swatch:checked { border-color: @theme_fg_color; }
.mw-list { border-radius: 14px; background-color: alpha(@theme_fg_color, 0.035); }
.mw-list row { padding: 10px 14px; border-bottom: 1px solid alpha(@theme_fg_color, 0.06); }
.mw-list row:last-child { border-bottom: none; }
.mw-bottom { padding: 14px 26px; border-top: 1px solid alpha(@theme_fg_color, 0.08); }
.mw-sum-key { opacity: 0.65; }
.mw-sum-val { font-weight: 600; }
.mw-chip { padding: 3px 10px; border-radius: 10px; font-size: 12px; background-color: alpha(@theme_selected_bg_color, 0.14); }
.mw-error { color: #E5484D; }
.mw-big-step { font-size: 14px; font-weight: 600; }
.mw-log { font-family: monospace; font-size: 11px; }
"""


# ---------------------------------------------------------------- kleine Bausteine
def label(text, cls=None, wrap=True, xalign=0.0, width=None, markup=False):
    lab = Gtk.Label()
    if markup:
        lab.set_markup(text)
    else:
        lab.set_text(text)
    lab.set_xalign(xalign)
    if wrap:
        lab.set_line_wrap(True)
        lab.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        lab.set_max_width_chars(width or 72)
    if cls:
        for c in cls.split():
            lab.get_style_context().add_class(c)
    return lab


def svg_pixbuf(path, w, h=-1):
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, w, h, True)
    except GLib.Error:
        return None


class RoundedImage(Gtk.DrawingArea):
    """Bild mit abgerundeten Ecken (scharf auch bei HiDPI)."""

    def __init__(self, path, width, radius=10, height=None):
        super().__init__()
        self.path, self.w, self.radius = path, width, radius
        self.pix = None
        self.h = height
        self._load()
        self.connect("draw", self._draw)

    def _load(self):
        scale = max(1, self.get_scale_factor())
        try:
            src = GdkPixbuf.Pixbuf.new_from_file(self.path)
            h = self.h or round(src.get_height() * self.w / src.get_width())
            self.h = h
            self.pix = src.scale_simple(self.w * scale, h * scale, GdkPixbuf.InterpType.HYPER)
        except GLib.Error:
            self.h = self.h or round(self.w * 0.5625)
        self.set_size_request(self.w, self.h)

    def set_path(self, path):
        self.path = path
        self.h = None
        self._load()
        self.queue_draw()

    def _draw(self, w, cr):
        r = self.radius
        W, H = self.w, self.h
        cr.new_sub_path()
        cr.arc(W - r, r, r, -1.5708, 0)
        cr.arc(W - r, H - r, r, 0, 1.5708)
        cr.arc(r, H - r, r, 1.5708, 3.1416)
        cr.arc(r, r, r, 3.1416, 4.7124)
        cr.close_path()
        cr.clip()
        if self.pix:
            scale = max(1, self.get_scale_factor())
            cr.scale(1 / scale, 1 / scale)
            Gdk.cairo_set_source_pixbuf(cr, self.pix, 0, 0)
            cr.paint()
        else:
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.2)
            cr.paint()
        return False


class SvgImage(Gtk.DrawingArea):
    """SVG-Symbol in Zielgröße, scharf bei HiDPI (selbst gezeichnet – auch innerhalb von Knöpfen sichtbar)."""

    def __init__(self, path, size):
        super().__init__()
        self.path, self.size = path, size
        self.pix = None
        self.set_size_request(size, size)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", self._draw)
        self._load()

    def _load(self):
        scale = max(1, self.get_scale_factor())
        self.pix = svg_pixbuf(self.path, self.size * scale, self.size * scale)
        self.queue_draw()

    def _draw(self, w, cr):
        if self.pix:
            scale = max(1, self.get_scale_factor())
            cr.scale(1 / scale, 1 / scale)
            Gdk.cairo_set_source_pixbuf(cr, self.pix, 0, 0)
            cr.paint()
        return False


def card_group(items, active, on_change, columns=2):
    """Auswahlkarten (wie Optionsfelder). items: (key, widget). Gibt Grid zurück."""
    grid = Gtk.Grid(column_spacing=14, row_spacing=14)
    group = None
    for i, (key, child) in enumerate(items):
        rb = Gtk.RadioButton.new_from_widget(group)
        group = group or rb
        rb.set_mode(False)
        rb.get_style_context().add_class("mw-card")
        rb.add(child)
        rb.set_active(key == active)
        rb.connect("toggled", lambda b, k=key: b.get_active() and on_change(k))
        grid.attach(rb, i % columns, i // columns, 1, 1)
    return grid


# ---------------------------------------------------------------- Assistent
class Wizard(Gtk.Window):
    def __init__(self, lang):
        super().__init__(title="Monterra")
        self.set_default_size(1060, 720)
        self.set_position(Gtk.WindowPosition.CENTER)
        logo = os.path.join(ROOT, "components", "menubar", "monterra-menubar@monterra", "icons", "monterra-logo-symbolic.svg")
        pb = svg_pixbuf(os.path.join(WZ, "extra-mode-install.svg") if not os.path.exists(logo) else logo, 64, 64)
        if pb:
            self.set_icon(pb)
        self.lang = lang
        self.running = False
        self.proc = None
        self.connect("delete-event", self._on_delete)

        # Vorbelegung
        cur_theme = Gtk.Settings.get_default().props.gtk_theme_name or ""
        self.c = {
            "mode": "install",
            "variant": "dark" if "dark" in cur_theme.lower() else "light",
            "layout": "menubar-dock",
            "wall": "sky",
            "accent": "match",
            "buttons": self._current_buttons(),
            "extras": self._default_extras(),
        }
        self.password = ""

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Gtk.Settings.get_default().props.gtk_icon_theme_name = "Monterra"

        hb = Gtk.HeaderBar(show_close_button=True)
        hb.set_title("Monterra")
        self.set_titlebar(hb)
        self.hb = hb

        self.root = Gtk.Box()
        self.add(self.root)
        self.build()
        self.apply_look()

    # ------------------------------------------------------------ Vorbelegung
    def _current_buttons(self):
        try:
            v = open(os.path.expanduser("~/.config/monterra-buttons.conf")).read().strip()
            v = {"gross": "22", "sehr-gross": "28", "normal": "16"}.get(v, v)
            n = int(v)
            return n if 14 <= n <= 32 else 16
        except (OSError, ValueError):
            return 16

    def _default_extras(self):
        home = os.path.expanduser("~")
        def exists(*p): return any(os.path.exists(os.path.join(home, x)) for x in p)
        ext = os.path.join(home, ".local/share/cinnamon/extensions")
        on = {"font", "appicons", "auto", "werkst", "fgroesse", "setgrid", "folders", "splash", "login"}
        if exists(".mozilla/firefox", ".config/mozilla/firefox", ".var/app/org.mozilla.firefox", "snap/firefox/common/.mozilla/firefox"):
            on.add("firefox")
        if exists(".thunderbird", ".var/app/org.mozilla.Thunderbird", "snap/thunderbird/common/.thunderbird"):
            on.add("thunderb")
        if os.path.isdir(os.path.join(ext, "monterra-window-shadows@monterra")) or os.path.isdir(os.path.join(ext, "monterra-fenster@monterra")):
            on.add("fenster")
        return on

    # ------------------------------------------------------------ Hilfen
    def t(self, key):
        return self.L.get(key, key)

    def dark(self):
        return self.c["variant"] == "dark"

    def vs(self):
        return "dark" if self.dark() else "light"

    def match_color(self):
        if self.c["wall"] != "keep":
            return MOTIF_ACCENT[self.c["wall"]]
        try:
            n = open(os.path.expanduser("~/.config/monterra-akzent.conf")).read().strip()
            return accent.normalize(n).lower()
        except (OSError, SystemExit):
            return "blue"

    def accent_key(self):
        return self.match_color() if self.c["accent"] == "match" else self.c["accent"]

    def color_name(self, key):
        names = self.L.get("S_COLORS", [])
        i = COLOR_KEYS.index(key)
        return names[i] if i < len(names) else key

    def motif_name(self, key):
        names = self.L.get("S_MOTIFS", [])
        i = MOTIF_KEYS.index(key)
        return names[i].split(" – ")[0] if i < len(names) else key

    def needs_password(self):
        if self.c["mode"] == "uninstall":
            return True
        return bool(self.c["extras"] & {"font", "folders", "splash", "login"})

    def apply_look(self):
        """Den Assistenten selbst in Variante und Akzentfarbe der Auswahl zeigen."""
        name = theme_name(self.dark(), self.accent_key())
        try:
            ensure_theme(name)
            Gtk.Settings.get_default().props.gtk_theme_name = name
        except OSError:
            pass
        ctx = self.sidebar.get_style_context()
        ctx.remove_class("light" if self.dark() else "dark")
        ctx.add_class(self.vs())

    # ------------------------------------------------------------ Aufbau
    def build(self):
        self.L = load_lang(self.lang)
        for ch in self.root.get_children():
            self.root.remove(ch)

        # Seitenleiste
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.sidebar.get_style_context().add_class("mw-sidebar")
        self.sidebar.set_size_request(230, -1)
        brand = Gtk.Box(spacing=10, margin_bottom=18, margin_start=6)
        brand.pack_start(SvgImage(self._logo_path(), 36), False, False, 0)
        brand.pack_start(label("Monterra", "mw-brand", wrap=False), False, False, 0)
        self.sidebar.pack_start(brand, False, False, 0)
        self.step_rows = []
        self.root.pack_start(self.sidebar, False, False, 0)

        # Inhalt
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=180)
        right.pack_start(self.stack, True, True, 0)
        bottom = Gtk.Box(spacing=10)
        bottom.get_style_context().add_class("mw-bottom")
        self.btn_back = Gtk.Button(label=self.t("S_W_BACK"))
        self.btn_next = Gtk.Button(label=self.t("S_NEXT"))
        self.btn_next.get_style_context().add_class("suggested-action")
        self.btn_back.connect("clicked", lambda *a: self.go(-1))
        self.btn_next.connect("clicked", lambda *a: self.go(+1))
        self.btn_cancel = Gtk.Button(label=self.t("S_CANCEL"))
        self.btn_cancel.connect("clicked", lambda *a: self._on_delete())
        bottom.pack_start(self.btn_cancel, False, False, 0)
        bottom.pack_end(self.btn_next, False, False, 0)
        bottom.pack_end(self.btn_back, False, False, 0)
        right.pack_start(bottom, False, False, 0)
        self.root.pack_start(right, True, True, 0)

        self.pages = {}
        self.pages["welcome"] = self.page_welcome()
        self.pages["variant"] = self.page_variant()
        self.pages["layout"] = self.page_layout()
        self.pages["wall"] = self.page_wall()
        self.pages["accent"] = self.page_accent()
        self.pages["buttons"] = self.page_buttons()
        self.pages["extras"] = self.page_extras()
        self.pages["summary"] = self.page_summary()
        self.pages["remove"] = self.page_remove()
        self.pages["run"] = self.page_run()
        for k, w in self.pages.items():
            self.stack.add_named(w, k)
        self.hb.set_title(self.t("S_TITLE"))
        self.root.show_all()
        self.cur = getattr(self, "cur", "welcome")
        self.show_page(self.cur)

    def _logo_path(self):
        # Produkt-Logo (Monterra-Squircle); fehlt es, das schlichte Logo in Blau
        lp = os.path.join(WZ, "logo.svg")
        if not os.path.exists(lp):
            sys.path.insert(0, os.path.join(ROOT, "source", "tools"))
            try:
                from splash import LOGO
                svg = LOGO.replace("{color}", "#0A84FF")
            except Exception:
                svg = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"/>'
            lp = os.path.join(TMP, "logo.svg")
            open(lp, "w").write(svg)
        return lp

    def flow(self):
        if self.c["mode"] == "uninstall":
            return ["welcome", "remove", "run"]
        return ["welcome", "variant", "layout", "wall", "accent", "buttons", "extras", "summary", "run"]

    def step_title(self, k):
        return {
            "welcome": "S_W_STEP_WELCOME", "variant": "S_W_STEP_VARIANT", "layout": "S_W_STEP_LAYOUT",
            "wall": "S_W_STEP_WALL", "accent": "S_W_STEP_ACCENT", "buttons": "S_W_STEP_BUTTONS",
            "extras": "S_W_STEP_EXTRAS", "summary": "S_W_STEP_SUMMARY", "remove": "S_W_STEP_CONFIRM",
            "run": "S_W_STEP_INSTALL" if self.c["mode"] == "install" else "S_W_STEP_REMOVE",
        }[k]

    def refresh_sidebar(self):
        for r in self.step_rows:
            self.sidebar.remove(r)
        self.step_rows = []
        fl = self.flow()
        idx = fl.index(self.cur)
        finished = getattr(self, "finished_ok", False)
        for i, k in enumerate(fl):
            row = Gtk.Box(spacing=10)
            row.get_style_context().add_class("mw-step")
            state = "current" if i == idx else "done" if i < idx else "todo"
            if finished:
                state = "done"
            row.get_style_context().add_class(state)
            bub = label("✓" if state == "done" else str(i + 1), "mw-bubble", wrap=False, xalign=0.5)
            row.pack_start(bub, False, False, 0)
            row.pack_start(label(self.t(self.step_title(k)), wrap=False), False, False, 0)
            self.sidebar.pack_start(row, False, False, 0)
            self.step_rows.append(row)
        self.sidebar.show_all()

    def show_page(self, key):
        self.cur = key
        if key == "summary":
            self.fill_summary()
        if key in ("layout", "wall", "accent", "buttons"):
            self.update_variant_images()
        self.stack.set_visible_child_name(key)
        self.refresh_sidebar()
        fl = self.flow()
        i = fl.index(key)
        self.btn_back.set_visible(0 < i and key != "run")
        self.btn_cancel.set_visible(key != "run")
        if key == "summary":
            self.btn_next.set_label(self.t("S_W_INSTALL"))
        elif key == "remove":
            self.btn_next.set_label(self.t("S_W_REMOVE"))
            self.btn_next.get_style_context().add_class("destructive-action")
        elif key == "run":
            self.btn_next.set_label(self.t("S_W_CLOSE"))
        else:
            self.btn_next.set_label(self.t("S_NEXT"))
        if key != "remove":
            self.btn_next.get_style_context().remove_class("destructive-action")
        self.btn_next.set_sensitive(key != "run" or not self.running)

    def go(self, d):
        fl = self.flow()
        i = fl.index(self.cur)
        if self.cur == "run":
            if not self.running:
                Gtk.main_quit()
            return
        if d > 0 and self.cur in ("summary", "remove"):
            self.start_run()
            return
        j = max(0, min(len(fl) - 1, i + d))
        self.show_page(fl[j])

    # ------------------------------------------------------------ Seiten
    def page_frame(self, title, desc):
        sc = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=30)
        box.set_margin_top(26)
        sc.add(box)
        if title:
            box.pack_start(label(title, "mw-title"), False, False, 0)
        if desc:
            d = label(para(desc), "mw-desc", width=80)
            d.set_margin_bottom(12)
            box.pack_start(d, False, False, 0)
        sc.body = box
        return sc

    def card_content(self, image, title, desc, badge=None, width=None):
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        if image is not None:
            v.pack_start(image, False, False, 0)
        h = Gtk.Box(spacing=8)
        h.pack_start(label(title, "mw-card-title", wrap=True, width=28), False, False, 0)
        if badge:
            b = label(badge, "mw-badge", wrap=False, xalign=0.5)
            b.set_valign(Gtk.Align.CENTER)
            h.pack_start(b, False, False, 0)
        v.pack_start(h, False, False, 0)
        if desc:
            v.pack_start(label(desc, "mw-card-desc", width=(width or 300) // 7), False, False, 0)
        return v

    def page_welcome(self):
        p = self.page_frame(None, None)
        self.hero = RoundedImage(os.path.join(WZ, f"hero-{self.vs()}.jpg"), 720, radius=16, height=212)
        self.hero.set_halign(Gtk.Align.START)
        p.body.pack_start(self.hero, False, False, 6)
        p.body.pack_start(label(self.t("S_W_WELCOME_T"), "mw-title"), False, False, 6)
        p.body.pack_start(label(self.t("S_W_WELCOME_D"), "mw-desc", width=86), False, False, 0)

        lrow = Gtk.Box(spacing=12, margin_top=14, margin_bottom=10)
        lrow.pack_start(label(self.t("S_W_LANGUAGE"), "mw-card-title", wrap=False), False, False, 0)
        combo = Gtk.ComboBoxText()
        for code, name in (("de", "Deutsch"), ("en", "English"), ("es", "Español")):
            combo.append(code, name)
        combo.set_active_id(self.lang)
        combo.connect("changed", self._on_lang)
        lrow.pack_start(combo, False, False, 0)
        p.body.pack_start(lrow, False, False, 0)

        items = []
        for key, icon, t, d in (("install", "mode-install", "S_W_MODE_INSTALL_T", "S_W_MODE_INSTALL_D"),
                                ("uninstall", "mode-remove", "S_W_MODE_REMOVE_T", "S_W_MODE_REMOVE_D")):
            h = Gtk.Box(spacing=12)
            h.pack_start(SvgImage(os.path.join(WZ, f"extra-{icon}.svg"), 44), False, False, 0)
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            v.pack_start(label(self.t(t), "mw-card-title", width=30), False, False, 0)
            v.pack_start(label(self.t(d), "mw-card-desc", width=38), False, False, 0)
            h.pack_start(v, True, True, 0)
            h.set_size_request(320, -1)
            items.append((key, h))
        p.body.pack_start(card_group(items, self.c["mode"], self._on_mode, columns=2), False, False, 0)
        return p

    def _on_lang(self, combo):
        code = combo.get_active_id()
        if code and code != self.lang:
            self.lang = code
            try:
                os.makedirs(os.path.expanduser("~/.config"), exist_ok=True)
                open(os.path.expanduser("~/.config/monterra-sprache.conf"), "w").write(code + "\n")
            except OSError:
                pass
            GLib.idle_add(self.build)

    def _on_mode(self, key):
        self.c["mode"] = key
        self.refresh_sidebar()

    def page_variant(self):
        p = self.page_frame(self.t("S_W_VARIANT_T"), self.t("S_W_VARIANT_D"))
        items = []
        for key, t, d in (("light", "S_W_LIGHT_T", "S_W_LIGHT_D"), ("dark", "S_W_DARK_T", "S_W_DARK_D")):
            img = RoundedImage(os.path.join(WZ, f"variant-{key}.jpg"), 330, radius=10)
            items.append((key, self.card_content(img, self.t(t), self.t(d), width=330)))
        p.body.pack_start(card_group(items, self.c["variant"], self._on_variant), False, False, 0)
        return p

    def _on_variant(self, key):
        self.c["variant"] = key
        self.apply_look()
        self.update_variant_images()

    def page_layout(self):
        p = self.page_frame(self.t("S_W_LAYOUT_T"), self.t("S_W_LAYOUT_D"))
        self.layout_imgs = {}
        items = []
        for key, t, d in (("menubar-dock", "S_W_LAYOUT_MD_T", "S_W_LAYOUT_MD_D"),
                          ("menubar-panel", "S_W_LAYOUT_MP_T", "S_W_LAYOUT_MP_D"),
                          ("dock-only", "S_W_LAYOUT_DO_T", "S_W_LAYOUT_DO_D"),
                          ("keep", "S_W_LAYOUT_KEEP_T", "S_W_LAYOUT_KEEP_D")):
            img = RoundedImage(os.path.join(WZ, f"layout-{key}-{self.vs()}.svg"), 300, radius=12)
            self.layout_imgs[key] = img
            badge = self.t("S_W_RECOMMENDED") if key == "menubar-dock" else None
            items.append((key, self.card_content(img, self.t(t), self.t(d), badge=badge, width=300)))
        p.body.pack_start(card_group(items, self.c["layout"], lambda k: self.c.__setitem__("layout", k)), False, False, 0)
        return p

    def page_wall(self):
        p = self.page_frame(self.t("S_W_WALL_T"), self.t("S_W_WALL_D"))
        self.wall_imgs = {}
        items = []
        for key in MOTIF_KEYS + ["keep"]:
            f = MOTIF_FILE.get(key, "keep")
            img = RoundedImage(os.path.join(PV, "picker", f"motif-{f}-{'Dark' if self.dark() else 'Light'}.png"), 196, radius=10)
            self.wall_imgs[key] = img
            name = self.motif_name(key) if key != "keep" else self.t("S_WALL_KEEP")
            items.append((key, self.card_content(img, name, None, width=196)))
        p.body.pack_start(card_group(items, self.c["wall"], self._on_wall, columns=3), False, False, 0)
        return p

    def _on_wall(self, key):
        self.c["wall"] = key
        if self.c["accent"] == "match":
            self.apply_look()
        self.update_accent_preview()

    def page_accent(self):
        p = self.page_frame(self.t("S_W_ACCENT_T"), self.t("S_W_ACCENT_D"))
        h = Gtk.Box(spacing=28)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        grid = Gtk.Grid(column_spacing=6, row_spacing=6)
        group = None
        self.swatches = {}
        for i, key in enumerate(["match"] + COLOR_KEYS):
            rb = Gtk.RadioButton.new_from_widget(group)
            group = group or rb
            rb.set_mode(False)
            rb.get_style_context().add_class("mw-swatch")
            da = Gtk.DrawingArea()
            da.set_size_request(34, 34)
            da.connect("draw", self._draw_swatch, key)
            rb.add(da)
            rb.set_tooltip_text(self.t("S_W_ACCENT_MATCH") if key == "match" else self.color_name(key))
            rb.set_active(key == self.c["accent"])
            rb.connect("toggled", lambda b, k=key: b.get_active() and self._on_accent(k))
            grid.attach(rb, i % 7, i // 7, 1, 1)
            self.swatches[key] = da
        left.pack_start(grid, False, False, 0)
        self.accent_name = label("", "mw-card-title")
        left.pack_start(self.accent_name, False, False, 6)
        h.pack_start(left, False, False, 0)
        self.accent_img = RoundedImage(os.path.join(PV, "picker", f"accent-blue-{self.vs()}.png"), 360, radius=12)
        h.pack_start(self.accent_img, False, False, 0)
        p.body.pack_start(h, False, False, 0)
        self.update_accent_preview()
        return p

    def _hex(self, key):
        return accent.BASE[accent.normalize(key)][1 if self.dark() else 0]

    def _draw_swatch(self, da, cr, key):
        w, h = da.get_allocated_width(), da.get_allocated_height()
        r = min(w, h) / 2
        if key == "match":
            # halb/halb: passende Farbe + Regenbogen-Ring als „automatisch“
            cols = ["#FF453A", "#FF9F0A", "#FFD60A", "#30D158", "#64D2FF", "#0A84FF", "#BF5AF2"]
            import math
            for i, c in enumerate(cols):
                cr.move_to(w / 2, h / 2)
                cr.arc(w / 2, h / 2, r, i * 2 * math.pi / len(cols), (i + 1) * 2 * math.pi / len(cols))
                cr.close_path()
                cr.set_source_rgb(*[int(c[j:j + 2], 16) / 255 for j in (1, 3, 5)])
                cr.fill()
            c = self._hex(self.match_color())
            cr.arc(w / 2, h / 2, r * 0.58, 0, 6.2832)
        else:
            c = self._hex(key)
            cr.arc(w / 2, h / 2, r, 0, 6.2832)
        cr.set_source_rgb(*[int(c[j:j + 2], 16) / 255 for j in (1, 3, 5)])
        cr.fill()
        return False

    def _on_accent(self, key):
        self.c["accent"] = key
        self.apply_look()
        self.update_accent_preview()

    def update_accent_preview(self):
        if not hasattr(self, "accent_img"):
            return
        k = self.accent_key()
        self.accent_img.set_path(os.path.join(PV, "picker", f"accent-{k}-{self.vs()}.png"))
        txt = self.color_name(k)
        if self.c["accent"] == "match":
            txt = f"{self.t('S_W_ACCENT_MATCH')} – {txt}"
        self.accent_name.set_text(txt)
        for da in self.swatches.values():
            da.queue_draw()

    def page_buttons(self):
        p = self.page_frame(self.t("S_W_BUTTONS_T"), self.t("S_W_BUTTONS_D"))
        self.btn_preview = Gtk.DrawingArea()
        self.btn_preview.set_size_request(560, 150)
        self.btn_preview.set_halign(Gtk.Align.START)
        self.btn_preview.connect("draw", self._draw_buttons)
        p.body.pack_start(self.btn_preview, False, False, 4)
        adj = Gtk.Adjustment(value=self.c["buttons"], lower=14, upper=32, step_increment=2, page_increment=2)
        sc = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj, digits=0)
        sc.set_size_request(560, -1)
        sc.set_halign(Gtk.Align.START)
        for v in range(14, 33, 2):
            sc.add_mark(v, Gtk.PositionType.BOTTOM, f"{v}" if v in (14, 16, 22, 28, 32) else None)
        sc.connect("format-value", lambda s, v: f"{int(round(v / 2) * 2)} px")
        sc.connect("value-changed", self._on_buttons)
        p.body.pack_start(sc, False, False, 6)
        return p

    def _on_buttons(self, sc):
        v = int(round(sc.get_value() / 2) * 2)
        if v != self.c["buttons"]:
            self.c["buttons"] = v
            self.btn_preview.queue_draw()

    def _draw_buttons(self, da, cr):
        W, H = da.get_allocated_width(), da.get_allocated_height()
        dark = self.dark()
        def rr(x, y, w, h, r):
            cr.new_sub_path()
            cr.arc(x + w - r, y + r, r, -1.5708, 0); cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
            cr.arc(x + r, y + h - r, r, 1.5708, 3.1416); cr.arc(x + r, y + r, r, 3.1416, 4.7124)
            cr.close_path()
        # Fenster
        rr(1, 1, W - 2, H - 2, 12)
        cr.set_source_rgb(*((0.17, 0.17, 0.18) if dark else (1, 1, 1)))
        cr.fill_preserve()
        cr.set_source_rgba(*((1, 1, 1, 0.10) if dark else (0, 0, 0, 0.12)))
        cr.set_line_width(1)
        cr.stroke()
        bar = 52
        cr.save(); rr(1, 1, W - 2, H - 2, 12); cr.clip()
        cr.rectangle(0, 0, W, bar)
        cr.set_source_rgb(*((0.23, 0.23, 0.24) if dark else (0.95, 0.95, 0.96)))
        cr.fill()
        cr.restore()
        s = self.c["buttons"]
        x = 20
        for col in ((1.0, 0.37, 0.34), (1.0, 0.74, 0.18), (0.16, 0.78, 0.25)):
            cr.arc(x + s / 2, bar / 2, s / 2, 0, 6.2832)
            cr.set_source_rgb(*col)
            cr.fill()
            x += s + max(6, s * 0.45)
        cr.set_source_rgba(*((1, 1, 1, 0.85) if dark else (0, 0, 0, 0.75)))
        cr.select_font_face("Inter", SLANT, BOLD)
        cr.set_font_size(13)
        txt = f"{self.t('S_W_PREVIEW')} · {s} px"
        ext = cr.text_extents(txt)
        cr.move_to((W - ext.width) / 2, bar / 2 + ext.height / 2 - 1)
        cr.show_text(txt)
        cr.set_source_rgba(*((1, 1, 1, 0.10) if dark else (0, 0, 0, 0.08)))
        for i in range(3):
            rr(28, bar + 22 + i * 22, (W - 56) * (0.8 - i * 0.18), 9, 4.5)
            cr.fill()
        return False

    def page_extras(self):
        p = self.page_frame(self.t("S_W_EXTRAS_T"), self.t("S_W_EXTRAS_D"))
        lb = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        lb.get_style_context().add_class("mw-list")
        lb.set_size_request(700, -1)
        lb.set_halign(Gtk.Align.START)
        for key, tk, dk, pw in EXTRAS:
            row = Gtk.ListBoxRow(activatable=False)
            h = Gtk.Box(spacing=14)
            h.pack_start(SvgImage(os.path.join(WZ, f"extra-{key}.svg"), 40), False, False, 0)
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            v.set_valign(Gtk.Align.CENTER)
            v.pack_start(label(self.t(tk) + ("  🔒" if pw else ""), "mw-card-title", width=50), False, False, 0)
            v.pack_start(label(self.t(dk), "mw-card-desc", width=70), False, False, 0)
            h.pack_start(v, True, True, 0)
            sw = Gtk.Switch(active=key in self.c["extras"])
            sw.set_valign(Gtk.Align.CENTER)
            sw.connect("notify::active", lambda s, _p, k=key: self._on_extra(k, s.get_active()))
            h.pack_end(sw, False, False, 0)
            row.add(h)
            lb.add(row)
        p.body.pack_start(lb, False, False, 0)
        return p

    def _on_extra(self, key, on):
        (self.c["extras"].add if on else self.c["extras"].discard)(key)

    def password_box(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=18)
        box.pack_start(label("🔒  " + self.t("S_W_PW_T"), "mw-card-title"), False, False, 0)
        box.pack_start(label(self.t("S_W_PW_D"), "mw-card-desc", width=80), False, False, 0)
        entry = Gtk.Entry(visibility=False, input_purpose=Gtk.InputPurpose.PASSWORD)
        entry.set_size_request(320, -1)
        entry.set_halign(Gtk.Align.START)
        entry.connect("activate", lambda *a: self.go(+1))
        box.pack_start(entry, False, False, 0)
        err = label("", "mw-error")
        box.pack_start(err, False, False, 0)
        skip = Gtk.CheckButton(label=self.t("S_W_PW_SKIP"))
        box.pack_start(skip, False, False, 0)
        skip.connect("toggled", lambda b: entry.set_sensitive(not b.get_active()))
        box.entry, box.err, box.skip = entry, err, skip
        return box

    def page_summary(self):
        p = self.page_frame(self.t("S_W_SUMMARY_T"), self.t("S_W_SUMMARY_D"))
        self.sum_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        p.body.pack_start(self.sum_box, False, False, 0)
        self.pw_install = self.password_box()
        p.body.pack_start(self.pw_install, False, False, 0)
        return p

    def fill_summary(self):
        for ch in self.sum_box.get_children():
            self.sum_box.remove(ch)
        h = Gtk.Box(spacing=24)
        img = RoundedImage(os.path.join(PV, "picker", f"motif-{MOTIF_FILE.get(self.c['wall'], 'keep')}-{'Dark' if self.dark() else 'Light'}.png"), 260, radius=12)
        img.set_valign(Gtk.Align.START)
        h.pack_start(img, False, False, 0)
        g = Gtk.Grid(column_spacing=18, row_spacing=8)
        lay = {"menubar-dock": "S_W_LAYOUT_MD_T", "menubar-panel": "S_W_LAYOUT_MP_T", "dock-only": "S_W_LAYOUT_DO_T", "keep": "S_W_LAYOUT_KEEP_T"}
        rows = [
            ("S_SUM_VARIANT", self.t("S_W_DARK_T") if self.dark() else self.t("S_W_LIGHT_T")),
            ("S_SUM_LAYOUT", self.t(lay[self.c["layout"]])),
            ("S_SUM_WALL", self.motif_name(self.c["wall"]) if self.c["wall"] != "keep" else self.t("S_SUM_WALL_KEEP")),
            ("S_SUM_ACCENT", self.color_name(self.accent_key())),
            ("S_SUM_BUTTONS", f"{self.c['buttons']} px"),
        ]
        for i, (k, v) in enumerate(rows):
            g.attach(label(self.t(k), "mw-sum-key", wrap=False), 0, i, 1, 1)
            g.attach(label(v, "mw-sum-val", width=40), 1, i, 1, 1)
        h.pack_start(g, False, False, 0)
        self.sum_box.pack_start(h, False, False, 0)
        self.sum_box.pack_start(label(self.t("S_SUM_EXTRAS"), "mw-card-title"), False, False, 6)
        fb = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=4, column_spacing=6, row_spacing=6)
        chosen = [e for e in EXTRAS if e[0] in self.c["extras"]]
        for key, tk, _dk, _pw in chosen:
            chip = Gtk.Box(spacing=6)
            chip.get_style_context().add_class("mw-chip")
            chip.pack_start(SvgImage(os.path.join(WZ, f"extra-{key}.svg"), 18), False, False, 0)
            chip.pack_start(label(self.t(tk), wrap=False), False, False, 0)
            fb.add(chip)
        if not chosen:
            fb.add(label(self.t("S_L_NONE"), wrap=False))
        fb.set_size_request(700, -1)
        fb.set_halign(Gtk.Align.START)
        self.sum_box.pack_start(fb, False, False, 0)
        self.sum_box.show_all()
        self.pw_install.set_visible(self.needs_password())

    def page_remove(self):
        p = self.page_frame(self.t("S_W_REMOVE_T"), None)
        h = Gtk.Box(spacing=18)
        h.pack_start(SvgImage(os.path.join(WZ, "extra-mode-remove.svg"), 56), False, False, 0)
        h.pack_start(label(self.t("S_W_REMOVE_D"), "mw-desc", width=74), False, False, 0)
        p.body.pack_start(h, False, False, 0)
        self.pw_remove = self.password_box()
        p.body.pack_start(self.pw_remove, False, False, 0)
        return p

    def page_run(self):
        p = self.page_frame(None, None)
        self.run_icon = SvgImage(os.path.join(WZ, "extra-mode-install.svg"), 64)
        self.run_icon.set_halign(Gtk.Align.START)
        p.body.pack_start(self.run_icon, False, False, 4)
        self.run_title = label("", "mw-title")
        p.body.pack_start(self.run_title, False, False, 4)
        self.run_desc = label(self.t("S_W_RUN_D"), "mw-desc", width=80)
        p.body.pack_start(self.run_desc, False, False, 0)
        self.run_bar = Gtk.ProgressBar()
        self.run_bar.set_size_request(640, -1)
        self.run_bar.set_halign(Gtk.Align.START)
        self.run_bar.set_margin_top(18)
        p.body.pack_start(self.run_bar, False, False, 0)
        self.run_step = label("", "mw-big-step", width=80)
        p.body.pack_start(self.run_step, False, False, 6)
        self.run_fail = label("", "mw-error", width=80)
        p.body.pack_start(self.run_fail, False, False, 0)
        exp = Gtk.Expander(label=self.t("S_W_DETAILS"))
        exp.set_margin_top(8)
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(700, 220)
        self.run_log = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.run_log.get_style_context().add_class("mw-log")
        sw.add(self.run_log)
        exp.add(sw)
        p.body.pack_start(exp, False, False, 0)
        self.run_scroll = sw
        return p

    # ------------------------------------------------------------ Ausführen
    def start_run(self):
        pwbox = self.pw_remove if self.c["mode"] == "uninstall" else self.pw_install
        pw = ""
        if self.needs_password() and not pwbox.skip.get_active():
            pw = pwbox.entry.get_text()
            if pw:
                pwbox.err.set_text(self.t("S_W_PW_CHECKING"))
                while Gtk.events_pending():
                    Gtk.main_iteration()
                if not self.check_password(pw):
                    pwbox.err.set_text(self.t("S_W_PW_WRONG"))
                    pwbox.entry.grab_focus()
                    pwbox.entry.select_region(0, -1)
                    return
            pwbox.err.set_text("")
        self.password = pw
        self.write_answers()
        self.show_page("run")
        self.running = True
        self.btn_next.set_sensitive(False)
        inst = self.c["mode"] == "install"
        self.run_title.set_text(self.t("S_W_RUN_INSTALL") if inst else self.t("S_W_RUN_REMOVE"))
        self.total = self.estimate_steps()
        self.done = 0
        self.failed = []
        self.info_text = ""
        self.run_bar.set_fraction(0.02)
        env = dict(os.environ)
        env["XDG_DATA_DIRS"] = env["XDG_DATA_DIRS"].replace(TMP + ":", "")
        self.proc = subprocess.Popen(["bash", os.path.join(ROOT, "setup.sh"), "--answers=" + self.answers],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, bufsize=1, env=env, cwd=ROOT)
        try:
            self.proc.stdin.write((self.password or "") + "\n")
            self.proc.stdin.close()
        except OSError:
            pass
        self.password = ""
        threading.Thread(target=self._reader, daemon=True).start()
        GLib.timeout_add(120, self._pulse)

    def check_password(self, pw):
        try:
            r = subprocess.run(["sudo", "-S", "-k", "-p", "", "-v"], input=pw + "\n", text=True,
                               capture_output=True, timeout=20)
            return r.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def estimate_steps(self):
        if self.c["mode"] == "uninstall":
            return 12
        n = 2
        if self.c["layout"].startswith("menubar"):
            n += 1
        if self.c["layout"] in ("menubar-dock", "dock-only"):
            n += 1
        n += len(self.c["extras"]) + 1
        return max(n, 3)

    def write_answers(self):
        q = shlex.quote
        self.answers = os.path.join(TMP, "answers.sh")
        with open(self.answers, "w") as f:
            f.write(f"LANG_SEL={q(self.lang)}\nMODE={q(self.c['mode'])}\nVARIANT={q(self.c['variant'])}\n"
                    f"LAYOUT={q(self.c['layout'])}\nWALL={q(self.c['wall'])}\nAKZ={q(self.c['accent'])}\n"
                    f"BUTTONS={int(self.c['buttons'])}\nEXTRAS={q(':'.join(k for k, *_ in EXTRAS if k in self.c['extras']))}\n")

    def _reader(self):
        for line in self.proc.stdout:
            GLib.idle_add(self._on_line, line.rstrip("\n"))
        self.proc.wait()
        GLib.idle_add(self._on_finished, self.proc.returncode)

    def _on_line(self, line):
        buf = self.run_log.get_buffer()
        if line.startswith("@@STEP "):
            self.done += 1
            self.run_step.set_text(line[7:])
            self.run_bar.set_fraction(min(0.95, self.done / (self.total + 1)))
        elif line.startswith("@@FAIL "):
            self.failed.append(line[7:])
        elif line.startswith("@@INFO "):
            self.info_text = line[7:]
        elif line.startswith("@@DONE"):
            pass
        else:
            buf.insert(buf.get_end_iter(), line + "\n")
            adj = self.run_scroll.get_vadjustment()
            GLib.idle_add(lambda: adj.set_value(adj.get_upper()) or False)
        return False

    def _pulse(self):
        return self.running

    def _on_finished(self, code):
        self.running = False
        self.btn_next.set_sensitive(True)
        self.btn_next.set_label(self.t("S_W_CLOSE"))
        self.run_bar.set_fraction(1.0)
        inst = self.c["mode"] == "install"
        if self.failed or code not in (0, None):
            self.run_icon.path = os.path.join(WZ, "extra-warning.svg")
            self.run_title.set_text(self.t("S_W_FAILED_T"))
            self.run_desc.set_text(self.t("S_W_FAILED_D"))
            self.run_fail.set_text("\n".join("• " + f for f in self.failed))
        else:
            self.run_icon.path = os.path.join(WZ, "extra-done.svg")
            self.run_title.set_text(self.t("S_W_DONE_T") if inst else self.t("S_W_REMOVED_T"))
            text = para(self.info_text or (self.t("S_I_DONE") if inst else self.t("S_UN_DONE")))
            parts = text.split("\n\n")
            if inst and len(parts) > 1:      # erster Absatz („Fertig – … eingerichtet!“) steht schon als Überschrift da
                text = "\n\n".join(parts[1:])
            self.run_desc.set_text(text)
            self.finished_ok = True
            self.run_bar.hide()
        self.run_icon._load()
        self.run_step.set_text("")
        self.refresh_sidebar()
        return False

    def _on_delete(self, *a):
        if self.running:
            d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                                  buttons=Gtk.ButtonsType.YES_NO, text=self.t("S_W_QUIT_Q"))
            r = d.run()
            d.destroy()
            if r != Gtk.ResponseType.YES:
                return True
        Gtk.main_quit()
        return False

    def update_variant_images(self):
        vs = self.vs()
        if hasattr(self, "layout_imgs"):
            for k, img in self.layout_imgs.items():
                img.set_path(os.path.join(WZ, f"layout-{k}-{vs}.svg"))
        if hasattr(self, "wall_imgs"):
            for k, img in self.wall_imgs.items():
                img.set_path(os.path.join(PV, "picker", f"motif-{MOTIF_FILE.get(k, 'keep')}-{'Dark' if self.dark() else 'Light'}.png"))
        if hasattr(self, "hero"):
            self.hero.set_path(os.path.join(WZ, f"hero-{vs}.jpg"))
        self.update_accent_preview()
        if hasattr(self, "btn_preview"):
            self.btn_preview.queue_draw()


def main():
    lang = None
    for a in sys.argv[1:]:
        if a.startswith("--lang="):
            lang = a.split("=", 1)[1]
    if lang not in ("de", "en", "es"):
        try:
            lang = open(os.path.expanduser("~/.config/monterra-sprache.conf")).read().strip()
        except OSError:
            lang = ""
    if lang not in ("de", "en", "es"):
        env = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
        lang = "en" if env.startswith("en") else "es" if env.startswith("es") else "de"
    if os.geteuid() == 0 and not os.environ.get("MONTERRA_TEST"):
        print(load_lang(lang).get("S_NO_SUDO", "Please run without sudo.").replace("\\n", "\n"))
        return 1
    win = Wizard(lang)
    win.show_all()
    # nur zum Testen: --page=NAME öffnet direkt eine Seite, --variant=dark wählt die Variante vor
    for a in sys.argv[1:]:
        if a.startswith("--mode="):
            win.c["mode"] = a.split("=", 1)[1]
        if a.startswith("--variant="):
            win._on_variant(a.split("=", 1)[1])
        if a.startswith("--extras="):
            win.c["extras"] = set(x for x in a.split("=", 1)[1].split(",") if x)
        if a.startswith("--page="):
            win.cur = a.split("=", 1)[1]
    win.show_page(win.cur)
    if "--autostart" in sys.argv:
        GLib.timeout_add(1500, lambda: win.start_run() or False)
    Gtk.main()
    if win.proc and win.proc.poll() is None:
        win.proc.terminate()
    shutil.rmtree(TMP, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
