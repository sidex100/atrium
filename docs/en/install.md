# Installing atrium from scratch

[Русская версия](../ru/install.md) · [Hardware and BIOS](hardware.md) · [Updates](updates.md) · [Known problems](problems.md) · [TV output](tv-output.md) · [Game streaming](streaming.md)

This guide rebuilds atrium step by step: from a bare box to a media center by the TV. Each step says
what we do and why. The commands come from the history of the real installation and were tested on the
live box.

**How to read the commands.** Everything in a `bash` block runs on the box as `root` over SSH, unless
stated otherwise. `powershell` blocks run on a Windows computer. You can paste each block as a whole:
the variables it needs are declared at its start.

**Your own values.** Commands and files use example values: the home network is `192.168.0.0/24`, the box gets the address `192.168.0.42` from
a static DHCP lease on the router, its network name is `atrium.lan`, and its hostname is
`atrium.example.com`. If yours are different, change them in the commands below and in the repository
files. To see where they occur, run `grep -rn "192\.168\.0\.\|atrium\.lan\|example\.com" rootfs src`.

---

## 0. What you need

- A **Beelink SER5 MAX** box (Ryzen 7 7735U, Radeon 680M) and a second 2 TB NVMe drive for media. The
  full list, the BIOS settings and everything about the TV are in [hardware.md](hardware.md).
- A passive **HDMI Ultra High Speed (48G)** cable from the box's HDMI to the TV. With the kernel parameter
  from step 12, the box's own HDMI gives 4K 120 Hz, RGB, 10-bit and HDR (details in
  [tv-output.md](tv-output.md)).
- A USB DAC, if you want good sound (ours is an SMSL). We turn off the box's built-in audio.
- A USB stick of 2 GB or more, a USB keyboard (for the BIOS and the installer) and a wired network with
  DHCP.
- A second computer for SSH. The BIOS is updated from the box's own Windows, before it is wiped.

## 1. BIOS — before installation

**Why.** A fresh BIOS removes the power limit on the graphics core, and the settings below turn off
everything that gets in the way of a media center: sleep, PCIe link power saving, HDMI audio, network
boot.

1. **Updating the BIOS to ASER5012** is done from the Windows that comes preinstalled on the box, before
   installing Linux. How exactly, with which flags and why — see [hardware.md](hardware.md), section
   "BIOS".
2. **Settings.** The **Del** key at power-on opens the BIOS, **F7** opens the boot menu. The full table of
   settings with explanations is in [hardware.md](hardware.md), section "BIOS settings". The main ones:
   - sleep and hibernation in ACPI — off (the box works as a server and never sleeps);
   - ASPM on all PCIe ports — Disabled (the links do not go to sleep, no hangs or delays);
   - NB Azalia (HDMI audio) — Disabled, sound goes only through the USB DAC;
   - UMA Frame Buffer — **4G** (emulators up to PS3 need video memory);
   - AC Power Loss — Always On (after a power cut the box turns itself back on);
   - Network Stack and PXE — Disabled, Quiet Boot — Disabled.

## 2. Cable to the TV

An ordinary passive **Ultra High Speed (48G)** HDMI cable from the box's HDMI to any HDMI 2.1 input of the
TV. Nothing needs to be flashed. The spec sheet lists the box's port as HDMI 2.0, but it does carry
HDMI 2.1: the kernel parameter `amdgpu.dcfeaturemask=0x402` in step 12 turns it on. Until that step the
picture runs as HDMI 2.0 (4K 60 Hz), and that is expected.

How we struggled for a month with active DP → HDMI 2.1 cables before finding this, and the fallback if
your HDMI port does not carry HDMI 2.1 — [tv-output.md](tv-output.md).

## 3. Installing Fedora

**Why this way.** The Fedora Everything network installer sets up a bare system, without the Workstation
set of programs. After that we install exactly what a media center needs, and we know every package.

1. Download **Fedora Everything, Network Install, x86_64** — https://fedoraproject.org/misc/ (the Everything section)
   (we use Fedora 44). Write the USB stick with Fedora Media Writer or `dd`.
2. Boot from the stick (F7 → the stick) and go through the installer:
   - **Language:** English (United States). A Russian GNOME interface is not needed, and English is more
     reliable in the console.
   - **Keyboard:** English (US).
   - **Time & Date:** region Etc / UTC — the system clock runs in UTC, and the TV user gets local time
     separately (step 9). In **NTP servers** we entered the home router (`router.lan`); you can keep the
     default Fedora pool.
   - **Software Selection:** **Fedora Custom Operating System**, no add-ons. This is the barest base.
   - **Installation Destination:** select **only the system drive** (ours is a Crucial P3 Plus 1 TB), do
     not touch the second drive. **Custom**, partitions by hand:

     | Mount point | Size | File system | Why |
     |---|---|---|---|
     | `/boot/efi` | 600 MiB | EFI System Partition | UEFI boot loader |
     | `/boot` | 2 GiB | ext4 | kernels; 2 GB holds three kernels with room to spare |
     | `/` | all the rest | ext4 | system and programs |

     There is no swap partition: Fedora turns on swap in memory (zram) by itself.
   - **Root Account:** enable root, set a password and tick **Allow root SSH login with password**.
     Do not create a user here: the TV user `view` appears in step 6 and must get uid 1000 — the
     commands below depend on that number (`/run/user/1000`).
3. **Begin Installation**, and when it finishes — **Reboot System**; remove the stick.

## 4. First SSH login and getting the repository

**Why.** From here on everything is done from your main computer over SSH. Logging in with a key saves
you the password and lets you paste long commands.

On the Windows PC, create a key and send it to the box. Find the box's address in the DHCP lease on the
router or with `ip a` on the box itself.

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\atrium_ed25519" -N '""' -C "atrium"
scp "$env:USERPROFILE\.ssh\atrium_ed25519.pub" root@192.168.0.42:/tmp/
```

On the box (password login one last time: `ssh root@192.168.0.42`):

```bash
install -d -m 700 /root/.ssh && tr -d '\r' < /tmp/atrium_ed25519.pub >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys && restorecon -R /root/.ssh && rm -f /tmp/atrium_ed25519.pub
```

From now on, log in like this: `ssh -i ~/.ssh/atrium_ed25519 root@192.168.0.42`.

Now put this repository on the box in `/root/atrium`. If you have access to it on GitHub:

```bash
dnf -y install git && git clone https://github.com/sidex100/atrium.git /root/atrium
```

If the repository is private and the box has no access to it, download it on the PC (Code → Download
ZIP), unpack it and copy the folder: `scp -r atrium root@192.168.0.42:/root/`.

## 5. Base: hostname, updates, RPM Fusion, video through the GPU

**Why.** RPM Fusion provides what Fedora lacks because of patents: full ffmpeg and the hardware H.264/HEVC
decoding driver for AMD graphics (`mesa-va-drivers-freeworld`). Without it the CPU decodes video.
`fastestmirror` and parallel downloads are needed because nearby mirrors often stalled for us.

```bash
R=/root/atrium/rootfs
hostnamectl set-hostname atrium.example.com
\cp -a /etc/dnf/dnf.conf /etc/dnf/dnf.conf.bak-$(date +%Y%m%d) && install -m 644 $R/etc/dnf/dnf.conf /etc/dnf/dnf.conf
dnf -y upgrade --refresh
dnf -y install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm pciutils usbutils
for k in /etc/pki/rpm-gpg/RPM-GPG-KEY-rpmfusion-*-fedora-$(rpm -E %fedora); do echo "$k"; gpg --show-keys --with-fingerprint "$k" 2>/dev/null | grep -A1 '^pub'; done
```

Check the key fingerprints against https://rpmfusion.org/keys. Then the video driver and a check:

```bash
dnf -y install mesa-va-drivers-freeworld ffmpeg libva-utils
vainfo --display drm 2>&1 | grep -E "Driver version|VAProfile(H264|HEVC|VP9|AV1)"
```

The output must list the H.264, HEVC (including Main10), VP9 and AV1 profiles.

24-hour time in the console, as on our servers:

```bash
R=/root/atrium/rootfs
\cp -a /etc/locale.conf /etc/locale.conf.bak-$(date +%Y%m%d) && install -m 644 $R/etc/locale.conf /etc/locale.conf
```

## 6. GNOME, the TV user, autologin, no sleep at all

**Why.** We install only the GNOME shell (Wayland) and what it cannot work properly without. The user
`view` is the TV: no password, logs in by itself. Sleep is disabled at the systemd level: the box runs
around the clock (torrents, the shared folder, remote access).

```bash
dnf -y install mc nano htop gnome-shell gdm gnome-session-wayland-session gnome-control-center nautilus ptyxis gnome-shell-extension-dash-to-dock xdg-desktop-portal-gnome xdg-user-dirs-gtk gnome-keyring pipewire-alsa
dnf mark user tuned
dnf remove --assumeno gnome-tour malcontent-control tuned-ppd
```

The last command only shows what would be removed. **Always preview any `dnf remove` with
`--assumeno` first**: dnf also removes "orphaned" dependencies. Once the file manager went away this way
together with an unneeded package. The line `dnf mark user tuned` protects `tuned` from such removal. If
the list contains only these three packages, remove them:

- `gnome-tour` — the welcome tour;
- `malcontent-control` — parental controls;
- `tuned-ppd` — the power mode switch in the menu; our mode is always "performance".

```bash
R=/root/atrium/rootfs
dnf -y remove gnome-tour malcontent-control tuned-ppd
systemctl --global mask localsearch-3.service
systemctl enable --now tuned && tuned-adm profile throughput-performance
useradd -c TV view && passwd -d view && id view
\cp -a /etc/gdm/custom.conf /etc/gdm/custom.conf.bak-$(date +%Y%m%d) && install -m 644 $R/etc/gdm/custom.conf /etc/gdm/custom.conf
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
systemctl set-default graphical.target
```

- `localsearch` — the GNOME file indexer. A media center does not need it, and it loads the disk.
- `throughput-performance` — the CPU always runs at high clocks, with no ramp-up delays. Turbo and
  C-states still work; at idle the box draws 3–4 W.
- `custom.conf` — autologin for `view` and **a new login after 5 seconds** if the GNOME session crashes.
  The session once crashed because of a mutter bug (see [problems.md](problems.md)), and RDP came back
  on its own.

Do not reboot yet: the media drive comes first.

## 7. Second drive: /srv

**Why.** Movies, music, downloads and games live on a separate 2 TB NVMe mounted at `/srv`. The system
does not depend on it: if the drive fails (`nofail`), the box still boots.

If the drive is a WD Blue SN5000, update its firmware first (291020WD → 291050WD). How — see
[hardware.md](hardware.md), section "WD Blue SN5000 firmware". Then partition it. The command finds the
drive **by model**, not by the name `nvme0`/`nvme1`: the names change from boot to boot. It stops if the
drive already has partitions.

```bash
M="WD Blue SN5000 2TB"
D=$(for c in /sys/class/nvme/nvme*; do [ "$(xargs < $c/model)" = "$M" ] && echo /dev/${c##*/}n1; done); echo "disk = $D"
[ -b "$D" ] && [ "$(lsblk -n -o NAME $D | wc -l)" = 1 ] && parted -s $D mklabel gpt mkpart srv xfs 1MiB 100% && udevadm settle && mkfs.xfs -L srv ${D}p1 && U=$(blkid -p -s UUID -o value ${D}p1) && \cp -p /etc/fstab /etc/fstab.bak-$(date +%Y%m%d) && printf '%s\n' "# /srv on the media NVMe; nofail - boot even without it" "UUID=$U /srv xfs defaults,nofail 0 0" >> /etc/fstab && systemctl daemon-reload && mkdir -p /srv && mount /srv && findmnt /srv
```

Folders. `2775` and the group `view` are needed so that the TV, Transmission and the Samba shared folder
can all write to them:

```bash
install -d -o view -g view -m 2775 /srv/video /srv/music /srv/download /srv/torrent /srv/docs /srv/pics /srv/games
restorecon -R /srv && ls -l /srv
reboot
```

After the reboot the TV shows the GNOME desktop of the user `view`.

## 8. Programs

**Why each one.**

- **Browsers.** Google Chrome is the main one: its own codecs, Widevine, the fastest. Firefox is the
  backup, with the system ffmpeg and VA-API. Chromium is for testing.
- **Players.** **mpv** — the default player for all video, best quality. MPC-QT — an mpv front end in the
  style of MPC-HC. VLC — just in case. **fooyin** — music, in the style of foobar2000.
- **Torrents.** Transmission Remote GTK — a window for the torrent daemon (step 13).
- **Look.** Geist and Inter fonts, the dark GTK3 theme, emoji. Freon — CPU temperature in the panel. Just
  Perfection — removes clutter from the GNOME menu.
- **Spotify** — from Flathub.

```bash
dnf -y group install standard
dnf -y install fedora-workstation-repositories && dnf config-manager setopt google-chrome.enabled=1
dnf -y install google-chrome-stable firefox chromium mpv mpc-qt vlc vlc-plugins-freeworld fooyin transmission-remote-gtk flatpak gnome-tweaks gnome-backgrounds adw-gtk3-theme google-noto-color-emoji-fonts rsms-inter-vf-fonts vercel-geist-fonts vercel-geist-mono-fonts gnome-shell-extension-freon gnome-shell-extension-just-perfection lm_sensors
rpm -qa 'gpg-pubkey*' --qf '%{version} %{summary}\n' | grep -i google
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install -y --noninteractive flathub com.spotify.Client
```

The Google key must have the fingerprint `EB4C 1BFD 4F04 2F6D DDCC EC91 7721 F63B D38B 4796`. You can
check it with `rpm -qi gpg-pubkey-d38b4796`.

## 9. Settings: the system and the TV user

**Why.**

- **Firefox** — a policy removes the Fedora home page and tiles.
- **Chromium** — `master_preferences` removes the Fedora start page. This affects only a new
  profile.
- **The dark theme** is locked with a dconf lock: the light one cannot be chosen from the menu.
- **Dock icons** are locked with a dconf lock: they cannot be unpinned or rearranged with the mouse. To
  change them, edit the file and run `dconf update`.
- **atrium-no-overview** — GNOME 50 opens the overview (search and workspaces) right at login, and
  extensions load too late to stop it. The script closes the overview over D-Bus.
- **Wallpaper** — a painting by Gustave Boulanger (1861, public domain) with the caption ATRIUM. Evening
  version: warm light in the center, dark edges. The generator is in `src/wallpaper/`.
- **Files of the user `view`.** File associations (video → mpv, explicit audio → fooyin, links →
  Chrome), settings for mpv, MPC-QT and VLC, the TV's time zone (the repository has the example `TZ=UTC` — set yours), the folders
  "Videos/Music/Downloads/Documents/Pictures" in `/srv`, file manager bookmarks, the display mode
  (`monitors.xml`: 3840×2160, 120 Hz, 250 % scale, SDR).
- **Auto HDR.** The desktop runs in SDR: in HDR GNOME re-composes every frame, and the GPU has no headroom
  left for 4K HDR in the browser. HDR turns on by itself only while mpv plays an HDR video (PQ or HLG):
  the `auto-hdr.lua` script in the mpv settings pauses, calls `atrium-hdr on` and resumes 2 seconds later;
  when the video is over or mpv is closed — `atrium-hdr off`. The TV blanks for 1–2 seconds on each
  switch. While an RDP client is connected, `atrium-hdr` does not switch the screen (GNOME 50 crashed on a
  display change during RDP). By hand: `atrium-hdr on|off|status` as the user `view`.

```bash
R=/root/atrium/rootfs
install -D -m 644 $R/etc/firefox/policies/policies.json /etc/firefox/policies/policies.json
\cp -a /etc/chromium/master_preferences /etc/chromium/master_preferences.bak-$(date +%Y%m%d) && install -m 644 $R/etc/chromium/master_preferences /etc/chromium/master_preferences
install -D -m 644 -t /etc/dconf/db/local.d $R/etc/dconf/db/local.d/00-atrium-dark $R/etc/dconf/db/local.d/00-atrium-dock
install -D -m 644 -t /etc/dconf/db/local.d/locks $R/etc/dconf/db/local.d/locks/00-atrium-dark $R/etc/dconf/db/local.d/locks/00-atrium-dock
dconf update
install -m 755 $R/usr/local/bin/atrium-no-overview /usr/local/bin/atrium-no-overview
install -m 755 $R/usr/local/bin/atrium-hdr /usr/local/bin/atrium-hdr
install -D -m 644 -t /usr/local/share/backgrounds/atrium $R/usr/local/share/backgrounds/atrium/atrium-painting-evening-v2-4k.png
cp -r --no-preserve=ownership $R/home/view/.config/. /home/view/.config/ && chown -R view:view /home/view/.config && chmod 600 /home/view/.config/vlc/vlcrc
restorecon -R /etc/firefox /etc/chromium /etc/dconf /usr/local /home/view
```

The GNOME settings of the user `view` (theme, fonts, keyboard layouts, panel, extensions) are loaded into
the running session. What each line means is explained in the comments at the top of
`src/dconf/view-atrium.ini`.

```bash
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
$V dconf load / < /root/atrium/src/dconf/view-atrium.ini
$V gsettings get org.gnome.desktop.interface clock-format
```

The keyboard layouts work like this: Alt+Shift switches, Caps Lock selects English, Shift+Caps selects
Russian, right Alt works as AltGr.

## 10. GNOME extensions and load in the panel

**Why.** The GNOME panel shows who is working right now (CPU, GPU, VIDEO — the hardware video decoder),
network speed and temperature. The desktop shows disk usage. Clicking these gadgets opens nothing. Our
extensions:

| Extension | What it does |
|---|---|
| `atrium-lock` | blocks clicks and menus on Freon and the desktop widgets (Executor is locked by its own setting) |
| `atrium-brightness-value` | shows the exact HDR brightness value next to the slider and on the bar at the bottom |
| `atrium-no-dnd-icon` | hides the "Do Not Disturb" bell: there are no notifications on the TV at all |

We install all extensions **system-wide** in `/usr/local/share/gnome-shell/extensions`. The reason: with
the setting `allow-extension-installation false` (GNOME does not check for updates and shows no
notifications), GNOME 50 stops loading extensions from the home folder.

We download the three third-party extensions from extensions.gnome.org in exactly the versions installed
on atrium and verify their checksums:

| Extension | Version | What it gives |
|---|---|---|
| Executor | 30 | command output in the panel: CPU/GPU/VIDEO load and network speed |
| Desktop Widgets (azclock) | 21 (16.1) | text on the desktop: `df` and `du` of the disks |
| GJS OSK | 53 | an on-screen keyboard like in Windows |

```bash
E=/usr/local/share/gnome-shell/extensions; mkdir -p $E; cd /tmp
while read -r uuid tag sum; do
  curl -fsSL -o ext.zip "https://extensions.gnome.org/download-extension/$uuid.shell-extension.zip?version_tag=$tag" &&
  echo "$sum  ext.zip" | sha256sum -c - && rm -rf "$E/$uuid" && mkdir "$E/$uuid" && unzip -q ext.zip -d "$E/$uuid" &&
  { [ -f "$E/$uuid/schemas/gschemas.compiled" ] || glib-compile-schemas "$E/$uuid/schemas"; } && rm -f ext.zip
done <<'EOF'
executor@raujonas.github.io 70219 1ea446f27f7d33cf58b14fc440f33ac6ec50ae9c50c5e3dec53594a4939ddb07
azclock@azclock.gitlab.com 75151 79b0e9fcd4d11fb86985dd64eef4d4f6310698a6c37646507812bc3e2eb5b603
gjsosk@vishram1123.com 74269 38578bfb54880c8fec13e24783406d4c77ad047b5bc205b7a5814dc631231b6d
EOF
R=/root/atrium/rootfs
cp -r $R/usr/local/share/gnome-shell/extensions/. $E/
chown -R root:root $E && chmod -R u=rwX,go=rX $E && restorecon -R $E && ls $E
```

The `atrium-sysload` service writes CPU/GPU/VIDEO load and network speed to `/run/atrium-sysload/` once a
second, and Executor shows these lines in the panel. The service runs as a throwaway user with no
privileges, with no network and with a read-only system. It takes its data from kernel counters:
`gpu_busy_percent`, `vcn_busy_percent` (the video decoder), `/proc/stat` and the network adapter
counters.

The service starts `/usr/local/sbin/atrium-sysload`, while the file goes to `/usr/local/bin` — it is the
same place: on Fedora 42 and later `/usr/local/sbin` is a link to `bin` (created by the `filesystem`
package).

```bash
R=/root/atrium/rootfs
install -m 755 $R/usr/local/bin/atrium-sysload /usr/local/bin/atrium-sysload
install -m 644 $R/etc/systemd/system/atrium-sysload.service /etc/systemd/system/atrium-sysload.service
restorecon /usr/local/bin/atrium-sysload /etc/systemd/system/atrium-sysload.service
systemctl daemon-reload && systemctl enable --now atrium-sysload && sleep 2 && cat /run/atrium-sysload/panel /run/atrium-sysload/net
reboot
```

GNOME sees new system extensions only after a new login, so we reboot. Check after the reboot:

```bash
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
$V gnome-extensions list --enabled --details | grep -E "^[a-z]|State"
```

All of them must show `State: ACTIVE`.

## 11. Apple Aerial screensaver and turning off the screen

**Why.** GNOME has no screensaver, it can only blank the screen. And when GNOME blanks the screen, it
raises a screen "shield", under which GNOME forbids remote desktop (RDP silently fails to connect). So:

- **15 minutes without input** — Apple Aerial videos (cities, nature, the ISS, underwater) play full
  screen in 4K, without sound;
- **30 minutes** — the screen turns off through Mutter (the same switch GNOME itself uses), but without
  the shield;
- **any touch** of the mouse, keyboard, remote or RDP — everything comes back;
- while a movie or YouTube is playing, the player holds an idle inhibitor, and the screensaver stays out
  of the way.

The videos belong to Apple and are not in the repository: we download them from Apple's servers. That is
20 videos, 7.9 GB. Apple's server is signed by an Apple root certificate that Fedora does not trust, so
the download uses this root explicitly. It is not added to the system trust store.

```bash
d=/usr/local/share/atrium-screensaver && u=https://sylvan.apple.com/Aerials/2x/Videos && install -d -m 755 $d/aerial && curl -sSf https://www.apple.com/appleca/AppleIncRootCertificate.cer | base64 -w64 | sed -e '1i -----BEGIN CERTIFICATE-----' -e '$a -----END CERTIFICATE-----' > $d/apple-root.pem && systemd-run --unit=atrium-aerial-fetch curl -sSf --retry 3 --cacert $d/apple-root.pem --output-dir $d/aerial -o new-york.mov $u/comp_N008_C009_PS_v01_SDR_PS_20180925_SDR_4K_HEVC.mov -o hong-kong.mov $u/comp_HK_H004_C008_PSNK_v19_SDR_PS_20180914_SDR_4K_HEVC.mov -o dubai.mov $u/comp_DB_D008_C010_PSNK_v21_SDR_PS_20180914_F0F16157_SDR_4K_HEVC.mov -o london.mov $u/comp_L007_C007_PS_v01_SDR_PS_20180925_SDR_4K_HEVC.mov -o san-francisco.mov $u/comp_A012_C014_1223PT_v53_SDR_PS_FINAL_20180709_F0F8700_SDR_4K_HEVC.mov -o iceland.mov $u/I003_C008_SDR_4K_HEVC.mov -o greenland.mov $u/comp_GL_G002_C002_PSNK_v03_SDR_PS_20180925_SDR_4K_HEVC.mov -o yosemite.mov $u/Y005_C003_SDR_4K_HEVC.mov -o patagonia.mov $u/P006_C002_UHD_SDR_4K_HEVC.mov -o hawaii.mov $u/comp_H005_C012_PS_v01_SDR_PS_20180925_SDR_4K_HEVC.mov -o scotland.mov $u/S006_C007_SDR_4K_HEVC.mov -o grand-canyon.mov $u/G010_C026_UHD_SDR_v02_4K_HEVC.mov -o space-north-america-aurora.mov $u/comp_GMT314_139M_170NC_NORTH_AMERICA_AURORA__COMP_v22_SDR_20181206_v12CC_SDR_4K_HEVC.mov -o space-new-york-night.mov $u/comp_GMT307_136NC_134K_8277_NY_NIGHT_01_v25_SDR_PS_20180907_SDR_4K_HEVC.mov -o space-africa-night.mov $u/comp_GMT312_162NC_139M_1041_AFRICA_NIGHT_v14_SDR_FINAL_20180706_SDR_4K_HEVC.mov -o space-caribbean-day.mov $u/comp_GMT308_139K_142NC_CARIBBEAN_DAY_v09_SDR_FINAL_22062018_SDR_4K_HEVC.mov -o sea-california-kelp.mov $u/g201_CA_A016_C002_SDR_20191114_SDR_4K_HEVC.mov -o sea-humpback-whale.mov $u/g201_WH_D004_L014_SDR_20191031_SDR_4K_HEVC.mov -o sea-palau-jellies.mov $u/PA_A010_C007_SDR_20190717_SDR_4K_HEVC.mov -o sea-california-dolphins.mov $u/DL_B002_C011_SDR_20191122_SDR_4K_HEVC.mov
```

The download runs in the background and takes 5–10 minutes. To watch it: `systemctl status
atrium-aerial-fetch`, `du -sh $d/aerial`. Other videos: Apple's catalog is at
`https://sylvan.apple.com/Aerials/resources-16.tar` (`entries.json`, 114 videos), file names
`*_SDR_4K_HEVC.mov`.

The screensaver itself is a service in the TV user's session:

```bash
R=/root/atrium/rootfs
install -m 755 $R/usr/local/bin/atrium-screensaver /usr/local/bin/atrium-screensaver
install -m 644 $R/etc/systemd/user/atrium-screensaver.service /etc/systemd/user/atrium-screensaver.service
restorecon /usr/local/bin/atrium-screensaver /etc/systemd/user/atrium-screensaver.service
systemctl --global enable atrium-screensaver.service
systemctl --user -M view@ daemon-reload && systemctl --user -M view@ start atrium-screensaver.service && systemctl --user -M view@ is-active atrium-screensaver.service
```

## 12. Sound and kernel parameters (including HDMI 2.1)

**Why.** The box's built-in analog audio (`1022:15e3`) cannot be turned off in the BIOS. We hide it from
the system with the `pci-stub` kernel parameter, and the USB DAC remains the only sound card: no output
to choose, everything goes to the DAC. PipeWire runs at 48 kHz, but when a single stream plays, the DAC
switches to the track's sample rate (44.1–192 kHz), that is, without resampling.

Kernel parameters, all at once:

- `pci-stub.ids=1022:15e3` — hides the built-in audio;
- `amdgpu.dcfeaturemask=0x402` — turns on HDMI 2.1 (FRL) on the box's own HDMI: 4K 120 Hz, RGB, 10-bit,
  HDR. In kernel 7.2 it is off by default. `0x2` is the default value, `0x400` is the FRL bit
  ([tv-output.md](tv-output.md));
- `efi_pstore.pstore_disable=0` and `amdgpu.ppfeaturemask=0xfff73fff` — part of the freeze trap,
  explained in step 16.

On Fedora, `grubby --update-kernel=ALL` itself also adds the parameters to `/etc/default/grub`, and
sometimes to `/etc/kernel/cmdline`, so we add to `/etc/kernel/cmdline` only what is not there yet.

```bash
A="pci-stub.ids=1022:15e3 efi_pstore.pstore_disable=0 amdgpu.ppfeaturemask=0xfff73fff amdgpu.dcfeaturemask=0x402"
R=/root/atrium/rootfs
for f in /etc/kernel/cmdline /etc/default/grub; do [ ! -f $f ] || \cp -p $f $f.bak-$(date +%Y%m%d); done
grubby --update-kernel=ALL --args="$A"
[ ! -f /etc/kernel/cmdline ] || for p in $A; do grep -q -- "$p" /etc/kernel/cmdline || sed -i "1s|\$| $p|" /etc/kernel/cmdline; done
install -m 644 $R/etc/default/grub /etc/default/grub
install -D -m 644 $R/etc/pipewire/pipewire.conf.d/50-atrium-rates.conf /etc/pipewire/pipewire.conf.d/50-atrium-rates.conf
grubby --info=ALL | grep -E "^args"; cat /etc/kernel/cmdline 2>/dev/null
```

The changes touch three places:

- `grubby` — the kernels already installed;
- `/etc/kernel/cmdline` — kernels that future updates will install;
- `/etc/default/grub` — rebuilds of the boot menu.

They take effect after a reboot (step 18). Then `aplay -l` shows only the DAC.

## 13. Torrents and the shared folder

**Transmission.** The daemon always runs as a service and downloads into `/srv/download` by itself. A
`.torrent` file dropped into `/srv/torrent` (including from Windows through the shared folder) starts
downloading right away. Low-profile settings:

- encryption is required;
- DHT, LPD and uTP are off — they give the download away on the network;
- seeding stops right after the download finishes;
- the web interface and remote control are open only to the home network.

On the TV it is controlled with Transmission Remote GTK.

```bash
R=/root/atrium/rootfs; L=192.168.0.0/24
dnf -y install transmission-daemon && usermod -aG view transmission
install -d -o transmission -g transmission -m 700 /var/lib/transmission/.config /var/lib/transmission/.config/transmission-daemon
install -o transmission -g transmission -m 600 $R/var/lib/transmission/.config/transmission-daemon/settings.json /var/lib/transmission/.config/transmission-daemon/settings.json
install -D -m 644 $R/etc/systemd/system/transmission-daemon.service.d/override.conf /etc/systemd/system/transmission-daemon.service.d/override.conf
restorecon -R /var/lib/transmission /etc/systemd/system/transmission-daemon.service.d
systemctl daemon-reload && systemctl enable --now transmission-daemon
firewall-cmd --add-service=transmission-client && firewall-cmd --permanent --add-service=transmission-client
r="rule family=\"ipv4\" source address=\"$L\" port port=\"9091\" protocol=\"tcp\" accept"; firewall-cmd --add-rich-rule="$r" && firewall-cmd --permanent --add-rich-rule="$r"
```

Edit `settings.json` only while the service is stopped: when it stops, the daemon writes its own settings
over the file. In Transmission Remote GTK: Edit → Local Preferences → Connection → `localhost:9091`, path
`/transmission/rpc`, no login, and turn on connecting at startup.

**Samba.** The shared folder `\\atrium.lan\media` is the whole `/srv`, **with no login or password** and
only for the home network. Folders in the root of `/srv` cannot be deleted or renamed; inside them you
can read and write. wsdd makes atrium visible in "Network" in Windows.

```bash
R=/root/atrium/rootfs; L=192.168.0.0/24
dnf -y install samba wsdd policycoreutils-python-utils
\cp -a /etc/samba/smb.conf /etc/samba/smb.conf.bak-$(date +%Y%m%d) && install -m 644 $R/etc/samba/smb.conf /etc/samba/smb.conf
\cp -a /etc/sysconfig/wsdd /etc/sysconfig/wsdd.bak-$(date +%Y%m%d) && install -m 644 $R/etc/sysconfig/wsdd /etc/sysconfig/wsdd
semanage fcontext -a -t samba_share_t '/srv(/.*)?' && semanage fcontext -a -t samba_share_t '/srv' && restorecon -R /srv
testparm -s 2>/dev/null | grep -A3 '^\[media\]'
systemctl enable --now smb wsdd
for s in samba wsdd wsdd-http; do r="rule family=\"ipv4\" source address=\"$L\" service name=\"$s\" accept"; firewall-cmd --add-rich-rule="$r" && firewall-cmd --permanent --add-rich-rule="$r"; done
```

By default Windows 11 does not allow access to shared folders without a password. Once on each PC, in
PowerShell as administrator:

```powershell
Set-SmbClientConfiguration -EnableInsecureGuestLogons $true -RequireSecuritySignature $false -Force
```

`/etc/sysconfig/wsdd` contains the network interface name (`eno1`) and the Windows workgroup (`TRUE`) —
check yours: `ip -br link`.

**Wi-Fi takes priority over the wire** (optional). If you connect to any Wi-Fi, internet traffic goes
through it while it stays connected. The home network always stays on the wire:

```bash
R=/root/atrium/rootfs
\cp -p /etc/NetworkManager/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf.bak-$(date +%Y%m%d) && install -m 644 $R/etc/NetworkManager/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf && nmcli general reload conf
```

## 14. Control: phone and RDP

**Unified Remote** turns a phone into a touchpad, keyboard and remote. The server is the official one, but
on Wayland it works through `/dev/uinput`, and it has two flaws that we fix with a patch:

- **a short tap did not click.** The server sends "press" and "release" in one frame, and GNOME loses
  such a click. The patch separates them with a 15 ms pause.
- **capital letters, Cyrillic and symbols did not type.** The server knows only simple keys. The patch
  types each character with its own key and the right modifier, and picks the layout (us or ru) for the
  character by itself. It works with any layout active on the TV.

```bash
mkdir -p /root/dist && cd /root/dist && curl -fL -A "Mozilla/5.0" -o urserver-3.14.0.2574.rpm https://www.unifiedremote.com/static/builds/server/linux-x64/2574/urserver-3.14.0.2574.rpm && echo "8fd30d91781711a4d6a4926c442a8907e46dd80ff0c376667b1efa15c01842ba  urserver-3.14.0.2574.rpm" | sha256sum -c && dnf -y install ./urserver-3.14.0.2574.rpm
cd /opt/urserver/remotes/Unified && patch -p1 --backup --suffix=.orig < /root/atrium/patches/urserver/atrium-urserver.patch
R=/root/atrium/rootfs; L=192.168.0.0/24
install -m 644 $R/etc/udev/rules.d/60-atrium-uinput.rules /etc/udev/rules.d/60-atrium-uinput.rules && udevadm control --reload && modprobe uinput
for p in 9511/udp 9512/tcp 9512/udp; do r="rule family=\"ipv4\" source address=\"$L\" port port=\"${p%/*}\" protocol=\"${p#*/}\" accept"; firewall-cmd --add-rich-rule="$r" && firewall-cmd --permanent --add-rich-rule="$r"; done
runuser -u view -- env HOME=/home/view XDG_SESSION_TYPE=wayland XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus /opt/urserver/urserver-start --no-manager --no-notify
```

- The udev rule gives the user at the screen the right to create a virtual mouse and keyboard (the
  `steam-devices` package does the same).
- The first run of `urserver-start` adds the server to `view`'s autostart by itself.
- The phone app finds the server by itself.
- If a new version of Unified Remote is out, the checksum will not match. Then take the new one, and
  `patch` will show whether the changes applied (details in [updates.md](updates.md)).

**RDP** shows the TV screen on a computer: the same session, the same desktop. It has its own login and
password, while autologin on the TV stays passwordless. The certificate is self-signed and valid for
10 years.

```bash
H=atrium.lan; IP=192.168.0.42; L=192.168.0.0/24
dnf -y install openssl
( set -e; D=/home/view/.local/share/gnome-remote-desktop/certificates; G="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus grdctl rdp"; runuser -u view -- mkdir -p -m 700 $D; runuser -u view -- openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -noenc -subj "/CN=$H" -addext "subjectAltName=DNS:$H,DNS:$(hostname),IP:$IP" -keyout $D/rdp-tls.key -out $D/rdp-tls.crt; chmod 600 $D/rdp-tls.key; $G set-tls-cert $D/rdp-tls.crt; $G set-tls-key $D/rdp-tls.key; $G disable-view-only; $G set-credentials; $G enable )
systemctl --user -M view@ enable --now gnome-remote-desktop.service
r="rule family=\"ipv4\" source address=\"$L\" service name=\"rdp\" accept"; firewall-cmd --add-rich-rule="$r" && firewall-cmd --permanent --add-rich-rule="$r"
```

`set-credentials` asks for the login (ours is `view`) and the RDP password. **Type the password in the
English layout.** If you erase Cyrillic with Backspace, fragments of bytes stay in the password, and
`grdctl` still reports success.

## 15. Games

**What we install.**

- **RetroDECK** — emulators for PS1, PS2, PS3, PSP and other consoles in one package, with a menu made
  for a gamepad.
- **Steam** — Linux and Windows games through Proton.
- **Steam Link and Moonlight** — game streaming from a powerful PC. Our PC runs Apollo (a fork of
  Sunshine), the stream is 3840×2160 at 120 fps in AV1, 150 Mbit/s. Server and client setup, the network
  and MikroTik — [streaming.md](streaming.md).
- **steam-devices** — gamepad permissions (DualSense Edge and others) for the user at the screen.

```bash
L=192.168.0.0/24
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
dnf -y install steam-devices steam && udevadm trigger --subsystem-match=hidraw
flatpak install -y --noninteractive flathub net.retrodeck.retrodeck com.valvesoftware.SteamLink com.moonlight_stream.Moonlight
r="rule family=\"ipv4\" source address=\"$L\" service name=\"steam-streaming\" accept"; firewall-cmd --add-rich-rule="$r" && firewall-cmd --permanent --add-rich-rule="$r"
R=/root/atrium/rootfs; install -m 644 $R/etc/sysctl.d/90-atrium-stream.conf /etc/sysctl.d/ && sysctl -p /etc/sysctl.d/90-atrium-stream.conf
```

`90-atrium-stream.conf` increases the UDP receive buffer: the 4K Steam Link stream overflowed the default
one.

**First run of RetroDECK** — at the TV; the setup wizard is graphical only. Choose Custom Location and in
the file chooser **select** `/srv/games`: the dialog does not accept the folder you are currently in.
RetroDECK appends `/retrodeck` by itself; ROMs, BIOS files and saves also go there. Over the network this
is `\\atrium.lan\media\games\retrodeck\roms\<system>`. The wizard installs the PS3 and PS Vita firmware by
itself. Put the PS1 and PS2 BIOS files in `bios/` — your own, dumped from your own console.

**RetroArch changes.** Make them only while RetroArch is **closed**: on exit it rewrites its file.

- **Full screen at 250 % scale.** RetroArch asks for a 3840×2160 surface in logical pixels, and the window
  slides off the screen. We set the logical screen size: 3840/2.5 × 2160/2.5 = 1536×864. With a different
  scale, recalculate.
- **Sound through PipeWire.** With `pulse` it crackled.
- **Gamepads through udev.**
- **Cross = OK**, European style.
- **Analog sticks in PS1 (SwanStation)** are always on.

```bash
pkill -u view -x retroarch; while pgrep -u view -x retroarch >/dev/null; do sleep 1; done
c=/home/view/.var/app/net.retrodeck.retrodeck/config/retroarch
\cp -p $c/retroarch.cfg $c/retroarch.cfg.bak-$(date +%Y%m%d) && \cp -p $c/retroarch-core-options.cfg $c/retroarch-core-options.cfg.bak-$(date +%Y%m%d)
sed -i -e 's/^video_fullscreen_x = .*/video_fullscreen_x = "1536"/' -e 's/^video_fullscreen_y = .*/video_fullscreen_y = "864"/' -e 's/^audio_driver = .*/audio_driver = "pipewire"/' -e 's/^input_joypad_driver = .*/input_joypad_driver = "udev"/' -e 's/^menu_swap_ok_cancel_buttons = .*/menu_swap_ok_cancel_buttons = "true"/' $c/retroarch.cfg
sed -i 's/^swanstation_Controller1_ForceAnalog = .*/swanstation_Controller1_ForceAnalog = "true"/' $c/retroarch-core-options.cfg
grep -nE '^(video_fullscreen_[xy]|audio_driver|input_joypad_driver|menu_swap_ok_cancel_buttons) ' $c/retroarch.cfg
```

To exit a game in RetroArch, press Ctrl+Q. The in-game menu is L3+R3. `.cue` files with Windows paths
inside do not start: the first line must be `FILE "<name>.bin" BINARY`.

## 16. Freeze trap

**Why.** The box froze at night while the screen was off and left no traces (12.10; a similar case on
07.10 may have had an external cause). The trap makes sure
that next time it reboots by itself and leaves a report:

- **the motherboard's hardware watchdog** (SP5100 TCO): if the kernel does not respond for 60 seconds,
  the board reboots the box;
- **a CPU lockup or a kernel error causes a panic**, followed by a reboot after 10 seconds;
- **the panic report** is written to UEFI memory (pstore); after boot, systemd moves it to
  `/var/lib/systemd/pstore`. The SSH login screen shows this as a red `pstore` line;
- **GFXOFF is off** (`amdgpu.ppfeaturemask` without bit `0x8000`). Deep sleep of the graphics core while
  the screen is off is one of the suspects. A box on mains power does not need the graphics to doze off
  (the saving is a fraction of a watt), so we keep it off for good. The kernel parameter was added in
  step 12.

```bash
R=/root/atrium/rootfs
if [ -e /etc/systemd/system.conf ]; then echo "system.conf exists - add RuntimeWatchdogSec=60 under [Manager] by hand"; else install -m 644 $R/etc/systemd/system.conf /etc/systemd/system.conf; fi
install -m 644 $R/etc/sysctl.d/90-atrium-lockup.conf /etc/sysctl.d/ && sysctl -p /etc/sysctl.d/90-atrium-lockup.conf
systemctl daemon-reexec && systemctl show -p RuntimeWatchdogUSec && cat /sys/class/watchdog/watchdog0/state
```

What to look at after a freeze — see [problems.md](problems.md), section "Night freezes".

## 17. Status screen at SSH login

When you log in over SSH you see right away: uptime, memory, both drives with their temperatures, the
network, whether the screen is on, failed services and trap reports. `atrium-login.sh` calls
`/usr/local/sbin/atrium-motd` — the same file in `/usr/local/bin` (the `sbin` → `bin` link, see the
`atrium-sysload` step).

```bash
R=/root/atrium/rootfs
install -m 755 $R/usr/local/bin/atrium-motd /usr/local/bin/atrium-motd
install -m 644 $R/etc/profile.d/atrium-login.sh /etc/profile.d/atrium-login.sh
restorecon /usr/local/bin/atrium-motd /etc/profile.d/atrium-login.sh
```

## 18. Reboot, display and check

```bash
reboot
```

**Display.** If the TV and the connection are the same as ours (LG C3 on the box's HDMI, `HDMI-1` in
GNOME), the `monitors.xml` from step 9 already sets 3840×2160 at 120 Hz, 250 % scale and SDR. Otherwise,
set this at the TV in Settings → Displays. Do not turn HDR on by hand: mpv turns it on for HDR videos (step 9,
"Auto HDR"). While HDR is on, the quick settings menu has an HDR brightness slider. The factory neutral
value is 100 %; we keep it at about 110 %. Each time HDR turns on, the slider goes back to 100 %.

**Check.** Everything should be green:

```bash
V="runuser -u view -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
systemctl --failed; systemctl --user -M view@ --failed
cat /proc/cmdline; aplay -l | grep ^card
findmnt /srv; ls -ldZ /srv
vainfo --display drm 2>&1 | grep -c VAProfile
$V gnome-extensions list --enabled --details | grep -cE "State: ACTIVE"
systemctl is-active transmission-daemon smb wsdd atrium-sysload; systemctl --user -M view@ is-active atrium-screensaver gnome-remote-desktop
firewall-cmd --list-all
cat /sys/class/watchdog/watchdog0/state
```

Expected:

- no failed services;
- `/proc/cmdline` contains our four parameters;
- `aplay -l` shows one DAC;
- `/srv` is mounted;
- more than ten VA-API profiles;
- nine extensions ACTIVE;
- all services active;
- watchdog in state `active`.

Next — [updates and what to check after them](updates.md).
