# Browser tests: method and results

[Русская версия](../ru/browser-tests.md) · [Install](install.md) · [Known problems](problems.md) · [Updates](updates.md)

How we measured video smoothness in Chrome, Chromium and Firefox from the box itself, without walking to
the TV, and what came out. The script is `src/tools/atrium-browser-bench.py`.

## Why

Dropped frames are visible by eye only at the TV, and YouTube's own numbers ("Stats for nerds") add dropped
frames themselves and need somebody at the screen. The script does what a person with a remote does: opens
a video, picks 4K, goes full screen. Then for 30 seconds it counts dropped frames, GPU and CPU load, while
the browser shows the video on the TV as usual. Every browser variant or setting goes through the same
procedure, so the results can be compared.

## One run

1. Close all browsers of the TV user.
2. Start the browser in the TV user's session (`systemd-run --user -M view@`) with a throwaway profile and a
   debugging port on `127.0.0.1` only: Chrome and Chromium — DevTools protocol (CDP), Firefox — WebDriver
   BiDi. **Firefox gets a fresh profile for every variant** (why — below, in the pitfalls).
3. Open the video (4K60 HDR, `SCJxEhG-CZQ`), decline the cookie dialog, skip ads.
4. Ask the browser about codecs the same way YouTube does (the `caps` field).
5. Ask YouTube for 2160p, play muted, go full screen **by pressing F**: browsers do not allow
   `requestFullscreen()` from a script, but a real key press works.
6. 15 seconds of warm-up (quality switch and going full screen drop a batch of frames, not counted).
7. 30 seconds of measuring.
8. Save logs: for Chrome the pages `chrome://gpu` and `chrome://version`, for Firefox the decoder log
   (`MOZ_LOG`).

At the end the script closes the browsers and deletes the throwaway profiles (the copy of the real profile
holds cookies).

## What is measured

| Field | Source | Meaning |
|---|---|---|
| `dropped N/M` | `video.getVideoPlaybackQuality()` over 30 s | dropped of shown frames; 60 fps × 30 s ≈ 1800 |
| resolution, codec | YouTube player `getStatsForNerds()` | what YouTube actually served (`vp09` — VP9, `av01` — AV1, `avc1` — H.264) |
| `hdr`, `fs` | `matchMedia('(dynamic-range: high)')`, `document.fullscreenElement` | does the browser see an HDR screen; did full screen engage |
| `gpu busy` | `/sys/class/drm/card1/device/gpu_busy_percent`, 5 times a second | average GPU load and the share of time at 95–100 % |
| `browser gfx`, `vcn` | `/proc/<pid>/fdinfo` (DRM fdinfo), per browser process | GPU time for drawing and for the video decoder (VCN) |
| `shell gfx` | the same for gnome-shell | how much GPU GNOME spends composing the screen |
| `screen` | `/sys/kernel/debug/dri/1/{state,framebuffer}` | whose buffer is on screen and its format (`XR30` — 10 bit, `AR24` — 8 bit) |
| `caps` | `MediaSource.isTypeSupported` and `navigator.mediaCapabilities.decodingInfo` for 4K60 | `ms` — supported; `s`/`m`/`e` — supported / smooth / power efficient |
| `cpu` | `/proc/<pid>/stat` per process kind | browser CPU, % of one core |
| `raf` | `requestAnimationFrame` for 3 seconds | how often the browser gives the page a frame (normal ≈ the screen refresh, 120), the longest gap, gaps over 20 ms |

## How to run

As root on the box:

```bash
python3 atrium-browser-bench.py                          # every variant (long: ~75 s per variant)
python3 atrium-browser-bench.py chrome-base firefox-base # only these
python3 atrium-browser-bench.py firefox                  # every variant whose name starts with firefox-
```

Do not touch the mouse or the remote during the test: the browser is full screen, the video is muted.
Results are appended to `/tmp/atrium-browser-bench.txt` (each run is a block starting with `===`), Firefox
logs go to `/tmp/atrium-bench-mozlog/`.

A new variant is one line in `VARIANTS`: for Chrome the third field is command-line flags, for Firefox it
is `user_pref(...)` lines for the `user.js` of the throwaway profile.

## Pitfalls

- **A shared profile spoils Firefox.** Firefox remembers in the profile how smoothly each codec played and
  tells YouTube. After one bad variant YouTube served 1080p to every following one. So every Firefox
  variant gets its own clean profile.
- **Few frames — the result is invalid.** If far fewer than 1800 frames were shown in 30 seconds, the video
  stalled (buffering) or YouTube served 30 fps.
- **`fs=n`** — full screen did not engage; do not compare such a result with the others.
- **YouTube picks the format itself.** Once Firefox without any settings got AV1 1080p instead of the usual
  VP9 4K. Check in the line what actually played.
- **The batch at the start** (quality switch, full screen, resuming for a signed-in user) is the `start`
  field; it is not part of the measurement.
- **"Stats for nerds"** on top of the video adds dropped frames itself (variant `chrome-real-auto-stats`).
- **Chrome 136+** does not open a debugging port on the default profile: hence a throwaway profile or a copy
  of it (`chrome-real`).
- **Firefox `about:support`** cannot be opened over the debugging port — the `MOZ_LOG` log replaces it.

## Variants

| Variant | What it changes |
|---|---|
| `chrome-base` | Chrome as is |
| `chrome-overlay` | `--enable-features=WaylandOverlayDelegation` |
| `chrome-zerocopy` | `AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL` |
| `chrome-overlay-zerocopy` | both |
| `chrome-vulkan` | ANGLE on Vulkan |
| `chrome-nohdr` | Chrome does not see the HDR screen |
| `chrome-base-auto`, `chrome-base-high` | GPU clock mode for the test |
| `chrome-real-auto`, `-stats`, `-noext` | a copy of the real profile; with "Stats for nerds"; without extensions |
| `chromium-base` | Chromium as is |
| `firefox-base` | Firefox as is |
| `firefox-av1` | no VP9 for MediaSource, so YouTube serves AV1 |
| `firefox-sysffmpeg` | the system ffmpeg instead of the bundled ffvpx |
| `firefox-av1-sysffmpeg` | both |
| `firefox-hwforce` | hardware decoding forced on |
| `firefox-nolayer` | without the new WebRender compositor that Fedora turns on |
| `firefox-hwwr`, `firefox-swwr` | WebRender forced on the GPU / on the CPU |
| `firefox-hwwr-fr120` | `layout.frame_rate=120` |
| `firefox-hwwr-timer120`, `firefox-timer120` | `widget.wayland.vsync.enabled=false` + `layout.frame_rate=120` (with forced WebRender and without) |
| `firefox-hwwr-nofrac` | without Wayland fractional scaling |

## Results

The box: Ryzen 7 7735U, Radeon 680M, Fedora 44, GNOME 50 (Wayland), TV 3840×2160 at 120 Hz, 250 % scale.

### Chrome and Chromium, 2026-10-13

The desktop was in HDR then. Full screen:

| Variant | Video | Dropped | GPU: average / time at 95–100 % | Browser / gnome-shell |
|---|---|---|---|---|
| `chrome-base` | AV1 10 bit HDR | 4 of 1809 (0.2 %) | 61 % / 52 % | 30 % / 33 % |
| `chrome-overlay` | AV1 HDR | 3 of 1807 (0.2 %) | 65 % / 55 % | 32 % / 36 % |
| `chrome-nohdr` | VP9 SDR | 2 of 1810 (0.1 %) | **13 % / 7 %** | 5 % / 18 % |
| `chromium-base` | AV1 HDR | 4 of 1808 (0.2 %) | 61 % / 54 % | 28 % / 31 % |
| `chrome-real-auto` | AV1 HDR | 8 of 1805 (0.4 %) | 78 % / 69 % | 56 % / 30 % |
| `chrome-real-auto-stats` | AV1 HDR | 9 of 1807 (0.5 %) | 77 % / 73 % | 58 % / 33 % |

Windowed: `chrome-zerocopy` and `chrome-overlay-zerocopy` — 4–5 of ~1810 (0.2–0.3 %), the same as without;
`chrome-vulkan` — VP9 decoded by the CPU (VCN 0 %), **545 of 1817 (30 %)**.

**Conclusion.** In HDR Chrome draws the frame in a 16-bit format, and GNOME composes the whole screen in
HDR again: half of the time the GPU is 95–100 % busy. Without HDR — 13 %. Flags do not help, Vulkan
breaks the hardware decoder. **Fix:** the desktop in SDR, HDR only for movies in mpv (install step 9,
"Auto HDR").

### Firefox 158, 2026-10-14

The desktop in SDR, full screen, a fresh profile for every variant.

| Run | Variant | Video | Dropped | CPU | Page frames |
|---|---|---|---|---|---|
| 1 | `firefox-base` | VP9 4K | 330 of 1805 (18.3 %) | — | — |
| 1 | `firefox-av1` | **H.264 1080p** | 330 of 1810 (18.2 %) | — | — |
| 1 | `firefox-sysffmpeg` | VP9 4K | 294 of 1806 (16.3 %) | — | — |
| 1 | `firefox-av1-sysffmpeg` | H.264 1080p | 220 of 1810 (12.2 %) | — | — |
| 1 | `firefox-hwforce` | VP9 4K | 248 of 1808 (13.7 %) | — | — |
| 1 | `firefox-nolayer` | VP9 4K, the video stalled | 119 of 378 | — | — |
| 2 | `firefox-base` | VP9 4K | 326 of 1810 (18.0 %) | 46 % | 91/s, 98 hitches |
| 2 | `firefox-hwwr` | VP9 4K | 287 of 1810 (15.9 %) | 47 % | 113/s, 3 hitches |
| 2 | `firefox-swwr` | VP9 4K | 1563 of 1791 (87 %) | 295 % | 152/s |
| 3 | `firefox-hwwr` | AV1 1080p 30 fps (YouTube's choice) | 0 of 903 | 27 % | 124/s |
| 3 | `firefox-hwwr-fr120` | VP9 4K, not full screen | 213 of 897 (23.7 %) | 54 % | 89/s |
| 3 | `firefox-hwwr-timer120` | VP9 4K, not full screen | 1 of 1366 (0.1 %) | 51 % | 120/s, 0 hitches |
| 3 | `firefox-hwwr-nofrac` | VP9 4K | 305 of 1812 (16.8 %) | 52 % | 97/s |
| 4 | `firefox-base` | VP9 4K | 258 of 1809 (14.3 %) | 51 % | 86/s, 76 hitches |
| 4 | `firefox-timer120` | VP9 4K | **1 of 1810 (0.1 %)** | 46 % | 119/s, 1 hitch |
| 4 | `firefox-hwwr-timer120` | VP9 4K | **0 of 1810 (0 %)** | 43 % | 119/s, 1 hitch |
| 5 | `firefox-base` with the policy | VP9 4K | **2 of 1809 (0.1 %)** | 46 % | 119/s, 1 hitch |

The video decoder (VCN) in every VP9 4K variant is about 50 %; the `MOZ_LOG` log shows VA-API, a 4K frame
in 0.45 ms. In every variant `caps` is `ms/sme`: Firefox says it plays VP9, AV1 and H.264 in 4K60 smoothly
and power-efficiently.

**Conclusion.**
- codecs and ffmpeg are not the cause: the GPU decodes with a huge margin;
- YouTube does not serve AV1 to Firefox: without VP9 it is H.264 1080p, so extensions like
  enhanced-h264ify do not help;
- WebRender already runs on the GPU (the software one takes 3 cores and drops 87 %);
- **the frame clock is the cause:** the frames from GNOME on Wayland come unevenly (86–91 a second instead
  of 120). On its own 120 Hz timer Firefox draws evenly, and the drops go away.

**Fix:** the Firefox policy `widget.wayland.vsync.enabled = false`, `layout.frame_rate = 120`
(`/etc/firefox/policies/policies.json`, install step 9; more in "Known problems", "Dropped frames in
Firefox").
