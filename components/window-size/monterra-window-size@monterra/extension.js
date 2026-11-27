// Monterra Fenstergröße – merkt sich Größe und Position der Programmfenster.
//
//  * Gespeichert wird je Programm (Fensterklasse) die letzte normale Größe und Position
//    sowie, ob das Fenster maximiert war. Beim nächsten Öffnen wird das wiederhergestellt.
//  * Nur normale Programmfenster – keine Dialoge, Menüs oder Hilfsfenster.
//  * Öffnet ein Programm ein zweites Fenster, bekommt es nur die Größe (keine Überlagerung).
//  * Liegt die gespeicherte Position nicht mehr auf einem Bildschirm (z. B. zweiter Monitor
//    abgesteckt), bleibt Cinnamons eigene Platzierung; die Größe wird an den Bildschirm angepasst.
//  * Nutzt nur offizielle Fensterfunktionen von Cinnamon (Muffin); Daten:
//    ~/.config/monterra/fenstergroessen.json
const Meta = imports.gi.Meta;
const GLib = imports.gi.GLib;

const DIR = GLib.build_filenamev([GLib.get_user_config_dir(), "monterra"]);
const FILE = GLib.build_filenamev([DIR, "fenstergroessen.json"]);

let store = {};
let displaySignal = 0;
let tracked = new Map();     // MetaWindow -> [Signal-IDs]
let saveTimer = 0;

function load() {
    try {
        let [ok, data] = GLib.file_get_contents(FILE);
        if (ok) store = JSON.parse(imports.byteArray.toString(data)) || {};
    } catch (e) {
        store = {};
    }
}

function save() {
    if (saveTimer) { GLib.source_remove(saveTimer); saveTimer = 0; }
    try {
        GLib.mkdir_with_parents(DIR, 0o755);
        GLib.file_set_contents(FILE, JSON.stringify(store));
    } catch (e) {
        global.logError("Monterra Fenstergröße: " + e);
    }
}

function saveLater() {
    if (saveTimer) GLib.source_remove(saveTimer);
    saveTimer = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, 2, () => { saveTimer = 0; save(); return GLib.SOURCE_REMOVE; });
}

function keyOf(win) {
    let c = win.get_wm_class();
    return c ? c.toLowerCase() : null;
}

function eligible(win) {
    return win.get_window_type() === Meta.WindowType.NORMAL && !win.get_transient_for() &&
           !win.is_skip_taskbar() && win.allows_resize() && keyOf(win) !== null;
}

function isTiled(win) {
    try { return win.tile_mode !== undefined && win.tile_mode !== Meta.TileMode.NONE; } catch (e) { return false; }
}

function remember(win) {
    let key = keyOf(win);
    if (!key || win.is_fullscreen() || isTiled(win)) return;
    let entry = store[key] || {};
    if (win.get_maximized() === Meta.MaximizeFlags.BOTH) {
        entry.max = true;                     // normale Größe von vorher behalten
    } else if (win.get_maximized() === 0) {
        let r = win.get_frame_rect();
        if (r.width < 50 || r.height < 50) return;
        entry.x = r.x; entry.y = r.y; entry.w = r.width; entry.h = r.height; entry.max = false;
    } else {
        return;                               // halb maximiert: nicht merken
    }
    store[key] = entry;
    saveLater();
}

function onScreen(win, x, y, w, h) {
    let n = global.display.get_n_monitors();
    for (let i = 0; i < n; i++) {
        let a = win.get_work_area_for_monitor(i);
        // mindestens die Titelleiste muss gut erreichbar auf einem Bildschirm liegen
        if (x >= a.x - 20 && y >= a.y && x + Math.min(w, 200) <= a.x + a.width && y + 40 <= a.y + a.height)
            return a;
    }
    return null;
}

function otherWindowsOf(win, key) {
    return global.display.list_windows(0).some(w => w !== win && keyOf(w) === key && w.get_window_type() === Meta.WindowType.NORMAL);
}

function restore(win) {
    let key = keyOf(win);
    let s = store[key];
    if (!s || s.w === undefined) {
        if (s && s.max) win.maximize(Meta.MaximizeFlags.BOTH);
        return;
    }
    let cur = win.get_frame_rect();
    let x = s.x, y = s.y, w = s.w, h = s.h;
    let area = onScreen(win, x, y, w, h);
    if (!area || otherWindowsOf(win, key)) {   // Position nicht übernehmen
        x = cur.x; y = cur.y;
        area = win.get_work_area_for_monitor(win.get_monitor());
    }
    w = Math.min(w, area.width); h = Math.min(h, area.height);
    x = Math.max(area.x, Math.min(x, area.x + area.width - w));
    y = Math.max(area.y, Math.min(y, area.y + area.height - h));
    if (cur.x !== x || cur.y !== y || cur.width !== w || cur.height !== h)
        win.move_resize_frame(true, x, y, w, h);
    if (s.max) win.maximize(Meta.MaximizeFlags.BOTH);
}

// Cinnamons Öffnen-Effekt („traditional“) animiert die Bildschirmposition des Fensters ab der
// Stelle, an der es beim Anzeigen stand. Wird das Fenster danach an die gemerkte Stelle gesetzt,
// läuft die Animation trotzdem an der alten Stelle weiter und das Fenster springt erst an ihrem
// Ende – genau der sichtbare Versatz. Deshalb die Positions-Animation an die neue Stelle holen.
function followAnimation(win) {
    let actor = win.get_compositor_private();
    if (!actor) return;
    let b = win.get_buffer_rect();
    let moved = false;
    for (let prop of ["x", "y"]) {
        if (actor.get_transition(prop)) { actor.remove_transition(prop); moved = true; }
    }
    if (moved || actor.x !== b.x || actor.y !== b.y) actor.set_position(b.x, b.y);
}

function restoreNow(win) {
    try {
        if (!differs(win)) return;
        restore(win);
        followAnimation(win);
    } catch (e) { global.logError("Monterra Fenstergröße: " + e); }
}

// weicht das Fenster von der gemerkten Größe ab? (Position nur, wenn sie übernommen wird)
function differs(win) {
    let s = store[keyOf(win)];
    if (!s || s.w === undefined || s.max) return false;
    let r = win.get_frame_rect();
    let area = win.get_work_area_for_monitor(win.get_monitor());
    let w = Math.min(s.w, area.width), h = Math.min(s.h, area.height);
    let movePos = onScreen(win, s.x, s.y, s.w, s.h) && !otherWindowsOf(win, keyOf(win));
    return Math.abs(r.width - w) > 2 || Math.abs(r.height - h) > 2 ||
           (movePos && (Math.abs(r.x - s.x) > 2 || Math.abs(r.y - s.y) > 2));
}

function track(win) {
    if (tracked.has(win)) return;
    let ids = [
        win.connect("size-changed", () => remember(win)),
        win.connect("position-changed", () => remember(win)),
        win.connect("unmanaged", () => { untrack(win); }),
    ];
    tracked.set(win, ids);
}

function untrack(win) {
    let ids = tracked.get(win);
    if (!ids) return;
    for (let id of ids) { try { win.disconnect(id); } catch (e) {} }
    tracked.delete(win);
}

function onCreated(display, win) {
    if (!eligible(win)) return;
    // Sofort anwenden, noch bevor das Fenster zum ersten Mal gezeichnet wird – so erscheint es
    // gleich an der gemerkten Stelle in der gemerkten Größe (vorher sprang es kurz danach dorthin).
    try { restore(win); } catch (e) { global.logError("Monterra Fenstergröße: " + e); }
    // Cinnamon platziert ein neues Fenster erst beim Anzeigen und überschreibt dabei die Position.
    // Diese Platzierung kommt als „position-changed“, noch bevor das Fenster gezeichnet wird –
    // dann sofort zurück an die gemerkte Stelle (höchstens dreimal, nur bis zum ersten Bild).
    let fixes = 0, placeId = 0;
    try {
        placeId = win.connect("position-changed", () => {
            if (fixes >= 3 || !differs(win)) return;
            fixes++;
            // nicht mitten in Cinnamons eigener Verschiebung, sondern direkt vor dem nächsten Bild
            Meta.later_add(Meta.LaterType.BEFORE_REDRAW, () => { restoreNow(win); return false; });
        });
    } catch (e) {}
    let done = false;
    let check = () => {
        if (done) return;
        done = true;
        // manche Programme setzen beim Start noch einmal ihre eigene Größe – dann nachziehen
        if (placeId) { try { win.disconnect(placeId); } catch (e) {} placeId = 0; }
        restoreNow(win);
        track(win);
    };
    let actor = win.get_compositor_private();
    if (actor) {
        let id = actor.connect("first-frame", () => { actor.disconnect(id); check(); });
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1500, () => { check(); return GLib.SOURCE_REMOVE; });
    } else {
        GLib.idle_add(GLib.PRIORITY_DEFAULT, () => { check(); return GLib.SOURCE_REMOVE; });
    }
}

function init() {}

function enable() {
    load();
    displaySignal = global.display.connect("window-created", onCreated);
    // bereits offene Fenster beobachten (nichts verschieben)
    for (let win of global.display.list_windows(0))
        if (eligible(win)) track(win);
}

function disable() {
    if (displaySignal) { global.display.disconnect(displaySignal); displaySignal = 0; }
    for (let win of Array.from(tracked.keys())) untrack(win);
    save();
}
