#!/usr/bin/env python3
"""
Kontrastprüfung für GTK 3: baut viele typische Fenster und Bedienelemente auf
(Dialoge, Dateiauswahl, Menüs, Seitenleisten, Listen, Kopfleisten, Tooltips …),
liest für jedes Element und jeden Zustand Schrift- und Hintergrundfarbe aus dem Theme
und meldet Stellen mit zu wenig Kontrast.

  contrast_gtk3.py THEME   -> Liste "Kontrast  Zustand  Elementpfad  Schrift / Hintergrund"
"""
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402

THEME = sys.argv[1]
settings = Gtk.Settings.get_default()
settings.set_property("gtk-theme-name", THEME)

S = Gtk.StateFlags
STATES = {
    "normal": S.NORMAL,
    "hover": S.PRELIGHT,
    "aktiv": S.ACTIVE,
    "gewählt": S.SELECTED,
    "gewählt+hover": S.SELECTED | S.PRELIGHT,
    "fokus": S.FOCUSED,
    "inaktiv-fenster": S.BACKDROP,
    "gewählt+inaktiv-fenster": S.SELECTED | S.BACKDROP,
    "checked": S.CHECKED,
}


def lum(c):
    def ch(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def over(top, bottom):
    a = top[3]
    return tuple(top[i] * a + bottom[i] * (1 - a) for i in range(3)) + (1.0,)


def rgba(c):
    return (c.red, c.green, c.blue, c.alpha)


def bg_of(ctx, state):
    c = ctx.get_property("background-color", state)
    img = ctx.get_property("background-image", state)
    return rgba(c), img is not None


def effective_bg(widget, state):
    """Hintergrund unter dem Element: von innen nach außen zusammensetzen."""
    layers = []
    w = widget
    st = state
    while w is not None:
        ctx = w.get_style_context()
        c, has_img = bg_of(ctx, st if w is widget else (ctx.get_state() | (st & S.BACKDROP)))
        layers.append((c, has_img, w))
        if c[3] >= 0.99:
            break
        w = w.get_parent()
        st = state
    base = (1, 1, 1, 1) if lum(layers[-1][0][:3]) > 0.5 or layers[-1][0][3] < 0.99 else layers[-1][0]
    col = layers[-1][0] if layers[-1][0][3] >= 0.99 else base
    for c, _img, _w in reversed(layers[:-1]):
        col = over(c, col)
    image = any(img for _c, img, _w in layers)
    return col, image


results = []
seen = set()


def check(widget, tag, states=("normal", "hover", "gewählt", "inaktiv-fenster")):
    ctx = widget.get_style_context()
    for name in states:
        flags = STATES[name]
        old = ctx.get_state()
        ctx.set_state(flags)
        fg = rgba(ctx.get_color(flags))
        bg, img = effective_bg(widget, flags)
        ctx.set_state(old)
        if fg[3] < 0.3:
            continue
        fgc = over(fg, bg)
        r = ratio(fgc[:3], bg[:3])
        path = ctx.get_path().to_string()
        key = (path, name)
        if key in seen:
            continue
        seen.add(key)
        results.append((r, name, tag, path, fgc, bg, img))


def hexc(c):
    return "#%02X%02X%02X" % tuple(round(v * 255) for v in c[:3])


def walk(w, tag, states=None):
    kids = []
    if isinstance(w, Gtk.Container):
        kids = w.get_children()
        try:
            kids += [c for c in w.get_internal_children()] if hasattr(w, "get_internal_children") else []
        except Exception:
            pass
    if isinstance(w, (Gtk.Label, Gtk.Entry, Gtk.TextView, Gtk.Image, Gtk.AccelLabel)):
        check(w, tag, states or ("normal", "hover", "gewählt", "inaktiv-fenster"))
    for k in kids:
        walk(k, tag, states)


def forall(w, fn):
    fn(w)
    if isinstance(w, Gtk.Container):
        w.forall(lambda c: forall(c, fn))


def scan(top, tag):
    def fn(w):
        if isinstance(w, (Gtk.Label, Gtk.Entry, Gtk.Image, Gtk.TextView)):
            check(w, tag, ("normal", "hover", "inaktiv-fenster"))
        if isinstance(w, Gtk.Button):
            check(w, tag + " (Knopf)", ("normal", "hover", "aktiv", "inaktiv-fenster"))
    forall(top, fn)


# ------------------------------------------------------------------ Fenster bauen
windows = []


def win(title, child, csd=False, cls=()):
    w = Gtk.Window(title=title)
    for c in cls:
        w.get_style_context().add_class(c)
    if csd:
        hb = Gtk.HeaderBar(title=title, subtitle="Untertitel", show_close_button=True)
        for t in ("Zurück", "Teilen"):
            hb.pack_start(Gtk.Button(label=t))
        sb = Gtk.Button(label="Fertig")
        sb.get_style_context().add_class("suggested-action")
        hb.pack_end(sb)
        w.set_titlebar(hb)
    w.add(child)
    w.show_all()
    windows.append(w)
    return w


# 1) Allgemeine Bedienelemente
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
for txt, cls in (("Normal", None), ("Vorgeschlagen", "suggested-action"), ("Löschen", "destructive-action"),
                 ("Flach", "flat")):
    b = Gtk.Button(label=txt)
    if cls:
        b.get_style_context().add_class(cls)
    box.add(b)
lnk = Gtk.Box()
lnk.get_style_context().add_class("linked")
for t in ("Links", "Mitte", "Rechts"):
    lnk.add(Gtk.ToggleButton(label=t))
box.add(lnk)
box.add(Gtk.Entry(text="Eingabe"))
box.add(Gtk.CheckButton(label="Kontrollkästchen"))
box.add(Gtk.RadioButton(label="Optionsfeld"))
cb = Gtk.ComboBoxText()
cb.append_text("Auswahl")
cb.set_active(0)
box.add(cb)
box.add(Gtk.LinkButton(uri="https://x", label="Verweis"))
sp = Gtk.SpinButton.new_with_range(0, 10, 1)
box.add(sp)
pb = Gtk.ProgressBar(text="50 %", show_text=True, fraction=0.5)
box.add(pb)
for typ in (Gtk.MessageType.INFO, Gtk.MessageType.WARNING, Gtk.MessageType.ERROR, Gtk.MessageType.QUESTION):
    ib = Gtk.InfoBar(message_type=typ)
    ib.get_content_area().add(Gtk.Label(label=f"Hinweis {typ.value_nick}"))
    ib.add_button("Knopf", 1)
    box.add(ib)
nb = Gtk.Notebook()
nb.append_page(Gtk.Label(label="Seite"), Gtk.Label(label="Reiter 1"))
nb.append_page(Gtk.Label(label="Seite"), Gtk.Label(label="Reiter 2"))
box.add(nb)
ss = Gtk.StackSwitcher()
st = Gtk.Stack()
st.add_titled(Gtk.Label(label="a"), "a", "Erste")
st.add_titled(Gtk.Label(label="b"), "b", "Zweite")
ss.set_stack(st)
box.add(ss)
box.add(st)
sbar = Gtk.Statusbar()
sbar.push(0, "Statuszeile")
box.add(sbar)
tb = Gtk.Toolbar()
tb.insert(Gtk.ToolButton(label="Werkzeug"), 0)
box.add(tb)
mb = Gtk.MenuBar()
mi = Gtk.MenuItem(label="Datei")
mb.append(mi)
box.add(mb)
w1 = win("Bedienelemente", box, csd=True)
w2 = win("Bedienelemente SSD", Gtk.Label(label="Systemrahmen"), csd=False)

# 2) Listen / Baumansicht mit gewählter Zeile
store = Gtk.ListStore(str, str)
for r in ("Dokumente", "Bilder", "Musik"):
    store.append([r, "Ordner"])
tv = Gtk.TreeView(model=store)
for i, t in enumerate(("Name", "Art")):
    tv.append_column(Gtk.TreeViewColumn(t, Gtk.CellRendererText(), text=i))
tv.get_selection().select_path(Gtk.TreePath(1))
lb = Gtk.ListBox()
for t in ("Zeile 1", "Zeile 2"):
    lb.add(Gtk.Label(label=t))
lb.select_row(lb.get_row_at_index(0))
side = Gtk.PlacesSidebar()
hb = Gtk.Box()
hb.add(side)
hb.add(tv)
hb.add(lb)
win("Listen", hb)

# 3) Nemo-ähnliches Fenster (Klassen wie in Nemo)
nemo_box = Gtk.Box()
nside = Gtk.TreeView(model=store)
nside.append_column(Gtk.TreeViewColumn("", Gtk.CellRendererText(), text=0))
nside.get_style_context().add_class("sidebar")
nside.get_selection().select_path(Gtk.TreePath(0))
nemo_box.add(nside)
iv = Gtk.IconView(model=store)
iv.set_text_column(0)
iv.select_path(Gtk.TreePath(2))
nemo_box.add(iv)
win("Nemo", nemo_box, cls=("nemo-window",))

# 4) Dialoge: Rückfrage mit Standardknopf (wie Nemo „Löschen“), Fortschritt
md = Gtk.MessageDialog(message_type=Gtk.MessageType.QUESTION, text="Endgültig löschen?",
                       secondary_text="Diese Datei wird gelöscht.")
md.add_button("Abbrechen", Gtk.ResponseType.CANCEL)
md.add_button("Löschen", Gtk.ResponseType.OK)
md.set_default_response(Gtk.ResponseType.OK)
md.show_all()
windows.append(md)

pd = Gtk.Window(title="Dateivorgänge")
pbx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
pbx.add(Gtk.Label(label="Kopiere 3 Dateien nach „Dokumente“"))
pbx.add(Gtk.ProgressBar(fraction=0.3))
pl = Gtk.Label(label="12 MB von 40 MB")
pl.get_style_context().add_class("dim-label")
pbx.add(pl)
pd.add(pbx)
pd.show_all()
windows.append(pd)

# 5) Dateiauswahl (Speichern)
fc = Gtk.FileChooserDialog(title="Speichern", action=Gtk.FileChooserAction.SAVE)
fc.add_button("Abbrechen", Gtk.ResponseType.CANCEL)
fc.add_button("Speichern", Gtk.ResponseType.ACCEPT)
fc.set_default_response(Gtk.ResponseType.ACCEPT)
fc.show_all()
windows.append(fc)

# 6) Menü, Popover, Tooltip
menu = Gtk.Menu()
for t in ("Öffnen", "Umbenennen …", "In den Papierkorb"):
    item = Gtk.MenuItem(label=t)
    menu.append(item)
chk = Gtk.CheckMenuItem(label="Versteckte Dateien")
menu.append(chk)
menu.show_all()
menu.popup_at_pointer(None) if False else None
pop = Gtk.Popover(relative_to=box.get_children()[0])
pbx2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
for t in ("Eintrag A", "Eintrag B"):
    m = Gtk.ModelButton(text=t)
    pbx2.add(m)
pop.add(pbx2)
pop.show_all()
tip = Gtk.Window(type=Gtk.WindowType.POPUP)
tip.get_style_context().add_class("tooltip")
tip.get_style_context().add_class("background")
tlabel = Gtk.Label(label="Kurzinfo")
tip.add(tlabel)
tip.set_name("gtk-tooltip")
tip.show_all()
windows.append(tip)

while Gtk.events_pending():
    Gtk.main_iteration()

for w in windows:
    scan(w, w.get_title() or "Kurzinfo")
for it in menu.get_children():
    for st_ in ("normal", "hover"):
        check(it.get_child(), "Menü", (st_,))
    check(it, "Menü (Eintrag)", ("normal", "hover"))
for m in pbx2.get_children():
    forall(m, lambda w: isinstance(w, Gtk.Label) and check(w, "Popover", ("normal", "hover")))
# gewählte Zeilen in Listen: Zellen werden mit dem Zustand der Liste gezeichnet
for v, tag in ((tv, "Liste"), (nside, "Nemo-Seitenleiste"), (iv, "Symbolansicht")):
    check(v, tag, ("normal", "gewählt", "gewählt+hover", "gewählt+inaktiv-fenster", "inaktiv-fenster"))
forall(side, lambda w: isinstance(w, Gtk.Label) and check(w, "Orte-Seitenleiste", ("normal", "hover")))
for row in lb.get_children():
    forall(row, lambda w: isinstance(w, Gtk.Label) and check(w, "ListBox", ("normal", "gewählt")))

LIMIT = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
bad = sorted((r for r in results if r[0] < LIMIT), key=lambda x: x[0])
for r, name, tag, path, fg, bg, img in bad:
    print(f"{r:5.2f}  {name:24} {tag:22} {hexc(fg)} auf {hexc(bg)}{' (Bild)' if img else ''}  {path[-110:]}")
print(f"# {len(results)} Prüfungen, {len(bad)} unter {LIMIT}", file=sys.stderr)
