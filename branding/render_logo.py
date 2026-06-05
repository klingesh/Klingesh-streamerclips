#!/usr/bin/env python3
"""StreamerClips logo generator.

Produces:
  - streamerclips_logo.png   (800x800 raster, ready for a YouTube profile picture)
  - streamerclips_logo.svg   (true vector master, same geometry)

No third-party deps: pure-Python distance-field rasterizer + stdlib PNG encoder.
"""
import math
import struct
import zlib

W = H = 800

# ----------------------------------------------------------------------------
# Palette  (premium black + electric blue)
# ----------------------------------------------------------------------------
BG_TOP   = (12, 18, 31)      # near-black, faint blue
BG_BOT   = (3, 5, 11)        # deep black
GLOW_COL = (34, 132, 255)    # electric-blue ambient glow
RING_COL = (64, 196, 255)    # thin frame ring

BLUE_HI  = (96, 210, 255)    # #60D2FF  letters gradient top
BLUE_LO  = (26, 104, 255)    # #1A68FF  letters gradient bottom

TRI_HI   = (240, 250, 255)   # play triangle gradient top (near white)
TRI_LO   = (150, 222, 255)   # play triangle gradient bottom (light cyan)

# ----------------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------------
CX, CY = 400.0, 400.0

RING_R, RING_HW = 372.0, 3.6

# "S" : two round-capped circular arcs that join at the middle
S_UX, S_UY = 230.0, 352.0      # upper lobe centre
S_LX, S_LY = 230.0, 448.0      # lower lobe centre
S_R        = 48.0
S_H        = 27.0              # half stroke width

# "C" : one round-capped arc, open on the right
C_X, C_Y   = 505.0, 400.0
C_R        = 120.0
C_H        = 27.0
C_GAP      = 50.0             # half opening angle (deg) around 0 (right)

# play triangle (sits inside the C)
TRI = [(462.0, 351.0), (462.0, 449.0), (560.0, 400.0)]
TRI_RR = 11.0                 # corner rounding


def _rad(a):
    return a * math.pi / 180.0


def endpoints(cx, cy, r, a0, a1):
    return (
        (cx + r * math.cos(_rad(a0)), cy - r * math.sin(_rad(a0))),
        (cx + r * math.cos(_rad(a1)), cy - r * math.sin(_rad(a1))),
    )


# Arc definitions: (cx, cy, r, a0, a1, ccw, h, (e0, e1))
S_UPPER = (S_UX, S_UY, S_R, 10.0, 270.0, True,  S_H, endpoints(S_UX, S_UY, S_R, 10.0, 270.0))
S_LOWER = (S_LX, S_LY, S_R, 90.0, 180.0, False, S_H, endpoints(S_LX, S_LY, S_R, 90.0, 180.0))
C_ARC   = (C_X,  C_Y,  C_R, C_GAP, 360.0 - C_GAP, True, C_H,
           endpoints(C_X, C_Y, C_R, C_GAP, 360.0 - C_GAP))


def arc_sdf(px, py, arc):
    cx, cy, r, a0, a1, ccw, h, (e0, e1) = arc
    dx = px - cx
    dy = py - cy
    d = math.sqrt(dx * dx + dy * dy)
    ang = math.degrees(math.atan2(-dy, dx))
    if ccw:
        sweep = (a1 - a0) % 360.0
        delta = (ang - a0) % 360.0
    else:
        sweep = (a0 - a1) % 360.0
        delta = (a0 - ang) % 360.0
    if delta <= sweep:
        return abs(d - r) - h
    d0 = math.hypot(px - e0[0], py - e0[1])
    d1 = math.hypot(px - e1[0], py - e1[1])
    return (d0 if d0 < d1 else d1) - h


def _dot(ax, ay, bx, by):
    return ax * bx + ay * by


def tri_sdf(px, py, v):
    # signed distance to triangle (negative inside) - iq's formula
    (x0, y0), (x1, y1), (x2, y2) = v
    e0x, e0y = x1 - x0, y1 - y0
    e1x, e1y = x2 - x1, y2 - y1
    e2x, e2y = x0 - x2, y0 - y2
    v0x, v0y = px - x0, py - y0
    v1x, v1y = px - x1, py - y1
    v2x, v2y = px - x2, py - y2

    def pq(vx, vy, ex, ey):
        t = (vx * ex + vy * ey) / (ex * ex + ey * ey)
        t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
        return vx - ex * t, vy - ey * t

    p0x, p0y = pq(v0x, v0y, e0x, e0y)
    p1x, p1y = pq(v1x, v1y, e1x, e1y)
    p2x, p2y = pq(v2x, v2y, e2x, e2y)
    s = 1.0 if (e0x * e2y - e0y * e2x) > 0 else -1.0
    d0x, d0y = _dot(p0x, p0x, p0y, p0y) if False else (p0x * p0x + p0y * p0y, s * (v0x * e0y - v0y * e0x))
    # compute components
    dd0 = p0x * p0x + p0y * p0y
    dd1 = p1x * p1x + p1y * p1y
    dd2 = p2x * p2x + p2y * p2y
    sd0 = s * (v0x * e0y - v0y * e0x)
    sd1 = s * (v1x * e1y - v1y * e1x)
    sd2 = s * (v2x * e2y - v2y * e2x)
    dmin = min(dd0, dd1, dd2)
    smin = min(sd0, sd1, sd2)
    return -math.sqrt(dmin) if smin > 0 else math.sqrt(dmin)


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else (hi if x > hi else x)


def mix(c1, c2, t):
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


def coverage(sd, aa=1.0):
    return clamp(0.5 - sd / aa)


def render(glow=True):
    px_buf = bytearray(W * H * 3)
    AA = 1.1
    idx = 0
    for y in range(H):
        fy = y + 0.5
        ty = fy / H
        # background vertical gradient
        bg = mix(BG_TOP, BG_BOT, ty)
        # letter gradient factor by y
        lt = clamp((fy - 290.0) / 220.0)
        lcol = mix(BLUE_HI, BLUE_LO, lt)
        tt = clamp((fy - 351.0) / 98.0)
        tcol = mix(TRI_HI, TRI_LO, tt)
        for x in range(W):
            fx = x + 0.5
            r, g, b = bg

            dc = math.hypot(fx - CX, fy - CY)
            if glow:
                # ambient radial glow toward centre
                amb = clamp(1.0 - dc / 430.0)
                amb = amb * amb * 0.16
                r += GLOW_COL[0] * amb
                g += GLOW_COL[1] * amb
                b += GLOW_COL[2] * amb

            # shape distances (bbox guards to save trig)
            s_sd = 1e9
            if 150.0 <= fx <= 312.0 and 270.0 <= fy <= 532.0:
                s_sd = min(arc_sdf(fx, fy, S_UPPER), arc_sdf(fx, fy, S_LOWER))
            c_sd = 1e9
            if fx >= 355.0 and 248.0 <= fy <= 552.0:
                c_sd = arc_sdf(fx, fy, C_ARC)
            t_sd = 1e9
            if 450.0 <= fx <= 575.0 and 338.0 <= fy <= 462.0:
                t_sd = tri_sdf(fx, fy, TRI) - TRI_RR

            mark_sd = min(s_sd, c_sd, t_sd)

            # neon edge glow around whole mark
            if glow and mark_sd > 0.0 and mark_sd < 40.0:
                gi = math.exp(-mark_sd / 9.0) * 0.55
                r += GLOW_COL[0] * gi
                g += GLOW_COL[1] * gi
                b += GLOW_COL[2] * gi

            # thin frame ring
            ring_sd = abs(dc - RING_R) - RING_HW
            cov = coverage(ring_sd, AA)
            if cov > 0.0:
                r, g, b = mix((r, g, b), RING_COL, cov)

            # letters S + C
            lett_sd = min(s_sd, c_sd)
            cov = coverage(lett_sd, AA)
            if cov > 0.0:
                r, g, b = mix((r, g, b), lcol, cov)

            # play triangle
            cov = coverage(t_sd, AA)
            if cov > 0.0:
                r, g, b = mix((r, g, b), tcol, cov)

            px_buf[idx] = int(clamp(r, 0, 255) + 0.5)
            px_buf[idx + 1] = int(clamp(g, 0, 255) + 0.5)
            px_buf[idx + 2] = int(clamp(b, 0, 255) + 0.5)
            idx += 3
    return px_buf


def _png(path, raw, color_type, depth=8):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", W, H, depth, color_type, 0, 0, 0)
    comp = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(sig)
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", comp))
        f.write(chunk(b"IEND", b""))


def write_png(path, buf):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw.extend(buf[y * stride:(y + 1) * stride])
    _png(path, raw, 2)


def render_transparent(glow=True):
    """Just the mark (S + C + play + ring) on a transparent background."""
    px_buf = bytearray(W * H * 4)
    AA = 1.1
    idx = 0
    for y in range(H):
        fy = y + 0.5
        lt = clamp((fy - 290.0) / 220.0)
        lcol = mix(BLUE_HI, BLUE_LO, lt)
        tt = clamp((fy - 351.0) / 98.0)
        tcol = mix(TRI_HI, TRI_LO, tt)
        for x in range(W):
            fx = x + 0.5
            r = g = b = a = 0.0
            dc = math.hypot(fx - CX, fy - CY)

            s_sd = 1e9
            if 150.0 <= fx <= 312.0 and 270.0 <= fy <= 532.0:
                s_sd = min(arc_sdf(fx, fy, S_UPPER), arc_sdf(fx, fy, S_LOWER))
            c_sd = 1e9
            if fx >= 355.0 and 248.0 <= fy <= 552.0:
                c_sd = arc_sdf(fx, fy, C_ARC)
            t_sd = 1e9
            if 450.0 <= fx <= 575.0 and 338.0 <= fy <= 462.0:
                t_sd = tri_sdf(fx, fy, TRI) - TRI_RR
            ring_sd = abs(dc - RING_R) - RING_HW

            # neon glow contributes soft blue alpha
            mark_sd = min(s_sd, c_sd, t_sd)
            if glow and mark_sd > 0.0 and mark_sd < 40.0:
                gi = math.exp(-mark_sd / 9.0) * 0.55
                r, g, b = mix((r, g, b), GLOW_COL, min(1.0, gi))
                a = max(a, min(1.0, gi))

            def paint(col, sd, rr, gg, bb, aa_):
                cov = coverage(sd, AA)
                if cov > 0.0:
                    nr, ng, nb = mix((rr, gg, bb), col, cov)
                    return nr, ng, nb, max(aa_, cov)
                return rr, gg, bb, aa_

            r, g, b, a = paint(RING_COL, ring_sd, r, g, b, a)
            r, g, b, a = paint(lcol, min(s_sd, c_sd), r, g, b, a)
            r, g, b, a = paint(tcol, t_sd, r, g, b, a)

            px_buf[idx] = int(clamp(r, 0, 255) + 0.5)
            px_buf[idx + 1] = int(clamp(g, 0, 255) + 0.5)
            px_buf[idx + 2] = int(clamp(b, 0, 255) + 0.5)
            px_buf[idx + 3] = int(clamp(a * 255.0, 0, 255) + 0.5)
            idx += 4
    return px_buf


def write_png_rgba(path, buf):
    raw = bytearray()
    stride = W * 4
    for y in range(H):
        raw.append(0)
        raw.extend(buf[y * stride:(y + 1) * stride])
    _png(path, raw, 6)


def rgb(c):
    return "#%02X%02X%02X" % (int(c[0]), int(c[1]), int(c[2]))


def arc_polyline(arc, n=120):
    cx, cy, r, a0, a1, ccw, h, _ = arc
    if ccw:
        sweep = (a1 - a0) % 360.0
        angs = [a0 + sweep * i / n for i in range(n + 1)]
    else:
        sweep = (a0 - a1) % 360.0
        angs = [a0 - sweep * i / n for i in range(n + 1)]
    pts = [(cx + r * math.cos(_rad(a)), cy - r * math.sin(_rad(a))) for a in angs]
    d = "M %.2f %.2f " % pts[0] + " ".join("L %.2f %.2f" % p for p in pts[1:])
    return d, h * 2.0


def write_svg(path, glow=True):
    su_d, su_w = arc_polyline(S_UPPER)
    sl_d, sl_w = arc_polyline(S_LOWER)
    c_d, c_w = arc_polyline(C_ARC)
    tri_pts = " ".join("%.1f,%.1f" % p for p in TRI)

    glow_defs = f"""
    <radialGradient id="glow" cx="400" cy="400" r="430" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{rgb(GLOW_COL)}" stop-opacity="0.22"/>
      <stop offset="1" stop-color="{rgb(GLOW_COL)}" stop-opacity="0"/>
    </radialGradient>
    <filter id="soft" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="6"/>
    </filter>""" if glow else ""

    glow_circle = '<circle cx="400" cy="400" r="430" fill="url(#glow)"/>' if glow else ""

    glow_layer = f"""
  <g fill="none" stroke="url(#blue)" stroke-linecap="round" stroke-linejoin="round" opacity="0.9" filter="url(#soft)">
    <path d="{su_d}" stroke-width="{su_w:.1f}"/>
    <path d="{sl_d}" stroke-width="{sl_w:.1f}"/>
    <path d="{c_d}" stroke-width="{c_w:.1f}"/>
  </g>""" if glow else ""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="800" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{rgb(BG_TOP)}"/>
      <stop offset="1" stop-color="{rgb(BG_BOT)}"/>
    </linearGradient>{glow_defs}
    <linearGradient id="blue" x1="0" y1="290" x2="0" y2="510" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{rgb(BLUE_HI)}"/>
      <stop offset="1" stop-color="{rgb(BLUE_LO)}"/>
    </linearGradient>
    <linearGradient id="play" x1="0" y1="351" x2="0" y2="449" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{rgb(TRI_HI)}"/>
      <stop offset="1" stop-color="{rgb(TRI_LO)}"/>
    </linearGradient>
  </defs>

  <rect width="800" height="800" fill="url(#bg)"/>
  {glow_circle}
  <circle cx="400" cy="400" r="{RING_R}" fill="none" stroke="{rgb(RING_COL)}" stroke-width="{RING_HW * 2:.1f}"/>
{glow_layer}
  <g fill="none" stroke="url(#blue)" stroke-linecap="round" stroke-linejoin="round">
    <path d="{su_d}" stroke-width="{su_w:.1f}"/>
    <path d="{sl_d}" stroke-width="{sl_w:.1f}"/>
    <path d="{c_d}" stroke-width="{c_w:.1f}"/>
  </g>

  <polygon points="{tri_pts}" fill="url(#play)" stroke="url(#play)"
           stroke-width="{TRI_RR * 2:.1f}" stroke-linejoin="round"/>
</svg>
"""
    with open(path, "w") as f:
        f.write(svg)


if __name__ == "__main__":
    print("rendering raster (dark badge, glow)...")
    write_png("streamerclips_logo.png", render(glow=True))
    write_png_rgba("streamerclips_logo_transparent.png", render_transparent(glow=True))
    write_svg("streamerclips_logo.svg", glow=True)

    print("rendering flat (no-glow) variants...")
    write_png("streamerclips_logo_flat.png", render(glow=False))
    write_png_rgba("streamerclips_logo_flat_transparent.png", render_transparent(glow=False))
    write_svg("streamerclips_logo_flat.svg", glow=False)
    print("done")
