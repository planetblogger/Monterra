# Monterra – Hintergrundmotive (wird von tools/setup.sh, tools/login-screen.sh und dem Installer setup.sh eingebunden)
#
#   Sky       Blue + Indigo
#   Desert    Orange + Yellow
#   Mars      Red + Brown
#   Jungle    Green + Teal + Cyan
#   Silk      Grey + Graphite
#   Blossom   Purple + Pink
MOTIFS="Sky Desert Mars Jungle Silk Blossom"

# motif_of NAME -> Motiv (nimmt Motiv- und Farbnamen auf Englisch, Deutsch und Spanisch an,
# auch die deutschen Namen früherer Versionen); leer = unbekannt
motif_of() {
  local n; n="$(echo "$1" | sed 's/ü/ue/g; s/Ü/Ue/g' | tr 'A-Z' 'a-z')"
  case "$n" in
    sky|himmel|cielo|blue|blau|azul|indigo) echo Sky ;;
    blossom|bluete|blute|blüte|flor|purple|lila|morado|pink|rosa) echo Blossom ;;
    desert|wueste|wuste|desierto|orange|naranja|yellow|gelb|amarillo) echo Desert ;;
    mars|marte|red|rot|rojo|brown|braun|marron|marrón) echo Mars ;;
    jungle|dschungel|jungla|green|gruen|verde|teal|petrol|cyan|cian) echo Jungle ;;
    silk|seide|seda|grey|gray|grau|gris|graphite|graphit|grafito) echo Silk ;;
    *) echo "" ;;
  esac
}

# passende Akzentfarbe zu einem Motiv
accent_for_motif() {
  case "$(motif_of "$1")" in
    Sky) echo blue ;; Desert) echo orange ;; Mars) echo red ;; Jungle) echo green ;; Silk) echo graphite ;; Blossom) echo purple ;;
    *) echo blue ;;
  esac
}

# Variante aus dem Dateinamen eines Monterra-Hintergrunds: "Monterra-Sky-Light.jpg" -> "Sky"
# (versteht auch die deutschen Namen früherer Versionen, z. B. "Monterra-Himmel-Hell.jpg")
motif_from_file() {
  local m
  m="$(echo "$1" | sed -n 's#.*Monterra-\([A-Za-z]*\)-\(Light\|Dark\|Hell\|Dunkel\)\.jpg.*#\1#p')"
  [ -n "$m" ] && motif_of "$m"
}
