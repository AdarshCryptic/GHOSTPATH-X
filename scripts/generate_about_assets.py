"""Generate GHOSTPATH X About-page visuals (local only, no network).

Run:  python3 scripts/generate_about_assets.py
Output: apps/api/static/assets/about/

Assets:
  about-hero.svg            hero banner: ghost following a glowing path
  about-noise-vs-path.svg   before/after: warning pile vs one verified path
  about-path-chain.svg      attack-path chain: 4 labelled boxes + arrows
  about-isolated-lab.svg    shield around an app, barred external arrow
  about-path-walk.gif       animated dot walking the 4-node path

Only stdlib + Pillow are used (pillow in requirements.txt).
Re-running the script regenerates every file deterministically.
SVG dots that look random come from random.Random(42), fixed seed.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ABOUT = ROOT / "apps" / "api" / "static" / "assets" / "about"

CYAN = "#22D3EE"
GREEN = "#00E5A0"
DANGER = "#FF3B5C"
AMBER = "#FFB020"
BG = "#05080F"
PANEL = "#0B1220"
MUTED = "#94A3B8"

# ---------------------------------------------------------------- SVG ---

HERO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 320" role="img" aria-label="A friendly ghost following a glowing network path through a dark graph">
  <defs>
    <radialGradient id="heroGlow" cx="62%" cy="45%" r="70%">
      <stop offset="0%" stop-color="#22D3EE" stop-opacity="0.35"/>
      <stop offset="55%" stop-color="#00E5A0" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="#22D3EE" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="heroGhost" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#E6FFFA"/>
      <stop offset="100%" stop-color="#22D3EE"/>
    </linearGradient>
    <filter id="soft" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="6"/>
    </filter>
  </defs>
  <rect width="960" height="320" fill="#05080F"/>
  <circle cx="600" cy="145" r="220" fill="url(#heroGlow)"/>
  <!-- faint background graph -->
  <g stroke="#22D3EE" stroke-width="1.5" opacity="0.22">
    <line x1="70" y1="70" x2="230" y2="150"/><line x1="230" y1="150" x2="180" y2="270"/>
    <line x1="230" y1="150" x2="420" y2="90"/><line x1="420" y1="90" x2="620" y2="60"/>
    <line x1="620" y1="60" x2="780" y2="120"/><line x1="780" y1="120" x2="900" y2="80"/>
    <line x1="420" y1="90" x2="560" y2="250"/><line x1="560" y1="250" x2="780" y2="120"/>
    <line x1="180" y1="270" x2="420" y2="260"/><line x1="420" y1="260" x2="560" y2="250"/>
  </g>
  <g fill="#0F172A" stroke="#22D3EE" stroke-width="1.5" opacity="0.6">
    <circle cx="70" cy="70" r="10"/><circle cx="180" cy="270" r="10"/>
    <circle cx="420" cy="90" r="10"/><circle cx="620" cy="60" r="10"/>
    <circle cx="900" cy="80" r="10"/><circle cx="560" cy="250" r="10"/>
    <circle cx="420" cy="260" r="10"/>
  </g>
  <!-- the glowing path the ghost follows -->
  <g stroke="#00E5A0" stroke-width="4" stroke-linecap="round" filter="url(#soft)" opacity="0.8">
    <polyline points="120,230 300,170 480,200 650,130 820,180" fill="none"/>
  </g>
  <g stroke="#00E5A0" stroke-width="3" stroke-linecap="round">
    <polyline points="120,230 300,170 480,200 650,130 820,180" fill="none"/>
  </g>
  <g fill="#00E5A0">
    <circle cx="120" cy="230" r="9"/><circle cx="300" cy="170" r="8"/>
    <circle cx="480" cy="200" r="8"/><circle cx="650" cy="130" r="8"/>
  </g>
  <g fill="#00E5A0" stroke="#05080F" stroke-width="2">
    <circle cx="820" cy="180" r="11"/>
  </g>
  <circle cx="820" cy="180" r="4" fill="#FF3B5C"/>
  <!-- friendly ghost riding the path -->
  <g transform="translate(430,58)">
    <path fill="url(#heroGhost)" d="M50 6c-27 0-44 21-44 49v58c0 5 6 7 9 3l8-9c2-2 6-2 8 0l6 6c2 2 6 2 8 0l6-6c2-2 6-2 8 0l6 6c2 2 6 2 8 0l8-9c3-4 9-2 9 3v-52c0-28-17-49-40-49z"/>
    <g fill="#05080F">
      <ellipse cx="34" cy="48" rx="7" ry="9"/><ellipse cx="66" cy="48" rx="7" ry="9"/>
    </g>
    <g fill="#22D3EE"><circle cx="36" cy="46" r="2.5"/><circle cx="68" cy="46" r="2.5"/></g>
    <path d="M42 68q8 6 16 0" stroke="#05080F" stroke-width="3" fill="none" stroke-linecap="round"/>
  </g>
  <text x="48" y="52" font-family="monospace" font-size="26" font-weight="bold" fill="#E6FFFA">Follow the ghost.</text>
  <text x="48" y="86" font-family="monospace" font-size="26" font-weight="bold" fill="#00E5A0">Prove the path.</text>
  <text x="48" y="292" font-family="monospace" font-size="14" fill="#94A3B8">GHOSTPATH X finds the one attack path that actually works — and proves it.</text>
</svg>
"""


def noise_vs_path_svg() -> str:
    """Left: messy pile of grey/red warning dots. Right: one clean green path."""
    rng = random.Random(42)
    dots = []
    # messy pile clustered on the left half (x 40..420, y 60..250)
    for _ in range(90):
        cx = rng.uniform(45, 415)
        cy = rng.uniform(60, 250)
        r = rng.uniform(2.5, 7)
        # mostly grey, ~1 in 4 red warnings
        col = DANGER if rng.random() < 0.28 else "#64748B"
        dots.append(
            f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.1f}" fill="{col}" opacity="0.85"/>'
        )
    # a few warning triangles mixed into the pile
    tris = []
    for _ in range(8):
        cx = rng.uniform(70, 390)
        cy = rng.uniform(80, 230)
        tris.append(
            f'<path d="M{cx:.0f} {cy - 9:.0f} l9 16 h-18 z" fill="{DANGER}" opacity="0.9"/>'
        )
    dots_svg = "\n    ".join(dots + tris)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 320" role="img" aria-label="Before: hundreds of warnings. After: one verified path.">
  <rect width="960" height="320" fill="#05080F"/>
  <!-- left: before -->
  <rect x="16" y="16" width="448" height="288" rx="16" fill="#0B1220"/>
  <text x="240" y="52" text-anchor="middle" font-family="monospace" font-size="17" font-weight="bold" fill="#FF3B5C">Before: hundreds of warnings</text>
  <g>
    {dots_svg}
  </g>
  <text x="240" y="292" text-anchor="middle" font-family="monospace" font-size="13" fill="#94A3B8">scanner output — every warning looks the same</text>
  <!-- divider -->
  <line x1="480" y1="24" x2="480" y2="296" stroke="#22D3EE" stroke-width="1.5" stroke-dasharray="6 6" opacity="0.5"/>
  <path d="M480 150 l14 10 -14 10 z" fill="#22D3EE"/>
  <!-- right: after -->
  <rect x="496" y="16" width="448" height="288" rx="16" fill="#0B1220"/>
  <text x="720" y="52" text-anchor="middle" font-family="monospace" font-size="17" font-weight="bold" fill="#00E5A0">After: one verified path</text>
  <g stroke="#00E5A0" stroke-width="4" stroke-linecap="round">
    <line x1="560" y1="190" x2="660" y2="130"/>
    <line x1="660" y1="130" x2="770" y2="185"/>
    <line x1="770" y1="185" x2="880" y2="125"/>
  </g>
  <g fill="#00E5A0" stroke="#05080F" stroke-width="2">
    <circle cx="560" cy="190" r="12"/><circle cx="660" cy="130" r="12"/>
    <circle cx="770" cy="185" r="12"/><circle cx="880" cy="125" r="14"/>
  </g>
  <circle cx="880" cy="125" r="5" fill="#FF3B5C"/>
  <g font-family="monospace" font-size="13" fill="#94A3B8" text-anchor="middle">
    <text x="560" y="225">start</text>
    <text x="660" y="165">step 2</text>
    <text x="770" y="220">step 3</text>
    <text x="880" y="160">proven</text>
  </g>
  <text x="720" y="292" text-anchor="middle" font-family="monospace" font-size="13" fill="#94A3B8">one path, replayed end to end, with evidence</text>
</svg>
"""


PATH_CHAIN_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 240" role="img" aria-label="Attack path chain: Customer B, Order API, Order Resource, Authorization Boundary">
  <defs>
    <marker id="chainArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M0 0L10 5L0 10z" fill="#00E5A0"/>
    </marker>
  </defs>
  <rect width="960" height="240" fill="#05080F"/>
  <!-- green path line behind the boxes -->
  <line x1="60" y1="120" x2="900" y2="120" stroke="#00E5A0" stroke-width="4" stroke-linecap="round" opacity="0.55"/>
  <g font-family="monospace" text-anchor="middle">
    <g>
      <rect x="40" y="72" width="180" height="96" rx="12" fill="#0B1220" stroke="#22D3EE" stroke-width="2"/>
      <text x="130" y="112" font-size="17" font-weight="bold" fill="#E6FFFA">Customer B</text>
      <text x="130" y="140" font-size="13" fill="#94A3B8">attacker identity</text>
    </g>
    <g>
      <rect x="280" y="72" width="180" height="96" rx="12" fill="#0B1220" stroke="#22D3EE" stroke-width="2"/>
      <text x="370" y="112" font-size="17" font-weight="bold" fill="#E6FFFA">Order API</text>
      <text x="370" y="140" font-size="13" fill="#94A3B8">GET /orders/{id}</text>
    </g>
    <g>
      <rect x="520" y="72" width="180" height="96" rx="12" fill="#0B1220" stroke="#22D3EE" stroke-width="2"/>
      <text x="610" y="112" font-size="17" font-weight="bold" fill="#E6FFFA">Order Resource</text>
      <text x="610" y="140" font-size="13" fill="#94A3B8">someone else's order</text>
    </g>
    <g>
      <rect x="760" y="72" width="180" height="96" rx="12" fill="#0B1220" stroke="#FFB020" stroke-width="3"/>
      <text x="850" y="106" font-size="16" font-weight="bold" fill="#FFB020">Authorization</text>
      <text x="850" y="128" font-size="16" font-weight="bold" fill="#FFB020">Boundary</text>
      <text x="850" y="152" font-size="13" fill="#94A3B8">the check that failed</text>
    </g>
  </g>
  <g stroke="#00E5A0" stroke-width="3" marker-end="url(#chainArrow)">
    <line x1="224" y1="120" x2="272" y2="120"/>
    <line x1="464" y1="120" x2="512" y2="120"/>
    <line x1="704" y1="120" x2="752" y2="120"/>
  </g>
  <text x="480" y="216" text-anchor="middle" font-family="monospace" font-size="14" fill="#94A3B8">Each step is replayed — the finding is real only if the whole chain holds.</text>
</svg>
"""

ISOLATED_LAB_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 320" role="img" aria-label="Isolated lab: a shield around the test app, no external network">
  <defs>
    <linearGradient id="labShield" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#22D3EE" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#22D3EE" stop-opacity="0.04"/>
    </linearGradient>
  </defs>
  <rect width="480" height="320" fill="#05080F"/>
  <text x="240" y="34" text-anchor="middle" font-family="monospace" font-size="17" font-weight="bold" fill="#E6FFFA">Isolated lab — nothing leaves</text>
  <!-- barred external-network arrow, outside the shield -->
  <g stroke="#FF3B5C" stroke-width="3" stroke-linecap="round">
    <line x1="392" y1="92" x2="452" y2="92"/>
    <path d="M452 92 l-12 -7 M452 92 l-12 7" fill="none"/>
  </g>
  <g stroke="#FF3B5C" stroke-width="4" stroke-linecap="round">
    <line x1="402" y1="66" x2="442" y2="118"/>
  </g>
  <circle cx="422" cy="92" r="30" fill="none" stroke="#FF3B5C" stroke-width="3"/>
  <text x="422" y="152" text-anchor="middle" font-family="monospace" font-size="12" fill="#FF3B5C">no external</text>
  <text x="422" y="169" text-anchor="middle" font-family="monospace" font-size="12" fill="#FF3B5C">network</text>
  <!-- shield around the app -->
  <path d="M240 52 L352 84 V168 C352 236 300 272 240 292 C180 272 128 236 128 168 V84 Z"
        fill="url(#labShield)" stroke="#22D3EE" stroke-width="3" stroke-linejoin="round"/>
  <!-- app window inside the shield -->
  <g>
    <rect x="168" y="118" width="144" height="104" rx="10" fill="#0B1220" stroke="#00E5A0" stroke-width="2"/>
    <line x1="168" y1="142" x2="312" y2="142" stroke="#00E5A0" stroke-width="1.5"/>
    <circle cx="182" cy="130" r="4" fill="#FF3B5C"/>
    <circle cx="196" cy="130" r="4" fill="#FFB020"/>
    <circle cx="210" cy="130" r="4" fill="#00E5A0"/>
    <rect x="182" y="156" width="116" height="10" rx="5" fill="#22D3EE" opacity="0.5"/>
    <rect x="182" y="174" width="80" height="10" rx="5" fill="#22D3EE" opacity="0.3"/>
    <rect x="182" y="196" width="60" height="12" rx="6" fill="#00E5A0" opacity="0.8"/>
  </g>
  <path d="M212 252 l12 12 24 -26" fill="none" stroke="#00E5A0" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="240" y="312" text-anchor="middle" font-family="monospace" font-size="12" fill="#94A3B8">tests run only against the lab target</text>
</svg>
"""


# ---------------------------------------------------------------- GIF ---

def _hex(rgb_hex: str) -> tuple[int, int, int]:
    h = rgb_hex.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def make_path_walk_gif(path: Path, width: int = 480, height: int = 240) -> int:
    """Dot walks 4 nodes left to right; each node turns green as reached,
    the connecting line lights up; at the end all nodes glow, then restart."""
    nodes = [(60, 120), (180, 108), (300, 132), (420, 116)]
    # Build a polyline timeline: travel node->node (10 frames each),
    # 1-frame arrival pause is folded into the next leg's start.
    legs = 3
    travel_frames = 12  # per leg
    hold_frames = 10    # all-green glow at the end
    total = legs * travel_frames + hold_frames
    imgs = []
    for f in range(total):
        img = Image.new("RGB", (width, height), _hex(BG))
        draw = ImageDraw.Draw(img, "RGBA")
        if f < legs * travel_frames:
            leg = f // travel_frames
            t = (f % travel_frames) / travel_frames
            reached = leg + 1  # nodes 0..leg are lit (node leg+1 reached at t=1)
            x0, y0 = nodes[leg]
            x1, y1 = nodes[leg + 1]
            dot = (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            lit_until = leg + (1 if t >= 0.999 else 0)
        else:
            reached = len(nodes)
            lit_until = len(nodes)
            dot = nodes[-1]
        # faint full path
        draw.line(nodes, fill=_hex(CYAN) + (70,), width=2, joint="curve")
        # lit segments: between consecutive reached nodes
        for i in range(min(lit_until, len(nodes) - 1)):
            draw.line([nodes[i], nodes[i + 1]], fill=_hex(GREEN) + (255,),
                      width=3, joint="curve")
        # nodes: unreached = dark with cyan ring; reached = green (+ glow)
        # during the final hold the glow pulses so frames stay distinct
        glow_all = f >= legs * travel_frames
        hold_i = f - legs * travel_frames if glow_all else 0
        pulse = 1.0 + 0.18 * math.sin(hold_i / max(hold_frames - 1, 1) * math.pi)
        for i, (nx, ny) in enumerate(nodes):
            is_lit = i < lit_until or (glow_all and i < len(nodes))
            if is_lit:
                r = int(round((13 if glow_all else 11) * pulse))
                draw.ellipse([nx - r - 6, ny - r - 6, nx + r + 6, ny + r + 6],
                             fill=_hex(GREEN) + (50,))
                draw.ellipse([nx - r, ny - r, nx + r, ny + r],
                             fill=_hex(GREEN) + (255,))
                draw.ellipse([nx - 4, ny - 4, nx + 4, ny + 4],
                             fill=(255, 255, 255, 255))
            else:
                draw.ellipse([nx - 10, ny - 10, nx + 10, ny + 10],
                             fill=_hex(PANEL) + (255,),
                             outline=_hex(CYAN) + (200,), width=2)
        # travelling dot (hidden during the final all-green hold)
        if not glow_all:
            dx, dy = dot
            draw.ellipse([dx - 10, dy - 10, dx + 10, dy + 10],
                         fill=_hex(CYAN) + (70,))
            draw.ellipse([dx - 6, dy - 6, dx + 6, dy + 6],
                         fill=_hex(CYAN) + (255,))
            draw.ellipse([dx - 2, dy - 2, dx + 2, dy + 2],
                         fill=(255, 255, 255, 255))
        draw.text((12, height - 22), "PATH WALK  ·  GHOSTPATH X",
                  fill=_hex(CYAN))
        imgs.append(img.convert("P", palette=Image.ADAPTIVE, colors=64))
    imgs[0].save(path, format="GIF", save_all=True, append_images=imgs[1:],
                 duration=80, loop=0, optimize=True)
    return total


# ---------------------------------------------------------------- main ---

def main() -> None:
    ABOUT.mkdir(parents=True, exist_ok=True)
    (ABOUT / "about-hero.svg").write_text(HERO_SVG, encoding="utf-8")
    (ABOUT / "about-noise-vs-path.svg").write_text(noise_vs_path_svg(),
                                                   encoding="utf-8")
    (ABOUT / "about-path-chain.svg").write_text(PATH_CHAIN_SVG,
                                                encoding="utf-8")
    (ABOUT / "about-isolated-lab.svg").write_text(ISOLATED_LAB_SVG,
                                                  encoding="utf-8")
    frames = make_path_walk_gif(ABOUT / "about-path-walk.gif")
    print(f"GIF frames: {frames}")
    for p in sorted(ABOUT.iterdir()):
        print(f"{p.name:28s} {p.stat().st_size:>8,} bytes")


if __name__ == "__main__":
    main()
