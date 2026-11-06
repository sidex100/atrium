# Updates: what can break and how to restore it

[Русская версия](../ru/updates.md) · [Install](install.md) · [Hardware](hardware.md) · [Known problems](problems.md)

## How we update

**The box updates itself, once a day** — `atrium-update` ([install, step 20](install.md)): from 07:00,
while nobody uses the box, it installs everything from the repositories and flatpak, checks with
`atrium-check`, mails before and after, reboots when needed. Without step 20 — the same by hand from the
console.

| What | How it is updated |
|---|---|
| System and programs from repositories | `atrium-update` (`dnf update -y`) or by hand `dnf upgrade`; a reboot if the kernel, mesa or GNOME was updated |
| Spotify, RetroDECK, Steam Link, Moonlight | `atrium-update` (`flatpak update -y`) or by hand `flatpak update` |
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
   curl -s -H 'Accept: application/json' 'https://bodhi.fedoraproject.org/updates/?packages=mesa&releases=F45&rows_per_page=3' | python3 -c "import sys,json; [print(u['title'], u['status'], 'testing', (u.get('date_testing') or '-')[:10], 'stable', (u.get('date_stable') or '-')[:10]) for u in json.load(sys.stdin)['updates']]"
   ```
   The opposite case — Fedora has published mesa but freeworld is not there yet — looks like mesa itself being
   skipped; wait the same way. With `--allowerasing` dnf removes freeworld, and video is decoded by the CPU.
3. After a kernel, mesa or GNOME update — reboot and check (below). `atrium-update` does it by itself.

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
- `/etc/postfix/main.cf`, `/etc/postfix/header_checks`, `/etc/aliases` (mail, step 20)
- SELinux labels `file_contexts.local`

Since Fedora 45 the Chrome repository lives in `/usr/share/dnf5/repos.d/google-chrome.repo` (the
`fedora-workstation-repositories` package), and "enabled" is our line in
`/etc/dnf/repos.override.d/99-config_manager.repo` (written by `dnf config-manager setopt google-chrome.enabled=1`).
The old `/etc/yum.repos.d/google-chrome.repo` was left as `.rpmsave` after the upgrade and was removed.

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

After every update we sort such files out with the standard `rpmconf` tool (the `rpmconf` package): for each
`.rpmnew` it shows the difference and asks — keep ours (`N`), take the new one (`Y`) or merge (`M`), and a
second run with `-c` finds "orphaned" `.rpmnew/.rpmsave` from removed packages and deletes them. No such
files should stay in the system: `atrium-check` warns about each one.

```bash
rpmconf -a && rpmconf -a -c
find / -xdev \( -path /proc -o -path /sys -o -path /srv \) -prune -o \( -name '*.rpmnew' -o -name '*.rpmsave' -o -name '*.rpmorig' \) -print
```

Sometimes `rpmconf` prints the right file name above the question (`Configuration file '/etc/postfix/main.cf'`)
and a different one in the question itself (`*** aliases`). Trust the `Configuration file` line.

## What can stop working

Packages do not touch our own files, but new versions of programs may fail to "understand" them.

1. **A new Fedora release means a new GNOME — the main risk.** GNOME disables extensions whose
   `metadata.json` does not list its version. Right now all of ours declare GNOME 51:
   - our three (`atrium-lock`, `atrium-brightness-value`, `atrium-no-dnd-icon`) — 50 and 51;
   - Executor (v32), GJS OSK (release 8761dd7 from GitHub) and Desktop Widgets (v21) — up to 51;
   - Dash to Dock, Freon and Just Perfection are installed as Fedora packages and are updated together
     with the system.
2. **Our extensions use gnome-shell internals**: the brightness slider, the Freon menu, the Desktop
   Widgets gadgets, the "Do Not Disturb" icon. They can break even on an update within GNOME 51.x. Then
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

All in one command — `atrium-check`. `atrium-update` runs it before a reboot and `atrium-boot-notify` after
boot:

```bash
atrium-check        # after an update, before a reboot
atrium-check boot   # after boot: also the kernel we booted with, and the TV output
```

What it checks:

- our kernel parameters (four, six with `atrium-hdmi-keep`) — in `/etc/kernel/cmdline` and in every boot
  entry; for the kernel of the next boot — the TV EDID in its initramfs when keep is on. The kernel of the
  next boot is not ready — exit code 2, and `atrium-update` does not reboot;
- no failed services — neither system ones nor in the TV session;
- all GNOME extensions `ACTIVE`;
- VA-API gives H.264, HEVC 10-bit and AV1, mesa and freeworld of the same version;
- one sound card — the DAC;
- no `.rpmnew` and `.rpmsave`;
- our Chromium `master_preferences` and Firefox `policies.json` in place, both prefs still known to Firefox;
- the copies of the Chrome and Chromium menu entries match the system ones except the Exec line;
- Transmission settings: TCP only, no DHT and LPD, encryption required, stop after download;
- the Unified Remote patch — 5 remotes;
- our changes in `retroarch.cfg`;
- with `boot`: the kernel booted with our parameters, the TV output (HDMI 2.1 FRL or "TV off").

The last line is `Problems:  none` or a list. The same by hand:

```bash
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
uname -r; cat /proc/cmdline
systemctl --failed; systemctl --user -M view@ --failed
$V gnome-extensions list --enabled --details | grep -E "^[a-z]|State"
vainfo --display drm 2>&1 | grep -E "VAProfile(H264|HEVC|AV1)" | head -4
cat /sys/kernel/debug/dri/0000:05:00.0/amdgpu_dm_dtn_log | sed -n '/^HPO:/,/^$/p'
cat /proc/asound/cards
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
- `/proc/asound/cards` shows one DAC;
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

## Moving to a new Fedora release

This is how we moved from 44 to 45 (2026-11-06). Not on release day. Everything that can be done and checked
is done on the old release first: Fedora cannot roll back.

**Preparation (on the old release, with a reboot and a check after each item):**

1. All extensions must declare the new GNOME. Third-party ones — new versions (for 45: Executor 32 from
   extensions.gnome.org, GJS OSK — the GitHub release, see [installation](install.md), step 10). Our three —
   `"51"` in `shell-version`, but first check the new gnome-shell sources at the places they reach into
   (checked for 51.1: the brightness slider and its label, the OSD, quick settings, the "Do Not Disturb"
   icon — unchanged). Install the new versions while still on the old GNOME and check that the settings are
   intact (`dconf dump` before and after).
2. RPM Fusion has a repository for the new release, and `mesa-va-drivers-freeworld` there matches Fedora's mesa.
3. A dry run — installs nothing, shows what gets replaced and removed:
   `dnf --releasever=45 --assumeno distro-sync`.
4. **The keyring.** Since Fedora 45 it is kept by oo7 instead of gnome-keyring. With autologin oo7 needs the
   keyring password in a systemd credential ([installation](install.md), step 6). Without it, from the second
   boot on oo7 keeps the keyring locked: Chrome logs out of every site, RDP does not find its password. Put the
   credential in place beforehand. Rename the keyring that gnome-keyring created as `Default_Keyring` to the
   standard `login` — **only right before the reboot into the upgrade**: with autologin gnome-keyring locks a
   keyring named `login`.

**The upgrade:**

```bash
systemctl disable --now atrium-update.timer && dnf system-upgrade download --releasever=45
K=/home/view/.local/share/keyrings && mv -f $K/Default_Keyring.keyring $K/login.keyring && printf login > $K/default && dnf5 offline reboot
```

Check the new Fedora key (`Importing OpenPGP key`) against https://fedoraproject.org/security/. The box
installs the upgrade by itself (15–30 minutes) and reboots into the new release.

**After the upgrade, before the second reboot:**

1. `atrium-check boot` — Problems: none.
2. The oo7 log: `Unlocking session keyring with systemd credential` and `Successfully migrated v0 keyring
   'login'`; the keyring is open (`Locked false`), RDP and Chrome work.
3. Config files: `rpmconf -a && rpmconf -a -c` (on 45 there were two: `postfix/main.cf.rpmnew` — kept ours and
   raised `compatibility_level` to 3.11; `google-chrome.repo.rpmsave` — removed).
4. Packages: `remove-retired-packages 44` (nothing to remove on 45), `dnf autoremove --assumeno` and, if the
   list makes sense, `dnf autoremove` (on 45 it took gcr3 from gnome-keyring and 7 more unused ones),
   `dnf clean all`. Leave the "dangling" symlinks from `symlinks -r /usr` alone: all of them belong to
   installed packages.
5. Flatpak: `flatpak update`, unused runtimes — `flatpak uninstall --unused`.
6. Leftovers: old `.bak` files, the old plain-text keyring (`login.keyring` and `login.keyring.migrated` next
   to `v1/`) — delete once everything is checked. At the end the `find` from the section above shows zero.
7. The second reboot: the oo7 log says `Unlocked keyring 'login'` — the keyring opened with the password from
   the credential.
8. `systemctl enable --now atrium-update.timer`.
