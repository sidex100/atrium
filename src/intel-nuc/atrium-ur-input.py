#!/usr/bin/python3
# atrium-ur-input - make Unified Remote clicks work on GNOME/Wayland.
# 2026-10-03: urserver writes a click as press AND release of the button in ONE input frame
# (no SYN between them). libinput sees "no change" and the click is lost (Windows tolerates it).
# This service grabs the virtual device of Unified Remote and re-emits everything through its own
# virtual device; when the same key/button changes twice inside one frame, the frame is split:
# press, SYN, 8 ms, release, SYN. Motion and everything else pass through unchanged.
import time

import evdev
from evdev import ecodes

SOURCE = "uinput-unifiedremote"
NAME = "atrium-ur-input"
GAP = 0.008


def find_source():
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except OSError:
            continue
        if dev.name == SOURCE:
            return dev
        dev.close()
    return None


def forward(dev):
    caps = dev.capabilities()
    caps.pop(ecodes.EV_SYN, None)
    if not caps.get(ecodes.EV_ABS):
        caps.pop(ecodes.EV_ABS, None)
    with evdev.UInput(caps, name=NAME) as ui:
        dev.grab()
        print(f"forwarding {dev.path} ({SOURCE}) -> {NAME}", flush=True)
        seen = set()
        for ev in dev.read_loop():
            if ev.type == ecodes.EV_SYN:
                if ev.code == ecodes.SYN_REPORT:
                    ui.syn()
                    seen.clear()
                continue
            if ev.type == ecodes.EV_KEY:
                if ev.code in seen:
                    ui.syn()
                    seen.clear()
                    time.sleep(GAP)
                seen.add(ev.code)
            ui.write(ev.type, ev.code, ev.value)


def main():
    waiting = False
    while True:
        dev = find_source()
        if dev is None:
            if not waiting:
                print(f"waiting for {SOURCE}", flush=True)
                waiting = True
            time.sleep(2)
            continue
        waiting = False
        try:
            forward(dev)
        except OSError as e:
            print(f"{SOURCE} gone: {e}", flush=True)
        finally:
            try:
                dev.close()
            except OSError:
                pass
        time.sleep(1)


if __name__ == "__main__":
    main()
