#!/usr/bin/env python3
"""
Monterra – Auswahl mit Vorschaubildern (für den Installer).

  image_picker.py --title T --text FRAGE --ok WEITER --cancel ABBRECHEN [--default KEY] [--columns 3]
                 KEY BILD BESCHRIFTUNG  [KEY BILD BESCHRIFTUNG …]

Gibt den gewählten KEY aus. Abbrechen: Rückgabewert 1. Doppelklick oder Enter wählt sofort.
"""
import argparse
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gtk  # noqa: E402

CSS = b"""
.monterra-pick flowboxchild { padding: 8px; border-radius: 14px; }
.monterra-pick flowboxchild:selected { background-color: alpha(@theme_selected_bg_color, 0.22); }
.monterra-pick flowboxchild:selected label { color: @theme_fg_color; font-weight: bold; }
.monterra-pick .question { font-size: 1.08em; }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="Monterra")
    ap.add_argument("--text", default="")
    ap.add_argument("--ok", default="OK")
    ap.add_argument("--cancel", default="Cancel")
    ap.add_argument("--default", default="")
    ap.add_argument("--columns", type=int, default=3)
    ap.add_argument("--thumb", type=int, default=0, help="Breite der Vorschaubilder in Pixeln (0 = nach Spaltenzahl)")
    ap.add_argument("items", nargs="*")
    a = ap.parse_args()
    if len(a.items) % 3 or not a.items:
        print("Einträge: KEY BILD BESCHRIFTUNG …", file=sys.stderr)
        return 2
    items = [a.items[i:i + 3] for i in range(0, len(a.items), 3)]
    if not a.thumb:
        a.thumb = 240 if a.columns <= 3 else 200 if a.columns == 4 else 176

    prov = Gtk.CssProvider()
    prov.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    dlg = Gtk.Dialog(title=a.title)
    dlg.set_default_size(min(1100, a.columns * (a.thumb + 40) + 60), -1)
    dlg.set_position(Gtk.WindowPosition.CENTER)
    dlg.get_style_context().add_class("monterra-pick")
    dlg.add_button(a.cancel, Gtk.ResponseType.CANCEL)
    okb = dlg.add_button(a.ok, Gtk.ResponseType.OK)
    okb.get_style_context().add_class("suggested-action")
    dlg.set_default_response(Gtk.ResponseType.OK)

    box = dlg.get_content_area()
    box.set_spacing(12)
    box.set_border_width(16)
    q = Gtk.Label(label=a.text.replace("\\n", "\n"), xalign=0)
    q.set_line_wrap(True)
    q.set_max_width_chars(80)
    q.get_style_context().add_class("question")
    box.pack_start(q, False, False, 0)

    fb = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.SINGLE, homogeneous=True,
                     max_children_per_line=a.columns, min_children_per_line=min(a.columns, len(items)),
                     column_spacing=6, row_spacing=6, activate_on_single_click=False)
    keys = []
    default_child = None
    for key, img, label in items:
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(img, a.thumb, -1, True)
            v.pack_start(Gtk.Image.new_from_pixbuf(pb), False, False, 0)
        except Exception:
            v.pack_start(Gtk.Image.new_from_icon_name("image-missing", Gtk.IconSize.DIALOG), False, False, 0)
        lab = Gtk.Label(label=label, justify=Gtk.Justification.CENTER)
        lab.set_line_wrap(True)
        lab.set_max_width_chars(28)
        v.pack_start(lab, False, False, 0)
        fb.add(v)
        keys.append(key)
    for child in fb.get_children():
        if keys[child.get_index()] == a.default:
            default_child = child
    fb.connect("child-activated", lambda f, c: dlg.response(Gtk.ResponseType.OK))

    sw = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
    sw.set_propagate_natural_height(True)
    sw.set_max_content_height(560)
    sw.add(fb)
    box.pack_start(sw, True, True, 0)
    dlg.show_all()
    start = default_child or fb.get_child_at_index(0)
    start.grab_focus()               # Fokus zuerst, sonst wählt GTK das erste Bild aus
    fb.select_child(start)

    resp = dlg.run()
    sel = fb.get_selected_children()
    if resp != Gtk.ResponseType.OK or not sel:
        return 1
    print(keys[sel[0].get_index()])
    return 0


if __name__ == "__main__":
    sys.exit(main())
