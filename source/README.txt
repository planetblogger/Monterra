Monterra source code – only needed if you want to rebuild the theme yourself.
This folder is not needed for the installation.

Build: git clone https://github.com/linuxmint/mint-themes
       pip install libsass pillow numpy scipy   (plus rsvg-convert, xcursorgen)
       python3 theme/build.py /path/to/mint-themes            -> theme/dist (GTK 2/3/4, Cinnamon, libadwaita)
         (accent colour: MONTERRA_ACCENT=Green python3 theme/build.py …; colour values in theme/accents.py)
       python3 theme/make_accents.py PACKAGE/themes           (all 13 accent colours: Blue + differences)
       python3 tools/icons.py dist/.icons/Monterra            (incl. settings and panel icons)
       python3 tools/cursors.py dist/.icons/Monterra-Cursor
       python3 tools/folder_colors.py dist/.icons dist/folder-colors/Monterra.json
       python3 tools/wallpaper_motifs.py OUT                  (wallpapers: 6 motifs × Light/Dark)
       python3 tools/login_backgrounds.py OUT OUT/login       (blurred login variants)
       python3 tools/installer_previews.py PACKAGE            (preview images for the installer)
       python3 tools/splash.py splash/monterra
       python3 tools/firefox_theme.py firefox                 (userChrome.css / userContent.css)
       python3 theme/checks/contrast_gtk3.py THEME_NAME       (contrast check of one installed theme)

theme/        – the theme: Mint-Y + colour palette + accent colour + larger radii + three small
                layers (theme/layers/_gtk3.scss, _gtk4.scss, _cinnamon.scss).
                No changes to the window manager; Cinnamon draws the system frames
                from the GTK 3 file. theme/previews/ = preview images for the theme selection.
third_party/  – Phosphor icons (MIT licence) as the basis for some icons

Icon Workshop: components/icon-workshop/glyphs.json is built from the npm package @phosphor-icons/core 2.1.1
(all 1512 "fill" icons with keywords, MIT licence).
