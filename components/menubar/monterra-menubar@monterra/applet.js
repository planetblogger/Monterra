// Monterra Menu Bar – classic menu bar for the Cinnamon panel:
// Monterra logo (system menu) followed by one drop-down menu per app category.
// GPL-3.0 – part of Monterra (https://github.com/planetblogger/Monterra)

const Applet = imports.ui.applet;
const PopupMenu = imports.ui.popupMenu;
const Settings = imports.ui.settings;
const Main = imports.ui.main;
const Util = imports.misc.util;
const GnomeSession = imports.misc.gnomeSession;
const ScreenSaver = imports.misc.screenSaver;
const { St, Clutter, Gio, GLib, Cinnamon, CMenu, Meta } = imports.gi;
const Gettext = imports.gettext;
const AppFavorites = imports.ui.appFavorites;

const UUID = "monterra-menubar@monterra";
Gettext.bindtextdomain(UUID, GLib.get_home_dir() + "/.local/share/locale");
function _(str) {
    const t = Gettext.dgettext(UUID, str);
    return t !== str ? t : Gettext.gettext(str);
}

const SYSTEM_CATEGORIES = ["administration", "preferences"];

const SEARCH_LIMIT = 10;

// ---------------------------------------------------------------- helpers

function decomp(s) {
    return (s || "").normalize("NFKD").replace(/\p{Grapheme_Extend}/gu, "").toLowerCase();
}

function haveCommand(cmd) {
    return GLib.find_program_in_path(cmd) !== null;
}

// all visible top-level categories with their apps, sorted like the Cinnamon menu
// (own menu tree, so changes from the menu editor show up right away)
function loadCategories(tree) {
    const appsys = Cinnamon.AppSystem.get_default();
    const root = tree.get_root_directory();
    if (!root) return [];
    const result = [];
    const iter = root.iter();
    let type;
    while ((type = iter.next()) !== CMenu.TreeItemType.INVALID) {
        if (type !== CMenu.TreeItemType.DIRECTORY) continue;
        const dir = iter.get_directory();
        if (dir.get_is_nodisplay()) continue;
        const apps = [];
        collect(dir, apps, appsys);
        if (dir.get_menu_id() === "wine-wine" && apps.length === 0) continue;
        const seen = new Set();
        const unique = apps.filter(a => !seen.has(a.get_id()) && seen.add(a.get_id()));
        unique.sort((a, b) => a.get_name().localeCompare(b.get_name(), undefined, { sensitivity: "base", ignorePunctuation: true }));
        result.push({ id: dir.get_menu_id().toLowerCase(), menuId: dir.get_menu_id(), name: dir.get_name(), apps: unique });
    }
    const bottom = ["development", "other", "preferences", "administration"];
    result.sort((a, b) => {
        const ia = bottom.indexOf(a.id), ib = bottom.indexOf(b.id);
        if (ia !== ib) return ia - ib;
        return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    });
    return result;
}

function collect(dir, apps, appsys) {
    const iter = dir.iter();
    let type;
    while ((type = iter.next()) !== CMenu.TreeItemType.INVALID) {
        if (type === CMenu.TreeItemType.ENTRY) {
            const app = appsys.lookup_app(iter.get_entry().get_desktop_file_id());
            if (app && !app.get_nodisplay()) apps.push(app);
        } else if (type === CMenu.TreeItemType.DIRECTORY) {
            collect(iter.get_directory(), apps, appsys);
        }
    }
}

// ---------------------------------------------------------------- menu items

class AppMenuItem extends PopupMenu.PopupBaseMenuItem {
    constructor(app, iconSize, applet, container) {
        super();
        this.app = app;
        this._applet = applet;
        this.container = container;     // section / submenu the item lives in
        this.actor.add_style_class_name("monterra-menubar-app");
        if (iconSize) {
            this._icon = app.create_icon_texture(iconSize);
            this.addActor(this._icon, { span: 0 });
        }
        this.label = new St.Label({ text: app.get_name(), y_align: Clutter.ActorAlign.CENTER });
        this.addActor(this.label);
    }

    // right mouse button: small menu with “Properties” and “Add to Dock”
    _onButtonReleaseEvent(actor, event) {
        if (event.get_button() === 3) {
            this._applet._openAppContext(this);
            return Clutter.EVENT_STOP;
        }
        return super._onButtonReleaseEvent(actor, event);
    }

    _onKeyPressEvent(actor, event) {
        const sym = event.get_key_symbol();
        if (sym === Clutter.KEY_Menu) { this._applet._openAppContext(this); return Clutter.EVENT_STOP; }
        return super._onKeyPressEvent(actor, event);
    }

    activate(event) {
        this.app.open_new_window(-1);
        super.activate(event);
    }
}

// menu entry that reacts to the left mouse button only
class LeftClickItem extends PopupMenu.PopupMenuItem {
    _onButtonReleaseEvent(actor, event) {
        if (event.get_button() !== 1) return Clutter.EVENT_STOP;
        return super._onButtonReleaseEvent(actor, event);
    }
}

// inset, rounded highlight like the rest of Monterra (instead of edge-to-edge)
function roundItem(item) {
    if (!item || !item.actor || item instanceof PopupMenu.PopupSeparatorMenuItem) return;
    item.actor.set_style("border-radius: 6px;");
}

class BarMenu extends PopupMenu.PopupMenu {
    constructor(sourceActor, orientation) {
        super(sourceActor, orientation);
        this.actor.add_style_class_name("monterra-menubar-menu");
        this.box.set_style("padding-left: 6px; padding-right: 6px;");
        Main.uiGroup.add_actor(this.actor);
        this.actor.hide();
    }
}

// ---------------------------------------------------------------- applet

class MonterraMenuBar extends Applet.Applet {
    constructor(metadata, orientation, panelHeight, instanceId) {
        super(orientation, panelHeight, instanceId);
        this.metadata = metadata;
        this._orient = orientation;

        this.actor.remove_style_class_name("applet-box");
        this.actor.add_style_class_name("monterra-menubar");
        this.actor.track_hover = false;
        this.actor.set_style("padding: 0; spacing: 0;");

        this.settings = new Settings.AppletSettings(this, UUID, instanceId);
        this.settings.bind("open-on-hover", "openOnHover");
        this.settings.bind("hover-delay", "hoverDelay");
        this.settings.bind("close-on-leave", "closeOnLeave");
        this.settings.bind("show-system-categories", "showSystemCategories", () => this._queueRebuild());
        this.settings.bind("show-icons", "showIcons", () => this._queueRebuild());
        this.settings.bind("show-search", "showSearch", () => this._queueRebuild());
        this.settings.bind("overlay-key", "overlayKey", () => this._updateKeybinding());

        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this._session = new GnomeSession.SessionManager();
        this._screenSaver = new ScreenSaver.ScreenSaverProxy();

        this._items = [];          // { button, menu }
        this._hoverTimer = 0;
        this._leaveTimer = 0;
        this._watchTimer = 0;
        this._rebuildId = 0;
        this._openedByHover = false;

        this._appsysId = Cinnamon.AppSystem.get_default().connect("installed-changed", () => this._queueRebuild());
        this._tree = CMenu.Tree.new("cinnamon-applications.menu", CMenu.TreeFlags.SHOW_EMPTY);
        this._treeId = this._tree.connect("changed", () => this._queueRebuild());
        try { this._tree.load_sync(); } catch (e) { global.logError("Monterra Menu Bar: " + e); }
        this._ifaceSettings = new Gio.Settings({ schema_id: "org.cinnamon.theme" });
        this._themeId = this._ifaceSettings.connect("changed::name", () => this._queueRebuild());

        this._rebuild();
        this._updateKeybinding();
    }

    // ------------------------------------------------------------ style

    _isDark() {
        const name = (this._ifaceSettings.get_string("name") || "").toLowerCase();
        return name.includes("dark");
    }

    _buttonStyle(active) {
        const dark = this._isDark();
        const bg = active ? (dark ? "rgba(255,255,255,0.16)" : "rgba(0,0,0,0.09)") : "transparent";
        const scale = global.ui_scale || 1;
        const h = Math.max(18, Math.round((this._panelHeight || 28) / scale) - 8);
        return `padding: 0 9px; margin: 0 1px; border-radius: 6px; height: ${h}px; background-color: ${bg};` +
               (active ? "" : "");
    }

    _setActive(button, active) {
        button.set_style(this._buttonStyle(active));
    }

    // ------------------------------------------------------------ building

    _queueRebuild() {
        if (this._rebuildId) return;
        this._rebuildId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 400, () => {
            this._rebuildId = 0;
            this._rebuild();
            return GLib.SOURCE_REMOVE;
        });
    }

    _clear() {
        this._closeContext();
        for (const it of this._items) {
            if (it.menu.isOpen) it.menu.close(false);
            this.menuManager.removeMenu(it.menu);
            it.menu.destroy();
            it.button.destroy();
        }
        this._items = [];
        this._logoMenu = null;
    }

    _rebuild() {
        this._closeAll();
        this._clear();
        try { this._tree.load_sync(); } catch (e) { /* keep the last tree */ }
        const all = loadCategories(this._tree);
        const cats = all.filter(c => c.apps.length > 0);
        const systemCats = cats.filter(c => SYSTEM_CATEGORIES.includes(c.id));
        const barCats = this.showSystemCategories ? cats : cats.filter(c => !SYSTEM_CATEGORIES.includes(c.id));
        this._allApps = [];
        const seen = new Set();
        for (const c of cats) for (const a of c.apps) {
            if (!seen.has(a.get_id())) { seen.add(a.get_id()); this._allApps.push(a); }
        }

        // logo
        const logo = new St.Icon({
            gicon: Gio.FileIcon.new(Gio.File.new_for_path(this.metadata.path + "/icons/monterra-logo-symbolic.svg")),
            icon_type: St.IconType.SYMBOLIC,
            icon_size: 16,
            style_class: "applet-icon",
        });
        const logoBtn = this._makeButton(logo, _("Monterra"));
        const logoMenu = this._addMenu(logoBtn);
        this._logoMenu = logoMenu;
        this._fillLogoMenu(logoMenu, this.showSystemCategories ? [] : systemCats);

        // categories
        for (const c of barCats) {
            const label = new St.Label({ text: c.name, y_align: Clutter.ActorAlign.CENTER });
            const btn = this._makeButton(label, c.name);
            const menu = this._addMenu(btn);
            this._fillAppMenu(menu, c.apps);
        }
    }

    _makeButton(child, accessibleName) {
        const button = new St.Bin({
            reactive: true, can_focus: true, track_hover: true,
            x_fill: false, y_fill: false,
            y_align: St.Align.MIDDLE,
            child: child,
            accessible_name: accessibleName,
            style_class: "monterra-menubar-item",
        });
        button.set_style(this._buttonStyle(false));
        this.actor.add(button, { y_align: St.Align.MIDDLE, y_fill: false });
        return button;
    }

    _addMenu(button) {
        const menu = new BarMenu(button, this._orient);
        this.menuManager.addMenu(menu);
        const item = { button, menu };
        this._items.push(item);

        // round every item that ends up in this menu (also search results and submenus)
        const origAdd = menu.addMenuItem.bind(menu);
        menu.addMenuItem = (it, pos) => { roundItem(it); return origAdd(it, pos); };
        menu.connect("open-state-changed", (m, open) => {
            this._setActive(button, open);
            if (!open) this._closeContext();
            if (open) this._startWatch(); else if (!this._anyOpen()) this._stopWatch();
            if (!open && menu === this._logoMenu && this._searchEntry) this._searchEntry.set_text("");
        });
        menu.actor.connect("key-press-event", (a, ev) => this._onMenuKey(item, ev));

        button.connect("button-press-event", (a, ev) => {
            if (ev.get_button() !== 1) return Clutter.EVENT_PROPAGATE;
            this._cancelHover();
            this._openedByHover = false;
            if (menu.isOpen) menu.close(true);
            else { this._closeAll(); menu.open(true); }
            return Clutter.EVENT_STOP;
        });
        button.connect("enter-event", () => {
            if (!this.openOnHover || this._anyOpen() || Main.overview && Main.overview.visible) return Clutter.EVENT_PROPAGATE;
            this._cancelHover();
            this._hoverTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, Math.max(0, this.hoverDelay), () => {
                this._hoverTimer = 0;
                if (!this._anyOpen() && button.hover) { this._openedByHover = true; menu.open(true); }
                return GLib.SOURCE_REMOVE;
            });
            return Clutter.EVENT_PROPAGATE;
        });
        button.connect("leave-event", () => { this._cancelHover(); return Clutter.EVENT_PROPAGATE; });
        return menu;
    }

    _section() {
        const s = new PopupMenu.PopupMenuSection();
        const origAdd = s.addMenuItem.bind(s);
        s.addMenuItem = (it, pos) => { roundItem(it); return origAdd(it, pos); };
        return s;
    }

    _fillAppMenu(menu, apps) {
        const section = this._section();
        const size = this.showIcons ? 20 : 0;
        for (const app of apps)
            section.addMenuItem(new AppMenuItem(app, size, this, section));
        this._addScrolling(menu, section);
    }

    // put a section into a scroll view so long categories fit on the screen
    _addScrolling(menu, section) {
        menu.addMenuItem(section);
        const monitor = Main.layoutManager.primaryMonitor;
        const scale = global.ui_scale || 1;
        const maxH = Math.round((monitor.height * 0.8) / scale);
        // only long lists need a scroll view (it costs a little room on the right)
        const rowH = this.showIcons ? 30 : 26;
        if (section._getMenuItems().length * rowH < maxH - 40) return null;
        const scroll = new St.ScrollView({
            hscrollbar_policy: St.PolicyType.NEVER,
            vscrollbar_policy: St.PolicyType.AUTOMATIC,
            style: `max-height: ${maxH}px;`,
            style_class: "vfade",
        });
        menu.box.remove_actor(section.actor);
        scroll.add_actor(section.actor);
        menu.box.add_actor(scroll);
        return scroll;
    }

    _fillLogoMenu(menu, systemCats) {
        // search
        this._searchEntry = null;
        if (this.showSearch) {
            const searchItem = new PopupMenu.PopupBaseMenuItem({ reactive: false, activate: false });
            this._searchEntry = new St.Entry({
                hint_text: _("Search apps…"),
                can_focus: true, track_hover: true,
                x_expand: true,
                style: "min-width: 220px;",
            });
            searchItem.addActor(this._searchEntry, { expand: true, span: -1 });
            menu.addMenuItem(searchItem);
            this._results = this._section();
            menu.addMenuItem(this._results);
            this._searchEntry.clutter_text.connect("text-changed", () => this._onSearch());
            this._searchEntry.clutter_text.connect("key-press-event", (a, ev) => {
                const sym = ev.get_key_symbol();
                if (sym === Clutter.KEY_Return || sym === Clutter.KEY_KP_Enter) {
                    const first = this._results._getMenuItems()[0];
                    if (first) first.activate(ev);
                    return Clutter.EVENT_STOP;
                }
                if (sym === Clutter.KEY_Down) {
                    const first = this._results._getMenuItems()[0];
                    if (first) first.actor.grab_key_focus();
                    return Clutter.EVENT_STOP;
                }
                return Clutter.EVENT_PROPAGATE;
            });
        }

        this._systemSection = this._section();
        menu.addMenuItem(this._systemSection);
        const s = this._systemSection;
        const add = (label, cb) => { const it = new PopupMenu.PopupMenuItem(label); it.connect("activate", cb); s.addMenuItem(it); return it; };
        const sep = () => s.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        if (this._searchEntry) sep();
        // Linux Mint 22 shows system information in “System Reports” (mintreport);
        // older versions have it as a module of the System Settings
        add(_("About This Computer"), () => Util.spawnCommandLine(haveCommand("mintreport") ? "mintreport" : "cinnamon-settings info"));
        sep();
        add(_("System Settings…"), () => Util.spawnCommandLine("cinnamon-settings"));
        if (haveCommand("mintinstall")) add(_("Software Manager…"), () => Util.spawnCommandLine("mintinstall"));
        if (haveCommand("mintupdate")) add(_("Update Manager…"), () => Util.spawnCommandLine("mintupdate"));
        // own section: categories (move apps, create, rename, delete) are managed in Cinnamon's
        // menu editor; "Preferences" is left out – the System Settings window shows the same tools
        sep();
        if (haveCommand("cinnamon-menu-editor")) add(_("Edit Menu…"), () => Util.spawnCommandLine("cinnamon-menu-editor"));
        for (const c of systemCats.filter(c => c.id !== "preferences")) {
            const sub = new PopupMenu.PopupSubMenuMenuItem(c.name);
            for (const app of c.apps) {
                const it = new AppMenuItem(app, this.showIcons ? 16 : 0, this, sub.menu);
                roundItem(it);
                sub.menu.addMenuItem(it);
            }
            s.addMenuItem(sub);
        }
        if (haveCommand("gnome-system-monitor")) {
            sep();
            add(_("Force Quit…"), () => Util.spawnCommandLine("gnome-system-monitor -p"));
        }
        sep();
        add(_("Sleep"), () => Util.spawnCommandLine("systemctl suspend"));
        add(_("Restart…"), () => Util.spawnCommandLine("cinnamon-session-quit --reboot"));
        add(_("Shut Down…"), () => this._session.ShutdownRemote());
        sep();
        add(_("Lock Screen"), () => this._lock());
        const user = GLib.get_real_name() && GLib.get_real_name() !== "Unknown" ? GLib.get_real_name() : GLib.get_user_name();
        add(_("Log Out %s…").replace("%s", user), () => this._session.LogoutRemote(0));
    }

    // Right mouse button (or the menu key) on an app: a few actions appear directly below it,
    // inside the same menu. No separate pop-up menu – that is the most robust way on all
    // Cinnamon versions (a nested pop-up could take Cinnamon down on 6.6).
    _openAppContext(item) {
        const same = this._ctx && this._ctx.owner === item;
        this._closeContext();
        if (same || !item.container) return;
        const app = item.app;
        const ctx = this._section();
        ctx.owner = item;
        const indent = item._icon ? 46 : 22;     // first guess, corrected below once laid out
        const add = (label, cb) => {
            const it = new LeftClickItem(label);
            it.connect("activate", () => { this._closeContext(); cb(); });
            ctx.addMenuItem(it);
            it._indent = indent;
            it.actor.set_style(`border-radius: 6px; padding-left: ${indent}px; font-size: 0.92em;`);
            return it;
        };
        const id = app.get_id();
        const info = app.get_app_info();
        const file = info && info.get_filename ? info.get_filename() : null;
            const favs = AppFavorites.getAppFavorites();
            const dock = global.settings.get_strv("enabled-extensions").some(e => e.startsWith("monterra-dock@monterra"));
            if (favs.isFavorite(id))
                add(dock ? _("Remove from Dock") : _("Remove from Favorites"), () => favs.removeFavorite(id));
            else
                add(dock ? _("Add to Dock") : _("Add to Favorites"), () => favs.addFavorite(id));
            if (file && haveCommand("cinnamon-desktop-editor"))
                add(_("Properties…"), () => Util.spawnCommandLine("cinnamon-desktop-editor -mlauncher -o " + GLib.shell_quote(file)));
        item.container.addMenuItem(ctx);
        const box = ctx.actor.get_parent();
        if (box && box === item.actor.get_parent()) box.set_child_above_sibling(ctx.actor, item.actor);
        this._ctx = ctx;
        // line the entries up exactly with the app name above them (measured once both are laid out)
        ctx.actor.opacity = 0;
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 20, () => {
            if (this._ctx !== ctx) return GLib.SOURCE_REMOVE;
            try {
                const scale = global.ui_scale || 1;
                const x = a => a.get_transformed_position()[0] / scale;
                const want = x(item.label) - x(item.actor);              // name offset in the app row
                for (const it of ctx._getMenuItems()) {
                    if (!it.label) continue;
                    const extra = (x(it.label) - x(it.actor)) - it._indent; // what the theme adds before the text
                    const pad = Math.max(0, Math.round(want - extra));
                    it._indent = pad;
                    it.actor.set_style(`border-radius: 6px; padding-left: ${pad}px; font-size: 0.92em;`);
                }
            } catch (e) { /* keep the first guess */ }
            ctx.actor.opacity = 255;
            return GLib.SOURCE_REMOVE;
        });
        const first = ctx._getMenuItems()[0];
        if (first) first.actor.grab_key_focus();
    }

    _closeContext() {
        if (!this._ctx) return;
        const ctx = this._ctx;
        this._ctx = null;
        // keep the keyboard focus inside the menu – if the focused entry simply vanished,
        // Cinnamon would take that as “focus left the menu” and close it
        try {
            const focus = global.stage.key_focus;
            if (focus && ctx.actor.contains(focus) && ctx.owner && ctx.owner.actor.mapped)
                ctx.owner.actor.grab_key_focus();
        } catch (e) { /* nothing */ }
        try { ctx.destroy(); } catch (e) { /* already gone */ }
    }

    _lock() {
        const ss = new Gio.Settings({ schema_id: "org.cinnamon.desktop.screensaver" });
        if (haveCommand("cinnamon-screensaver-command")) {
            if (ss.get_boolean("ask-for-away-message")) Util.spawnCommandLine("cinnamon-screensaver-lock-dialog");
            else Util.spawnCommandLine("cinnamon-screensaver-command --lock");
        } else {
            this._screenSaver.LockRemote("");
        }
    }

    _onSearch() {
        const q = decomp(this._searchEntry.get_text().trim());
        this._closeContext();
        this._results.removeAll();
        this._systemSection.actor.visible = q.length === 0;
        if (!q) return;
        const hits = [];
        for (const app of this._allApps) {
            const name = decomp(app.get_name());
            let score = -1;
            if (name.startsWith(q)) score = 0;
            else if (name.includes(q)) score = 1;
            else if (decomp(app.get_keywords ? app.get_keywords() : "").includes(q)) score = 2;
            else if (decomp(app.get_description()).includes(q)) score = 3;
            if (score >= 0) hits.push([score, app]);
        }
        hits.sort((a, b) => a[0] - b[0] || a[1].get_name().localeCompare(b[1].get_name()));
        if (hits.length === 0) {
            const none = new PopupMenu.PopupMenuItem(_("No apps found"), { reactive: false });
            this._results.addMenuItem(none);
            return;
        }
        for (const [, app] of hits.slice(0, SEARCH_LIMIT))
            this._results.addMenuItem(new AppMenuItem(app, 20, this, this._results));
    }

    // ------------------------------------------------------------ open / close

    _anyOpen() {
        return this._items.some(it => it.menu.isOpen);
    }

    _closeAll() {
        for (const it of this._items) if (it.menu.isOpen) it.menu.close(false);
    }

    _cancelHover() {
        if (this._hoverTimer) { GLib.source_remove(this._hoverTimer); this._hoverTimer = 0; }
    }

    // Left/Right switch to the neighbouring menu, like a classic menu bar
    _onMenuKey(item, ev) {
        const sym = ev.get_key_symbol();
        if (sym !== Clutter.KEY_Left && sym !== Clutter.KEY_Right) return Clutter.EVENT_PROPAGATE;
        const focus = global.stage.key_focus;
        if (focus && focus instanceof Clutter.Text) return Clutter.EVENT_PROPAGATE;   // cursor in the search field
        const i = this._items.indexOf(item);
        const n = this._items.length;
        const next = this._items[(i + (sym === Clutter.KEY_Right ? 1 : n - 1)) % n];
        this.menuManager._changeMenu(next.menu);
        next.menu.actor.navigate_focus(null, St.DirectionType.TAB_FORWARD, false);
        return Clutter.EVENT_STOP;
    }

    // When a menu was opened by hovering, close it once the pointer has left
    // the menu bar and the open menu for a short moment.
    _startWatch() {
        if (this._watchTimer) return;
        this._outside = 0;
        this._watchTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
            if (!this._anyOpen()) { this._watchTimer = 0; return GLib.SOURCE_REMOVE; }
            if (!this.openOnHover || !this.closeOnLeave || !this._openedByHover) return GLib.SOURCE_CONTINUE;
            if (this._searchEntry && this._searchEntry.get_text()) return GLib.SOURCE_CONTINUE;
            const [x, y] = global.get_pointer();
            const inside = this._contains(this.actor, x, y) ||
                           this._items.some(it => it.menu.isOpen && this._contains(it.menu.actor, x, y, 6));
            this._outside = inside ? 0 : this._outside + 1;
            if (this._outside >= 5) { this._closeAll(); this._watchTimer = 0; return GLib.SOURCE_REMOVE; }
            return GLib.SOURCE_CONTINUE;
        });
    }

    _stopWatch() {
        if (this._watchTimer) { GLib.source_remove(this._watchTimer); this._watchTimer = 0; }
    }

    _contains(actor, x, y, pad = 0) {
        if (!actor || !actor.visible) return false;
        const [ax, ay] = actor.get_transformed_position();
        const [w, h] = actor.get_transformed_size();
        return x >= ax - pad && x <= ax + w + pad && y >= ay - pad && y <= ay + h + pad;
    }

    // ------------------------------------------------------------ keyboard shortcut (Super)

    _updateKeybinding() {
        Main.keybindingManager.addHotKey("overlay-key-" + this.instance_id, this.overlayKey, () => {
            if (!this._logoMenu) return;
            if (this._logoMenu.isOpen) { this._logoMenu.close(true); return; }
            this._closeAll();
            this._openedByHover = false;
            this._logoMenu.open(true);
            if (this._searchEntry) this._searchEntry.grab_key_focus();
        });
    }

    // ------------------------------------------------------------ applet API

    on_applet_clicked() {}

    on_panel_height_changed() {
        this._queueRebuild();
    }

    on_orientation_changed(orientation) {
        this._orient = orientation;
        this._queueRebuild();
    }

    on_applet_removed_from_panel() {
        Main.keybindingManager.removeHotKey("overlay-key-" + this.instance_id);
        this._cancelHover();
        this._stopWatch();
        if (this._rebuildId) GLib.source_remove(this._rebuildId);
        Cinnamon.AppSystem.get_default().disconnect(this._appsysId);
        try { this._tree.disconnect(this._treeId); } catch (e) {}
        this._ifaceSettings.disconnect(this._themeId);
        this._clear();
        // Bei „Neu laden“ meldet sich die neue Instanz mit derselben ID an, bevor die alte entfernt
        // wird – dann darf die alte die Einstellungen nicht abmelden (sonst erreicht der Dialog nichts mehr).
        try {
            const reg = Main.settingsManager.uuids[UUID];
            if (reg && reg[this.instance_id] === this.settings) this.settings.finalize();
            else { this.settings.unbindAll && this.settings.unbindAll(); }
        } catch (e) { /* nichts */ }
    }
}

function main(metadata, orientation, panelHeight, instanceId) {
    return new MonterraMenuBar(metadata, orientation, panelHeight, instanceId);
}
