Quellcode von Monterra – nur nötig, wenn du das Theme selbst neu bauen möchtest.
Für die Installation wird dieser Ordner nicht gebraucht.

Build: git clone https://github.com/linuxmint/mint-themes
       pip install libsass pillow numpy scipy   (außerdem rsvg-convert, xcursorgen)
       python3 theme/build.py /pfad/zu/mint-themes           -> theme/dist (GTK 2/3/4, Cinnamon, libadwaita)
         (Akzentfarbe: MONTERRA_AKZENT=Gruen python3 theme/build.py …; Farbwerte in theme/akzente.py)
       python3 theme/make_akzente.py PAKET/themes             (alle 13 Akzentfarben, Blau + Abweichungen)
       python3 tools/icons.py dist/.icons/Monterra            (inkl. Einstellungs- und Panel-Symbole)
       python3 tools/cursors.py dist/.icons/Monterra-Cursor
       python3 tools/folder_colors.py dist/.icons dist/folder-colors/Monterra.json
       python3 tools/wallpapers_motive.py OUT                 (Hintergründe: 6 Motive × Hell/Dunkel)
       python3 tools/login_backgrounds.py OUT OUT/anmeldung   (weichgezeichnete Anmelde-Varianten)
       python3 tools/splash.py splash/monterra
       python3 tools/firefox_theme.py firefox                (userChrome.css / userContent.css)

theme/      – das Theme: Mint-Y + Farbpalette + Akzentfarbe + größere Radien + drei kleine
              Schichten (theme/schichten/_gtk3.scss, _gtk4.scss, _cinnamon.scss).
              Keine Eingriffe in den Fenstermanager; Cinnamon zeichnet die Systemrahmen
              aus der GTK-3-Datei. theme/vorschau/ = Vorschaubilder für die Theme-Auswahl.
third_party/ – Phosphor-Symbole (MIT-Lizenz) als Grundlage für einige Symbole

Symbolwerkstatt: komponenten/symbolwerkstatt/glyphs.json entsteht aus dem npm-Paket @phosphor-icons/core 2.1.1
(alle 1512 "fill"-Symbole samt Stichwörtern, MIT-Lizenz).
