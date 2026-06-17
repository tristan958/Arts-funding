#!/usr/bin/env python3
"""
Generate the Open Graph / social-share image (assets/og-image.png).

Pure standard library — no Pillow/cairo/matplotlib required. It includes a tiny
TrueType rasteriser so the dashboard's social card can be regenerated in any
environment that has Python 3 (and the bundled OFL fonts in tools/fonts/).

Run:  python tools/make_og_image.py
"""

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_DIRS = [Path(__file__).resolve().parent / "fonts",
             Path("/mnt/skills/examples/canvas-design/canvas-fonts")]
OUT = ROOT / "assets" / "og-image.png"

W, H = 1200, 630
SS = 4  # supersampling factor for anti-aliasing


# ---------------------------------------------------------------------------
# Minimal TrueType font reader (simple + composite glyphs, cmap 4 & 12)
# ---------------------------------------------------------------------------

class Font:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        self._tables = {}
        self._cmap = {}
        self._parse()

    def _u16(self, o): return struct.unpack(">H", self.data[o:o + 2])[0]
    def _s16(self, o): return struct.unpack(">h", self.data[o:o + 2])[0]
    def _u32(self, o): return struct.unpack(">I", self.data[o:o + 4])[0]

    def _parse(self):
        num = self._u16(4)
        p = 12
        for _ in range(num):
            tag = self.data[p:p + 4].decode("latin-1")
            self._tables[tag] = (self._u32(p + 8), self._u32(p + 12))
            p += 16
        head = self._tables["head"][0]
        self.units = self._u16(head + 18)
        self.loca_long = self._s16(head + 50)
        self.num_glyphs = self._u16(self._tables["maxp"][0] + 4)
        self.num_hmetrics = self._u16(self._tables["hhea"][0] + 34)
        self._parse_loca()
        self._parse_cmap()

    def _parse_loca(self):
        off, _ = self._tables["loca"]
        self.loca = []
        if self.loca_long:
            for i in range(self.num_glyphs + 1):
                self.loca.append(self._u32(off + i * 4))
        else:
            for i in range(self.num_glyphs + 1):
                self.loca.append(self._u16(off + i * 2) * 2)

    def _parse_cmap(self):
        base = self._tables["cmap"][0]
        n = self._u16(base + 2)
        best = None
        for i in range(n):
            plat = self._u16(base + 4 + i * 8)
            enc = self._u16(base + 6 + i * 8)
            sub = self._u32(base + 8 + i * 8)
            score = {(3, 10): 4, (3, 1): 3, (0, 4): 3, (0, 3): 2, (3, 0): 1}.get((plat, enc), 0)
            if best is None or score > best[0]:
                best = (score, base + sub)
        self._read_cmap_subtable(best[1])

    def _read_cmap_subtable(self, o):
        fmt = self._u16(o)
        if fmt == 4:
            segx2 = self._u16(o + 6)
            seg = segx2 // 2
            end = o + 14
            start = end + segx2 + 2
            delta = start + segx2
            rangeoff = delta + segx2
            for s in range(seg):
                e = self._u16(end + s * 2)
                st = self._u16(start + s * 2)
                dl = self._u16(delta + s * 2)
                ro = self._u16(rangeoff + s * 2)
                for c in range(st, e + 1):
                    if c == 0xFFFF:
                        continue
                    if ro == 0:
                        g = (c + dl) & 0xFFFF
                    else:
                        gi = rangeoff + s * 2 + ro + (c - st) * 2
                        g = self._u16(gi)
                        if g:
                            g = (g + dl) & 0xFFFF
                    if g:
                        self._cmap[c] = g
        elif fmt == 12:
            ngroups = self._u32(o + 12)
            p = o + 16
            for _ in range(ngroups):
                sc, ec, sg = self._u32(p), self._u32(p + 4), self._u32(p + 8)
                for c in range(sc, ec + 1):
                    self._cmap[c] = sg + (c - sc)
                p += 12

    def advance(self, gid):
        off = self._tables["hmtx"][0]
        if gid >= self.num_hmetrics:
            gid = self.num_hmetrics - 1
        return self._u16(off + gid * 4)

    def glyph_contours(self, gid, depth=0):
        """Return list of contours; each contour a list of (x, y) in em units."""
        if gid >= self.num_glyphs:
            return []
        start = self._tables["glyf"][0] + self.loca[gid]
        end = self._tables["glyf"][0] + self.loca[gid + 1]
        if end <= start:
            return []
        nc = self._s16(start)
        if nc < 0:
            return self._composite(start + 10, depth)
        return self._simple(start, nc)

    def _simple(self, o, nc):
        p = o + 10
        ends = [self._u16(p + i * 2) for i in range(nc)]
        p += nc * 2
        npts = ends[-1] + 1
        ilen = self._u16(p)
        p += 2 + ilen
        flags = []
        while len(flags) < npts:
            f = self.data[p]; p += 1
            flags.append(f)
            if f & 8:
                r = self.data[p]; p += 1
                flags.extend([f] * r)
        xs, x = [], 0
        for f in flags:
            if f & 2:
                d = self.data[p]; p += 1
                x += d if (f & 16) else -d
            elif not (f & 16):
                x += self._s16(p); p += 2
            xs.append(x)
        ys, y = [], 0
        for f in flags:
            if f & 4:
                d = self.data[p]; p += 1
                y += d if (f & 32) else -d
            elif not (f & 32):
                y += self._s16(p); p += 2
            ys.append(y)
        pts = [(xs[i], ys[i], bool(flags[i] & 1)) for i in range(npts)]
        contours, s = [], 0
        for e in ends:
            contours.append(self._flatten(pts[s:e + 1]))
            s = e + 1
        return contours

    def _composite(self, p, depth):
        contours = []
        if depth > 5:
            return contours
        while True:
            flags = self._u16(p); gi = self._u16(p + 2); p += 4
            if flags & 1:  # ARG_1_AND_2_ARE_WORDS
                a1 = self._s16(p); a2 = self._s16(p + 2); p += 4
            else:
                a1 = struct.unpack(">b", self.data[p:p + 1])[0]
                a2 = struct.unpack(">b", self.data[p + 1:p + 2])[0]
                p += 2
            sx = sy = 1.0; s01 = s10 = 0.0
            if flags & 8:
                sx = sy = self._s16(p) / 16384.0; p += 2
            elif flags & 0x40:
                sx = self._s16(p) / 16384.0; sy = self._s16(p + 2) / 16384.0; p += 4
            elif flags & 0x80:
                sx = self._s16(p) / 16384.0; s01 = self._s16(p + 2) / 16384.0
                s10 = self._s16(p + 4) / 16384.0; sy = self._s16(p + 6) / 16384.0; p += 8
            dx, dy = (a1, a2) if (flags & 2) else (0, 0)
            for c in self.glyph_contours(gi, depth + 1):
                contours.append([(sx * x + s10 * y + dx, s01 * x + sy * y + dy) for x, y in c])
            if not (flags & 0x20):  # MORE_COMPONENTS
                break
        return contours

    @staticmethod
    def _flatten(pts):
        if not pts:
            return []
        # Ensure the contour starts on-curve (insert implied midpoints as needed).
        if not pts[0][2]:
            if pts[-1][2]:
                pts = [pts[-1]] + pts[:-1]
            else:
                mx = (pts[0][0] + pts[-1][0]) / 2
                my = (pts[0][1] + pts[-1][1]) / 2
                pts = [(mx, my, True)] + pts
        out = [(pts[0][0], pts[0][1])]
        n = len(pts)
        i = 1
        cur = (pts[0][0], pts[0][1])
        while i <= n:
            p = pts[i % n]
            if p[2]:
                out.append((p[0], p[1])); cur = (p[0], p[1]); i += 1
            else:
                nxt = pts[(i + 1) % n]
                if nxt[2]:
                    end = (nxt[0], nxt[1]); i += 2
                else:
                    end = ((p[0] + nxt[0]) / 2, (p[1] + nxt[1]) / 2); i += 1
                for t in (k / 8 for k in range(1, 9)):
                    mt = 1 - t
                    x = mt * mt * cur[0] + 2 * mt * t * p[0] + t * t * end[0]
                    y = mt * mt * cur[1] + 2 * mt * t * p[1] + t * t * end[1]
                    out.append((x, y))
                cur = end
        return out


# ---------------------------------------------------------------------------
# Canvas + rasteriser
# ---------------------------------------------------------------------------

class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.buf = bytearray(w * h * 3)

    def set_bg_gradient(self, top, bottom):
        for y in range(self.h):
            t = y / (self.h - 1)
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            row = y * self.w * 3
            for x in range(self.w):
                i = row + x * 3
                self.buf[i] = r; self.buf[i + 1] = g; self.buf[i + 2] = b

    def blend(self, x, y, color, a):
        if a <= 0 or x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = (y * self.w + x) * 3
        for k in range(3):
            self.buf[i + k] = int(self.buf[i + k] * (1 - a) + color[k] * a)

    def fill(self, contours, color, alpha=1.0):
        """Fill polygon contours (device coords, y-down) with anti-aliasing."""
        if not contours:
            return
        xs = [p[0] for c in contours for p in c]
        ys = [p[1] for c in contours for p in c]
        minx, maxx = int(min(xs)) - 1, int(max(xs)) + 2
        miny, maxy = int(min(ys)) - 1, int(max(ys)) + 2
        minx = max(minx, 0); miny = max(miny, 0)
        maxx = min(maxx, self.w); maxy = min(maxy, self.h)
        if maxx <= minx or maxy <= miny:
            return
        bw, bh = maxx - minx, maxy - miny
        hw, hh = bw * SS, bh * SS
        # Build edges in hi-res local coords.
        edges = []
        for c in contours:
            m = len(c)
            for j in range(m):
                x0, y0 = c[j]
                x1, y1 = c[(j + 1) % m]
                y0 = (y0 - miny) * SS; y1 = (y1 - miny) * SS
                x0 = (x0 - minx) * SS; x1 = (x1 - minx) * SS
                if y0 == y1:
                    continue
                edges.append((y0, y1, x0, x1))
        cov = [0] * (bw * bh)
        for sy in range(hh):
            yc = sy + 0.5
            xs_hits = []
            for y0, y1, x0, x1 in edges:
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    t = (yc - y0) / (y1 - y0)
                    xs_hits.append((x0 + t * (x1 - x0), 1 if y1 > y0 else -1))
            if not xs_hits:
                continue
            xs_hits.sort()
            wind = 0
            py = (sy // SS) * bw
            for k in range(len(xs_hits) - 1):
                wind += xs_hits[k][1]
                if wind != 0:
                    xa = xs_hits[k][0]; xb = xs_hits[k + 1][0]
                    xi = int(xa + 0.5)
                    xe = int(xb + 0.5)
                    for hx in range(max(xi, 0), min(xe, hw)):
                        cov[py + (hx // SS)] += 1
        inv = 1.0 / (SS * SS)
        for py in range(bh):
            for px in range(bw):
                c = cov[py * bw + px]
                if c:
                    self.blend(minx + px, miny + py, color, min(c * inv, 1.0) * alpha)

    def write_png(self, path):
        raw = bytearray()
        for y in range(self.h):
            raw.append(0)
            raw.extend(self.buf[y * self.w * 3:(y + 1) * self.w * 3])
        comp = zlib.compress(bytes(raw), 9)

        def chunk(tag, data):
            c = struct.pack(">I", len(data)) + tag + data
            return c + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            f.write(chunk(b"IHDR", ihdr))
            f.write(chunk(b"IDAT", comp))
            f.write(chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# Text layout
# ---------------------------------------------------------------------------

def find_font(name):
    for d in FONT_DIRS:
        p = d / name
        if p.exists():
            return Font(p)
    raise FileNotFoundError(name)


def text_width(font, text, size, tracking=0):
    s = size / font.units
    w = 0
    for ch in text:
        gid = font._cmap.get(ord(ch), 0)
        w += font.advance(gid) * s + tracking
    return w


def draw_text(canvas, font, text, x, baseline, size, color, tracking=0, alpha=1.0):
    s = size / font.units
    pen = x
    for ch in text:
        gid = font._cmap.get(ord(ch), 0)
        if ch != " ":
            contours = []
            for c in font.glyph_contours(gid):
                contours.append([(pen + px * s, baseline - py * s) for px, py in c])
            canvas.fill(contours, color, alpha)
        pen += font.advance(gid) * s + tracking
    return pen


def diamond(cx, cy, r):
    return [[(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]]


def main():
    gold = (212, 160, 23)
    cream = (245, 242, 233)
    muted = (176, 171, 158)

    cv = Canvas(W, H)
    cv.set_bg_gradient((26, 25, 20), (43, 41, 35))

    title = find_font("BigShoulders-Bold.ttf")
    label = find_font("InstrumentSans-Bold.ttf")
    body = find_font("InstrumentSans-Regular.ttf")

    M = 96  # left margin

    # Brand diamond motif (echoes the favicon), set on the right.
    dcx, dcy = 1000, 232
    cv.fill(diamond(dcx, dcy, 150), gold, 0.16)   # faint halo
    cv.fill(diamond(dcx, dcy, 118), gold, 0.9)    # outer ring
    cv.fill(diamond(dcx, dcy, 86), (32, 31, 26), 1.0)  # punch the centre
    cv.fill(diamond(dcx, dcy, 30), gold, 1.0)     # solid core

    # Kicker label
    draw_text(cv, label, "SOUTH AFRICA  ·  ARTS", M, 132, 30, gold, tracking=3)

    # Title stack (condensed display face)
    draw_text(cv, title, "ARTS FUNDING", M - 4, 270, 132, cream, tracking=1)
    draw_text(cv, title, "DASHBOARD", M - 4, 390, 132, gold, tracking=1)

    # Gold rule
    cv.fill([[(M, 430), (M + 360, 430), (M + 360, 436), (M, 436)]], gold, 1.0)

    # Subtitle
    draw_text(cv, body, "Live grants, tenders, bursaries & calls for proposals",
              M, 492, 33, muted, tracking=0)

    # Status diamonds (open / closing / closed) — subtle nod to the dashboard.
    for i, col in enumerate([(46, 125, 50), (216, 67, 21), (198, 40, 40)]):
        cv.fill(diamond(M + 10 + i * 34, 565, 9), col, 0.95)
    draw_text(cv, body, "Updated weekly", M + 130, 572, 24, muted)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv.write_png(OUT)
    print(f"Wrote {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
