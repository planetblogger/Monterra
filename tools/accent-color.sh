#!/bin/bash
# =====================================================================
#  Monterra – Akzentfarbe wählen (ohne sudo)
#
#     bash tools/accent-color.sh green       -> Akzentfarbe Grün
#     bash tools/accent-color.sh             -> zeigt die aktuelle Farbe und alle Möglichkeiten
#
#  Farben: Blue Indigo Purple Pink Red Orange Yellow Green Teal Cyan Brown Grey Graphite
#  (deutsche und spanische Namen wie „gruen“ oder „verde“ gehen ebenfalls)
#
#  Jede Akzentfarbe ist ein eigenes Theme (wie bei Mint-Y): „Monterra“ und „Monterra-Dark“
#  sind Blue, die anderen heißen z. B. „Monterra-Green“ und „Monterra-Dark-Green“.
#  Alle stehen in den Systemeinstellungen unter Themen → Anwendungen zur Auswahl.
#  Wird dort ein Monterra-Theme gewählt, zieht ein kleiner Abgleich im Hintergrund
#  (accent-sync.sh) Desktop-Theme, Fensterrahmen, Ordnerfarbe, Firefox und Thunderbird nach.
#
#  --files-only  installiert nur die Themes und merkt sich die Farbe (wird von setup.sh benutzt)
# =====================================================================
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
CONF="$HOME/.config/monterra-akzent.conf"
DATA="$HOME/.local/share/monterra"
PY="${MONTERRA_PY:-python3}"

FARBE=""; ONLY_FILES=0
for a in "$@"; do
  case "$a" in
    --files-only|--nur-dateien) ONLY_FILES=1 ;;
    -h|--help) sed -n 2,18p "$0"; exit 0 ;;
    *) FARBE="$a" ;;
  esac
done
if [ -z "$FARBE" ]; then
  if [ "$ONLY_FILES" = 1 ]; then
    FARBE="$(cat "$CONF" 2>/dev/null || echo Blue)"
  else
    echo "Aktuelle Akzentfarbe: $(cat "$CONF" 2>/dev/null || echo Blue)"
    echo "Möglich: $("$PY" "$HERE/accent.py" --list)"
    echo "Beispiel: bash tools/accent-color.sh green"
    exit 0
  fi
fi
eval "$("$PY" "$HERE/accent.py" "$FARBE")" || exit 1     # setzt AKZENT_NAME, AKZENT_FOLDERS …

theme_name() {   # $1 = Monterra | Monterra-Dark, $2 = Akzentfarbe
  if [ "$2" = Blue ]; then echo "$1"; else echo "$1-$2"; fi
}

# Themes mit deutschen Farbnamen früherer Versionen (bis 1.1, z. B. „Monterra-Dark-Gruen“) entfernen
for t in Monterra Monterra-Dark; do
  for old in Lila Rot Gelb Gruen Petrol Braun Grau Graphit; do rm -rf "$HOME/.themes/$t-$old"; done
done

# 1) alle Akzent-Themes installieren: Blue vollständig, die übrigen teilen sich unveränderte
#    Dateien per Hardlink mit Blue (spart rund 80 % Platz) und bekommen nur ihre eigenen Dateien
mkdir -p "$HOME/.themes"
for t in Monterra Monterra-Dark; do
  [ -d "$ROOT/themes/$t" ] || continue
  rm -rf "$HOME/.themes/$t"
  cp -r "$ROOT/themes/$t" "$HOME/.themes/"
  for a in $("$PY" "$HERE/accent.py" --list); do
    [ "$a" = Blue ] && continue
    n="$(theme_name "$t" "$a")"; d="$HOME/.themes/$n"
    rm -rf "$d"
    cp -al "$HOME/.themes/$t" "$d" 2>/dev/null || cp -r "$HOME/.themes/$t" "$d"
    [ -d "$ROOT/themes/accents/$a/$t" ] && cp -r --remove-destination "$ROOT/themes/accents/$a/$t/." "$d/"
    # eigener Name (sed -i legt neue Dateien an – die Hardlinks zu Blue bleiben unberührt)
    sed -i "s/^Name=.*/Name=$n/; s/^GtkTheme=.*/GtkTheme=$n/; s/^MetacityTheme=.*/MetacityTheme=$n/" "$d/index.theme"
    [ -f "$d/metacity-1/metacity-theme-3.xml" ] && sed -i "s#<name>$t</name>#<name>$n</name>#" "$d/metacity-1/metacity-theme-3.xml"
  done
done
mkdir -p "$(dirname "$CONF")"
echo "$AKZENT_NAME" > "$CONF"

# gewählte Größe der Fensterknöpfe in alle Themes eintragen
if [ -f "$HOME/.config/monterra-buttons.conf" ]; then
  MONTERRA_NO_RELOAD=1 bash "$HERE/window-buttons.sh" "$(cat "$HOME/.config/monterra-buttons.conf")" >/dev/null 2>&1 || true
fi

# 2) Abgleich im Hintergrund einrichten (Auswahl in den Systemeinstellungen → alles passt sich an)
mkdir -p "$DATA" "$HOME/.config/autostart"
cp "$HERE/accent.py" "$HERE/accent-sync.sh" "$DATA/"
# Abgleich früherer Versionen (deutsche Dateinamen) ablösen
pkill -f "monterra/akzent-sync.sh" 2>/dev/null || true
rm -f "$DATA/akzent.py" "$DATA/akzent-sync.sh" "$HOME/.config/autostart/monterra-akzent-sync.desktop"
echo "$ROOT" > "$HOME/.config/monterra-paket.conf"
cat > "$HOME/.config/autostart/monterra-accent-sync.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Monterra Akzentfarbe
Name[en]=Monterra accent colour
Name[es]=Color de acento de Monterra
Comment=Gleicht Desktop-Theme, Ordnerfarbe, Firefox und Thunderbird an das gewählte Monterra-Theme an
Exec=bash "$DATA/accent-sync.sh"
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF
if [ -n "$DISPLAY$WAYLAND_DISPLAY" ] && command -v gsettings >/dev/null; then
  pkill -f "monterra/accent-sync.sh" 2>/dev/null || true
  (setsid bash "$DATA/accent-sync.sh" >/dev/null 2>&1 &) || true
fi
[ "$ONLY_FILES" = 1 ] && exit 0

# 3) gewähltes Theme einschalten (hell/dunkel wie bisher)
CUR="$(gsettings get org.cinnamon.desktop.interface gtk-theme | tr -d "'")"
case "$CUR" in Monterra-Dark*) BASE=Monterra-Dark ;; *) BASE=Monterra ;; esac
NAME="$(theme_name "$BASE" "$AKZENT_NAME")"
if [ "$CUR" = "$NAME" ]; then              # gleiches Theme neu laden (Dateien wurden ersetzt)
  gsettings set org.cinnamon.desktop.interface gtk-theme 'Mint-Y'; sleep 0.3
fi
gsettings set org.cinnamon.desktop.interface gtk-theme "$NAME"
gsettings set org.cinnamon.desktop.wm.preferences theme "$NAME"
CT="$(gsettings get org.cinnamon.theme name | tr -d "'")"
[ "$CT" = "$NAME" ] && { gsettings set org.cinnamon.theme name 'cinnamon'; sleep 0.3; }
gsettings set org.cinnamon.theme name "$NAME"

# 4) Ordnersymbole in der Akzentfarbe (nur wenn Monterra-Symbole aktiv sind)
IT="$(gsettings get org.cinnamon.desktop.interface icon-theme | tr -d "'")"
if [ "${IT#Monterra}" != "$IT" ] && [ "$IT" != "Monterra-Local" ] && [ -d "$HOME/.icons/$AKZENT_FOLDERS" ]; then
  gsettings set org.cinnamon.desktop.interface icon-theme "$AKZENT_FOLDERS"
fi

# 5) Firefox / Thunderbird nachziehen, falls dort das Monterra-Theme installiert ist
[ -f "$HOME/.config/monterra-firefox.conf" ] && bash "$HERE/firefox.sh" --quiet >/dev/null 2>&1 || true
[ -f "$HOME/.config/monterra-thunderbird.conf" ] && bash "$HERE/thunderbird.sh" --quiet >/dev/null 2>&1 || true

# Programme mit libadwaita (z. B. neuere GNOME-Apps) übernehmen die Farbe über den
# Desktop-Portal-Dienst automatisch; zur Sicherheit auch den Ersatzwert setzen:
if gsettings list-keys org.x.apps.portal 2>/dev/null | grep -qx accent-rgb; then
  gsettings set org.x.apps.portal accent-rgb "$AKZENT_LIGHT" 2>/dev/null || true
fi
echo "Akzentfarbe: $AKZENT_NAME (Theme „$NAME“)"
