// Monterra Dock – a small, elegant dock for Linux Mint Cinnamon.
// Runs inside Cinnamon (no extra process), purely event driven: the frame loop only
// runs while something moves and stops as soon as everything has settled.
//
// Pinned apps = Cinnamon's favourites (shared with the menu), plus running apps.
// Click: launch / focus / cycle windows / minimise. Middle click: new window.
// Right click: window list, new window, keep in dock, quit. Drag and drop to reorder,
// drag apps from the menu into the dock to pin them. Optional trash and auto-hide.
// Freely placeable separators between the pinned apps: add them via right click on an app,
// move them by drag and drop, remove them via right click on the separator.
//
// Layout is done by hand (no layout managers) with sub-pixel positions, once per frame,
// right before Cinnamon paints. Sizes follow their targets with a frame-rate independent
// low-pass filter, which gives the smooth "liquid" magnification without any jitter.

const { Clutter, Cinnamon, GLib, Gio, Meta, St } = imports.gi;
const Main = imports.ui.main;
const AppFavorites = imports.ui.appFavorites;
const DND = imports.ui.dnd;
const PopupMenu = imports.ui.popupMenu;
const Settings = imports.ui.settings;
const Util = imports.misc.util;

const UUID = "monterra-dock@monterra";
const MARGIN = 6;            // gap between dock and screen edge (logical px)
const PAD_X = 7;             // horizontal padding inside the dock background
const PAD_TOP = 6;           // space above the icons inside the background
const UNDER = 12;            // space below the icons (running dot)
const SPACING = 4;           // space between icons
const SEP_W = 11;            // separator incl. its margins
const MAX_RENDER = 128;      // icons are rendered once at this size and scaled down
const TAU_SIZE = 0.07;       // s – smoothing of resting widths (apps appearing/leaving, drag gaps)
const TAU_AMP = 0.06;        // s – magnification growing in / fading out
const TAU_PTR = 0.035;       // s – smoothing of the pointer position used for magnification
const TAU_POS = 0.09;        // s – smoothing when the dock switches between anchoring modes
const RANGE = 3.2;           // magnification reaches this many icon widths to each side

let dock = null;

// ---------------------------------------------------------------- helpers
function scale() { return global.ui_scale || 1; }

function primaryMonitor() { return Main.layoutManager.primaryMonitor; }

function windowsOnWorkspace(app) {
    const ws = global.workspace_manager.get_active_workspace();
    return app.get_windows().filter(w => !w.is_skip_taskbar() && (w.get_workspace() === ws || w.is_on_all_workspaces()));
}

function appWindows(app) {
    return app.get_windows().filter(w => !w.is_skip_taskbar());
}

function nowSec() { return GLib.get_monotonic_time() / 1e6; }

// ---------------------------------------------------------------- one dock item
class DockItem {
    constructor(dock, app, pinned) {
        this.dock = dock;
        this.app = app;
        this.pinned = pinned;
        this.menu = null;
        this._bounceId = 0;
        this.isDraggableApp = !app.is_window_backed();   // lets panel launchers accept drops from the dock

        this.actor = new St.Widget({ style_class: "monterra-dock-item", reactive: true });
        this.actor._delegate = this;
        this.iconBox = new St.Widget({ reactive: false });
        this.icon = this._makeIcon(MAX_RENDER);
        this.icon.set_pivot_point(0, 0);
        this.iconBox.add_child(this.icon);
        this.actor.add_child(this.iconBox);
        this.dot = new St.Widget({ style_class: "monterra-dock-dot" });
        this.actor.add_child(this.dot);

        this.actor.connect("button-release-event", (a, e) => this._onRelease(e));
        if (this.isDraggableApp) {
            this._draggable = DND.makeDraggable(this.actor);
            this._draggable.connect("drag-begin", () => this.dock.onItemDragBegin(this));
            this._draggable.connect("drag-cancelled", () => this.dock.onItemDragCancelled(this));
            this._draggable.connect("drag-end", () => this.dock.onItemDragEnd(this));
        }
        this.updateRunning();
    }

    _makeIcon(size) {
        const info = this.app.get_app_info ? this.app.get_app_info() : null;
        const gicon = info ? info.get_icon() : null;
        if (gicon)
            return new St.Icon({ gicon: gicon, icon_size: size, icon_type: St.IconType.FULLCOLOR });
        return this.app.create_icon_texture(size);
    }

    // geometry in physical pixels, set by the dock once per frame
    place(x, y, fp, size, s) {
        this.actor.set_position(x, y);
        this.actor.set_size(Math.max(1, fp), size + UNDER * s);
        this.iconBox.set_position((fp - size) / 2, 0);
        this.iconBox.set_size(Math.max(1, size), Math.max(1, size));
        const f = size / (MAX_RENDER * s);
        this.icon.set_scale(f, f);
        const dw = this.dot.width;
        this.dot.set_position((fp - dw) / 2, size + 3 * s);
    }

    get_app_id() { return this.app.get_id(); }

    getDragActor() {
        const size = Math.max(16, Math.round((this.dock.sizeOf(this) || this.dock.baseSize * scale()) / scale()));
        return this._makeIcon(size);
    }

    getDragActorSource() { return this.iconBox; }

    updateRunning() {
        const running = this.updateRunningQuiet();
        this.dot.opacity = running ? 255 : 0;
        if (running)
            this.stopBounce();
        return running;
    }

    updateRunningQuiet() {
        return this.app.state !== Cinnamon.AppState.STOPPED && appWindows(this.app).length > 0;
    }

    // -------- clicks
    _onRelease(event) {
        const button = event.get_button();
        this.dock.hideLabel();
        if (button === 1)
            this.activate();
        else if (button === 2)
            this.newWindow();
        else if (button === 3)
            this.openMenu();
        return Clutter.EVENT_STOP;
    }

    activate() {
        const wins = windowsOnWorkspace(this.app).length ? windowsOnWorkspace(this.app) : appWindows(this.app);
        if (wins.length === 0) {
            this.launch();
            return;
        }
        const focus = global.display.focus_window;
        const ours = wins.find(w => w === focus);
        wins.sort((a, b) => b.get_user_time() - a.get_user_time());   // most recently used first
        if (ours) {
            if (wins.length > 1) {
                const visible = wins.filter(w => !w.minimized);
                const idx = visible.indexOf(ours);
                const next = visible[(idx + 1) % visible.length];
                if (next && next !== ours) {
                    Main.activateWindow(next, global.get_current_time());
                    return;
                }
            }
            if (this.dock.clickMinimize)
                wins.forEach(w => w.minimize());
        } else {
            Main.activateWindow(wins[0], global.get_current_time());
        }
    }

    launch() {
        this.startBounce();
        try {
            this.app.open_new_window(-1);
        } catch (e) {
            this.app.activate();
        }
    }

    newWindow() {
        if (this.app.can_open_new_window && !this.app.can_open_new_window() && this.app.state !== Cinnamon.AppState.STOPPED)
            this.activate();
        else
            this.launch();
    }

    // -------- launch bounce (stops as soon as the first window appears, at most ~3 s)
    startBounce() {
        if (this._bounceId)
            return;
        let n = 0;
        const h = this.dock.baseSize * 0.32 * scale();
        const step = () => {
            if (n++ >= 3 || this.updateRunningQuiet()) {
                this._bounceId = 0;
                this.iconBox.ease({ translation_y: 0, duration: 180, mode: Clutter.AnimationMode.EASE_OUT_QUAD });
                return GLib.SOURCE_REMOVE;
            }
            this.iconBox.ease({ translation_y: -h, duration: 260, mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                onComplete: () => this.iconBox.ease({ translation_y: 0, duration: 260,
                                                       mode: Clutter.AnimationMode.EASE_IN_QUAD }) });
            return GLib.SOURCE_CONTINUE;
        };
        step();
        this._bounceId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 760, step);
    }

    stopBounce() {
        if (this._bounceId) {
            GLib.source_remove(this._bounceId);
            this._bounceId = 0;
            this.iconBox.ease({ translation_y: 0, duration: 150, mode: Clutter.AnimationMode.EASE_OUT_QUAD });
        }
    }

    // -------- context menu
    openMenu() {
        if (!this.menu) {
            this.menuManager = new PopupMenu.PopupMenuManager({ actor: this.actor });
            this.menu = new PopupMenu.PopupMenu(this.actor, St.Side.BOTTOM);
            this.menu.actor.add_style_class_name("monterra-dock-menu");
            Main.uiGroup.add_child(this.menu.actor);
            this.menu.actor.hide();
            this.menuManager.addMenu(this.menu);
            this.menu.connect("open-state-changed", (m, open) => this.dock.onMenuOpen(open));
        }
        this.menu.removeAll();

        const title = new PopupMenu.PopupMenuItem(this.app.get_name(), { reactive: false });
        title.label.add_style_class_name("monterra-dock-menu-title");
        this.menu.addMenuItem(title);

        const wins = appWindows(this.app);
        if (wins.length > 0) {
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            wins.forEach(w => {
                const t = (w.get_title() || this.app.get_name()).substring(0, 60);
                const item = new PopupMenu.PopupMenuItem((w.has_focus() ? "• " : "   ") + t);
                item.connect("activate", () => Main.activateWindow(w, global.get_current_time()));
                this.menu.addMenuItem(item);
            });
        }

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        const nw = new PopupMenu.PopupMenuItem("Neues Fenster");
        nw.connect("activate", () => this.launch());
        this.menu.addMenuItem(nw);

        const id = this.app.get_id();
        const favs = AppFavorites.getAppFavorites();
        if (!this.app.is_window_backed()) {
            const keep = new PopupMenu.PopupMenuItem(favs.isFavorite(id) ? "Aus dem Dock entfernen" : "Im Dock behalten");
            keep.connect("activate", () => {
                if (favs.isFavorite(id)) {
                    this.dock.onUnpin(global.settings.get_strv("favorite-apps").indexOf(id));
                    favs.removeFavorite(id);
                } else {
                    favs.addFavorite(id);
                }
            });
            this.menu.addMenuItem(keep);
            if (favs.isFavorite(id)) {
                const ids = global.settings.get_strv("favorite-apps");
                const pos = ids.indexOf(id);
                if (pos > 0) {
                    const left = new PopupMenu.PopupMenuItem("Nach links verschieben");
                    left.connect("activate", () => favs.moveFavoriteToPos(id, pos - 1));
                    this.menu.addMenuItem(left);
                }
                if (pos >= 0 && pos < ids.length - 1) {
                    const right = new PopupMenu.PopupMenuItem("Nach rechts verschieben");
                    right.connect("activate", () => favs.moveFavoriteToPos(id, pos + 1));
                    this.menu.addMenuItem(right);
                }
                // separators sit between pinned apps: position p = number of pinned apps before it
                const seps = this.dock.separatorPositions();
                const n = favs.getFavorites().length;
                const sepItems = [];
                if (pos > 0 && !seps.includes(pos)) sepItems.push(["Trenner links einfügen", pos]);
                if (pos >= 0 && pos + 1 < n && !seps.includes(pos + 1)) sepItems.push(["Trenner rechts einfügen", pos + 1]);
                if (sepItems.length) {
                    this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
                    sepItems.forEach(([text, p]) => {
                        const it = new PopupMenu.PopupMenuItem(text);
                        it.connect("activate", () => this.dock.addSeparator(p));
                        this.menu.addMenuItem(it);
                    });
                }
            }
        }

        if (wins.length > 0) {
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            const quit = new PopupMenu.PopupMenuItem(wins.length > 1 ? `Alle ${wins.length} Fenster schließen` : "Beenden");
            quit.connect("activate", () => {
                wins.forEach(w => w.delete(global.get_current_time()));
            });
            this.menu.addMenuItem(quit);
        }

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        const prefs = new PopupMenu.PopupMenuItem("Dock-Einstellungen …");
        prefs.connect("activate", () => Util.spawnCommandLine("xlet-settings extension " + UUID));
        this.menu.addMenuItem(prefs);

        this.menu.toggle();
    }

    destroy() {
        this.stopBounce();
        if (this.menu) {
            this.menuManager.removeMenu(this.menu);
            this.menu.destroy();
            this.menu = null;
        }
        this.actor.destroy();
    }
}

// ---------------------------------------------------------------- trash item
class TrashItem {
    constructor(dock) {
        this.dock = dock;
        this.actor = new St.Widget({ style_class: "monterra-dock-item", reactive: true });
        this.actor._delegate = this;
        this.iconBox = new St.Widget();
        this.icon = new St.Icon({ icon_name: "user-trash", icon_size: MAX_RENDER, icon_type: St.IconType.FULLCOLOR });
        this.icon.set_pivot_point(0, 0);
        this.iconBox.add_child(this.icon);
        this.actor.add_child(this.iconBox);
        this.dot = new St.Widget({ style_class: "monterra-dock-dot", opacity: 0 });
        this.actor.add_child(this.dot);
        this.app = { get_name: () => "Papierkorb", get_id: () => "monterra-trash" };
        this.pinned = false;
        this.menu = null;

        this._file = Gio.File.new_for_uri("trash:///");
        try {
            this._monitor = this._file.monitor_directory(Gio.FileMonitorFlags.NONE, null);
            this._monitor.connect("changed", () => this._update());
        } catch (e) {
            this._monitor = null;
        }
        this._update();
        this.actor.connect("button-release-event", (a, e) => this._onRelease(e));
    }

    place(x, y, fp, size, s) { DockItem.prototype.place.call(this, x, y, fp, size, s); }
    updateRunning() { return false; }

    _update() {
        let full = false;
        try {
            const info = this._file.query_info("trash::item-count", Gio.FileQueryInfoFlags.NONE, null);
            full = info.get_attribute_uint32("trash::item-count") > 0;
        } catch (e) { /* trash not available */ }
        this.icon.icon_name = full ? "user-trash-full" : "user-trash";
    }

    _onRelease(event) {
        this.dock.hideLabel();
        const b = event.get_button();
        if (b === 1) {
            Gio.AppInfo.launch_default_for_uri("trash:///", global.create_app_launch_context(0, -1));
        } else if (b === 3) {
            if (!this.menu) {
                this.menuManager = new PopupMenu.PopupMenuManager({ actor: this.actor });
                this.menu = new PopupMenu.PopupMenu(this.actor, St.Side.BOTTOM);
                this.menu.actor.add_style_class_name("monterra-dock-menu");
                Main.uiGroup.add_child(this.menu.actor);
                this.menu.actor.hide();
                this.menuManager.addMenu(this.menu);
                this.menu.connect("open-state-changed", (m, open) => this.dock.onMenuOpen(open));
                const open = new PopupMenu.PopupMenuItem("Öffnen");
                open.connect("activate", () => Gio.AppInfo.launch_default_for_uri("trash:///", null));
                this.menu.addMenuItem(open);
                const empty = new PopupMenu.PopupMenuItem("Papierkorb leeren …");
                empty.connect("activate", () => Util.spawn(["gio", "trash", "--empty"]));
                this.menu.addMenuItem(empty);
            }
            this.menu.toggle();
        }
        return Clutter.EVENT_STOP;
    }

    destroy() {
        if (this._monitor) this._monitor.cancel();
        if (this.menu) { this.menuManager.removeMenu(this.menu); this.menu.destroy(); }
        this.actor.destroy();
    }
}

// ---------------------------------------------------------------- user separator
// A thin line between pinned apps. Its whole slot is reactive, so it can be grabbed
// (drag and drop) and right-clicked although the line itself is only 1 px wide.
class DockSeparator {
    constructor(dock) {
        this.dock = dock;
        this.menu = null;
        this.isMonterraSeparator = true;
        this.app = { get_name: () => "Trenner", get_id: () => "monterra-separator" };
        this.actor = new St.Widget({ style_class: "monterra-dock-user-sep", reactive: true });
        this.actor._delegate = this;
        this.line = new St.Widget({ style_class: "monterra-dock-separator", opacity: 0 });
        this.actor.add_child(this.line);
        this._draggable = DND.makeDraggable(this.actor);
        this._draggable.connect("drag-begin", () => this.dock.onItemDragBegin(this));
        this._draggable.connect("drag-cancelled", () => this.dock.onItemDragCancelled(this));
        this._draggable.connect("drag-end", () => this.dock.onItemDragEnd(this));
        this.actor.connect("button-release-event", (a, e) => this._onRelease(e));
    }

    getDragActor() {
        const s = scale();
        const w = new St.Widget({ style_class: "monterra-dock-separator monterra-dock-separator-drag" });
        w.set_size(Math.max(2, Math.round(2 * s)), Math.round(this.dock.baseSize * 0.7 * s));
        return w;
    }

    getDragActorSource() { return this.line; }

    _onRelease(event) {
        this.dock.hideLabel();
        if (event.get_button() !== 3) return Clutter.EVENT_STOP;
        if (!this.menu) {
            this.menuManager = new PopupMenu.PopupMenuManager({ actor: this.actor });
            this.menu = new PopupMenu.PopupMenu(this.actor, St.Side.BOTTOM);
            this.menu.actor.add_style_class_name("monterra-dock-menu");
            Main.uiGroup.add_child(this.menu.actor);
            this.menu.actor.hide();
            this.menuManager.addMenu(this.menu);
            this.menu.connect("open-state-changed", (m, open) => this.dock.onMenuOpen(open));
            const title = new PopupMenu.PopupMenuItem("Trenner", { reactive: false });
            title.label.add_style_class_name("monterra-dock-menu-title");
            this.menu.addMenuItem(title);
            const hint = new PopupMenu.PopupMenuItem("Zum Verschieben mit der Maus ziehen", { reactive: false });
            this.menu.addMenuItem(hint);
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            const rm = new PopupMenu.PopupMenuItem("Trenner entfernen");
            rm.connect("activate", () => this.dock.removeSeparator(this));
            this.menu.addMenuItem(rm);
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            const prefs = new PopupMenu.PopupMenuItem("Dock-Einstellungen …");
            prefs.connect("activate", () => Util.spawnCommandLine("xlet-settings extension " + UUID));
            this.menu.addMenuItem(prefs);
        }
        this.menu.toggle();
        return Clutter.EVENT_STOP;
    }

    destroy() {
        if (this.menu) { this.menuManager.removeMenu(this.menu); this.menu.destroy(); this.menu = null; }
        this.actor.destroy();
    }
}

// ---------------------------------------------------------------- the dock
//
// The dock is a row of "slots". A slot is an item (app or trash), a separator or a gap
// (the free space that opens while dragging). Every slot has a resting width `rest`,
// a current width `cur` and – for items – a magnified target. `cur` follows its target
// each frame; dying slots shrink to zero and are then removed.
class MonterraDock {
    constructor() {
        this.slots = [];
        this.trash = null;
        this._signals = [];
        this._hidden = false;
        this._menuOpen = false;
        this._overlapId = 0;
        this._rebuildId = 0;
        this._laterId = 0;
        this._watchId = 0;
        this._anchored = false;
        this._amp = 0;
        this._spx = 0;
        this._L = null;
        this._lOff = 0;
        this._geo = null;           // last applied geometry {L, W, H, top}
        this._dragItem = null;      // our item being dragged
        this._drop = null;          // {source, index} while something hovers over the dock
        this._built = false;

        this.settings = new Settings.ExtensionSettings(this, UUID);
        this.settings.bind("icon-size", "baseSize", () => this.rebuild());
        this.settings.bind("magnify", "magnify", () => this.kick());
        this.settings.bind("magnify-size", "magnifySize", () => this.kick());
        this.settings.bind("autohide", "autohide", () => this._applyAutohide());
        this.settings.bind("show-running", "showRunning", () => this.rebuild());
        this.settings.bind("click-minimize", "clickMinimize", null);
        this.settings.bind("show-trash", "showTrash", () => this.rebuild());
        this.settings.bind("style", "style", () => this._applyStyle());
        this.settings.bind("separators", "separators", () => this._queueRebuild());

        // actors: container [bg, separators, items] + strut + hot edge + name label
        this.actor = this.container = new St.Widget({ name: "monterraDock", reactive: true });
        this.container._delegate = this;
        this.bg = new St.Widget({ style_class: "monterra-dock-bg" });
        this.container.add_child(this.bg);
        this._sepRun = this._makeSeparator();
        this._sepTrash = this._makeSeparator();
        // no track_hover: a :hover style change would re-layout the dock under the pointer
        this.container.connect("enter-event", () => { this._onHover(true); return Clutter.EVENT_PROPAGATE; });
        this.container.connect("leave-event", () => { this._onHover(false); return Clutter.EVENT_PROPAGATE; });
        this.container.connect("motion-event", () => { this.kick(); return Clutter.EVENT_PROPAGATE; });

        this.label = new St.Label({ style_class: "monterra-dock-label", opacity: 0 });
        this.label.hide();
        this._labelItem = null;
        Main.uiGroup.add_child(this.label);

        this.strut = new St.Widget({ reactive: false, opacity: 0 });
        Cinnamon.util_set_hidden_from_pick(this.strut, true);   // invisible, must not shadow the dock for drag and drop
        this.hotEdge = new St.Widget({ reactive: true, opacity: 0 });
        this.hotEdge.connect("enter-event", () => { this._show(); this._queueOverlap(1200); });
        this.hotEdge._delegate = {   // reveal the hidden dock when something is dragged to the screen edge
            handleDragOver: () => { this._show(); this._queueOverlap(1500); return DND.DragMotionResult.CONTINUE; },
        };

        Main.layoutManager.addChrome(this.container, { affectsStruts: false, visibleInFullscreen: false });
        Main.layoutManager.addChrome(this.strut, { affectsStruts: true, affectsInputRegion: false });
        Main.layoutManager.addChrome(this.hotEdge, { affectsStruts: false, visibleInFullscreen: false });

        // events (no polling)
        const appSys = Cinnamon.AppSystem.get_default();
        this._connect(appSys, "app-state-changed", () => this._queueRebuild());
        this._connect(appSys, "installed-changed", () => this._queueRebuild());
        this._connect(AppFavorites.getAppFavorites(), "changed", () => this._queueRebuild());
        this._connect(Cinnamon.WindowTracker.get_default(), "window-app-changed", () => this._queueRebuild());
        this._connect(global.display, "window-created", () => this._queueRebuild());
        this._connect(global.display, "notify::focus-window", () => { this._trackFocusWindow(); this._queueOverlap(); });
        try { this._connect(global.display, "grab-op-end", () => this._queueOverlap(50)); } catch (e) {}
        this._connect(global.display, "restacked", () => this._queueOverlap());
        this._connect(global.window_manager, "switch-workspace", () => { this._updateDots(); this._queueOverlap(); });
        this._connect(global.window_manager, "minimize", () => this._queueOverlap());
        this._connect(global.window_manager, "unminimize", () => this._queueOverlap());
        this._connect(Main.layoutManager, "monitors-changed", () => { this._updateStruts(); this.kick(); });
        this._connect(global, "scale-changed", () => this.rebuild());
        this._themeSettings = new Gio.Settings({ schema_id: "org.cinnamon.theme" });
        this._connect(this._themeSettings, "changed::name", () => this._applyStyle());

        // Arbeitsflächen-Übersicht (Expo) und Fensterübersicht (Scale), z. B. über aktive Ecken:
        // dort bekommt das Dock keine Mausereignisse – also ausblenden und danach frisch starten,
        // statt im letzten (vergrößerten) Zustand „einzufrieren“.
        this._inOverview = false;
        [Main.expo, Main.overview].forEach(ov => {
            if (!ov) return;
            try {
                this._connect(ov, "showing", () => this._onOverview(true));
                this._connect(ov, "hidden", () => this._onOverview(false));
            } catch (e) { /* ältere/neuere Cinnamon-Version ohne diese Signale */ }
        });

        this._applyStyle();
        this.rebuild();
        this._applyAutohide();
    }

    _onOverview(open) {
        if (!this.container || this._inOverview === open) return;
        this._inOverview = open;
        if (open) {
            this.hideLabel();
            this._amp = 0;                                  // Vergrößerung sofort zurücksetzen
            this.container.reactive = false;
            this.container.ease({ opacity: 0, duration: 120, mode: Clutter.AnimationMode.EASE_OUT_QUAD });
        } else {
            this.container.reactive = true;
            this.container.ease({ opacity: 255, duration: 160, mode: Clutter.AnimationMode.EASE_OUT_QUAD });
            this.kick();
            this._queueOverlap(300);
        }
    }

    _connect(obj, sig, cb) {
        this._signals.push([obj, obj.connect(sig, cb)]);
    }

    _makeSeparator() {
        const actor = new St.Widget({ style_class: "monterra-dock-separator", opacity: 0 });
        this.container.add_child(actor);
        return { kind: "sep", actor, cur: 0, rest: 0 };
    }

    // -------- user separators (stored as positions: number of pinned apps before the separator)
    separatorPositions() {
        const raw = Array.isArray(this.separators) ? this.separators : [];
        const out = [];
        raw.forEach(p => { p = parseInt(p); if (!isNaN(p) && p > 0 && !out.includes(p)) out.push(p); });
        return out.sort((a, b) => a - b);
    }

    _saveSeparators(list) {
        const n = AppFavorites.getAppFavorites().getFavorites().length;
        const clean = [];
        list.forEach(p => { if (p > 0 && p < n && !clean.includes(p)) clean.push(p); });
        clean.sort((a, b) => a - b);
        this.settings.setValue("separators", clean);
        this._queueRebuild();
    }

    addSeparator(pos) {
        const list = this.separatorPositions();
        list.push(pos);
        this._saveSeparators(list);
    }

    removeSeparator(sep) {
        const order = this._unitTokens(null);
        const i = order.findIndex(t => t.sep === sep);
        if (i < 0) return;
        order.splice(i, 1);
        this._saveSeparators(this._positionsFrom(order));
    }

    onUnpin(favIndex) {
        if (favIndex < 0) return;
        this._saveSeparators(this.separatorPositions().map(p => (p > favIndex ? p - 1 : p)));
    }

    // pinned apps and user separators in dock order (optionally without one slot)
    _units(skip) {
        return this.slots.filter(sl => !sl.dying && sl !== skip &&
            ((sl.kind === "item" && sl.item.pinned && sl.item !== this._dragItem) ||
             (sl.kind === "sep" && sl.user && sl.sep !== this._dragItem)));
    }

    _unitTokens(skip) {
        return this._units(skip).map(sl => (sl.kind === "item" ? { t: "a", id: sl.item.app.get_id() } : { t: "s", sep: sl.sep }));
    }

    _positionsFrom(tokens) {
        const out = [];
        let apps = 0;
        tokens.forEach(t => { if (t.t === "a" || t.t === "new") apps++; else if (t.t === "s" || t.t === "newsep") out.push(apps); });
        return out;
    }

    _slotOf(src) { return this.slots.find(x => x.item === src || x.sep === src); }

    // -------- building
    _queueRebuild() {
        if (this._rebuildId) return;
        this._rebuildId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 120, () => {
            this._rebuildId = 0;
            this.rebuild();
            return GLib.SOURCE_REMOVE;
        });
    }

    rebuild() {
        if (!this.container) return;
        if (this._dragItem || this._drop) {          // never reshuffle while something is dragged
            this._rebuildPending = true;
            return;
        }
        this._rebuildPending = false;
        const s = scale();
        const baseS = this.baseSize * s;
        const favs = AppFavorites.getAppFavorites().getFavorites();
        const favIds = favs.map(a => a.get_id());
        const running = Cinnamon.AppSystem.get_default().get_running()
            .filter(a => !favIds.includes(a.get_id()) && appWindows(a).length > 0);
        const runningShown = this.showRunning ? running : [];

        const old = new Map();
        this.slots.forEach(sl => { if (sl.kind === "item" && sl.item !== this.trash) old.set(sl.item.app.get_id(), sl); });
        const order = [];
        const useItem = (app, pinned) => {
            let sl = old.get(app.get_id());
            if (sl) {
                old.delete(app.get_id());
            } else {
                const item = new DockItem(this, app, pinned);
                this.container.add_child(item.actor);
                sl = { kind: "item", item, cur: this._built ? 0 : baseS, rest: 0 };
            }
            sl.item.pinned = pinned;
            sl.dying = false;
            sl.rest = baseS;
            sl.item.actor.reactive = true;
            sl.item.updateRunning();
            order.push(sl);
        };
        // user separators: reuse the existing ones in order, new ones grow in
        const sepPos = favs.length > 1 ? this.separatorPositions().filter(p => p < favs.length) : [];
        const oldSeps = this.slots.filter(sl => sl.kind === "sep" && sl.user && !sl.dying);
        const useSep = () => {
            let sl = oldSeps.shift();
            if (!sl) {
                const sep = new DockSeparator(this);
                this.container.add_child(sep.actor);
                sl = { kind: "sep", user: true, sep, cur: this._built ? 0 : SEP_W * s, rest: 0 };
            }
            sl.dying = false;
            sl.rest = SEP_W * s;
            sl.sep.actor.reactive = true;
            order.push(sl);
        };
        favs.forEach((a, i) => {
            sepPos.filter(p => p === i).forEach(useSep);
            useItem(a, true);
        });
        this._sepRun.rest = favs.length > 0 && runningShown.length > 0 ? SEP_W * s : 0;
        order.push(this._sepRun);
        runningShown.forEach(a => useItem(a, false));

        this._sepTrash.rest = this.showTrash && order.some(sl => sl.kind === "item") ? SEP_W * s : 0;
        order.push(this._sepTrash);
        let trashSlot = this.slots.find(sl => sl.kind === "item" && sl.item === this.trash);
        if (this.showTrash) {
            if (!trashSlot) {
                this.trash = new TrashItem(this);
                this.container.add_child(this.trash.actor);
                trashSlot = { kind: "item", item: this.trash, cur: this._built ? 0 : baseS, rest: 0 };
            }
            trashSlot.rest = baseS;
            trashSlot.dying = false;
            order.push(trashSlot);
        } else if (trashSlot) {
            old.set("monterra-trash", trashSlot);
            this.trash = null;
        }

        // items that disappeared shrink away at their old place
        old.forEach(sl => {
            sl.dying = true;
            sl.rest = 0;
            sl.item.actor.reactive = false;
            order.splice(Math.min(this.slots.indexOf(sl), order.length), 0, sl);
        });
        oldSeps.forEach(sl => {
            sl.dying = true;
            sl.rest = 0;
            sl.sep.actor.reactive = false;
            order.splice(Math.min(this.slots.indexOf(sl), order.length), 0, sl);
        });
        this.slots.filter(sl => sl.kind === "gap").forEach(sl => {
            sl.dying = true; sl.rest = 0;
            order.splice(Math.min(this.slots.indexOf(sl), order.length), 0, sl);
        });
        this.slots = order;
        this._built = true;
        this._updateStruts();
        this.kick();
        this._queueOverlap();
    }

    itemSlots() { return this.slots.filter(sl => sl.kind === "item" && !sl.dying); }

    sizeOf(item) {
        const sl = this.slots.find(x => x.item === item);
        return sl ? (sl.shown || sl.cur) : 0;
    }

    _updateDots() { this.itemSlots().forEach(sl => sl.item.updateRunning()); }

    // footprint of a slot of width w: items carry their spacing, which fades with their size
    _fp(sl, w, s) {
        if (sl.kind !== "item") return w;
        const baseS = this.baseSize * s;
        return w + SPACING * s * Math.min(1, w / Math.max(1, baseS));
    }

    _restWidth(s) {
        let w = 2 * (PAD_X - SPACING / 2) * s;
        this.slots.forEach(sl => { w += this._fp(sl, sl.rest, s); });
        return w;
    }

    _bgHeight(s) { return (this.baseSize + PAD_TOP + UNDER) * s; }

    // strut and hot edge follow the *resting* size of the dock
    _updateStruts() {
        const m = primaryMonitor();
        if (!m || !this.strut) return;
        const s = scale();
        const restW = this._restWidth(s);
        const bgH = this._bgHeight(s) + MARGIN * s;
        this.strut.set_size(Math.round(restW), this.autohide ? 0 : Math.round(bgH));
        this.strut.set_position(Math.round(m.x + (m.width - restW) / 2), Math.round(m.y + m.height - (this.autohide ? 0 : bgH)));
        const hw = Math.round(Math.max(restW, 200 * s));
        this.hotEdge.set_size(hw, Math.max(2, Math.round(2 * s)));
        this.hotEdge.set_position(Math.round(m.x + (m.width - hw) / 2), m.y + m.height - this.hotEdge.height);
        this.hotEdge.visible = !!this.autohide;
    }

    // -------- frame loop
    kick() {
        if (this._laterId || !this.container) return;
        this._last = nowSec() - 1 / 60;
        this._laterId = Meta.later_add(Meta.LaterType.BEFORE_REDRAW, () => this._tick());
        this.container.queue_redraw();      // make sure a frame comes (pointer motion alone does not paint)
    }

    _tick() {
        this._laterId = 0;
        if (!this.container) return false;
        if (this._menuOpen) {               // keep everything still while a menu hangs on an icon
            this._last = nowSec();
            return false;
        }
        const m = primaryMonitor();
        if (!m) return false;
        const s = scale();
        const t = nowSec();
        const dt = Math.max(0.001, Math.min(0.05, t - this._last));
        this._last = t;
        const [px, py] = global.get_pointer();
        const baseS = this.baseSize * s;
        const edge = (PAD_X - SPACING / 2) * s;
        const bottom = m.y + m.height - MARGIN * s;
        const bgH = this._bgHeight(s);
        let moving = false;

        // where is the pointer, what are we doing?
        const inside = this._pointerInside(px, py);
        const dragging = !!(this._dragItem || this._drop);
        const wantMag = !dragging && this.magnify && inside && !this._hidden && !this._inOverview;

        // 1) resting widths follow their targets (items appearing/leaving, drag gaps, size changes)
        const k = 1 - Math.exp(-dt / TAU_SIZE);
        this.slots.forEach(sl => {
            const diff = sl.rest - sl.cur;
            if (Math.abs(diff) < 0.08) sl.cur = sl.rest;
            else { sl.cur += diff * k; moving = true; }
        });

        // 2) magnification = one smoothed strength + one smoothed pointer position.
        //    Everything below is a pure function of these two values, so the layout can never wobble.
        const ampTarget = wantMag ? 1 : 0;
        if (this._amp === 0 && wantMag) this._spx = px;            // start right under the pointer
        const dAmp = ampTarget - this._amp;
        if (Math.abs(dAmp) < 0.002) this._amp = ampTarget;
        else { this._amp += dAmp * (1 - Math.exp(-dt / TAU_AMP)); moving = true; }
        if (this._amp > 0) {
            const dx = px - this._spx;
            if (wantMag && Math.abs(dx) > 0.05) { this._spx += dx * (1 - Math.exp(-dt / TAU_PTR)); moving = true; }
            else if (wantMag) this._spx = px;
        }
        const spx = this._spx;
        const amp = this._amp;

        // unmagnified layout (current widths) – reference for magnification and anchoring
        const baseFps = this.slots.map(sl => this._fp(sl, sl.cur, s));
        const baseW = 2 * edge + baseFps.reduce((a, b) => a + b, 0);
        const baseLeft = m.x + (m.width - baseW) / 2;

        // displayed widths
        const maxF = Math.max(1, this.magnifySize / this.baseSize);
        const range = baseS * RANGE;
        let bx = baseLeft + edge;
        const widths = this.slots.map((sl, i) => {
            let w = sl.cur;
            if (amp > 0 && sl.kind === "item" && !sl.dying && sl.cur > 0) {
                const d = Math.abs(spx - (bx + baseFps[i] / 2));
                if (d < range)
                    w = sl.cur * (1 + (maxF - 1) * amp * (Math.cos(Math.PI * d / range) + 1) / 2);
            }
            bx += baseFps[i];
            return w;
        });
        let W = 2 * edge, maxSize = 0;
        const fps = this.slots.map((sl, i) => {
            const f = this._fp(sl, widths[i], s);
            W += f;
            if (sl.kind === "item") maxSize = Math.max(maxSize, widths[i]);
            return f;
        });
        const H = Math.max(bgH, maxSize + (PAD_TOP / 2 + UNDER) * s);

        // horizontal anchor
        const anchored = amp > 0 && !dragging;
        let targetL;
        if (anchored) {
            // the spot under the pointer keeps its place, the dock grows around it
            const rel = spx - baseLeft - edge;
            let mapped = rel;
            if (rel > 0) {
                let restX = 0, newX = 0, found = false;
                for (let i = 0; i < this.slots.length; i++) {
                    const rf = baseFps[i];
                    if (rf > 0 && rel < restX + rf) {
                        mapped = newX + (rel - restX) / rf * fps[i];
                        found = true;
                        break;
                    }
                    restX += rf;
                    newX += fps[i];
                }
                if (!found) mapped = newX + (rel - restX);
            }
            targetL = spx - edge - mapped;
        } else {
            targetL = m.x + (m.width - W) / 2;
        }
        if (anchored !== this._anchored) {
            this._lOff = this._L === null ? 0 : this._L - targetL;
            this._anchored = anchored;
        }
        this._lOff *= Math.exp(-dt / TAU_POS);
        if (Math.abs(this._lOff) < 0.1) this._lOff = 0; else moving = true;
        let L = targetL + this._lOff;
        if (!moving) L = Math.round(L);     // settle on whole pixels
        this._L = L;

        // apply
        const top = bottom - H;
        this.container.set_position(L, top);
        this.container.set_size(W, H);
        this.bg.set_position(0, H - bgH);
        this.bg.set_size(W, bgH);
        const iconBottom = H - UNDER * s;
        let x = edge;
        let hovered = null, hoverCx = 0, hoverTop = 0;
        this.slots.forEach((sl, i) => {
            const f = fps[i];
            if (sl.kind === "item") {
                const w = widths[i];
                sl.item.place(x, iconBottom - w, f, w, s);
                sl.shown = w;
                if (inside && !sl.dying && px >= L + x && px < L + x + f) {
                    hovered = sl.item;
                    hoverCx = L + x + f / 2;
                    hoverTop = top + iconBottom - w;
                }
            } else if (sl.kind === "sep") {
                const lw = Math.max(1, Math.round(s));
                const h = Math.round(baseS * 0.7);
                const op = Math.round(255 * Math.min(1, f / (SEP_W * s)));
                if (sl.user) {
                    sl.sep.actor.set_position(x, iconBottom - baseS);
                    sl.sep.actor.set_size(Math.max(1, f), Math.max(1, baseS));
                    sl.sep.line.set_position((f - lw) / 2, baseS / 2 - h / 2);
                    sl.sep.line.set_size(lw, h);
                    sl.sep.line.opacity = op;
                } else {
                    sl.actor.set_position(x + (f - lw) / 2, iconBottom - baseS / 2 - h / 2);
                    sl.actor.set_size(lw, h);
                    sl.actor.opacity = op;
                }
            }
            x += f;
        });
        this._geo = { L, W, H, top };

        // finished slots
        const dead = this.slots.filter(sl => sl.dying && sl.cur === 0);
        if (dead.length) {
            dead.forEach(sl => { if (sl.item) sl.item.destroy(); if (sl.sep) sl.sep.destroy(); });
            this.slots = this.slots.filter(sl => !dead.includes(sl));
        }

        // name bubble
        if (hovered && !dragging && !this._menuOpen && !this._hidden && !this._inOverview) {
            if (hovered !== this._labelItem) this._showLabel(hovered);
            this._positionLabel(hoverCx, hoverTop);
        } else if (this._labelItem) {
            this.hideLabel();
        }

        // an external drag was cancelled with Esc while over the dock
        if (this._drop && !DND.isDragging()) this._clearDrop();

        if (moving || this._drop) {
            this._laterId = Meta.later_add(Meta.LaterType.BEFORE_REDRAW, () => this._tick());
            if (!moving) this.container.queue_redraw();
        }
        if (this._amp > 0 || this._labelItem) this._ensureWatch();
        return false;
    }

    _pointerInside(px, py) {
        const g = this._geo;
        if (!g) return false;
        const m = primaryMonitor();
        return px >= g.L && px <= g.L + g.W && py >= g.top && py < m.y + m.height;
    }

    // Leave events are not reliable when the pointer jumps away quickly, so while the dock is
    // magnified (or shows a name) the pointer is checked 10× per second – and only then.
    _ensureWatch() {
        if (this._watchId) return;
        this._watchId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
            if (!this.container || (this._amp === 0 && !this._labelItem)) {
                this._watchId = 0;
                return GLib.SOURCE_REMOVE;
            }
            if (this._menuOpen) return GLib.SOURCE_CONTINUE;
            const [px, py] = global.get_pointer();
            if (!this._pointerInside(px, py)) this.kick();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _onHover(entered) {
        if (entered) this._show();
        else this._queueOverlap(600);
        this.kick();
    }

    // -------- name bubble
    _showLabel(item) {
        if (this._menuOpen) return;
        this._labelItem = item;
        this.label.text = item.app.get_name();
        this.label.show();
        this.label.remove_all_transitions();
        this.label.ease({ opacity: 255, duration: 100, mode: Clutter.AnimationMode.EASE_OUT_QUAD });
    }

    _positionLabel(cx, iconTop) {
        const [, lw] = this.label.get_preferred_width(-1);
        const [, lh] = this.label.get_preferred_height(lw);
        this.label.set_position(Math.round(cx - lw / 2), Math.round(iconTop - lh - 10 * scale()));
    }

    hideLabel() {
        this._labelItem = null;
        this.label.remove_all_transitions();
        this.label.opacity = 0;
        this.label.hide();
    }

    onMenuOpen(open) {
        this._menuOpen = open;
        if (open) {
            this.hideLabel();
        } else {
            this._queueOverlap(400);
            this.kick();
        }
    }

    // -------- drag and drop
    onItemDragBegin(item) {
        this.hideLabel();
        this._dragItem = item;
        const sl = this._slotOf(item);
        if (sl) sl.rest = 0;
        item.actor.opacity = 0;
        this.kick();
    }

    onItemDragCancelled(item) {
        this._restoreDragged(item);
    }

    onItemDragEnd(item) {
        this._restoreDragged(item);
        this._dragItem = null;
        this._clearDrop();
        if (this._rebuildPending) this._queueRebuild();
        this._queueOverlap(400);
    }

    _restoreDragged(item) {
        const sl = this._slotOf(item);
        if (sl && !sl.dying) sl.rest = item.isMonterraSeparator ? SEP_W * scale() : this.baseSize * scale();
        item.actor.opacity = 255;
        this.kick();
    }

    _isOwnSeparator(source) {
        return !!(source && source.isMonterraSeparator && source.dock === this);
    }

    _isAppSource(source) {
        return source && (source instanceof DockItem ? source.isDraggableApp : !!source.isDraggableApp) &&
               typeof source.get_app_id === "function";
    }

    // insertion index among the pinned apps and user separators (without the dragged one)
    _dropIndex(source, px) {
        const units = this._units();
        const ownUnpinned = source instanceof DockItem && !source.pinned;
        let x = this._geo ? this._geo.L + (PAD_X - SPACING / 2) * scale() : 0;
        let idx = 0, pinnedEnd = x;
        for (const sl of this.slots) {
            const f = this._fp(sl, sl.cur, scale());
            if (units.includes(sl)) {
                if (px > x + f / 2) idx = units.indexOf(sl) + 1;
                pinnedEnd = x + f;
            } else if (sl.kind === "gap" && !sl.dying) {
                pinnedEnd = Math.max(pinnedEnd, x + f);
            }
            x += f;
        }
        if (ownUnpinned && px > pinnedEnd + this.baseSize * scale() * 0.5)
            return null;                        // a running app moved within the running area: nothing to pin
        return idx;
    }

    handleDragOver(source, actor, x, y, time) {
        const isSep = this._isOwnSeparator(source);
        if (!isSep && !this._isAppSource(source))
            return DND.DragMotionResult.NO_DROP;
        if (!this._dragMonitor) {
            this._dragMonitor = { dragMotion: (e) => this._onDragMotion(e) };
            DND.addDragMonitor(this._dragMonitor);
        }
        this._show();
        const [px] = global.get_pointer();
        this._setDrop(source, this._dropIndex(source, px));
        return source instanceof DockItem || isSep ? DND.DragMotionResult.MOVE_DROP : DND.DragMotionResult.COPY_DROP;
    }

    _onDragMotion(e) {
        const g = this._geo;
        const pad = 12 * scale();
        if (g && !(e.x >= g.L - pad && e.x <= g.L + g.W + pad && e.y >= g.top - 2 * pad))
            this._clearDrop();
        return DND.DragMotionResult.CONTINUE;
    }

    _setDrop(source, index) {
        if (index === null) { this._clearDrop(); return; }
        if (this._drop && this._drop.index === index && this._drop.gap && !this._drop.gap.dying) return;
        if (this._drop && this._drop.gap) { this._drop.gap.dying = true; this._drop.gap.rest = 0; }
        // insert a gap before the index-th unit (pinned app or separator) or after the last one
        const units = this._units();
        let pos;
        if (index < units.length) {
            pos = this.slots.indexOf(units[index]);
        } else {
            const last = this.slots.reduce((acc, sl, i) => (sl.kind === "item" && sl.item.pinned) || sl.kind === "gap" ||
                                                          (sl.kind === "sep" && sl.user) ? i : acc, -1);
            pos = last + 1;
        }
        const gapW = this._isOwnSeparator(source) ? SEP_W * scale() : (this.baseSize + SPACING) * scale();
        let gap = [this.slots[pos - 1], this.slots[pos]].find(sl => sl && sl.kind === "gap");
        if (!gap) {
            gap = { kind: "gap", cur: 0, rest: 0 };
            this.slots.splice(pos, 0, gap);
        }
        gap.dying = false;
        gap.rest = gapW;
        this._drop = { source, index, gap };
        this.kick();
    }

    _clearDrop() {
        if (this._dragMonitor) {
            DND.removeDragMonitor(this._dragMonitor);
            this._dragMonitor = null;
        }
        if (!this._drop) return;
        if (this._drop.gap) { this._drop.gap.dying = true; this._drop.gap.rest = 0; }
        this._drop = null;
        if (this._rebuildPending && !this._dragItem) this._queueRebuild();
        this.kick();
    }

    acceptDrop(source, actor, x, y, time) {
        if (this._drop && this._isOwnSeparator(source)) return this._acceptSeparator(source);
        if (!this._drop || !this._isAppSource(source)) return false;
        const { index, gap } = this._drop;
        // new order of apps and separators -> separator positions and the app's favourite index
        const tokens = this._unitTokens(null);
        tokens.splice(index, 0, { t: "new" });
        const appId = source.get_app_id();
        const order = tokens.filter(t => !(t.t === "a" && t.id === appId));
        const appIndex = order.filter((t, i) => t.t === "a" && i < order.findIndex(u => u.t === "new")).length;
        const id = source.get_app_id();
        const favs = AppFavorites.getAppFavorites();
        const gi = this.slots.indexOf(gap);
        const s = scale();
        const width = Math.max(0, gap.cur - SPACING * s);

        // put the item into the gap right away (no jump), then store the new order
        let sl = this.slots.find(x => x.kind === "item" && !x.dying && x.item.app.get_id && x.item.app.get_id() === id);
        if (sl) {
            this.slots.splice(this.slots.indexOf(sl), 1);
        } else {
            const app = Cinnamon.AppSystem.get_default().lookup_app(id);
            if (app) {
                const item = new DockItem(this, app, true);
                this.container.add_child(item.actor);
                sl = { kind: "item", item, cur: 0, rest: 0 };
            }
        }
        if (sl) {
            sl.cur = width;
            sl.rest = this.baseSize * s;
            sl.dying = false;
            sl.item.pinned = true;
            sl.item.actor.opacity = 255;
            sl.item.actor.reactive = true;
            this.slots.splice(this.slots.indexOf(gap), 1, sl);
        } else if (gi >= 0) {
            gap.dying = true; gap.rest = 0;
        }
        this._drop = null;
        if (this._dragMonitor) { DND.removeDragMonitor(this._dragMonitor); this._dragMonitor = null; }

        const n = favs.getFavorites().length + (favs.isFavorite(id) ? 0 : 1);
        const newSeps = this._positionsFrom(order).filter(p => p > 0 && p < n);
        const curSeps = this.separatorPositions();
        if (newSeps.join(",") !== curSeps.join(","))
            this.settings.setValue("separators", newSeps);
        if (favs.isFavorite(id)) favs.moveFavoriteToPos(id, appIndex);
        else favs.addFavoriteAtPos(id, appIndex);
        this._rebuildPending = true;
        this.kick();
        return true;
    }

    _acceptSeparator(sep) {
        const { index, gap } = this._drop;
        const tokens = this._unitTokens(null);
        tokens.splice(index, 0, { t: "newsep" });
        // put the separator into the gap right away (no jump), then store the new positions
        const sl = this._slotOf(sep);
        if (sl && this.slots.includes(gap)) {
            this.slots.splice(this.slots.indexOf(sl), 1);
            sl.cur = gap.cur;
            sl.rest = SEP_W * scale();
            this.slots.splice(this.slots.indexOf(gap), 1, sl);
        }
        sep.actor.opacity = 255;
        this._drop = null;
        if (this._dragMonitor) { DND.removeDragMonitor(this._dragMonitor); this._dragMonitor = null; }
        this._saveSeparators(this._positionsFrom(tokens));   // at the very start or end it disappears
        this._rebuildPending = true;
        this.kick();
        return true;
    }

    // -------- auto-hide (only when a window actually overlaps the dock)
    _applyAutohide() {
        this._updateStruts();
        this._trackFocusWindow();
        if (!this.autohide) this._show();
        this._queueOverlap();
    }

    _queueOverlap(delay = 150) {
        if (!this.autohide) return;
        if (this._overlapId) GLib.source_remove(this._overlapId);
        this._overlapId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, delay, () => {
            this._overlapId = 0;
            this._checkOverlap();
            return GLib.SOURCE_REMOVE;
        });
    }

    // follow moves/resizes of the focused window only (cheap)
    _trackFocusWindow() {
        if (this._focusWin) {
            this._focusIds.forEach(id => { try { this._focusWin.disconnect(id); } catch (e) {} });
        }
        this._focusWin = this.autohide ? global.display.focus_window : null;
        this._focusIds = [];
        if (this._focusWin) {
            this._focusIds.push(this._focusWin.connect("position-changed", () => this._queueOverlap(80)));
            this._focusIds.push(this._focusWin.connect("size-changed", () => this._queueOverlap(80)));
        }
    }

    _pointerNearDock() {
        const [px, py] = global.get_pointer();
        const g = this._geo;
        return (g && px >= g.L && px <= g.L + g.W && py >= g.top - 4) || py >= this.hotEdge.y - 1;
    }

    _checkOverlap() {
        if (!this.autohide || this._menuOpen || this._dragItem || this._drop) return;
        if (!this._hidden && this._pointerNearDock()) {
            this._queueOverlap(700);              // check again once the pointer has left
            return;
        }
        const m = primaryMonitor();
        const s = scale();
        const w = this._restWidth(s);
        const top = m.y + m.height - this._bgHeight(s) - MARGIN * s;
        const left = m.x + (m.width - w) / 2, right = left + w;
        const ws = global.workspace_manager.get_active_workspace();
        const overlap = ws.list_windows().some(win => {
            if (win.minimized || !win.showing_on_its_workspace()) return false;
            const t = win.get_window_type();
            if (t !== Meta.WindowType.NORMAL && t !== Meta.WindowType.DIALOG) return false;
            const r = win.get_frame_rect();
            return r.x < right && r.x + r.width > left && r.y + r.height > top && win.get_monitor() === m.index;
        });
        if (overlap) this._hide(); else this._show();
    }

    _hide() {
        if (this._hidden) return;
        this._hidden = true;
        this.hideLabel();
        this.container.ease({ translation_y: this.container.height + MARGIN * scale() + 4, duration: 220,
                              mode: Clutter.AnimationMode.EASE_IN_QUAD });
    }

    _show() {
        if (!this._hidden) return;
        this._hidden = false;
        this.container.ease({ translation_y: 0, duration: 200, mode: Clutter.AnimationMode.EASE_OUT_QUAD });
    }

    // -------- style
    _applyStyle() {
        let dark = this.style === "dark";
        if (this.style === "auto") {
            const name = this._themeSettings ? this._themeSettings.get_string("name") : "";
            dark = /dark/i.test(name);
        }
        [this.container, this.label].forEach(a => {
            if (!a) return;
            if (dark) a.add_style_class_name("monterra-dock-dark"); else a.remove_style_class_name("monterra-dock-dark");
        });
    }

    destroy() {
        this._signals.forEach(([o, id]) => { try { o.disconnect(id); } catch (e) {} });
        if (this._focusWin) this._focusIds.forEach(id => { try { this._focusWin.disconnect(id); } catch (e) {} });
        this._focusWin = null;
        this._signals = [];
        if (this._dragMonitor) DND.removeDragMonitor(this._dragMonitor);
        if (this._laterId) Meta.later_remove(this._laterId);
        [this._rebuildId, this._overlapId, this._watchId].forEach(id => { if (id) GLib.source_remove(id); });
        this.slots.forEach(sl => { if (sl.item) sl.item.destroy(); if (sl.sep) sl.sep.destroy(); });
        this.slots = [];
        Main.layoutManager.removeChrome(this.container);
        Main.layoutManager.removeChrome(this.strut);
        Main.layoutManager.removeChrome(this.hotEdge);
        this.container.destroy();
        this.strut.destroy();
        this.hotEdge.destroy();
        this.label.destroy();
        this.container = null;
        if (this.settings) this.settings.finalize();
    }
}

// ---------------------------------------------------------------- extension entry points
function init(metadata) {}

function enable() {
    dock = new MonterraDock();
}

function disable() {
    if (dock) {
        dock.destroy();
        dock = null;
    }
}
