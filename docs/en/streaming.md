# Game streaming from a PC: Apollo → Moonlight, Steam Link, and the network

[Русская версия](../ru/streaming.md) · [Install](install.md) · [Hardware](hardware.md) · [Known problems](problems.md) · [TV output](tv-output.md)

## In short

- The gaming PC (Windows, NVIDIA RTX 40) runs **Apollo**, the streaming server. atrium runs **Moonlight**, the
  client.
- The stream: **3840×2160 at 120 fps, AV1, 150 Mbit/s**, decoded by the box's GPU. The TV runs at 120 Hz, so
  the stream matches it frame for frame.
- **Steam Link** is the second option, for Steam games.
- Smoothness is decided by the **network**: a wired path without speed steps (2.5 → 1 Gbit/s) and switch
  queues that do not drop bursts. What we fixed on MikroTik is below.

## Server: Apollo on the Windows PC

**What it is.** Apollo is a fork of Sunshine, the open-source game streaming server that Moonlight talks to.
Its main addition is a **virtual display** (SudoVDA): for each stream Apollo creates a virtual monitor with
the client's resolution and refresh rate, 3840×2160 at 120 Hz. The PC does not need a real 4K 120 Hz monitor,
and its real monitors can stay off.

**Install.** Download the Windows installer from the Apollo releases on GitHub (ClassicOldSong/Apollo). The web
UI is at `https://localhost:47990` on the PC (self-signed certificate) — set the login there on first start.
The installer opens the Windows firewall ports: TCP 47984, 47989, 48010 and UDP 47998–48000, 48002, 48010.
The web UI port 47990 is meant for the PC itself.

**Pairing.** Moonlight finds the PC by itself on the LAN (mDNS) or by IP. It shows a PIN: enter it in the
Apollo web UI, PIN tab.

**Settings we use:**
- **Encoder:** NVENC on the PC's GPU, codec AV1 (RTX 40 has an AV1 encoder).
- **Virtual display:** "Headless Mode" on; "Move the Virtual Display to the bottom right" on. During the
  first stream, make the virtual display the main one in Windows Settings → Display: Windows remembers the
  layout for that display.
- **Apps:** Desktop and Steam Big Picture.
- **Command Preparations, Undo:** after a stream Windows forgets the wallpaper of each monitor (the set of
  monitors changed). `src/pc/apollo-wallpapers.ps1` puts them back:
  1. once, while the wallpapers are right: `powershell -ExecutionPolicy Bypass -File <path>\apollo-wallpapers.ps1 save`;
  2. in Apollo, Undo command: `powershell -NoProfile -ExecutionPolicy Bypass -File "<path>\apollo-wallpapers.ps1" restore`.
     It returns at once; a background copy waits until the virtual display is gone and sets the wallpapers.
- **End the stream from the PC keyboard:** `src/pc/apollo-stop.ps1`. Once:
  `powershell -ExecutionPolicy Bypass -File <path>\apollo-stop.ps1 setup` — it asks for the Apollo web UI
  login, stores it encrypted for this Windows user only (DPAPI, `apollo-cred.xml` next to the script — do not
  put it into git) and creates a Start menu shortcut with the hotkey **Ctrl+Alt+End**. The hotkey logs into
  the web API and closes the running app. Apollo keeps a session for about 90 seconds after the client
  disconnects, so end it with Quit in Moonlight or with this hotkey.

## Client: Moonlight on atrium

Installed in step 15 of the installation (Flathub `com.moonlight_stream.Moonlight`), it is in the dock.

| Setting | Value | Why |
|---|---|---|
| Resolution | 3840×2160 | native for the TV |
| Frame rate | **120 FPS** | the TV runs at 120 Hz: one stream frame per refresh, no judder |
| Bitrate | 150 Mbit/s | plenty for 4K 120 in AV1; a fraction of a gigabit link |
| Video codec | AV1 | best quality per bit; the Radeon 680M decodes it in hardware |
| Video decoder | hardware (VA-API) | the CPU stays free; in the panel VCN shows the decoder load |
| V-Sync | off | lowest latency |
| Frame pacing | off | lowest latency; turn it on if frame times look uneven |
| HDR | off | the desktop runs in SDR |
| YUV 4:4:4 | off | not needed for games, costs bandwidth |
| Display mode | full screen | |

Moonlight keeps these in `~/.var/app/com.moonlight_stream.Moonlight/config/Moonlight Game Streaming Project/Moonlight.conf`
of the TV user. During a stream, **Ctrl+Alt+Shift+S** shows the performance overlay: decoder, frame times,
dropped frames, network latency. **Ctrl+Alt+Shift+Q** quits the stream.

atrium's firewall needs nothing extra for Moonlight: the client connects out.

## Steam Link

Flathub `com.valvesoftware.SteamLink` (step 15), pairs with Steam on the PC, decodes with VA-API. Step 15 also
opens the firewall service `steam-streaming` for the LAN. Its log is
`~/.var/app/com.valvesoftware.SteamLink/data/Valve Corporation/SteamLink/streaming_client.log` of the TV user:
"Got video sequence N, expected N-1, sending lost data notification" means lost packets.

## The network: why the stream stuttered and what fixed it

**Symptom.** Steam Link stuttered every 1–3 seconds, Moonlight showed dropped frames. The log was full of
"lost data notification".

1. **The UDP receive buffer on atrium.** The counter `RcvbufErrors` (`nstat -az UdpRcvbufErrors`) grew.
   `/etc/sysctl.d/90-atrium-stream.conf` raises `net.core.rmem_default/rmem_max` to 16 MB (step 15). The
   counter stopped, but packets were still lost. Steam Link sets its own socket buffer, so for it this
   setting is a safety margin only.
2. **A speed step on the path.** The PC was on a 2.5 Gbit/s switch port, the rest of the path to atrium was
   1 Gbit/s. The PC sends each frame as a burst at 2.5 Gbit/s, and the first 1 Gbit/s port's queue
   overflows. On MikroTik this is the `tx-queue-drop` counter of that port (`/interface ethernet print stats`)
   — it had thousands. **Fix:** the PC moved to a 1 Gbit/s port, so the whole path is one speed.
3. **Short queues on MikroTik.** By default MikroTik ports use only the small hardware queue
   (`only-hardware-queue`), and bursts were still dropped now and then (every 30–60 seconds). **Fix:** a
   software FIFO queue of 500 packets on all LAN ethernet ports of every MikroTik on the path:

   ```
   /queue type add name=pfifo-500 kind=pfifo pfifo-limit=500
   /queue interface set [find where interface~"ether" and interface!="ether1"] queue=pfifo-500
   ```

   `ether1` is the WAN port on the router — leave it out there: on a 100 Mbit/s uplink 500 packets are up to
   60 ms of queue. On switches without WAN, set it on all `ether` ports. The CPU load of the switches stayed
   at 1–2 %. Check: `/queue interface print` and `tx-queue-drop` in `/interface ethernet print stats`.
   Rollback:

   ```
   /queue interface set [find where interface~"ether"] queue=only-hardware-queue
   /queue type remove pfifo-500
   ```

**Recommendations:**
- both ends on a cable; Wi-Fi only as a backup;
- one speed along the whole path, or at the speed step a switch with a large shared buffer (for example
  MikroTik CRS) instead of small switches with a few hundred kilobytes of buffer;
- the bitrate itself is not the problem: 150 Mbit/s is 15 % of a gigabit link; the problem is bursts.
