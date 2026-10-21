# Updates: what can break and how to restore it

[Русская версия](../ru/updates.md) · [Install](install.md) · [Hardware](hardware.md) · [Known problems](problems.md)

## How we update

**Manually from the console only**, nothing automatic:

| What | How it is updated |
|---|---|
| System and programs from repositories | `dnf upgrade`, then a reboot if the kernel, mesa or GNOME was updated |
| Spotify, RetroDECK, Steam Link, Moonlight | `flatpak update` |
| GNOME extensions in `/usr/local/share/gnome-shell/extensions` | never update by themselves; install a new version by hand, the same way as during installation |
| Unified Remote | an RPM without a repository, `dnf` does not touch it; install a new version by hand, then apply the patch again (below) |
| Windscribe | an RPM without a repository; a new stable version comes from GitHub (Windscribe/Desktop-App), check the sha256 from the release notes, `dnf install ./…rpm` |

gnome-software and PackageKit are **not installed**, so an "updates available" notice will never pop up
on the TV. GNOME does not check for extension updates (`allow-extension-installation false`).

Three rules:

1. **`dnf remove` — first with `--assumeno`.** dnf also removes "orphaned" dependencies. That is how the
   file manager and `tuned` were once lost.
2. **Never `--allowerasing`.** Every few weeks `dnf update` prints
   `Problem: … nothing provides mesa-filesystem(x86-64) = X needed by mesa-va-drivers-freeworld-X …` and below
   it `Skipping packages with broken dependencies: mesa-va-drivers-freeworld`. **This is a notice, not an
   error:** the transaction goes through, everything else is installed, and video keeps working on the current
   mesa and freeworld pair. The cause is two halves of one driver from two repositories: freeworld loads the
   Mesa core from a file with the version in its name (`libgallium-26.2.4.so`) and must match it exactly, so
   RPM Fusion requires the same `mesa-filesystem` version. It builds against the mesa from Fedora
   **updates-testing** and publishes right away, while Fedora keeps mesa in testing for 5–7 days — that window
   is the "Skipping". Do nothing: in a week `dnf update` installs both halves together. Where mesa is right now
   (`testing` or `stable`, since which date):
   ```bash
   curl -s -H 'Accept: application/json' 'https://bodhi.fedoraproject.org/updates/?packages=mesa&releases=F44&rows_per_page=3' | python3 -c "import sys,json; [print(u['title'], u['status'], 'testing', (u.get('date_testing') or '-')[:10], 'stable', (u.get('date_stable') or '-')[:10]) for u in json.load(sys.stdin)['updates']]"
   ```
   The opposite case — Fedora has published mesa but freeworld is not there yet — looks like mesa itself being
   skipped; wait the same way. With `--allowerasing` dnf removes freeworld, and video is decoded by the CPU.
3. After a kernel, mesa or GNOME update — reboot and check (below).

## What packages overwrite

Checked with `rpm -Va` on atrium (2026-10-13): of all package files, only these have been changed.

**An update will keep our file.** It will put the package's new version next to it as `.rpmnew` (this is
`%config(noreplace)`):

- `/etc/samba/smb.conf`
- `/etc/sysconfig/wsdd`
- `/etc/gdm/custom.conf`
- `/etc/NetworkManager/NetworkManager.conf`
- `/etc/dnf/dnf.conf`
- `/etc/chrony.conf` (the installer wrote our NTP server here)
- `/etc/yum.repos.d/google-chrome.repo` (Chrome itself rewrites it)
- SELinux labels `file_contexts.local`

`/etc/systemd/system.conf`, `/etc/locale.conf` and `/etc/default/grub` are not installed by the package at
all (`%ghost`), so updates do not touch them.

**An update will overwrite:**

| File | When | What comes back | How to fix |
|---|---|---|---|
| `/etc/chromium/master_preferences` | if Fedora changes this file in the chromium package; ours goes to `.rpmsave` | the Fedora start page, but only in a **new** Chromium profile | `install -m 644 /root/atrium/rootfs/etc/chromium/master_preferences /etc/chromium/` |
| 5 remotes in `/opt/urserver/remotes` | when a new version of urserver is installed | a short tap does not click; capital letters, Cyrillic and symbols are not typed | apply the patch again (below) |

The other way round, the TV user's copies of the Chrome and Chromium launchers
(`~/.local/share/applications/{google-chrome,chromium-browser}.desktop`, Russian UI, step 8) are **not
updated**: if a package changes its launcher (a new menu item, a different launch line), the copy stays
old. Run the step 8 command again.

Find such files after an update:

```bash
find /etc -name '*.rpmnew' -o -name '*.rpmsave'
```

## What can stop working

Packages do not touch our own files, but new versions of programs may fail to "understand" them.

1. **Fedora 45 (GNOME 51) is the main risk.** GNOME disables extensions whose `metadata.json` does not
   list its version:
   - our three (`atrium-lock`, `atrium-brightness-value`, `atrium-no-dnd-icon`) declare only 50;
   - Executor (v30) and GJS OSK (v53) — up to 50;
   - Desktop Widgets (v21) already supports 51;
   - Dash to Dock, Freon and Just Perfection are installed as Fedora packages and will be updated together
     with the system.
2. **Our extensions use gnome-shell internals**: the brightness slider, the Freon menu, the Desktop
   Widgets gadgets, the "Do Not Disturb" icon. They can break even on an update within GNOME 50.x. Then
   the extension gets the ERROR state, and the gadget simply stops being locked or stops showing the
   number. The session does not crash.
3. **The screensaver** turns the screen off through `org.gnome.Mutter.DisplayConfig.PowerSaveMode` and
   tracks idle time through `org.gnome.Mutter.IdleMonitor`. If mutter changes them, the screen will stop
   turning off.
4. **atrium-sysload** reads the kernel counters `gpu_busy_percent` and `vcn_busy_percent`. If they
   disappear, the panel will show zeros.
5. **Hardware video** depends on whether the versions of `mesa-va-drivers-freeworld` (RPM Fusion) and
   Fedora's mesa match (see rule 2).
6. **RetroDECK** may offer to reset its settings during an update and restore the factory
   `retroarch.cfg`. Then the fullscreen, audio, gamepad and button tweaks will be lost. Repeat install
   step 15.
7. **Transmission** renames settings in new versions. That is how `utp-enabled` stopped working in 4.1,
   and uTP can now be turned off only through `preferred_transports: ["tcp"]`. After an update, check the
   log and `settings.json`.
8. **The kernel and linux-firmware** affect output to the TV (HDMI 2.1) and stability. Old kernels stay
   in the boot menu (`installonly_limit=3`), and you can roll back to them. New kernels take kernel
   parameters from `/etc/kernel/cmdline`: verified on 7.2.9-201.
9. **`amdgpu.ppfeaturemask=0xfff73fff`** is set as a full mask. If a new kernel adds feature bits, the
   mask may accidentally turn them off or on. Once the hang trap is no longer needed, it is better to
   remove this parameter.
10. **`amdgpu.dcfeaturemask=0x402`** turns on HDMI 2.1 (FRL) and is also a full mask: `0x2` (the kernel 7.2
    default) + `0x400` (FRL). Kernel 7.4 is expected to turn FRL on by default together with VRR and ALLM.
    After moving to 7.4, look at the new default (`modinfo -p amdgpu`, the `amd_shared.h` source) and most
    likely remove the parameter: our mask may turn off new features that 7.4 enables by itself. How to
    check that HDMI 2.1 is in use after a kernel update — below and in [tv-output.md](tv-output.md).
11. **Auto HDR** (`atrium-hdr`, `auto-hdr.lua`) relies on `gdctl` and the `color-mode` property of the
    DisplayConfig D-Bus interface — that is GNOME. After a GNOME update, check as `view`: `atrium-hdr status`
    answers `sdr`, and an HDR film in mpv turns HDR on and off.
12. **`atrium-hdmi-keep`** (if it is on, [installation, step 19](install.md)): new kernels take the
    `drm.edid_firmware=` and `video=` parameters from `/etc/kernel/cmdline`, and the display description file
    `/usr/lib/firmware/edid/atrium-tv.bin` gets into the initramfs of every new kernel through
    `/etc/dracut.conf.d/90-atrium-hdmi-keep.conf` — all by itself when a kernel is installed. What can break
    it: (a) the kernel renames the parameter or stops understanding `video=…:e` — then `status` shows `kernel
    log: 0 x 'forcing …'`; (b) you changed the TV or a TV setting that changes the EDID — the file is stale,
    save it again: `off`, reboot, `on`, reboot. After a kernel update — `atrium-hdmi-keep status`.

## Checking after an update

```bash
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
uname -r; cat /proc/cmdline
systemctl --failed; systemctl --user -M view@ --failed
$V gnome-extensions list --enabled --details | grep -E "^[a-z]|State"
vainfo --display drm 2>&1 | grep -E "VAProfile(H264|HEVC|AV1)" | head -4
cat /sys/kernel/debug/dri/0000:05:00.0/amdgpu_dm_dtn_log | sed -n '/^HPO:/,/^$/p'
aplay -l | grep ^card
find /etc -name '*.rpmnew' -o -name '*.rpmsave'
rpm -V urserver | grep remotes
atrium-hdmi-keep status
```

Expected:

- our four kernel parameters are in place (six if `atrium-hdmi-keep` is on: its `status` then shows
  `configured: on`, `active now: on`, 1 copy of the file in the initramfs);
- no failed services;
- all extensions are `ACTIVE`;
- VA-API profiles are present;
- `aplay -l` shows one DAC;
- `rpm -V urserver` shows 5 modified remotes: this means the patch is in place.

## Restoring the Unified Remote patch

After installing a new version of urserver:

```bash
cd /opt/urserver/remotes/Unified && patch -p1 --dry-run < /root/atrium/patches/urserver/atrium-urserver.patch && patch -p1 --backup --suffix=.orig < /root/atrium/patches/urserver/atrium-urserver.patch
E="env HOME=/home/view XDG_SESSION_TYPE=wayland XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
runuser -u view -- $E /opt/urserver/urserver-stop; runuser -u view -- $E /opt/urserver/urserver-start --no-manager --no-notify
```

If `--dry-run` complains, the vendor has changed these files. Then the changes have to be carried over by
hand: what exactly the patch does is described in install step 14. The on-screen keyboards are built by
`src/urserver/build.py`.

## Moving to Fedora 45

Not on release day. First:

1. On extensions.gnome.org, check whether Executor and GJS OSK have been released with GNOME 51 support.
2. In the `metadata.json` of our three extensions, add `"51"` to `shell-version`, but only after testing
   on GNOME 51: they use shell internals.
3. Check that RPM Fusion has a repository for 45 and that `mesa-va-drivers-freeworld` is in it.

The upgrade itself is the standard one:

```bash
dnf upgrade --refresh && dnf system-upgrade download --releasever=45 && dnf offline reboot
```

After the upgrade — the check above and `dnf repolist` (RPM Fusion and Google Chrome should be on 45).
