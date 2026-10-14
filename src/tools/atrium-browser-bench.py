#!/usr/bin/python3
# atrium-browser-bench - dropped frames of 4K HDR YouTube in Chrome / Chromium / Firefox with different
# flags, measured from the box itself (nobody has to look at the TV). Run as root on atrium.
#   python3 atrium-browser-bench.py                 # all variants
#   python3 atrium-browser-bench.py chrome-base firefox-base
#   python3 atrium-browser-bench.py firefox     # every variant whose name starts with "firefox"
# Each variant: close the browsers of user view, start one in view's session with a throwaway profile and
# a local-only debugging port (127.0.0.1), play the video full screen in 4K, warm up, then measure:
# dropped / total frames (from the page), GPU time of the browser and of gnome-shell (DRM fdinfo),
# video engine time, GPU busy, who owns the framebuffer on the screen. Results: /tmp/atrium-browser-bench.txt
# 2026-10-13: written to find why Chrome drops frames on 4K HDR YouTube at 4K 120 Hz.
import base64, json, os, re, signal, socket, struct, subprocess, sys, time, urllib.request

URL = "https://www.youtube.com/watch?v=SCJxEhG-CZQ"
PORT = 9222
WARM = 15        # s after full screen before measuring
MEAS = 30        # s of measuring
VIEW = "view"
PROFILES = "/home/view/.cache/atrium-bench"
OUT = "/tmp/atrium-browser-bench.txt"
DRI = "/sys/kernel/debug/dri/1"
CARD = "/sys/class/drm/card1/device"

DIRS = {"chrome": "/opt/google/chrome/", "chrome-real": "/opt/google/chrome/", "chromium": "/usr/lib64/chromium-browser/",
        "firefox": "/usr/lib64/firefox/"}
VARIANTS = [
    ("chrome-base", "chrome", []),
    ("chrome-overlay", "chrome", ["--enable-features=WaylandOverlayDelegation"]),
    ("chrome-zerocopy", "chrome",
     ["--enable-features=AcceleratedVideoDecodeLinuxGL,AcceleratedVideoDecodeLinuxZeroCopyGL"]),
    ("chrome-overlay-zerocopy", "chrome",
     ["--enable-features=WaylandOverlayDelegation,AcceleratedVideoDecodeLinuxGL,"
      "AcceleratedVideoDecodeLinuxZeroCopyGL"]),
    ("chrome-vulkan", "chrome",
     ["--use-angle=vulkan", "--enable-features=Vulkan,VulkanFromANGLE,DefaultANGLEVulkan"]),
    ("chrome-nohdr", "chrome", ["--disable-features=WaylandWpColorManagerV1"]),
    ("chromium-base", "chromium", []),
    ("firefox-base", "firefox", []),
    # 2026-10-13: the same Chrome with the GPU clock policy switched for the run (restored afterwards)
    ("chrome-base-auto", "chrome", [], "auto"),
    ("chrome-base-high", "chrome", [], "high"),
    # 2026-10-13: a copy of the real profile of view (extensions, tabs, login); +stats = "Stats for nerds" shown
    ("chrome-real-auto", "chrome-real", [], "auto"),
    ("chrome-real-auto-stats", "chrome-real", [], "auto", True),
    ("chrome-real-noext", "chrome-real", ["--disable-extensions"], "auto"),
    # 2026-10-14: Firefox - for "firefox" the third field is extra user.js lines (prefs) instead of flags.
    #   av1: no VP9 for media source -> YouTube serves AV1 (hardware AV1 decode on the Radeon 680M)
    #   sysffmpeg: VP8/VP9/AV1 through the system ffmpeg (RPM Fusion) instead of the bundled ffvpx
    #   hwforce: hardware decoding on, whatever the blocklist says
    #   nolayer: without the WebRender layer compositor that Fedora turns on
    ("firefox-av1", "firefox", ['user_pref("media.mediasource.vp9.enabled", false);']),
    ("firefox-sysffmpeg", "firefox", ['user_pref("media.ffvpx.enabled", false);']),
    ("firefox-av1-sysffmpeg", "firefox", ['user_pref("media.mediasource.vp9.enabled", false);',
                                          'user_pref("media.ffvpx.enabled", false);']),
    ("firefox-hwforce", "firefox", ['user_pref("media.hardware-video-decoding.force-enabled", true);',
                                    'user_pref("media.ffmpeg.vaapi.enabled", true);']),
    ("firefox-nolayer", "firefox", ['user_pref("gfx.webrender.layer-compositor", false);']),
    # 2026-10-14: decoding is not the problem (VA-API, 0.45 ms a frame) - is WebRender drawing on the GPU?
    ("firefox-hwwr", "firefox", ['user_pref("gfx.webrender.all", true);',
                                 'user_pref("gfx.webrender.software", false);']),
    ("firefox-swwr", "firefox", ['user_pref("gfx.webrender.software", true);']),
    # 2026-10-14: WebRender is on the GPU already, frames are lost when they are handed to GNOME - the frame clock:
    #   fr120: refresh fixed at 120; timer120: no Wayland frame callbacks, a 120 Hz timer instead;
    #   nofrac: without Wayland fractional scaling (the screen is at 250 %)
    ("firefox-hwwr-fr120", "firefox", ['user_pref("gfx.webrender.all", true);',
                                       'user_pref("gfx.webrender.software", false);',
                                       'user_pref("layout.frame_rate", 120);']),
    ("firefox-hwwr-timer120", "firefox", ['user_pref("gfx.webrender.all", true);',
                                          'user_pref("gfx.webrender.software", false);',
                                          'user_pref("widget.wayland.vsync.enabled", false);',
                                          'user_pref("layout.frame_rate", 120);']),
    # 2026-10-14: timer120 above gave 0.1 % - the same without forcing WebRender (only the frame clock changed)
    ("firefox-timer120", "firefox", ['user_pref("widget.wayland.vsync.enabled", false);',
                                     'user_pref("layout.frame_rate", 120);']),
    ("firefox-hwwr-nofrac", "firefox", ['user_pref("gfx.webrender.all", true);',
                                        'user_pref("gfx.webrender.software", false);',
                                        'user_pref("widget.wayland.fractional-scale.enabled", false);']),
]

STATE_JS = r"""(() => { const v = document.querySelector('video'); const p = document.getElementById('movie_player');
 let s = {}; try { s = (p && p.getStatsForNerds) ? p.getStatsForNerds() : {}; } catch (e) {}
 const q = (v && v.getVideoPlaybackQuality) ? v.getVideoPlaybackQuality() : null;
 return JSON.stringify({host: location.host, ad: !!(p && p.classList.contains('ad-showing')),
  playing: v ? !v.paused : false, w: v ? v.videoWidth : 0, h: v ? v.videoHeight : 0,
  dropped: q ? q.droppedVideoFrames : -1, total: q ? q.totalVideoFrames : -1,
  fs: !!document.fullscreenElement, hdr: matchMedia('(dynamic-range: high)').matches,
  codecs: String(s.codecs || ''), color: String(s.color || ''),
  logged: !!(window.ytcfg && ytcfg.get && ytcfg.get('LOGGED_IN')),
  logo: (() => { try { return ytInitialData.topbar.desktopTopbarRenderer.logo.topbarLogoRenderer.iconImage.iconType; }
          catch (e) { return ''; } })()}); })()"""
START_JS = r"""(async () => { const v = document.querySelector('video'); const p = document.getElementById('movie_player');
 try { p.setPlaybackQualityRange('hd2160', 'hd2160'); } catch (e) {}
 try { v.muted = true; await v.play(); } catch (e) {}
 try { if (!document.fullscreenElement) await (p || v).requestFullscreen(); } catch (e) {}
 return 'ok'; })()"""
SKIP_JS = r"""(() => { for (const b of document.querySelectorAll('.ytp-skip-ad-button, .ytp-ad-skip-button, .ytp-ad-skip-button-modern'))
 b.click(); return 'ok'; })()"""
CONSENT_JS = r"""(() => { for (const b of document.querySelectorAll('button, input[type=submit]')) {
 const t = (b.innerText || b.value || '').toLowerCase(); if (t.includes('reject') || t.includes('accept')) { b.click(); return t; } }
 return ''; })()"""

FIREFOX_PREFS = """user_pref("media.autoplay.default", 0);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.aboutwelcome.enabled", false);
user_pref("datareporting.policy.dataSubmissionPolicyBypassNotification", true);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("full-screen-api.warning.timeout", 0);
"""


class WS:
    """Minimal WebSocket client (stdlib only) for the browser debugging port."""
    def __init__(self, url):
        hostport, _, path = url[len("ws://"):].partition("/")
        host, _, port = hostport.partition(":")
        self.s = socket.create_connection((host, int(port)), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
                        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                        f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.s.recv(4096)
            if not chunk:
                raise RuntimeError("websocket handshake: connection closed")
            buf += chunk
        head, _, self.buf = buf.partition(b"\r\n\r\n")
        status = head.split(b"\r\n")[0]
        if b" 101" not in status:
            raise RuntimeError("websocket handshake: " + status.decode(errors="replace"))
        self.next_id = 0

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(65536)
            if not chunk:
                raise RuntimeError("websocket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _frame(self, op, data):
        hdr = bytearray([0x80 | op])
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        mask = os.urandom(4)
        hdr += mask
        self.s.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2)
            op, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            mask = self._read(4) if b2 & 0x80 else None
            payload = self._read(n)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if op == 8:
                raise RuntimeError("websocket closed by the browser")
            if op == 9:
                self._frame(0xA, payload)
                continue
            if op in (0, 1, 2):
                msg += payload
                if b1 & 0x80:
                    return json.loads(msg)

    def call(self, method, params):
        self.next_id += 1
        mid = self.next_id
        self._frame(1, json.dumps({"id": mid, "method": method, "params": params}).encode())
        while True:
            m = self.recv()
            if m.get("id") == mid:
                if m.get("error"):
                    raise RuntimeError(f"{method}: {m.get('error')} {m.get('message', '')}")
                return m.get("result", {})


class ChromePage:
    def __init__(self):
        url = None
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=2))
                pages = [t for t in tabs if t.get("type") == "page" and URL.split("v=")[1] in t.get("url", "")]
                if pages:
                    url = pages[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                pass
            time.sleep(1)
        if not url:
            raise RuntimeError("no YouTube tab on the debugging port")
        self.ws = WS(url)

    def eval(self, expr):
        r = self.ws.call("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                              "awaitPromise": True, "userGesture": True})
        if r.get("exceptionDetails"):
            raise RuntimeError("js: " + str(r["exceptionDetails"].get("text")))
        return r["result"].get("value")

    def key_f(self):
        # 2026-10-13: requestFullscreen() from a script is refused; a real key press "f" (YouTube) works
        self.ws.call("Page.bringToFront", {})
        for t in ("keyDown", "keyUp"):
            self.ws.call("Input.dispatchKeyEvent", {"type": t, "key": "f", "code": "KeyF", "text": "f",
                                                    "windowsVirtualKeyCode": 70, "nativeVirtualKeyCode": 70})


class FirefoxPage:
    def __init__(self):
        self.ws = None
        for _ in range(60):
            try:
                self.ws = WS(f"ws://127.0.0.1:{PORT}/session")
                break
            except Exception:
                time.sleep(1)
        if not self.ws:
            raise RuntimeError("Firefox debugging port not reachable")
        self.ws.call("session.new", {"capabilities": {}})
        self.ctx = self.ws.call("browsingContext.getTree", {})["contexts"][0]["context"]

    def eval(self, expr):
        r = self.ws.call("script.evaluate", {"expression": expr, "target": {"context": self.ctx},
                                             "awaitPromise": True, "userActivation": True})
        if r.get("type") == "exception":
            raise RuntimeError("js: " + str(r.get("exceptionDetails", {}).get("text")))
        return r["result"].get("value")

    def key_f(self):
        self.ws.call("input.performActions", {"context": self.ctx, "actions": [
            {"type": "key", "id": "kbd", "actions": [{"type": "keyDown", "value": "f"},
                                                     {"type": "keyUp", "value": "f"}]}]})


def view_uid():
    return int(subprocess.run(["id", "-u", VIEW], capture_output=True, text=True).stdout)


def pids(prefix=None, comm=None):
    uid, out = view_uid(), []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            if os.stat(f"/proc/{d}").st_uid != uid:
                continue
            if prefix and not os.readlink(f"/proc/{d}/exe").startswith(prefix):
                continue
            if comm and open(f"/proc/{d}/comm").read().strip() != comm:
                continue
            out.append(int(d))
        except OSError:
            pass
    return out


def close_browsers():
    for sig in (signal.SIGTERM, signal.SIGKILL):
        left = [p for d in DIRS.values() for p in pids(d)]
        if not left:
            return
        for p in left:
            try:
                os.kill(p, sig)
            except OSError:
                pass
        for _ in range(20):
            time.sleep(0.5)
            if not [p for d in DIRS.values() for p in pids(d)]:
                return


def gpu_ns(pidlist):
    """pid -> (gfx ns, video engine ns), each DRM client counted once."""
    res = {}
    for p in pidlist:
        clients = {}
        try:
            fds = os.listdir(f"/proc/{p}/fdinfo")
        except OSError:
            continue
        for fd in fds:
            try:
                txt = open(f"/proc/{p}/fdinfo/{fd}").read()
            except OSError:
                continue
            if "drm-client-id" not in txt:
                continue
            cid, g, v = None, 0, 0
            for line in txt.splitlines():
                k, _, val = line.partition(":")
                val = val.strip()
                if k == "drm-client-id":
                    cid = val
                elif k == "drm-engine-gfx":
                    g = int(val.split()[0])
                elif k.startswith(("drm-engine-dec", "drm-engine-enc", "drm-engine-jpeg")):
                    v += int(val.split()[0])
            clients[cid] = (g, v)
        if clients:
            res[p] = (sum(c[0] for c in clients.values()), sum(c[1] for c in clients.values()))
    return res


def cpu_ticks(pidlist):
    """pid -> (CPU ticks, process kind): Firefox -contentproc <kind> / Chrome --type=<kind>, else main."""
    res = {}
    for p in pidlist:
        try:
            stat = open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split()
            args = open(f"/proc/{p}/cmdline").read().split("\0")
        except OSError:
            continue
        args = [a for a in args if a]
        kind = "main"
        if "-contentproc" in args and args:
            kind = args[-1]
        for a in args:
            if a.startswith("--type="):
                kind = a[len("--type="):]
        res[p] = (int(stat[11]) + int(stat[12]), kind)   # utime + stime
    return res


def cpu_line(a, b, secs):
    # 2026-10-14: CPU of the browser by process kind, % of one core
    tck, per = os.sysconf("SC_CLK_TCK"), {}
    for p, (t, kind) in b.items():
        if p in a:
            per[kind] = per.get(kind, 0) + (t - a[p][0])
    return " ".join(f"{k} {100.0 * v / (secs * tck):.0f}%" for k, v in sorted(per.items(), key=lambda x: -x[1]) if v)


# 2026-10-14: how often the page gets a frame (requestAnimationFrame follows the display refresh the browser
# sees: ~120 here); max gap and gaps longer than 20 ms show stalls in the browser's own drawing
RAF_JS = r"""new Promise(res => { const t = []; const f = (ts) => { t.push(ts);
 if (ts - t[0] < 3000) { requestAnimationFrame(f); return; }
 const d = []; for (let i = 1; i < t.length; i++) d.push(t[i] - t[i - 1]);
 res('raf ' + ((t.length - 1) * 1000 / (t[t.length - 1] - t[0])).toFixed(0) + '/s max ' +
     Math.max(...d).toFixed(0) + 'ms >20ms ' + d.filter(x => x > 20).length); };
 requestAnimationFrame(f); })"""


def delta_pct(a, b, secs):
    g = sum(b[p][0] - a[p][0] for p in b if p in a)
    v = sum(b[p][1] - a[p][1] for p in b if p in a)
    return 100.0 * g / (secs * 1e9), 100.0 * v / (secs * 1e9)


def screen_owner():
    try:
        st = open(f"{DRI}/state").read()
        fbs = open(f"{DRI}/framebuffer").read()
    except OSError:
        return "?"
    owners = []
    for block in re.split(r"\n(?=plane\[|crtc\[|connector\[)", st):
        if not block.startswith("plane["):
            continue
        crtc = re.search(r"\n\tcrtc=(\S+)", block)
        fb = re.search(r"\n\tfb=(\d+)", block)
        if crtc and crtc.group(1) != "(null)" and fb and fb.group(1) != "0":
            m = re.search(r"framebuffer\[%s\]:\n\tallocated by = (.+)" % fb.group(1), fbs)
            fmt = re.search(r"\n\t\tformat=(\S+)", block)
            owners.append(f"{m.group(1) if m else '?'}:{fmt.group(1) if fmt else '?'}")
    return "+".join(owners) or "none"


def launch(name, browser, flags, idx):
    prof = f"{PROFILES}/{browser}"
    env = []
    if browser == "firefox":
        # 2026-10-14: a fresh profile per variant - Firefox keeps in the profile how smoothly each codec played
        # and tells YouTube (MediaCapabilities), so one variant must not inherit another's history
        prof = f"{PROFILES}/{name}"
        subprocess.run(["rm", "-rf", prof], check=True)
        # decoder log: which decoder Firefox takes (VA-API or software) and why
        env = ["--setenv=MOZ_LOG=rotate:20,PlatformDecoderModule:5,FFmpegVideo:4",
               f"--setenv=MOZ_LOG_FILE={PROFILES}/{name}-moz"]
    subprocess.run(["runuser", "-u", VIEW, "--", "mkdir", "-p", prof], check=True)
    if browser == "chrome-real":
        subprocess.run(["runuser", "-u", VIEW, "--", "rsync", "-a", "--delete", "--exclude=Cache",
                        "--exclude=Code Cache", "--exclude=GPUCache", "--exclude=*ShaderCache",
                        "--exclude=Dawn*Cache", "--exclude=Singleton*",
                        "/home/view/.config/google-chrome/", prof + "/"], check=True)
    if browser == "firefox":
        subprocess.run(["runuser", "-u", VIEW, "--", "sh", "-c", f"cat > '{prof}/user.js'"],
                       input=FIREFOX_PREFS + "".join(x + "\n" for x in flags), text=True, check=True)
        cmd = ["/usr/bin/firefox", "--new-instance", "--profile", prof,
               "--remote-debugging-port", str(PORT), URL]
    else:
        binary = "/usr/bin/chromium-browser" if browser == "chromium" else "/usr/bin/google-chrome-stable"
        store = [] if browser == "chrome-real" else ["--password-store=basic"]   # real copy: keyring as usual
        cmd = [binary, f"--user-data-dir={prof}", f"--remote-debugging-port={PORT}", "--no-first-run",
               "--no-default-browser-check"] + store + [
               "--autoplay-policy=no-user-gesture-required", "--disable-session-crashed-bubble"] + flags + [URL]
    unit = f"atrium-bench-{idx}-{int(time.time())}"
    subprocess.run(["systemd-run", "--user", "-M", f"{VIEW}@", "--collect", "--quiet", f"--unit={unit}"] + env + cmd,
                   check=True)
    return unit


DEEP_TEXT_JS = r"""(() => { const out = []; const walk = (n) => { if (n.shadowRoot) walk(n.shadowRoot);
 for (const c of n.childNodes) { if (c.nodeType === 3) { const t = c.textContent.trim(); if (t) out.push(t); } else walk(c); } };
 walk(document.body); return out.join('\n'); })()"""


def dump_pages(name):
    # 2026-10-13: save chrome://gpu and chrome://version of this run to compare profiles
    for url, tag in (("chrome://gpu", "gpu"), ("chrome://version", "version")):
        path = f"/tmp/atrium-bench-{tag}-{name}.txt"
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?{url}", method="PUT")
            t = json.load(urllib.request.urlopen(req, timeout=5))
            ws = WS(t["webSocketDebuggerUrl"])
            time.sleep(5)
            r = ws.call("Runtime.evaluate", {"expression": DEEP_TEXT_JS, "returnByValue": True})
            open(path, "w").write(r["result"].get("value") or "")
        except Exception as e:
            open(path, "w").write(f"ERROR {e}\n")


# 2026-10-14: what the browser tells YouTube about 4K60 (the same questions YouTube asks before it picks a
# format): MediaSource.isTypeSupported -> "ms", MediaCapabilities -> s(upported) m (smooth) e (power efficient).
# (about:support cannot be opened over the debugging port - Firefox refuses the navigation.)
CAPS_JS = r"""(async () => { const out = [];
 for (const [n, c] of [['vp9', 'video/webm; codecs="vp09.00.51.08"'], ['av1', 'video/mp4; codecs="av01.0.12M.08"'],
                       ['av1-10', 'video/mp4; codecs="av01.0.13M.10"'], ['h264', 'video/mp4; codecs="avc1.640033"']]) {
  const ms = window.MediaSource ? MediaSource.isTypeSupported(c) : false; let d = {};
  try { d = await navigator.mediaCapabilities.decodingInfo({type: 'media-source', video: {contentType: c,
          width: 3840, height: 2160, bitrate: 20000000, framerate: 60}}); } catch (e) {}
  out.push(n + ':' + (ms ? 'ms' : '--') + '/' + (d.supported ? 's' : '-') + (d.smooth ? 'm' : '-') + (d.powerEfficient ? 'e' : '-')); }
 return out.join(' '); })()"""


def save_firefox_log(name):
    subprocess.run(["sh", "-c", f"mkdir -p /tmp/atrium-bench-mozlog && cp {PROFILES}/{name}-moz* /tmp/atrium-bench-mozlog/ "
                    "2>/dev/null; true"])


def state(page):
    return json.loads(page.eval(STATE_JS))


def run(name, browser, flags, idx, level=None, stats=False):
    if level:
        prev = open(f"{CARD}/power_dpm_force_performance_level").read().strip()
        open(f"{CARD}/power_dpm_force_performance_level", "w").write(level)
        try:
            return run(name, browser, flags, idx, None, stats)
        finally:
            open(f"{CARD}/power_dpm_force_performance_level", "w").write(prev)
    close_browsers()
    launch(name, browser, flags, idx)
    page = ChromePage() if browser != "firefox" else FirefoxPage()
    st, end, ads = None, time.time() + 90, False
    while time.time() < end:
        try:
            st = state(page)
            if st["host"].startswith("consent."):
                page.eval(CONSENT_JS)
            elif st["ad"]:
                ads = True
                page.eval(SKIP_JS)
            elif st["w"] > 0:
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        raise RuntimeError(f"video did not start (last state: {st})")
    try:
        caps = page.eval(CAPS_JS)
    except Exception as e:
        caps = f"? {e}"[:60]
    page.eval(START_JS)
    time.sleep(3)
    for _ in range(3):
        if state(page)["fs"]:
            break
        page.key_f()
        time.sleep(3)
    page.eval(START_JS)
    if stats:
        page.eval("(() => { try { document.getElementById('movie_player').showVideoInfo(); } catch (e) {} return 'ok'; })()")
    time.sleep(WARM)
    s0 = state(page)
    bpids, spids = pids(DIRS[browser]), pids(comm="gnome-shell")
    a_b, a_s = gpu_ns(bpids), gpu_ns(spids)
    c_b, c_s = cpu_ticks(bpids), cpu_ticks(spids)
    t0, busy, owner = time.time(), [], "?"
    while time.time() - t0 < MEAS:
        try:
            busy.append(int(open(f"{CARD}/gpu_busy_percent").read()))
        except OSError:
            pass
        if owner == "?" and time.time() - t0 > MEAS / 2:
            owner = screen_owner()
        time.sleep(0.2)
    secs = time.time() - t0
    s1 = state(page)
    cpu_b = cpu_line(c_b, cpu_ticks(pids(DIRS[browser])), secs)
    cpu_s = cpu_line(c_s, cpu_ticks(pids(comm="gnome-shell")), secs)
    try:
        raf = page.eval(RAF_JS)
    except Exception as e:
        raf = f"raf ? {e}"[:40]
    if browser != "firefox":
        dump_pages(name)
    else:
        save_firefox_log(name)
    b_b, b_s = gpu_ns(pids(DIRS[browser])), gpu_ns(pids(comm="gnome-shell"))
    bg, bv = delta_pct(a_b, b_b, secs)
    sg, _ = delta_pct(a_s, b_s, secs)
    frames, dropped = s1["total"] - s0["total"], s1["dropped"] - s0["dropped"]
    if frames < 0 or dropped < 0:   # the player swapped the video element (ad, reload) - counters reset
        frames, dropped = s1["total"], s1["dropped"]
    avg = sum(busy) / len(busy) if busy else 0
    hi = 100.0 * sum(1 for x in busy if x >= 95) / len(busy) if busy else 0
    acct = (f"acct={'in' if s1.get('logged') else 'out'} "
            f"premium={'y' if 'PREMIUM' in str(s1.get('logo')) else 'n'} ads={'y' if ads else 'n'}")
    return (f"{name:24} {acct} | start {s0['dropped']}/{s0['total']} | {s1['w']}x{s1['h']} {s1['codecs'][:14]:14} hdr={'y' if s1['hdr'] else 'n'} "
            f"fs={'y' if s1['fs'] else 'n'} | dropped {dropped}/{frames} "
            f"({100.0 * dropped / frames if frames > 0 else 0:.1f}%) | gpu busy avg {avg:.0f}% "
            f">=95% {hi:.0f}% | browser gfx {bg:.0f}% vcn {bv:.0f}% | shell gfx {sg:.0f}% | screen {owner} "
            f"| caps {caps} | cpu {cpu_b} | shell cpu {cpu_s} | {raf}")


def main():
    if os.geteuid() != 0:
        sys.exit("run as root")
    want = sys.argv[1:]
    todo = [v for v in VARIANTS if not want or v[0] in want or any(v[0].startswith(w + "-") for w in want)]
    level = open(f"{CARD}/power_dpm_force_performance_level").read().strip()
    with open(OUT, "a") as f:
        f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S %Z')} gpu level={level} video={URL}\n")
    for idx, (name, browser, flags, *level) in enumerate(todo):
        print(f"[{idx + 1}/{len(todo)}] {name} ...", flush=True)
        try:
            line = run(name, browser, flags, idx, *level)
        except Exception as e:
            line = f"{name:24} ERROR {e}"
        print(line, flush=True)
        with open(OUT, "a") as f:
            f.write(line + "\n")
    close_browsers()
    subprocess.run(["rm", "-rf", PROFILES])   # test profiles (the real-profile copy holds cookies) - not kept
    print(f"done. Results in {OUT}. The browsers are closed - open yours again from the dock.")


if __name__ == "__main__":
    main()
