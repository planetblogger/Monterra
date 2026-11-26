#!/bin/bash
# =====================================================================
#  Monterra – neue Programme automatisch anpassen
#
#     bash tools/auto-icons.sh            -> Automatik einschalten
#     bash tools/auto-icons.sh --remove   -> Automatik ausschalten
#     bash tools/auto-icons.sh --status   -> zeigen, ob sie aktiv ist
#
#  Sobald ein Programm oder eine Web-App neu installiert wird, bekommt es
#  automatisch ein Symbol in Monterra-Form – ohne dass du etwas tun musst:
#   • sofort nach der Installation (Überwachung der Programm-Ordner) und
#   • zusätzlich bei jeder Anmeldung (falls etwas verpasst wurde).
#  Bereits angepasste Programme werden nicht erneut bearbeitet; im Leerlauf
#  läuft nichts. Die nötigen Dateien werden nach ~/.local/share/monterra
#  kopiert – der entpackte Monterra-Ordner wird danach nicht mehr gebraucht.
#  Kein sudo nötig.
# =====================================================================
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/share/monterra/automatik"
AUTOSTART="$HOME/.config/autostart/monterra-automatik.desktop"
UNITS="$HOME/.config/systemd/user"
STAMP="$DEST/stand.txt"
LOG="$DEST/automatik.log"
PY="${MONTERRA_PY:-/usr/bin/python3}"

# Ordner, in denen Programme ihre Menü-Einträge ablegen (apt, Flatpak, Snap, Web-Apps)
WATCH=(
  "$HOME/.local/share/applications"
  "$HOME/.local/share/flatpak/exports/share/applications"
  "/var/lib/flatpak/exports/share/applications"
  "/var/lib/snapd/desktop/applications"
  "/usr/share/applications"
  "/usr/local/share/applications"
)

have_systemd() { systemctl --user show-environment >/dev/null 2>&1; }

# ------------------------------------------------------------------ Prüfung (läuft im Hintergrund)
if [ "$1" = "--check" ]; then
  [ "$2" = "--wait" ] && sleep 20          # Installation erst fertig werden lassen
  exec 9>"$DEST/.lock"; flock -n 9 || exit 0
  [ -d "$HOME/.icons/Monterra" ] || exit 0  # Monterra nicht (mehr) installiert
  sig() {
    for d in "${WATCH[@]}"; do
      [ -d "$d" ] && find "$d" -name '*.desktop' -printf '%p %T@\n' 2>/dev/null
    done | sort | md5sum | cut -d' ' -f1
  }
  now="$(sig)"
  [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$now" ] && exit 0
  before=$(ls "$HOME/.icons/Monterra-Local/apps/256" 2>/dev/null | wc -l)
  {
    echo "==== $(date '+%F %T')"
    "$PY" "$DEST/app_icons.py" apply --new
    ls "$HOME"/.local/share/applications/WebApp-*.desktop >/dev/null 2>&1 && \
      "$PY" "$DEST/webapps.py" apply --new
    # mitgebrachte eigene Symbole, deren Programm inzwischen installiert wurde
    for z in "$HOME"/.local/share/monterra/ausstehend/*.zip; do
      [ -f "$z" ] && [ -f "$DEST/icon_workshop.py" ] && "$PY" "$DEST/icon_workshop.py" --import "$z"
    done
  } >> "$LOG" 2>&1
  after=$(ls "$HOME/.icons/Monterra-Local/apps/256" 2>/dev/null | wc -l)
  sig > "$STAMP"                            # nach dem Anpassen: eigene Änderungen zählen nicht
  tail -n 400 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
  n=$((after - before))
  if [ "$n" -gt 0 ] && command -v notify-send >/dev/null; then
    [ "$n" = 1 ] && txt="1 neues Programm hat ein Monterra-Symbol bekommen." \
                 || txt="$n neue Programme haben ein Monterra-Symbol bekommen."
    notify-send -i preferences-desktop-theme "Monterra" "$txt" 2>/dev/null || true
  fi
  exit 0
fi

# ------------------------------------------------------------------ Status
if [ "$1" = "--status" ]; then
  if [ -f "$AUTOSTART" ]; then
    echo "Automatik ist eingeschaltet."
    have_systemd && systemctl --user is-active --quiet monterra-automatik.path && \
      echo "Überwachung neuer Programme läuft." || echo "Prüfung erfolgt bei jeder Anmeldung."
    [ -f "$LOG" ] && { echo; echo "Letzte Einträge:"; tail -n 8 "$LOG"; }
  else
    echo "Automatik ist ausgeschaltet."
  fi
  exit 0
fi

if [ "$(id -u)" -eq 0 ]; then echo "Bitte ohne sudo starten."; exit 1; fi

# ------------------------------------------------------------------ Ausschalten
if [ "$1" = "--remove" ]; then
  if have_systemd; then
    systemctl --user disable --now monterra-automatik.path >/dev/null 2>&1
    systemctl --user stop monterra-automatik.service >/dev/null 2>&1
  fi
  rm -f "$UNITS/monterra-automatik.path" "$UNITS/monterra-automatik.service" "$AUTOSTART"
  have_systemd && systemctl --user daemon-reload >/dev/null 2>&1
  rm -rf "$DEST"
  rmdir "$HOME/.local/share/monterra" 2>/dev/null
  echo "Automatik ausgeschaltet. Bereits angepasste Symbole bleiben erhalten."
  exit 0
fi

# ------------------------------------------------------------------ Einschalten
for f in app_icons.py webapps.py monterra_iconframe.py icon_workshop.py; do
  [ -f "$HERE/$f" ] || { echo "$f fehlt – bitte im entpackten Monterra-Ordner ausführen."; exit 1; }
done
mkdir -p "$DEST" "$(dirname "$AUTOSTART")"
cp "$HERE/app_icons.py" "$HERE/webapps.py" "$HERE/monterra_iconframe.py" "$HERE/icon_workshop.py" "$DEST/"
cp "$HERE/auto-icons.sh" "$DEST/auto-icons.sh"
rm -f "$DEST/programmsymbole.py" "$DEST/symbolwerkstatt.py" "$DEST/automatik.sh"   # Dateinamen bis Version 1.1
chmod +x "$DEST/auto-icons.sh"

# 1) bei jeder Anmeldung prüfen
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=Monterra-Automatik
Comment=Gibt neu installierten Programmen ein Symbol in Monterra-Form
Exec=bash "$DEST/auto-icons.sh" --check --wait
Icon=preferences-desktop-theme
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=30
EOF

# 2) sofort reagieren, wenn ein Programm installiert wird (systemd-Überwachung, kostet im Leerlauf nichts)
if have_systemd; then
  mkdir -p "$UNITS"
  {
    echo "[Unit]"
    echo "Description=Monterra: neue Programme erkennen"
    echo
    echo "[Path]"
    for d in "${WATCH[@]}"; do echo "PathChanged=$d"; done
    echo
    echo "[Install]"
    echo "WantedBy=default.target"
  } > "$UNITS/monterra-automatik.path"
  cat > "$UNITS/monterra-automatik.service" <<EOF
[Unit]
Description=Monterra: Symbole neuer Programme anpassen

[Service]
Type=oneshot
Nice=10
ExecStart=/bin/bash "$DEST/auto-icons.sh" --check --wait
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now monterra-automatik.path >/dev/null 2>&1 && SYSD=1
fi

# einmal sofort prüfen (Stand merken, fehlende Symbole nachholen)
bash "$DEST/auto-icons.sh" --check

echo "Automatik eingeschaltet."
if [ "${SYSD:-0}" = 1 ]; then
  echo "Neue Programme bekommen ihr Monterra-Symbol kurz nach der Installation – zusätzlich wird bei jeder Anmeldung geprüft."
else
  echo "Neue Programme werden bei jeder Anmeldung erkannt und angepasst."
fi
echo "Ausschalten: bash tools/auto-icons.sh --remove"
