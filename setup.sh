#!/bin/bash
# =====================================================================
#  Monterra – geführte Installation (alle Schritte mit Auswahl)
#  Monterra – guided setup · Monterra – instalación guiada
#
#     bash setup.sh            -> Fragen in Fenstern (Zenity)
#     bash setup.sh --text     -> Fragen im Terminal
#     bash setup.sh --lang=en  -> Sprache vorwählen (de | en | es)
#
#  Bitte im entpackten Monterra-Ordner aus einem Terminal starten
#  (für Boot-Splash, Anmeldebildschirm usw. wird einmal das Passwort abgefragt).
#  Protokoll / log: ~/monterra-installer.log
#  Texte: werkzeuge/sprachen/de.sh, en.sh, es.sh
# =====================================================================
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG="$HOME/monterra-installer.log"
UI="zenity"
LANG_SEL=""
# Umlaute in Dialogen brauchen eine UTF-8-Umgebung
[ "$(locale charmap 2>/dev/null)" = "UTF-8" ] || export LC_ALL=C.UTF-8
for a in "$@"; do
  case "$a" in
    --text) UI="text" ;;
    --lang=*) LANG_SEL="${a#--lang=}" ;;
  esac
done
{ [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; } && UI="text"
command -v zenity >/dev/null || UI="text"

# Per Doppelklick gestartet? -> in einem Terminalfenster neu öffnen (für die Passwortabfrage)
if [ ! -t 0 ] && [ -z "$MONTERRA_IN_TERM" ] && { [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; }; then
  export MONTERRA_IN_TERM=1
  if command -v gnome-terminal >/dev/null; then exec gnome-terminal --title="Monterra" -- bash "$0" "$@"
  elif command -v x-terminal-emulator >/dev/null; then exec x-terminal-emulator -e bash "$0" "$@"; fi
fi

# ------------------------------------------------------------------ Sprache / language / idioma
if [ ! -f "$HERE/werkzeuge/sprachen/de.sh" ]; then
  echo "Bitte im entpackten Monterra-Ordner starten. / Please start inside the unpacked Monterra folder."
  exit 1
fi
case "${LANG_SEL:-${LC_ALL:-${LC_MESSAGES:-$LANG}}}" in
  en*) LANG_DEF=en ;; es*) LANG_DEF=es ;; *) LANG_DEF=de ;;
esac
if [ -z "$LANG_SEL" ]; then
  LQ="Sprache · Language · Idioma"
  if [ "$UI" = "zenity" ]; then
    LANG_SEL=$(zenity --list --radiolist --title="Monterra" --text="$LQ" --width=420 --height=260 \
      --ok-label="OK" --cancel-label="Abbrechen · Cancel · Cancelar" --column="" --column="key" --column="" --hide-column=2 --print-column=2 \
      "$([ $LANG_DEF = de ] && echo TRUE || echo FALSE)" de "Deutsch" \
      "$([ $LANG_DEF = en ] && echo TRUE || echo FALSE)" en "English" \
      "$([ $LANG_DEF = es ] && echo TRUE || echo FALSE)" es "Español" 2>/dev/null) || exit 0
  else
    echo; echo "$LQ"
    echo "  1) Deutsch"; echo "  2) English"; echo "  3) Español"
    read -r -p "[1-3, Enter = $LANG_DEF]: " ans
    case "$ans" in 1) LANG_SEL=de ;; 2) LANG_SEL=en ;; 3) LANG_SEL=es ;; *) LANG_SEL=$LANG_DEF ;; esac
  fi
fi
case "$LANG_SEL" in de|en|es) ;; *) LANG_SEL=$LANG_DEF ;; esac
# shellcheck source=werkzeuge/sprachen/de.sh
. "$HERE/werkzeuge/sprachen/$LANG_SEL.sh"
TITLE="$S_TITLE"
# gewählte Sprache merken (z. B. für die Symbolwerkstatt)
mkdir -p "$HOME/.config" && echo "$LANG_SEL" > "$HOME/.config/monterra-sprache.conf"

[ -n "$MONTERRA_IN_TERM" ] && trap 'echo; read -r -p "$S_ENTER_CLOSE" _' EXIT

if [ "$(id -u)" -eq 0 ]; then
  echo -e "$S_NO_SUDO"; exit 1
fi
if [ ! -f "$HERE/werkzeuge/setup.sh" ] || [ ! -d "$HERE/themes/Monterra" ]; then
  echo "$S_WRONG_DIR"; exit 1
fi

# ------------------------------------------------------------------ UI helpers
# radio KEY-DEFAULT "Frage" key1 "Text 1" key2 "Text 2" …   -> gewählter key
radio() {
  local def="$1" question="$2"; shift 2
  if [ "$UI" = "zenity" ]; then
    local args=() k t
    while [ $# -gt 0 ]; do
      k="$1"; t="$2"; shift 2
      [ "$k" = "$def" ] && args+=(TRUE "$k" "$t") || args+=(FALSE "$k" "$t")
    done
    zenity --list --radiolist --title="$TITLE" --text="$question" --width=660 --height=440 --ok-label="$S_NEXT" --cancel-label="$S_CANCEL" \
      --column="" --column="key" --column="$S_COL_CHOICE" --hide-column=2 --print-column=2 "${args[@]}" 2>/dev/null
    return $?
  fi
  echo >&2; echo -e "$question" >&2
  local keys=() i=1 k t
  while [ $# -gt 0 ]; do
    k="$1"; t="$2"; shift 2
    keys+=("$k")
    [ "$k" = "$def" ] && echo "  $i) $t   [$S_DEFAULT]" >&2 || echo "  $i) $t" >&2
    i=$((i + 1))
  done
  local ans; read -r -p "$S_PROMPT_CHOICE" ans
  if [[ "$ans" =~ ^[0-9]+$ ]] && [ "$ans" -ge 1 ] && [ "$ans" -le "${#keys[@]}" ]; then
    echo "${keys[$((ans - 1))]}"
  else
    echo "$def"
  fi
}

# slider "Frage" MIN MAX STEP DEFAULT   -> Zahl
slider() {
  local question="$1" min="$2" max="$3" stp="$4" def="$5"
  if [ "$UI" = "zenity" ]; then
    zenity --scale --title="$TITLE" --text="$question" --width=560 --ok-label="$S_NEXT" --cancel-label="$S_CANCEL" \
      --min-value="$min" --max-value="$max" --step="$stp" --value="$def" 2>/dev/null
    return $?
  fi
  echo >&2; echo -e "$question" >&2
  local ans
  # shellcheck disable=SC2059
  read -r -p "$(printf "$S_PROMPT_SIZE" "$def")" ans
  if [[ "$ans" =~ ^[0-9]+$ ]] && [ "$ans" -ge "$min" ] && [ "$ans" -le "$max" ]; then
    echo $(( (ans - min) / stp * stp + min ))       # auf den nächsten gültigen Schritt abrunden
  else
    echo "$def"
  fi
}

# Auswahl mit Vorschaubildern (eigenes kleines GTK-Fenster), sonst Liste
HAS_PICK=0
if [ "$UI" = "zenity" ] && python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' 2>/dev/null; then
  HAS_PICK=1
fi
# pick KEY-DEFAULT "Frage" SPALTEN key1 bild1 "Text 1" …   -> gewählter key
pick() {
  local def="$1" question="$2" cols="$3"; shift 3
  python3 "$HERE/werkzeuge/bildauswahl.py" --title "$TITLE" --text "$question" --ok "$S_NEXT" --cancel "$S_CANCEL" \
    --default "$def" --columns "$cols" "$@" 2>/dev/null
}

# check "Frage" key1 on|off "Text 1" …   -> gewählte keys, durch ":" getrennt
check() {
  local question="$1"; shift
  if [ "$UI" = "zenity" ]; then
    local args=() k s t
    while [ $# -gt 0 ]; do
      k="$1"; s="$2"; t="$3"; shift 3
      [ "$s" = "on" ] && args+=(TRUE "$k" "$t") || args+=(FALSE "$k" "$t")
    done
    zenity --list --checklist --title="$TITLE" --text="$question" --width=760 --height=520 --ok-label="$S_NEXT" --cancel-label="$S_CANCEL" --separator=":" \
      --column="" --column="key" --column="$S_COL_PART" --hide-column=2 --print-column=2 "${args[@]}" 2>/dev/null
    return $?
  fi
  echo >&2; echo -e "$question" >&2
  local out="" k s t ans yes
  case "$LANG_SEL" in es) yes='^[SsYy]' ;; de) yes='^[JjYy]' ;; *) yes='^[Yy]' ;; esac
  while [ $# -gt 0 ]; do
    k="$1"; s="$2"; t="$3"; shift 3
    local y="${S_YES:0:1}" n="${S_NO:0:1}" d
    if [ "$s" = "on" ]; then d="${y^^}/${n,,}"; else d="${y,,}/${n^^}"; fi
    read -r -p "  $t? [$d] " ans
    if [ -z "$ans" ]; then [ "$s" = "on" ] && out="$out:$k"
    elif [[ "$ans" =~ $yes ]]; then out="$out:$k"; fi
  done
  echo "${out#:}"
}

yesno() {
  if [ "$UI" = "zenity" ]; then
    zenity --question --title="$TITLE" --width=560 --ok-label="$S_YES" --cancel-label="$S_NO" --text="$1" 2>/dev/null
    return $?
  fi
  echo; echo -e "$1"; local a yes
  case "$LANG_SEL" in es) yes='^[SsYy]' ;; de) yes='^[JjYy]' ;; *) yes='^[Yy]' ;; esac
  local y="${S_YES:0:1}" n="${S_NO:0:1}"
  read -r -p "[${y^^}/${n,,}] " a
  [ -z "$a" ] || [[ "$a" =~ $yes ]]
}

info() {
  if [ "$UI" = "zenity" ]; then
    zenity --info --title="$TITLE" --width=580 --text="$1" 2>/dev/null
  else
    echo; echo -e "$1"
  fi
}

abort() { echo "$S_ABORT"; exit 0; }

# ------------------------------------------------------------------ run helpers
FAILED=()
step() {   # step "Beschreibung" befehl …
  local desc="$1"; shift
  echo
  echo "▶ $desc"
  echo "==== $(date '+%F %T') $desc" >> "$LOG"
  if "$@" 2>&1 | tee -a "$LOG" | sed 's/^/   /'; then
    [ "${PIPESTATUS[0]}" -eq 0 ] && return 0
  fi
  FAILED+=("$desc")
  # shellcheck disable=SC2059
  echo "   $(printf "$S_STEP_FAILED" "$LOG")"
  return 1
}

sudo_keepalive() {
  echo
  echo "$S_SUDO_ASK"
  sudo -v || { echo "$S_SUDO_SKIP"; return 1; }
  ( while kill -0 $$ 2>/dev/null; do sudo -n true 2>/dev/null; sleep 50; done ) &
  return 0
}

restart_cinnamon() {
  gdbus call --session --dest org.Cinnamon --object-path /org/Cinnamon \
    --method org.Cinnamon.RestartCinnamon true >/dev/null 2>&1 || true
}

failed_report() {
  local list; list="• $(printf '%s\n• ' "${FAILED[@]}" | sed '$d')"
  # shellcheck disable=SC2059
  info "$(printf "$S_DONE_FAILED" "$list" "$LOG")"
}

. "$HERE/werkzeuge/motive.sh"
MOTIF_KEYS=(himmel wueste mars dschungel seide bluete)
motif_name() {   # key -> Anzeigename
  local i
  for i in "${!MOTIF_KEYS[@]}"; do
    [ "${MOTIF_KEYS[$i]}" = "$1" ] && { echo "${S_MOTIFS[$i]}"; return; }
  done
  echo "$1"
}
# Farbschlüssel (wie in den Dateinamen) und Anzeigenamen der gewählten Sprache
COLOR_KEYS=(blau indigo lila pink rot orange gelb gruen petrol cyan braun grau graphit)
color_name() {   # key -> Anzeigename
  local i
  for i in "${!COLOR_KEYS[@]}"; do
    [ "${COLOR_KEYS[$i]}" = "$1" ] && { echo "${S_COLORS[$i]}"; return; }
  done
  echo "$1"
}
color_args() {   # key "Name" key "Name" …  (Gelb mit Hinweis auf dunkle Schrift, falls $1 = accent)
  local i n
  for i in "${!COLOR_KEYS[@]}"; do
    n="${S_COLORS[$i]}"
    [ "$1" = accent ] && [ "${COLOR_KEYS[$i]}" = gelb ] && n="$n $S_YELLOW_NOTE"
    printf '%s\n%s\n' "${COLOR_KEYS[$i]}" "$n"
  done
}

# ================================================================== START
echo "==== Monterra $(date '+%F %T') ($LANG_SEL)" >> "$LOG"
[ -n "$S_TOOL_NOTE" ] && echo "$S_TOOL_NOTE"
MODE=$(radio install "$S_Q_MODE" \
  install   "$S_MODE_INSTALL" \
  uninstall "$S_MODE_UNINSTALL") || abort
[ -z "$MODE" ] && abort

# ================================================================== UNINSTALL
if [ "$MODE" = "uninstall" ]; then
  yesno "$S_UN_CONFIRM" || abort
  SUDO_OK=0; sudo_keepalive && SUDO_OK=1
  [ -f "$HOME/.local/share/cinnamon/extensions/monterra-dock@monterra/extension.js" ] && \
    step "$S_UN_DOCK" bash "$HERE/werkzeuge/dock.sh" --remove
  [ -d "$HOME/.local/share/cinnamon/extensions/monterra-fenster@monterra" ] && \
    step "$S_UN_WINDOWS" bash "$HERE/werkzeuge/fenster.sh" --remove
  step "$S_UN_SETGRID" bash "$HERE/werkzeuge/einstellungen.sh" --remove
  [ -d "$HOME/.local/share/cinnamon/extensions/monterra-fenstergroesse@monterra" ] && \
    step "$S_UN_WINSIZE" bash "$HERE/werkzeuge/fenstergroesse.sh" --remove
  [ -f "$HOME/.config/autostart/monterra-automatik.desktop" ] && \
    step "$S_UN_AUTO" bash "$HERE/werkzeuge/automatik.sh" --remove
  [ -f "$HOME/.local/share/applications/monterra-symbolwerkstatt.desktop" ] && \
    step "$S_UN_WERKST" python3 "$HERE/werkzeuge/symbolwerkstatt.py" --remove
  step "$S_UN_APPICONS" python3 "$HERE/werkzeuge/programmsymbole.py" restore
  [ -d "$HOME/.local/share/monterra-webapps" ] && \
    step "$S_UN_WEBAPPS" python3 "$HERE/werkzeuge/webapps.py" restore
  FF_DONE=0
  for f in "$HOME"/.mozilla/firefox/*/chrome/monterra-prefs.txt "$HOME"/.config/mozilla/firefox/*/chrome/monterra-prefs.txt \
           "$HOME"/.var/app/org.mozilla.firefox/.mozilla/firefox/*/chrome/monterra-prefs.txt \
           "$HOME"/.var/app/org.mozilla.firefox/config/mozilla/firefox/*/chrome/monterra-prefs.txt \
           "$HOME"/snap/firefox/common/.mozilla/firefox/*/chrome/monterra-prefs.txt; do
    [ -e "$f" ] && FF_DONE=1
  done
  [ "$FF_DONE" = 1 ] && step "$S_UN_FIREFOX" bash "$HERE/werkzeuge/firefox.sh" --remove
  [ -f "$HOME/.config/monterra-thunderbird.conf" ] && \
    step "$S_UN_THUNDERBIRD" bash "$HERE/werkzeuge/thunderbird.sh" --remove
  if [ "$SUDO_OK" = 1 ]; then
    [ -f /usr/share/folder-color-switcher/colors.d/Monterra.json ] && \
      step "$S_UN_FOLDERS" bash "$HERE/werkzeuge/ordnerfarben.sh" --remove
    [ -d /usr/share/plymouth/themes/monterra ] && \
      step "$S_UN_SPLASH" sudo bash "$HERE/werkzeuge/bootsplash.sh" --remove
    { [ -f /etc/lightdm/slick-greeter.conf.monterra-backup ] || [ -f /etc/lightdm/.monterra-had-no-conf ]; } && \
      step "$S_UN_LOGIN" sudo bash "$HERE/werkzeuge/anmeldung.sh" --remove
  fi
  step "$S_UN_RESTORE" bash "$HERE/werkzeuge/setup.sh" --restore
  step "$S_UN_FILES" bash -c 'pkill -f monterra/akzent-sync.sh; rm -rf ~/.themes/Monterra ~/.themes/Monterra-* ~/.config/autostart/monterra-akzent-sync.desktop ~/.local/share/monterra/akzent-sync.sh ~/.local/share/monterra/akzent.py ~/.config/monterra-paket.conf ~/.icons/Monterra ~/.icons/Monterra-* ~/.config/monterra-buttons.conf ~/.config/monterra-akzent.conf ~/.config/monterra-sprache.conf ~/.config/monterra-firefox.conf ~/.local/share/monterra/ausstehend'
  restart_cinnamon
  if [ ${#FAILED[@]} -eq 0 ]; then info "$S_UN_DONE"; else failed_report; fi
  exit 0
fi

# ================================================================== QUESTIONS
VARIANT=$(radio light "$S_Q_VARIANT" \
  light "$S_VARIANT_LIGHT" \
  dark  "$S_VARIANT_DARK") || abort

LAYOUT=$(radio menubar-dock "$S_Q_LAYOUT" \
  menubar-dock  "$S_LAYOUT_MENUBAR_DOCK" \
  menubar-panel "$S_LAYOUT_MENUBAR_PANEL" \
  dock-only     "$S_LAYOUT_DOCK_ONLY" \
  keep          "$S_LAYOUT_KEEP") || abort

# Hintergrund: fünf Motive (mit Vorschaubildern)
[ "$VARIANT" = dark ] && VS=Dunkel || VS=Hell
PV="$HERE/vorschau/auswahl"
if [ "$HAS_PICK" = 1 ]; then
  args=()
  for i in "${!MOTIF_KEYS[@]}"; do
    m="$(motiv_von "${MOTIF_KEYS[$i]}")"
    args+=("${MOTIF_KEYS[$i]}" "$PV/motiv-$m-$VS.png" "${S_MOTIFS[$i]}")
  done
  args+=(keep "$PV/motiv-keep-$VS.png" "$S_WALL_KEEP")
  WALL=$(pick himmel "$S_Q_WALL" 4 "${args[@]}") || abort
else
  args=()
  for i in "${!MOTIF_KEYS[@]}"; do args+=("${MOTIF_KEYS[$i]}" "${S_MOTIFS[$i]}"); done
  WALL=$(radio himmel "$S_Q_WALL" "${args[@]}" keep "$S_WALL_KEEP") || abort
fi
[ -n "$WALL" ] || abort

# Akzentfarbe: „passend“ = Farbe zum gewählten (bzw. eingestellten) Motiv
if [ "$WALL" = keep ]; then
  cur="$(gsettings get org.cinnamon.desktop.background picture-uri 2>/dev/null)"
  CURMOT="$(echo "$cur" | sed -n 's#.*/Monterra-\([A-Za-z]*\)-\(Hell\|Dunkel\)\.jpg.*#\1#p')"
  MATCH="$(cat "$HOME/.config/monterra-akzent.conf" 2>/dev/null | tr A-Z a-z)"
  [ -n "$MATCH" ] || MATCH="$(akzent_zu_motiv "${CURMOT:-himmel}")"
else
  MATCH="$(akzent_zu_motiv "$WALL")"
fi
[ "$VARIANT" = dark ] && vs=dunkel || vs=hell
if [ "$HAS_PICK" = 1 ]; then
  args=(passend "$PV/akzent-$MATCH-$vs.png" "$S_ACCENT_MATCH – $(color_name "$MATCH")")
  for i in "${!COLOR_KEYS[@]}"; do
    n="${S_COLORS[$i]}"; [ "${COLOR_KEYS[$i]}" = gelb ] && n="$n $S_YELLOW_NOTE"
    args+=("${COLOR_KEYS[$i]}" "$PV/akzent-${COLOR_KEYS[$i]}-$vs.png" "$n")
  done
  AKZ=$(pick passend "$S_Q_ACCENT" 5 "${args[@]}") || abort
else
  mapfile -t ACC_ARGS < <(color_args accent)
  AKZ=$(radio passend "$S_Q_ACCENT" passend "$S_ACCENT_MATCH – $(color_name "$MATCH")" "${ACC_ARGS[@]}") || abort
fi
[ -n "$AKZ" ] || abort
[ "$AKZ" = passend ] && AKZ="$MATCH"
AKZ="$(echo "$AKZ" | tr A-Z a-z)"

# Fensterknöpfe: Schieberegler 14–32 px in 2er-Schritten (bisherige Wahl vorbelegt)
CUR_BTN=16
if [ -f "$HOME/.config/monterra-buttons.conf" ]; then
  case "$(cat "$HOME/.config/monterra-buttons.conf")" in
    gross) CUR_BTN=22 ;; sehr-gross) CUR_BTN=28 ;; normal) CUR_BTN=16 ;;
    *) c="$(cat "$HOME/.config/monterra-buttons.conf")"; [[ "$c" =~ ^[0-9]+$ ]] && CUR_BTN="$c" ;;
  esac
fi
BUTTONS=$(slider "$S_Q_BUTTONS" 14 32 2 "$CUR_BTN") || abort
[[ "$BUTTONS" =~ ^[0-9]+$ ]] || BUTTONS=$CUR_BTN
[ $((BUTTONS % 2)) -ne 0 ] && BUTTONS=$((BUTTONS - 1))

HAS_FIREFOX=off
for d in "$HOME/.mozilla/firefox" "$HOME/.config/mozilla/firefox" "$HOME/.var/app/org.mozilla.firefox" "$HOME/snap/firefox/common/.mozilla/firefox"; do
  [ -e "$d" ] && HAS_FIREFOX=on
done
HAS_TB=off
for d in "$HOME/.thunderbird" "$HOME/.var/app/org.mozilla.Thunderbird" "$HOME/snap/thunderbird/common/.thunderbird"; do
  [ -e "$d" ] && HAS_TB=on
done
# Fensterschatten: nur vorausgewählt, wenn schon eingerichtet (sonst bleiben Mints Standardschatten)
HAS_WIN=off; [ -d "$HOME/.local/share/cinnamon/extensions/monterra-fenster@monterra" ] && HAS_WIN=on
EXTRAS=$(check "$S_Q_EXTRAS" \
  font     on  "$S_X_FONT" \
  appicons on  "$S_X_APPICONS" \
  auto     on  "$S_X_AUTO" \
  werkst   on  "$S_X_WERKST" \
  fenster  "$HAS_WIN" "$S_X_WINDOWS" \
  fgroesse on  "$S_X_WINSIZE" \
  setgrid  on  "$S_X_SETGRID" \
  firefox  "$HAS_FIREFOX" "$S_X_FIREFOX" \
  thunderb "$HAS_TB" "$S_X_THUNDERBIRD" \
  folders  on  "$S_X_FOLDERS" \
  splash   on  "$S_X_SPLASH" \
  login    on  "$S_X_LOGIN") || abort

has() { [[ ":$EXTRAS:" == *":$1:"* ]]; }

# ------------------------------------------------------------------ summary
txt_variant=$([ "$VARIANT" = dark ] && echo "$S_SUM_DARK" || echo "$S_SUM_LIGHT")
case "$LAYOUT" in
  menubar-dock)  txt_layout="$S_SUM_LAYOUT_MENUBAR_DOCK";;
  menubar-panel) txt_layout="$S_SUM_LAYOUT_MENUBAR_PANEL";;
  dock-only)     txt_layout="$S_SUM_LAYOUT_DOCK_ONLY";;
  *)             txt_layout="$S_SUM_LAYOUT_KEEP";;
esac
if [ "$WALL" = keep ]; then txt_wall="$S_SUM_WALL_KEEP"; else txt_wall="$(motif_name "$WALL")"; fi
txt_akz="$(color_name "$AKZ")"
list=""
has font     && list="$list\n   • $S_L_FONT"
has appicons && list="$list\n   • $S_L_APPICONS"
has auto     && list="$list\n   • $S_L_AUTO"
has werkst   && list="$list\n   • $S_L_WERKST"
has fenster  && list="$list\n   • $S_L_WINDOWS"
has fgroesse && list="$list\n   • $S_L_WINSIZE"
has setgrid  && list="$list\n   • $S_L_SETGRID"
has firefox  && list="$list\n   • $S_L_FIREFOX"
has thunderb && list="$list\n   • $S_L_THUNDERBIRD"
has folders  && list="$list\n   • $S_L_FOLDERS"
has splash   && list="$list\n   • $S_L_SPLASH"
has login    && list="$list\n   • $S_L_LOGIN"
[ -z "$list" ] && list="\n   • $S_L_NONE"

yesno "$S_SUM_TITLE\n\n   $S_SUM_VARIANT: $txt_variant\n   $S_SUM_LAYOUT: $txt_layout\n   $S_SUM_WALL: $txt_wall\n   $S_SUM_ACCENT: $txt_akz\n   $S_SUM_BUTTONS: $BUTTONS px\n\n   $S_SUM_EXTRAS:$list\n\n$S_SUM_OUTRO" || abort

# ================================================================== INSTALL
SUDO_OK=0
if has font || has folders || has splash || has login; then
  sudo_keepalive && SUDO_OK=1
fi

# 1) Schrift
if has font && [ "$SUDO_OK" = 1 ]; then
  if fc-list | grep -qi "Inter"; then
    echo; echo "▶ $S_I_FONT_PRESENT"
  else
    step "$S_I_FONT" sudo apt-get install -y fonts-inter
  fi
fi

# 2) Themes, Symbole, Mauszeiger, Schrift, Fensterknöpfe, Hintergrund, Layout
SETUP_ARGS=()
[ "$VARIANT" = dark ] && SETUP_ARGS+=(--dark)
[[ "$LAYOUT" == menubar-* ]] && SETUP_ARGS+=(--layout)
if [ "$WALL" = keep ]; then SETUP_ARGS+=(--keep-wallpaper); else SETUP_ARGS+=("--motiv=$WALL"); fi
SETUP_ARGS+=("--akzent=$AKZ")
step "$S_I_SETUP" bash "$HERE/werkzeuge/setup.sh" "${SETUP_ARGS[@]}"

# shellcheck disable=SC2059
step "$(printf "$S_I_BUTTONS" "$BUTTONS")" bash "$HERE/werkzeuge/fensterknoepfe.sh" "$BUTTONS"

# 3) Dock
case "$LAYOUT" in
  menubar-dock) step "$S_I_DOCK_NOPANEL" bash "$HERE/werkzeuge/dock.sh" --ohne-panel ;;
  dock-only)    step "$S_I_DOCK" bash "$HERE/werkzeuge/dock.sh" ;;
esac

# 4) Programm- und Web-App-Symbole
has appicons && step "$S_I_APPICONS" python3 "$HERE/werkzeuge/programmsymbole.py" apply
has appicons && ls "$HOME"/.local/share/applications/WebApp-*.desktop >/dev/null 2>&1 && \
  step "$S_I_WEBAPPS" python3 "$HERE/werkzeuge/webapps.py" apply
has auto     && step "$S_I_AUTO" bash "$HERE/werkzeuge/automatik.sh"
# mitgebrachte eigene Programmsymbole (Ordner meine-symbole) übernehmen
MY_ICONS=("$HERE"/meine-symbole/*.zip)
[ -e "${MY_ICONS[0]}" ] && step "$S_I_MYICONS" python3 "$HERE/werkzeuge/symbolwerkstatt.py" --import "${MY_ICONS[@]}"
has werkst   && step "$S_I_WERKST" python3 "$HERE/werkzeuge/symbolwerkstatt.py" --install
if has setgrid; then
  step "$S_I_SETGRID" bash "$HERE/werkzeuge/einstellungen.sh"
elif grep -qs "Monterra – Starter" "$HOME/.local/bin/cinnamon-settings"; then
  step "$S_UN_SETGRID" bash "$HERE/werkzeuge/einstellungen.sh" --remove
fi
if has fgroesse; then
  step "$S_I_WINSIZE" bash "$HERE/werkzeuge/fenstergroesse.sh"
elif [ -d "$HOME/.local/share/cinnamon/extensions/monterra-fenstergroesse@monterra" ]; then
  step "$S_UN_WINSIZE" bash "$HERE/werkzeuge/fenstergroesse.sh" --remove
fi
if has fenster; then
  step "$S_I_WINDOWS" bash "$HERE/werkzeuge/fenster.sh"
elif [ "$HAS_WIN" = on ]; then
  step "$S_UN_WINDOWS" bash "$HERE/werkzeuge/fenster.sh" --remove
fi
has firefox  && step "$S_I_FIREFOX" bash "$HERE/werkzeuge/firefox.sh"
has thunderb && step "$S_I_THUNDERBIRD" bash "$HERE/werkzeuge/thunderbird.sh"

# 5) Schritte mit Administratorrechten
if [ "$SUDO_OK" = 1 ]; then
  has folders && step "$S_I_FOLDERS" bash "$HERE/werkzeuge/ordnerfarben.sh"
  if has splash; then
    if [ "$VARIANT" = dark ]; then
      step "$S_I_SPLASH_DARK" sudo bash "$HERE/werkzeuge/bootsplash.sh"
    else
      step "$S_I_SPLASH_LIGHT" sudo bash "$HERE/werkzeuge/bootsplash.sh" --light
    fi
  fi
  if has login; then
    # Anmelde-Hintergrund passend zum Desktop-Motiv (weichgezeichnet)
    LMOT="$WALL"
    if [ "$LMOT" = keep ]; then             # Farbe des gerade eingestellten Monterra-Hintergrunds
      cur="$(gsettings get org.cinnamon.desktop.background picture-uri 2>/dev/null)"
      LMOT="$(echo "$cur" | sed -n 's#.*/Monterra-\([A-Za-z]*\)-\(Hell\|Dunkel\)\.jpg.*#\1#p' | tr A-Z a-z)"
      [ -n "$LMOT" ] || LMOT=himmel
    fi
    if [ "$VARIANT" = dark ]; then
      step "$S_I_LOGIN_DARK" sudo bash "$HERE/werkzeuge/anmeldung.sh" --motiv "$LMOT"
    else
      step "$S_I_LOGIN_LIGHT" sudo bash "$HERE/werkzeuge/anmeldung.sh" --motiv "$LMOT" --day
    fi
  fi
elif has folders || has splash || has login; then
  FAILED+=("$S_I_NO_PASSWORD")
fi

# 6) Cinnamon neu laden
echo; echo "▶ $S_I_RESTART"
restart_cinnamon

if [ ${#FAILED[@]} -eq 0 ]; then info "$S_I_DONE"; else failed_report; fi
