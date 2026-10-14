"""atrium wallpaper 3840x2160, the first variant (not in use): dark, glowing robot and ATRIUM.

Needs the Russo One font (SIL OFL 1.1, Google Fonts) as russo-one-latin.woff2 next to this script.
python make_robot_wallpaper.py  ->  atrium-wallpaper.svg + atrium-wallpaper.html; render the html to PNG
with headless Chrome, for example:
  chrome --headless --user-data-dir=<temp dir> --window-size=3840,2160 --screenshot=atrium-wallpaper.png atrium-wallpaper.html
Preview: atrium-robot-preview.jpg.
"""
import base64
import pathlib
import random

HERE = pathlib.Path(__file__).parent
FONT = HERE / "russo-one-latin.woff2"
W, H = 3840, 2160
CX = W // 2
RC = 880  # vertical centre of the glow behind the robot


def stars(n, seed=7):
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H * 0.92)
        r = rnd.choice([1.2, 1.5, 1.8, 2.2, 2.8])
        o = rnd.uniform(0.12, 0.55)
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#dbeafe" opacity="{o:.2f}"/>')
    return "\n    ".join(out)


font_b64 = base64.b64encode(FONT.read_bytes()).decode()

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <style>
      @font-face {{ font-family: "Russo One"; src: url(data:font/woff2;base64,{font_b64}) format("woff2"); }}
    </style>
    <radialGradient id="bg" cx="{CX}" cy="{RC}" r="2300" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#0e1c2c"/>
      <stop offset="0.45" stop-color="#080d16"/>
      <stop offset="1" stop-color="#030407"/>
    </radialGradient>
    <radialGradient id="vignette" cx="{CX}" cy="{H // 2}" r="2400" gradientUnits="userSpaceOnUse">
      <stop offset="0.55" stop-color="#000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000" stop-opacity="0.65"/>
    </radialGradient>
    <linearGradient id="shell" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#5a6272"/>
      <stop offset="0.5" stop-color="#363b47"/>
      <stop offset="1" stop-color="#1f232b"/>
    </linearGradient>
    <linearGradient id="shellSide" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#7dd3fc" stop-opacity="0.22"/>
      <stop offset="0.18" stop-color="#7dd3fc" stop-opacity="0"/>
      <stop offset="0.82" stop-color="#a78bfa" stop-opacity="0"/>
      <stop offset="1" stop-color="#a78bfa" stop-opacity="0.20"/>
    </linearGradient>
    <linearGradient id="visor" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#121722"/>
      <stop offset="1" stop-color="#06080c"/>
    </linearGradient>
    <linearGradient id="eye" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e0f7ff"/>
      <stop offset="0.45" stop-color="#7dd3fc"/>
      <stop offset="1" stop-color="#38bdf8"/>
    </linearGradient>
    <linearGradient id="title" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#bae6fd"/>
      <stop offset="0.5" stop-color="#f0f9ff"/>
      <stop offset="1" stop-color="#c4b5fd"/>
    </linearGradient>
    <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#7dd3fc" stop-opacity="0"/>
      <stop offset="0.5" stop-color="#7dd3fc" stop-opacity="0.7"/>
      <stop offset="1" stop-color="#a78bfa" stop-opacity="0"/>
    </linearGradient>
    <filter id="blurXL" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="170"/></filter>
    <filter id="blurL" filterUnits="userSpaceOnUse" x="-800" y="1000" width="1600" height="700"><feGaussianBlur stdDeviation="55"/></filter>
    <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="18"/></filter>
    <filter id="glowS" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="8"/></filter>
  </defs>

  <!-- sky -->
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <g>
    {stars(260)}
  </g>
  <circle cx="{CX}" cy="{RC}" r="560" fill="#38bdf8" opacity="0.17" filter="url(#blurXL)"/>
  <circle cx="{CX + 460}" cy="{RC + 380}" r="520" fill="#8b5cf6" opacity="0.11" filter="url(#blurXL)"/>
  <circle cx="{CX - 520}" cy="{RC + 300}" r="460" fill="#0ea5e9" opacity="0.08" filter="url(#blurXL)"/>

  <!-- the atrium: rings around the robot -->
  <g fill="none" stroke="#7dd3fc">
    <ellipse cx="{CX}" cy="{RC}" rx="640" ry="640" stroke-opacity="0.07" stroke-width="2"/>
    <ellipse cx="{CX}" cy="{RC}" rx="800" ry="800" stroke-opacity="0.05" stroke-width="2"/>
    <ellipse cx="{CX}" cy="{RC}" rx="960" ry="960" stroke-opacity="0.03" stroke-width="2"/>
  </g>
  <circle cx="{CX + 452}" cy="{RC - 452}" r="7" fill="#7dd3fc" opacity="0.7"/>
  <circle cx="{CX - 760}" cy="{RC + 250}" r="6" fill="#a78bfa" opacity="0.6"/>
  <circle cx="{CX + 300}" cy="{RC + 912}" r="5" fill="#7dd3fc" opacity="0.4"/>

  <!-- robot -->
  <g transform="translate({CX} 0)">
    <ellipse cx="0" cy="1350" rx="240" ry="46" fill="#38bdf8" opacity="0.38" filter="url(#blurL)"/>

    <!-- antenna -->
    <line x1="0" y1="505" x2="0" y2="410" stroke="#8a93a5" stroke-width="12" stroke-linecap="round"/>
    <circle cx="0" cy="388" r="30" fill="#7dd3fc" filter="url(#glow)" opacity="0.9"/>
    <circle cx="0" cy="388" r="22" fill="url(#eye)"/>

    <!-- ears -->
    <rect x="-338" y="640" width="64" height="176" rx="30" fill="url(#shell)" stroke="#6b7383" stroke-width="4"/>
    <rect x="274" y="640" width="64" height="176" rx="30" fill="url(#shell)" stroke="#6b7383" stroke-width="4"/>
    <rect x="-318" y="680" width="14" height="96" rx="7" fill="#7dd3fc" opacity="0.55"/>
    <rect x="304" y="680" width="14" height="96" rx="7" fill="#a78bfa" opacity="0.55"/>

    <!-- head -->
    <rect x="-280" y="500" width="560" height="450" rx="150" fill="url(#shell)" stroke="#6b7383" stroke-width="5"/>
    <rect x="-280" y="500" width="560" height="450" rx="150" fill="url(#shellSide)"/>
    <path d="M -170 540 Q 0 512 170 540" stroke="#ffffff" stroke-opacity="0.18" stroke-width="10"
          fill="none" stroke-linecap="round"/>

    <!-- visor and eyes -->
    <rect x="-212" y="588" width="424" height="222" rx="104" fill="url(#visor)" stroke="#1c2230" stroke-width="4"/>
    <rect x="-124" y="646" width="72" height="100" rx="36" fill="#7dd3fc" filter="url(#glow)" opacity="0.85"/>
    <rect x="52" y="646" width="72" height="100" rx="36" fill="#7dd3fc" filter="url(#glow)" opacity="0.85"/>
    <rect x="-120" y="650" width="64" height="92" rx="32" fill="url(#eye)"/>
    <rect x="56" y="650" width="64" height="92" rx="32" fill="url(#eye)"/>
    <ellipse cx="-100" cy="672" rx="10" ry="14" fill="#ffffff" opacity="0.8"/>
    <ellipse cx="76" cy="672" rx="10" ry="14" fill="#ffffff" opacity="0.8"/>
    <path d="M -180 640 Q -150 600 -60 604" stroke="#ffffff" stroke-opacity="0.10" stroke-width="12"
          fill="none" stroke-linecap="round"/>
    <rect x="-56" y="858" width="112" height="14" rx="7" fill="#0b0e14"/>
    <rect x="-40" y="862" width="80" height="6" rx="3" fill="#7dd3fc" opacity="0.35"/>

    <!-- neck -->
    <rect x="-56" y="946" width="112" height="64" rx="18" fill="#2a2f39" stroke="#4b5260" stroke-width="3"/>
    <line x1="-46" y1="966" x2="46" y2="966" stroke="#5b6372" stroke-width="3"/>
    <line x1="-46" y1="988" x2="46" y2="988" stroke="#5b6372" stroke-width="3"/>

    <!-- arms -->
    <g transform="rotate(12 -196 1050)">
      <rect x="-226" y="1040" width="58" height="176" rx="29" fill="url(#shell)" stroke="#6b7383" stroke-width="4"/>
      <circle cx="-197" cy="1228" r="34" fill="#2b3039" stroke="#6b7383" stroke-width="4"/>
    </g>
    <g transform="rotate(-12 196 1050)">
      <rect x="168" y="1040" width="58" height="176" rx="29" fill="url(#shell)" stroke="#6b7383" stroke-width="4"/>
      <circle cx="197" cy="1228" r="34" fill="#2b3039" stroke="#6b7383" stroke-width="4"/>
    </g>

    <!-- body -->
    <rect x="-200" y="1004" width="400" height="236" rx="92" fill="url(#shell)" stroke="#6b7383" stroke-width="5"/>
    <rect x="-200" y="1004" width="400" height="236" rx="92" fill="url(#shellSide)"/>
    <rect x="-124" y="1058" width="248" height="44" rx="22" fill="#0b0e14" stroke="#1c2230" stroke-width="3"/>
    <rect x="-100" y="1072" width="130" height="16" rx="8" fill="#7dd3fc" opacity="0.55"/>
    <circle cx="-62" cy="1168" r="22" fill="#86efac" filter="url(#glowS)" opacity="0.7"/>
    <circle cx="0" cy="1168" r="22" fill="#fbbf24" filter="url(#glowS)" opacity="0.7"/>
    <circle cx="62" cy="1168" r="22" fill="#f87171" filter="url(#glowS)" opacity="0.7"/>
    <circle cx="-62" cy="1168" r="15" fill="#86efac"/>
    <circle cx="0" cy="1168" r="15" fill="#fbbf24"/>
    <circle cx="62" cy="1168" r="15" fill="#f87171"/>
  </g>

  <!-- title -->
  <text x="{CX + 36}" y="1660" text-anchor="middle" font-family="Russo One" font-size="214"
        letter-spacing="72" fill="#7dd3fc" opacity="0.35" filter="url(#glow)">ATRIUM</text>
  <text x="{CX + 36}" y="1660" text-anchor="middle" font-family="Russo One" font-size="214"
        letter-spacing="72" fill="url(#title)">ATRIUM</text>
  <rect x="{CX - 420}" y="1730" width="840" height="4" rx="2" fill="url(#rule)"/>

  <rect width="{W}" height="{H}" fill="url(#vignette)"/>
</svg>
"""

(HERE / "atrium-wallpaper.svg").write_text(svg, encoding="ascii")
(HERE / "atrium-wallpaper.html").write_text(
    "<!doctype html><meta charset='utf-8'><style>html,body{margin:0;background:#000}"
    f"svg{{display:block}}</style>{svg}",
    encoding="ascii",
)
print("ok", len(svg))
