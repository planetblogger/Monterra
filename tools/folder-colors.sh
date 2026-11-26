#!/bin/bash
# =====================================================================
#  Monterra – Ordnerfarben im Nemo-Kontextmenü freischalten
#
#     bash tools/folder-colors.sh            -> einrichten (fragt nach dem Passwort)
#     bash tools/folder-colors.sh --remove   -> Registrierung wieder entfernen
#
#  Die farbigen Ordner-Symbole (Monterra-Red, -Orange, …) werden in ~/.icons
#  kopiert. Nemos Farbwähler liest seine Farbliste nur aus
#  /usr/share/folder-color-switcher/colors.d – dafür ist einmal sudo nötig.
# =====================================================================
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
TARGET=/usr/share/folder-color-switcher/colors.d/Monterra.json

if [ "$1" = "--remove" ]; then
  sudo rm -f "$TARGET"
  echo "Monterra-Farben aus dem Nemo-Farbwähler entfernt."
  echo "Bereits gefärbte Ordner behalten ihre Farbe, bis du im Farbwähler „x“ (Standard) wählst."
  nemo -q >/dev/null 2>&1 || true
  exit 0
fi

if [ "$(id -u)" -eq 0 ]; then
  echo "Bitte ohne sudo starten – die Symbole gehören in DEINEN Ordner ~/.icons. Das Skript fragt selbst nach dem Passwort."
  exit 1
fi

# 1) Farbige Ordner-Themes für den aktuellen Benutzer
mkdir -p "$HOME/.icons"
n=0
for d in "$ROOT"/icons/Monterra-*; do
  name=$(basename "$d")
  [ "$name" = "Monterra-Cursor" ] && continue
  rm -rf "$HOME/.icons/$name"
  cp -r "$d" "$HOME/.icons/"
  n=$((n + 1))
done
[ -d "$HOME/.icons/Monterra" ] || cp -r "$ROOT/icons/Monterra" "$HOME/.icons/"
echo "$n Ordnerfarben nach ~/.icons kopiert."

# 2) Farbwähler-Erweiterung vorhanden?
if [ ! -f /usr/share/nemo-python/extensions/nemo-folder-color-switcher.py ]; then
  echo "Installiere die Nemo-Erweiterung 'folder-color-switcher' …"
  sudo apt-get install -y folder-color-switcher \
    || echo "Hinweis: 'folder-color-switcher' konnte nicht installiert werden – bitte über die Anwendungsverwaltung nachinstallieren."
fi

# 3) Farben registrieren
sudo mkdir -p "$(dirname "$TARGET")"
sudo cp "$ROOT/components/folder-colors/Monterra.json" "$TARGET"
sudo chmod 644 "$TARGET"

# 4) Nemo neu starten, damit die Liste geladen wird
nemo -q >/dev/null 2>&1 || true

echo
echo "Fertig. Rechtsklick auf einen Ordner in Nemo zeigt jetzt die Monterra-Farbpunkte."
echo "Voraussetzung: Unter Systemeinstellungen → Themen ist bei „Symbole“ Monterra gewählt."
