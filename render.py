import math, random, subprocess, sys, os, glob
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

W, H, FPS = 1280, 720, 20
HERE = os.path.dirname(os.path.abspath(__file__))
NAR = os.path.join(HERE, "narration")
FF = imageio_ffmpeg.get_ffmpeg_exe()

BG = (18, 22, 32); BELT = (48, 54, 70); TXT = (235, 238, 245); DIM = (140, 150, 170)
GOLD = (232, 172, 52); GOLD_D = (150, 108, 34); BLUE = (110, 165, 240); BLUE_D = (56, 92, 150)
GREEN = (80, 205, 145); RED = (235, 85, 85); PANEL = (30, 36, 52); LINE = (70, 80, 105)

_fonts = {}
def font(sz, bold=False):
    k = (sz, bold)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", sz, index=1 if bold else 0)
    return _fonts[k]

def txt(d, x, y, s, sz=28, col=TXT, anchor="la", bold=False):
    d.text((x, y), s, font=font(sz, bold), fill=col, anchor=anchor)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, p): return a + (b - a) * p
def ease(p): p = clamp(p); return p * p * (3 - 2 * p)
def seg(t, a, b): return clamp((t - a) / (b - a)) if b > a else 1.0
def mix(c1, c2, p): return tuple(int(lerp(a, b, p)) for a, b in zip(c1, c2))

def box(d, x0, y0, x1, y1, fill=PANEL, outline=LINE, r=12, w=2):
    d.rounded_rectangle((x0, y0, x1, y1), r, fill=fill, outline=outline, width=w)

def header(d, n, title):
    txt(d, 50, 28, f"{n}", 40, GOLD, bold=True)
    txt(d, 100 if n < 10 else 120, 28, title, 40, TXT, bold=True)

def caption(d, s, col=TXT, y=668, sz=28):
    txt(d, W // 2, y, s, sz, col, "mm")

def disc(d, cx, cy, r, ang, face, sx=1.0, feat=True, alpha=1.0):
    rx = max(2, r * abs(sx))
    base = GOLD_D if face == "burr" else BLUE_D
    edge = GOLD if face == "burr" else BLUE
    d.ellipse((cx - rx, cy - r, cx + rx, cy + r), fill=base)
    if face == "burr":
        for i in range(40):
            a = i * 2 * math.pi / 40
            d.line((cx + math.cos(a) * (r - 3) * abs(sx), cy + math.sin(a) * (r - 3),
                    cx + math.cos(a) * (r + 8) * abs(sx), cy + math.sin(a) * (r + 8)), fill=GOLD, width=3)
        d.ellipse((cx - rx, cy - r, cx + rx, cy + r), outline=GOLD, width=3)
    else:
        d.ellipse((cx - rx, cy - r, cx + rx, cy + r), outline=edge, width=max(4, int(r * 0.09)))
    k = 0.72
    d.ellipse((cx - rx * k, cy - r * k, cx + rx * k, cy + r * k), outline=mix(base, edge, 0.35), width=2)
    if feat:
        a = math.radians(ang)
        fx = cx + math.cos(a) * r * 0.5 * sx
        fy = cy - math.sin(a) * r * 0.5
        fr = max(3, r * 0.12)
        d.ellipse((fx - fr * abs(sx) - 1, fy - fr, fx + fr * abs(sx) + 1, fy + fr), fill=BG, outline=TXT, width=2)

def belt(d, y0, y1, t, x0=0, x1=W, speed=120):
    d.rectangle((x0, y0, x1, y1), fill=BELT)
    off = (t * speed) % 40
    for x in range(int(x0 - 40 + off), int(x1), 40):
        d.line((x, y0 + 4, x, y1 - 4), fill=(60, 68, 88), width=2)

def arrow(d, x0, y0, x1, y1, col=DIM, w=3, h=12):
    d.line((x0, y0, x1, y1), fill=col, width=w)
    a = math.atan2(y1 - y0, x1 - x0)
    d.polygon([(x1, y1), (x1 - h * math.cos(a - .45), y1 - h * math.sin(a - .45)),
               (x1 - h * math.cos(a + .45), y1 - h * math.sin(a + .45))], fill=col)

def camera(d, cx, y, col=BLUE, label=None):
    box(d, cx - 36, y, cx + 36, y + 44, fill=(40, 48, 70), outline=col, r=8, w=3)
    d.ellipse((cx - 14, y + 44, cx + 14, y + 66), fill=(10, 12, 18), outline=col, width=3)
    if label: txt(d, cx, y - 14, label, 22, col, "mm", True)

# ------------------------------------------------------------------ scenes
rnd = random.Random(7)
S1 = [(rnd.uniform(0, 1500), rnd.uniform(380, 550), rnd.uniform(0, 360), rnd.choice(["burr", "rollover"]),
       rnd.uniform(-8, 8)) for _ in range(9)]

def scene1(d, t, D):
    header(d, 1, "The problem")
    for cx, face, lab, nm in ((330, "burr", "Burr side", "sharp raised edge from stamping"),
                              (950, "rollover", "Rollover side", "rounded edge")):
        disc(d, cx - 170, 170, 70, 40, face)
        txt(d, cx - 70, 130, lab, 32, GOLD if face == "burr" else BLUE, "lm", True)
        txt(d, cx - 70, 172, nm, 22, DIM, "lm")
    belt(d, 300, 600, t, speed=110)
    for x0, y, a, face, wob in S1:
        x = (x0 + t * 110) % 1600 - 160
        disc(d, x, y, 44, a + wob * t, face)
    p = seg(t, D * 0.55, D * 0.62)
    if p > 0:
        txt(d, W // 2, 648, "Random position  ·  random angle  ·  either face up", 30, TXT, "mm")
    if t > D * 0.78:
        box(d, 250, 616, 1030, 690, fill=(24, 60, 48), outline=GREEN)
        txt(d, W // 2, 653, "Goal: rollover up  ·  correct angle  ·  own slot", 30, GREEN, "mm", True)

ST = [("Presence\nsensor", 120), ("Camera 1", 330), ("Flipping\nmachine", 540),
      ("Camera 2", 750), ("Robot", 960), ("Slots", 1170)]

def station(d, i, x, active=1.0, hl=False):
    col = GREEN if hl else BLUE
    if i == 0:
        box(d, x - 22, 235, x + 22, 300, fill=(40, 48, 70), outline=col, r=6, w=3)
        d.line((x, 300, x, 330), fill=col, width=2)
    elif i in (1, 3):
        camera(d, x, 225, col)
        d.line((x, 291, x, 330), fill=col, width=2)
    elif i == 2:
        box(d, x - 70, 245, x + 70, 330, fill=(40, 48, 70), outline=GOLD if not hl else GREEN, r=10, w=3)
        txt(d, x, 288, "FLIP", 26, GOLD if not hl else GREEN, "mm", True)
    elif i == 4:
        d.line((x, 215, x - 40, 260), fill=col, width=8); d.line((x - 40, 260, x, 320), fill=col, width=8)
        d.ellipse((x - 14, 201, x + 14, 229), fill=col)
    elif i == 5:
        for r_ in range(2):
            for c_ in range(3):
                bx = x - 75 + c_ * 52; by = 440 + r_ * 52
                box(d, bx, by, bx + 44, by + 44, fill=(40, 48, 70), outline=col, r=6, w=2)

def line_scene(d, t, reveal, hl=None, disc_t=None):
    belt(d, 330, 400, t if disc_t is None else disc_t, speed=130)
    for i, (nm, x) in enumerate(ST):
        if i < reveal:
            station(d, i, x, hl=(hl == i))
            for k, ln in enumerate(nm.split("\n")):
                txt(d, x, 168 + k * 28, ln, 24, GREEN if hl == i else TXT, "mm", True)
    if reveal > 6:
        box(d, 640 - 70, 440, 640 + 70, 530, fill=(60, 30, 34), outline=RED)
        txt(d, 640, 485, "Reject bin", 22, RED, "mm", True)
        arrow(d, 600, 405, 620, 440, RED)
    if reveal > 7:
        box(d, 360, 78, 920, 130, fill=(30, 50, 44), outline=GREEN)
        txt(d, 640, 104, "Line computer + GPU  ·  every decision", 24, GREEN, "mm", True)
        for x in (330, 540, 750, 960):
            d.line((x, 131, x, 160), fill=GREEN, width=2)

def scene2(d, t, D):
    header(d, 2, "The cell layout")
    reveal = int(clamp((t - 0.5) / ((D - 3.0) / 8.0), 0, 8)) + 0
    reveal = min(8, reveal + 1) if t > 0.5 else 0
    line_scene(d, t, reveal)
    x = 40 + (t * 130) % 1100
    face = "burr" if x < 540 else "rollover"
    disc(d, x, 365, 26, 50 if x < 960 else 0, face)

def scene3(d, t, D):
    header(d, 3, "Camera 1 and its lighting")
    box(d, 330, 120, 950, 610, fill=(10, 12, 18), outline=LINE, w=3)
    txt(d, 940, 600, "enclosure", 18, DIM, "rm")
    camera(d, 640, 160, BLUE, None)
    txt(d, 760, 190, "Camera 1 · 12 MP", 20, BLUE, "lm", True)
    belt(d, 520, 570, t, 330, 950, speed=60)
    px = lerp(380, 640, ease(seg(t, 0.5, D * 0.2)))
    # low angle light on the left
    box(d, 345, 478, 395, 516, fill=(120, 100, 40), outline=GOLD, r=6, w=3)
    on = seg(t, D * 0.12, D * 0.2)
    if on > 0:
        for k in range(5):
            yy = 492 + k * 3
            d.line((395, yy, px - 70, 480 + k * 8), fill=mix(BG, GOLD, 0.25 + 0.15 * (k % 2)), width=2)
    disc(d, px, 480, 70, 30, "burr")
    if on > 0 and px > 600:
        for k in range(3):
            d.arc((px - 70 - k * 2, 410 - k * 2, px + 70 + k * 2, 550 + k * 2), 150, 210, fill=(255, 235, 150), width=5)
    txt(d, 640, 598, "low-angle light from the side", 20, GOLD, "mm")
    # left notes
    notes = ["PLC trigger as disc passes", "Belt position recorded", "Find disc and crop", "ML + OpenCV: which side?"]
    for i, n in enumerate(notes):
        if t > D * (0.22 + i * 0.12):
            txt(d, 40, 230 + i * 56, "• " + n, 22, TXT)
    # result
    p = seg(t, D * 0.72, D * 0.8)
    if p > 0:
        box(d, 985, 220, 1240, 470, fill=PANEL, outline=GOLD)
        disc(d, 1112, 320, 56, 30, "burr")
        txt(d, 1112, 405, "BURR", 30, GOLD, "mm", True)
        txt(d, 1112, 440, "confidence 97%", 22, TXT, "mm")
        d.rectangle((1010, 455, 1214, 463), fill=LINE); d.rectangle((1010, 455, 1010 + 204 * 0.97 * p, 463), fill=GREEN)
        arrow(d, 952, 340, 983, 340, GOLD)

def scene4(d, t, D):
    header(d, 4, "The decision and the flip")
    belt(d, 300, 380, t, speed=150)
    box(d, 560, 250, 720, 430, fill=(40, 48, 70), outline=GOLD, w=3)
    txt(d, 640, 240, "Flipping machine", 22, GOLD, "mm", True)
    box(d, 840, 450, 1000, 560, fill=(60, 30, 34), outline=RED)
    txt(d, 920, 505, "Reject bin", 24, RED, "mm", True)
    # disc A rollover passes
    def run(a, b):
        return ease(seg(t, D * a, D * b))
    pa = run(0.08, 0.38); xa = lerp(60, 1260, pa)
    disc(d, xa, 340, 32, 20, "rollover")
    pb = run(0.35, 0.65); xb = lerp(60, 1260, pb)
    fl = clamp((xb - 560) / 160)
    if fl < 0.5: disc(d, xb, 340, 32, 20, "burr", sx=math.cos(math.pi * fl))
    else: disc(d, xb, 340, 32, 20, "rollover", sx=-math.cos(math.pi * fl))
    pc = run(0.62, 0.92)
    xc = lerp(60, 920, min(1, pc * 1.4)); yc = 340 + 130 * clamp((pc - 0.7) / 0.3)
    disc(d, xc, yc, 32, 20, "burr")
    if t > D * 0.62: txt(d, xc, 290, "?", 40, RED, "mm", True)
    lab = [(0.08, "Rollover up » passes straight through", BLUE),
           (0.38, "Burr up » flipping machine turns it over", GOLD),
           (0.62, "Not confident » never guesses » reject bin", RED)]
    cur = [l for l in lab if t >= D * l[0]]
    if cur:
        txt(d, W // 2, 140, cur[-1][1], 32, cur[-1][2], "mm", True)
    if t > D * 0.5:
        txt(d, 40, 520, "Tracked by belt position count", 24, TXT)
        txt(d, 40, 556, "» right decision, right disc", 24, DIM)
    if t > D * 0.88:
        box(d, 250, 616, 1030, 690, fill=(24, 60, 48), outline=GREEN)
        txt(d, W // 2, 653, "Every disc that continues is rollover up", 30, GREEN, "mm", True)

def glow(d, cx, cy, r, col, n=8):
    for k in range(n, 0, -1):
        d.ellipse((cx - r * k / n, cy - r * k / n * 0.5, cx + r * k / n, cy + r * k / n * 0.5),
                  fill=mix(BG, col, 0.07 * (n - k + 1) * 0.6))

def scene5(d, t, D):
    header(d, 5, "Camera 2 and its lighting")
    box(d, 300, 110, 980, 620, fill=(10, 12, 18), outline=LINE, w=3)
    camera(d, 640, 140, BLUE)
    txt(d, 760, 160, "Camera 2 · 12 MP", 20, BLUE, "lm", True)
    on = seg(t, 1.0, 3.0)
    if on > 0:
        glow(d, 640, 420, 330 * on, (220, 230, 255))
    cx, cy, r = 640, 420, 150
    px = lerp(380, 640, ease(seg(t, 0.4, 3.0)))
    ang = 35
    spin = lerp(110, ang, ease(seg(t, 0.4, 3.0)))
    disc(d, px, cy, r, spin, "rollover")
    txt(d, 640, 590, "soft diffuse light shows the reference feature", 20, TXT, "mm")
    if t > D * 0.35:
        p = seg(t, D * 0.35, D * 0.45)
        a = math.radians(ang)
        fx = cx + math.cos(a) * r * 0.5; fy = cy - math.sin(a) * r * 0.5
        d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=GREEN)
        d.ellipse((fx - 14, fy - 14, fx + 14, fy + 14), outline=GREEN, width=3)
        d.line((cx, cy, cx + (fx - cx) * p, cy + (fy - cy) * p), fill=GREEN, width=4)
        d.line((cx, cy, cx + 120, cy), fill=DIM, width=2)
        d.arc((cx - 70, cy - 70, cx + 70, cy + 70), -ang, 0, fill=GOLD, width=4)
    if t > D * 0.5:
        txt(d, 1010, 220, "Angle", 26, DIM)
        txt(d, 1010, 250, f"{ang:.1f}°", 56, GREEN, bold=True)
        txt(d, 1010, 330, "Centre + feature", 22, TXT)
        txt(d, 1010, 358, "found by ML + OpenCV", 22, DIM)
    side = ["Own camera, own light:", "Cam 1 lit for the edge", "Cam 2 lit for the feature"]
    for i, s in enumerate(side):
        if t > D * (0.2 + i * 0.12): txt(d, 30, 230 + i * 40, s, 22, GOLD if i == 0 else TXT, "la", i == 0)
    if t > D * 0.72:
        txt(d, 30, 380, "Disc already flipped »", 22, TXT)
        txt(d, 30, 410, "no mirrored-angle fix", 22, TXT)
    if t > D * 0.88:
        txt(d, 30, 460, "Feature unclear » reject", 22, RED, "la", True)

def scene6(d, t, D):
    header(d, 6, "Why 12 megapixels")
    sizes = [56, 40, 28, 20, 14, 9]
    k = min(len(sizes) - 1, int(t / (D / len(sizes) * 0.98)))
    bs = sizes[k]
    cx, cy, R = 440, 390, 230
    n = int(2 * R // bs) + 1
    x0 = cx - n * bs / 2; y0 = cy - n * bs / 2
    for i in range(n):
        for j in range(n):
            px_ = x0 + i * bs + bs / 2; py_ = y0 + j * bs + bs / 2
            dist = math.hypot(px_ - cx, py_ - cy)
            if dist > R: continue
            col = BLUE_D
            if dist > R - 0.12 * R: col = BLUE
            fx = cx + math.cos(math.radians(35)) * R * 0.5; fy = cy - math.sin(math.radians(35)) * R * 0.5
            if math.hypot(px_ - fx, py_ - fy) < R * 0.12 + bs * 0.3: col = (235, 238, 245)
            d.rectangle((x0 + i * bs, y0 + j * bs, x0 + (i + 1) * bs - 1, y0 + (j + 1) * bs - 1), fill=col)
    npx = int(2 * R / bs)
    txt(d, 800, 190, "Pixels across the disc", 24, DIM)
    txt(d, 800, 222, f"{npx}", 64, TXT, bold=True)
    err = 12.0 / (npx / 8)
    txt(d, 800, 330, "Angle error", 24, DIM)
    txt(d, 800, 362, f"± {err:.1f}°", 64, GREEN, bold=True)
    d.rectangle((800, 460, 1200, 480), fill=LINE)
    d.rectangle((800, 460, 800 + 400 * clamp(err / 12), 480), fill=GREEN)
    txt(d, 800, 510, "More pixels » more precise angle,", 22, TXT)
    txt(d, 800, 540, "clearer view of the burr edge", 22, TXT)
    if t > D * 0.8:
        txt(d, W // 2, 668, "Final resolution set from disc size and field of view in testing", 24, GOLD, "mm")

def arm(d, bx, by, ex, ey, col=BLUE, l1=230, l2=230, w=12):
    dx, dy = ex - bx, ey - by
    dist = clamp(math.hypot(dx, dy), 20, l1 + l2 - 1)
    a = math.atan2(dy, dx)
    cosb = clamp((l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist), -1, 1)
    b = math.acos(cosb)
    jx = bx + l1 * math.cos(a - b); jy = by + l1 * math.sin(a - b)
    ex2 = bx + dist * math.cos(a); ey2 = by + dist * math.sin(a)
    d.line((bx, by, jx, jy), fill=col, width=w); d.line((jx, jy, ex2, ey2), fill=col, width=w)
    for (x, y) in ((bx, by), (jx, jy)): d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=col)
    d.ellipse((ex2 - 9, ey2 - 9, ex2 + 9, ey2 + 9), fill=GREEN)
    return ex2, ey2

def scene7(d, t, D):
    header(d, 7, "Calibration: camera and robot agree")
    # board
    bx0, by0, c = 60, 200, 38
    for i in range(7):
        for j in range(6):
            col = (225, 228, 236) if (i + j) % 2 == 0 else (30, 34, 46)
            d.rectangle((bx0 + i * c, by0 + j * c, bx0 + (i + 1) * c, by0 + (j + 1) * c), fill=col)
    k = int(seg(t, 1, D * 0.3) * 30)
    for n_ in range(k):
        i, j = n_ % 6, n_ // 6
        d.ellipse((bx0 + (i + 1) * c - 4, by0 + (j + 1) * c - 4, bx0 + (i + 1) * c + 4, by0 + (j + 1) * c + 4), fill=GREEN)
    txt(d, bx0 + 130, 170, "Camera sees pixels", 24, BLUE, "mm", True)
    camera(d, bx0 + 130, 460, BLUE)
    if t > D * 0.15:
        box(d, 330, 330, 560, 440, fill=PANEL, outline=GOLD)
        txt(d, 445, 360, "1. lens calibration", 20, TXT, "mm"); txt(d, 445, 388, "removes distortion", 20, DIM, "mm")
        txt(d, 445, 416, "2. camera » robot", 20, GOLD, "mm", True)
        arrow(d, 560, 385, 640, 385, GOLD)
    # robot side
    txt(d, 960, 170, "Robot moves in millimetres", 24, BLUE, "mm", True)
    box(d, 700, 200, 1220, 460, fill=(24, 28, 40), outline=LINE)
    pts = [(760 + i * 100, 250 + j * 80) for j in range(3) for i in range(5)]
    for (x, y) in pts: d.line((x - 8, y, x + 8, y), fill=DIM, width=2); d.line((x, y - 8, x, y + 8), fill=DIM, width=2)
    idx = int(seg(t, D * 0.3, D * 0.62) * (len(pts) - 1))
    tx, ty = pts[idx] if t > D * 0.3 else (960, 330)
    ex, ey = arm(d, 960, 560, tx, ty, l1=220, l2=220)
    for n_ in range(idx + 1 if t > D * 0.3 else 0):
        x, y = pts[n_]; d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=GREEN)
    txt(d, 960, 600, "six-axis: board through many poses · others: touch marked points", 18, DIM, "mm")
    if t > D * 0.64:
        txt(d, W // 2, 640, "Camera 2's calibration is the critical one: it tells the robot where to pick", 24, GOLD, "mm", True)
    if t > D * 0.78:
        box(d, 150, 660, 1130, 712, fill=PANEL, outline=LINE)
        txt(d, W // 2, 686, "Scheduled self-check  »  drift? recalibrate once  »  still out: stop, ask for maintenance", 22, GREEN, "mm", True)

def scene8(d, t, D):
    header(d, 8, "The robot picks, rotates and places")
    belt(d, 330, 400, t, speed=120)
    bx, by = 640, 80
    for r_ in range(2):
        for c_ in range(4):
            sx_ = 880 + c_ * 90; sy_ = 470 + r_ * 90
            box(d, sx_, sy_, sx_ + 76, sy_ + 76, fill=(40, 48, 70), outline=LINE, r=8)
            if r_ == 0 and c_ < 3 or (r_ == 1 and c_ < 1):
                disc(d, sx_ + 38, sy_ + 38, 28, 0, "rollover")
    txt(d, 1000, 450, "Slots", 22, DIM, "mm")
    a0 = 55
    pa = ease(seg(t, 0.5, D * 0.3))
    belt_x = lerp(100, 600, pa) if t < D * 0.4 else 600 + (t - D * 0.4) * 0
    # phases
    t1, t2, t3, t4 = D * 0.4, D * 0.5, D * 0.68, D * 0.9
    if t < t1:
        x = lerp(100, 640, ease(seg(t, 0.5, t1))); y = 365; ang = a0; ex, ey = x, 365 - 30 * seg(t, D * 0.25, t1)
        ex, ey = x, lerp(210, 345, ease(seg(t, D * 0.25, t1)))
    elif t < t2:
        p = ease(seg(t, t1, t2)); x = 640; ey = lerp(345, 220, p); y = ey + 20; ex = 640; ang = a0
    elif t < t3:
        p = ease(seg(t, t2, t3)); ex, ey = 640, 220; x, y = ex, ey + 20; ang = lerp(a0, 0, p)
    else:
        p = ease(seg(t, t3, t4)); ex = lerp(640, 880 + 90 * 1 + 38, p); ey = lerp(220, 470 + 90 + 38, p)
        x, y = ex, ey + 8 * (1 - p) + 0; ang = 0
    if t >= t4:
        x, y = 880 + 90 + 38, 470 + 90 + 38
        ex, ey = x, y - 20
    if t < t1 or t >= t4:
        pass
    if t >= t4:
        disc(d, x, y, 28, 0, "rollover")
    else:
        disc(d, x, y if t >= t1 else 365, 32 if t < t3 else 32 - 4 * seg(t, t3, t4), ang, "rollover")
    arm(d, bx, by, ex, ey - (0 if t >= t1 else 0), l1=250, l2=250)
    cap = [(0, "Instruction to PLC: pick position · belt count · rotation"), (t1, "Robot follows the belt and picks the disc"),
           (t2, "Rotates it by the measured amount"), (t3, "Places it in the matching slot")]
    cur = [c for c in cap if t >= c[0]][-1][1]
    txt(d, W // 2, 668, cur, 28, GOLD, "mm", True)
    if t >= t4:
        txt(d, W // 2, 625, "Rollover up · correct angle · correct place", 26, GREEN, "mm", True)

def scene9(d, t, D):
    header(d, 9, "Why a GPU")
    box(d, 520, 160, 860, 400, fill=PANEL, outline=GREEN, w=3)
    txt(d, 690, 145, "Line computer", 24, GREEN, "mm", True)
    box(d, 545, 195, 835, 255, fill=(40, 48, 70), outline=LINE); txt(d, 690, 225, "CPU: control, comms", 22, TXT, "mm")
    gpu_busy = 0.5 + 0.5 * math.sin(t * 3)
    box(d, 545, 280, 835, 375, fill=mix((40, 48, 70), (40, 110, 80), gpu_busy), outline=GREEN)
    txt(d, 690, 312, "GPU", 28, GREEN, "mm", True); txt(d, 690, 345, "side-deciding ML model", 20, TXT, "mm")
    for i, yy in enumerate((220, 330)):
        camera(d, 120, yy - 30, BLUE)
        txt(d, 120, yy + 55, f"Camera {i+1} · 12 MP", 18, DIM, "mm")
        for k in range(7):
            x = 200 + ((t * 150 + k * 80) % 560)
            if x < 510: d.rectangle((x, yy - 10, x + 36, yy + 10), fill=BLUE)
    if t > D * 0.4:
        txt(d, 1050, 230, "Always on", 26, TXT, "mm", True); txt(d, 1050, 262, "around the clock", 22, DIM, "mm")
        txt(d, 1050, 330, "Room to grow", 26, TXT, "mm", True); txt(d, 1050, 362, "larger models, more cameras", 20, DIM, "mm")
    rows = [("Capture next disc", BLUE), ("Judge this disc (GPU)", GREEN), ("Send last disc's instruction", GOLD)]
    for r_, (nm, col) in enumerate(rows):
        y = 450 + r_ * 56
        txt(d, 40, y + 20, nm, 20, TXT, "lm")
        for k in range(6):
            sx = 330 + k * 130 + r_ * 45
            d.rectangle((sx, y, sx + 100, y + 38), fill=mix(BG, col, 0.65))
    ph = 330 + ((t * 90) % 780)
    d.line((ph, 440, ph, 622), fill=TXT, width=2)
    txt(d, W // 2, 660, "Stages overlap: processing time stays steady under full load", 24, GOLD, "mm")
    if t > D * 0.78:
        box(d, 450, 80, 830, 118, fill=(24, 60, 48), outline=GREEN)
        txt(d, 640, 99, "On site · offline · designs stay confidential", 20, GREEN, "mm", True)

DR = random.Random(3)
CONF = [0.97 - 0.0015 * i + DR.uniform(-0.01, 0.01) - (0.0008 * max(0, i - 40) ** 1.1) for i in range(80)]

def scene10(d, t, D):
    header(d, 10, "Safety nets and keeping it healthy")
    panels = [(50, 120, 620, 360, "Confidence trend (wear watch)"), (660, 120, 1230, 360, "Reject rate"),
              (50, 390, 620, 620, "Count check"), (660, 390, 1230, 620, "Light & camera health")]
    for i, (x0, y0, x1, y1, nm) in enumerate(panels):
        if t < D * (0.05 + i * 0.1): continue
        box(d, x0, y0, x1, y1)
        txt(d, x0 + 20, y0 + 14, nm, 22, TXT, "la", True)
        if i == 0:
            n = int(seg(t, D * 0.1, D * 0.55) * 80)
            pts = [(x0 + 30 + k * 6.9, y1 - 30 - (CONF[k] - 0.7) / 0.3 * 160) for k in range(n)]
            if len(pts) > 1: d.line(pts, fill=BLUE, width=3)
            th = y1 - 30 - (0.9 - 0.7) / 0.3 * 160
            d.line((x0 + 30, th, x1 - 30, th), fill=RED, width=1)
            if n > 60: txt(d, x1 - 30, th - 14, "early alarm", 18, RED, "rm", True)
        if i == 1:
            for k in range(12):
                h = 20 + 10 * math.sin(k) + (k * 6 if k > 7 and t > D * 0.5 else 0)
                d.rectangle((x0 + 40 + k * 43, y1 - 30 - h, x0 + 70 + k * 43, y1 - 30), fill=GOLD if k <= 7 else RED if t > D * 0.5 else GOLD)
        if i == 2:
            txt(d, x0 + 30, y0 + 80, "Sensor count", 22, DIM); txt(d, x1 - 30, y0 + 80, "1,204", 26, TXT, "ra", True)
            txt(d, x0 + 30, y0 + 120, "Discs found", 22, DIM)
            ok = t < D * 0.7
            txt(d, x1 - 30, y0 + 120, "1,204" if ok else "1,203", 26, TXT if ok else RED, "ra", True)
            txt(d, x0 + 30, y0 + 170, "OK: match" if ok else "! missed disc noticed", 24, GREEN if ok else RED, "la", True)
        if i == 3:
            fail = t > D * 0.78
            for k, nm_ in enumerate(("Light", "Camera 1", "Camera 2")):
                cxx = x0 + 100 + k * 180
                col = GREEN if not (fail and k == 0) else RED
                d.ellipse((cxx - 28, y0 + 90, cxx + 28, y0 + 146), fill=col)
                txt(d, cxx, y0 + 170, nm_, 20, TXT, "mm")
            txt(d, (x0 + x1) // 2, y1 - 14, "Lamp fails » cell stops or rejects" if fail else "Brightness check running", 22, RED if fail else DIM, "mm", True)
    txt(d, W // 2, 668, "Unsure » reject · missed » noticed · unpicked » catch bin, back to input · new disc types: photograph and train", 20, DIM, "mm")

def scene11(d, t, D):
    header(d, 11, "Recap")
    steps = [(1, "Camera 1 finds the side"), (2, "The flipper corrects it"),
             (3, "Camera 2 measures the angle"), (4, "The robot picks, rotates and places it")]
    k = min(3, int(t / (D / 4.4)))
    hl = [1, 2, 3, 4][k]
    line_scene(d, t, 6, hl=hl, disc_t=t)
    x = 40 + (t / D) * 1130
    disc(d, x, 365, 26, 50 if x < 960 else 0, "burr" if x < 540 else "rollover")
    txt(d, W // 2, 600, f"{steps[k][0]}.  {steps[k][1]}", 36, GREEN, "mm", True)
    if t > D * 0.9:
        txt(d, W // 2, 660, "Rollover side up · every time", 28, TXT, "mm", True)

SCENES = [scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8, scene9, scene10, scene11]

def dur(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])

def main():
    auds = [os.path.join(NAR, f"scene{i+1:02d}.m4a") for i in range(11)]
    durs = [dur(a) + (1.0 if i < 10 else 1.8) for i, a in enumerate(auds)]
    # build audio track with padding
    cmd = [FF, "-y"]
    for a in auds: cmd += ["-i", a]
    fc = "".join(f"[{i}:a]apad=whole_dur={durs[i]:.3f}[a{i}];" for i in range(11))
    fc += "".join(f"[a{i}]" for i in range(11)) + "concat=n=11:v=0:a=1[out]"
    cmd += ["-filter_complex", fc, "-map", "[out]", os.path.join(HERE, "audio_padded.m4a")]
    subprocess.run(cmd, check=True, capture_output=True)
    out = os.path.join(HERE, "disc_orientation_video.mp4")
    pr = subprocess.Popen([FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", os.path.join(HERE, "audio_padded.m4a"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                           "-preset", "fast", "-crf", "20", "-c:a", "aac", "-shortest", out],
                          stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    total = sum(durs); done = 0.0
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    for si, (fn, D) in enumerate(zip(SCENES, durs)):
        n = int(D * FPS)
        for f in range(n):
            t = f / FPS
            img = Image.new("RGB", (W, H), BG)
            d = ImageDraw.Draw(img)
            fn(d, t, D)
            gt = done + t
            d.rectangle((0, H - 6, W * gt / total, H), fill=GOLD)
            pr.stdin.write(img.tobytes())
        done += D
        print("scene", si + 1, "done", flush=True)
    pr.stdin.close(); pr.wait()

if __name__ == "__main__":
    main()
