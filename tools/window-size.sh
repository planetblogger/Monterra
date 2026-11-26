#!/bin/bash
# =====================================================================
#  Monterra Fenstergröße – installieren / entfernen (ohne sudo)
#
#     bash tools/window-size.sh           -> einrichten und einschalten
#     bash tools/window-size.sh --remove  -> wieder entfernen
#
#  Kleine Cinnamon-Erweiterung: merkt sich für jedes Programm Größe und Position
#  des Fensters (auch „maximiert“) und stellt sie beim nächsten Öffnen wieder her –
#  Cinnamon selbst merkt sich das nicht. Daten:
#  ~/.config/monterra/fenstergroessen.json (beim Entfernen gelöscht)
# =====================================================================
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
UUID="monterra-window-size@monterra"
DEST="$HOME/.local/share/cinnamon/extensions/$UUID"
OLD_UUID="monterra-fenstergroesse@monterra"     # Name bis Version 1.1

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
  edit_list remove enabled-extensions "$OLD_UUID"
  rm -rf "$DEST" "$(dirname "$DEST")/$OLD_UUID"
  rm -f "$HOME"/.local/share/locale/*/LC_MESSAGES/"$UUID".mo "$HOME/.config/monterra/fenstergroessen.json"
  echo "Monterra Fenstergröße entfernt."
  exit 0
fi

if [ ! -f "$ROOT/components/window-size/$UUID/extension.js" ]; then
  echo "Ordner 'components/window-size/$UUID' nicht gefunden – bitte im entpackten Monterra-Ordner ausführen."; exit 1
fi
mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -r "$ROOT/components/window-size/$UUID" "$DEST"
# Übersetzungen von Name und Beschreibung (Deutsch, Spanisch) für die Liste der Erweiterungen
for mo in "$DEST"/locale/*/LC_MESSAGES/"$UUID".mo; do
  [ -f "$mo" ] || continue
  lang=$(basename "$(dirname "$(dirname "$mo")")")
  mkdir -p "$HOME/.local/share/locale/$lang/LC_MESSAGES"
  cp "$mo" "$HOME/.local/share/locale/$lang/LC_MESSAGES/"
done
# frühere Fassung mit deutschem Namen ablösen
edit_list remove enabled-extensions "$OLD_UUID"
rm -rf "$(dirname "$DEST")/$OLD_UUID"
# bei einem Update: einmal aus- und wieder einschalten, damit Cinnamon die neue Fassung lädt
edit_list remove enabled-extensions "$UUID"
sleep 0.5
edit_list add enabled-extensions "$UUID"
echo "Monterra Fenstergröße eingeschaltet – Fenster öffnen künftig in der zuletzt benutzten Größe."
