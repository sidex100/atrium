// 2026-10-13 atrium: lock the gadgets - nothing to open or change by a click (user: "lock on this").
//  - Freon (temperature in the top bar): its button stops reacting -> no menu with "Sensor Settings".
//  - Desktop Widgets (disk usage on the desktop): widgets stop reacting -> no right-click / long-press
//    menu with "Lock Position", "Always on Top", "Desktop Widgets Settings".
// Executor (CPU/GPU/VIDEO, LAN/Wi-Fi) is locked by its own setting click-on-output-active=false.
// The on-screen keyboard (GJS OSK) is left as is on purpose.
// /usr/local/share/gnome-shell/extensions/atrium-lock@atrium.example.com/
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const AZCLOCK = 'azclock@azclock.gitlab.com';

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
        this._disconnectAz();

        const freon = Main.panel.statusArea.freonMenu;
        if (freon)
            setReactive(freon, true);
        this._azclock()?.widgets?.forEach(widget => {
            widget.reactive = true;
        });
    }
}
