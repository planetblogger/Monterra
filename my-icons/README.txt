Take your own app icons with you.
(Deutsch: Hier kannst du deine selbst gestalteten Programmsymbole mitnehmen – Schritte siehe unten.)

1. On the computer where you designed the icons:
   Icon Workshop → File → "Export your own app icons …"
   (or: python3 tools/icon_workshop.py --export my.monterra-symbole.zip)

2. Put the resulting file (*.monterra-symbole.zip) into this folder.

3. On the other computer, run "bash setup.sh" as usual –
   every file in this folder is imported automatically.

You can also import later at any time:
   python3 tools/icon_workshop.py --import my-icons/*.zip
