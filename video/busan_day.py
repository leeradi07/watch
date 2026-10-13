#!/usr/bin/env python3
"""부산의 하루 — 부산 핫플레이스를 배경으로 새벽부터 밤까지 시간이 흐르는 영상 생성기.

모든 장면은 사진 없이 코드로 직접 그립니다. 하나의 시계가 05:00 → 23:00 으로 계속 흐르고,
하늘색·조명·해/달·별·창문 불빛이 그 시각에 맞춰 바뀌며 장소가 차례로 전환됩니다.

    해운대 해수욕장(새벽) → 해동용궁사(아침) → 감천문화마을(오전)
    → 블루라인파크 스카이캡슐(오후) → 부산타워·자갈치(노을)
    → 광안대교 드론쇼(저녁) → 마린시티 불꽃(밤)

사용법:
    pip install numpy pillow opencv-python-headless
    python3 video/busan_day.py                 # 1920x1080, video/busan_dawn_to_night.mp4
    BUSAN_W=960 python3 video/busan_day.py     # 빠른 미리보기 해상도
    python3 video/busan_day.py --still 3.0 9 20  # 해당 시각(초)의 정지 화면 PNG 만 저장
"""
import math
import os
import random
import re
import subprocess
import sys
import wave
from multiprocessing import Pool
from urllib.request import Request, urlopen

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W = int(os.environ.get("BUSAN_W", 1920))
H = W * 9 // 16
S = W / 1920.0          # 모든 좌표는 1920x1080 기준으로 작성하고 S 로 스케일
SS = 2                  # 정적 레이어 슈퍼샘플링 배율
FPS = 30
DUR = 44.0
FONT_DIR = os.path.join(HERE, "fonts")
OUT = os.environ.get("BUSAN_OUT", os.path.join(HERE, "busan_dawn_to_night.mp4"))


# ───────────────────────────── 공통 유틸 ─────────────────────────────

def lerp(a, b, t):
    return a + (b - a) * t


def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ss(e0, e1, x):
    t = clamp01((x - e0) / (e1 - e0))
    return t * t * (3 - 2 * t)


def ease(t):
    t = clamp01(t)
    return t * t * (3 - 2 * t)


def shade(c, k):
    return tuple(int(max(0, min(255, v * k))) for v in c)


def mixc(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def v3(c):
    return np.array(c, np.float32) / 255.0


def odd(n):
    n = max(1, int(n))
    return n if n % 2 else n + 1


# ───────────────────────────── 글꼴 ─────────────────────────────

FONT_WEIGHTS = {"Medium": 500, "Black": 900}


def ensure_fonts():
    os.makedirs(FONT_DIR, exist_ok=True)
    for name, wt in FONT_WEIGHTS.items():
        path = os.path.join(FONT_DIR, f"NotoSansKR-{name}.ttf")
        if os.path.exists(path):
            continue
        print(f"downloading Noto Sans KR {name} ...", flush=True)
        css = urlopen(Request(f"https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@{wt}",
                              headers={"User-Agent": "Mozilla/4.0"})).read().decode()
        url = re.search(r"url\((https://[^)]+\.ttf)\)", css).group(1)
        with open(path, "wb") as f:
            f.write(urlopen(url).read())


_fonts = {}


def font(weight, size):
    key = (weight, int(size))
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(FONT_DIR, f"NotoSansKR-{weight}.ttf"), int(size))
    return _fonts[key]


# ───────────────────────────── 시간 / 하늘 환경 ─────────────────────────────

# 영상 시각(초) → 하루 중 시각(시)
HOUR_KEYS = [(0.0, 5.0), (7.0, 6.6), (13.0, 8.6), (19.0, 12.0), (25.0, 16.6),
             (31.0, 19.2), (37.0, 21.3), (DUR, 23.0)]

# 시각 → (하늘 위쪽 색, 지평선 색, 주변광)
ENV_KEYS = [
    (5.0, (8, 12, 35), (35, 40, 80), (0.20, 0.22, 0.36)),
    (5.5, (18, 25, 62), (110, 80, 120), (0.32, 0.30, 0.45)),
    (6.0, (45, 60, 115), (240, 140, 110), (0.60, 0.50, 0.55)),
    (6.6, (80, 120, 185), (255, 195, 140), (0.90, 0.78, 0.70)),
    (7.5, (85, 145, 215), (225, 225, 220), (1.00, 0.93, 0.86)),
    (9.0, (70, 145, 230), (185, 220, 245), (1.02, 1.00, 0.97)),
    (12.0, (45, 125, 235), (165, 210, 250), (1.06, 1.05, 1.02)),
    (15.0, (55, 130, 225), (185, 215, 240), (1.04, 1.00, 0.95)),
    (16.8, (75, 125, 205), (245, 210, 160), (1.02, 0.90, 0.75)),
    (17.8, (70, 95, 175), (255, 170, 90), (0.98, 0.75, 0.55)),
    (18.6, (55, 60, 130), (250, 115, 75), (0.75, 0.50, 0.45)),
    (19.2, (35, 35, 95), (160, 85, 110), (0.45, 0.36, 0.48)),
    (19.8, (18, 22, 70), (60, 55, 110), (0.26, 0.26, 0.42)),
    (20.6, (8, 10, 35), (25, 30, 65), (0.16, 0.17, 0.30)),
    (23.0, (4, 6, 20), (16, 20, 45), (0.12, 0.13, 0.24)),
]


def hour_at(t):
    for (t0, h0), (t1, h1) in zip(HOUR_KEYS, HOUR_KEYS[1:]):
        if t <= t1:
            return lerp(h0, h1, clamp01((t - t0) / (t1 - t0)))
    return HOUR_KEYS[-1][1]


def sun_alt(h):
    return math.sin(math.pi * (h - 6.1) / 12.9)


class Env:
    def __init__(self, h):
        self.h = h
        keys = ENV_KEYS
        i = 0
        while i < len(keys) - 2 and h > keys[i + 1][0]:
            i += 1
        k0, k1 = keys[i], keys[i + 1]
        f = clamp01((h - k0[0]) / (k1[0] - k0[0]))
        self.top = lerp(v3(k0[1]), v3(k1[1]), f)
        self.hor = lerp(v3(k0[2]), v3(k1[2]), f)
        self.amb = lerp(np.array(k0[3], np.float32), np.array(k1[3], np.float32), f)
        self.night = max(1 - ss(5.3, 6.4, h), ss(17.7, 19.5, h))
        self.star = max(1 - ss(5.0, 5.9, h), ss(19.0, 20.4, h))
        self.moon = ss(19.6, 20.6, h)
        self.alt = sun_alt(h)
        warm = np.array([1.0, 0.50, 0.22], np.float32)
        mid = np.array([1.0, 0.80, 0.52], np.float32)
        high = np.array([1.0, 0.96, 0.88], np.float32)
        self.sun_col = lerp(lerp(warm, mid, ss(0.0, 0.25, self.alt)), high, ss(0.2, 0.6, self.alt))
        self.sun_vis = ss(-0.10, 0.03, self.alt)


# ───────────────────────────── 정적 레이어 ─────────────────────────────

class Layer:
    """1920x1080 설계 좌표로 그리는 정적 레이어. haze 는 대기원근(멀수록 지평선 색에 묻힘)."""

    def __init__(self, haze=0.0):
        self.haze = haze
        self.k = S * SS
        self.size = (W * SS, H * SS)
        self.im = Image.new("RGBA", self.size, (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.em = None

    def _em(self):
        if self.em is None:
            self.em = Image.new("RGB", self.size, (0, 0, 0))
            self.ed = ImageDraw.Draw(self.em)
            self.th = Image.new("L", self.size, 0)
            self.td = ImageDraw.Draw(self.th)

    def P(self, pts):
        k = self.k
        return [(x * k, y * k) for x, y in pts]

    @staticmethod
    def _c(col, a=255):
        return tuple(int(c) for c in col[:3]) + (int(a),)

    def poly(self, pts, col, a=255):
        self.d.polygon(self.P(pts), fill=self._c(col, a))

    def rect(self, x0, y0, x1, y1, col, a=255):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col, a)

    def ellipse(self, cx, cy, rx, ry, col, a=255):
        k = self.k
        self.d.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k], fill=self._c(col, a))

    def line(self, pts, col, w, a=255):
        self.d.line(self.P(pts), fill=self._c(col, a), width=max(1, int(round(w * self.k))), joint="curve")

    # 발광체: thr(0~1) 은 밤 정도가 그 값을 넘을 때 켜지는 순서
    def light_rect(self, x0, y0, x1, y1, col, thr):
        self._em()
        k = self.k
        box = [x0 * k, y0 * k, x1 * k - 1, y1 * k - 1]
        self.ed.rectangle(box, fill=tuple(int(c) for c in col))
        self.td.rectangle(box, fill=int(thr * 255))

    def light_ellipse(self, cx, cy, rx, ry, col, thr):
        self._em()
        k = self.k
        box = [(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k]
        self.ed.ellipse(box, fill=tuple(int(c) for c in col))
        self.td.ellipse(box, fill=int(thr * 255))

    def light_line(self, pts, col, w, thr):
        self._em()
        wd = max(1, int(round(w * self.k)))
        self.ed.line(self.P(pts), fill=tuple(int(c) for c in col), width=wd, joint="curve")
        self.td.line(self.P(pts), fill=int(thr * 255), width=wd, joint="curve")

    def finalize(self):
        a = np.asarray(self.im, np.float32) / 255.0
        al = a[..., 3:4]
        pm = cv2.resize(a[..., :3] * al, (W, H), interpolation=cv2.INTER_AREA)
        al = cv2.resize(al, (W, H), interpolation=cv2.INTER_AREA)[..., None]
        em = th = None
        if self.em is not None:
            em = cv2.resize(np.asarray(self.em, np.float32) / 255.0, (W, H), interpolation=cv2.INTER_AREA)
            th = cv2.resize(np.asarray(self.th, np.float32) / 255.0, (W, H), interpolation=cv2.INTER_AREA)[..., None]
        self.im = self.d = self.em = None
        return pm, al, em, th


class Group:
    """레이어 묶음을 미리 합성: img*(1-A) + B1*주변광 + HZ*지평선색 + E*밤조명."""

    def __init__(self, layers):
        B1 = np.zeros((H, W, 3), np.float32)
        HZ = np.zeros((H, W, 1), np.float32)
        A = np.zeros((H, W, 1), np.float32)
        E = np.zeros((H, W, 3), np.float32)
        R = np.ones((H, W, 1), np.float32)
        has_e = False
        for L in layers:
            pm, a, em, th = L.finalize()
            B1 = pm * (1 - L.haze) + B1 * (1 - a)
            HZ = a * L.haze + HZ * (1 - a)
            A = a + A * (1 - a)
            E *= (1 - a)
            if em is not None:
                has_e = True
                E += em
                cov = em.max(axis=2, keepdims=True) > 0.004
                R = np.where(cov, th, R)
        rows = np.nonzero((A[..., 0].max(axis=1) > 1e-3) | (E.max(axis=(1, 2)) > 1e-3))[0]
        self.y0, self.y1 = (int(rows[0]), int(rows[-1]) + 1) if len(rows) else (0, 0)
        sl = slice(self.y0, self.y1)
        self.B1, self.HZ, self.A = B1[sl].copy(), HZ[sl].copy(), A[sl].copy()
        self.E = E[sl].copy() if has_e else None
        self.R = R[sl].copy() if has_e else None

    def apply(self, img, env):
        if self.y1 <= self.y0:
            return
        reg = img[self.y0:self.y1]
        reg *= (1 - self.A)
        reg += self.B1 * env.amb + self.HZ * env.hor
        if self.E is not None and env.night > 0.002:
            reg += self.E * (np.clip((env.night - self.R) * 5.0, 0, 1) * 1.15)


# ───────────────────────────── 그리기 도우미 ─────────────────────────────

WARM = [(255, 205, 135), (255, 190, 120), (255, 222, 170), (240, 235, 255), (200, 220, 255)]


def ridge(rng, x0, x1, base, amp, step=8, octaves=4, wl=700):
    ph = [rng.uniform(0, 6.28) for _ in range(octaves)]
    pts = []
    x = x0
    while x <= x1 + step:
        y = base
        for i in range(octaves):
            y -= amp / (1.7 ** i) * math.sin(x * 2 * math.pi * (2 ** i) / wl + ph[i])
        pts.append((x, y))
        x += step
    return pts


def dome(rng, x0, x1, base, height, rough=6, step=6, power=0.6):
    pts = []
    ph = rng.uniform(0, 6.28)
    x = x0
    while x <= x1 + step:
        u = clamp01((x - x0) / (x1 - x0))
        y = base - height * (math.sin(math.pi * u) ** power) - rough * math.sin(x * 0.05 + ph) * math.sin(math.pi * u)
        pts.append((x, y))
        x += step
    return pts


def fill_below(L, pts, ybot, col):
    L.poly(list(pts) + [(pts[-1][0], ybot), (pts[0][0], ybot)], col)


def canopy(L, pts, rng, cols, size=14, density=0.5, depth=1.0):
    """능선을 따라 나무 수관(둥근 덩어리)을 얹어 숲 질감을 만든다."""
    for x, y in pts:
        if rng.random() > density:
            continue
        r = size * rng.uniform(0.6, 1.3)
        c = rng.choice(cols)
        L.ellipse(x + rng.uniform(-4, 4), y + r * 0.35 + rng.uniform(0, size * depth), r * 1.15, r, c)


def building(L, rng, x0, x1, top, bot, col, win=(5, 7, 6, 8), density=0.65, thr=(0.0, 0.85),
             glass=None, side=0.82, crown=None):
    L.rect(x0, top, x1, bot, col)
    L.rect(x0 + (x1 - x0) * 0.68, top, x1, bot, shade(col, side))
    ww, wh, gx, gy = win
    wc = glass or shade(col, 0.7)
    y = top + gy
    while y + wh < bot - 2:
        x = x0 + gx * 0.7
        while x + ww < x1 - gx * 0.5:
            L.rect(x, y, x + ww, y + wh, wc)
            if rng.random() < density:
                L.light_rect(x, y, x + ww, y + wh, rng.choice(WARM), rng.uniform(*thr))
            x += ww + gx
        y += wh + gy
    if crown:
        L.light_line([(x0, top + 1), (x1, top + 1)], crown, 2.0, 0.05)


def kroof(L, cx, ybot, w, h, col, lift=0.32):
    """기와지붕: 처마 끝이 살짝 들린 곡선 지붕."""
    n = 30
    eave = []
    for i in range(n + 1):
        u = i / n * 2 - 1
        eave.append((cx + u * w / 2, ybot - h * lift * abs(u) ** 3.2))
    rw = w * 0.56
    right = []
    for i in range(1, 11):
        s = i / 10
        right.append((lerp(cx + w / 2, cx + rw / 2, s), lerp(ybot - h * lift, ybot - h, s ** 0.55)))
    left = [(2 * cx - x, y) for x, y in reversed(right)]
    L.poly(eave + right + left, col)
    # 기와 골 표현
    for i in range(1, 16):
        u = i / 16 * 2 - 1
        x = cx + u * w * 0.46
        L.line([(x, ybot - h * lift * abs(u) ** 3.2 - 2), (lerp(x, cx + u * rw / 2, 0.9), ybot - h * 0.93)],
               shade(col, 0.82), 1.4)
    # 용마루
    L.rect(cx - rw / 2 - 4, ybot - h - 6, cx + rw / 2 + 4, ybot - h + 3, shade(col, 0.7))
    L.poly([(cx - rw / 2 - 4, ybot - h - 6), (cx - rw / 2 - 16, ybot - h - 16), (cx - rw / 2 - 2, ybot - h + 3)], shade(col, 0.7))
    L.poly([(cx + rw / 2 + 4, ybot - h - 6), (cx + rw / 2 + 16, ybot - h - 16), (cx + rw / 2 + 2, ybot - h + 3)], shade(col, 0.7))


def hall(L, rng, cx, base, w, hh, roof_w, roof_h):
    """단청을 입힌 전각."""
    L.rect(cx - w / 2 - 22, base - 14, cx + w / 2 + 22, base + 26, (150, 140, 125))
    L.rect(cx - w / 2 - 22, base - 14, cx + w / 2 + 22, base - 9, (175, 165, 150))
    top = base - 14 - hh
    L.rect(cx - w / 2, top, cx + w / 2, base - 14, (205, 165, 110))
    n = max(3, int(w / 62))
    for i in range(n + 1):
        x = cx - w / 2 + i * w / n
        L.rect(x - 5, top, x + 5, base - 14, (165, 48, 40))
        if i < n:
            for j in range(3):
                yy = top + 14 + j * (hh - 22) / 3
                L.rect(x + 12, yy, x + w / n - 12, yy + (hh - 30) / 3, (190, 140, 85))
                L.light_rect(x + 14, yy + 2, x + w / n - 14, yy + (hh - 34) / 3, (255, 190, 120), 0.1)
    L.rect(cx - w / 2 - 10, top - 16, cx + w / 2 + 10, top, (45, 125, 110))
    pal = [(220, 75, 60), (240, 200, 80), (70, 150, 205), (245, 245, 235)]
    x = cx - w / 2 - 8
    i = 0
    while x < cx + w / 2 + 6:
        L.rect(x, top - 12, x + 7, top - 4, pal[i % 4])
        x += 11
        i += 1
    kroof(L, cx, top - 12, roof_w, roof_h, (66, 72, 86))


def pine(L, rng, x, base, hgt, col=(38, 72, 50)):
    lean = rng.uniform(-0.25, 0.25)
    top = (x + lean * hgt, base - hgt)
    mid = (x + lean * hgt * 0.4 + rng.uniform(-8, 8), base - hgt * 0.5)
    L.line([(x, base), mid, top], (85, 60, 45), max(3, hgt * 0.05))
    for i in range(6):
        f = 0.35 + i * 0.13
        cx = lerp(x, top[0], f) + rng.uniform(-hgt * 0.15, hgt * 0.15)
        cy = lerp(base, top[1], f)
        rx = hgt * rng.uniform(0.14, 0.24) * (1.2 - f * 0.5)
        L.ellipse(cx, cy, rx, rx * 0.42, shade(col, rng.uniform(0.85, 1.15)))


def rocks(L, rng, pts_top, ybot, col):
    fill_below(L, pts_top, ybot, col)
    for _ in range(int(len(pts_top) * 1.2)):
        x, y = rng.choice(pts_top)
        w = rng.uniform(20, 70)
        hgt = rng.uniform(10, 40)
        yy = y + rng.uniform(4, max(6, (ybot - y) * 0.8))
        c = shade(col, rng.uniform(0.75, 1.25))
        L.poly([(x - w / 2, yy + hgt / 2), (x - w * 0.3, yy - hgt / 2), (x + w * 0.35, yy - hgt * 0.4),
                (x + w / 2, yy + hgt / 2)], c)


# ───────────────────────────── 스프라이트 / 입자 ─────────────────────────────

def render_sprite(w, h, draw_fn, ss_=4):
    w, h = max(2, int(round(w))), max(2, int(round(h)))
    im = Image.new("RGBA", (w * ss_, h * ss_), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im), ss_)
    arr = np.asarray(im, np.float32) / 255.0
    a = arr[..., 3:4]
    pm = cv2.resize(arr[..., :3] * a, (w, h), interpolation=cv2.INTER_AREA)
    a = cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA)
    rgb = pm / np.maximum(a[..., None], 1e-4)
    return rgb.astype(np.float32), a.astype(np.float32)


def blend(img, rgb, a, x, y, op=1.0):
    h, w = a.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(img.shape[1], x + w), min(img.shape[0], y + h)
    if x0 >= x1 or y0 >= y1:
        return
    sa = a[y0 - y:y1 - y, x0 - x:x1 - x][..., None] * op
    src = rgb if np.ndim(rgb) == 1 else rgb[y0 - y:y1 - y, x0 - x:x1 - x]
    reg = img[y0:y1, x0:x1]
    reg *= (1 - sa)
    reg += src * sa


KERN = [(0, 0, 1.0), (-1, 0, 0.45), (1, 0, 0.45), (0, -1, 0.45), (0, 1, 0.45),
        (-1, -1, 0.18), (1, -1, 0.18), (-1, 1, 0.18), (1, 1, 0.18)]


def splat(img, xs, ys, cols):
    if len(xs) == 0:
        return
    xi = np.round(xs).astype(np.int32)
    yi = np.round(ys).astype(np.int32)
    for dx, dy, wgt in KERN:
        X, Y = xi + dx, yi + dy
        m = (X >= 0) & (X < W) & (Y >= 0) & (Y < H)
        np.add.at(img, (Y[m], X[m]), cols[m] * wgt)


_gull_cache = {}


def gull_sprite(size, phase):
    key = (round(size, 1), phase)
    if key not in _gull_cache:
        f = math.sin(phase / 12 * 2 * math.pi)
        wpx, hpx = size * S * 2.2, size * S * 1.2

        def draw(d, k):
            cx, cy = wpx * k / 2, hpx * k / 2
            sx, sy = size * S * k, size * S * k
            pts = [(cx - sx, cy + sy * (0.05 - 0.35 * f)), (cx - sx * 0.45, cy - sy * (0.15 + 0.25 * f)),
                   (cx, cy + sy * 0.12), (cx + sx * 0.45, cy - sy * (0.15 + 0.25 * f)),
                   (cx + sx, cy + sy * (0.05 - 0.35 * f))]
            d.line(pts, fill=(255, 255, 255, 255), width=max(2, int(size * S * k * 0.16)), joint="curve")
        _gull_cache[key] = render_sprite(wpx, hpx, draw)
    return _gull_cache[key]


class Gulls:
    def __init__(self, rng, n, region, size=(9, 16), speed=(40, 80)):
        x0, y0, x1, y1 = region
        self.b = []
        for _ in range(n):
            d = rng.choice([-1, 1])
            self.b.append((rng.uniform(x0, x1), rng.uniform(y0, y1), d * rng.uniform(*speed),
                           rng.uniform(-6, 6), rng.uniform(*size), rng.uniform(0, 12), rng.uniform(5, 8)))

    def draw(self, img, lt, env):
        col = np.array([0.16, 0.16, 0.20], np.float32) + 0.22 * env.amb
        for x, y, vx, vy, sz, ph, fl in self.b:
            px = ((x + vx * lt + 200) % 2320) - 200
            py = y + vy * lt + 6 * math.sin(lt * 0.9 + ph)
            phase = int((ph + lt * fl) % 12)
            rgb, a = gull_sprite(sz, phase)
            blend(img, col, a, px * S - a.shape[1] / 2, py * S - a.shape[0] / 2)


_noise_cache = {}


def foam_tex():
    if "foam" not in _noise_cache:
        rng = np.random.default_rng(7)
        n = rng.random((H // 2, W // 2)).astype(np.float32)
        n = cv2.GaussianBlur(n, (0, 0), 1.2)
        n = (n - n.min()) / (n.max() - n.min())
        _noise_cache["foam"] = cv2.resize(np.clip(n * 1.6 - 0.2, 0, 1), (W, H))
    return _noise_cache["foam"]


def foam(img, edge, colmask, lt, env, run=16, direction=1, waves=2, speed=0.2, strength=0.9):
    """해안선(edge, 픽셀 y 배열)에 밀려왔다 빠지는 파도 거품."""
    lo = int(max(0, edge.min() - (run + 14) * S))
    hi = int(min(H, edge.max() + (run + 14) * S))
    if hi <= lo:
        return
    Y = np.arange(lo, hi, dtype=np.float32)[:, None]
    E = edge[None, :]
    X = np.arange(W, dtype=np.float32)[None, :]
    tex = np.roll(foam_tex()[lo:hi], int(lt * 6 * S), axis=1)
    total = np.exp(-((Y - E) / (2.2 * S)) ** 2) * 0.55 * tex
    for i in range(waves):
        cyc = (lt * speed + i / waves) % 1
        reach = run * S * math.sin(math.pi * cyc)
        front = E + direction * (reach + 3 * S * np.sin(X * 0.011 / S + i * 2.1 + lt * 0.6))
        line = np.exp(-((Y - front) / (2.6 * S)) ** 2) * (1 - 0.55 * cyc) * (0.4 + 0.8 * tex)
        between = (((Y - E) * direction) > 0) & (((front - Y) * direction) > 0)
        wash = between * (0.3 * (1 - cyc)) * (0.5 + 0.5 * tex)
        total = np.maximum(total, np.maximum(line, wash))
    total = np.clip(total, 0, 1) * colmask[None, :] * strength
    col = np.array([0.88, 0.93, 0.96], np.float32) * env.amb * 1.02 + 0.02
    reg = img[lo:hi]
    reg *= (1 - total[..., None])
    reg += col * total[..., None]


# ───────────────────────────── 장면 ─────────────────────────────

class Scene:
    def __init__(self, key, ko, en, caption, t0, t1):
        self.key, self.ko, self.en, self.caption, self.t0, self.t1 = key, ko, en, caption, t0, t1
        self.hz = None
        self.sky_h = 600
        self.sun_x = (960, 960)
        self.moon_pos = None
        self.back = self.front = None
        self.anim_sky = self.anim_back = self.anim_front = None
        self.cloud_n = 5
        self.cloud_alpha = 0.8
        self.cloud_speed = 6
        self.zoom = (1.0, 1.06)
        self.focus = (0.5, 0.55)

    # 하늘 장식(구름/별) 및 물결 지도 미리 계산
    def prepare(self, seed):
        rng = np.random.default_rng(seed)
        sky_px = int(self.sky_h * S)
        n = 600
        self.st_x = rng.integers(0, W, n)
        self.st_y = (rng.random(n) ** 1.4 * sky_px * 0.92).astype(np.int32)
        self.st_b = (rng.random(n) ** 3 * 0.9 + 0.1).astype(np.float32)
        self.st_ph = rng.random(n) * 6.28
        # 구름
        q = 4
        cm = Image.new("L", (W // q + 1, H // q + 1), 0)
        d = ImageDraw.Draw(cm)
        r2 = random.Random(seed)
        for _ in range(self.cloud_n):
            cx = r2.uniform(0, W / q)
            cy = r2.uniform(0.12, 0.62) * sky_px / q
            ln = r2.uniform(120, 360) * S / q
            for _ in range(14):
                ex = cx + r2.uniform(-ln / 2, ln / 2)
                ey = cy + r2.uniform(-10, 6) * S / q
                rx = r2.uniform(25, 70) * S / q
                ry = rx * r2.uniform(0.25, 0.45)
                d.ellipse([ex - rx, ey - ry, ex + rx, ey + ry], fill=int(r2.uniform(120, 230)))
        cmn = np.asarray(cm, np.float32) / 255.0
        cmn = cv2.GaussianBlur(cmn, (0, 0), 2.2 * S + 0.4)
        self.clouds = cv2.resize(cmn, (W, H))[:sky_px] * self.cloud_alpha
        # 물결 지도
        if self.hz is not None:
            hzp = int(self.hz * S)
            self.hzp = hzp
            rows = H - hzp
            X = np.tile(np.arange(W, dtype=np.float32)[None, :], (rows, 1))
            D = np.tile(np.arange(rows, dtype=np.float32)[:, None], (1, W))
            Dd = D / S
            k = 60.0 / (Dd + 20.0)
            self.w_X = X
            self.w_A = (X / S * 0.013 * k + Dd * 0.5).astype(np.float32)
            self.w_B = (X / S * 0.031 * k + Dd * 0.9).astype(np.float32)
            self.w_amp = ((1.2 + Dd * 0.025) * S).astype(np.float32)
            self.w_C = (((Dd + 1) ** 0.75) * 1.6 + 0.8 * np.sin(X / S * 0.004 + Dd * 0.01)).astype(np.float32)
            self.w_my = (hzp - 1 - D * 0.985).astype(np.float32)
            self.w_fres = lerp(0.84, 0.45, (np.arange(rows, dtype=np.float32) / rows) ** 0.7)[:, None, None]
            self.w_wid = ((18 + Dd * 0.55) * S).astype(np.float32)
            self.w_N = rng.random((rows, W)).astype(np.float32)
            self.w_N2 = cv2.GaussianBlur(rng.random((rows, W)).astype(np.float32), (0, 0), 6 * S + 1)
            self.w_N2 = (self.w_N2 - self.w_N2.min()) / (np.ptp(self.w_N2) + 1e-6)

    # ── 하늘 ──
    def sky(self, ctx):
        env = ctx.env
        sky_px = self.sky_h * S
        y = np.arange(H, dtype=np.float32)
        f = np.clip(y / sky_px, 0, 1) ** 0.85
        col = env.top[None, :] * (1 - f[:, None]) + env.hor[None, :] * f[:, None]
        img = np.repeat(col[:, None, :], W, axis=1)

        sx = lerp(self.sun_x[0], self.sun_x[1], ctx.p) * S
        sy = sky_px - env.alt * (sky_px - 90 * S)
        ctx.sun = (sx, sy)
        # 해 뜨고 질 무렵 지평선 노을 띠
        low = (1 - ss(0.0, 0.35, env.alt)) * ss(-0.30, -0.02, env.alt)
        if low > 0.002:
            gx = np.exp(-((np.arange(W, dtype=np.float32) - sx) / (750 * S)) ** 2)
            gy = np.exp(-np.maximum(0, sky_px - y) / (250 * S))
            img += (low * 0.5) * gy[:, None, None] * gx[None, :, None] * env.sun_col
        # 해
        if env.sun_vis > 0.002 and sy < sky_px + 60 * S:
            R = int(620 * S)
            x0, x1 = int(max(0, sx - R)), int(min(W, sx + R))
            y0, y1 = int(max(0, sy - R)), int(min(H, sy + R))
            if x1 > x0 and y1 > y0:
                yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
                dd = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2) / S
                glow = 0.55 * np.exp(-dd / 60) + 0.22 * np.exp(-dd / 230)
                disk = np.clip((38 - dd) / 1.6 + 0.5, 0, 1)
                core = env.sun_col * 0.35 + np.array([0.75, 0.68, 0.55], np.float32)
                img[y0:y1, x0:x1] += (glow[..., None] * env.sun_col + disk[..., None] * core * 0.9) * env.sun_vis
        # 별
        if env.star > 0.01:
            tw = 0.65 + 0.35 * np.sin(ctx.t * 2.3 + self.st_ph)
            v = (self.st_b * tw * env.star)[:, None] * np.array([0.95, 0.97, 1.0], np.float32)
            img[self.st_y, self.st_x] += v
        # 달
        if self.moon_pos and env.moon > 0.01:
            mx, my = self.moon_pos[0] * S, self.moon_pos[1] * S
            R = int(260 * S)
            x0, x1, y0, y1 = int(max(0, mx - R)), int(min(W, mx + R)), int(max(0, my - R)), int(min(H, my + R))
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            dd = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2) / S
            d2 = np.sqrt((xx - mx + 13 * S) ** 2 + (yy - my + 6 * S) ** 2) / S
            disk = np.clip((30 - dd) / 1.4 + 0.5, 0, 1) * (1 - 0.9 * np.clip((27 - d2) / 1.4 + 0.5, 0, 1))
            glow = 0.16 * np.exp(-dd / 45) + 0.06 * np.exp(-dd / 160)
            mc = np.array([1.0, 0.96, 0.85], np.float32)
            img[y0:y1, x0:x1] += (disk[..., None] * 1.1 + glow[..., None]) * mc * env.moon
        # 구름
        sky_rows = self.clouds.shape[0]
        cm = np.roll(self.clouds, int(ctx.lt * self.cloud_speed * S), axis=1)[..., None]
        lum = float(np.mean(env.amb))
        ccol = env.hor * 0.5 + np.array([1.0, 1.0, 1.0], np.float32) * min(1.0, lum) * 0.55
        ccol = ccol * (0.55 + 0.45 * min(1.0, lum * 1.4))
        reg = img[:sky_rows]
        reg *= (1 - cm)
        reg += ccol * cm
        return img

    # ── 바다 ──
    def water(self, img, ctx):
        env, t = ctx.env, ctx.t
        hzp = self.hzp
        dx = self.w_amp * (np.sin(self.w_A + t * 1.8) + 0.5 * np.sin(self.w_B - t * 1.2))
        mapx = self.w_X + dx
        mapy = self.w_my + self.w_amp * 0.5 * np.sin(self.w_B * 0.7 + t * 1.5)
        refl = cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        refl = cv2.GaussianBlur(refl, (1, odd(9 * S)), 0)
        deep = np.array([0.04, 0.16, 0.24], np.float32) * env.amb + env.hor * 0.08
        wat = refl * self.w_fres + deep * (1 - self.w_fres)
        wat *= (1 + 0.035 * np.sin(self.w_C + t * 1.4) * (0.6 + 0.8 * self.w_N2))[..., None]
        sx, sy = ctx.sun
        sources = []
        if env.sun_vis > 0.01 and sy < hzp:
            sources.append((sx, env.sun_col * 1.7 * env.sun_vis, 0.86))
        if self.moon_pos and env.moon > 0.01:
            sources.append((self.moon_pos[0] * S, np.array([0.8, 0.82, 0.9], np.float32) * 0.9 * env.moon, 0.9))
        if sources:
            N = np.roll(self.w_N, int(t * 30 * S) % W, axis=1)
            for x, col, thr in sources:
                g = np.exp(-((self.w_X - x) / self.w_wid) ** 2)
                spark = g * np.clip((N - thr) * 7, 0, 1)
                wat += (spark[..., None] + g[..., None] * 0.07) * col
        img[hzp:] = wat

    def render(self, ctx):
        img = self.sky(ctx)
        if self.anim_sky:
            self.anim_sky(img, ctx)
        if self.back:
            self.back.apply(img, ctx.env)
        if self.anim_back:
            self.anim_back(img, ctx)
        if self.hz is not None:
            self.water(img, ctx)
        if self.front:
            self.front.apply(img, ctx.env)
        if self.anim_front:
            self.anim_front(img, ctx)
        z = lerp(self.zoom[0], self.zoom[1], ease(ctx.p))
        cx, cy = self.focus[0] * W, self.focus[1] * H
        M = np.array([[z, 0, cx * (1 - z)], [0, z, cy * (1 - z)]], np.float32)
        return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


class Ctx:
    def __init__(self, sc, t):
        self.t = t
        self.h = hour_at(t)
        self.env = Env(self.h)
        self.lt = t - sc.t0
        self.p = clamp01((t - sc.t0) / (sc.t1 - sc.t0))
        self.sun = (0, 0)


def edge_array(fn):
    xs = np.arange(W, dtype=np.float32) / S
    return np.array([fn(x) for x in xs], np.float32) * S


# ── 1. 해운대 해수욕장 (새벽) ──
def build_haeundae(sc):
    rng = random.Random(11)
    sc.hz = sc.sky_h = 610
    sc.sun_x = (1000, 1040)
    sc.cloud_n = 6
    far = Layer(0.62)
    fill_below(far, ridge(rng, 980, 1940, 548, 26), 612, (70, 85, 100))
    mid = Layer(0.38)
    x = 1150
    while x < 1940:
        w = rng.uniform(40, 95)
        building(mid, rng, x, x + w, rng.uniform(430, 545), 612, mixc((150, 160, 175), (200, 195, 185), rng.random()),
                 win=(4, 6, 5, 6), density=0.55)
        x += w + rng.uniform(-12, 3)
    lct = Layer(0.22)
    for cx, w, top in [(1430, 80, 168), (1532, 66, 225), (1626, 72, 140)]:
        lct.poly([(cx - w / 2, top + 34), (cx + w / 2, top), (cx + w / 2, 612), (cx - w / 2, 612)], (118, 136, 158))
        lct.poly([(cx + w * 0.18, top + 11), (cx + w / 2, top), (cx + w / 2, 612), (cx + w * 0.18, 612)], (98, 114, 135))
        y = top + 44
        while y < 600:
            for i in range(6):
                xx = cx - w / 2 + 6 + i * (w - 10) / 6
                if rng.random() < 0.6:
                    lct.light_rect(xx, y, xx + (w - 10) / 6 - 4, y + 4, rng.choice(WARM), rng.uniform(0, 0.9))
            y += 9
    sc.lct_tops = [(1430 + 40 - 6, 172), (1532 + 33 - 6, 229), (1626 + 36 - 6, 144)]
    isl = Layer(0.16)
    pts = dome(rng, -60, 470, 612, 92, rough=7)
    fill_below(isl, pts, 614, (40, 72, 52))
    canopy(isl, pts, rng, [(36, 66, 48), (48, 84, 58), (30, 58, 42)], size=16, density=0.8)
    isl.rect(318, 552, 418, 586, (196, 186, 166))
    isl.poly([(305, 556), (368, 532), (432, 556)], (90, 82, 70))
    isl.light_rect(326, 562, 410, 574, (255, 210, 150), 0.2)
    fg = Layer(0.0)
    shore = lambda x: 806 - 46 * (x / 1920) + 9 * math.sin(x / 260)
    pts = [(x, shore(x)) for x in range(-20, 1960, 10)]
    fill_below(fg, pts, 1080, (212, 188, 150))
    fill_below(fg, [(x, y + 2) for x, y in pts], 1080, (170, 145, 115))
    fill_below(fg, [(x, y + 22) for x, y in pts], 1080, (200, 176, 140))
    fill_below(fg, [(x, y + 45) for x, y in pts], 1080, (214, 192, 155))
    for _ in range(260):
        x = rng.uniform(0, 1920)
        y = rng.uniform(shore(x) + 50, 1080)
        fg.ellipse(x, y, rng.uniform(2, 6), rng.uniform(1, 2.5), (190, 166, 130))
    sc.back = Group([far, mid, lct, isl])
    sc.front = Group([fg])
    edge = edge_array(shore)
    colmask = np.ones(W, np.float32)
    gulls = Gulls(rng, 5, (300, 260, 1500, 470), size=(8, 14))

    def anim_back(img, ctx):
        if ctx.env.night > 0.05:
            on = (ctx.t * 0.9) % 1 < 0.5
            if on:
                xs = np.array([p[0] for p in sc.lct_tops], np.float32) * S
                ys = np.array([p[1] for p in sc.lct_tops], np.float32) * S
                splat(img, xs, ys, np.tile(np.array([[1.6, 0.15, 0.1]], np.float32) * ctx.env.night, (len(xs), 1)))
        gulls.draw(img, ctx.lt, ctx.env)

    def anim_front(img, ctx):
        foam(img, edge, colmask, ctx.lt, ctx.env, run=22, direction=1, waves=2, speed=0.16)
        e2 = edge - 28 * S
        foam(img, e2, colmask, ctx.lt + 1.7, ctx.env, run=6, direction=1, waves=1, speed=0.22, strength=0.45)

    sc.anim_back, sc.anim_front = anim_back, anim_front


# ── 2. 해동용궁사 (아침) ──
def build_yonggungsa(sc):
    rng = random.Random(22)
    sc.hz = sc.sky_h = 600
    sc.sun_x = (1470, 1430)
    sc.cloud_n = 5
    sc.focus = (0.42, 0.55)
    far = Layer(0.6)
    fill_below(far, dome(rng, 1600, 2000, 602, 50, rough=4), 604, (80, 95, 105))
    cliff_pts = [(-20, 500), (150, 506), (300, 528), (420, 552), (560, 572), (720, 590), (880, 604), (980, 626),
                 (1060, 655), (1150, 702), (1250, 760), (1350, 820), (1500, 868), (1700, 900), (1940, 930)]
    fine = []
    for (x0, y0), (x1, y1) in zip(cliff_pts, cliff_pts[1:]):
        n = max(2, int((x1 - x0) / 10))
        for i in range(n):
            u = i / n
            fine.append((lerp(x0, x1, u), lerp(y0, y1, u) + rng.uniform(-3, 3)))
    fine.append(cliff_pts[-1])
    sc.cliff_fn = lambda x: np.interp(x, [p[0] for p in cliff_pts], [p[1] for p in cliff_pts])
    land = Layer(0.06)
    rocks(land, rng, fine, 1080, (112, 98, 84))
    for _ in range(40):
        x = rng.uniform(0, 1900)
        y = sc.cliff_fn(x) + rng.uniform(30, 300)
        land.line([(x, y), (x + rng.uniform(40, 140), y + rng.uniform(-10, 18))], (88, 76, 66), 2)
    # 계단
    for i in range(16):
        x = 1080 + i * 18
        y = sc.cliff_fn(x) + 6
        land.rect(x, y, x + 26, y + 6, (182, 172, 156))
        land.rect(x, y + 6, x + 26, y + 9, (140, 130, 118))
    temple = Layer(0.04)
    # 석탑
    px, pb = 300, 530
    temple.rect(px - 46, pb - 22, px + 46, pb + 6, (168, 160, 150))
    y = pb - 22
    for i, (bw, bh) in enumerate([(54, 46), (44, 26), (36, 22)]):
        temple.rect(px - bw / 2, y - bh, px + bw / 2, y, (178, 170, 160))
        temple.rect(px + bw * 0.15, y - bh, px + bw / 2, y, (150, 143, 134))
        ry = y - bh
        rw = bw + 34 - i * 6
        temple.poly([(px - rw / 2, ry + 2), (px - rw / 2 - 4, ry - 6), (px - bw * 0.35, ry - 12), (px + bw * 0.35, ry - 12),
                     (px + rw / 2 + 4, ry - 6), (px + rw / 2, ry + 2)], (140, 134, 126))
        y = ry - 12
    temple.rect(px - 3, y - 40, px + 3, y, (120, 112, 104))
    for k in range(4):
        temple.ellipse(px, y - 8 - k * 8, 6, 3, (130, 122, 112))
    hall(temple, rng, 700, 585, 330, 90, 470, 96)
    hall(temple, rng, 1000, 622, 160, 56, 250, 62)
    trees = Layer(0.04)
    pine(trees, rng, 110, 505, 230)
    pine(trees, rng, 470, 556, 150)
    pine(trees, rng, 1170, 712, 170)
    pine(trees, rng, 1290, 790, 120)
    # 연등 줄
    lan = Layer(0.0)
    lantern_cols = [(225, 60, 70), (245, 205, 70), (240, 120, 160), (80, 180, 120), (90, 150, 230), (245, 150, 60)]
    for (ax, ay), (bx, by), sag in [((-20, 300), (1180, 420), 90), ((-20, 380), (900, 470), 60)]:
        pts = []
        for i in range(81):
            u = i / 80
            pts.append((lerp(ax, bx, u), lerp(ay, by, u) + sag * 4 * u * (1 - u)))
        lan.line(pts, (60, 50, 45), 1.6)
        for i in range(2, 80, 3):
            x, y = pts[i]
            c = lantern_cols[(i // 3) % len(lantern_cols)]
            lan.line([(x, y), (x, y + 8)], (60, 50, 45), 1.2)
            lan.ellipse(x, y + 20, 10, 13, c)
            lan.ellipse(x - 3, y + 16, 3, 5, shade(c, 1.25))
            lan.rect(x - 6, y + 32, x + 6, y + 36, (240, 220, 160))
            lan.light_ellipse(x, y + 20, 8, 11, shade(c, 1.15), 0.0)
    sc.back = Group([far])
    sc.front = Group([land, temple, trees, lan])
    edge = edge_array(lambda x: sc.cliff_fn(x) - 1)
    colmask = (np.arange(W) / S > 930).astype(np.float32)
    gulls = Gulls(rng, 4, (900, 250, 1800, 480), size=(9, 15))

    def anim_back(img, ctx):
        gulls.draw(img, ctx.lt, ctx.env)

    def anim_front(img, ctx):
        foam(img, edge, colmask, ctx.lt, ctx.env, run=12, direction=-1, waves=3, speed=0.25)

    sc.anim_back, sc.anim_front = anim_back, anim_front


# ── 3. 감천문화마을 (오전) ──
def build_gamcheon(sc):
    rng = random.Random(33)
    sc.hz = None
    sc.sky_h = 470
    sc.sun_x = (1500, 1560)
    sc.cloud_n = 7
    sc.focus = (0.6, 0.5)
    far = Layer(0.62)
    fill_below(far, dome(rng, -40, 780, 470, 46, rough=4), 520, (95, 110, 120))
    sea = Layer(0.45)
    sea.rect(-20, 466, 820, 540, (90, 140, 170))
    for i in range(10):
        y = 470 + i * 7
        sea.line([(-20, y), (820, y)], (110, 160, 190), 1)
    mtn = Layer(0.45)
    pts = ridge(rng, 420, 1940, 330, 40, wl=900)
    pts = [(x, y + max(0, 520 - x) * 0.5) for x, y in pts]
    fill_below(mtn, pts, 700, (78, 108, 86))
    canopy(mtn, pts, rng, [(70, 100, 80), (86, 118, 92)], size=14, density=0.6)
    palette = [(243, 168, 178), (250, 220, 118), (128, 198, 222), (160, 214, 168), (200, 170, 230),
               (246, 244, 236), (242, 150, 112), (110, 168, 212), (255, 196, 140), (150, 220, 210)]
    rows = 16
    layers = [far, sea, mtn]
    for g in range(0, rows, 2):
        f_mid = (g + 1) / (rows - 1)
        L = Layer(lerp(0.4, 0.0, f_mid ** 0.8))
        for r in (g, g + 1):
            f = r / (rows - 1)
            hh = lerp(22, 118, f ** 1.35)
            ry = lerp(470, 1010, f ** 1.18)
            x = rng.uniform(-80, -10)
            while x < 1960:
                w = hh * rng.uniform(0.9, 1.9)
                xc = x + w / 2
                yb = ry - (xc - 760) * 0.13 * (1 - f * 0.55)
                top = yb - hh
                c = shade(rng.choice(palette), rng.uniform(0.9, 1.05))
                L.rect(x, top, x + w, yb + hh * 0.6, c)
                L.rect(x + w * 0.78, top, x + w, yb + hh * 0.6, shade(c, 0.86))
                L.rect(x - 1, top - hh * 0.05, x + w + 1, top + hh * 0.02, shade(c, 1.12))
                if rng.random() < 0.18:
                    L.poly([(x - hh * 0.05, top), (x + w / 2, top - hh * 0.32), (x + w + hh * 0.05, top)],
                           rng.choice([(200, 80, 60), (90, 120, 170), (220, 130, 70)]))
                elif rng.random() < 0.3:
                    tc = rng.choice([(70, 130, 205), (235, 190, 60)])
                    tx = x + rng.uniform(0.15, 0.6) * w
                    tw = hh * 0.22
                    L.rect(tx, top - tw * 0.9, tx + tw, top, tc)
                    L.ellipse(tx + tw / 2, top - tw * 0.9, tw / 2, tw * 0.18, shade(tc, 1.15))
                nwin = rng.randint(1, 3)
                for i in range(nwin):
                    wx = x + w * (0.15 + i * 0.28)
                    wy = top + hh * 0.3
                    if wx + hh * 0.18 < x + w * 0.95:
                        L.rect(wx, wy, wx + hh * 0.17, wy + hh * 0.22, (70, 82, 96))
                        L.light_rect(wx, wy, wx + hh * 0.17, wy + hh * 0.22, rng.choice(WARM), rng.uniform(0, 0.8))
                if rng.random() < 0.25:
                    dx = x + w * 0.6
                    L.rect(dx, yb - hh * 0.42, dx + hh * 0.16, yb, (120, 90, 70))
                x += w + rng.uniform(-hh * 0.15, hh * 0.25)
        layers.append(L)
    ledge = Layer(0.0)
    ledge.rect(-20, 945, 1940, 1080, (176, 168, 156))
    ledge.rect(-20, 928, 1940, 948, (212, 204, 190))
    ledge.rect(-20, 948, 1940, 956, (150, 142, 132))
    for x in range(0, 1940, 160):
        ledge.line([(x, 956), (x, 1080)], (160, 152, 140), 2)
    statue = Layer(0.0)
    # 사막여우
    fx = 1288
    statue.poly([(fx - 8, 930), (fx - 60, 922), (fx - 92, 932), (fx - 70, 940), (fx - 20, 938)], (205, 112, 48))
    statue.ellipse(fx - 88, 933, 10, 6, (245, 240, 230))
    statue.ellipse(fx, 900, 30, 32, (212, 118, 50))
    statue.ellipse(fx + 12, 902, 12, 26, (190, 100, 42))
    statue.ellipse(fx, 860, 20, 18, (214, 122, 54))
    statue.poly([(fx - 17, 856), (fx - 24, 822), (fx - 4, 846)], (200, 110, 46))
    statue.poly([(fx + 17, 856), (fx + 24, 822), (fx + 4, 846)], (200, 110, 46))
    statue.poly([(fx - 15, 852), (fx - 20, 830), (fx - 7, 847)], (120, 60, 40))
    statue.poly([(fx + 15, 852), (fx + 20, 830), (fx + 7, 847)], (120, 60, 40))
    # 어린왕자 (뒷모습)
    px = 1392
    statue.poly([(px - 52, 932), (px + 54, 932), (px + 40, 860), (px + 22, 818), (px - 22, 818), (px - 40, 860)], (70, 116, 98))
    statue.poly([(px + 8, 932), (px + 54, 932), (px + 40, 860), (px + 22, 818), (px + 6, 818)], (58, 98, 84))
    statue.line([(px, 822), (px, 930)], (52, 88, 76), 2)
    statue.poly([(px - 18, 818), (px + 22, 812), (px + 70, 790), (px + 118, 776), (px + 132, 792), (px + 100, 800),
                 (px + 66, 818), (px + 24, 834), (px - 16, 834)], (244, 196, 64))
    statue.poly([(px + 70, 790), (px + 118, 776), (px + 132, 792), (px + 100, 800)], (226, 172, 52))
    statue.ellipse(px, 784, 27, 30, (232, 196, 160))
    hair = []
    for i in range(15):
        a = math.pi + i / 14 * math.pi
        r = 36 if i % 2 == 0 else 27
        hair.append((px + math.cos(a) * r, 782 + math.sin(a) * r))
    statue.poly(hair + [(px + 27, 800), (px - 27, 800)], (238, 200, 88))
    statue.ellipse(px, 788, 28, 22, (238, 200, 88))
    sc.back = Group(layers)
    sc.front = Group([ledge, statue])
    gulls = Gulls(rng, 3, (100, 120, 1500, 330), size=(8, 13))

    def anim_back(img, ctx):
        gulls.draw(img, ctx.lt, ctx.env)

    sc.anim_back = anim_back


# ── 4. 블루라인파크 스카이캡슐 (오후) ──
def build_blueline(sc):
    rng = random.Random(44)
    sc.hz = sc.sky_h = 540
    sc.sun_x = (1430, 1600)
    sc.cloud_n = 6
    far = Layer(0.6)
    fill_below(far, dome(rng, 1520, 2000, 542, 44, rough=4), 544, (85, 100, 112))
    hill = Layer(0.12)
    hp = [(-20, 236), (200, 252), (420, 292), (640, 352), (840, 430), (1000, 518), (1120, 612), (1210, 690), (1300, 742)]
    fine = []
    for (x0, y0), (x1, y1) in zip(hp, hp[1:]):
        for i in range(8):
            u = i / 8
            fine.append((lerp(x0, x1, u), lerp(y0, y1, u) + rng.uniform(-4, 4)))
    fine.append(hp[-1])
    fill_below(hill, fine, 800, (62, 110, 64))
    for _ in range(14):
        x = rng.uniform(40, 760)
        y = np.interp(x, [p[0] for p in hp], [p[1] for p in hp])
        w = rng.uniform(40, 90)
        top = y - rng.uniform(30, 110)
        building(hill, rng, x, x + w, top, y + 50, mixc((236, 232, 222), (210, 200, 185), rng.random()),
                 win=(6, 8, 7, 9), density=0.5)
    trees = Layer(0.12)
    for _ in range(420):
        x = rng.uniform(-20, 1280)
        ytop = np.interp(x, [p[0] for p in hp], [p[1] for p in hp])
        y = rng.uniform(ytop + 20, 760)
        r = rng.uniform(10, 24)
        trees.ellipse(x, y, r * 1.2, r, rng.choice([(48, 92, 54), (62, 112, 62), (40, 80, 48), (74, 124, 70)]))
    canopy(trees, fine, rng, [(48, 92, 54), (62, 112, 62)], size=14, density=0.9, depth=0.3)
    rk = Layer(0.05)
    rtop = [(x, 742 + 18 * math.sin(x * 0.02) + rng.uniform(-6, 6)) for x in range(-20, 1340, 12)]
    rocks(rk, rng, rtop, 812, (126, 114, 102))
    rk.poly([(1290, 760), (1340, 742), (1380, 790), (1340, 814), (1280, 812)], (116, 104, 94))
    light = Layer(0.18)
    light.rect(1330, 600, 1580, 614, (176, 174, 168))
    light.rect(1650, 596, 1940, 610, (176, 174, 168))
    for lx, body, band in [(1545, (214, 60, 52), (240, 240, 236)), (1690, (242, 242, 238), (214, 60, 52))]:
        light.poly([(lx - 16, 602), (lx + 16, 602), (lx + 11, 520), (lx - 11, 520)], body)
        light.rect(lx - 13, 560, lx + 13, 568, band)
        light.rect(lx - 14, 516, lx + 14, 522, (70, 70, 74))
        light.rect(lx - 9, 500, lx + 9, 516, (120, 150, 170))
        light.poly([(lx - 12, 500), (lx, 488), (lx + 12, 500)], body)
        light.light_rect(lx - 7, 502, lx + 7, 514, (255, 120, 90) if body[0] > 230 and body[1] < 100 else (140, 255, 160), 0.0)
    rail = Layer(0.0)
    sc.rail = lambda u: (lerp(-40, 1960, u), lerp(712, 650, u))
    for i in range(16):
        x = -20 + i * 132
        _, y = sc.rail((x + 40) / 2000)
        rail.rect(x - 6, y, x + 6, 820, (196, 198, 204))
        rail.rect(x + 2, y, x + 6, 820, (160, 162, 170))
    rail.poly([(-40, 712), (1960, 650), (1960, 664), (-40, 728)], (78, 84, 96))
    rail.poly([(-40, 709), (1960, 647), (1960, 651), (-40, 713)], (176, 182, 192))
    for i in range(70):
        u = i / 70
        x, y = sc.rail(u)
        rail.light_ellipse(x, y + 10, 2.2, 2.2, (120, 200, 255), 0.0)
    sc.back = Group([far])
    sc.front = Group([hill, trees, light, rk, rail])
    edge = edge_array(lambda x: (np.interp(x, [p[0] for p in rtop], [p[1] for p in rtop]) + 70) if x < 1330 else 1e4)
    colmask = (np.arange(W) / S < 1320).astype(np.float32)
    edge = np.where(colmask > 0, edge, 812 * S).astype(np.float32)
    caps = {}
    cap_cols = [(232, 72, 72), (248, 200, 60), (90, 200, 170), (70, 140, 230), (240, 130, 180)]
    cw, ch = 58, 50
    for c in cap_cols:
        def draw(d, k, c=c):
            s = S * k
            d.rounded_rectangle([2 * s, 4 * s, (cw - 2) * s, (ch - 6) * s], radius=12 * s, fill=c + (255,))
            d.rounded_rectangle([7 * s, 11 * s, (cw - 7) * s, 28 * s], radius=6 * s, fill=(60, 82, 112, 255))
            d.polygon([(10 * s, 12 * s), (22 * s, 12 * s), (14 * s, 27 * s), (8 * s, 27 * s)], fill=(140, 170, 200, 255))
            d.rectangle([2 * s, 32 * s, (cw - 2) * s, 35 * s], fill=shade(c, 0.8) + (255,))
            d.rectangle([12 * s, (ch - 7) * s, (cw - 12) * s, (ch - 2) * s], fill=(50, 52, 60, 255))
        rgb, a = render_sprite(cw * S, ch * S, draw)
        win = np.zeros_like(a)
        win[int(11 * S):int(28 * S), int(7 * S):int((cw - 7) * S)] = 1
        caps[c] = (rgb, a, win * a)
    gulls = Gulls(rng, 4, (700, 160, 1800, 420), size=(9, 15))

    def anim_back(img, ctx):
        gulls.draw(img, ctx.lt, ctx.env)

    def anim_front(img, ctx):
        foam(img, edge, colmask, ctx.lt, ctx.env, run=10, direction=-1, waves=3, speed=0.24, strength=0.8)
        for i, c in enumerate(cap_cols * 2):
            u = (i / 10 + ctx.t * 0.012) % 1.05 - 0.02
            x, y = sc.rail(u)
            rgb, a, win = caps[c]
            lit = rgb * ctx.env.amb + win[..., None] * np.array([1.0, 0.8, 0.5], np.float32) * ctx.env.night
            blend(img, lit, a, x * S - a.shape[1] / 2, (y - ch + 6) * S)

    sc.anim_back, sc.anim_front = anim_back, anim_front


# ── 5. 용두산공원 부산타워 · 자갈치 (노을) ──
def build_tower(sc):
    rng = random.Random(55)
    sc.hz = sc.sky_h = 760
    sc.sun_x = (340, 280)
    sc.cloud_n = 7
    sc.focus = (0.5, 0.45)
    isl = Layer(0.66)
    fill_below(isl, dome(rng, -40, 440, 762, 52, rough=5), 764, (80, 85, 105))
    mtn = Layer(0.55)
    mp = [(x, lerp(764, y, ss(380, 720, x))) for x, y in ridge(rng, 380, 1940, 500, 48, wl=800)]
    fill_below(mtn, mp, 764, (80, 95, 105))
    city = Layer(0.38)
    x = 420
    while x < 1940:
        w = rng.uniform(34, 80)
        building(city, rng, x, x + w, rng.uniform(560, 670), 764, mixc((170, 170, 175), (205, 195, 180), rng.random()),
                 win=(4, 5, 5, 6), density=0.6, thr=(0.0, 0.75))
        x += w + rng.uniform(-8, 2)
    park = Layer(0.14)
    pts = dome(rng, 760, 1360, 764, 168, rough=6)
    fill_below(park, pts, 764, (64, 104, 66))
    canopy(park, pts, rng, [(56, 96, 60), (74, 116, 70), (48, 84, 54)], size=18, density=0.9, depth=1.6)
    tw = Layer(0.1)
    tx = 1060
    tw.poly([(tx - 18, 604), (tx + 18, 604), (tx + 13, 246), (tx - 13, 246)], (226, 228, 232))
    tw.poly([(tx + 2, 604), (tx + 18, 604), (tx + 13, 246), (tx + 2, 246)], (196, 198, 206))
    tw.light_line([(tx - 4, 600), (tx - 4, 250)], (190, 220, 255), 3, 0.15)
    tw.rect(tx - 36, 232, tx + 36, 248, (210, 212, 218))
    tw.poly([(tx - 50, 232), (tx + 50, 232), (tx + 46, 188), (tx - 46, 188)], (232, 234, 238))
    tw.rect(tx - 47, 198, tx + 47, 222, (70, 92, 118))
    for i in range(15):
        tw.light_rect(tx - 45 + i * 6, 202, tx - 41 + i * 6, 218, (190, 215, 245), 0.05 + 0.02 * i)
    tw.poly([(tx - 36, 188), (tx + 36, 188), (tx + 26, 172), (tx - 26, 172)], (214, 216, 222))
    tw.rect(tx - 4, 100, tx + 4, 174, (200, 202, 208))
    tw.rect(tx - 1.5, 70, tx + 1.5, 102, (200, 202, 208))
    sc.tower_top = (tx, 70)
    near = Layer(0.18)
    x = 560
    while x < 1520:
        w = rng.uniform(40, 90)
        top = rng.uniform(650, 720)
        if not (930 < x < 1180):
            building(near, rng, x, x + w, top, 764, mixc((185, 180, 175), (220, 210, 196), rng.random()),
                     win=(5, 6, 6, 7), density=0.6, thr=(0.0, 0.7))
        x += w + rng.uniform(-6, 4)
    jg = Layer(0.08)
    jg.rect(470, 694, 930, 764, (160, 182, 196))
    for i in range(24):
        xx = 476 + i * 19
        jg.line([(xx, 698), (xx, 760)], (120, 140, 156), 2)
    for i in range(23):
        for j in range(4):
            if rng.random() < 0.7:
                xx = 480 + i * 19
                jg.light_rect(xx, 706 + j * 13, xx + 13, 714 + j * 13, shade(rng.choice(WARM), 0.75), rng.uniform(0, 0.6))
    for i in range(3):
        x0 = 460 + i * 160
        x1 = x0 + 160
        pts = []
        for j in range(25):
            u = j / 24
            pts.append((lerp(x0, x1, u), 692 - 36 * math.sin(math.pi * u) ** 0.8))
        back = [(x, y + 12 + 4 * math.sin(math.pi * (x - x0) / 160)) for x, y in reversed(pts)]
        jg.poly(pts + back, (246, 246, 244))
    cr = Layer(0.2)
    sc.crane_tops = []
    for cx in (1580, 1730, 1880):
        c = (196, 64, 52)
        cr.rect(cx - 40, 600, cx - 30, 764, c)
        cr.rect(cx + 30, 600, cx + 40, 764, c)
        cr.line([(cx - 35, 700), (cx + 35, 620)], c, 4)
        cr.line([(cx - 35, 620), (cx + 35, 700)], c, 4)
        cr.rect(cx - 170, 590, cx + 70, 604, (232, 232, 230))
        cr.rect(cx - 30, 570, cx + 30, 590, (232, 232, 230))
        cr.poly([(cx - 30, 590), (cx - 6, 520), (cx + 6, 520), (cx + 30, 590)], c)
        cr.line([(cx - 6, 524), (cx - 170, 592)], (200, 200, 200), 2)
        sc.crane_tops.append((cx, 520))
    quay = Layer(0.0)
    quay.rect(-20, 1018, 1940, 1080, (112, 106, 100))
    quay.rect(-20, 1012, 1940, 1022, (150, 144, 136))
    for x in range(150, 1920, 330):
        quay.rect(x - 12, 992, x + 12, 1014, (60, 58, 60))
        quay.ellipse(x, 992, 16, 6, (70, 68, 70))
    sc.back = Group([isl, mtn, city, park, near, tw, jg, cr])
    sc.front = Group([quay])

    def boat_draw(d, k):
        s = S * k
        d.polygon([(4 * s, 30 * s), (150 * s, 30 * s), (134 * s, 48 * s), (18 * s, 48 * s)], fill=(240, 240, 236, 255))
        d.rectangle([12 * s, 38 * s, 140 * s, 42 * s], fill=(40, 90, 170, 255))
        d.rectangle([70 * s, 8 * s, 118 * s, 30 * s], fill=(230, 230, 226, 255))
        d.rectangle([76 * s, 13 * s, 112 * s, 22 * s], fill=(70, 90, 110, 255))
        d.line([(92 * s, 8 * s), (92 * s, -0 * s)], fill=(80, 80, 80, 255), width=int(2 * s))
    boat = render_sprite(156 * S, 52 * S, boat_draw)
    gulls = Gulls(rng, 7, (200, 220, 1700, 520), size=(8, 14))

    def anim_back(img, ctx):
        if ctx.env.night > 0.05 and (ctx.t * 0.8) % 1 < 0.5:
            pts = [sc.tower_top] + sc.crane_tops
            xs = np.array([p[0] for p in pts], np.float32) * S
            ys = np.array([p[1] for p in pts], np.float32) * S
            splat(img, xs, ys, np.tile(np.array([[1.7, 0.15, 0.1]], np.float32) * ctx.env.night, (len(xs), 1)))

    def anim_front(img, ctx):
        bx = 1500 - ctx.lt * 70
        by = 880
        rgb, a = boat
        wy = int(by * S)
        if 0 < bx < 1900:
            Y = np.arange(wy - int(6 * S), min(H, wy + int(60 * S)), dtype=np.float32)[:, None]
            X = np.arange(W, dtype=np.float32)[None, :]
            behind = (X - (bx + 150) * S) / S
            spread = np.clip(behind, 0, None) * 0.22 + 2
            yy = (Y - (wy + 44 * S)) / S
            wake = (np.exp(-((np.abs(yy) - spread * 0.5) / 2.0) ** 2) * (behind > 0) * np.exp(-behind / 260))
            wake = np.clip(wake * 0.7, 0, 1)[..., None]
            col = np.array([0.9, 0.93, 0.96], np.float32) * ctx.env.amb
            reg = img[int(Y[0, 0]):int(Y[-1, 0]) + 1]
            reg *= (1 - wake)
            reg += col * wake
        blend(img, rgb * ctx.env.amb, a, bx * S, (by - 6) * S)
        gulls.draw(img, ctx.lt, ctx.env)

    sc.anim_back, sc.anim_front = anim_back, anim_front


# ── 6. 광안대교 드론쇼 (저녁) ──
def heart_points(rng, n):
    pts = []
    while len(pts) < n:
        x, y = rng.uniform(-1.3, 1.3), rng.uniform(-1.3, 1.4)
        if (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0:
            pts.append((x, -y))
    return np.array(pts, np.float32)


def text_points(rng, text, n, size):
    fnt = font("Black", size)
    bb = fnt.getbbox(text)
    im = Image.new("L", (bb[2] + 10, bb[3] + 10), 0)
    ImageDraw.Draw(im).text((5 - bb[0], 5), text, font=fnt, fill=255)
    m = np.asarray(im)
    ys, xs = np.nonzero(m > 128)
    idx = rng.choice(len(xs), n, replace=len(xs) < n)
    return np.stack([xs[idx] - m.shape[1] / 2, ys[idx] - m.shape[0] / 2], 1).astype(np.float32)


def build_gwangan(sc):
    rng = random.Random(66)
    nrng = np.random.default_rng(66)
    sc.hz = sc.sky_h = 640
    sc.moon_pos = (1380, 205)
    sc.cloud_n = 3
    sc.cloud_alpha = 0.5
    sc.zoom = (1.0, 1.04)
    left = Layer(0.5)
    pts = ridge(rng, -20, 980, 560, 30, wl=900)
    fill_below(left, pts, 642, (60, 72, 90))
    for _ in range(220):
        x = rng.uniform(0, 960)
        yt = np.interp(x, [p[0] for p in pts], [p[1] for p in pts])
        y = rng.uniform(yt + 6, 636)
        left.light_rect(x, y, x + 2.5, y + 2.5, rng.choice(WARM), rng.uniform(0, 0.8))
    sky = Layer(0.42)
    x = 960
    while x < 1940:
        w = rng.uniform(26, 60)
        tall = 1450 < x < 1780
        top = rng.uniform(300, 380) if tall else rng.uniform(430, 570)
        building(sky, rng, x, x + w, top, 642, mixc((120, 130, 150), (170, 170, 175), rng.random()),
                 win=(3, 4, 4, 5), density=0.7, thr=(0.0, 0.7), crown=(120, 220, 255) if tall else None)
        x += w + rng.uniform(-6, 3)
    br = Layer(0.1)
    deck = lambda x: lerp(580, 532, x / 1920)
    thick = lambda x: lerp(30, 18, x / 1920)
    for px in range(60, 1960, 190):
        br.rect(px - lerp(9, 6, px / 1920), deck(px) + thick(px), px + lerp(9, 6, px / 1920), 642, (110, 116, 128))
    towers = [(640, 300), (1260, 330)]
    for tx, ty in towers:
        br.poly([(tx - 13, 642), (tx + 13, 642), (tx + 9, ty), (tx - 9, ty)], (150, 156, 168))
        br.rect(tx - 14, ty - 6, tx + 14, ty + 6, (170, 176, 186))
    top_pts = [(x, deck(x)) for x in range(-40, 1980, 20)]
    bot_pts = [(x, deck(x) + thick(x)) for x in range(1980, -60, -20)]
    br.poly(top_pts + bot_pts, (128, 134, 146))
    for x in range(-40, 1960, 14):
        y = deck(x)
        t_ = thick(x)
        br.line([(x, y + t_ * 0.42), (x + 7, y + t_ * 0.9)], (95, 100, 112), 1.4)
        br.line([(x + 7, y + t_ * 0.42), (x + 14, y + t_ * 0.9)], (95, 100, 112), 1.4)

    def cable_y(x):
        (a, ay), (b, by) = towers
        if x < a:
            u = (x - 60) / (a - 60)
            return lerp(deck(60), ay, u ** 1.7)
        if x < b:
            u = (x - a) / (b - a)
            base = lerp(ay, by, u)
            return base + (deck(x) - 14 - lerp(ay, by, 0.5)) * 4 * u * (1 - u)
        u = (x - b) / (1860 - b)
        return lerp(by, deck(1860), u ** 0.6)

    cab = [(x, cable_y(x)) for x in range(60, 1862, 6)]
    br.line(cab, (180, 186, 196), 3)
    for x in range(70, 1860, 16):
        cy = cable_y(x)
        if deck(x) - cy > 4:
            br.line([(x, cy), (x, deck(x))], (160, 166, 178), 1.0)
    for x in range(0, 1920, 36):
        br.light_ellipse(x, deck(x) - 3, 2, 2, (255, 210, 140), 0.1)
    sand = Layer(0.0)
    shore = lambda x: 900 + 26 * math.sin(x / 520 + 0.6)
    sp = [(x, shore(x)) for x in range(-20, 1960, 10)]
    fill_below(sand, sp, 1080, (186, 166, 136))
    fill_below(sand, [(x, y + 3) for x, y in sp], 1080, (150, 128, 102))
    fill_below(sand, [(x, y + 26) for x, y in sp], 1080, (188, 168, 138))
    people = Layer(0.0)
    for (x, y, s) in [(560, 1000, 1.0), (604, 1004, 0.92), (1380, 975, 0.8)]:
        people.ellipse(x, y - 64 * s, 11 * s, 12 * s, (40, 40, 48))
        people.poly([(x - 20 * s, y), (x + 20 * s, y), (x + 15 * s, y - 50 * s), (x - 15 * s, y - 50 * s)], (44, 44, 54))
    sc.back = Group([left, sky, br])
    sc.front = Group([sand, people])
    # 다리 LED 지도
    mask_im = Image.new("L", (W * SS, H * SS), 0)
    md = ImageDraw.Draw(mask_im)
    k = S * SS
    md.line([(x * k, (y - 1) * k) for x, y in cab], fill=255, width=max(1, int(2.4 * k)))
    md.line([(x * k, (deck(x) + thick(x) - 2) * k) for x in range(-40, 1980, 20)], fill=200, width=max(1, int(2.6 * k)))
    for tx, ty in towers:
        md.line([(tx * k, ty * k), (tx * k, deck(tx) * k)], fill=180, width=max(1, int(2 * k)))
    m = cv2.resize(np.asarray(mask_im, np.float32) / 255.0, (W, H), interpolation=cv2.INTER_AREA)
    yi, xi = np.nonzero(m > 0.02)
    sc.led = (yi, xi, m[yi, xi].astype(np.float32), (xi / W).astype(np.float32))
    # 차량 불빛
    ncar = 46
    car_off = nrng.uniform(0, 2000, ncar)
    car_dir = nrng.choice([-1, 1], ncar)
    car_spd = nrng.uniform(90, 150, ncar)
    # 드론쇼
    N = 520
    launch = np.stack([nrng.uniform(700, 1220, N), nrng.uniform(600, 640, N)], 1).astype(np.float32)
    grid = np.stack([np.tile(np.linspace(640, 1280, 26), 20)[:N], np.repeat(np.linspace(150, 400, 20), 26)[:N]], 1)
    grid = grid.astype(np.float32) + nrng.normal(0, 2, (N, 2)).astype(np.float32)
    busan = text_points(nrng, "BUSAN", N, 190) + np.array([960, 270], np.float32)
    heart = heart_points(nrng, N) * np.array([150, 150], np.float32) + np.array([960, 285], np.float32)

    def order(P):
        return P[np.argsort(P[:, 0] + P[:, 1] * 0.001)]

    shapes = [order(launch), order(grid), order(busan), order(heart)]
    sc.drone_shapes = shapes
    drone_ph = nrng.uniform(0, 6.28, N).astype(np.float32)
    keys = [(0.6, 1.9), (2.4, 3.4), (4.6, 5.6)]  # (모핑 시작, 끝) 국소 시각
    cols = [np.array([0.9, 0.95, 1.3], np.float32), np.array([0.9, 0.95, 1.3], np.float32),
            np.array([0.6, 1.0, 1.6], np.float32), np.array([1.7, 0.45, 0.85], np.float32)]
    gulls = None

    def anim_back(img, ctx):
        env = ctx.env
        on = ss(18.7, 19.6, ctx.h)
        if on > 0.01:
            yi, xi, mv, xn = sc.led
            hue = (xn * 1.3 - ctx.t * 0.18) % 1.0
            rgb = np.stack([0.5 + 0.5 * np.cos(6.283 * hue), 0.5 + 0.5 * np.cos(6.283 * (hue - 0.333)),
                            0.5 + 0.5 * np.cos(6.283 * (hue - 0.667))], 1) ** 1.4
            img[yi, xi] += rgb * (mv * on * 1.5)[:, None]
            xs = (car_off + car_dir * car_spd * ctx.t) % 2000 - 40
            ys = np.array([deck(x) for x in xs], np.float32) + np.where(car_dir > 0, -2.0, 1.0)
            cc = np.where(car_dir[:, None] > 0, np.array([[1.4, 0.2, 0.15]]), np.array([[1.3, 1.25, 1.1]]))
            splat(img, xs * S, ys * S, (cc * on * 0.7).astype(np.float32))
        lt = ctx.lt
        if lt > 0.5:
            P = shapes[0]
            col = cols[0]
            for i, (a, b) in enumerate(keys):
                u = ease((lt - a) / (b - a))
                if lt >= a:
                    P = shapes[i] + (shapes[i + 1] - shapes[i]) * u
                    col = cols[i] + (cols[i + 1] - cols[i]) * u
            tw = 0.75 + 0.25 * np.sin(ctx.t * 5 + drone_ph)
            fade = ss(0.5, 1.0, lt)
            c = (tw[:, None] * col[None, :] * fade).astype(np.float32)
            splat(img, P[:, 0] * S, P[:, 1] * S, c)

    edge = edge_array(shore)
    colmask = np.ones(W, np.float32)

    def anim_front(img, ctx):
        foam(img, edge, colmask, ctx.lt, ctx.env, run=16, direction=1, waves=2, speed=0.15, strength=0.7)

    sc.anim_back, sc.anim_front = anim_back, anim_front


# ── 7. 마린시티 야경 + 불꽃 (밤) ──
FIREWORK_TIMES = [38.0, 38.7, 39.3, 39.9, 40.5, 41.0, 41.5, 42.0, 42.6]


def fireworks_list():
    rng = np.random.default_rng(77)
    pal = [(1.8, 0.5, 0.4), (1.7, 1.3, 0.5), (0.6, 1.2, 1.9), (1.6, 0.6, 1.5), (0.7, 1.8, 0.9), (1.9, 1.6, 1.2)]
    out = []
    for i, t0 in enumerate(FIREWORK_TIMES):
        n = 150
        ang = rng.uniform(0, 6.283, n)
        spd = rng.uniform(0.55, 1.0, n) ** 0.5
        out.append(dict(t0=t0, cx=rng.uniform(380, 1540), cy=rng.uniform(130, 260), col=np.array(pal[i % len(pal)], np.float32),
                        dx=np.cos(ang) * spd, dy=np.sin(ang) * spd, r=rng.uniform(150, 230), fl=rng.uniform(0, 6.28, n)))
    return out


def build_marine(sc):
    rng = random.Random(77)
    sc.hz = sc.sky_h = 660
    sc.moon_pos = (1640, 235)
    sc.cloud_n = 3
    sc.cloud_alpha = 0.4
    sc.zoom = (1.04, 1.0)
    far = Layer(0.55)
    pts = ridge(rng, -20, 1940, 560, 34, wl=1100)
    fill_below(far, pts, 662, (60, 70, 88))
    for _ in range(160):
        x = rng.uniform(0, 1920)
        yt = np.interp(x, [p[0] for p in pts], [p[1] for p in pts])
        y = rng.uniform(yt + 8, 650)
        far.light_rect(x, y, x + 2.5, y + 2.5, rng.choice(WARM), rng.uniform(0, 0.6))
    city = Layer(0.32)
    x = -20
    while x < 1940:
        w = rng.uniform(30, 70)
        building(city, rng, x, x + w, rng.uniform(470, 600), 662, mixc((110, 118, 135), (150, 150, 160), rng.random()),
                 win=(3, 4, 4, 5), density=0.75, thr=(0.0, 0.6))
        x += w + rng.uniform(-6, 3)
    mc = Layer(0.1)
    sc.tops = []
    for x0, w, top in [(300, 120, 310), (470, 132, 250), (640, 124, 335)]:
        right = [(x0 + w * (1 - s ** 2.4) + 6, lerp(662, top, s)) for s in np.linspace(0, 1, 30)]
        mc.poly([(x0, 662)] + right + [(x0, top + 10)], (88, 106, 128))
        mc.poly([(x0, 662), (x0 + w * 0.35, 662), (x0 + w * 0.35 * 0.6, top + 40), (x0, top + 10)], (100, 120, 142))
        y = top + 24
        while y < 650:
            s = (662 - y) / (662 - top)
            xr = x0 + w * (1 - s ** 2.4) + 2
            if xr - x0 > 10:
                mc.rect(x0 + 3, y, xr - 3, y + 3, (60, 74, 92))
                xx = x0 + 4
                while xx < xr - 8:
                    seg = rng.uniform(8, 28)
                    if rng.random() < 0.7:
                        mc.light_rect(xx, y, min(xr - 4, xx + seg), y + 3, rng.choice(WARM), rng.uniform(0, 0.6))
                    xx += seg + 2
            y += 8
        mc.light_line(right, (120, 220, 255), 2.2, 0.0)
        sc.tops.append((x0 + 6, top + 4))
    for x0, w, top in [(1120, 112, 205), (1262, 116, 255), (1410, 122, 228), (860, 80, 410), (960, 70, 440),
                       (1560, 90, 390), (1680, 84, 430), (1790, 100, 460)]:
        mc.poly([(x0, 662), (x0, top + 30), (x0 + w * 0.5, top), (x0 + w, top + 30), (x0 + w, 662)], (92, 104, 124))
        mc.rect(x0 + w * 0.66, top + 30, x0 + w, 662, (78, 90, 108))
        y = top + 40
        while y < 650:
            xx = x0 + 6
            while xx < x0 + w - 8:
                if rng.random() < 0.72:
                    mc.light_rect(xx, y, xx + 5, y + 4, rng.choice(WARM), rng.uniform(0, 0.6))
                xx += 8
            y += 8
        crown = (200, 140, 255) if w > 110 else (120, 220, 255)
        mc.light_line([(x0, top + 30), (x0 + w * 0.5, top), (x0 + w, top + 30)], crown, 2.4, 0.0)
        sc.tops.append((x0 + w * 0.5, top - 2))
    prom = Layer(0.0)
    prom.rect(-20, 990, 1940, 1080, (58, 58, 66))
    prom.rect(-20, 984, 1940, 992, (90, 90, 98))
    prom.rect(-20, 940, 1940, 946, (70, 70, 78))
    for x in range(-20, 1940, 34):
        prom.rect(x, 944, x + 4, 986, (70, 70, 78))
    for x in (240, 900, 1560):
        prom.rect(x - 4, 780, x + 4, 990, (52, 52, 60))
        prom.ellipse(x, 774, 14, 14, (230, 220, 200))
        prom.light_ellipse(x, 774, 13, 13, (255, 200, 120), 0.0)
    sc.back = Group([far, city, mc])
    sc.front = Group([prom])
    fw = fireworks_list()
    tops = np.array(sc.tops, np.float32)

    def anim_back(img, ctx):
        if (ctx.t * 0.8) % 1 < 0.5:
            splat(img, tops[:, 0] * S, tops[:, 1] * S, np.tile(np.array([[1.5, 0.12, 0.1]], np.float32), (len(tops), 1)))

    def anim_sky(img, ctx):
        for b in fw:
            tau = ctx.t - b["t0"]
            if tau < -0.8 or tau > 2.4:
                continue
            if tau < 0:
                u = ease(1 + tau / 0.8)
                y = lerp(700, b["cy"], u)
                ys = np.array([y, y + 8, y + 16, y + 26], np.float32)
                xs = np.full(4, b["cx"], np.float32)
                cc = np.array([[1.4, 1.1, 0.7]], np.float32) * np.array([[1.0], [0.6], [0.35], [0.15]], np.float32)
                splat(img, xs * S, ys * S, cc)
                continue
            for lag, wgt in ((0.0, 1.0), (0.05, 0.55), (0.11, 0.3), (0.18, 0.15)):
                tt = max(0.0, tau - lag)
                reach = (1 - math.exp(-3.2 * tt)) / 3.2 * 3.2
                xs = b["cx"] + b["dx"] * b["r"] * reach
                ys = b["cy"] + b["dy"] * b["r"] * reach + 55 * tt * tt
                fade = math.exp(-tt * 1.5) * wgt
                flick = 0.7 + 0.3 * np.sin(ctx.t * 30 + b["fl"])
                whiten = math.exp(-tt * 5)
                col = b["col"] * (1 - whiten) + np.array([2.0, 1.9, 1.7], np.float32) * whiten
                cc = (flick[:, None] * col[None, :] * fade).astype(np.float32)
                splat(img, xs * S, ys * S, cc)
            if tau < 0.25:
                fl = (1 - tau / 0.25) * 0.25
                R = int(260 * S)
                cx, cy = b["cx"] * S, b["cy"] * S
                x0, x1, y0, y1 = int(max(0, cx - R)), int(min(W, cx + R)), int(max(0, cy - R)), int(min(H, cy + R))
                yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
                g = np.exp(-np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (80 * S))
                img[y0:y1, x0:x1] += g[..., None] * b["col"] * fl

    sc.anim_back, sc.anim_sky = anim_back, anim_sky


SCENES = [
    (build_haeundae, "haeundae", "해운대 해수욕장", "HAEUNDAE BEACH", "수평선 위로 떠오르는 첫 햇살", 0.0, 7.6),
    (build_yonggungsa, "yonggungsa", "해동용궁사", "HAEDONG YONGGUNGSA", "바다 위 사찰의 고요한 아침", 6.4, 13.6),
    (build_gamcheon, "gamcheon", "감천문화마을", "GAMCHEON CULTURE VILLAGE", "어린왕자와 함께 내려다보는 알록달록 골목", 12.4, 19.6),
    (build_blueline, "blueline", "해운대 블루라인파크", "HAEUNDAE BLUELINE PARK", "바다를 따라 달리는 스카이캡슐", 18.4, 25.6),
    (build_tower, "tower", "용두산공원 · 부산타워", "BUSAN TOWER & JAGALCHI", "항구를 붉게 물들이는 노을", 24.4, 31.6),
    (build_gwangan, "gwangan", "광안대교", "GWANGAN BRIDGE", "광안리 밤하늘을 수놓는 드론쇼", 30.4, 37.6),
    (build_marine, "marine", "마린시티", "MARINE CITY", "불꽃으로 마무리하는 부산의 밤", 36.4, DUR),
]


# ───────────────────────────── 자막 / HUD ─────────────────────────────

def text_sprite(lines, shadow=True, pad=40):
    """lines: [(text, weight, size, color(rgba), tracking, dy)] → (rgb, a, w, h)."""
    pad = int(pad * S)
    widths, heights = [], 0
    for text, wt, size, col, track, dy in lines:
        f = font(wt, size * S)
        w = sum(f.getlength(ch) + track * S for ch in text)
        widths.append(w)
    bw = int(max(widths) + pad * 2)
    bh = int(sum(l[5] for l in lines) * S + pad * 2 + lines[-1][2] * S * 0.6)
    txt = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)
    y = pad
    for (text, wt, size, col, track, dy), w in zip(lines, widths):
        f = font(wt, size * S)
        x = pad
        for ch in text:
            d.text((x, y), ch, font=f, fill=col)
            x += f.getlength(ch) + track * S
        y += dy * S
    arr = np.asarray(txt, np.float32) / 255.0
    rgb, a = arr[..., :3].copy(), arr[..., 3].copy()
    if shadow:
        sh = cv2.GaussianBlur(a, (0, 0), 7 * S) * 0.6
        out_a = a + sh * (1 - a)
        rgb = rgb * (a / np.maximum(out_a, 1e-4))[..., None]
        a = out_a
    return rgb, a


def label_sprite(i, sc):
    return text_sprite([
        (f"{i + 1:02d}  —  {sc.en}", "Medium", 24, (255, 236, 205, 235), 5, 46),
        (sc.ko, "Black", 82, (255, 255, 255, 255), 1, 112),
        (sc.caption, "Medium", 30, (255, 255, 255, 220), 1, 40),
    ])


def period_name(h):
    for lim, name in [(6.5, "새벽"), (9.5, "아침"), (12.0, "오전"), (17.0, "오후"), (19.3, "해질녘"), (21.0, "저녁")]:
        if h < lim:
            return name
    return "밤"


def hud_sprite(h):
    k = 3
    wpx, hpx = int(300 * S), int(84 * S)
    im = Image.new("RGBA", (wpx * k, hpx * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = S * k
    d.rounded_rectangle([0, 0, wpx * k - 1, hpx * k - 1], radius=int(42 * s), fill=(10, 14, 28, 120))
    cx, cy, r = 44 * s, 42 * s, 25 * s
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 235), width=int(3 * s))
    for i in range(12):
        a = i / 12 * 2 * math.pi
        d.line([(cx + math.sin(a) * r * 0.78, cy - math.cos(a) * r * 0.78), (cx + math.sin(a) * r * 0.9, cy - math.cos(a) * r * 0.9)],
               fill=(255, 255, 255, 200), width=int(2 * s))
    ha = (h % 12) / 12 * 2 * math.pi
    ma = (h * 60 % 60) / 60 * 2 * math.pi
    d.line([(cx, cy), (cx + math.sin(ha) * r * 0.5, cy - math.cos(ha) * r * 0.5)], fill=(255, 210, 120, 255), width=int(4 * s))
    d.line([(cx, cy), (cx + math.sin(ma) * r * 0.78, cy - math.cos(ma) * r * 0.78)], fill=(255, 255, 255, 255), width=int(3 * s))
    d.ellipse([cx - 3 * s, cy - 3 * s, cx + 3 * s, cy + 3 * s], fill=(255, 255, 255, 255))
    hh, mm = int(h), int(h * 60 % 60)
    d.text((86 * s, 12 * s), f"{hh:02d}:{mm:02d}", font=font("Black", 40 * s), fill=(255, 255, 255, 255))
    d.text((210 * s, 26 * s), period_name(h), font=font("Medium", 26 * s), fill=(255, 220, 160, 255))
    arr = np.asarray(im, np.float32) / 255.0
    a = arr[..., 3:4]
    pm = cv2.resize(arr[..., :3] * a, (wpx, hpx), interpolation=cv2.INTER_AREA)
    a = cv2.resize(a, (wpx, hpx), interpolation=cv2.INTER_AREA)
    return pm / np.maximum(a[..., None], 1e-4), a


# ───────────────────────────── 렌더 파이프라인 ─────────────────────────────

STATE = {}


def build_all():
    ensure_fonts()
    scenes = []
    for i, (fn, key, ko, en, cap, t0, t1) in enumerate(SCENES):
        sc = Scene(key, ko, en, cap, t0, t1)
        print(f"  building scene {i + 1}/{len(SCENES)}: {ko}", flush=True)
        fn(sc)
        sc.prepare(100 + i)
        sc.label = label_sprite(i, sc)
        scenes.append(sc)
    STATE["scenes"] = scenes
    STATE["intro"] = text_sprite([
        ("BUSAN  ·  FROM DAWN TO NIGHT", "Medium", 28, (255, 230, 200, 235), 8, 54),
        ("부산의 하루", "Black", 132, (255, 255, 255, 255), 4, 170),
        ("새벽부터 밤까지, 부산 핫플레이스 여행", "Medium", 34, (255, 255, 255, 225), 2, 40),
    ], pad=60)
    STATE["outro"] = text_sprite([
        ("GOOD NIGHT, BUSAN", "Medium", 28, (255, 230, 200, 235), 10, 54),
        ("부산의 하루", "Black", 120, (255, 255, 255, 255), 4, 160),
        ("해운대의 첫 햇살부터 마린시티의 불꽃까지", "Medium", 32, (255, 255, 255, 225), 2, 40),
    ], pad=60)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vd = ((xx / W - 0.5) ** 2 * 1.2 + (yy / H - 0.5) ** 2 * 1.6)
    STATE["vignette"] = (1 - 0.55 * np.clip(vd, 0, 1) ** 1.3)[..., None].astype(np.float32)
    g = np.clip((yy / H - 0.55) / 0.45, 0, 1)
    STATE["vignette"] = STATE["vignette"] * (1 - 0.38 * g ** 1.5 * np.clip(1.25 - xx / W, 0, 1))[..., None]
    STATE["wipe"] = ((xx / W) * 0.78 + (yy / H) * 0.22).astype(np.float32)


def tonemap(img):
    over = np.maximum(img - 0.82, 0)
    return np.minimum(img, 0.82) + 0.18 * (1 - np.exp(-over / 0.18))


def bloom(img):
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    br = np.maximum(small - 0.72, 0)
    b = cv2.GaussianBlur(br, (0, 0), 3.0 * S + 0.5) * 0.9 + cv2.GaussianBlur(br, (0, 0), 10 * S + 1) * 0.6
    return img + cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)


def render_frame(t):
    cv2.setNumThreads(1)
    scenes = STATE["scenes"]
    active = [sc for sc in scenes if sc.t0 - 1e-6 <= t <= sc.t1 + 1e-6]
    imgs = [sc.render(Ctx(sc, t)) for sc in active[:2]]
    if len(imgs) == 2:
        a, b = active[0], active[1]
        u = clamp01((t - b.t0) / (a.t1 - b.t0))
        feather = 0.16
        e = lerp(-feather, 1 + feather, ease(u))
        F = STATE["wipe"]
        wgt = np.clip((e - F) / feather + 0.5, 0, 1)
        wgt = (wgt * wgt * (3 - 2 * wgt))[..., None]
        img = imgs[0] * (1 - wgt) + imgs[1] * wgt
        edge = np.exp(-((F - e) / 0.035) ** 2)[..., None]
        img += edge * np.array([1.0, 0.85, 0.6], np.float32) * 0.17 * math.sin(math.pi * u)
    else:
        img = imgs[0]
    img = bloom(img)
    img = tonemap(img) * STATE["vignette"]

    # 장면 자막
    for i, sc in enumerate(active):
        start = sc.t0 + (3.9 if i == 0 and sc.key == "haeundae" else 1.0)
        end = sc.t1 - 1.5
        if sc.key == "marine":
            end = DUR - 5.6
        op = ss(start, start + 0.8, t) * (1 - ss(end, end + 0.6, t))
        if op > 0.003:
            rgb, a = sc.label
            blend(img, rgb, a, 96 * S - 40 * S, H - 330 * S + (1 - op) * 18 * S, op)
    # 인트로 / 아웃트로 타이틀
    op = ss(0.3, 1.2, t) * (1 - ss(3.0, 3.8, t))
    if op > 0.003:
        rgb, a = STATE["intro"]
        blend(img, rgb, a, (W - a.shape[1]) / 2, H * 0.40 - a.shape[0] / 2 + (1 - op) * 14 * S, op)
    op = ss(DUR - 5.0, DUR - 4.0, t)
    if op > 0.003:
        img *= 1 - 0.3 * op
        rgb, a = STATE["outro"]
        blend(img, rgb, a, (W - a.shape[1]) / 2, H * 0.36 - a.shape[0] / 2 + (1 - op) * 14 * S, op)
    # 시계 HUD + 하루 진행 막대
    h = hour_at(t)
    op = ss(3.4, 4.2, t) * (1 - ss(DUR - 5.4, DUR - 4.6, t))
    if op > 0.003:
        rgb, a = hud_sprite(h)
        blend(img, rgb, a, W - 96 * S - a.shape[1], 60 * S, op)
        x0, x1, y = int(96 * S), int(W - 96 * S), int(H - 58 * S)
        th = max(1, int(2 * S))
        prog = (h - 5.0) / 18.0
        xm = int(lerp(x0, x1, prog))
        img[y:y + th, x0:x1] = img[y:y + th, x0:x1] * (1 - 0.25 * op) + 0.25 * op
        img[y:y + th, x0:xm] = img[y:y + th, x0:xm] * (1 - 0.85 * op) + np.array([1.0, 0.86, 0.6], np.float32) * 0.85 * op
        for sc in STATE["scenes"]:
            hx = int(lerp(x0, x1, (hour_at((sc.t0 + sc.t1) / 2) - 5.0) / 18.0))
            r = int(4 * S) + 1
            on = 1.0 if hx <= xm else 0.45
            img[y - r + th // 2:y + r + th // 2, hx - r:hx + r] = img[y - r + th // 2:y + r + th // 2, hx - r:hx + r] * (1 - op * on) + op * on
        r = int(7 * S) + 1
        img[y - r + th // 2:y + r + th // 2, xm - r:xm + r] = img[y - r + th // 2:y + r + th // 2, xm - r:xm + r] * (1 - op) + np.array([1.0, 0.9, 0.7], np.float32) * op
    # 마지막 페이드아웃
    img *= (1 - ss(DUR - 1.3, DUR - 0.05, t)) * ss(0.0, 0.5, t)
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def _worker_frame(i):
    return render_frame(i / FPS).tobytes()


# ───────────────────────────── 사운드트랙 ─────────────────────────────

def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def make_audio(path, sr=44100):
    n = int(DUR * sr)
    t = np.arange(n) / sr
    out = np.zeros((n, 2), np.float32)
    rng = np.random.default_rng(3)
    chords = [[53, 57, 60, 64], [55, 59, 62, 64], [52, 55, 59, 62], [57, 60, 64, 67],
              [50, 53, 57, 60], [55, 60, 62, 65], [48, 52, 55, 59], [48, 55, 59, 62]]
    cl = DUR / len(chords)
    for ci, ch in enumerate(chords):
        s0 = int(max(0, (ci * cl - 0.8)) * sr)
        s1 = int(min(DUR, (ci + 1) * cl + 1.2) * sr)
        tt = t[s0:s1] - t[s0]
        L = tt[-1]
        env = np.minimum(1, tt / 1.6) * np.minimum(1, (L - tt) / 1.6)
        for note in ch + [ch[0] - 12]:
            f = midi(note)
            for det, pan in ((-0.12, 0.3), (0.12, 0.7)):
                ff = f * 2 ** (det / 12)
                ph = rng.uniform(0, 6.28)
                wv = np.sin(2 * np.pi * ff * tt + ph) + 0.3 * np.sin(4 * np.pi * ff * tt + ph) + 0.1 * np.sin(6 * np.pi * ff * tt)
                wv *= env * 0.028
                out[s0:s1, 0] += wv * (1 - pan)
                out[s0:s1, 1] += wv * pan
    # 벨 아르페지오 (낮에는 촘촘하게, 새벽·밤엔 성기게)
    step = 0.42
    k = 0
    tb = 1.6
    while tb < DUR - 2.5:
        ci = min(len(chords) - 1, int(tb / cl))
        ch = chords[ci]
        note = ch[[0, 2, 1, 3, 2, 1][k % 6]] + 12 + (12 if k % 12 in (5, 11) else 0)
        dens = 0.55 + 0.45 * math.sin(math.pi * tb / DUR)
        if rng.random() < dens:
            s0 = int(tb * sr)
            ln = int(1.8 * sr)
            tt = np.arange(min(ln, n - s0)) / sr
            f = midi(note)
            wv = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * f * 2.01 * tt) * np.exp(-tt * 6)) * np.exp(-tt * 2.6)
            wv *= 0.05 * np.minimum(1, tt / 0.004)
            pan = 0.5 + 0.35 * math.sin(k * 1.3)
            out[s0:s0 + tt.size, 0] += wv * (1 - pan)
            out[s0:s0 + tt.size, 1] += wv * pan
        tb += step
        k += 1
    # 파도 소리
    noise = rng.normal(0, 1, (n, 2)).astype(np.float32)
    b = np.cumsum(noise, axis=0)
    for c in range(2):
        b[:, c] -= np.convolve(b[:, c], np.ones(2001) / 2001, "same")
    b /= np.abs(b).max() + 1e-6
    sea_lvl = np.interp(t, [0, 7, 13, 18, 25, 31, 37, 44], [1.0, 0.9, 0.35, 0.6, 0.55, 0.85, 0.6, 0.4])
    swell = 0.55 + 0.45 * np.sin(2 * np.pi * t / 6.5) ** 2
    out += b * (0.09 * sea_lvl * swell)[:, None]
    # 불꽃 소리
    for t0 in FIREWORK_TIMES:
        s0 = int((t0 + 0.05) * sr)
        ln = int(1.6 * sr)
        tt = np.arange(min(ln, n - s0)) / sr
        thump = np.sin(2 * np.pi * (70 * tt - 25 * tt ** 2)) * np.exp(-tt * 7) * 0.35
        crack = rng.normal(0, 1, tt.size) * (rng.random(tt.size) < 0.02) * np.exp(-tt * 2.2) * 0.25
        out[s0:s0 + tt.size, 0] += thump + crack
        out[s0:s0 + tt.size, 1] += thump + np.roll(crack, 37)
    # 간단한 리버브
    ir_n = int(1.6 * sr)
    ir = rng.normal(0, 1, ir_n) * np.exp(-np.arange(ir_n) / sr * 3.2)
    ir /= np.sqrt((ir ** 2).sum())
    m = 1 << int(math.ceil(math.log2(n + ir_n)))
    IR = np.fft.rfft(ir, m)
    for c in range(2):
        wet = np.fft.irfft(np.fft.rfft(out[:, c], m) * IR, m)[:n]
        out[:, c] = out[:, c] * 0.8 + wet * 0.35
    fade = np.minimum(1, t / 1.5) * np.minimum(1, (DUR - t) / 3.0)
    out *= fade[:, None]
    out /= np.abs(out).max() + 1e-6
    out *= 0.85
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


# ───────────────────────────── main ─────────────────────────────

def main():
    args = sys.argv[1:]
    print(f"building scenes at {W}x{H} ...", flush=True)
    build_all()
    if args and args[0] == "--still":
        for s in args[1:]:
            t = float(s)
            p = os.path.join(os.environ.get("BUSAN_STILL_DIR", HERE), f"still_{t:05.1f}.png")
            Image.fromarray(render_frame(t)).save(p)
            print("saved", p)
        return
    nframes = int(DUR * FPS)
    tmp_video = OUT + ".video.mp4"
    tmp_audio = OUT + ".audio.wav"
    print("rendering soundtrack ...", flush=True)
    make_audio(tmp_audio)
    enc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp_video], stdin=subprocess.PIPE)
    procs = int(os.environ.get("BUSAN_PROCS", os.cpu_count() or 2))
    print(f"rendering {nframes} frames with {procs} processes ...", flush=True)
    with Pool(procs) as pool:
        for i, fr in enumerate(pool.imap(_worker_frame, range(nframes), chunksize=4)):
            enc.stdin.write(fr)
            if i % FPS == 0:
                print(f"  {i / FPS:5.1f}s / {DUR:.0f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_video, "-i", tmp_audio, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT], check=True)
    os.remove(tmp_video)
    os.remove(tmp_audio)
    print("done:", OUT)


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    main()
