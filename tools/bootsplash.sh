#!/bin/bash
# =====================================================================
#  Monterra – Boot-Splash (Plymouth) installieren / entfernen
#
#     sudo bash tools/bootsplash.sh            -> dunkler Splash (schwarz, weißes Logo)
#     sudo bash tools/bootsplash.sh --light    -> heller Splash (hellgrau, dunkles Logo)
#     sudo bash tools/bootsplash.sh --remove   -> zurück zum Linux-Mint-Standard
#
#  Benötigt Administratorrechte, da Plymouth-Themes systemweit liegen
#  (/usr/share/plymouth/themes) und das initramfs neu erzeugt werden muss.
# =====================================================================
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
if [ "$(id -u)" -ne 0 ]; then
  exec sudo bash "$0" "$@"
fi

THEMES=/usr/share/plymouth/themes
DIR=$THEMES/monterra
LINK=$THEMES/default.plymouth

if [ "$1" = "--remove" ]; then
  update-alternatives --remove default.plymouth "$DIR/monterra.plymouth" 2>/dev/null || true
  rm -rf "$DIR"
  echo "Aktiver Splash: $(readlink -f $LINK 2>/dev/null)"
  echo "Erzeuge initramfs neu (kann eine Minute dauern) …"
  update-initramfs -u
  echo "Monterra-Splash entfernt. Beim nächsten Start erscheint wieder der Standard-Splash."
  exit 0
fi

if [ ! -f "$ROOT/components/bootsplash/monterra/monterra.plymouth" ]; then
  echo "Ordner 'splash/monterra' nicht gefunden – bitte im entpackten Monterra-Ordner ausführen."
  exit 1
fi

rm -rf "$DIR"
cp -r "$ROOT/components/bootsplash/monterra" "$THEMES/"
if [ "$1" = "--light" ]; then
  sed -i 's/^light = 0;/light = 1;/' "$DIR/monterra.script"
fi
chmod -R a+rX "$DIR"

update-alternatives --install "$LINK" default.plymouth "$DIR/monterra.plymouth" 200
update-alternatives --set default.plymouth "$DIR/monterra.plymouth"

if ! dpkg -s plymouth-label >/dev/null 2>&1; then
  echo "Hinweis: Paket 'plymouth-label' fehlt – ohne es werden Texte (z. B. die Passwortabfrage) nicht angezeigt."
  echo "         Installation: sudo apt install plymouth-label"
fi

echo "Erzeuge initramfs neu (kann eine Minute dauern) …"
update-initramfs -u

if ! grep -qw splash /proc/cmdline; then
  echo
  echo "Hinweis: Der aktuelle Start nutzt keinen Splash ('splash' fehlt in den Kernel-Parametern)."
  echo "In /etc/default/grub bei GRUB_CMDLINE_LINUX_DEFAULT \"quiet splash\" eintragen und 'sudo update-grub' ausführen."
fi

echo
echo "Fertig. Der Monterra-Splash erscheint beim nächsten Neustart."
echo "Rückgängig: sudo bash tools/bootsplash.sh --remove"
