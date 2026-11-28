#!/usr/bin/env bash
# Monterra Menüleiste – klassische Menüleiste für das obere Panel
#
#     bash tools/menubar.sh              -> einrichten: ersetzt das Cinnamon-Menü im oberen Panel
#     bash tools/menubar.sh --files-only -> nur die Dateien kopieren (Panel bleibt unverändert)
#     bash tools/menubar.sh --remove     -> entfernen, das Cinnamon-Menü kommt an dieselbe Stelle zurück
#
# Links das Monterra-Logo (Systemmenü mit App-Suche, Einstellungen, Ausschalten …), daneben ein
# Aufklappmenü je App-Kategorie. Einstellungen: Rechtsklick auf die Menüleiste → Konfigurieren.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
UUID="monterra-menubar@monterra"
DEST="$HOME/.local/share/cinnamon/applets/$UUID"
STOCK="menu@cinnamon.org"

[ "$(id -u)" = 0 ] && { echo "Bitte ohne sudo starten."; exit 1; }

# tauscht in enabled-applets ein Applet gegen ein anderes (gleiche Stelle, gleiche ID);
# fehlt das alte, wird das neue links im obersten Panel eingefügt
swap_applet() {   # $1 = alt  $2 = neu
  python3 - "$1" "$2" <<'PY'
import ast, subprocess, sys
old, new = sys.argv[1], sys.argv[2]
raw = subprocess.run(["gsettings", "get", "org.cinnamon", "enabled-applets"], capture_output=True, text=True).stdout.strip()
raw = raw.replace("@as ", "")
items = ast.literal_eval(raw) if raw else []
parts = [i.split(":") for i in items]
if any(p[3] == new for p in parts):
    sys.exit(0)
done = False
for p in parts:
    if p[3] == old and not done:
        p[3] = new; done = True
if not done:
    panels = subprocess.run(["gsettings", "get", "org.cinnamon", "panels-enabled"], capture_output=True, text=True).stdout
    top = "panel1"
    for e in ast.literal_eval(panels.replace("@as ", "") or "[]"):
        pid, mon, pos = e.split(":")
        if pos == "top":
            top = "panel" + pid; break
    for p in parts:
        if p[0] == top and p[1] == "left":
            p[2] = str(int(p[2]) + 1)
    ids = [int(p[4]) for p in parts if len(p) > 4 and p[4].isdigit()]
    parts.insert(0, [top, "left", "0", new, str(max(ids, default=0) + 1)])
val = "[" + ", ".join("'" + ":".join(p) + "'" for p in parts) + "]"
subprocess.run(["gsettings", "set", "org.cinnamon", "enabled-applets", val], check=True)
PY
}

if [ "$1" = "--remove" ]; then
  swap_applet "$UUID" "$STOCK"
  python3 - "$UUID" <<'PY'
import ast, subprocess, sys
uuid = sys.argv[1]
raw = subprocess.run(["gsettings", "get", "org.cinnamon", "enabled-applets"], capture_output=True, text=True).stdout.strip().replace("@as ", "")
items = [i for i in (ast.literal_eval(raw) if raw else []) if i.split(":")[3] != uuid]
subprocess.run(["gsettings", "set", "org.cinnamon", "enabled-applets", "[" + ", ".join(f"'{i}'" for i in items) + "]"], check=True)
PY
  rm -rf "$DEST"
  rm -f "$HOME"/.local/share/locale/*/LC_MESSAGES/"$UUID".mo
  echo "Monterra Menüleiste entfernt – das Cinnamon-Menü ist zurück."
  exit 0
fi

# Update: läuft die Menüleiste schon, wird sie erst aus dem Panel genommen und nach dem Kopieren
# wieder an dieselbe Stelle gesetzt – Dateien unter einem laufenden Applet auszutauschen
# (oder es per ReloadXlet neu zu laden) bringt Cinnamon 6.6 in den Rückfallmodus.
SAVED=""
if [ "$1" != "--files-only" ] && gsettings get org.cinnamon enabled-applets 2>/dev/null | grep -q "$UUID"; then
  SAVED=$(gsettings get org.cinnamon enabled-applets)
  python3 - "$UUID" <<'PY'
import ast, subprocess, sys
uuid = sys.argv[1]
raw = subprocess.run(["gsettings", "get", "org.cinnamon", "enabled-applets"], capture_output=True, text=True).stdout.strip().replace("@as ", "")
items = [i for i in (ast.literal_eval(raw) if raw else []) if i.split(":")[3] != uuid]
subprocess.run(["gsettings", "set", "org.cinnamon", "enabled-applets", "[" + ", ".join(f"'{i}'" for i in items) + "]"], check=True)
PY
  sleep 2
fi

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -r "$ROOT/components/menubar/$UUID" "$DEST"
# Übersetzungen (Deutsch, Spanisch)
for mo in "$DEST"/locale/*/LC_MESSAGES/"$UUID".mo; do
  [ -f "$mo" ] || continue
  lang=$(basename "$(dirname "$(dirname "$mo")")")
  mkdir -p "$HOME/.local/share/locale/$lang/LC_MESSAGES"
  cp "$mo" "$HOME/.local/share/locale/$lang/LC_MESSAGES/"
done
[ "$1" = "--files-only" ] && { echo "Monterra Menüleiste kopiert."; exit 0; }

if [ -n "$SAVED" ]; then
  gsettings set org.cinnamon enabled-applets "$SAVED"      # alte Stelle, alte ID → Einstellungen bleiben
else
  swap_applet "$STOCK" "$UUID"
fi
echo "Monterra Menüleiste eingerichtet (Einstellungen: Rechtsklick auf die Menüleiste → Konfigurieren)."
