#!/bin/bash
# =====================================================================
#  Monterra Fenstergröße – installieren / entfernen (ohne sudo)
#
#     bash werkzeuge/fenstergroesse.sh           -> einrichten und einschalten
#     bash werkzeuge/fenstergroesse.sh --remove  -> wieder entfernen
#
#  Kleine Cinnamon-Erweiterung: merkt sich für jedes Programm Größe und Position
#  des Fensters (auch „maximiert“) und stellt sie beim nächsten Öffnen wieder her –
#  Cinnamon selbst merkt sich das nicht. Daten:
#  ~/.config/monterra/fenstergroessen.json (beim Entfernen gelöscht)
# =====================================================================
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
UUID="monterra-fenstergroesse@monterra"
DEST="$HOME/.local/share/cinnamon/extensions/$UUID"

if [ "$(id -u)" -eq 0 ]; then
  echo "Bitte ohne sudo starten."; exit 1
fi

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
  rm -rf "$DEST" "$HOME/.config/monterra/fenstergroessen.json"
  echo "Monterra Fenstergröße entfernt."
  exit 0
fi

if [ ! -f "$ROOT/komponenten/fenstergroesse/$UUID/extension.js" ]; then
  echo "Ordner 'komponenten/fenstergroesse/$UUID' nicht gefunden – bitte im entpackten Monterra-Ordner ausführen."; exit 1
fi
mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -r "$ROOT/komponenten/fenstergroesse/$UUID" "$DEST"
# bei einem Update: einmal aus- und wieder einschalten, damit Cinnamon die neue Fassung lädt
edit_list remove enabled-extensions "$UUID"
sleep 0.5
edit_list add enabled-extensions "$UUID"
echo "Monterra Fenstergröße eingeschaltet – Fenster öffnen künftig in der zuletzt benutzten Größe."
