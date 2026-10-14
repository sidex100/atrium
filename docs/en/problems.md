# Known problems and fixes

[Русская версия](../ru/problems.md) · [Install](install.md) · [Hardware](hardware.md) · [Updates](updates.md) · [TV output](tv-output.md) · [Game streaming](streaming.md)

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
- GNOME in HDR mode could not present every frame on time (back then the desktop was always in HDR; now it
  runs in SDR, and HDR turns on only for HDR videos — installation, step 9, "Auto HDR").

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

## Spotify: a blue Windows 9x style window frame

**Cause.** Spotify is Chromium inside, and new versions run on GNOME directly through Wayland. GNOME does
not draw frames for Wayland apps, the app draws its own, and Spotify cannot draw a GTK style frame. The
result is Chromium's stock frame. **Fix:** run Spotify through Xwayland, then GNOME draws the frame
(install step 8). Rollback: `runuser -u view -- flatpak override --user --reset com.spotify.Client` and
delete `~/.var/app/com.spotify.Client/config/spotify-flags.conf` of the TV user. Once Spotify can draw a
GTK style frame, you can go back to Wayland.

## TV crops the picture on the left

**Cause.** The picture is shifted by 4 pixels: this is "Screen Shift" in LG's OLED Care settings.
**Fix:** turn it off. You can check with the test wallpaper `src/wallpaper/make_edge_test.py`.

## Dropped frames in Chrome on 4K HDR YouTube

**What happened.** YouTube's "Stats for nerds" showed dozens of dropped frames in half a minute on an AV1 4K
60 fps HDR video while the desktop was in HDR.

**Investigation** — with the test script `src/tools/atrium-browser-bench.py`, without walking to the TV. It
starts the browser with a debugging port (in a separate profile: Chrome 136+ does not open that port on the
main one), plays the video full screen, after a 15-second warm-up counts dropped frames for 30 seconds and
measures the GPU load per process. Results:
- the GPU decodes the video (AV1 10-bit), the CPU is free;
- the bottleneck is graphics. In HDR Chrome redraws each frame into a 16-bit format (~30 % of the GPU), and
  GNOME re-composes the whole screen in HDR (~30 %). Half of the time the GPU is 95–100 % busy. Without HDR —
  about 12 %;
- Chrome flags (`WaylandOverlayDelegation`, zero-copy) do not help; Vulkan turns the hardware decoder off (30 %
  dropped); Firefox has no HDR, and its drops are a separate story (below); Chromium behaves like Chrome;
- in normal viewing 0.1–0.5 % of frames are dropped. A batch adds up at the start: quality switch, going full
  screen, and for a signed-in user resuming from the last position. "Stats for nerds" on top of the video
  adds drops by itself.

**Fix:** the desktop runs in SDR — YouTube in Chrome plays in SDR without drops. HDR films go to mpv, which
turns HDR on by itself (installation, step 9, "Auto HDR").

The script runs as root on the box: `python3 atrium-browser-bench.py` (all variants) or with variant names,
for example `python3 atrium-browser-bench.py chrome-base chrome-real-auto`. It closes the TV user's browsers,
writes results to `/tmp/atrium-browser-bench.txt` and deletes its temporary profiles at the end.

## Dropped frames in Firefox

**What happened.** Firefox dropped 14–18 % of frames on YouTube 4K60, on any codec and even on 1080p
H.264. The GPU was 7–20 % busy meanwhile.

**Where the truth was** (the same script `src/tools/atrium-browser-bench.py`, variants `firefox-*`):
- not the codecs. The GPU decodes through VA-API, a 4K frame in 0.45 ms (`MOZ_LOG`). The system ffmpeg
  instead of the bundled ffvpx changes nothing;
- not AV1. Firefox says it plays AV1 4K60 smoothly, but YouTube gives it 4K only in VP9; without VP9 it
  is H.264 1080p. Extensions like enhanced-h264ify do not help for that reason;
- not WebRender. It already draws on the GPU: the software variant eats 3 cores and drops 87 %;
- **the frame clock.** Firefox draws on the frames GNOME sends it on Wayland, and they come unevenly: the
  page gets 86–91 frames a second instead of 120, with dozens of hitches.

**Fix:** in the Firefox policy (`/etc/firefox/policies/policies.json`, install step 9)
`widget.wayland.vsync.enabled = false` and `layout.frame_rate = 120`: Firefox draws on its own 120 Hz
timer. The same video full screen — 1 dropped of 1810 (was 258), the page gets a steady 119–120 frames a
second. With another refresh rate, put that number instead of 120.

## Stutter in Steam Link and Moonlight

**Cause.** The PC was connected to a 2.5 Gbit/s port, while the rest of the path to atrium ran at 1 Gbit/s.
Bursts of frames overflowed the switch queue and packets were lost: in the Steam Link log this shows up as
"lost data notification".
**Fix:**
- the PC was moved to a 1 Gbit/s port;
- on the MikroTik routers the port queues were enlarged (`pfifo` of 500 packets);
- on atrium the UDP buffer was enlarged (`90-atrium-stream.conf`).

In detail, with the MikroTik commands and network recommendations — [streaming.md](streaming.md).

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
