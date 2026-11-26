#!/bin/bash
# =====================================================================
#  Monterra – Abgleich der Akzentfarbe (läuft im Hintergrund, startet mit der Anmeldung)
#
#  Wird in den Systemeinstellungen unter Themen → Anwendungen ein Monterra-Theme gewählt
#  (z. B. „Monterra-Dark-Green“), stellt dieser Abgleich passend dazu ein:
#    Desktop-Theme und Fensterrahmen (gleicher Name), Ordnerfarbe der Monterra-Symbole,
#    hell/dunkel für libadwaita-Programme sowie Firefox und Thunderbird (falls eingerichtet).
#  Andere Themes werden nicht angerührt. Wird von tools/accent-color.sh eingerichtet;
#  „Monterra vollständig entfernen“ im Installer entfernt ihn wieder.
# =====================================================================
DATA="$HOME/.local/share/monterra"
CONF="$HOME/.config/monterra-akzent.conf"
LOCK="${XDG_RUNTIME_DIR:-/tmp}/monterra-accent-sync.$(id -u).lock"

exec 9>"$LOCK"
flock -n 9 || exit 0                      # läuft schon

apply() {   # $1 = Name des gewählten GTK-Themes
  local name="$1" accent base
  case "$name" in Monterra|Monterra-*) ;; *) return ;; esac
  if [ ! -d "$HOME/.themes/$name" ]; then
    # Theme mit deutschem Farbnamen aus einer früheren Version (z. B. Monterra-Gruen) -> englischer Name
    local en
    en="$(echo "$name" | sed 's/-Lila$/-Purple/; s/-Rot$/-Red/; s/-Gelb$/-Yellow/; s/-Gruen$/-Green/; s/-Petrol$/-Teal/; s/-Braun$/-Brown/; s/-Grau$/-Grey/; s/-Graphit$/-Graphite/')"
    [ "$en" != "$name" ] && [ -d "$HOME/.themes/$en" ] && gsettings set org.cinnamon.desktop.interface gtk-theme "$en"
    return
  fi
  case "$name" in Monterra-Dark*) base=Monterra-Dark ;; *) base=Monterra ;; esac
  accent="${name#"$base"}"; accent="${accent#-}"; [ -n "$accent" ] || accent=Blue

  # Desktop-Theme und Fensterrahmen
  [ "$(gsettings get org.cinnamon.theme name | tr -d "'")" = "$name" ] || \
    gsettings set org.cinnamon.theme name "$name"
  [ "$(gsettings get org.cinnamon.desktop.wm.preferences theme | tr -d "'")" = "$name" ] || \
    gsettings set org.cinnamon.desktop.wm.preferences theme "$name"
  if [ "$base" = Monterra-Dark ]; then
    gsettings set org.x.apps.portal color-scheme 'prefer-dark' 2>/dev/null || true
  else
    gsettings set org.x.apps.portal color-scheme 'prefer-light' 2>/dev/null || true
  fi

  # Akzentfarbe geändert? Dann Ordner, Firefox, Thunderbird und libadwaita nachziehen
  [ "$(cat "$CONF" 2>/dev/null)" = "$accent" ] && return
  eval "$(python3 "$DATA/accent.py" "$accent" 2>/dev/null)" || return
  echo "$AKZENT_NAME" > "$CONF"
  local it; it="$(gsettings get org.cinnamon.desktop.interface icon-theme | tr -d "'")"
  if [ "${it#Monterra}" != "$it" ] && [ "$it" != "Monterra-Local" ] && [ -d "$HOME/.icons/$AKZENT_FOLDERS" ]; then
    gsettings set org.cinnamon.desktop.interface icon-theme "$AKZENT_FOLDERS"
  fi
  if gsettings list-keys org.x.apps.portal 2>/dev/null | grep -qx accent-rgb; then
    gsettings set org.x.apps.portal accent-rgb "$AKZENT_LIGHT" 2>/dev/null || true
  fi
  local pkg; pkg="$(cat "$HOME/.config/monterra-paket.conf" 2>/dev/null)"
  if [ -n "$pkg" ] && [ -d "$pkg/tools" ]; then
    [ -f "$HOME/.config/monterra-firefox.conf" ] && bash "$pkg/tools/firefox.sh" --quiet >/dev/null 2>&1
    [ -f "$HOME/.config/monterra-thunderbird.conf" ] && bash "$pkg/tools/thunderbird.sh" --quiet >/dev/null 2>&1
  fi
}

# beim Start einmal abgleichen, danach auf Änderungen warten
apply "$(gsettings get org.cinnamon.desktop.interface gtk-theme | tr -d "'")"
gsettings monitor org.cinnamon.desktop.interface gtk-theme | while read -r _key value; do
  apply "$(echo "$value" | tr -d "'")"
done
