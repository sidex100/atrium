# Known problems and fixes

[Русская версия](../ru/problems.md) · [Install](install.md) · [Hardware](hardware.md) · [Updates](updates.md)

Everything we have run into, with the cause and the fix.

## Night freezes

**What happened.**

- On 12 October 2026, at night, with the screen off, the box locked up completely: no network, no SSH, no
  console, for about 6 hours.
- The journal stopped in the middle of ordinary messages.
- No kernel errors, no overheating, no memory or disk errors.
- A similar case happened on 7 October, but an external cause is possible there.

**Suspects**, all equally likely:
- deep sleep of the graphics core (GFXOFF) while the output stays off for a long time;
- output over DisplayPort with DSC while the screen is blanked (no longer relevant since 13.10: the TV is on
  the box's own HDMI, with no DisplayPort and no DSC);
- MT7921 Wi-Fi in deep-sleep mode: the last line in the journal was the start of a Wi-Fi scan.

Memory was tested without a reboot: `stressapptest` for 10 minutes on 15 GB, no errors.

**What is in place now** (install steps 12 and 16):
- GFXOFF is disabled;
- a 60 s hardware watchdog;
- panic on a CPU lockup and on a kernel error;
- the panic report is written to pstore.

**After the next freeze**, only look:

```bash
journalctl -k -b | grep -i "reset reason"
ls -la /var/lib/systemd/pstore /sys/fs/pstore
journalctl -b -1 -n 50 --no-pager
nvme smart-log /dev/nvme0 | grep -i unsafe; nvme smart-log /dev/nvme1 | grep -i unsafe
```

How to read the reset reason: "watchdog" means the kernel or the CPU itself stopped (a driver or the platform).
`0xCF9` or ACPI mean a reset from outside or by the button. If there are files in `pstore`, they hold the
kernel's last words.

## No signal after turning off the TV or a long screen blank

This is a problem of active DisplayPort → HDMI 2.1 cables. Since 13.10 we have none: the TV is connected to
the box's own HDMI 2.1 ([tv-output.md](tv-output.md)).

**Cause.** When it blanks the screen, the driver puts the chip in the cable to sleep (DPCD `0x600 = 02`),
and the chip does not always wake up:
- the Chrontel CH7218 with the factory firmware did not bring HDMI back after the TV was turned off or the
  screen was blanked;
- with firmware 07.00.54 it came back after a short blank, but not after a night;
- from the box's side everything was alive meanwhile: the frame, the DisplayPort link, the TV's EDID;
- both active cables got warm while idle;
- the Synaptics VMM7100 adapter also flickered and lost the signal for 0.5–1 s, in games and on the
  desktop.

**Fix:** the box's own HDMI 2.1 and a passive 48G cable ([tv-output.md](tv-output.md)).

**If you stay on an active cable:** unplug and replug the cable, or turn the output off and on again
through mutter:

```bash
G="runuser -u view -- env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus gdbus call --session --dest org.gnome.Mutter.DisplayConfig --object-path /org/gnome/Mutter/DisplayConfig --method org.freedesktop.DBus.Properties.Set org.gnome.Mutter.DisplayConfig PowerSaveMode"
$G "<int32 3>"; sleep 3; $G "<int32 0>"
```

## RDP does not connect when the screen is blanked

**Cause.** When GNOME blanks the screen on its own, it raises the screen "shield". Under the shield, screen
sharing is not allowed: the journal shows `Session creation inhibited`, and the client silently drops even
though the password was accepted. **Fix:** the TV user has `idle-delay 0` (GNOME does not blank the screen on
its own), and `atrium-screensaver` turns the screen off through `PowerSaveMode` without the shield. To remove
the shield once:

```bash
runuser -u view -- env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus gdbus call --session --dest org.gnome.ScreenSaver --object-path /org/gnome/ScreenSaver --method org.gnome.ScreenSaver.SetActive false
```

## GNOME crashed with RDP connected

**Cause.** A bug in mutter 50.5 (SIGSEGV): a display connection event arrived while the screen was being
streamed over RDP, and the GNOME session crashed; on Wayland that ends the session. Automatic login works only
once per boot. **Fix:** timed login in `/etc/gdm/custom.conf`: 5 seconds after the session ends, `view` logs in
again, and RDP can reconnect without a reboot.

## Dropped frames in mpv at 4K 120 Hz with HDR

**Cause.** A 1080p VC-1 remux stuttered: the mpv statistics (`i`) showed hundreds of dropped frames. There were
two causes:

- interpolation and `video-sync=display-resample` made mpv render 4K on every one of the 120 refreshes per
  second;
- GNOME in HDR mode could not present every frame on time.

**Fix** (in `mpv.conf`):

- interpolation and `display-resample` are off. At 120 Hz a 24p film is already shown evenly, each frame
  5 times;
- sync to audio (`video-sync=audio`, the default);
- `ewa_lanczossharp` scaling is kept: 7.4 ms per frame, while a 24p frame has 41.7 ms.

Result: 0 drops.

The mpv statistics can be read over SSH through the socket `/run/user/1000/mpv.sock`.

## MPC-QT: green or black video

**Cause.** By default MPC-QT requests intermediate frames in the `rgb8` format, and the radeonsi driver does not
accept them. **Fix:** `fbo-format=auto` is added to MPC-QT's "custom mpv options". This is already in the
repository's `settings.json`.

## Unified Remote: taps do not click, symbols do not type

**Causes.**

- On Wayland the server sends "press" and "release" in the same frame, and GNOME loses such a click.
- The built-in text input knows only simple keys, without Shift: capital letters and Cyrillic do not
  type.

**Fix:** the patch `patches/urserver/atrium-urserver.patch` (install step 14).

If a long press in the app gets "stuck" (this is drag mode: the left button stays held until the next tap),
GNOME does not accept clicks from anyone, including RDP. One more tap fixes it.

## RetroArch: window in the corner and off screen

**Cause.** At 250 % scaling RetroArch requests a 3840×2160 fullscreen surface in logical pixels. **Fix:**
`video_fullscreen_x = "1536"` and `video_fullscreen_y = "864"` in `retroarch.cfg` (install step 15).

## TV crops the picture on the left

**Cause.** The picture is shifted by 4 pixels: this is "Screen Shift" in LG's OLED Care settings.
**Fix:** turn it off. You can check with the test wallpaper `src/wallpaper/make_edge_test.py`.

## Stutter in Steam Link and Moonlight

**Cause.** The PC was connected to a 2.5 Gbit/s port, while the rest of the path to atrium ran at 1 Gbit/s.
Bursts of frames overflowed the switch queue and packets were lost: in the Steam Link log this shows up as
"lost data notification".
**Fix:**
- the PC was moved to a 1 Gbit/s port;
- on the MikroTik routers the port queues were enlarged (`pfifo` of 500 packets);
- on atrium the UDP buffer was enlarged (`90-atrium-stream.conf`).

## Windows does not open the shared folder

**Cause.** Windows 11 does not allow access to shared folders without a password. **Fix:** once on the PC
(PowerShell as administrator):
`Set-SmbClientConfiguration -EnableInsecureGuestLogons $true -RequireSecuritySignature $false -Force`.

If the name `atrium.lan` points to the old address: `ipconfig /flushdns`. The Windows DNS cache keeps entries
for a day. If a corporate VPN is up on the PC, it may block DNS queries to the home router.

## RDP password "does not work"

**Cause.** The password was typed into the hidden `grdctl` field, and in the Russian layout Backspace over
Cyrillic leaves byte fragments behind, while `grdctl` still reports success. **Fix:** type the password only in
the English layout.

## The file manager disappeared after `dnf remove`

**Cause.** dnf removes "orphaned" dependencies along with the package. **Fix:** always run
`dnf remove --assumeno <package>` first, and mark what you need with `dnf mark user <package>`.

## GNOME extensions disappeared after the "no notifications" setting

**Cause.** In GNOME 50, `allow-extension-installation false` also turns off loading extensions from
`~/.local/share/gnome-shell/extensions`. **Fix:** all extensions are installed system-wide in
`/usr/local/share/gnome-shell/extensions`.

## Brightness in HDR

With HDR on, a brightness slider appears in the quick settings menu. This is mutter's software brightness, on a
10–210 % scale, with the factory neutral at 100 % (45 % of the slider). It is not saved anywhere: after a reboot
it is back to 100 %. The `atrium-brightness-value` extension shows the exact value. When the system is idle
(after about 60 s), the screen dims; this is normal.

## Transmission uses uTP again

**Cause.** In Transmission 4.1 the `utp-enabled: false` setting is overridden by the
`preferred_transports` list. **Fix:** `"preferred_transports": ["tcp"]`, already in the repository's
`settings.json`. `settings.json` is edited only while the service is stopped.
