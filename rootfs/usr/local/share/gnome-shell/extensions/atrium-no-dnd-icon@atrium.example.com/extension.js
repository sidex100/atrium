// 2026-10-06 atrium: hide the Do Not Disturb bell in the top bar.
// Notifications are off for good on the TV box (org.gnome.desktop.notifications show-banners false);
// GNOME 50 then always shows the bell and has no setting to hide it.
// /usr/local/share/gnome-shell/extensions/atrium-no-dnd-icon@atrium.example.com/
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class AtriumNoDndIcon extends Extension {
    enable() {
        this._qs = Main.panel.statusArea.quickSettings;
        if (this._qs._doNotDisturb) {
            this._hide(this._qs._doNotDisturb);
            return;
        }
        // quick settings are still being set up at login: wait for its indicators
        this._addedId = this._qs._indicators.connect('child-added', () => {
            if (!this._qs._doNotDisturb)
                return;
            this._qs._indicators.disconnect(this._addedId);
            this._addedId = 0;
            this._hide(this._qs._doNotDisturb);
        });
    }

    _hide(dnd) {
        this._dnd = dnd;
        this._icon = dnd._indicator;
        this._visibleId = this._icon.connect('notify::visible', () => {
            if (this._icon.visible)
                this._icon.hide();
        });
        this._icon.hide();
    }

    disable() {
        if (this._addedId) {
            this._qs._indicators.disconnect(this._addedId);
            this._addedId = 0;
        }
        if (this._icon) {
            this._icon.disconnect(this._visibleId);
            this._icon.visible = this._dnd.quickSettingsItems[0].checked;
        }
        this._qs = this._dnd = this._icon = null;
    }
}
