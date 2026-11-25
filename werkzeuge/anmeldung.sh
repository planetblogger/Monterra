#!/bin/bash
# =====================================================================
#  Monterra – Anmeldebildschirm (LightDM / Slick Greeter) einrichten
#
#     sudo bash werkzeuge/anmeldung.sh                 -> Blau, dunkle Fassung (Standard)
#     sudo bash werkzeuge/anmeldung.sh --day           -> helle Fassung
#     sudo bash werkzeuge/anmeldung.sh --motiv wueste  -> passend zum Desktop-Hintergrund:
#        himmel wueste mars dschungel seide bluete  (--farbe FARBE wählt das passende Motiv)
#     sudo bash werkzeuge/anmeldung.sh --remove  -> vorherigen Anmeldebildschirm wiederherstellen
#
#  Der Anmeldebildschirm läuft vor der Anmeldung und kann ~/.themes nicht
#  lesen. Deshalb werden Theme, Symbole, Mauszeiger und Hintergrund
#  systemweit nach /usr/share kopiert (Administratorrechte nötig).
# =====================================================================
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
if [ "$(id -u)" -ne 0 ]; then
  exec sudo bash "$0" "$@"
fi

CONF=/etc/lightdm/slick-greeter.conf
BACKUP=/etc/lightdm/slick-greeter.conf.monterra-backup
NOCONF=/etc/lightdm/.monterra-had-no-conf
BG=/usr/share/backgrounds/monterra

. "$HERE/motive.sh"
FARBE=Himmel; DAY=0; REMOVE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --remove) REMOVE=1 ;;
    --day|--light) DAY=1 ;;
    --farbe|--motiv) shift; FARBE="$(motiv_von "${1:-himmel}")" ;;
    --farbe=*|--motiv=*) FARBE="$(motiv_von "${1#*=}")" ;;
  esac
  shift
done
[ -n "$FARBE" ] || FARBE=Himmel

if [ "$REMOVE" = 1 ]; then
  if [ -f "$BACKUP" ]; then
    mv -f "$BACKUP" "$CONF"
    echo "Vorherige Einstellungen wiederhergestellt ($CONF)."
  elif [ -f "$NOCONF" ]; then
    rm -f "$CONF" "$NOCONF"
    echo "Monterra-Einstellungen entfernt (Standard von Linux Mint aktiv)."
  else
    echo "Keine Sicherung gefunden – $CONF bleibt unverändert."
  fi
  rm -rf /usr/share/themes/Monterra /usr/share/themes/Monterra-Dark \
         /usr/share/icons/Monterra /usr/share/icons/Monterra-Cursor "$BG"
  echo "Systemweite Monterra-Dateien entfernt. Wirksam nach dem nächsten Abmelden."
  exit 0
fi

for d in themes/Monterra themes/Monterra-Dark icons/Monterra icons/Monterra-Cursor komponenten/anmeldung; do
  if [ ! -e "$ROOT/$d" ]; then
    echo "'$d' nicht gefunden – bitte im entpackten Monterra-Ordner ausführen."; exit 1
  fi
done

# 1) Dateien systemweit bereitstellen
mkdir -p /usr/share/themes /usr/share/icons "$BG"
rm -rf /usr/share/themes/Monterra /usr/share/themes/Monterra-Dark /usr/share/icons/Monterra /usr/share/icons/Monterra-Cursor
cp -r "$ROOT/themes/Monterra" "$ROOT/themes/Monterra-Dark" /usr/share/themes/
cp -r "$ROOT/icons/Monterra" "$ROOT/icons/Monterra-Cursor" /usr/share/icons/
[ $DAY = 1 ] && V=Hell || V=Dunkel
IMG="Monterra-Login-$FARBE-$V.jpg"
[ -f "$ROOT/komponenten/anmeldung/$IMG" ] || { echo "$IMG fehlt im Paket."; exit 1; }
rm -f "$BG"/Monterra-Login-*.jpg          # nur das gewählte Bild systemweit ablegen
cp "$ROOT/komponenten/anmeldung/$IMG" "$BG/"
COLOR="$(awk -v f="$IMG" '$1 == f {print $2}' "$ROOT/komponenten/anmeldung/farben.txt")"
[ -n "$COLOR" ] || COLOR="#10143F"
chmod -R a+rX /usr/share/themes/Monterra* /usr/share/icons/Monterra* "$BG"
gtk-update-icon-cache -f -t /usr/share/icons/Monterra >/dev/null 2>&1 || true

# 2) Bisherige Konfiguration sichern (nur beim ersten Mal)
mkdir -p /etc/lightdm
if [ ! -f "$BACKUP" ] && [ ! -f "$NOCONF" ]; then
  if [ -f "$CONF" ]; then cp -a "$CONF" "$BACKUP"; else touch "$NOCONF"; fi
fi

# 3) Neue Konfiguration schreiben
WALL="$BG/$IMG"
FONT="Ubuntu 11"
fc-list | grep -qi "Inter" && FONT="Inter 11"

cat > "$CONF" <<EOF
[Greeter]
# Monterra – Anmeldebildschirm
background=$WALL
background-color=$COLOR
draw-user-backgrounds=false
draw-grid=false
show-hostname=false
content-align=center
theme-name=Monterra-Dark
icon-theme-name=Monterra
cursor-theme-name=Monterra-Cursor
cursor-theme-size=24
font-name=$FONT
clock-format=%a. %e. %b  %H:%M
logo=
EOF

# 4) Hinweis, falls ein anderer Greeter aktiv ist
if grep -rhs "^greeter-session" /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.d/ /usr/share/lightdm/lightdm.conf.d/ \
   | tail -1 | grep -qv "slick-greeter"; then
  echo "Hinweis: Es scheint ein anderer Anmeldebildschirm als 'slick-greeter' eingestellt zu sein."
fi

echo "Fertig. Der neue Anmeldebildschirm erscheint nach dem nächsten Abmelden oder Neustart."
echo "Feinheiten lassen sich danach unter Systemeinstellungen → Anmeldefenster anpassen."
echo "Rückgängig: sudo bash werkzeuge/anmeldung.sh --remove"
