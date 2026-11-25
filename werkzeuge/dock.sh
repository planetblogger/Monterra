#!/bin/bash
# =====================================================================
#  Monterra Dock – installieren / entfernen (ohne sudo)
#
#     bash werkzeuge/dock.sh                  -> Dock installieren und einschalten
#     bash werkzeuge/dock.sh --ohne-panel     -> zusätzlich das untere Panel entfernen
#                                              (das Dock ersetzt es; wird gesichert)
#     bash werkzeuge/dock.sh --remove         -> Dock entfernen, Panel ggf. zurückholen
#
#  Das Dock ist eine Cinnamon-Erweiterung: kein eigenes Programm, kein Autostart.
# =====================================================================
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
UUID="monterra-dock@monterra"
DEST="$HOME/.local/share/cinnamon/extensions/$UUID"
PANEL_BACKUP="$HOME/.config/monterra-dock-panels.txt"

if [ "$(id -u)" -eq 0 ]; then
  echo "Bitte ohne sudo starten – das Dock wird nur für deinen Benutzer eingerichtet."; exit 1
fi

# Liste in einer gsettings-Variablen ergänzen/entfernen (per Python, damit nichts kaputtgeht)
edit_list() {   # $1 = add|remove  $2 = key  $3 = value
  python3 - "$1" "$2" "$3" <<'PY'
import ast, subprocess, sys
op, key, val = sys.argv[1:]
cur = subprocess.run(["gsettings", "get", "org.cinnamon", key], capture_output=True, text=True).stdout.strip()
cur = cur.replace("@as ", "")
items = ast.literal_eval(cur) if cur else []
if op == "add" and val not in items:
    items.append(val)
if op == "remove":
    items = [i for i in items if i != val]
subprocess.run(["gsettings", "set", "org.cinnamon", key, str(items)], check=True)
PY
}

if [ "$1" = "--remove" ]; then
  edit_list remove enabled-extensions "$UUID"
  rm -rf "$DEST"
  rm -f "$HOME"/.local/share/locale/*/LC_MESSAGES/"$UUID".mo
  if [ -f "$PANEL_BACKUP" ]; then
    while IFS='=' read -r key value; do
      [ -n "$key" ] && gsettings set org.cinnamon "$key" "$value"
    done < "$PANEL_BACKUP"
    rm -f "$PANEL_BACKUP"
    echo "Unteres Panel wiederhergestellt."
  fi
  echo "Monterra Dock entfernt."
  exit 0
fi

if [ ! -f "$ROOT/komponenten/dock/$UUID/extension.js" ]; then
  echo "Ordner 'dock/$UUID' nicht gefunden – bitte im entpackten Monterra-Ordner ausführen."; exit 1
fi

# 1) Erweiterung kopieren
mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -r "$ROOT/komponenten/dock/$UUID" "$DEST"

# Übersetzungen (Deutsch, Spanisch) – Cinnamon sucht sie in ~/.local/share/locale
for mo in "$DEST"/locale/*/LC_MESSAGES/"$UUID".mo; do
  [ -f "$mo" ] || continue
  lang=$(basename "$(dirname "$(dirname "$mo")")")
  mkdir -p "$HOME/.local/share/locale/$lang/LC_MESSAGES"
  cp "$mo" "$HOME/.local/share/locale/$lang/LC_MESSAGES/"
done

# 2) Optional: untere Panels entfernen (Dock übernimmt deren Aufgabe)
if [ "$1" = "--ohne-panel" ]; then
  if [ ! -f "$PANEL_BACKUP" ]; then
    {
      for key in panels-enabled panels-height panels-autohide enabled-applets; do
        echo "$key=$(gsettings get org.cinnamon $key)"
      done
    } > "$PANEL_BACKUP"
  fi
  python3 - <<'PY'
import ast, subprocess
def get(k):
    v = subprocess.run(["gsettings", "get", "org.cinnamon", k], capture_output=True, text=True).stdout.strip()
    return ast.literal_eval(v.replace("@as ", "")) if v else []
def put(k, v):
    subprocess.run(["gsettings", "set", "org.cinnamon", k, str(v)], check=True)
panels = get("panels-enabled")
bottom = [p.split(":")[0] for p in panels if p.endswith(":bottom")]
if not bottom:
    print("Kein unteres Panel gefunden – nichts zu tun.")
elif len(bottom) == len(panels):
    print("Das untere Panel ist dein einziges Panel – es bleibt erhalten (sonst fehlen Uhr, Netzwerk usw.).")
else:
    put("panels-enabled", [p for p in panels if not p.endswith(":bottom")])
    put("enabled-applets", [a for a in get("enabled-applets") if a.split(":")[0] not in ("panel" + b for b in bottom)])
    print("Unteres Panel entfernt (gesichert in ~/.config/monterra-dock-panels.txt).")
PY
fi

# 3) Einschalten – Cinnamon lädt die Erweiterung sofort
edit_list add enabled-extensions "$UUID"

echo
echo "Fertig. Das Monterra Dock erscheint unten in der Bildschirmmitte."
echo "Programme anheften: Rechtsklick auf ein Symbol im Dock → „Im Dock behalten“"
echo "                    oder im Menü Rechtsklick → „Zu Favoriten hinzufügen“."
echo "Einstellungen:      Rechtsklick auf ein Symbol → „Dock-Einstellungen …“"
echo "Entfernen:          bash werkzeuge/dock.sh --remove"
