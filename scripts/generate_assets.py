"""Generate GHOSTPATH X brand assets (local only, no network).

Run:  python3 scripts/generate_assets.py
Output: apps/api/static/assets/

Assets:
  logo.svg / logo.png   ghost + network-path emblem (cyan/green glow on dark)
  graph-empty.svg       Attack Graph empty / loading illustration
  radar.gif             animated radar sweep, shown while a scan is running
  agent-*.svg           one small geometric mark per agent, one accent each

Only stdlib + Pillow are used (pillow==11.0.0 in requirements.txt).
Re-running the script regenerates every file deterministically.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "apps" / "api" / "static" / "assets"

CYAN = "#22D3EE"
GREEN = "#00E5A0"
DANGER = "#FF3B5C"
AMBER = "#FFB020"
BG = "#05080F"
PANEL = "#0B1220"

# ---------------------------------------------------------------- SVG ---

LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="GHOSTPATH X logo">
  <defs>
    <radialGradient id="glow" cx="50%" cy="42%" r="65%">
      <stop offset="0%" stop-color="#22D3EE" stop-opacity="0.45"/>
      <stop offset="60%" stop-color="#22D3EE" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="#22D3EE" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="ghost" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#E6FFFA"/>
      <stop offset="100%" stop-color="#22D3EE"/>
    </linearGradient>
  </defs>
  <rect width="256" height="256" rx="48" fill="#05080F"/>
  <circle cx="128" cy="108" r="98" fill="url(#glow)"/>
  <!-- network path: nodes + edges the ghost follows -->
  <g stroke="#00E5A0" stroke-width="3" stroke-linecap="round" opacity="0.9">
    <line x1="36" y1="196" x2="86" y2="158"/>
    <line x1="86" y1="158" x2="128" y2="186"/>
    <line x1="128" y1="186" x2="176" y2="150"/>
    <line x1="176" y1="150" x2="220" y2="188"/>
  </g>
  <g fill="#00E5A0">
    <circle cx="36" cy="196" r="7"/>
    <circle cx="86" cy="158" r="6"/>
    <circle cx="128" cy="186" r="6"/>
    <circle cx="176" cy="150" r="6"/>
    <circle cx="220" cy="188" r="7"/>
  </g>
  <g fill="#FF3B5C"><circle cx="220" cy="188" r="3.5"/></g>
  <!-- ghost silhouette -->
  <path fill="url(#ghost)" d="M128 34c-34 0-56 26-56 62v74c0 6 8 9 12 4l10-11c3-3 8-3 11 0l7 8c3 3 8 3 11 0l7-8c3-3 8-3 11 0l7 8c3 3 8 3 11 0l10-11c4-5 12-2 12 4v-68c0-36-22-62-53-62z"/>
  <g fill="#05080F">
    <ellipse cx="108" cy="92" rx="9" ry="12"/>
    <ellipse cx="148" cy="92" rx="9" ry="12"/>
  </g>
  <g fill="#22D3EE">
    <circle cx="110" cy="90" r="3.5"/>
    <circle cx="150" cy="90" r="3.5"/>
  </g>
  <path d="M118 118q10 8 20 0" stroke="#05080F" stroke-width="4" fill="none" stroke-linecap="round"/>
</svg>
"""

GRAPH_EMPTY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" role="img" aria-label="Attack graph empty state">
  <rect width="640" height="360" fill="#0B1220"/>
  <g stroke="#22D3EE" stroke-width="1.5" opacity="0.35">
    <line x1="110" y1="90" x2="270" y2="150"/>
    <line x1="270" y1="150" x2="430" y2="100"/>
    <line x1="270" y1="150" x2="380" y2="260"/>
    <line x1="430" y1="100" x2="540" y2="200"/>
    <line x1="110" y1="90" x2="200" y2="260"/>
    <line x1="200" y1="260" x2="380" y2="260"/>
  </g>
  <g fill="#0F172A" stroke="#22D3EE" stroke-width="2">
    <circle cx="110" cy="90" r="22"/><circle cx="270" cy="150" r="26"/>
    <circle cx="430" cy="100" r="22"/><circle cx="380" cy="260" r="22"/>
    <circle cx="540" cy="200" r="20"/><circle cx="200" cy="260" r="20"/>
  </g>
  <g fill="#22D3EE" opacity="0.9">
    <circle cx="110" cy="90" r="5"/><circle cx="270" cy="150" r="6"/>
    <circle cx="430" cy="100" r="5"/><circle cx="380" cy="260" r="5"/>
    <circle cx="540" cy="200" r="5"/><circle cx="200" cy="260" r="5"/>
  </g>
  <g fill="#00E5A0" opacity="0.9">
    <circle cx="270" cy="150" r="3" fill="#00E5A0"/>
  </g>
  <text x="320" y="330" text-anchor="middle" font-family="monospace" font-size="15" fill="#94A3B8">No graph data yet — run a scan to light up the paths</text>
</svg>
"""

# One accent colour + one simple geometric mark per agent.
AGENT_ICONS = {
    "agent-discovery.svg": ("#22D3EE", "magnifier",
        '<circle cx="32" cy="32" r="16" fill="none" stroke="{c}" stroke-width="5"/>'
        '<line x1="44" y1="44" x2="56" y2="56" stroke="{c}" stroke-width="5" stroke-linecap="round"/>'),
    "agent-identity.svg": ("#A855F7", "person",
        '<circle cx="32" cy="24" r="11" fill="none" stroke="{c}" stroke-width="5"/>'
        '<path d="M12 54c2-11 10-16 20-16s18 5 20 16" fill="none" stroke="{c}" stroke-width="5" stroke-linecap="round"/>'),
    "agent-workflow.svg": ("#FFB020", "flow",
        '<rect x="14" y="12" width="36" height="14" rx="4" fill="none" stroke="{c}" stroke-width="4"/>'
        '<rect x="14" y="38" width="36" height="14" rx="4" fill="none" stroke="{c}" stroke-width="4"/>'
        '<line x1="32" y1="26" x2="32" y2="38" stroke="{c}" stroke-width="4"/>'),
    "agent-graph.svg": ("#00E5A0", "nodes",
        '<circle cx="18" cy="18" r="7" fill="{c}"/><circle cx="48" cy="22" r="7" fill="{c}"/>'
        '<circle cx="30" cy="48" r="7" fill="{c}"/>'
        '<line x1="24" y1="22" x2="42" y2="22" stroke="{c}" stroke-width="3"/>'
        '<line x1="20" y1="25" x2="27" y2="42" stroke="{c}" stroke-width="3"/>'
        '<line x1="45" y1="28" x2="34" y2="43" stroke="{c}" stroke-width="3"/>'),
    "agent-reasoning.svg": ("#22D3EE", "brain / spark",
        '<path d="M32 8l6 14 15 2-11 10 3 15-13-8-13 8 3-15-11-10 15-2z" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>'),
    "agent-validation.svg": ("#00E5A0", "shield check",
        '<path d="M32 8l20 8v16c0 14-9 22-20 26-11-4-20-12-20-26V16z" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>'
        '<path d="M24 32l6 6 12-13" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'),
    "agent-evidence.svg": ("#FF3B5C", "document",
        '<path d="M18 8h20l10 10v38H18z" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>'
        '<line x1="25" y1="28" x2="41" y2="28" stroke="{c}" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="25" y1="38" x2="41" y2="38" stroke="{c}" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="25" y1="48" x2="35" y2="48" stroke="{c}" stroke-width="4" stroke-linecap="round"/>'),
}


def agent_svg(color: str, inner: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img">'
        '<rect width="64" height="64" rx="14" fill="#0B1220"/>'
        + inner.format(c=color)
        + "</svg>\n"
    )


# ---------------------------------------------------------------- PIL ---

def _hex(rgb_hex: str) -> tuple[int, int, int]:
    h = rgb_hex.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def make_logo_png(path: Path, size: int = 256) -> None:
    """Ghost emblem rasterised with PIL: dark rounded bg, cyan glow, ghost."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=48, fill=_hex(BG) + (255,))
    # glow: soft cyan radial blob behind the ghost
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([28, 8, size - 28, size - 60], fill=_hex(CYAN) + (70,))
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)
    # network path nodes along the bottom
    nodes = [(36, 196), (86, 158), (128, 186), (176, 150), (220, 188)]
    s = size / 256.0
    pts = [(x * s, y * s) for x, y in nodes]
    draw.line(pts, fill=_hex(GREEN) + (255,), width=max(2, int(3 * s)), joint="curve")
    for i, (x, y) in enumerate(pts):
        r = 7 * s if i in (0, 4) else 6 * s
        col = _hex(DANGER) if i == 4 else _hex(GREEN)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))
    # ghost body: rounded-top dome with a wavy hem
    gx0, gx1 = 72 * s, 184 * s
    gy0, gy1 = 34 * s, 172 * s
    draw.pieslice([gx0, gy0, gx1, gy0 + (gx1 - gx0)], start=180, end=360,
                  fill=_hex(CYAN) + (255,))
    draw.rectangle([gx0, gy0 + (gx1 - gx0) / 2, gx1, gy1 - 12 * s],
                   fill=_hex(CYAN) + (255,))
    # wavy hem: three scallops
    hem_y = gy1 - 12 * s
    step = (gx1 - gx0) / 3
    for i in range(3):
        x0 = gx0 + i * step
        draw.pieslice([x0, hem_y - 12 * s, x0 + step, hem_y + 12 * s],
                      start=0, end=180, fill=_hex(CYAN) + (255,))
    # eyes + mouth
    for cx in (108 * s, 148 * s):
        draw.ellipse([cx - 9 * s, 80 * s, cx + 9 * s, 104 * s],
                     fill=_hex(BG) + (255,))
        draw.ellipse([cx - 2 * s, 86 * s, cx + 5 * s, 93 * s],
                     fill=_hex(CYAN) + (255,))
    draw.arc([118 * s, 108 * s, 138 * s, 126 * s], start=20, end=160,
             fill=_hex(BG) + (255,), width=max(2, int(4 * s)))
    img.convert("RGB").save(path, format="PNG", optimize=True)


def make_radar_gif(path: Path, width: int = 480, height: int = 240,
                   frames: int = 24) -> None:
    """Animated radar sweep: dark bg, rotating cyan sweep + fading blips."""
    cx, cy, radius = width // 2, height // 2 + 8, 100
    blips = [  # (angle deg, distance 0..1, phase frame offset)
        (35, 0.55, 0), (120, 0.75, 6), (210, 0.4, 12),
        (290, 0.65, 3), (160, 0.9, 18), (250, 0.3, 9),
    ]
    imgs = []
    for f in range(frames):
        img = Image.new("RGB", (width, height), _hex(BG))
        draw = ImageDraw.Draw(img, "RGBA")
        # rings + crosshair
        for r in (radius, int(radius * 0.66), int(radius * 0.33)):
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         outline=_hex(CYAN) + (60,), width=1)
        draw.line([cx - radius, cy, cx + radius, cy], fill=_hex(CYAN) + (40,))
        draw.line([cx, cy - radius, cx, cy + radius], fill=_hex(CYAN) + (40,))
        # sweep wedge (trailing fade)
        sweep = (f / frames) * 360.0
        for trail in range(0, 50, 5):
            a0 = sweep - trail
            alpha = max(8, 110 - trail * 2)
            draw.pieslice([cx - radius, cy - radius, cx + radius, cy + radius],
                          start=a0 - 5, end=a0, fill=_hex(CYAN) + (alpha,))
        draw.line([cx, cy,
                   cx + radius * math.cos(math.radians(-sweep)),
                   cy + radius * math.sin(math.radians(-sweep))],
                  fill=_hex(CYAN) + (255,), width=2)
        # blips light up just after the sweep passes them, then fade
        for angle, dist, offset in blips:
            age = (f - offset) % frames
            if age > 10:
                continue
            a = math.radians(-angle)
            bx = cx + radius * dist * math.cos(a)
            by = cy + radius * dist * math.sin(a)
            alpha = int(255 * (1 - age / 10))
            r = 5 + (10 - age) // 3
            draw.ellipse([bx - r, by - r, bx + r, by + r],
                         fill=_hex(GREEN) + (alpha,))
            draw.ellipse([bx - 2, by - 2, bx + 2, by + 2],
                         fill=(255, 255, 255, alpha))
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=_hex(CYAN))
        # caption
        draw.text((12, height - 22), "SCANNING  ·  GHOSTPATH X",
                  fill=_hex(CYAN))
        imgs.append(img.convert("P", palette=Image.ADAPTIVE, colors=64))
    imgs[0].save(path, format="GIF", save_all=True, append_images=imgs[1:],
                 duration=90, loop=0, optimize=True)


# ---------------------------------------------------------------- main ---

def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "logo.svg").write_text(LOGO_SVG, encoding="utf-8")
    (ASSETS / "graph-empty.svg").write_text(GRAPH_EMPTY_SVG, encoding="utf-8")
    for name, (color, _label, inner) in AGENT_ICONS.items():
        (ASSETS / name).write_text(agent_svg(color, inner), encoding="utf-8")
    make_logo_png(ASSETS / "logo.png")
    make_radar_gif(ASSETS / "radar.gif")
    for p in sorted(ASSETS.iterdir()):
        print(f"{p.name:24s} {p.stat().st_size:>8,} bytes")


if __name__ == "__main__":
    main()
