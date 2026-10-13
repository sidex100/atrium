# Hardware, BIOS, TV output, drives

[Русская версия](../ru/hardware.md) · [Install](install.md) · [Updates](updates.md) · [Known problems](problems.md)

## Components

| What | Model | Notes |
|---|---|---|
| Box | **Beelink SER5 MAX** | AMD Ryzen 7 7735U: 8 cores / 16 threads, Zen 3+, up to 4.75 GHz |
| Graphics | Radeon 680M (12 CU, RDNA 2), VCN 3 block | hardware decoding of H.264, HEVC (incl. 10-bit), VP9 (incl. 10-bit), AV1; **no VC-1** (the CPU decodes it, and that is enough) |
| Memory | 24 GB LPDDR5, soldered | 4 GB is given to graphics (BIOS setting), the system sees ~19 GB |
| System drive | Crucial P3 Plus 1 TB (CT1000P3PSSD8) | M.2 slot 1 (PCIe 4.0 x4, root port 00:01.1), factory-installed |
| Media drive | **WD Blue SN5000 2 TB** (WDS200T4B0E) | M.2 slot 2 (PCIe 4.0 x4, port 00:02.4); TLC, 900 TBW; `/srv` |
| Network | Realtek 2.5GbE (`eno1`) | we use the wired connection |
| Wi-Fi / BT | MediaTek MT7921 (Wi-Fi 6) / MediaTek | Wi-Fi is a backup, BT is for the gamepads and the mouse |
| Outputs | HDMI, DisplayPort 1.4, USB-C 10 Gbit/s with video | the spec sheet says HDMI 2.0, but it carries HDMI 2.1 (see "TV output"); no Thunderbolt or USB4 |
| TV | **LG OLED65C36LC** (C3, 2023) | 4K 120 Hz, HDR10, all 4 inputs are HDMI 2.1 |
| TV cable | an ordinary passive HDMI **Ultra High Speed (48G)** cable into the box's HDMI | ours is the one that came with the PS5 |
| Sound | SMSL USB DAC | UAC2, no drivers needed; the box's built-in audio is disabled |
| Control | phone (Unified Remote), DualSense Edge, Xbox gamepad, Logitech MX Anywhere 2S mouse | gamepads and mouse over Bluetooth |

Idle power draw is 3–4 W at the CPU. Idle temperature is 45–55 °C, up to 75 °C under full
load.

Important: the drive names `nvme0` and `nvme1` reflect the order in which drives are detected at boot,
**not** the slot. They change from boot to boot. The system refers to drives by UUID, and commands
refer to them by model.

## BIOS

We run **ASER5012**. The factory BIOS for the 24 GB line is ASER5009. The update is done **from Windows**,
which comes preinstalled on the box, before installing Linux:

1. From the Beelink support site, download the BIOS archive for the SER5 MAX (Ryzen 7 7735U). The file
   `ASER5012.BIN` from the SER5-MAX-7735 folder ("Only Aser501X can flash") is byte-for-byte identical to
   the file from the SER5-MAX-6800 1G/24GB folder ("ASER50XX can update").
2. Run `winflash.CMD` as administrator. This is the AMI AFU utility with the flags `/P /B /N /K /X /R`,
   where `/X` disables the board ID check.
3. After the reboot, check the version in the BIOS.

Why: according to reports on the Beelink forum, with 5012 the 7735U's graphics core is no longer capped
at 15 W. **Risk:** flashing a BIOS with the ID check disabled is your own responsibility. If you are
worried, skip this step: atrium also works on the factory BIOS.

## BIOS settings

**Del** at power-on opens the BIOS, **F7** opens the boot menu. Everything else stays at the defaults.

| Setting | Value | Why |
|---|---|---|
| ACPI: Hibernation, Sleep | off | no sleep, ever: the box runs as a server |
| PCIe ASPM (all 4 ports) | Disabled | PCIe links do not go to sleep: no NVMe or network stalls, no wake-up delays |
| NB Azalia (HDMI/DP audio) | Disabled | sound goes only through the USB DAC |
| Wake On Voice | Disabled | not needed |
| Network Stack, LAN PXE ROM | Disabled | network boot is not needed, booting is faster |
| fTPM | Route to SPI TPM, Security Device Support: Disable | a media center does not need a TPM |
| UMA Frame Buffer Size | **4G** | video memory for emulators up to PS3 |
| FCH → Ac Power Loss Options | Always On | the box powers on by itself after a power outage |
| Quiet Boot | Disabled | boot messages are visible |
| Setup Prompt Timeout | 5 | time to press Del |
| Secure Boot | off (as shipped) | not needed. It can only be enabled here, in the BIOS; the Microsoft UEFI CA 2011/2023 keys are already in the database, so the Fedora bootloader boots with it on |

The built-in analog audio (`1022:15e3`) cannot be turned off in the BIOS: the Audio IOs item has no
Disabled option. It is hidden by the kernel parameter `pci-stub.ids=1022:15e3` (installation, step 12).

## TV output

The TV is connected to **the box's own HDMI port** with a passive Ultra High Speed (48G) cable:
3840×2160 at 120 Hz, RGB 4:4:4, 10-bit, HDR, no compression. The Beelink spec sheet lists this port as
HDMI 2.0, but the graphics core supports HDMI 2.1 (FRL) and the port carries it. In Linux, FRL for amdgpu
has existed since kernel 7.2, but it is disabled by default. The kernel parameter
`amdgpu.dcfeaturemask=0x402` turns it on (installation, step 12). Without the parameter, HDMI works as 2.0:
4K 60 Hz in RGB 8-bit, or 4K 120 Hz only in YCbCr 4:2:0.

Active DisplayPort → HDMI 2.1 cables are not needed. How we struggled with them for a month, where the
truth was, how to check that HDMI 2.1 is in use, and the fallback with an active cable (including the
Chrontel CH7218 flashing) — see [tv-output.md](tv-output.md).

The box's own HDMI has no CEC in Linux: CEC used to come from the chip in the active cable.

## LG OLED C3 TV

| Setting | Value | Why |
|---|---|---|
| Input | any HDMI (ours is HDMI 4) | on the C3 all four inputs are HDMI 2.1 with 4K 120 Hz; eARC is on HDMI 2 |
| HDMI Ultra HD Deep Colour | on for this input | otherwise the TV will not accept 4K 120 Hz with full color |
| Aspect Ratio | "Original" | pixel for pixel; webOS 23 has no separate Just Scan |
| **Screen Shift** (OLED Care) | **off** | it shifts the picture by a few pixels; a 4 px strip on the left was missing |
| "PC" input icon | not set | we have not compared with and without it |
| SIMPLINK (CEC) | optional | needed by the PS5 and other devices; atrium's own HDMI has no CEC |
| Brightness, picture mode | to taste | FILMMAKER MODE is good for SDR |

The OLED is protected like this: after 15 minutes of idle a screensaver starts, after 30 minutes the
screen is blanked, plus the TV's own auto power-off.

To check whether the TV crops the edges: `src/wallpaper/make_edge_test.py` generates a test wallpaper with
strips 1–16 px thick along each edge.

## Sound

- The USB DAC (ours is an SMSL, UAC2) is the **only** sound card in the system. HDMI audio is disabled in
  the BIOS, and the built-in analog audio is hidden via `pci-stub`.
- PipeWire runs at 48 kHz. When a single stream is playing, the DAC switches to the file's sample rate
  (44.1–192 kHz), without resampling (`/etc/pipewire/pipewire.conf.d/50-atrium-rates.conf`).
- To check the rate during playback: `cat /proc/asound/card0/pcm0p/sub0/hw_params`.
- Volume is controlled in software; the DAC's knob stays in one position. Dolby/DTS passthrough is turned
  off in the players: the DAC is stereo.

## Drives

**System drive: Crucial P3 Plus.** Its firmware P9CR411 is a Beelink build. Crucial's server answers "no
updates available", and the latest public version (P9CR40D) is older. There is nothing to update to and no
reason to.

### WD Blue SN5000 firmware

WD officially updates its drives only from Windows (WD Dashboard). But the firmware files are on their
server, and `nvme-cli` installs them on Linux. We had **291020WD** and now have **291050WD**, the latest for
the SN5000 500 GB/1 TB/2 TB, dated 13 March 2026.

The firmware file is described in `https://wddashboarddownloads.wdc.com/wdDashboard/firmware/WD_Blue_SN5000_2TB/291050WD/device_properties.xml`:
- install mode: mode3;
- it installs on top of 291000WD, 291010WD or 291020WD.

**The WD server's certificate expired on 27 November 2025**, so we download with a check against the
server's key fingerprint rather than the certificate. If WD renews the certificate, download with plain
`curl` without `-k`.

```bash
dnf -y install nvme-cli && mkdir -p /root/dist && cd /root/dist && curl -fsS -k --pinnedpubkey 'sha256//o7rO/T+OE4eHjYAaM71w35gNKlfT/dX4QzgZDDRDhxA=' -o 291050WD.fluf https://wddashboarddownloads.wdc.com/wdDashboard/firmware/WD_Blue_SN5000_2TB/291050WD/291050WD.fluf && echo "6c45aeb16cee701e03d286adf9ce9a7ccfc89b2fc13678733e990d30b7fba44b  291050WD.fluf" | sha256sum -c
```

Flashing. The command finds the drive by model on its own and stops if the version is not 291020WD or the
drive is mounted:

```bash
D=$(for c in /sys/class/nvme/nvme*; do [ "$(xargs < $c/model)" = "WD Blue SN5000 2TB" ] && echo /dev/${c##*/}; done); echo "WD = $D"; [ -n "$D" ] && [ "$(xargs < /sys/class/nvme/${D##*/}/firmware_rev)" = "291020WD" ] && ! grep -q "^${D}n1" /proc/mounts && cd /root/dist && nvme fw-download $D --fw=291050WD.fluf && { nvme fw-commit $D --slot=2 --action=3; sleep 3; nvme fw-log $D; nvme id-ctrl $D | grep -E "^(mn|fr) "; }
```

After this, reboot: the kernel logs "controller capabilities changed, reset may be required". The drive
erases the old firmware in slot 1, so there is no rollback.
