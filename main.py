#!/usr/bin/env python3
"""Render a single 1024x1024 PNG news-front-page summing up 2026-11-24 world news.

Deterministic: no network, no randomness, no timestamps from the clock.
If assets/base_collage.png exists and is a valid 1024x1024 RGB PNG the program
uses it as the textured background; otherwise it synthesises one from a
fixed seedless low-discrepancy pattern. Headlines are then drawn on top with
Pillow so that the final layout, text, and pixel bytes are identical between
runs on the same Pillow/freetype/libpng versions.

Output: /output/entry.png (overridable with --out)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.stderr.write("Pillow required: pip install Pillow\n")
    raise

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

CANVAS = 1024
OUTPUT_MAX_BYTES = 1_048_576  # 1 MiB gate
DATE_ISO = "2026-11-24"
DATE_HUMAN = "TUESDAY 24 NOVEMBER 2026"
MASTHEAD = "THE WORLD · DAILY BRIEF"

# Colour palette: high-contrast editorial (newsprint-ish but modernised).
PAPER = (247, 244, 236)
INK = (18, 20, 26)
RULE = (32, 36, 46)
RED = (176, 26, 34)
BLUE = (24, 58, 120)
GOLD = (196, 148, 30)
TEAL = (22, 92, 96)
GREY = (108, 112, 122)
WHITE = (255, 255, 255)

# Story layout. The lead is drawn biggest; secondaries are 4 balanced panels.
# Every string here is fixed so the image is exactly the same on every run.
LEAD_KICKER = "LEAD STORY · GLOBAL"
LEAD_HEADLINE = "RECORD CLIMATE ACCORD SIGNED IN GENEVA"
LEAD_DECK = (
    "194 nations commit to net-zero by 2040 and a $500bn annual "
    "adaptation fund; treaty enters force in March."
)
LEAD_META = "GENEVA · UNFCCC COP34"

SECONDARIES = [
    {
        "kicker": "ECONOMY",
        "head": "MARKETS RALLY\nON THAW IN\nTARIFF TALKS",
        "body": "US–EU framework deal trims\nsteel and EV levies.",
        "meta": "WASHINGTON / BRUSSELS",
        "colour": RED,
    },
    {
        "kicker": "MIDDLE EAST",
        "head": "CEASEFIRE HOLDS\nTHROUGH THIRD\nNIGHT IN GAZA",
        "body": "Aid convoys reach north;\ntalks on a lasting truce.",
        "meta": "GAZA / CAIRO",
        "colour": BLUE,
    },
    {
        "kicker": "ASIA · PACIFIC",
        "head": "TYPHOON MIRA\nMAKES LANDFALL\nNEAR MANILA",
        "body": "Mass evacuations; wind\ntops 240 km/h.",
        "meta": "MANILA",
        "colour": TEAL,
    },
    {
        "kicker": "SPORT",
        "head": "ARGENTINA IN\nFINAL AFTER\nLATE DRAMA",
        "body": "2–1 extra-time win sets\nup Sunday's decider.",
        "meta": "RIYADH",
        "colour": GOLD,
    },
]

# Sidebar/ticker items, small and dense.
TICKER = [
    "TOKYO: Nikkei +2.1% on tariff news",
    "BRUSSELS: ECB holds at 3.00%",
    "NEW DELHI: monsoon aid package approved",
    "SÃO PAULO: Amazon taskforce expanded",
    "NAIROBI: AU peace summit opens",
    "CANBERRA: reef recovery plan funded",
    "LONDON: cancer trial posts phase-III win",
    "SEOUL: chip export cap eased",
]

FOOTER = "PAGE 1 · CONTINUED ON A2–A9 · ALL TIMES UTC"


# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------

def _font_candidates():
    here = Path(__file__).resolve().parent
    return [
        here / "assets" / "fonts" / "editorial.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/Library/Fonts/Georgia.ttf"),
        Path("/System/Library/Fonts/Supplemental/Georgia.ttf"),
    ]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for cand in _font_candidates():
        if cand.is_file():
            try:
                return ImageFont.truetype(str(cand), size=size)
            except OSError:
                continue
    # Last resort: Pillow's bundled default (still deterministic per Pillow ver).
    return ImageFont.load_default(size=size)


# --------------------------------------------------------------------------
# Background
# --------------------------------------------------------------------------

def _procedural_background() -> Image.Image:
    """Deterministic newsprint texture: warm paper, faint world-map silhouette."""
    img = Image.new("RGB", (CANVAS, CANVAS), PAPER)
    px = img.load()
    # Very light vein pattern (deterministic; no RNG).
    for y in range(CANVAS):
        for x in range(0, CANVAS, 4):
            v = ((x * 1103515245 + y * 12345) >> 16) & 0x0F
            r, g, b = px[x, y]
            px[x, y] = (r - v // 3, g - v // 3, b - v // 4)
    draw = ImageDraw.Draw(img, "RGBA")
    # Faint globe motif (latitude/longitude arcs + landmass blobs).
    cx, cy, r = CANVAS // 2, 470, 300
    for i in range(3):
        draw.ellipse(
            [cx - r + i * 3, cy - r + i * 3, cx + r - i * 3, cy + r - i * 3],
            outline=(*BLUE, 40),
            width=1,
        )
    # Longitude arcs approximated by ellipses.
    for k in (40, 90, 150, 210, 260):
        w = max(6, int(abs(300 * (1 - k / 300)) + 8))
        draw.ellipse(
            [cx - w, cy - r, cx + w, cy + r], outline=(*BLUE, 26), width=1
        )
    # Latitude lines.
    for dy in (-180, -90, 0, 90, 180):
        yy = cy + dy
        draw.line([cx - r, yy, cx + r, yy], fill=(*BLUE, 26), width=1)
    # Rough landmasses (Africa / Eurasia / Americas).
    land = (140, 160, 140, 32)
    draw.ellipse([cx - 40, cy - 170, cx + 60, cy - 60], fill=land)   # Europe
    draw.ellipse([cx - 20, cy - 60, cx + 80, cy + 90], fill=land)    # Africa
    draw.ellipse([cx + 40, cy - 180, cx + 220, cy - 40], fill=land)  # Asia
    draw.ellipse([cx - 260, cy - 120, cx - 100, cy + 100], fill=land)  # Americas
    draw.ellipse([cx - 60, cy + 120, cx + 40, cy + 200], fill=land)  # S. America
    draw.ellipse([cx + 140, cy + 120, cx + 260, cy + 200], fill=land)  # Oceania
    return img


def _load_or_build_background() -> Image.Image:
    here = Path(__file__).resolve().parent
    p = here / "assets" / "base_collage.png"
    if p.is_file():
        try:
            with Image.open(p) as im:
                im.load()
                im = im.convert("RGB")
                if im.size == (CANVAS, CANVAS):
                    return im
        except (OSError, ValueError):
            pass
    return _procedural_background()


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------

def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Greedy word wrap; respects explicit newlines."""
    out: list[str] = []
    for raw in text.split("\n"):
        line = ""
        for word in raw.split(" "):
            cand = word if not line else line + " " + word
            if draw.textlength(cand, font=font) <= max_w:
                line = cand
            else:
                if line:
                    out.append(line)
                line = word
        if line:
            out.append(line)
    return out


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    fill,
    leading: int,
) -> int:
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += leading
    return y


def render(out_path: Path) -> None:
    img = _load_or_build_background().convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    margin = 40
    inner_w = CANVAS - 2 * margin

    f_masthead = load_font(24)
    f_date = load_font(22)
    f_kicker = load_font(20)
    f_lead = load_font(78)
    f_lead_deck = load_font(22)
    f_lead_meta = load_font(18)
    f_sec_head = load_font(34)
    f_sec_body = load_font(17)
    f_sec_meta = load_font(15)
    f_tick = load_font(16)
    f_footer = load_font(16)

    # --- Masthead ---------------------------------------------------------
    draw.rectangle([0, 0, CANVAS, 74], fill=INK)
    draw.text((margin, 20), MASTHEAD, font=f_masthead, fill=WHITE)
    date_text = DATE_HUMAN
    dw = draw.textlength(date_text, font=f_date)
    draw.text((CANVAS - margin - dw, 22), date_text, font=f_date, fill=GOLD)
    draw.line([0, 74, CANVAS, 74], fill=RED, width=4)

    # --- Lead story block -------------------------------------------------
    y = 96
    draw.rectangle([margin, y, margin + 6, y + 24], fill=RED)
    draw.text((margin + 16, y), LEAD_KICKER, font=f_kicker, fill=RED)
    y += 34

    lead_lines = _wrap(LEAD_HEADLINE, f_lead, inner_w, draw)
    lead_leading = int(f_lead.size * 1.06)
    y = _draw_text_block(draw, margin, y, lead_lines, f_lead, INK, lead_leading)
    y += 8
    draw.line([margin, y, CANVAS - margin, y], fill=RULE, width=2)
    y += 12

    deck_lines = _wrap(LEAD_DECK, f_lead_deck, inner_w - 40, draw)
    y = _draw_text_block(draw, margin, y, deck_lines, f_lead_deck, INK, 28)
    draw.text((margin, y + 4), LEAD_META, font=f_lead_meta, fill=GREY)
    y = y + 36

    # --- Secondary panels (2x2) ------------------------------------------
    grid_top = y + 8
    gutter = 24
    col_w = (inner_w - gutter) // 2
    row_h = 190
    for i, sec in enumerate(SECONDARIES):
        cx = margin + (i % 2) * (col_w + gutter)
        cy = grid_top + (i // 2) * (row_h + gutter)
        # Card body
        draw.rectangle([cx, cy, cx + col_w, cy + row_h], fill=(255, 255, 255, 235), outline=RULE, width=2)
        # Colour top band
        draw.rectangle([cx, cy, cx + col_w, cy + 6], fill=sec["colour"])
        # Kicker
        draw.text((cx + 14, cy + 16), sec["kicker"], font=f_kicker, fill=sec["colour"])
        # Headline
        head_lines = sec["head"].split("\n")
        hy = cy + 44
        for hl in head_lines:
            draw.text((cx + 14, hy), hl, font=f_sec_head, fill=INK)
            hy += int(f_sec_head.size * 1.06)
        # Body
        by = hy + 4
        for bl in sec["body"].split("\n"):
            draw.text((cx + 14, by), bl, font=f_sec_body, fill=INK)
            by += 22
        # Meta
        draw.text((cx + 14, cy + row_h - 26), sec["meta"], font=f_sec_meta, fill=GREY)

    # --- Ticker sidebar ---------------------------------------------------
    tick_top = grid_top + 2 * (row_h + gutter) + 6
    side_h = CANVAS - tick_top - 56
    draw.rectangle([margin, tick_top, CANVAS - margin, tick_top + side_h], fill=(255, 255, 255, 235), outline=RULE, width=2)
    draw.rectangle([margin, tick_top, CANVAS - margin, tick_top + 34], fill=INK)
    draw.text((margin + 14, tick_top + 8), "IN BRIEF · WORLDWIDE", font=f_kicker, fill=GOLD)
    ty = tick_top + 48
    for item in TICKER:
        if ty + 20 > tick_top + side_h - 4:
            break
        draw.text((margin + 14, ty), "• " + item, font=f_tick, fill=INK)
        ty += 24

    # --- Footer -----------------------------------------------------------
    draw.line([0, CANVAS - 40, CANVAS, CANVAS - 40], fill=RULE, width=2)
    draw.text((margin, CANVAS - 30), FOOTER, font=f_footer, fill=GREY)
    dw = draw.textlength(DATE_ISO + " · UTC", font=f_footer)
    draw.text((CANVAS - margin - dw, CANVAS - 30), DATE_ISO + " · UTC", font=f_footer, fill=GREY)

    # --- Final PNG (RGBA -> base colour composite to shrink + flatten) ----
    flat = Image.new("RGB", (CANVAS, CANVAS), PAPER)
    flat.paste(img, (0, 0), img)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Optimise + compress level 9. Oversize fallback: reduce to 8-bit palette.
    flat.save(out_path, format="PNG", optimize=True, compress_level=9)

    if out_path.stat().st_size > OUTPUT_MAX_BYTES:  # pragma: no cover
        flat2 = flat.convert("P", palette=Image.ADAPTIVE, colors=128)
        flat2.save(out_path, format="PNG", optimize=True, compress_level=9)


# --------------------------------------------------------------------------
# Verification helpers (used by tests, not by the render path)
# --------------------------------------------------------------------------

def _png_is_whole(data: bytes) -> bool:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    off = 8
    saw_iend = False
    while off + 12 <= len(data):
        length = struct.unpack(">I", data[off:off + 4])[0]
        ctype = data[off + 4:off + 8]
        off += 8
        chunk = data[off:off + length]
        if off + length + 4 > len(data):
            return False
        crc = struct.unpack(">I", data[off + length:off + length + 4])[0]
        if zlib.crc32(ctype + chunk) & 0xFFFFFFFF != crc:
            return False
        off += length + 4
        if ctype == b"IEND":
            saw_iend = True
            break
    return saw_iend and off == len(data)


# --------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render 2026-11-24 world-news front page.")
    ap.add_argument("--out", default="/output/entry.png", help="Output PNG path")
    ap.add_argument("--verify", action="store_true", help="Verify the produced PNG")
    args = ap.parse_args(argv)

    out_path = Path(args.out)
    try:
        render(out_path)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"render failed: {e}\n")
        return 1

    size = out_path.stat().st_size
    with out_path.open("rb") as fh:
        head = fh.read(32)
        fh.seek(0)
        data = fh.read()

    if not (_png_is_whole(data)):
        sys.stderr.write("error: output PNG is not whole\n")
        return 2
    if size > OUTPUT_MAX_BYTES:
        sys.stderr.write(f"error: output too large ({size} bytes)\n")
        return 3
    with Image.open(out_path) as im:
        if im.size != (CANVAS, CANVAS):
            sys.stderr.write(f"error: bad size {im.size}\n")
            return 4

    if args.verify:
        sha = hashlib.sha256(data).hexdigest()
        print(f"ok: {out_path} {size}B {CANVAS}x{CANVAS} sha256={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())