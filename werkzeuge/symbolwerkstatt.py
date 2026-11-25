#!/usr/bin/python3
"""
Monterra Symbolwerkstatt – Programmsymbole im Stil der Monterra-Systemeinstellungen:
weißes Symbol auf einer farbigen, abgerundeten Fläche (Squircle).

  Symbol aus einer Bildvorlage (PNG, JPG, SVG …) oder per Stichwort aus über
  1500 Symbolen wählen, Farbe aussuchen, als PNG/SVG speichern oder direkt
  einem installierten Programm zuweisen.

  python3 symbolwerkstatt.py                 Programm starten
  python3 symbolwerkstatt.py BILD            mit einer Bildvorlage starten
  python3 symbolwerkstatt.py --install       ins Menü eintragen (unter „Grafik“)
  python3 symbolwerkstatt.py --remove        aus dem Menü entfernen
  python3 symbolwerkstatt.py --export DATEI  eigene Programmsymbole für andere Rechner sichern
  python3 symbolwerkstatt.py --import DATEI  … und dort wieder einspielen
  python3 symbolwerkstatt.py --reparieren    eigene Symbole, die nicht erscheinen, richtig zuordnen
  python3 symbolwerkstatt.py --lang=en       Sprache wählen (de, en, es); sonst wie im Installer bzw. System

Symbole: Phosphor Icons (MIT-Lizenz), siehe PHOSPHOR-LICENSE.
"""
import configparser
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa: E402
import cairo  # noqa: E402

# ------------------------------------------------------------------ Sprache (de / en / es)
# Reihenfolge: --lang=xx, MONTERRA_LANG, die im Installer gewählte Sprache
# (~/.config/monterra-sprache.conf), sonst die Systemsprache. Grundsprache ist Deutsch.
def _detect_lang():
    for a in sys.argv:
        if a.startswith("--lang="):
            return a.split("=", 1)[1][:2].lower()
    if os.environ.get("MONTERRA_LANG"):
        return os.environ["MONTERRA_LANG"][:2].lower()
    try:
        v = (Path.home() / ".config" / "monterra-sprache.conf").read_text().strip()[:2].lower()
        if v:
            return v
    except OSError:
        pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var, "")
        if v and v not in ("C", "POSIX") and not v.startswith("C."):
            return v[:2].lower()
    return "de"


LANG = _detect_lang()
if LANG not in ("de", "en", "es"):
    LANG = "en"

TR = {
    # Fenster
    "Symbolwerkstatt": ("Icon Workshop", "Taller de iconos"),
    "Programmsymbole im Monterra-Stil": ("App icons in Monterra style", "Iconos de aplicaciones al estilo Monterra"),
    "Datei": ("File", "Archivo"),
    "Als PNG speichern (512 × 512) …": ("Save as PNG (512 × 512) …", "Guardar como PNG (512 × 512) …"),
    "Als SVG speichern (nur Stichwort-Symbole) …": ("Save as SVG (keyword symbols only) …",
                                                    "Guardar como SVG (solo símbolos por palabra clave) …"),
    "Eigene Programmsymbole exportieren …": ("Export my app icons …", "Exportar mis iconos de aplicaciones …"),
    "Eigene Programmsymbole importieren …": ("Import my app icons …", "Importar mis iconos de aplicaciones …"),
    "Für Programm verwenden …": ("Use for app …", "Usar para una aplicación …"),
    "Stichwörter, z. B. „Kamera“ oder „Musik, Noten“": ("Keywords, e.g. “camera” or “music, notes”",
                                                        "Palabras clave, p. ej. «cámara» o «música, notas»"),
    "Deutsche oder englische Begriffe – mehrere mit Komma trennen.": (
        "Enter English or German words – separate several with commas.",
        "Escribe palabras en español o inglés – separa varias con comas."),
    "Aus Stichwort": ("From keyword", "Por palabra clave"),
    "Bildvorlage wählen": ("Choose a template image", "Elegir imagen de plantilla"),
    "Bilder": ("Images", "Imágenes"),
    "Vorlage": ("Template", "Plantilla"),
    "Automatisch": ("Automatic", "Automático"),
    "Umriss (transparente Bilder)": ("Outline (transparent images)", "Contorno (imágenes transparentes)"),
    "Abhebung vom Hintergrund": ("Contrast with background", "Contraste con el fondo"),
    "Dunkle Bereiche": ("Dark areas", "Zonas oscuras"),
    "Helle Bereiche": ("Light areas", "Zonas claras"),
    "Erkennung": ("Detection", "Detección"),
    "Schwelle": ("Threshold", "Umbral"),
    "Umkehren (Flächen tauschen)": ("Invert (swap areas)", "Invertir (intercambiar zonas)"),
    "Am besten eignen sich einfache Logos oder Piktogramme mit klarer Form. "
    "Aus dem Bild wird automatisch eine weiße Silhouette.": (
        "Simple logos or pictograms with a clear shape work best. "
        "The image is turned into a white silhouette automatically.",
        "Funcionan mejor los logotipos o pictogramas sencillos de forma clara. "
        "La imagen se convierte automáticamente en una silueta blanca."),
    "Aus Bild": ("From image", "Desde imagen"),
    "<b>Hintergrundfarbe</b>": ("<b>Background colour</b>", "<b>Color de fondo</b>"),
    "Eigene Farbe": ("Custom colour", "Color personalizado"),
    "Eigene Farbe wählen": ("Choose a custom colour", "Elegir un color personalizado"),
    "Symbolgröße": ("Symbol size", "Tamaño del símbolo"),
    "Stern": ("star", "estrella"),
    # Farben
    "Blau": ("Blue", "Azul"), "Indigo": ("Indigo", "Índigo"), "Lila": ("Purple", "Morado"),
    "Pink": ("Pink", "Rosa"), "Rot": ("Red", "Rojo"), "Orange": ("Orange", "Naranja"),
    "Gelb": ("Yellow", "Amarillo"), "Grün": ("Green", "Verde"), "Petrol": ("Teal", "Verde azulado"),
    "Cyan": ("Cyan", "Cian"), "Braun": ("Brown", "Marrón"), "Grau": ("Grey", "Gris"),
    "Graphit": ("Graphite", "Grafito"),
    # Status
    "Symbol „{name}“ · Farbe {color}": ("Symbol “{name}” · colour {color}", "Símbolo «{name}» · color {color}"),
    "Vorlage {name} · Farbe {color}": ("Template {name} · colour {color}", "Plantilla {name} · color {color}"),
    "Wähle ein Symbol per Stichwort oder eine Bildvorlage.": (
        "Pick a symbol by keyword or load a template image.",
        "Elige un símbolo por palabra clave o carga una imagen de plantilla."),
    "Nichts gefunden – versuche ein anderes oder englisches Wort.": (
        "Nothing found – try another word.", "No se encontró nada – prueba otra palabra o una en inglés."),
    "{n} Treffer – Symbol anklicken. Deutsche oder englische Begriffe, mehrere mit Komma trennen.": (
        "{n} results – click a symbol. Separate several words with commas.",
        "{n} resultados – haz clic en un símbolo. Separa varias palabras con comas."),
    "Die Bilddatei konnte nicht gelesen werden.": ("The image file could not be read.",
                                                   "No se pudo leer el archivo de imagen."),
    "In der Vorlage wurde keine Form erkannt – Schwelle oder Erkennung ändern.": (
        "No shape found in the template – change the threshold or detection.",
        "No se detectó ninguna forma en la plantilla – cambia el umbral o la detección."),
    "_Abbrechen": ("_Cancel", "_Cancelar"),
    "_Speichern": ("_Save", "_Guardar"),
    "_Importieren": ("_Import", "_Importar"),
    "_Übernehmen": ("_Apply", "_Aplicar"),
    "Symbol als PNG speichern": ("Save symbol as PNG", "Guardar símbolo como PNG"),
    "Symbol als SVG speichern": ("Save symbol as SVG", "Guardar símbolo como SVG"),
    "Gespeichert: {fn}": ("Saved: {fn}", "Guardado: {fn}"),
    "Es gibt noch keine eigenen Programmsymbole.": ("There are no custom app icons yet.",
                                                    "Todavía no hay iconos de aplicaciones propios."),
    "Weise zuerst mit „Für Programm verwenden …“ einem Programm ein Symbol zu.": (
        "First assign a symbol to an app with “Use for app …”.",
        "Primero asigna un símbolo a una aplicación con «Usar para una aplicación …»."),
    "Eigene Programmsymbole exportieren": ("Export my app icons", "Exportar mis iconos de aplicaciones"),
    "Eigene Programmsymbole importieren": ("Import my app icons", "Importar mis iconos de aplicaciones"),
    "{n} eigene Programmsymbole exportiert.": ("{n} custom app icons exported.",
                                               "{n} iconos de aplicaciones exportados."),
    "Auf dem anderen Rechner: Datei in den Ordner „meine-symbole“ des Monterra-Pakets legen "
    "(der Installer übernimmt sie dann automatisch) oder hier über „Importieren …“ laden.": (
        "On the other computer: put the file into the “meine-symbole” folder of the Monterra package "
        "(the installer then applies it automatically) or load it here with “Import …”.",
        "En el otro ordenador: coloca el archivo en la carpeta «meine-symbole» del paquete Monterra "
        "(el instalador lo aplicará automáticamente) o cárgalo aquí con «Importar …»."),
    "Monterra-Symbole (*.zip)": ("Monterra icons (*.zip)", "Iconos Monterra (*.zip)"),
    "Die Datei konnte nicht importiert werden.": ("The file could not be imported.",
                                                  "No se pudo importar el archivo."),
    "Diese Programme sind hier (noch) nicht installiert: {apps}. Ist die Monterra-Automatik eingeschaltet, "
    "bekommen sie ihr Symbol nach der Installation von selbst – sonst danach einfach noch einmal importieren.\n\n": (
        "These apps are not installed here (yet): {apps}. If Monterra automation is on, they get their icon "
        "automatically once installed – otherwise just import again afterwards.\n\n",
        "Estas aplicaciones (todavía) no están instaladas aquí: {apps}. Si la automatización de Monterra está "
        "activada, recibirán su icono al instalarse; si no, vuelve a importar después.\n\n"),
    "{n} Programmsymbole übernommen.": ("{n} app icons applied.", "{n} iconos de aplicaciones aplicados."),
    "Im Menü erscheinen sie nach wenigen Sekunden, im Panel/Dock nach Alt+F2 → r.": (
        "They appear in the menu after a few seconds, in the panel/dock after Alt+F2 → r.",
        "Aparecen en el menú tras unos segundos y en el panel/dock tras Alt+F2 → r."),
    "Bitte zuerst ein Symbol wählen oder eine Bildvorlage laden.": (
        "Please pick a symbol or load a template image first.",
        "Primero elige un símbolo o carga una imagen de plantilla."),
    "Für Programm verwenden": ("Use for app", "Usar para una aplicación"),
    "Programm suchen …": ("Search apps …", "Buscar aplicación …"),
    "Das Symbol ersetzt das bisherige Programmsymbol im Monterra-Theme. "
    "Rückgängig: python3 werkzeuge/programmsymbole.py restore": (
        "The symbol replaces the app's current icon in the Monterra theme. "
        "Undo: python3 werkzeuge/programmsymbole.py restore",
        "El símbolo sustituye al icono actual de la aplicación en el tema Monterra. "
        "Deshacer: python3 werkzeuge/programmsymbole.py restore"),
    "Das Symbol konnte nicht übernommen werden.": ("The symbol could not be applied.",
                                                   "No se pudo aplicar el símbolo."),
    "„{app}“ hat jetzt das neue Symbol.": ("“{app}” now has the new icon.", "«{app}» ya tiene el nuevo icono."),
    "Gespeichert als {name}. Im Menü erscheint es nach wenigen Sekunden, "
    "im Panel/Dock nach Alt+F2 → r (Cinnamon neu laden).": (
        "Saved as {name}. It appears in the menu after a few seconds, "
        "in the panel/dock after Alt+F2 → r (reload Cinnamon).",
        "Guardado como {name}. Aparece en el menú tras unos segundos "
        "y en el panel/dock tras Alt+F2 → r (recargar Cinnamon)."),
    # Kommandozeile
    "Symbolwerkstatt ist jetzt im Menü unter „Grafik“ zu finden.": (
        "Icon Workshop is now in the menu under “Graphics”.",
        "El Taller de iconos ya está en el menú, en «Gráficos»."),
    "Symbolwerkstatt aus dem Menü entfernt. Bereits erstellte Symbole bleiben erhalten.": (
        "Icon Workshop removed from the menu. Icons you created stay in place.",
        "Taller de iconos eliminado del menú. Los iconos ya creados se conservan."),
    "Reparatur nicht möglich: {e}": ("Repair not possible: {e}", "No se pudo reparar: {e}"),
    "Eigene Symbole jetzt aktiv für: {apps} (im Panel/Dock nach Alt+F2 → r)": (
        "Custom icons now active for: {apps} (in the panel/dock after Alt+F2 → r)",
        "Iconos propios activos ahora para: {apps} (en el panel/dock tras Alt+F2 → r)"),
    "Alle eigenen Programmsymbole sind richtig zugeordnet.": ("All custom app icons are assigned correctly.",
                                                              "Todos los iconos propios están bien asignados."),
    "{n} eigene Programmsymbole exportiert nach {dest}": ("{n} custom app icons exported to {dest}",
                                                          "{n} iconos propios exportados a {dest}"),
    "Bitte die Export-Datei angeben.": ("Please give the export file.", "Indica el archivo de exportación."),
    "{name}: {n} Programmsymbole übernommen.": ("{name}: {n} app icons applied.",
                                                "{name}: {n} iconos de aplicaciones aplicados."),
    "   noch nicht installiert: {apps} – wird nach deren Installation von der Automatik übernommen "
    "(sonst erneut importieren)": (
        "   not installed yet: {apps} – applied by the automation once installed (otherwise import again)",
        "   aún no instaladas: {apps} – la automatización lo aplicará al instalarlas (si no, importa de nuevo)"),
}


HELP = {
    "en": """Monterra Icon Workshop – app icons in the style of the Monterra system settings:
a white symbol on a coloured, rounded tile (squircle).

  python3 symbolwerkstatt.py                 start the program
  python3 symbolwerkstatt.py IMAGE           start with a template image
  python3 symbolwerkstatt.py --install       add to the menu (under “Graphics”)
  python3 symbolwerkstatt.py --remove        remove from the menu
  python3 symbolwerkstatt.py --export FILE   back up your own app icons for other computers
  python3 symbolwerkstatt.py --import FILE   … and restore them there
  python3 symbolwerkstatt.py --repair        fix custom icons that do not show up
  python3 symbolwerkstatt.py --lang=de|en|es choose the language

Symbols: Phosphor Icons (MIT licence), see PHOSPHOR-LICENSE.
""",
    "es": """Taller de iconos de Monterra – iconos de aplicaciones al estilo de la configuración de Monterra:
un símbolo blanco sobre una placa de color redondeada (squircle).

  python3 symbolwerkstatt.py                 iniciar el programa
  python3 symbolwerkstatt.py IMAGEN          iniciar con una imagen de plantilla
  python3 symbolwerkstatt.py --install       añadir al menú (en «Gráficos»)
  python3 symbolwerkstatt.py --remove        quitar del menú
  python3 symbolwerkstatt.py --export ARCHIVO  guardar tus iconos para otros ordenadores
  python3 symbolwerkstatt.py --import ARCHIVO  … y restaurarlos allí
  python3 symbolwerkstatt.py --repair        corregir iconos propios que no aparecen
  python3 symbolwerkstatt.py --lang=de|en|es elegir el idioma

Símbolos: Phosphor Icons (licencia MIT), ver PHOSPHOR-LICENSE.
""",
}


def _(text, **kw):
    """Übersetzen; Platzhalter {name} werden danach eingesetzt."""
    if LANG != "de" and text in TR:
        text = TR[text][0 if LANG == "en" else 1]
    return text.format(**kw) if kw else text


# spanische Stichwörter -> englische Begriffe der Symbolbibliothek
ES = {
    "casa": "house home", "inicio": "house home", "hogar": "house home", "carpeta": "folder",
    "archivo": "file", "archivos": "files", "documento": "file text", "texto": "text file",
    "nota": "note notepad", "notas": "note notebook", "libro": "book", "libros": "books",
    "imagen": "image picture", "imágenes": "images", "foto": "camera image", "fotos": "images",
    "cámara": "camera", "camara": "camera", "vídeo": "video film", "video": "video film",
    "película": "film video", "música": "music note", "musica": "music note", "audio": "speaker waveform",
    "altavoz": "speaker", "micrófono": "microphone", "microfono": "microphone", "auriculares": "headphones",
    "radio": "radio", "televisión": "television", "tele": "television", "juego": "game controller",
    "juegos": "game", "dado": "dice", "correo": "envelope", "email": "envelope", "carta": "envelope",
    "mensaje": "chat message", "chat": "chat", "teléfono": "phone", "telefono": "phone", "móvil": "device mobile",
    "movil": "device mobile", "calendario": "calendar", "reloj": "clock", "alarma": "alarm",
    "tiempo": "cloud sun weather clock", "sol": "sun", "luna": "moon", "nube": "cloud", "lluvia": "rain",
    "nieve": "snowflake", "rayo": "lightning", "ajustes": "gear", "configuración": "gear",
    "configuracion": "gear", "engranaje": "gear", "herramienta": "wrench tool", "herramientas": "toolbox",
    "llave inglesa": "wrench", "martillo": "hammer", "pincel": "paint brush", "color": "palette",
    "pintar": "paint brush", "dibujar": "pencil pen", "lápiz": "pencil", "lapiz": "pencil",
    "tijeras": "scissors", "buscar": "magnifying glass", "búsqueda": "magnifying glass", "lupa": "magnifying glass",
    "seguridad": "shield lock", "candado": "lock", "llave": "key", "contraseña": "password key",
    "protección": "shield", "virus": "bug virus", "error": "bug warning", "red": "network",
    "internet": "globe", "web": "globe browser", "navegador": "browser globe", "wifi": "wifi",
    "bluetooth": "bluetooth", "nube de datos": "cloud", "descargar": "download", "descarga": "download",
    "subir": "upload", "compartir": "share", "impresora": "printer", "escáner": "scan", "escaner": "scan",
    "monitor": "monitor", "pantalla": "monitor", "ordenador": "desktop computer", "computadora": "desktop computer",
    "portátil": "laptop", "portatil": "laptop", "teclado": "keyboard", "ratón": "mouse", "raton": "mouse",
    "disco duro": "hard drive", "disco": "hard drive", "almacenamiento": "hard drives database",
    "base de datos": "database", "servidor": "hard drives", "usb": "usb", "procesador": "cpu",
    "batería": "battery", "bateria": "battery", "enchufe": "plug lightning", "terminal": "terminal",
    "código": "code", "codigo": "code", "programar": "code brackets", "consola": "terminal",
    "dinero": "money currency", "banco": "bank", "euro": "currency eur", "caja": "cash register",
    "comprar": "shopping cart", "compras": "shopping cart", "carrito": "shopping cart", "tienda": "storefront",
    "bolsa": "bag", "regalo": "gift", "mapa": "map", "navegación": "navigation compass",
    "brújula": "compass", "ubicación": "map pin", "lugar": "map pin", "coche": "car", "auto": "car",
    "bicicleta": "bicycle", "moto": "motorcycle", "autobús": "bus", "autobus": "bus", "tren": "train",
    "avión": "airplane", "avion": "airplane", "barco": "boat", "viaje": "airplane suitcase",
    "maleta": "suitcase", "cohete": "rocket", "persona": "user", "usuario": "user", "contactos": "address book",
    "grupo": "users", "familia": "users", "bebé": "baby", "niño": "baby", "corazón": "heart",
    "corazon": "heart", "estrella": "star", "favorito": "star", "marcador": "bookmark", "bandera": "flag",
    "campana": "bell", "notificación": "bell", "aviso": "bell warning", "información": "info",
    "ayuda": "question", "pregunta": "question", "advertencia": "warning", "atención": "warning",
    "listo": "check", "lista": "list", "tareas": "list checks", "plan": "kanban", "gráfico": "chart",
    "estadística": "chart bar", "tabla": "table", "presentación": "presentation", "calculadora": "calculator",
    "matemáticas": "math", "traducir": "translate", "idioma": "translate", "fuente": "text aa",
    "aprender": "graduation cap student", "escuela": "student", "ciencia": "flask atom",
    "medicina": "first aid heartbeat", "salud": "heartbeat", "deporte": "barbell", "comida": "fork knife",
    "cocinar": "cooking pot", "receta": "cooking pot", "café": "coffee", "cafe": "coffee",
    "bebida": "beer wine coffee", "pizza": "pizza", "naturaleza": "leaf tree", "planta": "plant",
    "árbol": "tree", "arbol": "tree", "flor": "flower", "animal": "paw print", "perro": "dog",
    "gato": "cat", "pájaro": "bird", "pajaro": "bird", "pez": "fish", "fuego": "fire flame", "agua": "drop",
    "papelera": "trash", "basura": "trash", "borrar": "trash", "eliminar": "trash", "archivar": "archive",
    "paquete": "package", "zip": "file zip", "copia de seguridad": "cloud arrow up", "respaldo": "cloud arrow up",
    "sincronizar": "arrows clockwise", "actualizar": "arrows clockwise", "sistema": "gear cpu",
    "aplicación": "app window", "aplicacion": "app window", "programa": "app window", "ventana": "app window",
    "copiar": "copy", "portapapeles": "clipboard", "enlace": "link", "adjunto": "paperclip",
    "editar": "pencil", "varita": "magic wand", "ia": "sparkle robot", "robot": "robot", "idea": "lightbulb",
    "luz": "lightbulb", "lámpara": "lamp lightbulb", "interruptor": "toggle", "control": "sliders",
    "mando": "remote", "router": "router", "vigilancia": "security camera", "podcast": "microphone podcast",
    "grabar": "record", "edición de imagen": "image paint brush", "vector": "pen nib", "3d": "cube",
    "puzle": "puzzle piece", "extensión": "puzzle piece",
}

HERE = Path(__file__).resolve().parent
HOME = Path.home()
DATA_CANDIDATES = [HERE, HERE.parent / "komponenten" / "symbolwerkstatt"]
LOCAL = HOME / ".icons" / "Monterra-Local"
MONTERRA = HOME / ".icons" / "Monterra"
CUSTOM_LIST = LOCAL / "eigene-symbole.txt"
INSTALL_DIR = HOME / ".local/share/monterra/symbolwerkstatt"
DESKTOP_FILE = HOME / ".local/share/applications/monterra-symbolwerkstatt.desktop"
APP_ICON = HOME / ".local/share/icons/hicolor/256x256/apps/monterra-symbolwerkstatt.png"

# Systemfarben (wie in den Monterra-Systemeinstellungen)
COLORS = [
    ("Blau", "#0A84FF"), ("Indigo", "#5E5CE6"), ("Lila", "#AF52DE"), ("Pink", "#FF375F"),
    ("Rot", "#FF453A"), ("Orange", "#FF9F0A"), ("Gelb", "#FFCC00"), ("Grün", "#30D158"),
    ("Petrol", "#30B0C7"), ("Cyan", "#32ADE6"), ("Braun", "#A2845E"), ("Grau", "#8E8E93"),
    ("Graphit", "#3A3A3C"),
]

SQUIRCLE = ("M32 5 C50.5 5 59 6.8 59 32 C59 57.2 50.5 59 32 59 "
            "C13.5 59 5 57.2 5 32 C5 6.8 13.5 5 32 5 Z")

# deutsche Stichwörter -> englische Begriffe der Symbolbibliothek
DE = {
    "haus": "house home", "zuhause": "house home", "start": "house home", "startseite": "house",
    "ordner": "folder", "datei": "file", "dateien": "files", "dokument": "file text", "text": "text file",
    "notiz": "note notepad", "notizen": "note notebook", "buch": "book", "bücher": "books",
    "bild": "image picture", "bilder": "images", "foto": "camera image", "fotos": "images",
    "kamera": "camera", "video": "video film", "film": "film video", "musik": "music note",
    "audio": "speaker waveform", "lautsprecher": "speaker", "mikrofon": "microphone",
    "kopfhörer": "headphones", "radio": "radio", "fernsehen": "television", "tv": "television",
    "spiel": "game controller", "spiele": "game", "würfel": "dice",
    "mail": "envelope", "email": "envelope", "e-mail": "envelope", "brief": "envelope",
    "nachricht": "chat message", "chat": "chat", "telefon": "phone", "handy": "device mobile",
    "kalender": "calendar", "uhr": "clock", "wecker": "alarm", "zeit": "clock timer",
    "wetter": "cloud sun weather", "sonne": "sun", "mond": "moon", "wolke": "cloud",
    "regen": "rain", "schnee": "snowflake", "blitz": "lightning",
    "einstellungen": "gear", "zahnrad": "gear", "werkzeug": "wrench tool", "werkzeuge": "toolbox",
    "schraubenschlüssel": "wrench", "hammer": "hammer", "pinsel": "paint brush", "farbe": "palette",
    "malen": "paint brush", "zeichnen": "pencil pen", "stift": "pencil pen", "schere": "scissors",
    "suche": "magnifying glass", "suchen": "magnifying glass", "lupe": "magnifying glass",
    "sicherheit": "shield lock", "schloss": "lock", "schlüssel": "key", "passwort": "password key",
    "schutz": "shield", "virus": "bug virus", "fehler": "bug warning",
    "netzwerk": "network", "internet": "globe", "web": "globe browser", "browser": "browser globe",
    "wlan": "wifi", "bluetooth": "bluetooth", "cloud": "cloud", "download": "download",
    "upload": "upload", "herunterladen": "download", "hochladen": "upload", "teilen": "share",
    "drucker": "printer", "scanner": "scan", "monitor": "monitor", "bildschirm": "monitor",
    "computer": "desktop computer", "laptop": "laptop", "tastatur": "keyboard", "maus": "mouse",
    "festplatte": "hard drive", "speicher": "hard drives database", "datenbank": "database",
    "server": "hard drives", "usb": "usb", "chip": "cpu", "prozessor": "cpu", "akku": "battery",
    "batterie": "battery", "strom": "plug lightning", "terminal": "terminal", "code": "code",
    "programmieren": "code brackets", "entwicklung": "code", "konsole": "terminal",
    "geld": "money currency", "bank": "bank", "euro": "currency eur", "kasse": "cash register",
    "einkaufen": "shopping cart", "warenkorb": "shopping cart", "shop": "storefront",
    "tasche": "bag", "geschenk": "gift", "karte": "map", "navigation": "navigation compass",
    "ort": "map pin", "standort": "map pin", "auto": "car", "fahrrad": "bicycle",
    "motorrad": "motorcycle", "bus": "bus", "zug": "train", "flugzeug": "airplane", "schiff": "boat",
    "reise": "airplane suitcase", "koffer": "suitcase", "rakete": "rocket",
    "person": "user", "benutzer": "user", "nutzer": "user", "kontakte": "address book",
    "gruppe": "users", "familie": "users", "kind": "baby", "herz": "heart", "stern": "star",
    "favorit": "star", "lesezeichen": "bookmark", "flagge": "flag", "glocke": "bell",
    "benachrichtigung": "bell", "info": "info", "hilfe": "question", "frage": "question",
    "warnung": "warning", "achtung": "warning", "häkchen": "check", "fertig": "check",
    "liste": "list", "aufgaben": "list checks", "todo": "list checks", "plan": "kanban",
    "diagramm": "chart", "statistik": "chart bar", "tabelle": "table", "präsentation": "presentation",
    "rechner": "calculator", "taschenrechner": "calculator", "mathe": "math",
    "übersetzen": "translate", "sprache": "translate", "schrift": "text aa",
    "lernen": "graduation cap student", "schule": "student", "wissenschaft": "flask atom",
    "medizin": "first aid heartbeat", "gesundheit": "heartbeat", "sport": "barbell",
    "essen": "fork knife", "kochen": "cooking pot", "rezept": "cooking pot", "kaffee": "coffee",
    "trinken": "beer wine coffee", "pizza": "pizza", "natur": "leaf tree", "pflanze": "plant",
    "baum": "tree", "blume": "flower", "tier": "paw print", "hund": "dog", "katze": "cat",
    "vogel": "bird", "fisch": "fish", "feuer": "fire flame", "wasser": "drop",
    "papierkorb": "trash", "müll": "trash", "löschen": "trash", "archiv": "archive",
    "paket": "package", "box": "package", "zip": "file zip", "backup": "cloud arrow up",
    "sicherung": "cloud arrow up clock counter", "synchron": "arrows clockwise",
    "aktualisieren": "arrows clockwise", "update": "arrows clockwise", "system": "gear cpu",
    "app": "app window", "programm": "app window", "fenster": "app window", "dock": "dock",
    "kopie": "copy", "kopieren": "copy", "zwischenablage": "clipboard", "link": "link",
    "anhang": "paperclip", "bearbeiten": "pencil", "zauberstab": "magic wand", "ki": "sparkle robot",
    "roboter": "robot", "smart": "lightbulb", "idee": "lightbulb", "licht": "lightbulb",
    "lampe": "lamp lightbulb", "schalter": "toggle", "regler": "sliders", "steuerung": "sliders",
    "fernbedienung": "remote", "router": "router", "nas": "hard drives", "smart home": "house",
    "kamera überwachung": "security camera", "überwachung": "security camera",
    "podcast": "microphone podcast", "stream": "broadcast", "aufnahme": "record",
    "bildbearbeitung": "image paint brush", "vektor": "pen nib", "3d": "cube", "würfel 3d": "cube",
    "puzzle": "puzzle piece", "erweiterung": "puzzle piece", "rakete start": "rocket launch",
}


# ---------------------------------------------------------------- data
def data_file(name):
    for d in DATA_CANDIDATES:
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(name)


def load_glyphs():
    data = json.loads(data_file("glyphs.json").read_text())
    return data["icons"]


# ---------------------------------------------------------------- SVG path -> cairo
_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def parse_path(d):
    """Parse SVG path data into absolute cairo commands: ('M',x,y) ('L',x,y) ('C',...) ('Z',)."""
    toks = _TOKEN.findall(d)
    out, i, cmd = [], 0, None
    x = y = sx = sy = 0.0
    lcx = lcy = None          # last control point (for S/T)
    lqx = lqy = None

    def num():
        nonlocal i
        v = float(toks[i])
        i += 1
        return v

    def flag():
        # arc flags may be written without separators ("011")
        nonlocal i
        t = toks[i]
        if t in ("0", "1"):
            i += 1
            return int(t)
        # split "01.5" style tokens
        f = int(t[0])
        toks[i] = t[1:]
        return f

    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                out.append(("Z",))
                x, y = sx, sy
                lcx = lqx = None
                continue
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            nx, ny = num(), num()
            if rel:
                nx += x; ny += y
            out.append(("M", nx, ny)); x, y = sx, sy = nx, ny
            cmd = "l" if rel else "L"
            lcx = lqx = None
        elif c == "L":
            nx, ny = num(), num()
            if rel:
                nx += x; ny += y
            out.append(("L", nx, ny)); x, y = nx, ny
            lcx = lqx = None
        elif c == "H":
            nx = num() + (x if rel else 0)
            out.append(("L", nx, y)); x = nx
            lcx = lqx = None
        elif c == "V":
            ny = num() + (y if rel else 0)
            out.append(("L", x, ny)); y = ny
            lcx = lqx = None
        elif c == "C":
            a = [num() for _ in range(6)]
            if rel:
                a = [a[k] + (x if k % 2 == 0 else y) for k in range(6)]
            out.append(("C", *a)); lcx, lcy = a[2], a[3]; x, y = a[4], a[5]
            lqx = None
        elif c == "S":
            a = [num() for _ in range(4)]
            if rel:
                a = [a[k] + (x if k % 2 == 0 else y) for k in range(4)]
            c1x, c1y = (2 * x - lcx, 2 * y - lcy) if lcx is not None else (x, y)
            out.append(("C", c1x, c1y, *a)); lcx, lcy = a[0], a[1]; x, y = a[2], a[3]
            lqx = None
        elif c in "QT":
            if c == "Q":
                qx, qy, nx, ny = [num() for _ in range(4)]
                if rel:
                    qx += x; qy += y; nx += x; ny += y
            else:
                nx, ny = num(), num()
                if rel:
                    nx += x; ny += y
                qx, qy = (2 * x - lqx, 2 * y - lqy) if lqx is not None else (x, y)
            out.append(("C", x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y),
                        nx + 2 / 3 * (qx - nx), ny + 2 / 3 * (qy - ny), nx, ny))
            lqx, lqy = qx, qy; x, y = nx, ny
            lcx = None
        elif c == "A":
            rx, ry, rot = num(), num(), num()
            fa, fs = flag(), flag()
            nx, ny = num(), num()
            if rel:
                nx += x; ny += y
            out.extend(_arc(x, y, rx, ry, rot, fa, fs, nx, ny))
            x, y = nx, ny
            lcx = lqx = None
        else:
            i += 1
    return out


def _arc(x1, y1, rx, ry, phi, fa, fs, x2, y2):
    """SVG elliptical arc -> cubic béziers (endpoint parameterisation, SVG spec F.6)."""
    if rx == 0 or ry == 0 or (x1 == x2 and y1 == y2):
        return [("L", x2, y2)]
    rx, ry = abs(rx), abs(ry)
    p = math.radians(phi)
    cp, sp = math.cos(p), math.sin(p)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1p ** 2) / (rx ** 2) + (y1p ** 2) / (ry ** 2)
    if lam > 1:
        s = math.sqrt(lam); rx *= s; ry *= s
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if fa == fs:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a
    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not fs and dt > 0:
        dt -= 2 * math.pi
    elif fs and dt < 0:
        dt += 2 * math.pi
    n = max(1, int(math.ceil(abs(dt) / (math.pi / 2) - 1e-9)))
    d = dt / n
    k = 4 / 3 * math.tan(d / 4)
    res = []
    for j in range(n):
        a1 = t1 + j * d
        a2 = a1 + d
        c1, s1, c2, s2 = math.cos(a1), math.sin(a1), math.cos(a2), math.sin(a2)
        pts = [(c1 - k * s1, s1 + k * c1), (c2 + k * s2, s2 - k * c2), (c2, s2)]
        seg = []
        for ex, ey in pts:
            ex, ey = ex * rx, ey * ry
            seg += [cp * ex - sp * ey + cx, sp * ex + cp * ey + cy]
        res.append(("C", *seg))
    return res


def draw_ops(ctx, ops):
    for op in ops:
        if op[0] == "M":
            ctx.move_to(op[1], op[2])
        elif op[0] == "L":
            ctx.line_to(op[1], op[2])
        elif op[0] == "C":
            ctx.curve_to(*op[1:])
        else:
            ctx.close_path()


SQUIRCLE_OPS = parse_path(SQUIRCLE)


# ---------------------------------------------------------------- colours
def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[k:k + 2], 16) / 255 for k in (0, 2, 4))


def mix(c, o, t):
    return tuple(a + (b - a) * t for a, b in zip(c, o))


# ---------------------------------------------------------------- template image -> white mask
def image_to_mask(path, mode="auto", threshold=0.5, invert=False, max_px=360):
    """Returns (cairo.ImageSurface ARGB32 white-with-alpha, width, height) cropped to content."""
    if str(path).lower().endswith((".svg", ".svgz")):
        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), max_px, max_px, True)   # vector: render sharp
    else:
        pb = GdkPixbuf.Pixbuf.new_from_file(str(path))
    w, h = pb.get_width(), pb.get_height()
    sc = min(1.0, max_px / max(w, h)) if max(w, h) > max_px else max_px / max(w, h)
    sc = min(sc, 8)
    nw, nh = max(1, round(w * sc)), max(1, round(h * sc))
    pb = pb.scale_simple(nw, nh, GdkPixbuf.InterpType.HYPER)
    if not pb.get_has_alpha():
        pb = pb.add_alpha(False, 0, 0, 0)
    w, h, rs = pb.get_width(), pb.get_height(), pb.get_rowstride()
    px = pb.get_pixels()

    def at(x, y):
        o = y * rs + x * 4
        return px[o], px[o + 1], px[o + 2], px[o + 3]

    # how much real transparency is there?
    transp = 0
    step = max(1, (w * h) // 4000)
    border = []
    for k in range(0, w * h, step):
        x, y = k % w, k // w
        r, g, b, a = at(x, y)
        if a < 200:
            transp += 1
    for x in range(0, w, max(1, w // 60)):
        border += [at(x, 0), at(x, h - 1)]
    for y in range(0, h, max(1, h // 60)):
        border += [at(0, y), at(w - 1, y)]
    has_alpha = transp > (w * h // step) * 0.03
    opaque_border = [p for p in border if p[3] > 200]
    if opaque_border:
        bg = tuple(sum(p[c] for p in opaque_border) / len(opaque_border) for c in range(3))
    else:
        bg = (255, 255, 255)
    if mode == "auto":
        mode = "shape" if has_alpha else "contrast"
    if mode == "shape" and invert:
        # inverting a plain silhouette would leave nothing – show the light inner details instead
        mode, invert = "light", False

    lo, hi = threshold - 0.08, threshold + 0.08
    mask = bytearray(w * h)
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        row = y * rs
        for x in range(w):
            o = row + x * 4
            r, g, b, a = px[o], px[o + 1], px[o + 2], px[o + 3]
            af = a / 255
            if mode == "shape":
                v = af
            elif mode == "dark":
                lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
                v = af * (1 - lum)
            elif mode == "light":
                lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
                v = af * lum
            else:   # contrast to the background colour
                v = af * max(abs(r - bg[0]), abs(g - bg[1]), abs(b - bg[2])) / 255
            if mode == "shape":
                t = v
            else:
                t = 0.0 if v <= lo else 1.0 if v >= hi else (v - lo) / (hi - lo)
            if invert:
                t = af - t if mode != "contrast" else 1 - t
                t = max(0.0, t)
            m = int(t * 255 + 0.5)
            mask[y * w + x] = m
            if m > 24:
                if x < minx: minx = x
                if x > maxx: maxx = x
                if y < miny: miny = y
                if y > maxy: maxy = y
    if maxx < 0:
        return None
    cw, ch = maxx - minx + 1, maxy - miny + 1
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, cw, ch)
    stride = surf.get_stride()
    buf = surf.get_data()
    for y in range(ch):
        src = (miny + y) * w + minx
        dst = y * stride
        for x in range(cw):
            m = mask[src + x]
            buf[dst + x * 4:dst + x * 4 + 4] = bytes((m, m, m, m))   # premultiplied white
    surf.mark_dirty()
    return surf


# ---------------------------------------------------------------- icon rendering
def render_icon(size, color, glyph=None, mask=None, glyph_size=34, offset=(0, 0)):
    """Monterra settings style: squircle (gradient, rim, soft shadow) + white glyph."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surf)
    ctx.scale(size / 64, size / 64)
    base = hex2rgb(color)
    top, bottom, rim = mix(base, (1, 1, 1), 0.18), mix(base, (0, 0, 0), 0.06), mix(base, (0, 0, 0), 0.18)
    # soft drop shadow (stacked, slightly growing silhouettes)
    for k, a in ((1.5, 0.03), (1.0, 0.045), (0.55, 0.06), (0.2, 0.08)):
        ctx.save()
        ctx.translate(32, 33)
        ctx.scale(1 + k / 27, 1 + k / 27)
        ctx.translate(-32, -32)
        draw_ops(ctx, SQUIRCLE_OPS)
        ctx.set_source_rgba(0, 0, 0, a)
        ctx.fill()
        ctx.restore()
    grad = cairo.LinearGradient(0, 5, 0, 59)
    grad.add_color_stop_rgb(0, *top)
    grad.add_color_stop_rgb(1, *bottom)
    draw_ops(ctx, SQUIRCLE_OPS)
    ctx.set_source(grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(*rim, 0.35)
    ctx.set_line_width(0.6)
    ctx.stroke()
    # glyph
    gs = glyph_size
    ox, oy = (64 - gs) / 2 + offset[0], (64 - gs) / 2 + offset[1]
    ctx.save()
    draw_ops(ctx, SQUIRCLE_OPS)
    ctx.clip()
    if glyph is not None:
        ctx.translate(ox, oy)
        ctx.scale(gs / 256, gs / 256)
        if "_ops" not in glyph:
            glyph["_ops"] = [parse_path(d) for d in glyph["d"]]
        for ops in glyph["_ops"]:
            draw_ops(ctx, ops)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
    elif mask is not None:
        mw, mh = mask.get_width(), mask.get_height()
        f = gs / max(mw, mh)
        ctx.translate(32 - mw * f / 2 + offset[0], 32 - mh * f / 2 + offset[1])
        ctx.scale(f, f)
        ctx.set_source_surface(mask, 0, 0)
        ctx.get_source().set_filter(cairo.FILTER_BEST)
        ctx.paint()
    ctx.restore()
    surf.flush()
    return surf


def icon_svg(color, glyph, glyph_size=34, offset=(0, 0)):
    base = hex2rgb(color)
    h = lambda c: "#%02X%02X%02X" % tuple(round(v * 255) for v in c)  # noqa: E731
    top, bottom, rim = h(mix(base, (1, 1, 1), 0.18)), h(mix(base, (0, 0, 0), 0.06)), h(mix(base, (0, 0, 0), 0.18))
    s = glyph_size / 256
    ox, oy = (64 - glyph_size) / 2 + offset[0], (64 - glyph_size) / 2 + offset[1]
    paths = "".join(f'<path d="{d}"/>' for d in glyph["d"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 64 64">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>
  <filter id="sh" x="-20%" y="-20%" width="140%" height="150%">
    <feDropShadow dx="0" dy="1" stdDeviation="1.1" flood-color="#000" flood-opacity="0.28"/></filter>
</defs>
<path filter="url(#sh)" d="{SQUIRCLE}" fill="url(#g)" stroke="{rim}" stroke-opacity=".35" stroke-width=".6"/>
<g transform="translate({ox:.3f} {oy:.3f}) scale({s:.5f})" fill="#FFFFFF">{paths}</g>
</svg>
'''


# ---------------------------------------------------------------- search
def search(glyphs, query, limit=72):
    q = query.strip().lower()
    if not q:
        return []
    words = []
    for part in re.split(r"[,;]+", q):
        part = part.strip()
        if not part:
            continue
        if part in DE:
            words += DE[part].split()
        elif part in ES:
            words += ES[part].split()
        for w in part.split():
            words += DE.get(w, ES.get(w, w)).split()
    words = list(dict.fromkeys(words))
    scored = []
    for g in glyphs:
        name = g["n"]
        parts = name.split("-")
        score = 0
        for w in words:
            if w == name:
                score += 12
            elif w in parts:
                score += 8 if parts[0] == w else 5
            elif any(p.startswith(w) for p in parts) and len(w) >= 3:
                score += 3
            if w in g["t"]:
                score += 4
            elif len(w) >= 5 and any(t.startswith(w) for t in g["t"]):
                score += 1
        if score:
            scored.append((-score, len(name), name, g))
    scored.sort()
    return [s[3] for s in scored[:limit]]


# ---------------------------------------------------------------- installed programs
def installed_apps():
    dirs = [HOME / ".local/share/applications", HOME / ".local/share/flatpak/exports/share/applications",
            Path("/var/lib/flatpak/exports/share/applications"), Path("/var/lib/snapd/desktop/applications"),
            Path("/usr/local/share/applications"), Path("/usr/share/applications")]
    seen, apps = set(), []
    for d in dirs:
        try:
            files = sorted(d.glob("*.desktop"))
        except OSError:
            continue
        for f in files:
            if f.name in seen:
                continue
            seen.add(f.name)
            cp = configparser.RawConfigParser(strict=False, interpolation=None)
            cp.optionxform = str
            try:
                cp.read(f, encoding="utf-8")
                e = cp["Desktop Entry"]
            except Exception:
                continue
            if e.get("Type", "Application") != "Application" or e.get("NoDisplay", "false").lower() == "true":
                continue
            name = e.get("Name[de]", e.get("Name", f.stem))
            apps.append((name, e.get("Icon", "").strip(), f))
    apps.sort(key=lambda a: a[0].lower())
    return apps


ENTRIES = LOCAL / "eigene-eintraege.txt"   # menu entries that got an own icon name: path<TAB>original icon


def _custom_names():
    return set(CUSTOM_LIST.read_text().split()) if CUSTOM_LIST.exists() else set()


def _ensure_local():
    (LOCAL / "apps" / "256").mkdir(parents=True, exist_ok=True)
    idx = LOCAL / "index.theme"
    if not idx.exists():
        idx.write_text("[Icon Theme]\nName=Monterra-Local\nComment=Programmsymbole in Monterra-Form\n"
                       "Hidden=true\nDirectories=apps/256\n\n[apps/256]\nContext=Applications\nSize=256\n"
                       "MinSize=16\nMaxSize=512\nType=Scalable\n")


def _remember(name):
    names = _custom_names()
    names.add(name)
    CUSTOM_LIST.write_text("\n".join(sorted(names)) + "\n")


def _activate():
    """Monterra prefers Monterra-Local; refresh icon caches."""
    mi = MONTERRA / "index.theme"
    if mi.exists():
        t = mi.read_text()
        m = re.search(r"^Inherits=(.*)$", t, re.M)
        parts = [p for p in (m.group(1).split(",") if m else []) if p and p != "Monterra-Local"]
        t = re.sub(r"^Inherits=.*$", "Inherits=" + ",".join(["Monterra-Local"] + parts), t, flags=re.M)
        mi.write_text(t)
    for d in (LOCAL, MONTERRA):
        if d.exists():
            subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(d)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _own_name(desktop_name):
    return "monterra-eigen-" + re.sub(r"[^a-z0-9]+", "-", Path(desktop_name).stem.lower()).strip("-")


def _point_entry(desktop_path, target_name, original_icon):
    """Give a program whose icon is a file path its own icon name (local copy of its menu entry)."""
    local = HOME / ".local/share/applications" / desktop_path.name
    local.parent.mkdir(parents=True, exist_ok=True)
    if local != desktop_path:
        shutil.copy2(desktop_path, local)
    text = local.read_text(encoding="utf-8")
    text = re.sub(r"^Icon=.*$", f"Icon={target_name}", text, flags=re.M) if re.search(r"^Icon=", text, re.M) \
        else text.replace("[Desktop Entry]", f"[Desktop Entry]\nIcon={target_name}", 1)
    local.write_text(text, encoding="utf-8")
    known = ENTRIES.read_text() if ENTRIES.exists() else ""
    if str(local) + "\t" not in known:
        with open(ENTRIES, "a") as f:
            f.write(f"{local}\t{original_icon}\n")
    subprocess.run(["update-desktop-database", str(local.parent)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _shadowed(name):
    """True if the Monterra icon theme itself has an icon of this name. Monterra is searched
    before Monterra-Local, so a self-made icon with the same name would never be shown."""
    if not name or not MONTERRA.exists():
        return False
    try:
        return any(MONTERRA.rglob(f"{name}.svg")) or any(MONTERRA.rglob(f"{name}.png"))
    except OSError:
        return False


def repair_shadowed():
    """Earlier versions saved icons under names Monterra already uses (e.g. the terminal or
    the system settings) – those never showed up. Give the programs their own icon names."""
    if not CUSTOM_LIST.exists():
        return []
    fixed = []
    apps = None
    for n in sorted(_custom_names()):
        if n.startswith("monterra-eigen-") or not _shadowed(n):
            continue
        png = LOCAL / "apps" / "256" / f"{n}.png"
        if png.exists():
            apps = apps if apps is not None else installed_apps()
            for name, icon, desk in apps:
                if icon == n:
                    own = _own_name(desk.name)
                    shutil.copy2(png, LOCAL / "apps" / "256" / f"{own}.png")
                    _point_entry(desk, own, icon)
                    _remember(own)
                    fixed.append(name)
            png.unlink()
        names = _custom_names()
        names.discard(n)
        CUSTOM_LIST.write_text("\n".join(sorted(names)) + "\n")
    if fixed:
        _activate()
    return fixed


def assign_to_app(surface512, icon_name, desktop_path):
    """Save the icon into ~/.icons/Monterra-Local and make the program use it."""
    _ensure_local()
    target_name = icon_name
    # own name if the icon is a file path – or if Monterra already has an icon of that name
    if not icon_name or icon_name.startswith("/") or _shadowed(icon_name):
        target_name = _own_name(desktop_path.name)
        _point_entry(desktop_path, target_name, icon_name)
    small = cairo.ImageSurface(cairo.FORMAT_ARGB32, 256, 256)
    c = cairo.Context(small)
    c.scale(0.5, 0.5)
    c.set_source_surface(surface512, 0, 0)
    c.get_source().set_filter(cairo.FILTER_BEST)
    c.paint()
    small.write_to_png(str(LOCAL / "apps" / "256" / f"{target_name}.png"))
    _remember(target_name)            # programmsymbole.py and the Automatik never overwrite it
    _activate()
    return target_name


# ---------------------------------------------------------------- transfer to other computers
EXPORT_SUFFIX = ".monterra-symbole.zip"
PENDING = HOME / ".local/share/monterra/ausstehend"   # imports waiting for programs not installed yet


def export_icons(zip_path):
    """Pack all self-made program icons (+ which program they belong to) into one file."""
    import zipfile
    names = sorted(_custom_names())
    entries = {}
    if ENTRIES.exists():
        for line in ENTRIES.read_text().splitlines():
            if "\t" in line:
                path = line.split("\t", 1)[0]
                entries[_own_name(Path(path).name)] = Path(path).name
    manifest, n = [], 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            png = LOCAL / "apps" / "256" / f"{name}.png"
            if not png.exists():
                continue
            z.write(png, f"symbole/{name}.png")
            manifest.append({"symbol": name, "programm": entries.get(name)})
            n += 1
        z.writestr("monterra-symbole.json", json.dumps({"version": 1, "symbole": manifest}, indent=1))
    return n


def import_icons(zip_path):
    """Install icons from an export file. Returns (installed, programs not found on this computer)."""
    import zipfile
    _ensure_local()
    out = LOCAL / "apps" / "256"
    installed, missing = 0, []
    installed_by_name = {p.name: p for _n, _i, p in installed_apps()}
    with zipfile.ZipFile(zip_path) as z:
        meta = json.loads(z.read("monterra-symbole.json"))
        for item in meta.get("symbole", []):
            name = item["symbol"]
            if not re.fullmatch(r"[A-Za-z0-9._+-]+", name):
                continue                      # never write outside the icon folder
            (out / f"{name}.png").write_bytes(z.read(f"symbole/{name}.png"))
            _remember(name)
            installed += 1
            prog = item.get("programm")
            if prog:                          # program that uses a file path as its icon
                desk = installed_by_name.get(prog)
                if desk is None:
                    missing.append(prog)
                    continue
                cp = configparser.RawConfigParser(strict=False, interpolation=None)
                cp.optionxform = str
                cp.read(desk, encoding="utf-8")
                cur = cp["Desktop Entry"].get("Icon", "") if cp.has_section("Desktop Entry") else ""
                if cur != name:
                    _point_entry(desk, name, cur)
    _activate()
    repair_shadowed()                         # older export files may contain names Monterra already uses
    # remember files with programs that are missing here – the Automatik finishes them after installation
    keep = PENDING / Path(zip_path).name
    if missing:
        PENDING.mkdir(parents=True, exist_ok=True)
        if Path(zip_path).resolve() != keep.resolve():
            shutil.copy2(zip_path, keep)
    elif keep.exists() and Path(zip_path).resolve() == keep.resolve():
        keep.unlink()
    return installed, missing


# ---------------------------------------------------------------- user interface
class Werkstatt(Gtk.ApplicationWindow):
    def __init__(self, app, template=None):
        super().__init__(application=app, title=_("Symbolwerkstatt"))
        self.set_default_size(980, 640)
        self.set_icon_name("monterra-symbolwerkstatt")
        self.glyphs = load_glyphs()
        self.color = COLORS[0][1]
        self.glyph = None
        self.mask = None
        self.template = None
        self.glyph_size = 34.0
        self._busy = 0

        hb = Gtk.HeaderBar(show_close_button=True, title=_("Symbolwerkstatt"),
                           subtitle=_("Programmsymbole im Monterra-Stil"))
        self.set_titlebar(hb)
        b_save = Gtk.MenuButton(label=_("Datei"))
        menu = Gio.Menu()
        menu.append(_("Als PNG speichern (512 × 512) …"), "win.save-png")
        menu.append(_("Als SVG speichern (nur Stichwort-Symbole) …"), "win.save-svg")
        sec = Gio.Menu()
        sec.append(_("Eigene Programmsymbole exportieren …"), "win.export")
        sec.append(_("Eigene Programmsymbole importieren …"), "win.import")
        menu.append_section(None, sec)
        b_save.set_menu_model(menu)
        b_assign = Gtk.Button(label=_("Für Programm verwenden …"))
        b_assign.get_style_context().add_class("suggested-action")
        b_assign.connect("clicked", self.on_assign)
        hb.pack_end(b_assign)
        hb.pack_end(b_save)
        for name, cb in (("save-png", self.on_save_png), ("save-svg", self.on_save_svg),
                         ("export", self.on_export), ("import", self.on_import)):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)
        self.save_svg_action = self.lookup_action("save-svg")

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(root)

        # ---- left: preview
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=20)
        self.preview = Gtk.DrawingArea()
        self.preview.set_size_request(300, 300)
        self.preview.connect("draw", self.draw_preview)
        left.pack_start(self.preview, True, True, 0)
        self.strip = Gtk.DrawingArea()
        self.strip.set_size_request(340, 80)
        self.strip.connect("draw", self.draw_strip)
        left.pack_start(self.strip, False, False, 0)
        self.status = Gtk.Label(xalign=0, wrap=True)
        self.status.get_style_context().add_class("dim-label")
        left.pack_start(self.status, False, False, 0)
        root.pack_start(left, True, True, 0)
        root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)

        # ---- right: controls
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=18)
        right.set_size_request(400, -1)
        root.pack_start(right, False, False, 0)

        stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        sw = Gtk.StackSwitcher(stack=stack, halign=Gtk.Align.CENTER)
        right.pack_start(sw, False, False, 0)
        right.pack_start(stack, True, True, 0)
        self.stack = stack

        # tab 1: keywords
        kw = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.search = Gtk.SearchEntry(placeholder_text=_("Stichwörter, z. B. „Kamera“ oder „Musik, Noten“"))
        self.search.connect("search-changed", self.on_search)
        kw.pack_start(self.search, False, False, 0)
        self.results = Gtk.FlowBox(max_children_per_line=8, min_children_per_line=6, homogeneous=True,
                                   selection_mode=Gtk.SelectionMode.SINGLE, row_spacing=4, column_spacing=4)
        self.results.connect("child-activated", self.on_glyph_chosen)
        self.results.set_valign(Gtk.Align.START)
        scr = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scr.add(self.results)
        kw.pack_start(scr, True, True, 0)
        self.hint = Gtk.Label(label=_("Deutsche oder englische Begriffe – mehrere mit Komma trennen."),
                              xalign=0, wrap=True)
        self.hint.get_style_context().add_class("dim-label")
        kw.pack_start(self.hint, False, False, 0)
        stack.add_titled(kw, "kw", _("Aus Stichwort"))

        # tab 2: image template
        im = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        fb = Gtk.FileChooserButton(title=_("Bildvorlage wählen"), action=Gtk.FileChooserAction.OPEN)
        flt = Gtk.FileFilter()
        flt.set_name(_("Bilder"))
        flt.add_pixbuf_formats()
        fb.add_filter(flt)
        fb.connect("file-set", self.on_file)
        self.filebtn = fb
        im.pack_start(self._row(_("Vorlage"), fb), False, False, 0)
        self.mode = Gtk.ComboBoxText()
        for k, t in (("auto", _("Automatisch")), ("shape", _("Umriss (transparente Bilder)")),
                     ("contrast", _("Abhebung vom Hintergrund")), ("dark", _("Dunkle Bereiche")),
                     ("light", _("Helle Bereiche"))):
            self.mode.append(k, t)
        self.mode.set_active_id("auto")
        self.mode.connect("changed", self.on_template_option)
        im.pack_start(self._row(_("Erkennung"), self.mode), False, False, 0)
        self.thr = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.05, 0.95, 0.01)
        self.thr.set_value(0.45)
        self.thr.set_draw_value(False)
        self.thr.connect("value-changed", self.on_template_option)
        im.pack_start(self._row(_("Schwelle"), self.thr), False, False, 0)
        self.inv = Gtk.CheckButton(label=_("Umkehren (Flächen tauschen)"))
        self.inv.connect("toggled", self.on_template_option)
        im.pack_start(self.inv, False, False, 0)
        self.src_preview = Gtk.Image()
        im.pack_start(self.src_preview, False, False, 6)
        tip = Gtk.Label(label=_("Am besten eignen sich einfache Logos oder Piktogramme mit klarer Form. "
                                "Aus dem Bild wird automatisch eine weiße Silhouette."), xalign=0, wrap=True)
        tip.get_style_context().add_class("dim-label")
        im.pack_start(tip, False, False, 0)
        stack.add_titled(im, "img", _("Aus Bild"))

        # colour
        right.pack_start(Gtk.Separator(), False, False, 0)
        cl = Gtk.Label(xalign=0)
        cl.set_markup(_("<b>Hintergrundfarbe</b>"))
        right.pack_start(cl, False, False, 0)
        colors = Gtk.FlowBox(max_children_per_line=14, selection_mode=Gtk.SelectionMode.NONE,
                             column_spacing=4, row_spacing=4)
        for name, col in COLORS:
            b = Gtk.Button(tooltip_text=_(name), relief=Gtk.ReliefStyle.NONE)
            da = Gtk.DrawingArea()
            da.set_size_request(22, 22)
            da.connect("draw", self._draw_swatch, col)
            b.add(da)
            b.connect("clicked", lambda _b, c=col: self.set_color(c))
            colors.add(b)
        self.colorbtn = Gtk.ColorButton(title=_("Eigene Farbe"), tooltip_text=_("Eigene Farbe wählen"))
        self.colorbtn.connect("color-set", self.on_custom_color)
        colors.add(self.colorbtn)
        right.pack_start(colors, False, False, 0)

        # size
        self.size_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 22, 46, 1)
        self.size_scale.set_value(self.glyph_size)
        self.size_scale.set_draw_value(False)
        self.size_scale.add_mark(34, Gtk.PositionType.BOTTOM, None)
        self.size_scale.connect("value-changed", self.on_size)
        right.pack_start(self._row(_("Symbolgröße"), self.size_scale), False, False, 0)

        self.search.set_text(_("Stern"))
        self.on_search(self.search)
        self.glyph = next(g for g in self.glyphs if g["n"] == "star")
        self.refresh()
        self.show_all()
        if template and template.endswith(".zip"):
            GLib.idle_add(lambda: self.on_import(path=template) and False)
        elif template:
            self.filebtn.set_filename(template)
            self.stack.set_visible_child_name("img")
            self.on_file(self.filebtn)

    # -------- helpers
    def _row(self, label, widget):
        box = Gtk.Box(spacing=10)
        lb = Gtk.Label(label=label, xalign=0)
        lb.set_size_request(92, -1)
        box.pack_start(lb, False, False, 0)
        box.pack_start(widget, True, True, 0)
        return box

    def _draw_swatch(self, w, cr, col):
        a = w.get_allocated_width()
        cr.arc(a / 2, a / 2, a / 2 - 1, 0, 2 * math.pi)
        cr.set_source_rgb(*hex2rgb(col))
        cr.fill_preserve()
        cr.set_source_rgba(0, 0, 0, 0.15)
        cr.set_line_width(1)
        cr.stroke()
        if col.upper() == self.color.upper():
            cr.arc(a / 2, a / 2, 4, 0, 2 * math.pi)
            cr.set_source_rgb(1, 1, 1)
            cr.fill()

    def current_surface(self, size=512):
        return render_icon(size, self.color, glyph=self.glyph, mask=self.mask if self.glyph is None else None,
                           glyph_size=self.glyph_size)

    def refresh(self):
        self.preview.queue_draw()
        self.strip.queue_draw()
        self.save_svg_action.set_enabled(self.glyph is not None)
        if self.glyph is not None:
            self.status.set_text(_("Symbol „{name}“ · Farbe {color}", name=self.glyph['n'], color=self.color.upper()))
        elif self.mask is not None:
            self.status.set_text(_("Vorlage {name} · Farbe {color}", name=Path(self.template).name,
                                  color=self.color.upper()))
        else:
            self.status.set_text(_("Wähle ein Symbol per Stichwort oder eine Bildvorlage."))

    # -------- drawing
    def draw_preview(self, w, cr):
        aw, ah = w.get_allocated_width(), w.get_allocated_height()
        s = int(min(aw, ah, 512))
        surf = self.current_surface(512)
        cr.translate((aw - s) / 2, (ah - s) / 2)
        cr.scale(s / 512, s / 512)
        cr.set_source_surface(surf, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_BEST)
        cr.paint()

    def draw_strip(self, w, cr):
        aw, ah = w.get_allocated_width(), w.get_allocated_height()
        # light and dark half like the Monterra themes
        cr.rectangle(0, 0, aw / 2, ah)
        cr.set_source_rgb(0.94, 0.94, 0.94)
        cr.fill()
        cr.rectangle(aw / 2, 0, aw / 2, ah)
        cr.set_source_rgb(0.16, 0.16, 0.16)
        cr.fill()
        sizes = [s for s in (64, 48, 32, 24, 16) if True]
        while sum(sizes) + 10 * (len(sizes) + 1) > aw / 2 and len(sizes) > 2:
            sizes.pop(0)
        for half in (0, 1):
            x = half * aw / 2 + (aw / 2 - sum(sizes) - 10 * (len(sizes) - 1)) / 2
            for s in sizes:
                surf = self.current_surface(s * 2)
                cr.save()
                cr.translate(x, (ah - s) / 2)
                cr.scale(0.5, 0.5)
                cr.set_source_surface(surf, 0, 0)
                cr.get_source().set_filter(cairo.FILTER_BEST)
                cr.paint()
                cr.restore()
                x += s + 10

    # -------- events
    def set_color(self, col):
        self.color = col
        self.refresh()
        for child in self.get_children():
            child.queue_draw()
        self.queue_draw()
        self._update_result_icons()

    def on_custom_color(self, btn):
        rgba = btn.get_rgba()
        self.set_color("#%02X%02X%02X" % (round(rgba.red * 255), round(rgba.green * 255), round(rgba.blue * 255)))

    def on_size(self, sc):
        self.glyph_size = sc.get_value()
        self.refresh()

    def on_search(self, entry):
        for c in self.results.get_children():
            self.results.remove(c)
        found = search(self.glyphs, entry.get_text())
        for g in found:
            da = Gtk.DrawingArea(tooltip_text=g["n"])
            da.set_size_request(40, 40)
            da.connect("draw", self._draw_result, g)
            self.results.add(da)
        self.results.show_all()
        if entry.get_text().strip() and not found:
            self.hint.set_text(_("Nichts gefunden – versuche ein anderes oder englisches Wort."))
        else:
            self.hint.set_text(_("{n} Treffer – Symbol anklicken. Deutsche oder englische Begriffe, "
                                 "mehrere mit Komma trennen.", n=len(found)) if found else
                               _("Deutsche oder englische Begriffe – mehrere mit Komma trennen."))

    def _draw_result(self, w, cr, g):
        surf = render_icon(80, self.color, glyph=g, glyph_size=34)
        cr.scale(0.5, 0.5)
        cr.set_source_surface(surf, 0, 0)
        cr.paint()

    def _update_result_icons(self):
        for c in self.results.get_children():
            c.queue_draw()

    def on_glyph_chosen(self, box, child):
        da = child.get_child()
        name = da.get_tooltip_text()
        self.glyph = next(g for g in self.glyphs if g["n"] == name)
        self.refresh()

    def on_file(self, fb):
        self.template = fb.get_filename()
        if not self.template:
            return
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.template, 96, 96, True)
            self.src_preview.set_from_pixbuf(pb)
        except GLib.Error:
            pass
        self.on_template_option()

    def on_template_option(self, *_a):
        # short delay so dragging the slider stays smooth
        if getattr(self, "_mask_timer", 0):
            GLib.source_remove(self._mask_timer)
        self._mask_timer = GLib.timeout_add(120, self._update_mask)

    def _update_mask(self):
        self._mask_timer = 0
        if not self.template:
            return False
        try:
            self.mask = image_to_mask(self.template, self.mode.get_active_id(), self.thr.get_value(),
                                      self.inv.get_active())
        except GLib.Error as e:
            self.message(_("Die Bilddatei konnte nicht gelesen werden."), str(e))
            return False
        self.glyph = None
        self.refresh()
        if self.mask is None:
            self.status.set_text(_("In der Vorlage wurde keine Form erkannt – Schwelle oder Erkennung ändern."))
        return False

    # -------- output
    def ask_save(self, title, name, pattern):
        dlg = Gtk.FileChooserDialog(title=title, transient_for=self, action=Gtk.FileChooserAction.SAVE)
        dlg.add_buttons(_("_Abbrechen"), Gtk.ResponseType.CANCEL, _("_Speichern"), Gtk.ResponseType.ACCEPT)
        dlg.set_default_response(Gtk.ResponseType.ACCEPT)
        dlg.set_do_overwrite_confirmation(True)
        pics = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
        if pics:
            dlg.set_current_folder(pics)
        dlg.set_current_name(name)
        f = Gtk.FileFilter()
        f.add_pattern(pattern)
        dlg.set_filter(f)
        r = dlg.run()
        fn = dlg.get_filename() if r == Gtk.ResponseType.ACCEPT else None
        dlg.destroy()
        return fn

    def _basename(self):
        if self.glyph is not None:
            return "symbol-" + self.glyph["n"]
        if self.template:
            return "symbol-" + Path(self.template).stem
        return "symbol"

    def on_save_png(self, *_a):
        if self.glyph is None and self.mask is None:
            return
        fn = self.ask_save(_("Symbol als PNG speichern"), self._basename() + ".png", "*.png")
        if fn:
            if not fn.lower().endswith(".png"):
                fn += ".png"
            self.current_surface(512).write_to_png(fn)
            self.status.set_text(_("Gespeichert: {fn}", fn=fn))

    def on_save_svg(self, *_a):
        if self.glyph is None:
            return
        fn = self.ask_save(_("Symbol als SVG speichern"), self._basename() + ".svg", "*.svg")
        if fn:
            if not fn.lower().endswith(".svg"):
                fn += ".svg"
            Path(fn).write_text(icon_svg(self.color, self.glyph, self.glyph_size))
            self.status.set_text(_("Gespeichert: {fn}", fn=fn))

    def on_export(self, *_a):
        if not _custom_names():
            self.message(_("Es gibt noch keine eigenen Programmsymbole."),
                         _("Weise zuerst mit „Für Programm verwenden …“ einem Programm ein Symbol zu."))
            return
        fn = self.ask_save(_("Eigene Programmsymbole exportieren"), "meine" + EXPORT_SUFFIX, "*.zip")
        if not fn:
            return
        if not fn.endswith(".zip"):
            fn += EXPORT_SUFFIX
        n = export_icons(fn)
        self.message(_("{n} eigene Programmsymbole exportiert.", n=n),
                     _("Auf dem anderen Rechner: Datei in den Ordner „meine-symbole“ des Monterra-Pakets legen "
                       "(der Installer übernimmt sie dann automatisch) oder hier über „Importieren …“ laden."))

    def on_import(self, *_a, path=None):
        if path is None:
            dlg = Gtk.FileChooserDialog(title=_("Eigene Programmsymbole importieren"), transient_for=self,
                                        action=Gtk.FileChooserAction.OPEN)
            dlg.add_buttons(_("_Abbrechen"), Gtk.ResponseType.CANCEL, _("_Importieren"), Gtk.ResponseType.ACCEPT)
            f = Gtk.FileFilter()
            f.set_name(_("Monterra-Symbole (*.zip)"))
            f.add_pattern("*.zip")
            dlg.add_filter(f)
            r = dlg.run()
            path = dlg.get_filename() if r == Gtk.ResponseType.ACCEPT else None
            dlg.destroy()
            if not path:
                return
        try:
            n, missing = import_icons(path)
        except Exception as e:  # noqa: BLE001
            self.message(_("Die Datei konnte nicht importiert werden."), str(e), Gtk.MessageType.ERROR)
            return
        extra = ""
        if missing:
            extra = _("Diese Programme sind hier (noch) nicht installiert: {apps}. Ist die Monterra-Automatik "
                      "eingeschaltet, bekommen sie ihr Symbol nach der Installation von selbst – sonst danach einfach "
                      "noch einmal importieren.\n\n", apps=", ".join(missing))
        self.message(_("{n} Programmsymbole übernommen.", n=n),
                     extra + _("Im Menü erscheinen sie nach wenigen Sekunden, im Panel/Dock nach Alt+F2 → r."))

    def message(self, text, secondary=None, kind=Gtk.MessageType.INFO):
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=kind,
                              buttons=Gtk.ButtonsType.OK, text=text)
        if secondary:
            d.format_secondary_text(secondary)
        d.run()
        d.destroy()

    def on_assign(self, *_a):
        if self.glyph is None and self.mask is None:
            self.message(_("Bitte zuerst ein Symbol wählen oder eine Bildvorlage laden."))
            return
        dlg = Gtk.Dialog(title=_("Für Programm verwenden"), transient_for=self, modal=True)
        dlg.add_buttons(_("_Abbrechen"), Gtk.ResponseType.CANCEL, _("_Übernehmen"), Gtk.ResponseType.ACCEPT)
        dlg.set_default_response(Gtk.ResponseType.ACCEPT)
        dlg.set_default_size(460, 520)
        box = dlg.get_content_area()
        box.set_spacing(8)
        box.set_border_width(12)
        entry = Gtk.SearchEntry(placeholder_text=_("Programm suchen …"))
        box.pack_start(entry, False, False, 0)
        store = Gtk.ListStore(str, str, object, GdkPixbuf.Pixbuf)
        theme = Gtk.IconTheme.get_default()
        for name, icon, path in installed_apps():
            pb = None
            try:
                if icon.startswith("/") and os.path.isfile(icon):
                    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon, 32, 32, True)
                elif icon:
                    pb = theme.load_icon(icon, 32, Gtk.IconLookupFlags.FORCE_SIZE)
            except GLib.Error:
                pb = None
            store.append([name, icon, path, pb])
        flt = store.filter_new()
        flt.set_visible_func(lambda m, it, _d: entry.get_text().lower() in m[it][0].lower())
        entry.connect("search-changed", lambda *_: flt.refilter())
        tv = Gtk.TreeView(model=flt, headers_visible=False)
        col = Gtk.TreeViewColumn()
        rp = Gtk.CellRendererPixbuf()
        rt = Gtk.CellRendererText()
        col.pack_start(rp, False)
        col.pack_start(rt, True)
        col.add_attribute(rp, "pixbuf", 3)
        col.add_attribute(rt, "text", 0)
        tv.append_column(col)
        tv.connect("row-activated", lambda *_: dlg.response(Gtk.ResponseType.ACCEPT))
        sc = Gtk.ScrolledWindow()
        sc.add(tv)
        box.pack_start(sc, True, True, 0)
        note = Gtk.Label(label=_("Das Symbol ersetzt das bisherige Programmsymbol im Monterra-Theme. "
                                 "Rückgängig: python3 werkzeuge/programmsymbole.py restore"), wrap=True, xalign=0)
        note.get_style_context().add_class("dim-label")
        box.pack_start(note, False, False, 0)
        dlg.show_all()
        r = dlg.run()
        model, it = tv.get_selection().get_selected()
        chosen = model[it] if (r == Gtk.ResponseType.ACCEPT and it) else None
        app_name = chosen[0] if chosen else None
        icon, path = (chosen[1], chosen[2]) if chosen else (None, None)
        dlg.destroy()
        if not chosen:
            return
        try:
            name = assign_to_app(self.current_surface(512), icon, path)
        except Exception as e:  # noqa: BLE001
            self.message(_("Das Symbol konnte nicht übernommen werden."), str(e), Gtk.MessageType.ERROR)
            return
        self.message(_("„{app}“ hat jetzt das neue Symbol.", app=app_name),
                     _("Gespeichert als {name}. Im Menü erscheint es nach wenigen Sekunden, "
                       "im Panel/Dock nach Alt+F2 → r (Cinnamon neu laden).", name=name))


# ---------------------------------------------------------------- install into the menu
def install():
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(__file__, INSTALL_DIR / "symbolwerkstatt.py")
    for f in ("glyphs.json", "PHOSPHOR-LICENSE"):
        shutil.copy2(data_file(f), INSTALL_DIR / f)
    APP_ICON.parent.mkdir(parents=True, exist_ok=True)
    glyph = next(g for g in load_glyphs() if g["n"] == "magic-wand")
    render_icon(256, "#AF52DE", glyph=glyph).write_to_png(str(APP_ICON))
    DESKTOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP_FILE.write_text(f"""[Desktop Entry]
Type=Application
Name=Symbolwerkstatt
Name[en]=Icon Workshop
Name[es]=Taller de iconos
Comment=Programmsymbole im Monterra-Stil gestalten
Comment[en]=Design app icons in Monterra style
Comment[es]=Diseña iconos de aplicaciones al estilo Monterra
Exec=/usr/bin/python3 "{INSTALL_DIR / 'symbolwerkstatt.py'}" %f
Icon=monterra-symbolwerkstatt
Categories=Graphics;GTK;
Keywords=Icon;Symbol;Monterra;
Keywords[es]=Icono;Símbolo;Monterra;
StartupNotify=true
""")
    for cmd in (["gtk-update-icon-cache", "-f", "-t", str(APP_ICON.parent.parent.parent)],
                ["update-desktop-database", str(DESKTOP_FILE.parent)]):
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(_("Symbolwerkstatt ist jetzt im Menü unter „Grafik“ zu finden."))


def remove():
    DESKTOP_FILE.unlink(missing_ok=True)
    APP_ICON.unlink(missing_ok=True)
    shutil.rmtree(INSTALL_DIR, ignore_errors=True)
    subprocess.run(["update-desktop-database", str(DESKTOP_FILE.parent)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(_("Symbolwerkstatt aus dem Menü entfernt. Bereits erstellte Symbole bleiben erhalten."))


def _repair_report(quiet=False):
    try:
        fixed = repair_shadowed()
    except Exception as e:  # noqa: BLE001
        if not quiet:
            print(_("Reparatur nicht möglich: {e}", e=e))
        return
    if fixed:
        print(_("Eigene Symbole jetzt aktiv für: {apps} (im Panel/Dock nach Alt+F2 → r)", apps=", ".join(fixed)))
    elif not quiet:
        print(_("Alle eigenen Programmsymbole sind richtig zugeordnet."))


def main():
    if "--reparieren" in sys.argv or "--repair" in sys.argv:
        _repair_report()
        return
    if "--install" in sys.argv:
        install()
        _repair_report(quiet=True)
        return
    if "--remove" in sys.argv:
        remove()
        return
    if "--export" in sys.argv:
        i = sys.argv.index("--export")
        dest = sys.argv[i + 1] if len(sys.argv) > i + 1 else "meine" + EXPORT_SUFFIX
        print(_("{n} eigene Programmsymbole exportiert nach {dest}", n=export_icons(dest), dest=dest))
        return
    if "--import" in sys.argv:
        files = [a for a in sys.argv[sys.argv.index("--import") + 1:] if not a.startswith("-")]
        if not files:
            print(_("Bitte die Export-Datei angeben."))
            sys.exit(1)
        for f in files:
            n, missing = import_icons(f)
            print(_("{name}: {n} Programmsymbole übernommen.", name=Path(f).name, n=n))
            if missing:
                print(_("   noch nicht installiert: {apps} – wird nach deren Installation von der Automatik "
                        "übernommen (sonst erneut importieren)", apps=", ".join(missing)))
        return
    if "--help" in sys.argv or "-h" in sys.argv:
        print(HELP.get(LANG, __doc__))
        return
    _repair_report(quiet=True)          # Symbole früherer Versionen still nachbessern
    files = [a for a in sys.argv[1:] if not a.startswith("-") and os.path.isfile(a)]
    template = os.path.abspath(files[0]) if files else None
    app = Gtk.Application(application_id="org.monterra.Symbolwerkstatt", flags=Gio.ApplicationFlags.NON_UNIQUE)
    app.connect("activate", lambda a: Werkstatt(a, template))
    app.run(None)


if __name__ == "__main__":
    main()
