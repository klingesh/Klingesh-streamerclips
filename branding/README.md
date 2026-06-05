# StreamerClips — Branding

Logo assets for StreamerClips. The mark is an **SC monogram** where the **C**
frames a **play triangle** (the "watch / clip" symbol), sitting inside a circular
badge — designed to work well as a YouTube profile picture (cropped to a circle).

## Files

| File | Background | Style | Use |
|------|-----------|-------|-----|
| `streamerclips_logo.png` | Dark badge | Glow | YouTube avatar (neon look) |
| `streamerclips_logo_transparent.png` | Transparent | Glow | Overlays / watermarks |
| `streamerclips_logo.svg` | Dark badge | Glow | Vector master (glow) |
| `streamerclips_logo_flat.png` | Dark badge | Flat | YouTube avatar (minimal) |
| `streamerclips_logo_flat_transparent.png` | Transparent | Flat | Overlays / watermarks |
| `streamerclips_logo_flat.svg` | Dark badge | Flat | Vector master (flat) |

All raster files are **800 × 800**. The SVGs are resolution-independent — export
any size you need from them.

## Palette

| Role | Hex |
|------|-----|
| Background top | `#0C121F` |
| Background bottom | `#03050B` |
| Electric blue (light) | `#60D2FF` |
| Electric blue (deep) | `#1A68FF` |
| Play triangle (light) | `#F0FAFF` |
| Frame ring | `#40C4FF` |

## Re-rendering / tweaking

The logo is generated programmatically by [`render_logo.py`](render_logo.py)
(pure Python — no third-party dependencies). It writes all six files:

```bash
python3 render_logo.py
```

Geometry, colors, and the glow on/off toggle live near the top of the script,
so colors, spacing, sizes, and styling can be adjusted and re-rendered easily.
