# Transcript — news-image-20261124

Deterministic program. No network, no clock, no randomness.
Every run produces byte-identical output given the same Pillow/freetype/libpng versions.

## Inputs

- Fixed constants in `main.py` (headlines, decks, kickers, palette).
- Optional `assets/base_collage.png` (1024x1024 RGB) used as textured background if present.
- Otherwise: procedurally synthesised background from a fixed seedless low-discrepancy pattern.

## Render steps

1. Create 1024x1024 RGB canvas on `PAPER` background.
2. Draw masthead bar with `MASTHEAD`, date `DATE_HUMAN`, and rules in `INK`/`RULE`.
3. Draw lead block: kicker `LEAD_KICKER`, headline `LEAD_HEADLINE`, deck `LEAD_DECK`, meta `LEAD_META`.
4. Draw four secondary panels from the `SECONDARIES` list (Economy, Middle East, Asia-Pacific, Sport).
5. Draw "In Brief" sidebar ticker (8 items, fixed strings).
6. Draw faint globe motif and footer date stamp `DATE_HUMAN`.
7. Save PNG to `/output/entry.png` (or `--out`).
8. Verify byte size ≤ `OUTPUT_MAX_BYTES` (1 MiB).

## Determinism

- No `datetime.now`, no `random`, no network calls.
- Text, coordinates, colours, and fonts are module-level constants.
- Output bytes are a pure function of `main.py` + Pillow/freetype/libpng versions.

## Output

- `entry.png`: 1024x1024 PNG, RGB.
- Size gate: 1 MiB.