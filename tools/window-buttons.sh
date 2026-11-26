#!/bin/bash
# =====================================================================
#  Monterra – Größe der Fensterknöpfe (Schließen, Minimieren, Maximieren)
#
#     bash tools/window-buttons.sh 16      -> Standard
#     bash tools/window-buttons.sh 22      -> z. B. 4K-Monitor ohne Skalierung
#     bash tools/window-buttons.sh         -> zuletzt gewählte Größe erneut anwenden
#
#  Größe von 14 bis 32 in 2er-Schritten. Die früheren Namen normal (16),
#  gross (22) und sehr-gross (28) gehen weiterhin.
#
#  Es wird nur ein kleiner CSS-Block im Monterra-Theme ersetzt. Cinnamon liest
#  dieselbe Datei für die Systemrahmen – die Größe gilt also für alle Fenster.
#  Die Wahl wird gemerkt und bei jeder Neuinstallation wieder angewendet. Kein sudo nötig.
# =====================================================================
HERE="$(cd "$(dirname "$0")" && pwd)"
CONF="$HOME/.config/monterra-buttons.conf"
PY="${MONTERRA_PY:-python3}"
SIZE="${1:-}"
[ -z "$SIZE" ] && [ -f "$CONF" ] && SIZE="$(cat "$CONF")"
case "$SIZE" in
  normal|"")                   SIZE=16 ;;
  gross|groß|large)            SIZE=22 ;;
  sehr-gross|sehr-groß|xlarge) SIZE=28 ;;
esac
if ! [[ "$SIZE" =~ ^[0-9]+$ ]] || [ "$SIZE" -lt 14 ] || [ "$SIZE" -gt 32 ] || [ $((SIZE % 2)) -ne 0 ]; then
  echo "Ungültige Größe: $SIZE (14, 16, 18 … 32)"; exit 1
fi

DIRS=()
for d in "$HOME"/.themes/Monterra "$HOME"/.themes/Monterra-*; do   # alle Akzent-Themes
  [ -f "$d/gtk-3.0/gtk.css" ] && DIRS+=("$d")
done
if [ ${#DIRS[@]} -eq 0 ]; then
  echo "Monterra-Theme ist nicht installiert."; exit 1
fi
"$PY" "$HERE/buttons.py" "$SIZE" "${DIRS[@]}" >/dev/null || exit 1
mkdir -p "$(dirname "$CONF")"
echo "$SIZE" > "$CONF"

[ -n "$MONTERRA_NO_RELOAD" ] && exit 0
# Theme neu laden (Programme und Fensterrahmen)
reload() {   # $1 = Schema, $2 = Schlüssel
  local cur; cur="$(gsettings get "$1" "$2" 2>/dev/null | tr -d "'")"
  case "$cur" in Monterra*) ;; *) return ;; esac
  gsettings set "$1" "$2" 'Mint-Y'; sleep 0.5
  gsettings set "$1" "$2" "$cur"
}
reload org.cinnamon.desktop.interface gtk-theme
reload org.cinnamon.desktop.wm.preferences theme
echo "Fensterknöpfe: Größe $SIZE"
