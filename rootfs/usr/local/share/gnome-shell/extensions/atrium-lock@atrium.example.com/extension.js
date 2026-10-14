// 2026-10-13 atrium: lock the gadgets - nothing to open or change by a click (user: "lock on this").
//  - Freon (temperature in the top bar): its button stops reacting -> no menu with "Sensor Settings".
//  - Desktop Widgets (disk usage on the desktop): widgets stop reacting -> no right-click / long-press
//    menu with "Lock Position", "Always on Top", "Desktop Widgets Settings".
// Executor (CPU/GPU/VIDEO, LAN/Wi-Fi) is locked by its own setting click-on-output-active=false.
// 2026-10-14: GJS OSK (on-screen keyboard) adds a "Screen Keyboard" toggle to the quick settings menu; it
// only turns the keyboard button in the top bar on and off. The toggle is hidden, the button stays
// (indicator-enabled=true) - user: "the option is not needed, the keyboard is".
// 2026-10-14: the keyboard button goes right before the temperature (user: "keyboard left of the
// temperature"). GJS OSK re-creates the button on every monitor change (also on atrium-hdr on/off), so
// the order is checked again whenever something is added to the top bar.
// /usr/local/share/gnome-shell/extensions/atrium-lock@atrium.example.com/
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const AZCLOCK = 'azclock@azclock.gitlab.com';
const GJSOSK = 'gjsosk@vishram1123.com';
const OSK_BUTTON = 'GJS OSK Indicator';

function setReactive(actor, on) {
    actor.reactive = on;
    actor.can_focus = on;
    actor.track_hover = on;
}

export default class AtriumLock extends Extension {
    enable() {
        // re-apply whenever an extension is (re)enabled - Freon / Desktop Widgets rebuild their actors then
        this._stateId = Main.extensionManager.connect('extension-state-changed', () => this._queue());
        if (Main.layoutManager._startingUp)
            this._startupId = Main.layoutManager.connect('startup-complete', () => this._queue());
        // a button (re)added to the top bar may change the order
        this._boxIds = [Main.panel._leftBox, Main.panel._centerBox, Main.panel._rightBox].map(box =>
            [box, box.connect('child-added', () => this._queue())]);
        this._queue();
    }

    _queue() {
        if (this._idleId)
            return;
        this._idleId = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this._idleId = 0;
            this._apply();
            return GLib.SOURCE_REMOVE;
        });
    }

    _azclock() {
        return Main.extensionManager.lookup(AZCLOCK)?.stateObj ?? null;
    }

    _apply() {
        const freon = Main.panel.statusArea.freonMenu;
        if (freon) {
            freon.menu?.close();
            setReactive(freon, false);
        }

        const az = this._azclock();
        // Desktop Widgets re-creates its widgets when its widget list changes
        if (az?.settings && az.settings !== this._azSettings) {
            this._disconnectAz();
            this._azSettings = az.settings;
            this._azChangedId = this._azSettings.connect('changed::widgets', () => this._queue());
        }
        az?.widgets?.forEach(widget => {
            widget._menu?.close();
            widget.reactive = false;
        });

        // the quick settings grid skips hidden items
        this._oskToggles().forEach(item => {
            item.menu?.close();
            item.visible = false;
        });

        const kb = Main.panel.statusArea[OSK_BUTTON]?.container;
        const temp = freon?.container;
        if (kb && temp?.get_parent() && kb.get_next_sibling() !== temp) {
            kb.get_parent()?.remove_child(kb);
            temp.get_parent().insert_child_below(kb, temp);
        }
    }

    _oskToggles() {
        return Main.extensionManager.lookup(GJSOSK)?.stateObj?._quick_settings_indicator?.quickSettingsItems ?? [];
    }

    _disconnectAz() {
        if (this._azSettings && this._azChangedId)
            this._azSettings.disconnect(this._azChangedId);
        this._azSettings = null;
        this._azChangedId = 0;
    }

    disable() {
        if (this._idleId) {
            GLib.source_remove(this._idleId);
            this._idleId = 0;
        }
        if (this._stateId) {
            Main.extensionManager.disconnect(this._stateId);
            this._stateId = 0;
        }
        if (this._startupId) {
            Main.layoutManager.disconnect(this._startupId);
            this._startupId = 0;
        }
        this._boxIds?.forEach(([box, id]) => box.disconnect(id));
        this._boxIds = null;
        this._disconnectAz();

        const freon = Main.panel.statusArea.freonMenu;
        if (freon)
            setReactive(freon, true);
        this._azclock()?.widgets?.forEach(widget => {
            widget.reactive = true;
        });
        this._oskToggles().forEach(item => {
            item.visible = true;
        });
    }
}
