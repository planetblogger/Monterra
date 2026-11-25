#!/bin/bash
# =====================================================================
#  Monterra – optionales Einrichtungs-Skript für Linux Mint (Cinnamon)
#
#  Aufruf (im entpackten Ordner):
#     bash werkzeuge/setup.sh            -> Themes/Icons aktivieren, Knöpfe links, Schrift
#     bash werkzeuge/setup.sh --dark     -> wie oben, aber dunkle Variante
#     bash werkzeuge/setup.sh --layout   -> zusätzlich Panel-Layout (oben Menüleiste, unten Dock)
#     bash werkzeuge/setup.sh --motiv=wueste -> Hintergrundmotiv:
#              himmel (Blau/Indigo) · wueste (Orange/Gelb) · mars (Rot/Braun)
#              dschungel (Grün/Petrol/Cyan) · seide (Grau/Graphit) · bluete (Lila/Pink)
#              (--farbe=FARBE geht weiterhin und wählt das passende Motiv)
#     bash werkzeuge/setup.sh --akzent=gruen -> Akzentfarbe (Knöpfe, Auswahl, Ordner), Standard: Blau
#     bash werkzeuge/setup.sh --keep-wallpaper -> Hintergrundbild nicht ändern
#     bash werkzeuge/setup.sh --restore  -> vorherige Einstellungen wiederherstellen
#
#  Das Skript kopiert nichts nach /usr und braucht kein sudo.
# =====================================================================
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
BACKUP="$HOME/.config/monterra-backup.dconf"
VARIANT="Monterra"
LAYOUT=0
WALL="Himmel"
AKZENT=""
. "$HERE/motive.sh"
OLDCOLORS="Blau Indigo Lila Pink Rot Orange Gelb Gruen Petrol Cyan Braun Grau Graphit"

for arg in "$@"; do
  case "$arg" in
    --dark)    VARIANT="Monterra-Dark" ;;
    --layout)  LAYOUT=1 ;;
    --motiv=*|--farbe=*)
      WALL="$(motiv_von "${arg#*=}")"
      [ -n "$WALL" ] || { echo "Unbekanntes Motiv: ${arg#*=} (himmel, wueste, mars, dschungel, seide, bluete)"; exit 1; } ;;
    --waves|--dunes|--silk|--bloom) ;;      # frühere Motive – gibt es nicht mehr, Standard wird verwendet
    --keep-wallpaper) WALL="none" ;;
    --akzent=*) AKZENT="${arg#--akzent=}" ;;
    --restore)
      if [ -f "$BACKUP" ]; then
        dconf reset -f /org/cinnamon/ && dconf load /org/cinnamon/ < "$BACKUP"
        echo "Vorherige Cinnamon-Einstellungen wiederhergestellt ($BACKUP)."
      else
        echo "Keine Sicherung gefunden ($BACKUP)."
      fi
      exit 0 ;;
    -h|--help) sed -n 2,16p "$0"; exit 0 ;;
  esac
done

# 1) Dateien installieren (falls noch nicht manuell geschehen)
mkdir -p "$HOME/.themes" "$HOME/.icons"
# Themes in der gewählten Akzentfarbe (ohne Angabe: bisherige Wahl bzw. Blau)
bash "$HERE/akzentfarbe.sh" --nur-dateien $AKZENT
eval "$(python3 "$HERE/akzent.py" "$(cat "$HOME/.config/monterra-akzent.conf" 2>/dev/null || echo Blau)")"
# jede Akzentfarbe ist ein eigenes Theme: Monterra[-Dark] = Blau, sonst Monterra[-Dark]-<Farbe>
BASEVAR="$VARIANT"
[ "${AKZENT_NAME:-Blau}" != Blau ] && VARIANT="$BASEVAR-$AKZENT_NAME"
[ -d "$ROOT/icons/Monterra" ] && cp -r "$ROOT/icons/Monterra" "$HOME/.icons/"
for d in "$ROOT"/icons/Monterra-*; do   # Mauszeiger + farbige Ordner-Varianten
  [ -d "$d" ] && rm -rf "$HOME/.icons/$(basename "$d")" && cp -r "$d" "$HOME/.icons/"
done
# gewählte Größe der Fensterknöpfe (fensterknoepfe.sh) wieder anwenden
if [ -f "$HOME/.config/monterra-buttons.conf" ] && [ -f "$HERE/fensterknoepfe.sh" ]; then
  bash "$HERE/fensterknoepfe.sh" "$(cat "$HOME/.config/monterra-buttons.conf")" >/dev/null 2>&1 || true
fi
# Datei-URI für gsettings (Leerzeichen im Ordnernamen werden als %20 geschrieben)
file_uri() { python3 -c 'import pathlib, sys; print(pathlib.Path(sys.argv[1]).as_uri())' "$1"; }
WPDIR=""
if [ -d "$ROOT/hintergruende" ]; then
  PICDIR="$(xdg-user-dir PICTURES 2>/dev/null || echo "$HOME/Bilder")"
  WPDIR="$PICDIR/Monterra Wallpaper"
  mkdir -p "$WPDIR" && cp "$ROOT"/hintergruende/*.jpg "$WPDIR/" 2>/dev/null || true
  # früherer Ordnername „Monterra“: Monterra-Bilder umziehen, eingestellten Hintergrund mitnehmen
  OLDDIR="$PICDIR/Monterra"
  if [ -d "$OLDDIR" ]; then
    CUR_WP="$(gsettings get org.cinnamon.desktop.background picture-uri 2>/dev/null | tr -d "'")"
    for f in "$OLDDIR"/Monterra-*; do
      [ -f "$f" ] || continue
      mv -f "$f" "$WPDIR/"
      if [ "$CUR_WP" = "file://$f" ] || [ "$CUR_WP" = "$(file_uri "$f")" ]; then
        gsettings set org.cinnamon.desktop.background picture-uri "$(file_uri "$WPDIR/$(basename "$f")")"
      fi
    done
    rmdir "$OLDDIR" 2>/dev/null || true        # nur wenn leer – eigene Bilder bleiben unangetastet
  fi
  # Hintergründe früherer Monterra-Versionen entfernen (Farbwellen in 13 Farben, Hügel, Dünen, …)
  CUR_WP="$(gsettings get org.cinnamon.desktop.background picture-uri 2>/dev/null | tr -d "'")"
  OLD_IN_USE=""
  OLDFILES=("$WPDIR"/Monterra-Hills-* "$WPDIR"/Monterra-Dunes-* "$WPDIR"/Monterra-Silk-* "$WPDIR"/Monterra-Bloom-*
            "$WPDIR"/Monterra-Waves-* "$WPDIR"/Monterra-Light.png "$WPDIR"/Monterra-Dark.png)
  for c in $OLDCOLORS; do OLDFILES+=("$WPDIR/Monterra-$c-Hell.jpg" "$WPDIR/Monterra-$c-Dunkel.jpg"); done
  for old in "${OLDFILES[@]}"; do
    [ -f "$old" ] || continue
    if [ "$CUR_WP" = "file://$old" ] || [ "$CUR_WP" = "$(file_uri "$old")" ]; then   # eingestellt: neues Motiv merken
      c="$(basename "$old" | sed -n 's/^Monterra-\([A-Za-z]*\)-\(Hell\|Dunkel\)\.jpg$/\1/p')"
      OLD_IN_USE="$(motiv_von "$c")"; [ -n "$OLD_IN_USE" ] || OLD_IN_USE=Himmel
    fi
    rm -f "$old"
  done
  # war eines davon eingestellt, auf das passende neue Motiv wechseln (auch bei --keep-wallpaper)
  if [ -n "$OLD_IN_USE" ] && [ "$WALL" = "none" ]; then WALL="$OLD_IN_USE"; fi
fi
gtk-update-icon-cache -f -t "$HOME/.icons/Monterra" >/dev/null 2>&1 || true

# 2) Sicherung der aktuellen Einstellungen (nur beim ersten Mal)
if ! command -v dconf >/dev/null; then
  echo "Hinweis: 'dconf' nicht gefunden – es wird keine Sicherung angelegt (sudo apt install dconf-cli)."
elif [ ! -f "$BACKUP" ]; then
  mkdir -p "$(dirname "$BACKUP")"
  dconf dump /org/cinnamon/ > "$BACKUP"
  echo "Sicherung der bisherigen Einstellungen: $BACKUP"
fi

# 3) Themes aktivieren
gsettings set org.cinnamon.desktop.interface gtk-theme "$VARIANT"
gsettings set org.cinnamon.desktop.wm.preferences theme "$VARIANT"
gsettings set org.cinnamon.theme name "$VARIANT"
# Symbole: Monterra, Ordner in der Akzentfarbe
gsettings set org.cinnamon.desktop.interface icon-theme "${AKZENT_FOLDERS:-Monterra}"
gsettings set org.cinnamon.desktop.interface cursor-theme "Monterra-Cursor"
gsettings set org.gnome.desktop.interface cursor-theme "Monterra-Cursor" 2>/dev/null || true
if [ "$BASEVAR" = "Monterra-Dark" ]; then
  gsettings set org.x.apps.portal color-scheme 'prefer-dark' 2>/dev/null || true
else
  gsettings set org.x.apps.portal color-scheme 'prefer-light' 2>/dev/null || true
fi

# 4) Fensterknöpfe links (Schließen, Minimieren, Maximieren)
gsettings set org.cinnamon.desktop.wm.preferences button-layout 'close,minimize,maximize:'

# 5) Schrift: Inter (frei verfügbar, klar und gut lesbar)
if fc-list | grep -qi "Inter"; then
  gsettings set org.cinnamon.desktop.interface font-name 'Inter 10'
  gsettings set org.nemo.desktop font 'Inter 10' 2>/dev/null || true
  gsettings set org.cinnamon.desktop.wm.preferences titlebar-font 'Inter Bold 10'
  gsettings set org.gnome.desktop.interface document-font-name 'Inter 10' 2>/dev/null || true
else
  echo "Tipp: Für die passende Schrift 'sudo apt install fonts-inter' ausführen und das Skript erneut starten."
fi

# Fensterwechsler (Alt+Tab): große Programmsymbole in einer Reihe
gsettings set org.cinnamon alttab-switcher-style 'icons' 2>/dev/null || true

# Sperrbildschirm: große Uhr, Datum darunter, feste Position
gsettings set org.cinnamon.desktop.screensaver floating-widgets false 2>/dev/null || true
gsettings set org.cinnamon.desktop.screensaver use-custom-format true 2>/dev/null || true
gsettings set org.cinnamon.desktop.screensaver time-format '%H:%M' 2>/dev/null || true
gsettings set org.cinnamon.desktop.screensaver date-format '%A, %e. %B' 2>/dev/null || true
if fc-list | grep -qi "Inter"; then
  gsettings set org.cinnamon.desktop.screensaver font-time 'Inter Semi-Bold 88' 2>/dev/null || true
  gsettings set org.cinnamon.desktop.screensaver font-date 'Inter Medium 22' 2>/dev/null || true
  gsettings set org.cinnamon.desktop.screensaver font-message 'Inter 14' 2>/dev/null || true
fi

# 6) Hintergrundbild
if [ -n "$WPDIR" ] && [ "$WALL" != "none" ]; then
  [ "$BASEVAR" = "Monterra-Dark" ] && WP="Monterra-$WALL-Dunkel.jpg" || WP="Monterra-$WALL-Hell.jpg"
  WP="$WPDIR/$WP"
  [ -f "$WP" ] && gsettings set org.cinnamon.desktop.background picture-uri "$(file_uri "$WP")"
fi

# 7) Optional: Layout – Menüleiste oben, Dock unten (zentrierte Fensterliste)
if [ "$LAYOUT" = "1" ]; then
  gsettings set org.cinnamon panels-enabled "['1:0:top', '2:0:bottom']"
  gsettings set org.cinnamon panels-height "['1:28', '2:56']"
  gsettings set org.cinnamon panels-autohide "['1:false', '2:false']"
  # Werte sind JSON-Strings; 0 = automatisch an Panelhöhe anpassen
  gsettings set org.cinnamon panel-zone-icon-sizes "'[{\"panelId\": 1, \"left\": 0, \"center\": 0, \"right\": 0}, {\"panelId\": 2, \"left\": 0, \"center\": 0, \"right\": 0}]'"
  gsettings set org.cinnamon panel-zone-symbolic-icon-sizes "'[{\"panelId\": 1, \"left\": 16, \"center\": 16, \"right\": 16}, {\"panelId\": 2, \"left\": 28, \"center\": 28, \"right\": 28}]'"
  gsettings set org.cinnamon enabled-applets "['panel1:left:0:menu@cinnamon.org:0', 'panel1:right:0:systray@cinnamon.org:1', 'panel1:right:1:xapp-status@cinnamon.org:2', 'panel1:right:2:notifications@cinnamon.org:3', 'panel1:right:3:printers@cinnamon.org:4', 'panel1:right:4:removable-drives@cinnamon.org:5', 'panel1:right:5:keyboard@cinnamon.org:6', 'panel1:right:6:favorites@cinnamon.org:7', 'panel1:right:7:network@cinnamon.org:8', 'panel1:right:8:sound@cinnamon.org:9', 'panel1:right:9:power@cinnamon.org:10', 'panel1:right:10:calendar@cinnamon.org:11', 'panel2:center:0:grouped-window-list@cinnamon.org:12']"
  echo "Layout gesetzt (oben Menüleiste, unten Dock)."
fi

echo
echo "Fertig. Falls das Panel nicht sofort neu gezeichnet wird: Alt+F2, 'r' eingeben, Enter (Cinnamon neu starten)."
echo "Rückgängig machen: bash werkzeuge/setup.sh --restore"
