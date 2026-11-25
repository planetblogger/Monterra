#!/bin/bash
# =====================================================================
#  Monterra für Firefox – schlichte Oberfläche passend zu Monterra
#
#     bash werkzeuge/firefox.sh                  -> in alle Firefox-Profile einrichten
#     bash werkzeuge/firefox.sh --keep-titlebar  -> System-Titelleiste behalten
#                                                (sonst: Tabs in der Titelleiste
#                                                 mit Ampel-Knöpfen)
#     bash werkzeuge/firefox.sh --remove         -> alles rückgängig machen
#     (--still: ohne Ausgaben, z. B. nach dem Wechsel der Akzentfarbe)
#
#  Ohne sudo ausführen. Firefox danach einmal neu starten.
#  Funktioniert mit Firefox aus Mint (.deb), Flatpak und Snap.
# =====================================================================
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
SRC="$ROOT/komponenten/firefox"
MARK="Monterra für Firefox"
CONF="$HOME/.config/monterra-firefox.conf"
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
  echo "Bitte ohne sudo starten (Firefox-Profile gehören deinem Benutzer)."; exit 1
fi
if [ "$MODE" = install ] && [ ! -f "$SRC/userChrome.css" ]; then
  echo "Dateien fehlen: $SRC – bitte im entpackten Monterra-Ordner starten."; exit 1
fi

# ------------------------------------------------------------------ Profile finden
ROOTS=(
  "$HOME/.mozilla/firefox"
  "$HOME/.config/mozilla/firefox"
  "$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox"
  "$HOME/.var/app/org.mozilla.firefox/config/mozilla/firefox"
  "$HOME/snap/firefox/common/.mozilla/firefox"
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
  echo "Kein Firefox-Profil gefunden. Bitte Firefox einmal starten und wieder schließen,"
  echo "dann dieses Skript erneut ausführen."
  exit 1
fi

if pgrep -x firefox >/dev/null 2>&1 || pgrep -x firefox-bin >/dev/null 2>&1 || pgrep -f "/firefox/firefox" >/dev/null 2>&1; then
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

# bisherigen Wert einer Einstellung aus prefs.js lesen (leer = Firefox-Standard)
read_pref() {
  grep -F "user_pref(\"$2\"," "$1/prefs.js" 2>/dev/null | tail -1 | sed -E 's/.*, *(.*)\);.*/\1/'
}

# ------------------------------------------------------------------ Installieren
if [ "$MODE" = install ]; then
  for p in "${PROFILES[@]}"; do
    mkdir -p "$p/chrome"
    for f in userChrome.css userContent.css; do
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
        echo "inTitlebar=$(read_pref "$p" browser.tabs.inTitlebar)"
      } > "$p/chrome/monterra-prefs.txt"
    fi
    strip_block "$p/user.js"
    {
      echo "// >>> Monterra (von firefox.sh, wird bei --remove entfernt)"
      echo 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);'
      [ "$TITLEBAR" = 1 ] && echo 'user_pref("browser.tabs.inTitlebar", 1);'
      echo "// <<< Monterra"
    } >> "$p/user.js"
    echo "✓ Profil eingerichtet: $p"
  done
  mkdir -p "$(dirname "$CONF")"
  echo "TITLEBAR=$TITLEBAR" > "$CONF"
  echo
  echo "Fertig. Firefox jetzt (neu) starten."
  [ "$RUNNING" = 1 ] && echo "Hinweis: Firefox läuft gerade – bitte ganz beenden und neu öffnen."
  echo "Wichtig: Unter Einstellungen → Erweiterungen & Themes → Themes muss"
  echo "„System-Theme – automatisch“ aktiv sein (Standard). Hell/Dunkel folgt dann Monterra."
  exit 0
fi

# ------------------------------------------------------------------ Entfernen
if [ "$RUNNING" = 1 ]; then
  echo "Bitte Firefox zuerst ganz beenden und das Skript dann erneut starten."
  exit 1
fi

# eine Einstellung in prefs.js auf den früheren Wert setzen (leer = Firefox-Standard)
set_pref() {
  local f="$1/prefs.js" name="$2" value="$3"
  [ -f "$f" ] || return 0
  grep -vF "user_pref(\"$name\"," "$f" > "$f.tmp" && mv "$f.tmp" "$f"
  [ -n "$value" ] && echo "user_pref(\"$name\", $value);" >> "$f"
}

for p in "${PROFILES[@]}"; do
  [ -d "$p/chrome" ] || continue
  had_own=0
  for f in userChrome.css userContent.css; do
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
    set_pref "$p" browser.tabs.inTitlebar "$old_tb"
    rm -f "$p/chrome/monterra-prefs.txt"
  fi
  rmdir "$p/chrome" 2>/dev/null
  echo "✓ Profil zurückgesetzt: $p"
done
rm -f "$CONF"
echo
echo "Fertig. Firefox sieht beim nächsten Start wieder aus wie vorher."
