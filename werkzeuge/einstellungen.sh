#!/bin/bash
# =====================================================================
#  Monterra – Systemeinstellungen: Symbole gleichmäßig ausrichten (ohne sudo)
#
#     bash werkzeuge/einstellungen.sh           -> einrichten
#     bash werkzeuge/einstellungen.sh --remove  -> wieder entfernen
#
#  Cinnamon baut in der Übersicht der Systemeinstellungen jede Gruppe als eigenes
#  Raster; dessen Spaltenbreite richtet sich nach dem längsten Namen der Gruppe –
#  die Symbole stehen deshalb nicht untereinander. Ein kleiner Starter in
#  ~/.local/bin ruft die unveränderten Systemeinstellungen auf und gibt allen
#  Gruppen dieselbe Spaltenbreite. Cinnamon selbst wird nicht verändert.
#  Der Menüeintrag „Systemeinstellungen“ startet ihn sofort; andere Wege (z. B. Rechtsklick
#  auf die Leiste) ab der nächsten Anmeldung, falls ~/.local/bin neu angelegt wurde.
# =====================================================================
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$(dirname "$HERE")/komponenten/einstellungen/cinnamon-settings"
DEST="$HOME/.local/bin/cinnamon-settings"
APPS="$HOME/.local/share/applications"
ENTRY="$APPS/cinnamon-settings.desktop"
SYS_ENTRY="/usr/share/applications/cinnamon-settings.desktop"
MARK="X-Monterra-Starter"

# Menüeintrag auf den Starter zeigen lassen (eine vorhandene eigene Kopie, z. B. von der
# Symbolwerkstatt, wird nur in der Exec-Zeile angepasst)
entry_on() {
  mkdir -p "$APPS"
  if [ ! -f "$ENTRY" ]; then
    [ -f "$SYS_ENTRY" ] || return 0
    cp "$SYS_ENTRY" "$ENTRY"
    echo "$MARK=neu" >> "$ENTRY"
  elif ! grep -q "^$MARK=" "$ENTRY"; then
    echo "$MARK=geaendert" >> "$ENTRY"
  fi
  sed -i "s#^Exec=cinnamon-settings#Exec=$DEST#" "$ENTRY"
}
entry_off() {
  [ -f "$ENTRY" ] || return 0
  if grep -q "^$MARK=neu" "$ENTRY"; then
    rm -f "$ENTRY"
  else
    sed -i "s#^Exec=$DEST#Exec=cinnamon-settings#; /^$MARK=/d" "$ENTRY"
  fi
}

if [ "$1" = "--remove" ]; then
  if [ -f "$DEST" ] && grep -q "Monterra – Starter für Cinnamons Systemeinstellungen" "$DEST"; then
    rm -f "$DEST"
  fi
  entry_off
  echo "Systemeinstellungen: Monterra-Ausrichtung entfernt."
  exit 0
fi

if [ -e "$DEST" ] && ! grep -q "Monterra – Starter für Cinnamons Systemeinstellungen" "$DEST" 2>/dev/null; then
  echo "Hinweis: $DEST gehört nicht zu Monterra – nichts verändert."; exit 0
fi
mkdir -p "$HOME/.local/bin"
NEW=0; case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) NEW=1 ;; esac
install -m 755 "$SRC" "$DEST"
entry_on
echo "Systemeinstellungen: Symbole werden gleichmäßig ausgerichtet."
[ "$NEW" = 1 ] && echo "   (über das Menü sofort, über andere Wege nach der nächsten Anmeldung)"
exit 0
