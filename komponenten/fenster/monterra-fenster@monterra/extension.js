// Monterra Fensterschatten – weiche Schatten für Fenster mit Systemrahmen.
//  * Nutzt nur die offizielle Schatten-Einstellung des Fenstermanagers (Meta.ShadowFactory):
//    keine Zeicheneffekte, keine Eingriffe in Cinnamon-Interna, keine laufenden Kosten.
//  * Die Werte entsprechen den Schatten, die das Monterra-Theme Programmen mit eigener
//    Titelleiste (GTK-CSD) gibt – so sehen alle Fenster gleich aus.
//  * Aktives Fenster: kräftiger Schatten; inaktive Fenster: gleich groß, nur schwächer.
const Meta = imports.gi.Meta;

// [Fensterart, aktiv, Unschärfe-Radius, y-Versatz, Deckkraft 0–255]
const SHADOWS = [
    ["normal",       true,  26, 8, 80],
    ["normal",       false, 26,   8,   36],
    ["dialog",       true,  26, 8, 80],
    ["dialog",       false, 26,   8,   36],
    ["modal_dialog", true,  26, 8, 80],
    ["modal_dialog", false, 26,   8,   36],
];

let saved = [];

function params(radius, y, opacity) {
    let p = new Meta.ShadowParams();
    p.radius = radius;
    p.top_fade = -1;
    p.x_offset = 0;
    p.y_offset = y;
    p.opacity = opacity;
    return p;
}

function init() {}

function enable() {
    let f = Meta.ShadowFactory.get_default();
    saved = [];
    for (let [cls, focused, r, y, o] of SHADOWS) {
        try {
            let old = f.get_params(cls, focused);
            saved.push([cls, focused, params(old.radius, old.y_offset, old.opacity), old.top_fade, old.x_offset]);
            f.set_params(cls, focused, params(r, y, o));
        } catch (e) {
            global.logError("Monterra Fensterschatten: " + cls + ": " + e);
        }
    }
}

function disable() {
    let f = Meta.ShadowFactory.get_default();
    for (let [cls, focused, p, fade, x] of saved) {
        p.top_fade = fade;
        p.x_offset = x;
        try { f.set_params(cls, focused, p); } catch (e) {}
    }
    saved = [];
}
