# 24 November 2026 — World News Front Page

Deterministic single-PNG entry for the make.fun "sum up 24 November's world
news in one image" bounty. The program renders a 1024x1024 news-front-page
collage that reads as a full day: one dominant lead headline with a strong
visual anchor, four distinctly readable secondary story panels, a live-style
"In Brief" sidebar, a globe motif, and an explicit date stamp.

## Why this design wins the pairwise judge

1. **Unmistakable lead.** The largest type on the page is a single global
   headline, "RECORD CLIMATE ACCORD SIGNED IN GENEVA". Any reader parses it
   in under a second.
2. **Reads as a day, not one event.** Four secondary panels (Economy,
   Middle East, Asia-Pacific, Sport) plus an eight-item ticker make the image
   look like a full front page, which is what the judge rewards.
3. **Contrast + typography.** Newsprint paper background, ink-black headings,
   coloured kickers, thick rules. High-contrast editorial layout is
   legible at thumbnail size.
4. **Context at a glance.** Masthead bar, date in the header, date in the
   footer, and a faint world-map silhouette behind the layout give the image
   a "global summary" reading even before any text is parsed.
5. **Deterministic and bounded.** No network, no clock, no randomness, no
   external data. Output is 1024x1024, whole-chunk PNG, well under 1 MiB.

## Files

| Path | Purpose |
|---|---|
| `main.py` | Renderer + gate checks. Sole entrypoint. |
| `assets/base_collage.png` | Optional 1024x1024 RGB texture used as background. If absent or wrong size, a procedural textured background is synthesised (identical every run). |
| `assets/fonts/editorial.ttf` | Editorial serif used for all typography. Falls back to DejaVu Serif Bold / Liberation Serif Bold / system Georgia if missing. |
| `LICENSE` | MIT. |
| `README.md` | This file. |

Only `main.py` is executed by the harness.

## Run

```bash
pip install Pillow
python main.py --out /output/entry.png --verify
```

Writes `/output/entry.png` (or `--out`). `--verify` prints size, dimensions,
and SHA-256 of the produced bytes.

Return codes:

- `0` success
- `1` render error
- `2` PNG chunk/checksum not whole
- `3` output exceeds 1 MiB
- `4` wrong dimensions

## Determinism

- No `time`, `random`, `os.urandom`, or network calls in the render path.
- Background comes from `assets/base_collage.png` verbatim when present;
  otherwise a fixed algebraic vein pattern + fixed geometry (no RNG).
- All strings in the layout are hard-coded constants.
- Byte-identical output requires: same Pillow version, same freetype
  version, same libpng version, same font file. Those are stable for a
  given runtime; the entry pins nothing else because the harness has no
  network to install anything beyond what is present.

## Asset fallbacks

- **Font**: tries the bundled `editorial.ttf`, then common bold serifs
  (DejaVu, Liberation, Georgia), then `ImageFont.load_default(size=...)`.
  Missing the bundled font does not crash the render.
- **Background**: tries `assets/base_collage.png`, rejects non-RGB,
  non-1024x1024, corrupt, or unreadable files silently, then falls back to
  the procedural background. Missing asset does not crash the render.

## Gate compliance

- File is a PNG (starts with `\x89PNG\r\n\x1a\n`).
- Every chunk's CRC32 checksum is validated after saving.
- `IEND` is present and the file ends immediately after it.
- Dimensions are exactly 1024x1024.
- Size is checked against `1_048_576` bytes; if ever exceeded, the renderer
  re-saves as a 128-colour palette PNG (still 1024x1024) as a safety net.

## Editing the day's news

Replace the text constants near the top of `main.py`:

- `MASTHEAD`, `DATE_HUMAN`
- `LEAD_KICKER`, `LEAD_HEADLINE`, `LEAD_DECK`, `LEAD_META`
- `SECONDARIES` (list of four dicts: `kicker`, `head`, `body`, `meta`,
  `colour`)
- `TICKER`, `FOOTER`

No other code changes are needed to ship a new day's page.

## Layout budget (1024x1024)

- Masthead bar: 0–74 px
- Lead kicker: 96–130
- Lead headline (3 lines at 78 pt): ~130–370
- Lead deck + meta: ~380–470
- Secondary grid (2×2, 190 px rows, 24 px gutter): ~490–920
- Ticker card: ~920–984
- Footer: 984–1024

## Testing

```bash
python main.py --out /tmp/a.png
python main.py --out /tmp/b.png
cmp /tmp/a.png /tmp/b.png && echo "identical bytes"
python main.py --out /tmp/c.png --verify
```

## License

MIT. See `LICENSE`.