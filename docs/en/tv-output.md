# TV output: 4K 120 Hz and HDR over HDMI 2.1 — a month of searching and where the truth was

[Русская версия](../ru/tv-output.md) · [Install](install.md) · [Hardware](hardware.md) · [Updates](updates.md) · [Known problems](problems.md)

## In short

- The TV is connected **to the box's own HDMI port** with an ordinary passive **Ultra High Speed (48G)**
  cable.
- The TV receives **3840×2160 at 120 Hz, full RGB 4:4:4 color, 10-bit, HDR** (BT.2020 / PQ), with no
  compression.
- All it takes is **one kernel parameter**: `amdgpu.dcfeaturemask=0x402` (Linux 7.2 or newer).
- Active DisplayPort → HDMI 2.1 cables and adapters are **not needed**.

## Where the truth was

**The limit was in the driver, not in the hardware.**

- The Beelink SER5 MAX spec sheet lists the HDMI port as **2.0** (4K 60 Hz). Shops and the manual say the
  same.
- The Radeon 680M graphics core supports **HDMI 2.1 (FRL)**, and the port on the board carries it. Tested:
  4K 120 Hz RGB 10-bit goes through the box's HDMI, which is ~36 Gbit/s — HDMI 2.0 (up to 18 Gbit/s)
  cannot carry that.
- For years Linux had no HDMI 2.1 for AMD graphics: in 2024 the HDMI Forum refused to let AMD publish an
  open implementation. In 2026 the code did land in kernel **7.2**, but **disabled by default**: it waits
  for VRR over HDMI. It is promised to be on by default in kernel 7.4.
- Without the parameter, the driver treats HDMI as version 2.0. So the "HDMI 2.0" in our measurements was
  the driver's ceiling, not the port's.

Everything we did with cables was a workaround for the driver. And active cables bring their own trouble:
firmware, heat, getting stuck after sleep.

**About articles.** News about FRL names the parameter `amdgpu.dc_feature_mask=0x400`. That parameter
does not exist. The correct name is `amdgpu.dcfeaturemask`, the FRL bit is `0x400` (`DC_FRL_MASK` in
`drivers/gpu/drm/amd/include/amd_shared.h`), and the default value is `0x2`. So you need `0x402` to keep
the default bit. Check such things against the kernel source and `modinfo -p amdgpu`, not retellings —
these days they are not only written by people.

## How to enable it

The parameter is set together with the others in step 12 of the installation ([install.md](install.md)).
On its own:

```bash
grubby --update-kernel=ALL --args=amdgpu.dcfeaturemask=0x402
grep -q dcfeaturemask /etc/kernel/cmdline || sed -i '1s/$/ amdgpu.dcfeaturemask=0x402/' /etc/kernel/cmdline
reboot
```

On Fedora, `grubby --update-kernel=ALL` itself also adds the parameter to `/etc/default/grub`, and
sometimes to `/etc/kernel/cmdline`. That is why the second line adds it only if it is not there yet.

After the boot:

```bash
printf 'dcfeaturemask=0x%x\n' $(cat /sys/module/amdgpu/parameters/dcfeaturemask)
cat /sys/kernel/debug/dri/0000:05:00.0/amdgpu_dm_dtn_log | sed -n '/^HPO:/,/^$/p'
```

Row `[0]` of the `HPO` table (that is the HDMI 2.1 block) should show `4:4:4`, depth `10` and `4` lanes.
The `Link` field shows `Training` even with a working picture — that is normal. If the table is empty
(`HPO` is not in use), the signal goes over the old HDMI 2.0. The address `0000:05:00.0` is the graphics
card of our box; on other hardware, look at `ls /sys/kernel/debug/dri/`.

In GNOME: "Settings → Displays" → 3840×2160, 120 Hz. Do not turn HDR on by hand: the desktop runs in SDR,
and HDR turns on by itself while mpv plays an HDR video (installation, step 9, "Auto HDR"). The reason is
load: in HDR GNOME re-composes every frame, and the GPU has no headroom left for 4K HDR in the browser. On
the TV, **HDMI Ultra HD Deep Colour** must be
on for this input. The cable must be a certified **Ultra High Speed (48G)** one: simpler cables do not
hold 4K 120 Hz.

## Timeline

| Date | What we tried | What happened |
|---|---|---|
| 06.10.2026 | The box's HDMI directly | 4K 60 Hz in RGB 8-bit. 4K 100/120 Hz only in YCbCr 4:2:0 8-bit, HDR only 8-bit. We concluded the port is HDMI 2.0, as the spec sheet says |
| 10.10 | Active cable **Vention HFPBAC** DP 1.4 → HDMI 2.1 (**Chrontel CH7218** chip) | 4K 120 Hz RGB: DSC compression on DisplayPort, the cable converts to HDMI 2.1. But after the TV was turned off or the screen was blanked — a black screen with a live signal. Turning the output off and on fixed it |
| 10.10 | **Vention** DP → HDMI 2.1 adapter (**Synaptics VMM7100** chip) | up to 1080p only, a black screen at 4K |
| 12.10 | The same adapter with the 48G cable from a PS5 | the bundled HDMI cable was the culprit: with a proper one — 4K 120 Hz and CEC. But then the picture flickered, the TV lost the signal for half a second, the adapter got very hot. Removed |
| 12.10 | The CH7218 cable reflashed with **UGREEN 07.00.54** firmware | CEC appeared, the picture came back after a short screen blank |
| 13.10 | A night with the screen blanked | in the morning, after moving the mouse — "No signal". From the box's side everything was alive: the frame, the DisplayPort link, the TV's EDID. Only unplugging and replugging the cable helped. Both active cables got warm **while idle**: when it blanks the screen, the driver puts the cable chip to sleep (DPCD `0x600 = 02`), and after a long sleep the chip did not bring HDMI back up. We tried workarounds: a software unplug/replug (`trigger_hotplug`), turning the TV off over CEC |
| 13.10 | Looking for why HDMI is "2.0" | found HDMI 2.1 FRL in kernel 7.2, disabled by default. `amdgpu.dcfeaturemask=0x402` → the box's own HDMI: 4K 120 Hz, RGB 4:4:4, 10-bit, HDR, no DSC and no active cable |
| 19.10 | The TV on the PS5 input for a day | the TV stopped answering on the box's input, GNOME was left without a screen, RDP did not connect. `atrium-hdmi-keep on`: the output always "connected", the EDID from a file — RDP works whatever input the TV is on (below) |

## What we gained and what we lost

**Gained:**
- no active chip between the box and the TV: nothing to heat up, fall asleep or get stuck, nothing to
  flash;
- an uncompressed picture (before, DSC was used on DisplayPort);
- cheaper: a passive 48G cable instead of an active one.

**Lost:**
- **CEC.** CEC came from the chip in the cable, passed over the DisplayPort service channel. The box's own
  HDMI has no CEC device in Linux (`/dev/cec*` disappears). atrium does not turn the TV on over CEC; if
  waking the TV from atrium is ever needed — over the network (Wake-on-LAN and the webOS network control). A
  USB CEC dongle (Pulse-Eight) sits inline in the HDMI cable and most likely will not pass HDMI 2.1.

**Not yet (waiting for kernel 7.4):** VRR (FreeSync) and ALLM over HDMI. There was no VRR through the
active cables either.

## The TV on another input: HDMI always "connected"

Since 19.10 `atrium-hdmi-keep` is on: the box's output always counts as connected (`video=HDMI-A-1:e`),
and the kernel takes the display description from a file saved from the TV
(`drm.edid_firmware=HDMI-A-1:edid/atrium-tv.bin`). Why: a TV switched to the PS5 for a long time stops
answering on the box's input, GNOME is left without a single screen, and RDP does not connect — exactly
when it is needed. With keep, GNOME never loses the monitor: the same LG, 4K 120 Hz, HDR. When the TV
comes back, the kernel trains the HDMI 2.1 link again and sets the current mode; the picture appears by
itself. Checked on 19.10: the cable unplugged from the TV — RDP works, plugged back — 4K 120 is back. Who
needs it (not everyone), how to turn it on, off and check it — [installation, step 19](install.md); the
symptoms without it — [known problems](problems.md).

With keep, the output `status` in `/sys/class/drm` is always `connected`, and `edid` is the file itself.
Whether the TV really receives shows in the FRL table of the driver log (`atrium-hdmi-keep status`, the
`HDMI link` line): while the TV receives, the link is trained; a TV in standby drops it after a few minutes
and trains it again when turned on.

## Fallback: an active DisplayPort → HDMI 2.1 cable

If your kernel is older than 7.2 or your HDMI port does not negotiate FRL, DisplayPort with an active cable
remains. What we learned about them:

- the cable between the adapter and the TV must be Ultra High Speed (48G); the bundled Vention cable could
  not do 4K;
- the Synaptics VMM7100 flickered and got very hot for us. There is Cable Matters firmware 7.02.126 for it
  (VMMDPTool64 utility, same chip) — we have not tried it;
- the Chrontel CH7218 with the UGREEN 07.00.54 firmware worked best, but after a long screen blank it
  sometimes stayed without a signal: unplugging and replugging the cable, or turning the output off and
  on, helps (the command is in [problems.md](problems.md), section "No signal after turning off the TV or
  a long screen blank").

### Flashing the Chrontel CH7218 cable (Vention HFPBAC)

UGREEN builds its own DP134/DP135 cables on the same chip. UGREEN's instructions for the DP134 (85564) and
DP135 (85596) point to a "CH7218 Firmware Update Tool" archive: the Chrontel Chip FW Update Tool V03.03.02
utility for Windows and the file `CH7218A-IMG.G000.07.00.54`. The instructions are a UGREEN PDF dated 17.04.2026 (on
Amazon's image server, in the DP134/DP135 listing); the archive is on MediaFire as
`85564&85996-CH7218+Firmware+Update+Tool.zip.rar`. Download and check files from a file host yourself: no
firmware or tools are stored in this repository.

1. Connect the cable to the DisplayPort output of any Windows PC, with a powered-on TV at the other end.
   We used a PC with an RTX 4090: the utility works through NVIDIA.
2. CHIP **CH7218A**, Update Channel **AUX** → Get version. It should show the current version (ours was
   `05.03.75 (FLASH)`).
3. The normal path "Burn → Only Update" on the Vention cable gives `[Err]:MCU CLK mismatch!!!` and writes
   nothing.
4. The working path: **Conf_Enter → Advanced_Configuration → Update FW ALL**, tick **keep_hdcp**, file
   07.00.54, **Update And Restart**. The utility writes the firmware, then reboots the PC.
5. After the reboot, Get version → `07.00.54 (FLASH)`.

**Risk:** the utility does not back up the factory firmware, so there is no way to restore 05.03.75. The
procedure poses no risk to the graphics card: the write goes over the AUX service channel.

What else we saw: the factory 05.03.75 gave a black screen after the TV was turned off and did not pass CEC;
with 07.00.54 CEC appeared (`/dev/cec0`), waking after a short blank worked, after a night — not always.

### Software replug and CEC through the cable

For the active cable path, `src/variants/dp-cable/` keeps what we installed:
- a software DP unplug/replug right after the screen wakes up (script, service, polkit rule, a patch for the
  screensaver);
- CEC commands for the cable: TV on and off, the device list.

Description and install — `src/variants/dp-cable/README.md`.

### Flashing the Synaptics VMM7100 adapter (Cable Matters)

We **did not** flash it: we removed the Vention VMM7100 adapter earlier (flicker, heat). If you have such an
adapter with the same trouble, here is what we found:

- Cable Matters builds its 102101, 102103, 101101 and 101109 adapters on the same chip and publishes the
  firmware in its knowledge base: article EntryID=185, archive
  `https://kb.cablematters.com/index.php?View=afile&EntryID=185&AttachID=103`.
- The archive holds the `VMMDPTool64.exe` utility (Windows, run as administrator) and two firmware files:
  `Spyder_fw_DP_CM_7.02.126.fullrom` — the normal one, and `…7.02.120.fullrom` — with VRR (Cable Matters says
  it may flicker).
- Order: the adapter in the PC's DisplayPort, a powered-on screen on its HDMI side → the version on the Debug
  tab → FLASH → LOAD to FLASH → the firmware file → wait for "Action complete" → replug the adapter.
- On an adapter of another brand the utility will most likely say "Product ID did not match". According to
  the Cable Matters article, answering "Yes" flashes it past the brand check. One user reported that the
  utility did not see a non-Cable Matters adapter at all.
- Flash only if the current version is below 7.02.126. Linux does not show the build in DPCD; VMMDPTool shows
  it on the Debug tab.
- There is also an unofficial 7.02.130 (DP → HDMI, discussed on Intel Community); we could not download it.

## Sources

- [Hardware Busters — FRL: off in Linux 7.2 and enabled with a parameter, on by default later](https://hwbusters.com/news/amds-hdmi-2-1-frl-goes-default-on-in-linux-and-the-boot-flag-retires-with-it/)
- [Phoronix — FRL on by default in 7.4 together with VRR and ALLM](https://www.phoronix.com/news/Linux-7.4-AMDGPU-HDMI-2.1-Go)
- [Phoronix — FRL initially disabled by default](https://www.phoronix.com/news/AMDGPU-FRL-Disabled-By-Default)
- [amd_shared.h in kernel v7.2 (DC_FRL_MASK = 0x400)](https://github.com/torvalds/linux/blob/v7.2/drivers/gpu/drm/amd/include/amd_shared.h)
