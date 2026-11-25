# Monterra – Hintergrundmotive (wird von werkzeuge/setup.sh, werkzeuge/anmeldung.sh und dem Installer setup.sh eingebunden)
#
#   Himmel     Blau + Indigo
#   Wueste     Orange + Gelb
#   Mars       Rot + Braun
#   Dschungel  Grün + Petrol + Cyan
#   Seide      Grau + Graphit
#   Bluete     Lila + Pink
MOTIVE="Himmel Wueste Mars Dschungel Seide Bluete"

# motiv_von NAME -> Motiv (nimmt Motivnamen und – für frühere Versionen – Farbnamen an); leer = unbekannt
motiv_von() {
  local n; n="$(echo "$1" | sed 's/ü/ue/g; s/Ü/Ue/g' | tr 'A-Z' 'a-z')"
  case "$n" in
    himmel|sky|cielo|blau|blue|azul|indigo) echo Himmel ;;
    bluete|blute|blüte|blossom|flor|lila|purple|morado|pink|rosa) echo Bluete ;;
    wueste|wuste|desert|desierto|orange|naranja|gelb|yellow|amarillo) echo Wueste ;;
    mars|marte|rot|red|rojo|braun|brown|marron|marrón) echo Mars ;;
    dschungel|jungle|jungla|gruen|green|verde|petrol|teal|cyan|cian) echo Dschungel ;;
    seide|silk|seda|grau|grey|gray|gris|graphit|graphite|grafito) echo Seide ;;
    *) echo "" ;;
  esac
}

# passende Akzentfarbe zu einem Motiv
akzent_zu_motiv() {
  case "$(motiv_von "$1")" in
    Himmel) echo blau ;; Wueste) echo orange ;; Mars) echo rot ;; Dschungel) echo gruen ;; Seide) echo graphit ;; Bluete) echo lila ;;
    *) echo blau ;;
  esac
}
