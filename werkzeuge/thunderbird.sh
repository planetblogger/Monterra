#!/bin/bash
# =====================================================================
#  Monterra für Thunderbird – ruhige Oberfläche passend zu Monterra
#
#     bash werkzeuge/thunderbird.sh                  -> in alle Thunderbird-Profile einrichten
#     bash werkzeuge/thunderbird.sh --keep-titlebar  -> System-Titelleiste behalten
#                                                (sonst: Tabs in der Titelleiste
#                                                 mit Ampel-Knöpfen)
#     bash werkzeuge/thunderbird.sh --remove         -> alles rückgängig machen
#     (--still: ohne Ausgaben, z. B. nach dem Wechsel der Akzentfarbe)
#
#  Ohne sudo ausführen. Thunderbird danach einmal neu starten.
#  Funktioniert mit Thunderbird aus Mint (.deb), Flatpak und Snap.
# =====================================================================
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
SRC="$ROOT/komponenten/thunderbird"
MARK="Monterra für Thunderbird"
CONF="$HOME/.config/monterra-thunderbird.conf"
MODE="install"
TITLEBAR=1
QUIET=0
for arg in "$@"; do
  case "$arg" in
    --remove) MODE="remove" ;;
    --keep-titlebar) TITLEBAR=0 ;;
    --still) QUIET=1 ;;
    *) echo "Unbekannte Option: $arg"; exit 1 ;;
  esac
done
if [ "$QUIET" = 1 ]; then
  exec >/dev/null
  [ -f "$CONF" ] && . "$CONF"          # bisherige Wahl (Titelleiste) beibehalten
fi
AKZENT="$(cat "$HOME/.config/monterra-akzent.conf" 2>/dev/null || echo Blau)"

if [ "$(id -u)" -eq 0 ]; then
  echo "Bitte ohne sudo starten (Thunderbird-Profile gehören deinem Benutzer)."; exit 1
fi
if [ "$MODE" = install ] && [ ! -f "$SRC/userChrome.css" ]; then
  echo "Dateien fehlen: $SRC – bitte im entpackten Monterra-Ordner starten."; exit 1
fi

# ------------------------------------------------------------------ Profile finden
ROOTS=(
  "$HOME/.thunderbird"
  "$HOME/.config/thunderbird"
  "$HOME/.var/app/org.mozilla.Thunderbird/.thunderbird"
  "$HOME/.var/app/org.mozilla.Thunderbird/config/thunderbird"
  "$HOME/snap/thunderbird/common/.thunderbird"
)
PROFILES=()
for root in "${ROOTS[@]}"; do
  ini="$root/profiles.ini"
  [ -f "$ini" ] || continue
  while IFS='|' read -r path rel; do
    [ -z "$path" ] && continue
    if [ "$rel" = "0" ]; then dir="$path"; else dir="$root/$path"; fi
    [ -d "$dir" ] && PROFILES+=("$dir")
  done < <(awk -F= '
      /^\[/ { if (p != "") print p "|" r; p = ""; r = "1"; next }
      $1 == "Path" { p = substr($0, 6) }
      $1 == "IsRelative" { r = $2 }
      END { if (p != "") print p "|" r }' "$ini")
done

if [ ${#PROFILES[@]} -eq 0 ]; then
  echo "Kein Thunderbird-Profil gefunden. Bitte Thunderbird einmal starten und wieder schließen,"
  echo "dann dieses Skript erneut ausführen."
  exit 1
fi

if pgrep -x thunderbird >/dev/null 2>&1 || pgrep -x thunderbird-bin >/dev/null 2>&1 || pgrep -f "/thunderbird/thunderbird" >/dev/null 2>&1; then
  RUNNING=1
else
  RUNNING=0
fi

# user.js: unseren Block entfernen (zwischen den Markierungen)
strip_block() {
  local f="$1"
  [ -f "$f" ] || return 0
  awk '/^\/\/ >>> Monterra/ {skip=1; next} /^\/\/ <<< Monterra/ {skip=0; next} !skip' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
  [ -s "$f" ] || rm -f "$f"
}

# bisherigen Wert einer Einstellung aus prefs.js lesen (leer = Thunderbird-Standard)
read_pref() {
  grep -F "user_pref(\"$2\"," "$1/prefs.js" 2>/dev/null | tail -1 | sed -E 's/.*, *(.*)\);.*/\1/'
}

# ------------------------------------------------------------------ Installieren
if [ "$MODE" = install ]; then
  for p in "${PROFILES[@]}"; do
    mkdir -p "$p/chrome"
    for f in userChrome.css; do
      if [ -f "$p/chrome/$f" ] && ! grep -q "$MARK" "$p/chrome/$f" && [ ! -f "$p/chrome/$f.monterra-backup" ]; then
        mv "$p/chrome/$f" "$p/chrome/$f.monterra-backup"
        echo "   eigene $f gesichert als $f.monterra-backup"
      fi
      cp "$SRC/$f" "$p/chrome/$f"
      python3 "$HERE/akzent.py" --css "$AKZENT" "$p/chrome/$f" 2>/dev/null || true   # Akzentfarbe
    done
    # vorherige Werte einmalig merken (für --remove)
    if [ ! -f "$p/chrome/monterra-prefs.txt" ]; then
      {
        echo "stylesheets=$(read_pref "$p" toolkit.legacyUserProfileCustomizations.stylesheets)"
        echo "inTitlebar=$(read_pref "$p" mail.tabs.drawInTitlebar)"
      } > "$p/chrome/monterra-prefs.txt"
    fi
    strip_block "$p/user.js"
    {
      echo "// >>> Monterra (von thunderbird.sh, wird bei --remove entfernt)"
      echo 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);'
      [ "$TITLEBAR" = 1 ] && echo 'user_pref("mail.tabs.drawInTitlebar", true);'
      echo "// <<< Monterra"
    } >> "$p/user.js"
    echo "✓ Profil eingerichtet: $p"
  done
  mkdir -p "$(dirname "$CONF")"
  echo "TITLEBAR=$TITLEBAR" > "$CONF"
  echo
  echo "Fertig. Thunderbird jetzt (neu) starten."
  [ "$RUNNING" = 1 ] && echo "Hinweis: Thunderbird läuft gerade – bitte ganz beenden und neu öffnen."
  echo "Wichtig: Unter Einstellungen → Add-ons und Themes → Themes muss"
  echo "„System-Theme – automatisch“ aktiv sein (Standard). Hell/Dunkel folgt dann Monterra."
  exit 0
fi

# ------------------------------------------------------------------ Entfernen
if [ "$RUNNING" = 1 ]; then
  echo "Bitte Thunderbird zuerst ganz beenden und das Skript dann erneut starten."
  exit 1
fi

# eine Einstellung in prefs.js auf den früheren Wert setzen (leer = Thunderbird-Standard)
set_pref() {
  local f="$1/prefs.js" name="$2" value="$3"
  [ -f "$f" ] || return 0
  grep -vF "user_pref(\"$name\"," "$f" > "$f.tmp" && mv "$f.tmp" "$f"
  [ -n "$value" ] && echo "user_pref(\"$name\", $value);" >> "$f"
}

for p in "${PROFILES[@]}"; do
  [ -d "$p/chrome" ] || continue
  had_own=0
  for f in userChrome.css; do
    if [ -f "$p/chrome/$f" ] && grep -q "$MARK" "$p/chrome/$f"; then rm -f "$p/chrome/$f"; fi
    if [ -f "$p/chrome/$f.monterra-backup" ]; then
      mv "$p/chrome/$f.monterra-backup" "$p/chrome/$f"; had_own=1
    fi
  done
  strip_block "$p/user.js"
  if [ -f "$p/chrome/monterra-prefs.txt" ]; then
    old_ss=$(sed -n 's/^stylesheets=//p' "$p/chrome/monterra-prefs.txt")
    old_tb=$(sed -n 's/^inTitlebar=//p' "$p/chrome/monterra-prefs.txt")
    [ "$had_own" = 0 ] && set_pref "$p" toolkit.legacyUserProfileCustomizations.stylesheets "$old_ss"
    set_pref "$p" mail.tabs.drawInTitlebar "$old_tb"
    rm -f "$p/chrome/monterra-prefs.txt"
  fi
  rmdir "$p/chrome" 2>/dev/null
  echo "✓ Profil zurückgesetzt: $p"
done
rm -f "$CONF"
echo
echo "Fertig. Thunderbird sieht beim nächsten Start wieder aus wie vorher."
