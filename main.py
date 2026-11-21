"""NIMBARA — a travel poster for a place that does not exist.

Pure-stdlib PNG painter: gradient dusk sky, a floating island with a
lighthouse, waterfalls that dissolve into a sea of clouds, and the
place's name set in a hand-drawn stroke font. No network, no files read;
the same bytes come out every run.
"""
import os
import zlib
import struct

W, H = 768, 1024

# frame buffer, RGB
px = bytearray(W * H * 3)


def put(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i:i + 3] = bytes(color)


def blend_px(x, y, color, a):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i] = int(px[i] * (1 - a) + color[0] * a)
        px[i + 1] = int(px[i + 1] * (1 - a) + color[1] * a)
        px[i + 2] = int(px[i + 2] * (1 - a) + color[2] * a)


def fill_span(y, x0, x1, color):
    if y < 0 or y >= H:
        return
    x0 = max(0, int(x0))
    x1 = min(W - 1, int(x1))
    if x1 < x0:
        return
    i = (y * W + x0) * 3
    px[i:i + (x1 - x0 + 1) * 3] = bytes(color) * (x1 - x0 + 1)


def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def sky():
    stops = [(0.0, (22, 32, 72)), (0.42, (52, 66, 122)),
             (0.60, (146, 96, 110)), (0.68, (240, 166, 96)),
             (0.74, (246, 196, 128))]
    for y in range(H):
        t = y / H
        for k in range(len(stops) - 1):
            t0, c0 = stops[k]
            t1, c1 = stops[k + 1]
            if t0 <= t <= t1:
                fill_span(y, 0, W - 1, lerp(c0, c1, (t - t0) / (t1 - t0)))
                break
        else:
            fill_span(y, 0, W - 1, stops[-1][1])


class Rng:
    def __init__(self, seed):
        self.s = seed

    def next(self, n):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s % n


def stars():
    rng = Rng(20261121)
    for _ in range(130):
        x = rng.next(W)
        y = rng.next(430)
        b = 120 + rng.next(120)
        a = max(0.0, 1.0 - y / 430.0) * 0.8
        blend_px(x, y, (b, b, min(255, b + 20)), a)
        if rng.next(4) == 0:
            blend_px(x + 1, y, (b, b, b), a * 0.6)


def disc(cx, cy, r, color, blend_a=None):
    for y in range(cy - r, cy + r + 1):
        dy = (y - cy) / r
        dx = int(r * (1 - dy * dy) ** 0.5)
        if blend_a is None:
            fill_span(y, cx - dx, cx + dx, color)
        else:
            for x in range(cx - dx, cx + dx + 1):
                blend_px(x, y, color, blend_a)


def ellipse(cx, cy, rx, ry, color):
    for y in range(cy - ry, cy + ry + 1):
        if ry == 0:
            continue
        dy = (y - cy) / ry
        if abs(dy) > 1:
            continue
        dx = int(rx * (1 - dy * dy) ** 0.5)
        fill_span(y, cx - dx, cx + dx, color)


def polygon(points, color):
    ys = [p[1] for p in points]
    for y in range(int(min(ys)), int(max(ys)) + 1):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            fill_span(y, xs[k], xs[k + 1], color)


def polygon_blend(points, color, a):
    ys = [p[1] for p in points]
    for y in range(int(min(ys)), int(max(ys)) + 1):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(max(0, int(xs[k])), min(W - 1, int(xs[k + 1])) + 1):
                blend_px(x, y, color, a)


def line(x0, y0, x1, y1, r, color):
    steps = max(int(abs(x1 - x0)), int(abs(y1 - y0)), 1)
    for i in range(steps + 1):
        t = i / steps
        disc(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), r, color)


def cloud(cx, cy, s, base, shade):
    ellipse(cx, cy + int(10 * s), int(120 * s), int(30 * s), shade)
    for dx, dy, rx, ry in [(-70, 6, 62, 30), (0, -12, 78, 42), (66, 4, 66, 32),
                           (-30, -2, 56, 30), (36, -6, 52, 28)]:
        ellipse(cx + int(dx * s), cy + int(dy * s), int(rx * s), int(ry * s), base)


def cloud_sea():
    # distant bank
    for cx, cy, s in [(90, 700, 1.2), (330, 716, 1.5), (610, 706, 1.3),
                      (760, 724, 1.1)]:
        cloud(cx, cy, s, (238, 214, 178), (206, 178, 148))
    # main sea: warm cream banks to the bottom edge
    fill_span(760, 0, W - 1, (244, 224, 188))
    for y in range(761, H):
        fill_span(y, 0, W - 1, (244, 224, 188))
    for cx, cy, s in [(60, 786, 1.6), (300, 812, 1.9), (560, 792, 1.7),
                      (740, 830, 1.5), (180, 884, 2.0), (480, 900, 2.1),
                      (700, 940, 1.8), (60, 960, 1.7), (330, 972, 2.0),
                      (600, 986, 1.9)]:
        cloud(cx, cy, s, (252, 244, 226), (226, 204, 170))


def waterfall(x, y0, y1, w0):
    for y in range(y0, y1):
        t = (y - y0) / (y1 - y0)
        w = w0 * (1 - t * 0.45)
        cx = x + int(6 * (t * t) * 4) // 4
        fill_span(y, cx - w, cx + w, lerp((198, 226, 234), (240, 244, 240), t))
        if y % 7 < 3:
            fill_span(y, cx - 1, cx + 1, (255, 255, 255))


def lower_cloud_shade():
    for cx, cy, s in [(150, 952, 1.5), (520, 976, 1.7), (720, 918, 1.2)]:
        cloud(cx, cy, s, (246, 232, 204), (214, 190, 156))


def island():
    # waterfalls first (behind the rock's front face at the edges)
    waterfall(292, 486, 716, 13)
    waterfall(478, 486, 700, 10)
    # rock: wide plateau tapering to a point
    polygon([(238, 452), (532, 452), (470, 560), (408, 668), (384, 692),
             (356, 660), (300, 556)], (56, 56, 88))
    polygon([(384, 452), (532, 452), (470, 560), (408, 668), (384, 692),
             (384, 452)], (76, 74, 110))
    # plateau top
    ellipse(385, 452, 150, 20, (96, 128, 94))
    ellipse(385, 448, 150, 18, (110, 142, 100))
    # a few pines
    for x, y, s in [(286, 442, 1.0), (316, 436, 0.8), (478, 440, 0.9),
                    (452, 434, 0.7)]:
        polygon([(x, y - int(34 * s)), (x - int(11 * s), y),
                 (x + int(11 * s), y)], (38, 74, 62))
        fill_span(y, x - 1, x + 1, (60, 46, 36)) if False else None
        for yy in range(y, y + 6):
            fill_span(yy, x - 1, x + 1, (60, 46, 36))


def lighthouse():
    bx, by = 372, 446  # base centre on the plateau
    # light beam, drawn before the tower cap
    polygon_blend([(bx + 8, by - 136), (bx + 214, by - 192), (bx + 218, by - 118)],
                  (255, 238, 170), 0.82)
    # tower: stacked bands, slight taper
    bands = [(0, (238, 233, 218)), (26, (198, 74, 60)), (52, (238, 233, 218)),
             (78, (198, 74, 60)), (102, (238, 233, 218))]
    for off, color in bands:
        w_top = 17 - off // 12
        w_bot = 19 - off // 12
        polygon([(bx - w_bot, by - off), (bx + w_bot, by - off),
                 (bx + w_top, by - off - 26), (bx - w_top, by - off - 26)],
                color)
    # gallery + lamp room
    fill_span(by - 132, bx - 16, bx + 16, (40, 40, 58))
    for yy in range(by - 131, by - 128):
        fill_span(yy, bx - 16, bx + 16, (40, 40, 58))
    for yy in range(by - 152, by - 132):
        fill_span(yy, bx - 11, bx + 11, (255, 214, 110))
    polygon([(bx - 15, by - 152), (bx + 15, by - 152), (bx, by - 168)],
            (40, 40, 58))
    disc(bx, by - 142, 21, (255, 230, 150), blend_a=0.5)


FONT = {
    "N": [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    "I": [[(2, 0), (2, 6)], [(0, 0), (4, 0)], [(0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2, 3), (4, 0), (4, 6)]],
    "B": [[(0, 0), (0, 6)], [(0, 0), (2.8, 0), (4, 1.1), (4, 2.1), (2.8, 3), (0, 3)],
          [(0, 3), (3, 3), (4, 4), (4, 5.1), (2.8, 6), (0, 6)]],
    "A": [[(0, 6), (2, 0), (4, 6)], [(1, 4.1), (3, 4.1)]],
    "R": [[(0, 0), (0, 6)], [(0, 0), (2.8, 0), (4, 1.1), (4, 2.1), (2.8, 3), (0, 3)],
          [(2.2, 3), (4, 6)]],
}


def draw_text(text, cx, y_top, size, color, r, tracking=0.32):
    unit = size / 6.0
    adv = size * (4 / 6.0) + size * tracking
    total = adv * len(text) - size * tracking
    x = cx - total / 2
    for ch in text:
        for stroke in FONT[ch]:
            pts = [(x + gx * unit, y_top + gy * unit) for gx, gy in stroke]
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                line(x0, y0, x1, y1, r, color)
        x += adv


def birds():
    for cx, cy, s in [(150, 250, 9), (196, 224, 7), (600, 206, 8),
                      (648, 238, 6), (556, 352, 5)]:
        line(cx - s, cy, cx - 1, cy - s // 2, 2, (30, 34, 58))
        line(cx + 1, cy - s // 2, cx + s, cy, 2, (30, 34, 58))


def frame():
    c = (250, 240, 214)
    for i in range(3):
        o = 22 + i
        for x in range(o, W - o):
            put(x, o, c)
            put(x, H - 1 - o, c)
        for y in range(o, H - o):
            put(o, y, c)
            put(W - 1 - o, y, c)


def render():
    sky()
    stars()
    disc(384, 612, 215, (255, 190, 110), blend_a=0.13)  # sunset halo, soft steps
    disc(384, 612, 165, (255, 198, 114), blend_a=0.17)
    disc(384, 612, 118, (255, 208, 124), blend_a=0.22)
    island()
    lighthouse()
    cloud_sea()
    lower_cloud_shade()
    birds()
    draw_text("NIMBARA", 384, 84, 96, (240, 180, 100), 7)
    draw_text("NIMBARA", 381, 81, 96, (250, 240, 214), 7)
    frame()
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += px[y * W * 3:(y + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", comp)
           + chunk(b"IEND", b""))
    return png


def main():
    data = render()
    assert len(data) <= 1_048_576, "poster exceeds the 1 MiB gate"
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
