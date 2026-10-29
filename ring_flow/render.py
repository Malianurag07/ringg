# Renders the ring orientation cell walkthrough video.
# Needs voice/ (from make_voice.py). Usage: python render.py [scene ...]
import json, math, os, random, shutil, subprocess, sys
from contextlib import contextmanager
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(HERE, "voice")
TMP = os.path.join(HERE, "build")
OUT = os.path.join(HERE, "ring_orientation_flow.mp4")
FF = shutil.which("ffmpeg") or __import__("imageio_ffmpeg").get_ffmpeg_exe()

W, H, K = 1280, 720, 2            # design space, supersample factor
OW, OH, FPS = 1920, 1080, 25      # output

BG = (13, 17, 27); PANEL = (24, 30, 44); PANEL2 = (32, 40, 58); LINE = (58, 68, 92)
TXT = (236, 239, 245); DIM = (138, 149, 172); FAINT = (84, 94, 120)
GOLD = (238, 178, 58); GOLD_D = (150, 104, 28); BLUE = (96, 165, 250); BLUE_D = (42, 86, 156)
GREEN = (72, 212, 140); RED = (242, 86, 86); CYAN = (70, 212, 232); YEL = (252, 216, 72)
PURP = (172, 132, 252); ORANGE = (250, 150, 60); BELT = (42, 48, 62); BELT_L = (55, 62, 80)
WHITE = (255, 252, 240)

FONTS = {"r": "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
         "m": "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
         "s": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
         "b": "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
         "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
         "monob": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"}
_fc = {}
def font(px, f):
    k = (px, f)
    if k not in _fc: _fc[k] = ImageFont.truetype(FONTS[f], px)
    return _fc[k]

# ------------------------------------------------------------------ math
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, p): return a + (b - a) * p
def ease(p): p = clamp(p); return p * p * (3 - 2 * p)
def seg(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def ev(t, a, d=0.5): return ease(seg(t, a, a + d))
def mix(c1, c2, p): p = clamp(p); return tuple(int(lerp(a, b, p)) for a, b in zip(c1, c2))

# ------------------------------------------------------------------ view transform + primitives
class VW: s, ox, oy = 1.0, 0.0, 0.0

def view(s=1.0, cx=640, cy=400, sx=640, sy=400):
    VW.s, VW.ox, VW.oy = s, sx - cx * s, sy - cy * s

@contextmanager
def screen():
    old = (VW.s, VW.ox, VW.oy); VW.s, VW.ox, VW.oy = 1.0, 0.0, 0.0
    yield
    VW.s, VW.ox, VW.oy = old

def P(x, y): return ((x * VW.s + VW.ox) * K, (y * VW.s + VW.oy) * K)
def L(v): return v * VW.s * K
def LW(w): return max(1, round(L(w)))

def rect(d, x0, y0, x1, y1, fill=None, outline=None, w=2, r=0):
    a, b = P(x0, y0), P(x1, y1)
    if r: d.rounded_rectangle((a, b), radius=L(r), fill=fill, outline=outline, width=LW(w) if outline else 0)
    else: d.rectangle((a, b), fill=fill, outline=outline, width=LW(w) if outline else 0)

def ell(d, cx, cy, rx, ry=None, fill=None, outline=None, w=2):
    ry = rx if ry is None else ry
    a, b = P(cx - rx, cy - ry), P(cx + rx, cy + ry)
    if b[0] - a[0] < 1 or b[1] - a[1] < 1: return
    d.ellipse((a, b), fill=fill, outline=outline, width=LW(w) if outline else 0)

def line(d, pts, col, w=2):
    d.line([P(*p) for p in pts], fill=col, width=LW(w), joint="curve")

def poly(d, pts, fill=None, outline=None, w=2):
    d.polygon([P(*p) for p in pts], fill=fill, outline=outline, width=LW(w) if outline else 0)

def arc(d, cx, cy, r, a0, a1, col, w=3):
    # a0..a1 in maths degrees (counter-clockwise)
    a, b = P(cx - r, cy - r), P(cx + r, cy + r)
    lo, hi = sorted((a0, a1))
    d.arc((a, b), -hi, -lo, fill=col, width=LW(w))

def text(d, x, y, s, sz=18, col=TXT, anchor="la", f="r"):
    px = max(6, round(sz * VW.s * K))
    d.text(P(x, y), s, font=font(px, f), fill=col, anchor=anchor)

def tw(s, sz, f="r"): return font(round(sz * K), f).getlength(s) / K

def dashed(d, pts, col, w=2, dash=7, gap=5):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = math.hypot(x1 - x0, y1 - y0); u = 0.0
        while u < n:
            v = min(n, u + dash)
            line(d, [(lerp(x0, x1, u / n), lerp(y0, y1, u / n)), (lerp(x0, x1, v / n), lerp(y0, y1, v / n))], col, w)
            u += dash + gap

def arrow(d, x0, y0, x1, y1, col=DIM, w=3, h=11):
    line(d, [(x0, y0), (x1, y1)], col, w)
    a = math.atan2(y1 - y0, x1 - x0)
    poly(d, [(x1, y1), (x1 - h * math.cos(a - .45), y1 - h * math.sin(a - .45)),
             (x1 - h * math.cos(a + .45), y1 - h * math.sin(a + .45))], fill=col)

def tick(d, x, y, sz=14, col=GREEN, w=3):
    line(d, [(x - sz * .45, y), (x - sz * .1, y + sz * .35), (x + sz * .5, y - sz * .4)], col, w)

def cross(d, x, y, sz=12, col=RED, w=3):
    line(d, [(x - sz / 2, y - sz / 2), (x + sz / 2, y + sz / 2)], col, w)
    line(d, [(x - sz / 2, y + sz / 2), (x + sz / 2, y - sz / 2)], col, w)

def glow_box(d, x0, y0, x1, y1, col, p, r=10):
    # pulsing highlight around something that just appeared / is active
    for k in range(3):
        g = 3 + k * 3
        rect(d, x0 - g, y0 - g, x1 + g, y1 + g, outline=mix(BG, col, p * (0.8 - k * 0.25)), w=2, r=r + g)

def chip(d, x, y, s, col, sz=13, f="s", fill=None, anchor="l"):
    wdt = tw(s, sz, f) + 16; h = sz + 10
    x0 = x if anchor == "l" else x - wdt / 2 if anchor == "m" else x - wdt
    rect(d, x0, y - h / 2, x0 + wdt, y + h / 2, fill=fill or mix(BG, col, 0.18), outline=col, w=1.5, r=h / 2)
    text(d, x0 + wdt / 2, y, s, sz, col, "mm", f)
    return x0 + wdt

def card(d, x0, y0, x1, y1, title=None, col=LINE, fill=PANEL, tcol=TXT, sz=17):
    rect(d, x0, y0, x1, y1, fill=fill, outline=col, w=2, r=12)
    if title: text(d, x0 + 16, y0 + 14, title, sz, tcol, "la", "s")

# ------------------------------------------------------------------ rings
TYPES = {1: [(90, 26, .17)],
         2: [(90, 18, .15), (270, 18, .15)],
         3: [(90, 24, .17), (210, 11, .12), (330, 11, .12)],
         4: [(90, 14, .15), (0, 14, .15), (180, 14, .15), (270, 14, .15)],
         5: [(90, 32, .19), (135, 9, .1)]}

def ring_pts(cx, cy, r, ang, typ, sx=1.0, scale=1.0, n=240):
    pts = []
    for i in range(n):
        a = i * 360 / n; rr = r * scale
        for na, nw, nd in TYPES[typ]:
            if abs(((a - na + 180) % 360) - 180) < nw / 2: rr = r * scale * (1 - nd)
        A = math.radians(a + ang)
        pts.append((cx + math.cos(A) * rr * sx, cy - math.sin(A) * rr))
    return pts

def ring(d, cx, cy, r, ang, face, typ=3, sx=1.0, bg=BELT, photo=False, lit=0.0):
    burr = face == "burr"
    base, edge = (GOLD_D, GOLD) if burr else (BLUE_D, BLUE)
    if photo: base, edge = mix(base, (90, 90, 96), .35), mix(edge, (200, 200, 205), .3)
    base = mix(base, WHITE, lit * .35); edge = mix(edge, WHITE, lit * .4)
    if abs(sx) < 0.06:
        line(d, [(cx, cy - r), (cx, cy + r)], edge, 4); return
    pts = ring_pts(cx, cy, r, ang, typ, sx)
    poly(d, pts, fill=base)
    if photo:
        for k, sc in enumerate((0.97, 0.92, 0.86, 0.8, 0.74)):
            poly(d, ring_pts(cx, cy, r, ang, typ, sx, sc), fill=mix(base, edge, 0.12 + 0.07 * k))
    if burr:
        rough = random.Random(int(r * 10))
        for i in range(0, 240, 4):
            a, b = pts[i], (cx + (pts[i][0] - cx) * 1.06, cy + (pts[i][1] - cy) * 1.06 + rough.uniform(-.8, .8))
            line(d, [a, b], edge, 1.5)
    poly(d, pts, outline=edge, w=2 if not burr else 2.5)
    hr = r * 0.5
    ell(d, cx, cy, r * 0.74 * abs(sx), r * 0.74, outline=mix(base, edge, .45), w=1.2)
    ell(d, cx, cy, hr * abs(sx), hr, fill=bg, outline=mix(base, edge, .7), w=1.5)

# ------------------------------------------------------------------ plant layout (design coords)
BX0, BX1, BY0, BY1 = 20, 1010, 232, 312; BYC = 272
CAM1, CAM2, FLIPX, SENS1, SENS2 = 300, 660, 480, 150, 562
ROBOT = (930, 360)
PINS = [(1063 + i * 44, 245) for i in range(5)] + [(1063 + i * 44, 305) for i in range(5)]
LOGBOX = (900, 400, 1265, 700)

WIRES = {
    "trig1":    [(160, 221), (205, 221), (205, 148), (270, 148)],
    "cam1":     [(260, 340), (260, 470)],
    "cam2":     [(700, 340), (700, 415), (315, 415), (315, 485), (290, 485)],
    "enc":      [(40, 336), (40, 505), (90, 505)],
    "sw_srv":   [(290, 505), (340, 505)],
    "srv_plc":  [(560, 480), (600, 480)],
    "plc_srv":  [(600, 480), (560, 480)],
    "plc_flip": [(620, 440), (620, 385), (FLIPX, 385), (FLIPX, 340)],
    "plc_robot": [(780, 480), (830, 480), (830, 360), (908, 360)],
    "trig2":    [(530, 214), (575, 214), (575, 148), (630, 148)],
    "sens2":    [(SENS2, 222), (SENS2, 200), (760, 200)],
    "power":    [(600, 645), (560, 645)],
}
ALL = {"flap", "belt", "cam1", "cam2", "lights1", "lights2", "sensor", "encoder", "switch", "server", "ups",
       "plc", "flip", "robot", "pins", "wires", "log"}

def plen(pts): return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
def ppos(pts, p):
    tot = plen(pts) * clamp(p)
    for a, b in zip(pts, pts[1:]):
        s = math.hypot(b[0] - a[0], b[1] - a[1])
        if tot <= s: return (lerp(a[0], b[0], tot / s if s else 0), lerp(a[1], b[1], tot / s if s else 0))
        tot -= s
    return pts[-1]
def psub(pts, p):
    # leading part of a polyline, for "drawing" a wire or a lit trail
    tot = plen(pts) * clamp(p); out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        s = math.hypot(b[0] - a[0], b[1] - a[1])
        if tot >= s: out.append(b); tot -= s
        else: out.append((lerp(a[0], b[0], tot / s), lerp(a[1], b[1], tot / s))); break
    return out

def packet(d, path, p, label, col):
    if p <= 0 or p >= 1: return
    line(d, psub(path, p), col, 3)
    x, y = ppos(path, p)
    ell(d, x, y, 6, fill=col)
    wd = tw(label, 11, "monob") + 12
    rect(d, x + 9, y - 21, x + 9 + wd, y - 5, fill=mix(BG, col, .25), outline=col, w=1.2, r=4)
    text(d, x + 15, y - 13, label, 11, col, "lm", "monob")

def camera_icon(d, cx, y, col, label, sub):
    rect(d, cx - 30, y - 20, cx + 30, y + 20, fill=(34, 42, 62), outline=col, w=2.5, r=6)
    ell(d, cx, y + 26, 12, 8, fill=(8, 10, 16), outline=col, w=2.5)
    rect(d, cx + 8, y - 26, cx + 20, y - 20, fill=col)
    text(d, cx, y - 46, label, 15, col, "mm", "b")
    text(d, cx, y - 30, sub, 11, DIM, "mm", "m")

def belt_draw(d, off):
    rect(d, BX0, BY0, BX1, BY1, fill=BELT, r=6)
    n = int((BX1 - BX0) / 30)
    for i in range(n + 1):
        x = BX0 + ((i * 30 + off) % (n * 30))
        line(d, [(x, BY0 + 4), (x, BY1 - 4)], BELT_L, 2)
    for x in (BX0 + 6, BX1 - 6):
        rect(d, x - 7, BY0 - 4, x + 7, BY1 + 4, fill=(70, 78, 98), r=5)
    text(d, BX0 + 4, BY0 - 14, "Conveyor  →", 12, FAINT, "lm", "m")

def plant(d, t, st):
    show = st.get("show", ALL); new = st.get("new", {}); lit = st.get("lit", {})
    tech = st.get("techdim", False)
    def pulse(k):
        return 0.0 if k not in new else clamp(1 - (t - new[k]) / 1.6) * (0.6 + 0.4 * math.sin((t - new[k]) * 9))
    # wires first (they run under the belt)
    if "wires" in show:
        wp = st.get("wire_p", 1.0)
        for k, pts in WIRES.items():
            if k in ("plc_srv",) : continue
            if k == "sens2" and not st.get("sens2"): continue
            need = {"trig1": "sensor", "cam1": "cam1", "cam2": "cam2", "enc": "encoder", "sw_srv": "server",
                    "srv_plc": "plc", "plc_flip": "flip", "plc_robot": "robot", "trig2": "flip", "power": "ups", "sens2": "plc"}
            if need.get(k) not in show: continue
            col = lit.get(k, (50, 60, 82))
            if k == "sens2": dashed(d, psub(pts, wp), col, 2)
            else: line(d, psub(pts, wp), col, 2.5 if k in lit else 2)
    if "belt" in show: belt_draw(d, st.get("belt_off", t * 18))
    # Technocraft equipment
    tcol = FAINT if tech else None
    if "flip" in show:
        c = tcol or GOLD
        rect(d, FLIPX - 50, 206, FLIPX + 50, 340, fill=mix(BG, c, .08), outline=c, w=2.5, r=8)
        text(d, FLIPX, 190, "Flip mechanism", 14, c, "mm", "b")
        if st.get("flip_busy"):
            glow_box(d, FLIPX - 50, 206, FLIPX + 50, 340, GOLD, st["flip_busy"], 8)
    if "flap" in show:
        c = tcol or RED
        rect(d, 376, 322, 428, 370, fill=mix(BG, c, .08), outline=mix(BG, c, .7), w=1.5, r=5)
        text(d, 402, 382, "flap → reject", 10, c, "mm", "s")
        a = math.radians(-st.get("flap", 0) * 75)
        line(d, [(380, 228), (380 + 46 * math.cos(a), 228 - 46 * math.sin(a))], c, 5)
        ell(d, 380, 228, 5, fill=c)
    if "pins" in show:
        c = tcol or BLUE
        rect(d, 1035, 205, 1255, 345, fill=(30, 36, 52), outline=mix(BG, c, .6), w=2, r=10)
        text(d, 1145, 190, "Pins (placing station)", 14, c, "mm", "b")
        for i, (x, y) in enumerate(PINS):
            ell(d, x, y, 5, fill=(150, 160, 180))
            if i < st.get("filled", 3): ring(d, x, y, 18, 0, "rollover", bg=(30, 36, 52))
    if "plc" in show:
        c = tcol or ORANGE
        rect(d, 600, 440, 780, 520, fill=mix(BG, c, .1), outline=c, w=2.5, r=10)
        text(d, 690, 466, "Line controller", 15, c, "mm", "b")
        text(d, 690, 488, "PLC / robot controller", 11, DIM, "mm", "m")
        text(d, 690, 506, "Technocraft", 10, FAINT, "mm", "m")
        p = pulse("plc")
        if p: glow_box(d, 600, 440, 780, 520, ORANGE, p)
    # V7AI-specified hardware
    for key, cx, lbl in (("cam1", CAM1, "Camera 1"), ("cam2", CAM2, "Camera 2")):
        if key not in show: continue
        fx0, fx1 = cx - 70, cx + 70
        fl = st.get("flash1" if key == "cam1" else "flash2", 0)
        rect(d, fx0, 205, fx1, 340, fill=mix(BELT, WHITE, fl * .55) if fl else None, outline=(110, 120, 145), w=1.5, r=10)
        dashed(d, [(fx0 - 5, 200), (fx1 + 5, 200), (fx1 + 5, 345), (fx0 - 5, 345), (fx0 - 5, 200)], (90, 98, 120), 1.5, 5, 4)
        camera_icon(d, cx, 148, BLUE, lbl, "12 MP")
        line(d, [(cx, 174), (cx, 205)], (90, 100, 125), 1.5)
        p = pulse(key)
        if p: glow_box(d, fx0 - 5, 120, fx1 + 5, 345, BLUE, p)
    if "lights1" in show:
        on = st.get("flash1", 0)
        for i in range(24):
            a = i * 15
            ell(d, CAM1 + math.cos(math.radians(a)) * 58, BYC - math.sin(math.radians(a)) * 58, 2.6,
                fill=mix((120, 100, 50), WHITE, on) if on else (150, 120, 50))
        p = pulse("lights1")
        if p: ell(d, CAM1, BYC, 66, outline=mix(BG, GOLD, p), w=3)
    for key, cx, fl in (("lights1", CAM1, "flash1"), ("lights2", CAM2, "flash2")):
        if key in show:
            on = st.get(fl, 0)
            c = mix((150, 160, 185), WHITE, on)
            for (x0, x1) in ((cx - 64, cx - 58), (cx + 58, cx + 64)):
                rect(d, x0, 214, x1, 330, fill=c, r=2)
            if key == "lights2":
                p = pulse("lights2")
                if p: glow_box(d, cx - 68, 210, cx + 68, 334, WHITE, p)
    if "sensor" in show:
        c = RED if st.get("beam") else (230, 90, 90)
        rect(d, SENS1 - 10, 212, SENS1 + 10, 230, fill=(60, 34, 40), outline=RED, w=2, r=3)
        rect(d, SENS1 - 8, 314, SENS1 + 8, 324, fill=(60, 34, 40), outline=RED, w=1.5, r=2)
        if st.get("beam"):
            line(d, [(SENS1, 230), (SENS1, 314)], (255, 120, 120), 3)
            ell(d, SENS1, 222, 14, outline=mix(BG, RED, .9), w=2)
        else: dashed(d, [(SENS1, 230), (SENS1, 314)], mix(BELT, RED, .7), 1.5, 4, 4)
        text(d, SENS1, 196, "Presence sensor", 13, RED, "mm", "b")
        p = pulse("sensor")
        if p: glow_box(d, SENS1 - 16, 185, SENS1 + 16, 330, RED, p, 6)
    if st.get("sens2"):
        rect(d, SENS2 - 8, 214, SENS2 + 8, 228, outline=RED, w=1.5, r=3)
        dashed(d, [(SENS2, 228), (SENS2, 314)], mix(BELT, RED, .45), 1.2, 3, 4)
    if "encoder" in show:
        ell(d, 40, 336, 12, fill=(40, 46, 62), outline=CYAN, w=2)
        a = math.radians(st.get("belt_off", t * 18) * 6)
        line(d, [(40, 336), (40 + 9 * math.cos(a), 336 - 9 * math.sin(a))], CYAN, 2)
        text(d, 58, 352, "Encoder", 12, CYAN, "lm", "b")
        p = pulse("encoder")
        if p: ell(d, 40, 336, 20, outline=mix(BG, CYAN, p), w=3)
    if "switch" in show:
        rect(d, 90, 470, 290, 540, fill=(26, 34, 48), outline=CYAN, w=2.5, r=8)
        text(d, 190, 492, "Industrial Ethernet switch", 13, CYAN, "mm", "b")
        for i in range(8):
            on = (int(t * 7 + i * 3) % 5) != 0
            rect(d, 106 + i * 22, 512, 122 + i * 22, 526, fill=(16, 20, 28), outline=(70, 80, 100), w=1, r=2)
            ell(d, 114 + i * 22, 509, 2, fill=GREEN if on else (40, 70, 50))
        p = pulse("switch")
        if p: glow_box(d, 90, 470, 290, 540, CYAN, p)
    if "server" in show:
        rect(d, 340, 420, 560, 690, fill=(22, 30, 42), outline=GREEN, w=2.5, r=10)
        text(d, 450, 440, "Server", 16, GREEN, "mm", "b")
        text(d, 450, 459, "cooled cabinet · V7 AI Solutions software", 10.5, DIM, "mm", "m")
        rows = [("Camera network card", CYAN, 474, 500), ("CPU · signals + control", BLUE, 508, 540),
                ("GPU · runs the ML models", PURP, 548, 580), ("Storage · logs + images", DIM, 588, 614)]
        hl = st.get("srv_hl", {})
        for nm, c, y0, y1 in rows:
            key = nm.split(" ")[0]
            hh = hl.get(key, 0)
            rect(d, 356, y0, 544, y1, fill=mix((30, 38, 54), c, .12 + .3 * hh), outline=mix(LINE, c, .4 + .6 * hh), w=1.5, r=5)
            text(d, 368, (y0 + y1) / 2, nm, 12, mix(TXT, c, .3), "lm", "s")
        for i in range(3):
            cx_ = 395 + i * 55
            ell(d, cx_, 652, 16, outline=(70, 82, 104), w=1.5)
            a = t * 12 + i
            for k in range(3):
                b = a + k * 2.09
                line(d, [(cx_, 652), (cx_ + 13 * math.cos(b), 652 + 13 * math.sin(b))], (90, 104, 128), 2)
        p = pulse("server")
        if p: glow_box(d, 340, 420, 560, 690, GREEN, p)
    if "ups" in show:
        rect(d, 600, 600, 720, 690, fill=(30, 34, 46), outline=YEL, w=2, r=8)
        text(d, 660, 624, "UPS", 15, YEL, "mm", "b")
        rect(d, 630, 646, 684, 668, outline=YEL, w=1.5, r=3); rect(d, 684, 652, 689, 662, fill=YEL)
        lvl = st.get("ups_lvl", 1.0)
        rect(d, 633, 649, 633 + 48 * lvl, 665, fill=mix(RED, GREEN, lvl), r=2)
        p = pulse("ups")
        if p: glow_box(d, 600, 600, 720, 690, YEL, p)
    if "robot" in show:
        c = tcol or BLUE
        bx, by = ROBOT
        ex, ey = st.get("arm", (930, 250))
        arm2(d, bx, by, ex, ey, c)
        text(d, bx + 34, by + 4, "Robot", 14, c, "lm", "b")
        text(d, bx + 34, by + 21, "+ gripper", 11, DIM, "lm", "m")
    if not tech: return
    # "Technocraft line" tag in setup scene
    text(d, 690, 534, "", 10, FAINT)

def arm2(d, bx, by, ex, ey, col, l1=170, l2=170):
    dx, dy = ex - bx, ey - by
    dist = clamp(math.hypot(dx, dy), 20, l1 + l2 - 1)
    a = math.atan2(dy, dx)
    b = math.acos(clamp((l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist), -1, 1))
    jx, jy = bx + l1 * math.cos(a + b), by + l1 * math.sin(a + b)
    tx, ty = bx + dist * math.cos(a), by + dist * math.sin(a)
    ell(d, bx, by, 24, fill=(40, 50, 72), outline=col, w=2.5)
    line(d, [(bx, by), (jx, jy)], col, 11); line(d, [(jx, jy), (tx, ty)], mix(col, TXT, .2), 9)
    ell(d, jx, jy, 9, fill=(40, 50, 72), outline=col, w=2.5)
    ell(d, tx, ty, 8, outline=GREEN, w=2.5)

# ------------------------------------------------------------------ backend log
# (scene, time-in-scene as f(S), clock, text, colour)
LOG = [
    (3, lambda S: -9, "01.204", "#1041 rotate 22.1° sent → robot", DIM),
    (3, lambda S: -9, "03.180", "#1041 placed on pins", DIM),
    (3, lambda S: -9, "05.000", "heartbeat ok (server ↔ PLC)", FAINT),
    (3, lambda S: S[2] + 0.9, "07.112", "#1042 sensor triggered", RED),
    (3, lambda S: S[3] + 0.6, "07.112", "#1042 ID assigned · count 1042", TXT),
    (3, lambda S: S[4] + 0.8, "07.113", "#1042 waiting 1,850 enc. pulses", CYAN),
    (4, lambda S: S[1] + 0.2, "08.326", "#1042 cam1 strobe 0.2 ms · shot", BLUE),
    (4, lambda S: S[3] + 3.2, "08.431", "#1042 cam1 image in · 12 MP", BLUE),
    (5, lambda S: S[1] + 2.5, "08.702", "#1042 one complete ring  ✓", GREEN),
    (5, lambda S: S[2] + 1.8, "08.744", "#1042 type 3 · centred (41.3, 12.7)", TXT),
    (5, lambda S: S[3] + 3.0, "08.851", "#1042 BURR up · confidence score ok", GOLD),
    (5, lambda S: S[4] + 0.4, "08.853", "#1042 side check done (< 1 s)", GREEN),
    (6, lambda S: S[0] + 2.4, "08.860", "#1042 SIGNAL 1 → PLC: FLIP = YES", ORANGE),
    (6, lambda S: S[0] + 3.4, "08.871", "PLC ack · signal 1", FAINT),
    (6, lambda S: S[2] + 6.5, "10.410", "#1042 flip done (PLC)", GOLD),
    (7, lambda S: S[0] + 2.2, "10.452", "#1042 flip trigger + delay → cam2", ORANGE),
    (7, lambda S: S[1] + 3.0, "10.453", "#1042 cam2 diffuse strobe · shot", BLUE),
    (7, lambda S: S[2] + 2.0, "10.559", "#1042 cam2 image in · 12 MP", BLUE),
    (8, lambda S: S[1] + 2.0, "10.802", "#1042 3 notches found", GREEN),
    (8, lambda S: S[1] + 6.5, "10.871", "#1042 rotate 37.4° CW (0–89°)", GREEN),
    (8, lambda S: S[3] + 2.5, "10.872", "#1042 matched to sensor ID  ✓", GREEN),
    (9, lambda S: S[0] + 2.0, "10.880", "#1042 SIGNAL 2 → robot: 37.4°", ORANGE),
    (9, lambda S: S[1] + 4.6, "12.950", "#1042 placed on pins  ✓", GREEN),
    (9, lambda S: S[2] + 3.0, "13.112", "#1043 sensor triggered", RED),
    (9, lambda S: S[2] + 3.1, "13.112", "#1043 ID assigned · count 1043", TXT),
]

def draw_log(d, si, t, S_all, box=LOGBOX, title="V7 AI Solutions · live log", extra=()):
    x0, y0, x1, y1 = box
    rect(d, x0, y0, x1, y1, fill=(10, 14, 22), outline=(52, 64, 88), w=2, r=10)
    for i, c in enumerate((RED, YEL, GREEN)): ell(d, x0 + 16 + i * 14, y0 + 16, 4, fill=mix(BG, c, .7))
    text(d, x0 + 62, y0 + 16, title, 12, DIM, "lm", "s")
    line(d, [(x0, y0 + 32), (x1, y0 + 32)], (40, 50, 70), 1)
    rows = []
    for sc, f, clk, s, c in LOG:
        tt = f(S_all[sc])
        if sc < si or (sc == si and t >= tt): rows.append((clk, s, c, (t - tt) if sc == si else 99))
    for tt, clk, s, c in extra:
        if t >= tt: rows.append((clk, s, c, t - tt))
    n = int((y1 - y0 - 44) // 19)
    for k, (clk, s, c, age) in enumerate(rows[-n:]):
        y = y0 + 46 + k * 19
        if age < 0.6: rect(d, x0 + 6, y - 9, x1 - 6, y + 9, fill=mix((10, 14, 22), c, .25 * (1 - age / .6)), r=3)
        text(d, x0 + 12, y, clk if ":" in clk else "10:42:" + clk, 11, FAINT, "lm", "mono")
        text(d, x0 + 110, y, s, 11.5, c, "lm", "mono")
    if int(t * 2) % 2 == 0:
        y = y0 + 46 + min(len(rows), n) * 19
        if y < y1 - 8: rect(d, x0 + 12, y - 6, x0 + 19, y + 7, fill=DIM)

# ------------------------------------------------------------------ header / step tracker
STEPS = ["Ring travels on the belt", "Presence sensor detects it", "Wait until it's centred",
         "Camera 1 takes the picture", "Image sent to the server", "Software checks the image",
         "Decide and send signal 1", "Flip (if needed)", "Ring reaches Camera 2", "Camera 2 takes the picture",
         "Image sent to the server", "Software measures the angle", "Send signal 2", "Robot places the ring"]

def header(d, title, step=None, sub=None):
    rect(d, 0, 0, W, 78, fill=(17, 22, 34))
    line(d, [(0, 78), (W, 78)], (38, 46, 66), 1)
    sec = title.split(" · ")[0] if " · " in title else None
    x = 34
    if sec:
        col = {"A": CYAN, "B": GREEN, "C": PURP, "D": PURP}[sec]
        x = chip(d, 34, 39, {"A": "A · ONE-TIME SETUP", "B": "B · EVERY RING", "C": "C · ALWAYS RUNNING", "D": "D · THE GPU"}[sec], col, 12, "b") + 14
        title = title.split(" · ", 1)[1]
    text(d, x, 39, title, 25, TXT, "lm", "b")
    if step:
        for i in range(14):
            cx = 860 + i * 28
            c = GREEN if i + 1 == step else mix(BG, GREEN, .55) if i + 1 < step else (52, 60, 80)
            ell(d, cx, 28, 9 if i + 1 == step else 7, fill=c)
            if i + 1 == step: text(d, cx, 28, str(step), 10, BG, "mm", "b")
        text(d, 1240, 56, f"Step {step} of 14 · {STEPS[step - 1]}", 13, GREEN, "rm", "s")
    elif sub:
        text(d, 1246, 39, sub, 13, DIM, "rm", "m")

# ------------------------------------------------------------------ scenes
def legend(d, x, y):
    ring(d, x, y, 13, 30, "burr", bg=BG); text(d, x + 22, y, "burr side up", 13, GOLD, "lm", "s")
    ring(d, x + 150, y, 13, 30, "rollover", bg=BG); text(d, x + 172, y, "rollover side up", 13, BLUE, "lm", "s")

def s_intro(d, t, D, S, si, SA):
    belt_y = 560
    rect(d, 0, belt_y - 50, W, belt_y + 50, fill=BELT)
    for i in range(45):
        x = (i * 30 + t * 40) % 1350 - 30
        line(d, [(x, belt_y - 46), (x, belt_y + 46)], BELT_L, 2)
    rnd = random.Random(2)
    for i in range(7):
        x = (i * 200 + t * 40) % 1400 - 70
        ring(d, x, belt_y + rnd.uniform(-14, 14), 34, rnd.uniform(0, 360), rnd.choice(["burr", "rollover"]), rnd.randint(1, 5))
    a = ev(t, 0.3, 1.0)
    text(d, 640, 150, "Computer Vision for Ring Side Identification", 44 * (0.9 + .1 * a), mix(BG, TXT, a), "mm", "b")
    text(d, 640, 205, "and Angular Orientation", 44 * (0.9 + .1 * a), mix(BG, TXT, a), "mm", "b")
    text(d, 640, 262, "How the setup works, and the journey of a ring through the line", 21, mix(BG, DIM, ev(t, 1.0, 1)), "mm", "r")
    p = ev(t, S[1], .8)
    if p:
        x = chip(d, 420, 330, "V7 AI Solutions · vision software", GREEN, 15, "s")
        chip(d, x + 24, 330, "Technocraft · line & robot", ORANGE, 15, "s")
    p = ev(t, S[2], .8)
    if p:
        rect(d, 300, 362, 980, 398, fill=mix(BG, YEL, .1 * p), outline=mix(BG, YEL, p), w=1.5, r=8)
        text(d, 640, 380, "A complete theoretical estimation, visualised to better define the scope", 15, mix(BG, YEL, p), "mm", "s")
    p = ev(t, S[3], .8)
    if p:
        legend(d, 520, 430)
        text(d, 640, 462, "Every ring must leave rollover side up, at the right angle, on the pins", 15, mix(BG, TXT, p), "mm", "m")

def s_hw(d, t, D, S, si, SA):
    header(d, "A · Setup: the hardware", sub="Specified by V7 AI Solutions · procured by Technocraft")
    show = {"belt", "flip", "pins", "plc", "robot", "flap"}
    new = {}
    seq = [(S[1] + 0.5, ["cam1", "cam2"]), (S[2] + 0.3, ["lights1"]), (S[2] + 3.3, ["lights2"]),
           (S[3] + 0.6, ["sensor"]), (S[3] + 3.5, ["encoder"]), (S[4] + 1.0, ["switch"]), (S[4] + 3.4, ["server"]),
           (S[4] + 5.6, ["ups"]), (S[4] + 1.0, ["wires"])]
    for tt, ks in seq:
        if t >= tt:
            for k in ks: show.add(k); new[k] = tt
    st = {"show": show, "new": new, "belt_off": t * 22, "techdim": True, "wire_p": ev(t, S[4] + 1.0, 6.0)}
    plant(d, t, st)
    # callouts
    if t >= S[1] + 1.5:
        p = ev(t, S[1] + 1.5)
        text(d, 480, 128, "vibration-isolated frames", 12.5, mix(BG, BLUE, p), "mm", "s")
        text(d, 480, 146, "light-tight shrouds", 12.5, mix(BG, BLUE, p), "mm", "s")
    if t >= S[2] + 1.0:
        p = ev(t, S[2] + 1.0)
        chip(d, 300, 400, "low-angle ring light + diffuse (optional)", GOLD, 11, "s", anchor="m")
    if t >= S[2] + 3.6:
        chip(d, 660, 400, "diffuse light", (220, 225, 240), 11, "s", anchor="m")
    rect(d, 900, 400, 1265, 700, fill=PANEL, outline=LINE, w=2, r=12)
    text(d, 920, 420, "Hardware list", 16, TXT, "la", "b")
    items = [(S[1] + 0.5, "2 × 12 MP industrial cameras + lenses", BLUE), (S[1] + 1.5, "Isolated frames + light-tight shrouds", BLUE),
             (S[2] + 0.3, "Ring light, diffuse (cam 1: optional), strobe", GOLD), (S[3] + 0.6, "Presence sensor", RED),
             (S[3] + 3.5, "Belt encoder (if the line has none)", CYAN), (S[4] + 1.0, "Industrial Ethernet switch + cabling", CYAN),
             (S[4] + 3.4, "Server (CPU + GPU) in a cooled cabinet", GREEN), (S[4] + 5.6, "UPS", YEL),
             (S[5] + 0.5, "ML training workstation + GPU card", PURP)]
    for i, (tt, s, c) in enumerate(items):
        if t >= tt:
            y = 452 + i * 24
            ell(d, 926, y, 4, fill=c); text(d, 940, y, s, 12.5, mix(BG, TXT, ev(t, tt, .4)), "lm", "m")
    if t >= S[5]:
        p = ev(t, S[5], .6)
        card(d, 30, 560, 330, 700, "ML models: trained beforehand", col=mix(LINE, PURP, p), tcol=PURP, sz=14)
        text(d, 46, 606, "ring images from Technocraft", 12, TXT, "lm", "m")
        arrow(d, 46, 628, 70, 628, PURP, 2); text(d, 78, 628, "ML workstation + GPU card", 12, TXT, "lm", "s")
        arrow(d, 46, 652, 70, 652, PURP, 2); text(d, 78, 652, "trained models", 12, TXT, "lm", "m")
        arrow(d, 46, 676, 70, 676, PURP, 2); text(d, 78, 676, "loaded onto the server", 12, GREEN, "lm", "s")
    if t >= S[6]:
        p = ev(t, S[6], .6)
        rect(d, 912, 665, 1253, 690, fill=mix(PANEL, GREEN, .12 * p), outline=mix(PANEL, GREEN, p), w=1.5, r=6)
        text(d, 1082, 677, "Specified by V7 AI Solutions · procured by Technocraft", 10.5, mix(PANEL, GREEN, p), "mm", "b")
    text(d, 690, 548, "Technocraft line equipment shown in grey", 10.5, FAINT, "mm", "m")

def s_sw(d, t, D, S, si, SA):
    header(d, "A · Setup: teaching the system", sub="Done once, before production")
    boxes = [(30, 100, 630, 395), (650, 100, 1250, 395), (30, 410, 630, 705), (650, 410, 1250, 705)]
    titles = [("1  Set the scale", CYAN), ("2  Teach the 5 ring types", GOLD), ("3  Trigger timing + rotation direction", BLUE),
              ("4  Agree the signal link", ORANGE)]
    for i, ((x0, y0, x1, y1), (tt, c)) in enumerate(zip(boxes, titles)):
        st = S[i + 1]
        if t < st - 0.2:
            rect(d, x0, y0, x1, y1, outline=(34, 42, 60), w=1.5, r=12); continue
        p = ev(t, st - 0.2, .6)
        card(d, x0, y0, x1, y1, tt, col=mix(LINE, c, .6 * p), tcol=c)
        lt = t - st
        if i == 0:
            cx, cy = 200, 260
            ring(d, cx, cy, 80, 90, "rollover", typ=1, bg=PANEL)
            q = ev(lt, 1.0, 1.2)
            line(d, [(cx - 80, cy + 104), (cx - 80 + 160 * q, cy + 104)], CYAN, 2)
            line(d, [(cx - 80, cy + 94), (cx - 80, cy + 114)], CYAN, 2)
            if q >= 1: line(d, [(cx + 80, cy + 94), (cx + 80, cy + 114)], CYAN, 2)
            if lt > 2.2:
                text(d, cx, cy + 126, "known size: Ø 100.00 mm", 13, CYAN, "mm", "s")
                text(d, 330, 210, "measured in the image", 13, DIM, "la", "m")
                text(d, 330, 236, "2,000 px across", 24, TXT, "la", "b")
            if lt > 3.4:
                arrow(d, 330, 280, 360, 280, DIM, 2)
                text(d, 330, 306, "1 px = 0.050 mm", 26, CYAN, "la", "b")
                text(d, 330, 338, "used for every position + size", 12.5, DIM, "la", "m")
        if i == 1:
            for k in range(5):
                cx = 715 + k * 113; cy = 225
                on = lt > 0.8 + k * 0.5
                if not on: continue
                ring(d, cx, cy, 40, 0, "rollover", typ=k + 1, bg=PANEL)
                text(d, cx, 284, f"Type {k + 1}", 14, TXT, "mm", "b")
                text(d, cx, 304, f"{len(TYPES[k + 1])} notch" + ("es" if len(TYPES[k + 1]) > 1 else ""), 11.5, DIM, "mm", "m")
                if lt > 4.0:
                    text(d, cx, 324, f"target {[0, 15, 30, 45, 0][k]}°", 11.5, GOLD, "mm", "s")
                    dashed(d, [(cx, cy - 52), (cx, cy - 44)], GOLD, 2, 3, 2)
            if lt > 5.5:
                text(d, 950, 368, "outline · notch layout · target angle · image settings tuned", 12, DIM, "mm", "m")
        if i == 2:
            y = 490
            q = ev(lt, 0.5, 1)
            line(d, [(60, y + 40), (590, y + 40)], (60, 70, 92), 2)
            rect(d, 70, y + 10, 82, y + 40, fill=RED); text(d, 76, y - 2, "sensor", 11, RED, "mm", "s")
            dl = ev(lt, 1.5, 2.5)
            rect(d, 84, y + 22, 84 + 330 * dl, y + 34, fill=mix(BG, CYAN, .7), r=3)
            if dl > .5: text(d, 250, y + 6, "delay: 1,850 encoder pulses (≈ 0.6–2.5 s)", 12, CYAN, "mm", "s")
            if dl >= 1:
                rect(d, 416, y + 4, 432, y + 40, fill=BLUE); text(d, 424, y - 8, "shutter", 11, BLUE, "mm", "s")
            if lt > 5.2:
                cx, cy = 200, 630
                a0 = (lt * 60) % 360
                arc(d, cx, cy, 34, 200, 520 - 40, GREEN, 4)
                arrow(d, cx + 34 * math.cos(math.radians(160)), cy - 34 * math.sin(math.radians(160)),
                      cx + 34 * math.cos(math.radians(140)), cy - 34 * math.sin(math.radians(140)), GREEN, 4, 12)
                text(d, 260, 620, "Rotation direction", 15, TXT, "lm", "b")
                chip(d, 262, 650, "Clockwise ✓", GREEN, 12, "s"); chip(d, 380, 650, "Anticlockwise", FAINT, 12, "m")
                text(d, 262, 680, "agreed with the Technocraft team", 11.5, DIM, "lm", "m")
        if i == 3:
            rect(d, 690, 470, 840, 530, fill=mix(BG, GREEN, .12), outline=GREEN, w=2, r=8)
            text(d, 765, 500, "Server", 15, GREEN, "mm", "b")
            rect(d, 1060, 470, 1210, 530, fill=mix(BG, ORANGE, .12), outline=ORANGE, w=2, r=8)
            text(d, 1135, 500, "Line controller", 15, ORANGE, "mm", "b")
            line(d, [(840, 500), (1060, 500)], (70, 80, 104), 3)
            for k in range(2):
                ph = (lt * 0.6 + k * .5) % 1
                x = lerp(840, 1060, ph) if k == 0 else lerp(1060, 840, ph)
                ell(d, x, 500, 5, fill=GREEN if k == 0 else ORANGE)
            text(d, 950, 482, "agreed industrial protocol", 11, DIM, "mm", "m")
            rows = [("Signal 1", "flip: yes / no", GREEN), ("Signal 2", "rotation angle 0–89°", GREEN),
                    ("Heartbeat", "both sides, continuously", CYAN), ("Link drops", "→ safe stop", RED)]
            for k, (a, b, c) in enumerate(rows):
                if lt > 1.0 + k * 1.2:
                    y = 562 + k * 32
                    text(d, 700, y, a, 13, c, "lm", "b"); text(d, 810, y, b, 13, TXT, "lm", "m")

def ring_on_belt(st, x, y=262, ang=-37.4, face="burr", sx=1.0, lit=0.0, idlabel=None):
    st.setdefault("rings", []).append(dict(x=x, y=y, ang=ang, face=face, sx=sx, lit=lit, id=idlabel))

def draw_rings(d, st, t):
    for r in st.get("rings", []):
        if r["x"] < BX0 - 30: continue
        ring(d, r["x"], r["y"], 26, r["ang"], r["face"], sx=r["sx"], lit=r["lit"])
        if r["id"]:
            chip(d, r["x"], r["y"] + 46, r["id"], TXT, 10.5, "monob", fill=(30, 36, 52), anchor="m")

def full_plant(d, t, st):
    plant(d, t, st)
    draw_rings(d, st, t)

def s_arrive(d, t, D, S, si, SA):
    # ring enters, breaks beam, gets ID, travels to camera 1 centre
    x_enter = lerp(-40, 95, ev(t, S[1] - 0.5, 3.0))
    x = x_enter
    if t > S[2]: x = lerp(95, SENS1 - 22, ev(t, S[2], 1.2))
    if t > S[4] + 1.0: x = lerp(SENS1 - 22, CAM1, ev(t, S[4] + 1.0, D - S[4] - 2.5))
    beam = SENS1 - 30 < x + 26 and x - 26 < SENS1 + 30 and t > S[2] + 0.9
    st = {"belt_off": x, "beam": beam, "lit": {}, "new": {}}
    pk = []
    if t > S[2] + 1.0:
        p = seg(t, S[2] + 1.0, S[2] + 2.4)
        if p < 1: st["lit"]["trig1"] = YEL
        pk.append(("trig1", p, "PULSE", YEL))
    if t > S[3] + 0.3: st["new"]["server"] = S[3] + 0.3
    if t > S[4] + 0.8:
        st["lit"]["enc"] = CYAN; pk.append(("enc", (t - S[4] - 0.8) % 1.2 / 1.2, "ENC", CYAN))
    ring_on_belt(st, x, idlabel="#1042" if t > S[3] + 0.6 else None)
    if t < S[1] + 2.5 and t > S[1] - 0.5:
        st["rings"][-1]["y"] = 262 - 14 * (1 - ev(t, S[1] - 0.5, 1.0))
    header(d, "B · A ring arrives", step=1 if t < S[2] else 2 if t < S[4] else 3)
    full_plant(d, t, st)
    for k, p, lab, c in pk: packet(d, WIRES[k], p, lab, c)
    if S[1] + 0.5 < t < S[2] + 0.5:
        text(d, 110, 380, "random position · either side up", 13, GOLD, "mm", "s")
    if t > S[3] + 0.6:
        p = ev(t, S[3] + 0.6, .5)
        rect(d, 30, 560, 300, 690, fill=PANEL, outline=mix(PANEL, RED, p), w=2, r=10)
        text(d, 46, 580, "Sensor event", 13, RED, "lm", "b")
        text(d, 46, 608, "Ring ID", 12, DIM, "lm", "m"); text(d, 284, 608, "#1042", 17, TXT, "rm", "monob")
        text(d, 46, 636, "Count today", 12, DIM, "lm", "m")
        text(d, 284, 636, f"{1041 + (1 if t > S[3] + 1.4 else 0):,}", 17, TXT, "rm", "monob")
        if t > S[4] + 0.8:
            pulses = int(1850 * ev(t, S[4] + 1.0, D - S[4] - 2.5))
            text(d, 46, 664, "Encoder pulses", 12, DIM, "lm", "m")
            text(d, 284, 664, f"{pulses:,} / 1,850", 15, CYAN, "rm", "monob")
    draw_log(d, si, t, SA)

def cam_zoom(t, a, b, D, cx, s=2.3):
    zin = ev(t, a, 1.6); zout = ev(t, b, 1.6)
    z = zin * (1 - zout)
    view(lerp(1, s, z), lerp(640, cx, z), lerp(400, BYC, z), lerp(640, 420, z), lerp(400, 300, z))
    return z

def s_cam1(d, t, D, S, si, SA):
    z = cam_zoom(t, 0.1, S[3] + 0.3, D, CAM1)
    flash = 0.0
    for ft in (S[1] + 0.6, S[1] + 3.6):
        if ft <= t < ft + 0.45: flash = 1 - (t - ft) / 0.45
    st = {"belt_off": CAM1 + t * 0.6, "flash1": flash, "lit": {}, "srv_hl": {}}
    ring_on_belt(st, CAM1 + t * 0.6, lit=flash, idlabel="#1042")
    full_plant(d, t, st)
    if S[2] - 0.2 < t < S[3] + 0.5:
        q = ev(t, S[2], .6)
        for side in (-1, 1):
            for k in range(5):
                y = BYC - 22 + k * 11
                line(d, [(CAM1 + side * 58, y), (CAM1 + side * lerp(58, 30, q), y + side * 2)], mix(BELT, YEL, .8 * q), 1.4)
        rr = 26
        for i in range(0, 360, 12):
            a = math.radians(i + t * 40)
            ell(d, CAM1 + t * 0.6 + math.cos(a) * rr * 1.04, 262 - math.sin(a) * rr * 1.04, 1.4, fill=mix(GOLD, WHITE, .6 * q))
    if t > S[3] + 0.6:
        p = seg(t, S[3] + 1.6, S[3] + 3.2)
        st["lit"]["cam1"] = BLUE
        packet(d, WIRES["cam1"], p, "IMAGE 12 MP", BLUE)
        if p >= 1:
            p2 = seg(t, S[3] + 3.2, S[3] + 3.9)
            packet(d, WIRES["sw_srv"], p2, "IMG", BLUE)
    with screen():
        header(d, "B · Camera 1 takes the picture", step=4 if t < S[3] else 5)
        if z > 0.3 and t > S[1]:
            p = ev(t, S[1], .5)
            card(d, 40, 560, 400, 690, "Strobe flash", col=mix(LINE, YEL, p), tcol=YEL)
            text(d, 56, 612, "≈ 0.2 ms", 30, TXT, "lm", "b")
            text(d, 56, 646, "ring light (+ diffuse, optional)", 12.5, DIM, "lm", "m")
            text(d, 56, 668, "freezes the ring on a moving belt", 12.5, DIM, "lm", "m")
        if z > 0.3 and t > S[2]:
            p = ev(t, S[2], .5)
            card(d, 420, 560, 860, 690, "Why a low-angle light?", col=mix(LINE, GOLD, p), tcol=GOLD)
            text(d, 436, 612, "light skims across the surface", 14, TXT, "lm", "m")
            text(d, 436, 638, "→ the raised burr edge lights up", 14, GOLD, "lm", "s")
            text(d, 436, 664, "→ the rounded rollover edge stays dark", 14, BLUE, "lm", "s")
        if t > S[3] + 2.0:
            text(d, 90, 560, "≈ 0.1 s → server's camera network card", 12, BLUE, "lm", "s")
        draw_log(d, si, t, SA)
    view()

def img_frame(d, x0, y0, x1, y1, label, col):
    rect(d, x0, y0, x1, y1, fill=(36, 38, 44), outline=col, w=2, r=6)
    for i in range(int((x1 - x0) / 26)):
        line(d, [(x0 + 10 + i * 26, y0 + 6), (x0 + 10 + i * 26, y1 - 6)], (42, 44, 50), 2)
    text(d, x0 + 12, y0 - 14, label, 13, col, "lm", "s")
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        line(d, [(cx + sx * 4, cy + sy * 22), (cx + sx * 4, cy + sy * 4), (cx + sx * 22, cy + sy * 4)], col, 3)

def s_check(d, t, D, S, si, SA):
    header(d, "B · The server checks the image", step=6)
    x0, y0, x1, y1 = 30, 112, 500, 582
    img_frame(d, x0, y0, x1, y1, "Camera 1 image · #1042 · 12 MP", BLUE)
    cx, cy, r = 280, 340, 150
    ring(d, cx, cy, r, -37.4, "burr", bg=(36, 38, 44), photo=True)
    # stage 1: count + completeness
    if t > S[1]:
        q = ev(t, S[1] + 0.3, 2.0)
        pts = ring_pts(cx, cy, r + 4, -37.4, 3)
        line(d, pts[:max(2, int(len(pts) * q))], GREEN, 3)
        if q >= 1:
            line(d, [pts[-1], pts[0]], GREEN, 3)
            dashed(d, [(cx - r - 14, cy - r - 14), (cx + r + 14, cy - r - 14), (cx + r + 14, cy + r + 14), (cx - r - 14, cy + r + 14), (cx - r - 14, cy - r - 14)], GREEN, 1.5)
    if t > S[2]:
        q = ev(t, S[2], .6)
        line(d, [(cx - 30 * q, cy), (cx + 30 * q, cy)], CYAN, 2); line(d, [(cx, cy - 30 * q), (cx, cy + 30 * q)], CYAN, 2)
        ell(d, cx, cy, 5, fill=CYAN)
        text(d, cx + 12, cy + 18, "(41.3, 12.7) mm", 12, CYAN, "la", "monob")
    if t > S[3] + 1.0:
        q = ev(t, S[3] + 1.0, 1.5)
        for i in range(0, 360, 8):
            a = math.radians(i - 37.4)
            ell(d, cx + math.cos(a) * (r + 6), cy - math.sin(a) * (r + 6), 2.2 * q, fill=YEL)
    # results card
    rx0 = 520
    card(d, rx0, 112, 885, 700, "Checks", col=LINE)
    rows = [
        (S[1] + 0.2, "Exactly one ring in view?", "1 ring", GREEN),
        (S[1] + 2.2, "Complete, not cut at the edge?", "yes", GREEN),
        (S[2] + 0.3, "Where is it?", "x 41.3 · y 12.7 mm", CYAN),
        (S[2] + 1.6, "Which of the 5 types?", "Type 3", GOLD),
    ]
    for k, (tt, q_, a_, c) in enumerate(rows):
        if t < tt: continue
        y = 160 + k * 50
        text(d, rx0 + 18, y, q_, 13.5, DIM, "lm", "m")
        text(d, rx0 + 18, y + 20, a_, 15, c, "lm", "b")
        tick(d, 860, y + 8, 16)
    if t > S[2] + 1.6:
        for k in range(5):
            x = rx0 + 40 + k * 66
            on = k == 2
            ring(d, x, 386, 20, 0, "rollover", typ=k + 1, bg=PANEL)
            if on: rect(d, x - 28, 358, x + 28, 414, outline=GOLD, w=2, r=6)
            text(d, x, 424, f"T{k + 1}", 11, GOLD if on else FAINT, "mm", "s")
    if t > S[3]:
        p = ev(t, S[3], .5)
        rect(d, rx0 + 14, 446, 871, 600, fill=mix(PANEL, GOLD, .1 * p), outline=mix(PANEL, GOLD, p), w=2, r=10)
        text(d, rx0 + 30, 468, "Which side is up?", 13.5, DIM, "lm", "m")
        if t > S[3] + 2.0:
            text(d, rx0 + 30, 500, "BURR SIDE UP", 24, GOLD, "lm", "b")
            conf = 0.9 * ev(t, S[3] + 2.2, 1.4)
            text(d, rx0 + 30, 534, "confidence score", 12.5, DIM, "lm", "m")
            chip(d, 855, 534, "example", FAINT, 10.5, "s", anchor="r")
            rect(d, rx0 + 30, 552, 855, 564, fill=(44, 52, 72), r=6)
            rect(d, rx0 + 30, 552, rx0 + 30 + (855 - rx0 - 30) * conf, 564, fill=GREEN, r=6)
            text(d, rx0 + 30, 583, "high enough → decision is sent", 11, GREEN, "lm", "s")
    if t > S[4]:
        p = ev(t, S[4], .5)
        rect(d, rx0 + 14, 616, 871, 686, fill=mix(PANEL, GREEN, .15 * p), outline=GREEN, w=2, r=10)
        text(d, rx0 + 30, 651, "Total time", 14, DIM, "lm", "m")
        text(d, 855, 651, "under 1 s", 22, GREEN, "rm", "b")
    text(d, 265, 610, "ML model on the server", 14, TXT, "mm", "s")
    text(d, 265, 632, "trained beforehand on ring images from Technocraft", 12, DIM, "mm", "m")
    draw_log(d, si, t, SA, box=(900, 100, 1265, 700))

def s_flip(d, t, D, S, si, SA):
    x = CAM1 + 12
    if t > S[2] + 1.0: x = lerp(CAM1 + 12, FLIPX, ev(t, S[2] + 1.0, 3.0))
    fl = ev(t, S[2] + 4.2, 1.8)
    after = lerp(FLIPX, FLIPX + 50, ev(t, S[2] + 6.4, D - S[2] - 6.6))
    if fl >= 1: x = after
    face = "burr" if fl < 0.5 else "rollover"
    sx = math.cos(math.pi * fl) if fl < 0.5 else -math.cos(math.pi * fl)
    ang = -37.4 if fl < 0.5 else 37.4
    st = {"belt_off": x, "lit": {}, "flip_busy": (1 - abs(2 * fl - 1)) if 0 < fl < 1 else 0, "new": {}}
    ring_on_belt(st, x, ang=ang, face=face, sx=sx, idlabel="#1042")
    if S[1] + 0.8 < t < S[2] + 0.3:
        push = ev(t, S[1] + 5.0, 1.2)
        st["flap"] = ev(t, S[1] + 4.6, .5) * (1 - ev(t, S[1] + 7.0, .6))
        if push < 1:
            ring_on_belt(st, 405, y=lerp(262, 346, push), ang=10, face="burr", idlabel="example" if push < .3 else None)
    if t > S[0] + 0.8:
        p = seg(t, S[0] + 0.8, S[0] + 2.4)
        if p < 1: st["lit"]["srv_plc"] = GREEN
        if p >= 1: st["new"]["plc"] = S[0] + 2.4
    step = 7 if t < S[2] else 8
    header(d, "B · Signal 1 and the flip", step=step)
    full_plant(d, t, st)
    if t > S[0] + 0.8: packet(d, WIRES["srv_plc"], seg(t, S[0] + 0.8, S[0] + 2.4), "SIGNAL 1: FLIP = YES", GREEN)
    if t > S[2] + 0.5: packet(d, WIRES["plc_flip"], seg(t, S[2] + 0.5, S[2] + 2.5), "FLIP", ORANGE)
    if t > S[0] + 2.4 and t < S[1]:
        chip(d, 690, 560, "Burr up + confident → FLIP = YES", GREEN, 12.5, "s", anchor="m")
    if S[1] - 0.2 < t < S[2] + 0.3:
        p = ev(t, S[1] - 0.2, .5) * (1 - ev(t, S[2], .3))
        x0, y0, x1, y1 = 30, 420, 880, 700
        rect(d, x0, y0, x1, y1, fill=mix(BG, (40, 18, 22), p), outline=mix(BG, RED, p), w=2.5, r=14)
        if p > 0.5:
            text(d, x0 + 24, y0 + 30, "⚠  Side check not clear? The system never guesses.", 20, RED, "lm", "b")
            for k, a in enumerate(("confidence score too low", "no ring in view", "two rings in view")):
                y = y0 + 76 + k * 30
                if t > S[1] + 0.8 + k * 0.9:
                    ell(d, x0 + 34, y, 4, fill=RED); text(d, x0 + 48, y, a, 15, TXT, "lm", "m")
            if t > S[1] + 4.5:
                text(d, x0 + 24, y0 + 182, "Alert raised → a diverter flap pushes the ring", 15, TXT, "lm", "s")
                text(d, x0 + 24, y0 + 206, "into a separate reject section", 15, TXT, "lm", "s")
                chip(d, x0 + 24, y0 + 246, "example ring shown on the belt", FAINT, 12, "s")
    if t > S[2] + 0.2:
        y = 380
        text(d, FLIPX + 60, 352, "burr up → turned over", 12.5, GOLD, "lm", "s")
        text(d, FLIPX + 60, 370, "rollover up → passes straight through", 12, BLUE, "lm", "m")
    draw_log(d, si, t, SA)

def s_cam2(d, t, D, S, si, SA):
    x = lerp(FLIPX + 50, CAM2, ev(t, S[0] + 9.5, 4.0))
    z = cam_zoom(t, S[1] - 0.2, S[2] - 0.6, D, CAM2)
    flash = 0.0
    ft = S[1] + 3.0
    if ft <= t < ft + 0.7: flash = 1 - (t - ft) / 0.7
    st = {"belt_off": x, "flash2": flash, "lit": {}}
    ring_on_belt(st, x + max(0, t - S[0] - 3.2) * 0.4, ang=37.4, face="rollover", lit=flash * .6, idlabel="#1042")
    header_step = 9 if t < S[1] else 10 if t < S[2] else 11
    full_plant(d, t, st)
    if t > S[0] + 6.0: packet(d, WIRES["trig2"], seg(t, S[0] + 6.0, S[0] + 9.0), "FLIP TRIGGER + DELAY", YEL)
    if S[0] + 3.0 < t < S[1] - 0.2:
        q = ev(t, S[0] + 9.5, 4.0)
        card(d, 30, 560, 330, 700, "Camera 2 trigger", col=YEL, tcol=YEL, sz=14)
        text(d, 46, 604, "not sent by the line controller", 12, RED, "lm", "s")
        text(d, 46, 628, "start: flipper trigger", 12, TXT, "lm", "m")
        text(d, 46, 652, "delay counted in encoder pulses", 12, TXT, "lm", "m")
        text(d, 46, 676, f"{int(640 * q):,} / 640 pulses → capture", 12, CYAN, "lm", "monob")
    if z > 0.3 and t > S[1] + 3.0:
        rx = x + max(0, t - S[0] - 3.2) * 0.4
        pts = ring_pts(rx, 262, 28, 37.4, 3, 1, 1.0)
        line(d, pts + [pts[0]], mix(BELT, CYAN, ev(t, S[1] + 3.2, .6)), 1.6)
    if t > S[2]:
        p = seg(t, S[2] + 0.6, S[2] + 2.6)
        packet(d, WIRES["cam2"], p, "IMAGE 12 MP", BLUE)
        if p >= 1: packet(d, WIRES["sw_srv"], seg(t, S[2] + 2.6, S[2] + 3.3), "IMG", BLUE)
    with screen():
        header(d, "B · Camera 2 takes the picture", step=header_step)
        if z > 0.3 and t > S[1] + 0.3:
            p = ev(t, S[1] + 0.3, .5)
            card(d, 40, 560, 420, 690, "Camera 2 · 12 MP", col=mix(LINE, BLUE, p), tcol=BLUE)
            text(d, 56, 612, "diffuse strobe", 22, TXT, "lm", "b")
            text(d, 56, 644, "soft, even light, no glare", 12.5, DIM, "lm", "m")
            text(d, 56, 666, "→ clean outline of the notches", 12.5, CYAN, "lm", "s")
        draw_log(d, si, t, SA)
    view()

def s_angle(d, t, D, S, si, SA):
    header(d, "B · Measuring the angle", step=12)
    x0, y0, x1, y1 = 30, 112, 500, 582
    img_frame(d, x0, y0, x1, y1, "Camera 2 image · #1042 · 12 MP", BLUE)
    cx, cy, r = 265, 350, 150
    ang = 37.4  # ring rotation; the key notch points at 90° + ang
    ring(d, cx, cy, r, ang, "rollover", bg=(36, 38, 44), photo=True)
    key = ang + 90
    if t > S[1] + 0.3:
        for k, (na, nw, nd) in enumerate(TYPES[3]):
            if t < S[1] + 0.6 + k * 0.6: continue
            a = math.radians(na + ang)
            px, py = cx + math.cos(a) * r * 0.93, cy - math.sin(a) * r * 0.93
            ell(d, px, py, 20 if k == 0 else 15, outline=GREEN, w=3)
        ell(d, cx, cy, 6, fill=CYAN)
    if t > S[1] + 3.5:
        q = ev(t, S[1] + 3.5, 1.0)
        a = math.radians(key)
        line(d, [(cx, cy), (cx + math.cos(a) * r * 1.15 * q, cy - math.sin(a) * r * 1.15 * q)], GREEN, 3)
        dashed(d, [(cx, cy), (cx, cy - r * 1.15)], GOLD, 2.5)
        text(d, cx + 8, cy - r * 1.15 - 4, "target", 12, GOLD, "lm", "s")
    if t > S[1] + 5.0:
        q = ev(t, S[1] + 5.0, 1.2)
        arc(d, cx, cy, 70, key, lerp(key, 90, q), YEL, 4)
        text(d, cx + 70, cy - 92, "37.4°", 20, YEL, "lm", "b")
    rx0 = 520
    card(d, rx0, 112, 885, 700, "Result", col=LINE)
    if t > S[1] + 2.0:
        text(d, rx0 + 18, 160, "Notches found", 13.5, DIM, "lm", "m")
        text(d, rx0 + 18, 182, "3 (Type 3 layout)", 16, GREEN, "lm", "b"); tick(d, 860, 170, 16)
    if t > S[1] + 6.0:
        p = ev(t, S[1] + 6.0, .5)
        text(d, rx0 + 18, 222, "Rotate by", 13.5, DIM, "lm", "m")
        text(d, rx0 + 18, 256, "37.4°  clockwise", 30, mix(PANEL, YEL, p), "lm", "b")
        # range bar 0..89
        bx0, bx1, by = rx0 + 20, 860, 300
        rect(d, bx0, by, bx1, by + 10, fill=(44, 52, 72), r=5)
        xv = lerp(bx0, bx1, 37.4 / 89)
        rect(d, bx0, by, xv, by + 10, fill=YEL, r=5)
        text(d, bx0, by + 24, "0°", 11, DIM, "lm", "m"); text(d, bx1, by + 24, "≈ 89°", 11, DIM, "rm", "m")
        text(d, (bx0 + bx1) / 2, by + 24, "always in the configured direction", 11, DIM, "mm", "m")
    if t > S[2]:
        p = ev(t, S[2], .5)
        rect(d, rx0 + 14, 350, 871, 560, fill=mix(PANEL, PURP, .1 * p), outline=mix(PANEL, PURP, p), w=2, r=10)
        text(d, rx0 + 30, 374, "How the notches are found", 14, PURP, "lm", "b")
        rect(d, rx0 + 30, 396, 855, 466, fill=mix(PANEL, PURP, .16), outline=PURP, w=2, r=8)
        text(d, (rx0 + 30 + 855) / 2, 420, "ML model", 19, TXT, "mm", "b")
        text(d, (rx0 + 30 + 855) / 2, 446, "runs on the server's GPU", 11.5, DIM, "mm", "m")
        if t > S[2] + 2.5:
            text(d, rx0 + 30, 494, "trained beforehand on images of real rings", 13, TXT, "lm", "m")
            text(d, rx0 + 30, 518, "received from Technocraft", 13, TXT, "lm", "m")
    if t > S[3]:
        p = ev(t, S[3], .5)
        rect(d, rx0 + 14, 576, 871, 686, fill=mix(PANEL, GREEN, .12 * p), outline=mix(PANEL, GREEN, p), w=2, r=10)
        text(d, rx0 + 30, 600, "Matched to ring ID #1042", 14, GREEN, "lm", "b")
        x = chip(d, rx0 + 30, 640, "sensor", RED, 12.5, "s")
        arrow(d, x + 6, 640, x + 30, 640, DIM, 2)
        x = chip(d, x + 36, 640, "camera 1", BLUE, 12.5, "s")
        arrow(d, x + 6, 640, x + 30, 640, DIM, 2)
        x = chip(d, x + 36, 640, "camera 2", BLUE, 12.5, "s")
        tick(d, 856, 640, 16)
    text(d, 265, 610, "Notch finding: ML model", 14, TXT, "mm", "s")
    text(d, 265, 632, "trained beforehand on ring images from Technocraft", 12, DIM, "mm", "m")
    draw_log(d, si, t, SA, box=(900, 100, 1265, 700))

def s_robot(d, t, D, S, si, SA):
    # ring moves to pick point, robot picks, rotates, places on pins
    pick = (870, 262); slot = PINS[3]
    xr = lerp(CAM2 + 4, pick[0], ev(t, 0.2, max(1.0, S[1] + 0.5)))
    t1, t2, t3, t4 = S[1] + 0.6, S[1] + 1.8, S[1] + 3.2, S[1] + 4.6
    ang = 37.4; rpos = (xr, pick[1]); arm = (930, 250); filled = 3; placed = False
    if t < t1:
        arm = (lerp(930, xr, ev(t, S[1] - 0.6, 1.2)), lerp(250, pick[1], ev(t, S[1] - 0.6, 1.2)))
    elif t < t2:
        p = ev(t, t1, t2 - t1)
        rpos = (lerp(pick[0], 1000, p), lerp(pick[1], 200, p)); arm = rpos
    elif t < t3:
        rpos = (1000, 200); arm = rpos
        ang = lerp(37.4, 0, ev(t, t2, t3 - t2))
    elif t < t4:
        p = ev(t, t3, t4 - t3)
        rpos = (lerp(1000, slot[0], p), lerp(200, slot[1], p)); arm = rpos; ang = 0
    else:
        placed = True; arm = (lerp(slot[0], 930, ev(t, t4, 1.2)), lerp(slot[1], 250, ev(t, t4, 1.2))); filled = 4
    st = {"belt_off": xr if t < t1 else pick[0] + (t - t1) * 14, "lit": {}, "arm": arm, "filled": filled, "new": {}}
    # next ring arriving
    if t > S[2] + 0.8:
        nx = lerp(-40, SENS1 - 10, ev(t, S[2] + 0.8, 2.5))
        st["beam"] = t > S[2] + 2.9
        ring_on_belt(st, nx, y=280, ang=-70, face="rollover", idlabel="#1043" if t > S[2] + 3.1 else None)
    header(d, "B · Signal 2 and the robot", step=13 if t < S[1] else 14)
    full_plant(d, t, st)
    if not placed:
        ring(d, rpos[0], rpos[1], 26 if t < t3 else lerp(26, 18, ev(t, t3, t4 - t3)), ang, "rollover", bg=BELT)
        chip(d, rpos[0], rpos[1] + 44, "#1042", TXT, 10.5, "monob", fill=(30, 36, 52), anchor="m")
        bx, by = ROBOT; arm2(d, bx, by, arm[0], arm[1], BLUE)
    if t > S[0] + 0.5:
        p = seg(t, S[0] + 0.5, S[0] + 1.8)
        packet(d, WIRES["srv_plc"], p, "SIGNAL 2: 37.4°", GREEN)
        if p >= 1: packet(d, WIRES["plc_robot"], seg(t, S[0] + 1.8, S[0] + 3.0), "ROTATE 37.4°", ORANGE)
    if t2 < t < t3 + 0.5:
        arc(d, 1000, 200, 40, 90 + 37.4, 90 + ang, YEL, 3); text(d, 1000, 145, f"rotating {37.4 - ang:.1f}°", 13, YEL, "mm", "b")
    if t > t4:
        p = ev(t, t4, .5)
        rect(d, 30, 560, 320, 690, fill=mix(PANEL, GREEN, .12 * p), outline=GREEN, w=2, r=10)
        text(d, 48, 586, "Ring #1042 done", 16, GREEN, "lm", "b")
        text(d, 48, 614, "rollover side up · 37.4° turned", 12.5, TXT, "lm", "m")
        text(d, 48, 636, "placed on the pins", 12.5, TXT, "lm", "m")
        text(d, 48, 664, "next ring every ~6 s", 12.5, DIM, "lm", "m")
    if t > S[2] + 3.0:
        packet(d, WIRES["trig1"], seg(t, S[2] + 3.0, S[2] + 4.2), "PULSE", YEL)
    draw_log(d, si, t, SA)

CONF = [97.5 - 0.004 * i + random.Random(i).uniform(-0.5, 0.5) - (0.01 * max(0, i - 120) ** 1.45) for i in range(200)]

def s_bg(d, t, D, S, si, SA):
    header(d, "C · Running in the background", sub="V7 AI Solutions software on the server · 24/7")
    tiles = [(20, 96, 430, 396), (440, 96, 850, 396), (860, 96, 1270, 396),
             (20, 408, 430, 708), (440, 408, 850, 708), (860, 408, 1270, 708)]
    names = [("Logging & traceability", BLUE), ("Missed-ring check", RED), ("Confidence watch", GOLD),
             ("Heartbeat", CYAN), ("Operator screen", GREEN), ("Automatic restart", YEL)]
    for i, ((x0, y0, x1, y1), (nm, c)) in enumerate(zip(tiles, names)):
        st = S[i + 1] - 0.3
        if t < st:
            rect(d, x0, y0, x1, y1, outline=(32, 40, 58), w=1.5, r=12); continue
        lt = t - st
        p = ev(lt, 0, .6)
        card(d, x0, y0, x1, y1, nm, col=mix(LINE, c, .35 + .65 * p * (1 if i == min(5, sum(t >= s - .3 for s in S[1:]) - 1) else .4)), tcol=c)
        if i == 0:
            rows = ["#1040  img1 img2  BURR  score  flip  52.0°",
                    "#1041  img1 img2  ROLL  score  pass  22.1°",
                    "#1042  img1 img2  BURR  score  flip  37.4°",
                    "#1043  img1 img2  ROLL  score  pass  11.8°",
                    "#1044  img1 img2  BURR  score  flip  64.3°",
                    "#1045  img1 img2  ROLL  score  pass   5.6°"]
            n = min(len(rows), 3 + int(lt / 1.2))
            text(d, x0 + 16, y0 + 50, "ID     images     side  conf.  flip  angle   (example)", 10.5, FAINT, "lm", "mono")
            for k, s in enumerate(rows[:n]):
                text(d, x0 + 16, y0 + 74 + k * 24, s, 10.5, TXT if k != 2 else GOLD, "lm", "mono")
            text(d, x0 + 16, y1 - 22, "every image, decision, confidence score + signal, by ring ID", 11, DIM, "lm", "m")
        if i == 1:
            sc = 1042 + int(lt / 1.5); pr = sc if lt < 6 else sc - 1
            text(d, x0 + 20, y0 + 70, "Presence sensor count", 13, DIM, "lm", "m"); text(d, x1 - 20, y0 + 70, f"{sc:,}", 22, TXT, "rm", "monob")
            text(d, x0 + 20, y0 + 110, "Rings processed", 13, DIM, "lm", "m")
            text(d, x1 - 20, y0 + 110, f"{pr:,}", 22, TXT if pr == sc else RED, "rm", "monob")
            ok = pr == sc
            rect(d, x0 + 20, y0 + 150, x1 - 20, y0 + 200, fill=mix(PANEL, GREEN if ok else RED, .15), outline=GREEN if ok else RED, w=1.5, r=8)
            text(d, (x0 + x1) / 2, y0 + 175, "counts match" if ok else "⚠ 1 ring missed → alert", 15, GREEN if ok else RED, "mm", "b")
            text(d, x0 + 20, y1 - 22, "a missed ring never slips by unnoticed", 11, DIM, "lm", "m")
        if i == 2:
            n = int(clamp(lt / 9) * 199) + 1
            gx0, gx1, gy0, gy1 = x0 + 46, x1 - 20, y0 + 50, y1 - 50
            def gy(v): return lerp(gy1, gy0, (v - 85) / 15)
            for v in (90, 95, 100):
                line(d, [(gx0, gy(v)), (gx1, gy(v))], (40, 48, 66), 1)
            line(d, [(gx0, gy(92)), (gx1, gy(92))], RED, 1.5)
            text(d, gx1, gy(92) + 10, "alarm level", 10, RED, "rm", "s")
            pts = [(lerp(gx0, gx1, k / 199), gy(CONF[k])) for k in range(n)]
            if len(pts) > 1: line(d, pts, GOLD, 2)
            if n > 1 and CONF[n - 1] < 92:
                rect(d, x0 + 16, y1 - 40, x1 - 16, y1 - 12, fill=mix(PANEL, RED, .2), outline=RED, w=1.5, r=6)
                text(d, (x0 + x1) / 2, y1 - 26, "⚠ confidence drifting: check light / rust", 12, RED, "mm", "b")
            else:
                text(d, x0 + 16, y1 - 22, "confidence score trend (example)", 11, DIM, "lm", "m")
        if i == 3:
            ax, bx_, y = x0 + 90, x1 - 90, y0 + 120
            drop = lt > 5.0
            rect(d, ax - 60, y - 28, ax + 40, y + 28, fill=mix(PANEL, GREEN, .15), outline=GREEN, w=2, r=8); text(d, ax - 10, y, "Server", 13, GREEN, "mm", "b")
            rect(d, bx_ - 40, y - 28, bx_ + 60, y + 28, fill=mix(PANEL, ORANGE, .15), outline=ORANGE, w=2, r=8); text(d, bx_ + 10, y, "PLC", 13, ORANGE, "mm", "b")
            if not drop:
                line(d, [(ax + 40, y), (bx_ - 40, y)], (70, 82, 104), 2)
                for k in range(2):
                    ph = (lt * .9 + k * .5) % 1
                    ell(d, lerp(ax + 40, bx_ - 40, ph if k == 0 else 1 - ph), y, 6, fill=CYAN)
                text(d, (x0 + x1) / 2, y + 60, "♥  heartbeat ok", 15, CYAN, "mm", "b")
            else:
                line(d, [(ax + 40, y), ((ax + bx_) / 2 - 14, y)], (70, 82, 104), 2)
                line(d, [((ax + bx_) / 2 + 14, y), (bx_ - 40, y)], (70, 82, 104), 2)
                cross(d, (ax + bx_) / 2, y, 18, RED, 3)
                rect(d, x0 + 60, y + 44, x1 - 60, y + 88, fill=mix(PANEL, RED, .25), outline=RED, w=2, r=8)
                text(d, (x0 + x1) / 2, y + 66, "LINK LOST → SAFE STOP", 15, RED, "mm", "b")
            text(d, x0 + 16, y1 - 22, "server and line controller check each other", 11, DIM, "lm", "m")
        if i == 4:
            sx0, sy0, sx1, sy1 = x0 + 40, y0 + 46, x1 - 40, y1 - 50
            rect(d, sx0, sy0, sx1, sy1, fill=(12, 16, 24), outline=(90, 100, 124), w=3, r=6)
            rect(d, (sx0 + sx1) / 2 - 20, sy1, (sx0 + sx1) / 2 + 20, sy1 + 14, fill=(70, 78, 98))
            alert = lt > 3.0
            chip(d, sx0 + 12, sy0 + 20, "● RUNNING" if not alert else "● ATTENTION", GREEN if not alert else GOLD, 11, "b")
            text(d, sx1 - 12, sy0 + 20, "rings today 1,042", 10.5, DIM, "rm", "mono")
            text(d, sx0 + 12, sy0 + 50, "cycle 6.0 s · all checks running", 10.5, TXT, "lm", "mono")
            if alert:
                rect(d, sx0 + 10, sy0 + 68, sx1 - 10, sy1 - 10, fill=mix(BG, GOLD, .12), outline=GOLD, w=1.2, r=4)
                text(d, sx0 + 20, sy0 + 84, "Low confidence score on #1051, diverted", 11, GOLD, "lm", "s")
                for k, s in enumerate(("1. Check ring in reject section", "2. Wipe Camera 1 window", "3. Press RESUME")):
                    text(d, sx0 + 20, sy0 + 106 + k * 18, s, 10.5, TXT, "lm", "m")
        if i == 5:
            cyc = (lt % 5.0) / 5.0
            dip = 0.35 < cyc < 0.6
            gx0, gx1, gy = x0 + 20, x1 - 20, y0 + 80
            text(d, x0 + 20, y0 + 52, "mains power", 11, DIM, "lm", "m")
            pts = [(lerp(gx0, gx1, k / 60), gy + (22 if 0.35 < k / 60 < 0.6 else 0)) for k in range(61)]
            line(d, pts, YEL, 2)
            ph = lerp(gx0, gx1, cyc); line(d, [(ph, gy - 14), (ph, gy + 30)], TXT, 1)
            rect(d, x0 + 20, y0 + 130, x0 + 190, y0 + 190, fill=mix(PANEL, GREEN, .15), outline=GREEN, w=1.5, r=8)
            text(d, x0 + 105, y0 + 152, "Server", 13, GREEN, "mm", "b"); text(d, x0 + 105, y0 + 172, "still running", 11, TXT, "mm", "m")
            rect(d, x0 + 210, y0 + 130, x1 - 20, y0 + 190, fill=mix(PANEL, YEL, .15 if dip else .05), outline=YEL, w=1.5, r=8)
            text(d, (x0 + 210 + x1 - 20) / 2, y0 + 152, "UPS", 13, YEL, "mm", "b")
            text(d, (x0 + 210 + x1 - 20) / 2, y0 + 172, "on battery" if dip else "standby", 11, TXT, "mm", "m")
            text(d, x0 + 16, y1 - 22, "after a fault or power dip: restarts on its own", 11, DIM, "lm", "m")

MULTI_FACES = ["burr", "rollover", "burr", "burr", "rollover", "burr", "rollover", "rollover", "burr", "rollover"]
MULTI_ANG = [random.Random(50 + k).uniform(-60, 60) for k in range(10)]

def clock(tt):
    sec = 42 * 60 + 13.112 + tt * 4
    return f"10:{int(sec // 60):02d}:{sec % 60:06.3f}"

def s_multi(d, t, D, S, si, SA):
    header(d, "B · Ten rings in a row", sub="Detect · check side · flip if needed · measure angle · place")
    N, PICK, t0 = 10, 870.0, 1.0
    gap = clamp((D - 4.25) / 16.5, 1.35, 2.0); v = 120.0 / gap
    def xr(i, tt): return -30 + v * (tt - t0 - i * gap)
    def tat(i, x): return t0 + i * gap + (x + 30) / v
    tp = [tat(i, PICK) for i in range(N)]
    CARRY, BACK = 0.75, 0.6
    filled = sum(t >= tp[i] + CARRY for i in range(N))
    st = {"belt_off": v * t, "lit": {}, "filled": filled, "new": {}, "flash1": 0, "flash2": 0}
    flipped = passed = 0
    carry = None
    for i in range(N):
        x = xr(i, t)
        if x < -40 or t >= tp[i] + CARRY: continue
        burr = MULTI_FACES[i] == "burr"
        if t >= tp[i]:
            carry = i; continue
        face, sx, ang = MULTI_FACES[i], 1.0, MULTI_ANG[i]
        if burr:
            fl = clamp((x - (FLIPX - 25)) / 50)
            if fl >= 0.5: face, ang = "rollover", -MULTI_ANG[i]
            sx = math.cos(math.pi * fl) if fl < 0.5 else -math.cos(math.pi * fl)
            if 0 < fl < 1: st["flip_busy"] = 1 - abs(2 * fl - 1)
        st["flash1"] = max(st["flash1"], clamp(1 - abs(x - CAM1) / 10))
        st["flash2"] = max(st["flash2"], clamp(1 - abs(x - CAM2) / 10))
        if abs(x - SENS1) < 26: st["beam"] = True
        ring_on_belt(st, x, ang=ang, face=face, sx=sx, lit=max(clamp(1 - abs(x - CAM1) / 10), clamp(1 - abs(x - CAM2) / 10)) * .6,
                     idlabel=f"#{1044 + i}" if x > SENS1 else None)
    for i in range(N):
        if xr(i, t) > FLIPX + 25 or t >= tp[i]:
            if MULTI_FACES[i] == "burr": flipped += 1
            else: passed += 1
    # robot arm
    rest = (930, 250)
    arm = rest
    if t < tp[0]: arm = (lerp(rest[0], PICK, ev(t, tp[0] - 1.2, 1.0)), lerp(rest[1], 262, ev(t, tp[0] - 1.2, 1.0)))
    for i in range(N):
        sl = PINS[i]
        if tp[i] <= t < tp[i] + CARRY:
            p = ev(t, tp[i], CARRY); arm = (lerp(PICK, sl[0], p), lerp(262, sl[1], p))
        elif tp[i] + CARRY <= t < tp[i] + CARRY + BACK:
            p = ev(t, tp[i] + CARRY, BACK)
            tgt = (PICK, 262) if i < N - 1 else rest
            arm = (lerp(sl[0], tgt[0], p), lerp(sl[1], tgt[1], p))
        elif i < N - 1 and tp[i] + CARRY + BACK <= t < tp[i + 1]: arm = (PICK, 262)
    if t >= tp[-1] + CARRY + BACK: arm = rest
    st["arm"] = arm
    full_plant(d, t, st)
    if carry is not None:
        p = ev(t, tp[carry], CARRY)
        a0 = -MULTI_ANG[carry] if MULTI_FACES[carry] == "burr" else MULTI_ANG[carry]
        ring(d, arm[0], arm[1], lerp(26, 18, p), lerp(a0, 0, p), "rollover")
        arm2(d, ROBOT[0], ROBOT[1], arm[0], arm[1], BLUE)
    # data packets for each ring
    for i in range(N):
        tc1, tc2 = tat(i, CAM1), tat(i, CAM2)
        packet(d, WIRES["cam1"], (t - tc1) / 0.6, "IMG", BLUE)
        packet(d, WIRES["srv_plc"], (t - tc1 - 0.7) / 0.5, "FLIP" if MULTI_FACES[i] == "burr" else "PASS", GREEN)
        packet(d, WIRES["cam2"], (t - tc2) / 0.7, "IMG", BLUE)
        packet(d, WIRES["plc_robot"], (t - tc2 - 0.8) / 0.5, "ANGLE", ORANGE)
    rect(d, 30, 560, 330, 700, fill=PANEL, outline=GREEN, w=2, r=10)
    text(d, 48, 584, "Run counter", 14, GREEN, "lm", "b")
    for k, (a, b, c) in enumerate((("Placed in slots", f"{filled} / 10", GREEN), ("Flipped (burr up)", str(flipped), GOLD),
                                   ("Passed straight (rollover up)", str(passed), BLUE))):
        y = 616 + k * 26
        text(d, 48, y, a, 12.5, DIM, "lm", "m"); text(d, 314, y, b, 15, c, "rm", "monob")
    if filled == N:
        p = ev(t, tp[-1] + CARRY, .6)
        rect(d, 1035, 352, 1255, 384, fill=mix(BG, GREEN, .2 * p), outline=mix(BG, GREEN, p), w=1.5, r=8)
        text(d, 1145, 368, "10 / 10 rollover up · aligned", 12, mix(BG, GREEN, p), "mm", "b")
    extra = []
    for i in range(N):
        rid = f"#{1044 + i}"; burr = MULTI_FACES[i] == "burr"
        ang = MULTI_ANG[i] if burr else -MULTI_ANG[i]
        rot = (-ang) % 90 if False else abs(MULTI_ANG[i])
        tt = tat(i, SENS1); extra.append((tt, clock(tt), f"{rid} sensor triggered · ID", RED))
        tt = tat(i, CAM1) + 0.7; extra.append((tt, clock(tt), f"{rid} {'BURR up → flip' if burr else 'ROLL up → pass'}", GOLD if burr else BLUE))
        tt = tat(i, CAM2) + 0.6; extra.append((tt, clock(tt), f"{rid} rotate {rot:.1f}°", GREEN))
        tt = tp[i] + CARRY; extra.append((tt, clock(tt), f"{rid} placed in slot {i + 1}  ✓", GREEN))
    extra.sort(key=lambda r: r[0])
    draw_log(d, si, t, SA, extra=extra)

def s_gpu(d, t, D, S, si, SA):
    header(d, "D · Why the GPU is needed", sub="Training and running the ML models")
    x0, y0, x1, y1 = 30, 100, 430, 420
    card(d, x0, y0, x1, y1, "GPU vs CPU", col=GREEN, tcol=GREEN)
    gpu_on = t > S[3]
    rect(d, 50, 150, 410, 250, fill=mix(PANEL, BLUE, .12), outline=BLUE, w=2, r=8)
    text(d, 66, 170, "CPU", 18, BLUE, "lm", "b")
    text(d, 66, 196, "a few powerful cores, one job after another", 11.5, DIM, "lm", "m")
    for k in range(8):
        busy = (int(t * 3) + k) % 3 != 0
        rect(d, 66 + k * 42, 212, 100 + k * 42, 240, fill=mix(PANEL, BLUE, .6 if busy else .2), r=4)
    rect(d, 50, 266, 410, 400, fill=mix(PANEL, PURP, .2 if gpu_on else .06), outline=PURP, w=2, r=8)
    text(d, 66, 286, "GPU", 18, PURP, "lm", "b")
    text(d, 66, 312, "thousands of small cores, all at once", 11.5, DIM, "lm", "m")
    for i in range(40):
        for j in range(6):
            on = gpu_on and (math.sin(t * 6 + i * .5 + j) > -0.2)
            rect(d, 66 + i * 8.4, 328 + j * 11, 72 + i * 8.4, 336 + j * 11, fill=mix(PANEL, PURP, .9 if on else .25))
    if t > S[1]:
        rx0, ry0 = 460, 100
        card(d, rx0, ry0, 1250, 270, "Real rings aren't perfect → an ML model copes better than fixed rules", col=mix(LINE, GOLD, ev(t, S[1], .5)), tcol=GOLD)
        variants = [("clean", 0), ("rust", 1), ("oil", 2), ("scratches", 3), ("light changes", 4)]
        for k, (nm, _) in enumerate(variants):
            if t < S[1] + 2.5 + k * 0.7: continue
            cx = rx0 + 90 + k * 150; cy = 192
            rect(d, cx - 55, cy - 55, cx + 55, cy + 55, fill=(36, 38, 44), r=6)
            ring(d, cx, cy, 42, 40, "burr", bg=(36, 38, 44), photo=True)
            rnd = random.Random(k)
            if nm == "rust":
                for _ in range(26):
                    a = rnd.uniform(0, 6.28); rr = rnd.uniform(24, 40)
                    ell(d, cx + math.cos(a) * rr, cy + math.sin(a) * rr, rnd.uniform(2, 5), fill=(150, 70, 30))
            if nm == "oil": ell(d, cx + 10, cy - 12, 22, 12, fill=(52, 46, 46))
            if nm == "scratches":
                for _ in range(5):
                    a = rnd.uniform(0, 6.28); line(d, [(cx + math.cos(a) * 40, cy + math.sin(a) * 40), (cx + math.cos(a + 1.2) * 30, cy + math.sin(a + 1.2) * 30)], (220, 220, 210), 1.2)
            if nm == "light changes": ell(d, cx - 18, cy - 18, 20, fill=(240, 236, 220))
            text(d, cx, cy + 68, nm, 12, TXT, "mm", "s")
    if t > S[2]:
        p = ev(t, S[2], .5)
        card(d, 460, 282, 1250, 420, "Trained beforehand", col=mix(LINE, PURP, p), tcol=PURP)
        steps = [("Ring images", "from Technocraft", GOLD), ("ML workstation", "with a GPU card", PURP),
                 ("Trained models", "side check + notches", GREEN), ("Server", "on the line", GREEN)]
        for k, (a, b, c) in enumerate(steps):
            if t < S[2] + 1.0 + k * 1.3: continue
            bx = 480 + k * 192
            rect(d, bx, 330, bx + 160, 396, fill=mix(PANEL, c, .14), outline=c, w=2, r=8)
            text(d, bx + 80, 354, a, 14, TXT, "mm", "b"); text(d, bx + 80, 376, b, 11, DIM, "mm", "m")
            if k: arrow(d, bx - 30, 363, bx - 4, 363, c, 2.5)
    if t > S[3]:
        p = ev(t, S[3], .5)
        card(d, 30, 432, 700, 640, "Why a GPU: training and running the models", col=mix(LINE, PURP, p), tcol=TXT)
        rows = [("Training on a CPU only", BLUE, 0.92, "very slow", S[3] + 1.5),
                ("Training on a GPU", PURP, 0.16, "much faster", S[3] + 3.0)]
        for k, (nm, c, ln, note, ts) in enumerate(rows):
            y = 486 + k * 58
            text(d, 50, y, nm, 14, TXT, "lm", "s"); text(d, 680, y, note, 12, c, "rm", "m")
            rect(d, 50, y + 16, 680, y + 38, fill=(36, 44, 62), r=5)
            if t > ts: rect(d, 50, y + 16, 50 + 630 * ln * ev(t, ts, 1.2), y + 38, fill=c, r=5)
        if t > S[4]:
            text(d, 50, 600, "On the line: the server's GPU runs the models, fast + steady per image;", 12, PURP, "lm", "s")
            text(d, 50, 620, "the CPU stays free for cameras, signals and logging", 12, BLUE, "lm", "s")
        else:
            text(d, 50, 612, "time to train (illustrative)", 10.5, FAINT, "lm", "m")
    if t > S[5]:
        p = ev(t, S[5], .5)
        card(d, 712, 432, 1250, 640, "New ring type?", col=mix(LINE, GREEN, p), tcol=GREEN)
        cx, cy, R = 980, 540, 66
        steps = ["new ring type", "Technocraft sends\nnew images", "retrain the model", "update the\nserver"]
        for k, s_ in enumerate(steps):
            a = math.radians(90 - k * 90)
            px, py = cx + math.cos(a) * R * 1.75, cy - math.sin(a) * R * 0.95
            on = t > S[5] + 0.6 + k * 0.8
            for jj, ln in enumerate(s_.split("\n")):
                text(d, px, py + jj * 15 - (len(s_.split("\n")) - 1) * 7, ln, 11.5, TXT if on else FAINT, "mm", "s")
        ang = (t * 70) % 360
        arc(d, cx, cy, 34, ang, ang + 270, GREEN, 3)
    if t > S[6]:
        p = ev(t, S[6], .6)
        rect(d, 160, 654, 1120, 704, fill=mix(BG, PURP, .3 * p), outline=mix(BG, PURP, p), w=2.5, r=12)
        text(d, 640, 679, "The GPU makes accurate, reliable ML possible, without slowing the line", 17, mix(BG, TXT, p), "mm", "b")

def s_own(d, t, D, S, si, SA):
    header(d, "Who owns what")
    cols = [(40, 630, "V7 AI Solutions", "Vision software", GREEN, S[1],
             ["Ring-type setup + ML model training", "Sensor event → ring ID + count", "Camera 1: one ring, type, side",
              "Signal 1: flip yes / no", "Camera 2: notch angle (ML)", "Signal 2: rotation angle",
              "Logging, monitoring, operator screen"]),
            (650, 1240, "Technocraft", "Line, robot + hardware", ORANGE, S[2],
             ["Conveyor", "Flip mechanism", "Robot, gripper + robot program", "Line controller (PLC) program",
              "Pins", "Procures all hardware", "Ring images for ML training"])]
    for x0, x1, nm, sub, c, st, items in cols:
        if t < st - 0.3:
            rect(d, x0, 110, x1, 600, outline=(32, 40, 58), w=1.5, r=14); continue
        p = ev(t, st - 0.3, .6)
        rect(d, x0, 110, x1, 600, fill=mix(BG, c, .07 * p), outline=mix(BG, c, p), w=2.5, r=14)
        text(d, x0 + 28, 150, nm, 30, c, "lm", "b"); text(d, x0 + 28, 184, sub, 15, DIM, "lm", "m")
        for k, s in enumerate(items):
            if t < st + 0.4 + k * 0.45: continue
            y = 232 + k * 48
            tick(d, x0 + 40, y, 16, c); text(d, x0 + 62, y, s, 17, TXT, "lm", "m")
    if t > S[3]:
        p = ev(t, S[3], .8)
        text(d, 640, 650, "Thanks for watching", 30, mix(BG, TXT, p), "mm", "b")
        text(d, 640, 688, "V7 AI Solutions × Technocraft · ring orientation cell", 14, mix(BG, DIM, p), "mm", "m")

SCENES = [s_intro, s_hw, s_sw, s_arrive, s_cam1, s_check, s_flip, s_cam2, s_angle, s_robot, s_bg, s_multi, s_gpu, s_own]

# ------------------------------------------------------------------ render
def load_timing():
    with open(os.path.join(VO, "timing.json")) as f: return json.load(f)

def frame(si, t, TM):
    img = Image.new("RGB", (W * K, H * K), BG)
    d = ImageDraw.Draw(img)
    view()
    SA = [x["starts"] for x in TM]
    SCENES[si](d, t, TM[si]["dur"], TM[si]["starts"], si, SA)
    view()
    # fade in / out at scene edges
    D = TM[si]["dur"]
    img = img.resize((OW, OH), Image.LANCZOS)
    a = min(1.0, t / 0.35, (D - t) / 0.35)
    if a < 1: img = Image.blend(Image.new("RGB", (OW, OH), BG), img, max(0, a))
    # overall progress bar
    tot = sum(x["dur"] for x in TM); done = sum(x["dur"] for x in TM[:si]) + t
    ImageDraw.Draw(img).rectangle((0, OH - 5, OW * done / tot, OH), fill=GREEN)
    return img

def render_scene(si):
    TM = load_timing(); D = TM[si]["dur"]
    out = os.path.join(TMP, f"v{si:02d}.mp4")
    wav = os.path.join(VO, f"scene{si:02d}.wav")
    pr = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-t", f"{D:.3f}", out],
                          stdin=subprocess.PIPE)
    for f in range(int(round(D * FPS))):
        pr.stdin.write(frame(si, f / FPS, TM).tobytes())
    pr.stdin.close(); pr.wait()
    print("scene", si, "done", flush=True)
    return out

def main():
    os.makedirs(TMP, exist_ok=True)
    if sys.argv[1:2] == ["-1"]:       # preview stills: render.py -1 scene:t ...
        TM = load_timing()
        for a in sys.argv[2:]:
            si, t = a.split(":"); frame(int(si), float(t), TM).save(os.path.join(TMP, f"p{int(si):02d}_{float(t):05.1f}.png"))
        return
    only = [int(a) for a in sys.argv[1:]]
    TM = load_timing(); todo = only or list(range(len(TM)))
    with Pool(min(4, os.cpu_count())) as pool:
        pool.map(render_scene, sorted(todo, key=lambda i: -TM[i]["dur"]))
    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        for i in range(len(TM)): f.write(f"file 'v{i:02d}.mp4'\n")
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    "-movflags", "+faststart", OUT], check=True)
    print("wrote", OUT)

if __name__ == "__main__":
    main()
