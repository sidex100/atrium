// 2026-10-13 atrium: show the brightness in percent (user: "when changing it, see exactly how many percent").
// With HDR on, the brightness slider in quick settings sets mutter's software luminance for the TV:
// range 10..210, 100 = reference white (45 % of the slider). GNOME shows no number; this adds it
//  - next to the brightness slider in quick settings,
//  - on the on-screen bar that pops up at the bottom of the screen while it is being changed.
// /usr/local/share/gnome-shell/extensions/atrium-brightness-value@atrium.example.com/
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

function backlight() {
    for (const lm of global.backend.get_monitor_manager().get_logical_monitors()) {
        for (const m of lm.get_monitors()) {
            if (m.get_backlight() && m.is_active())
                return m.get_backlight();
        }
    }
    return null;
}

function percent(value) {
    const b = backlight();
    const min = b?.brightnessMin ?? 0;
    const max = b?.brightnessMax ?? 100;
    return `${Math.round(min + (max - min) * value)} %`;
}

export default class AtriumBrightnessValue extends Extension {
    enable() {
        this._manager = Main.brightnessManager;

        // the bar at the bottom of the screen: same as GNOME's _showOSD, plus the label
        this._manager._showOSD = scales => {
            const levels = {};
            let text = null;
            for (const scale of scales) {
                levels[scale.monitor.get_number()] = {level: scale.value};
                text ??= percent(scale.value);
            }
            Main.osdWindowManager.show(
                Gio.Icon.new_for_string('display-brightness-symbolic'), text, levels);
        };

        // the label right of the slider in quick settings
        this._label = new St.Label({
            y_align: Clutter.ActorAlign.CENTER,
            style: 'margin: 0 6px; min-width: 3.5em; text-align: right;',
        });
        this._qs = Main.panel.statusArea.quickSettings;
        if (!this._attach()) {
            // quick settings are still being set up at login: wait for its indicators
            this._addedId = this._qs._indicators.connect('child-added', () => {
                if (!this._attach())
                    return;
                this._qs._indicators.disconnect(this._addedId);
                this._addedId = 0;
            });
        }

        this._changedId = this._manager.connect('changed', () => this._hookScale());
        this._hookScale();
    }

    _attach() {
        const item = this._qs._brightness?.quickSettingsItems?.[0];
        if (!item)
            return false;
        const sliderBin = item.slider.get_parent();
        sliderBin.get_parent().insert_child_above(this._label, sliderBin);
        this._update();
        return true;
    }

    _hookScale() {
        if (this._scale && this._scaleId)
            this._scale.disconnect(this._scaleId);
        this._scale = this._manager.globalScale;
        this._scaleId = this._scale
            ? this._scale.connect('notify::value', () => this._update()) : 0;
        this._update();
    }

    _update() {
        const scale = this._manager.globalScale;
        this._label.text = scale ? percent(scale.value) : '';
    }

    disable() {
        delete this._manager._showOSD;  // back to GNOME's own method
        if (this._addedId) {
            this._qs._indicators.disconnect(this._addedId);
            this._addedId = 0;
        }
        if (this._changedId) {
            this._manager.disconnect(this._changedId);
            this._changedId = 0;
        }
        if (this._scale && this._scaleId)
            this._scale.disconnect(this._scaleId);
        this._scale = null;
        this._scaleId = 0;
        this._label?.destroy();
        this._label = null;
        this._qs = this._manager = null;
    }
}
