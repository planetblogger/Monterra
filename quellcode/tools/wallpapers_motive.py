#!/usr/bin/env python3
"""
Monterra-Hintergründe: abstrakte Motive in den Systemfarben, je Hell und Dunkel,
3840 × 2160, weich und ruhig.

  Himmel     Blau + Indigo           schwebende Wolkenbänder
  Wueste     Orange + Gelb           Sanddünen im Streiflicht
  Mars       Rot + Braun             Hochebenen und Krater unter rötlichem Dunst
  Dschungel  Grün + Petrol + Cyan    große Blätter in mehreren Tiefenebenen
  Seide      Grau + Graphit          fließendes Seidentuch
  Bluete     Lila + Pink             große, durchscheinende Blütenblätter

Alles wird mit numpy gerechnet (eigene Arbeit, keine fremden Bilder) und mit Rauschen
gegen Farbstufen versehen.

usage: wallpapers_motive.py AUSGABE [--preview] [motiv …]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

W, H = 3840, 2160
WORK = 2          # gerechnet wird in halber Auflösung, danach weich hochskaliert
MOTIVE = ["Himmel", "Wueste", "Mars", "Dschungel", "Seide", "Bluete"]


# ------------------------------------------------------------------ Grundlagen
def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def ramp(t, colors, pos=None):
    cols = [hexrgb(c) for c in colors]
    pos = np.linspace(0, 1, len(cols)) if pos is None else np.array(pos, np.float32)
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,), np.float32)
    for i in range(len(cols) - 1):
        a, b = pos[i], pos[i + 1]
        m = (t >= a) & (t <= b) if i == len(cols) - 2 else (t >= a) & (t < b)
        k = smooth(0, 1, (t - a) / max(b - a, 1e-6))
        for c in range(3):
            out[..., c] = np.where(m, cols[i][c] + (cols[i + 1][c] - cols[i][c]) * k, out[..., c])
    out[t < pos[0]] = cols[0]
    out[t > pos[-1]] = cols[-1]
    return out


def over(img, col, alpha):
    """col (3,) oder (h,w,3) mit Deckkraft alpha (h,w) über img legen"""
    return img + (col - img) * np.clip(alpha, 0, 1)[..., None]


def gauss(a, sigma):
    """trennbare Gauß-Unschärfe (float, Ränder gespiegelt)"""
    if sigma < 0.3:
        return a
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2).astype(np.float32)
    k /= k.sum()
    for ax in (0, 1):
        pad = [(0, 0)] * a.ndim
        pad[ax] = (r, r)
        p = np.pad(a, pad, mode="reflect")
        a = sum(k[i] * np.take(p, range(i, i + a.shape[ax]), axis=ax) for i in range(2 * r + 1))
    return a.astype(np.float32)


def noise2(w, h, scale, rng, octaves=4):
    """weiches Wertrauschen (fBm), Werte etwa 0..1"""
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = max(2, int(scale * 2 ** o))
        g = rng.random((n + 1, int(n * w / h) + 2)).astype(np.float32)
        im = Image.fromarray(g, "F").resize((w, h), Image.BICUBIC)
        out += np.asarray(im, np.float32) * amp
        tot += amp
        amp *= 0.5
    return out / tot


def grid(w, h):
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    return np.broadcast_to(x, (h, w)), np.broadcast_to(y, (h, w))


def vignette(img, x, y, k):
    v = (x - 0.5) ** 2 * 0.9 + (y - 0.55) ** 2 * 0.7
    return img * (1 - k * v)[..., None]


# ------------------------------------------------------------------ Himmel (Blau + Indigo)
def himmel(dark, w, h, rng):
    x, y = grid(w, h)
    X = x * w / h
    if not dark:
        img = ramp(y, ["#2F6FD6", "#4F8BE4", "#86AEEC", "#B4CBF0"], [0, 0.35, 0.72, 1])
        img = over(img, hexrgb("#5856D6"), smooth(0.3, 1.0, x) * (1 - y) * 0.45)     # Indigo von rechts oben
        bands = [("#F4F6FF", 0.36), ("#FFFFFF", 0.50), ("#ECEBFF", 0.63), ("#FFFFFF", 0.76), ("#E6ECFB", 0.90)]
        strength = [0.30, 0.45, 0.55, 0.62, 0.58]
        shade = "#5B7FD0"
        d = np.sqrt((X - 0.25) ** 2 + (y - 0.05) ** 2)
        img = over(img, hexrgb("#EAF2FF"), np.exp(-(d / 0.55) ** 2) * 0.35)       # helles Licht links oben
    else:
        img = ramp(y, ["#04061A", "#090E30", "#121A4E", "#1B2668"], [0, 0.35, 0.75, 1])
        img = over(img, hexrgb("#5E5CE6"), smooth(0.3, 1.0, x) * smooth(0.2, 0.9, y) * 0.25)
        bands = [("#24308A", 0.36), ("#2E3DA8", 0.50), ("#3A44C0", 0.63), ("#3249B8", 0.76), ("#4650C8", 0.90)]
        strength = [0.25, 0.32, 0.40, 0.46, 0.50]
        shade = "#070A24"
        # wenige, sehr feine Sterne im oberen Bereich
        n = int(260 * w / 1920)
        sx, sy = rng.integers(0, w, n), (rng.random(n) ** 1.6 * h * 0.5).astype(int)
        for px, py, b in zip(sx, sy, rng.random(n) ** 3 * 0.5 + 0.1):
            img[py, px] += (1 - img[py, px]) * b
    # Wolkenbänder: weiche, wellige Bahnen mit hellerer Oberkante
    for i, ((col, base), st) in enumerate(zip(bands, strength)):
        ph = rng.random() * 6.28
        yc = base + 0.05 * np.sin(X * (0.9 + 0.25 * i) + ph) + 0.022 * np.sin(X * 2.3 + ph * 1.7)
        thick = 0.035 + 0.02 * (0.5 + 0.5 * np.sin(X * 1.3 + ph * 0.6)) + 0.01 * i
        d = (y - yc) / thick
        body = np.exp(-d ** 2) * (0.75 + 0.25 * noise2(w, h, 3, rng, 3))
        top = np.exp(-((d + 0.9) / 0.35) ** 2) * 0.35          # helle Oberkante
        bottom = np.exp(-((d - 1.0) / 0.6) ** 2) * 0.25        # leichter Schatten darunter
        img = over(img, hexrgb(shade), bottom * st)
        img = over(img, hexrgb(col), body * st)
        img = over(img, hexrgb(col), top * st * (0.6 if dark else 1.0))
    return vignette(img, x, y, 0.22 if dark else 0.12)


# ------------------------------------------------------------------ Wüste (Orange + Gelb)
def _skewed(xs, f, ph, skew):
    t = xs * f * 2 * np.pi + ph
    return np.sin(t + skew * np.sin(t))


def wueste(dark, w, h, rng):
    x, y = grid(w, h)
    if not dark:
        img = ramp(y, ["#F6B25E", "#FAD08A", "#FDE6BC", "#FFE9C4"], [0, 0.3, 0.55, 0.62])
        glow = ("#FFF3D6", 0.75, (0.72, 0.50), 0.30)
        lit = [("#FFD27A", "#F7B14A"), ("#FDC266", "#EE9A33"), ("#F9B254", "#E4862A"),
               ("#F2A044", "#D47322"), ("#E88C38", "#C2611B")]
        shd = [("#E9A05A", "#D88742"), ("#E08C46", "#C97431"), ("#D57A39", "#B86227"),
               ("#C66A2F", "#A4521F"), ("#B25A27", "#8C4419")]
        haze = [0.40, 0.28, 0.18, 0.09, 0.03]
    else:
        img = ramp(y, ["#120A14", "#2A1420", "#5A2A22", "#8A4A26"], [0, 0.3, 0.55, 0.62])
        glow = ("#FFB347", 0.40, (0.72, 0.58), 0.22)
        lit = [("#9A5A26", "#874C1F"), ("#8A4E21", "#743F1A"), ("#7A421C", "#643415"),
               ("#683716", "#532A11"), ("#552C12", "#41200D")]
        shd = [("#5C2E1C", "#4C2417"), ("#4E2618", "#3F1E13"), ("#401F14", "#33180F"),
               ("#33180F", "#28120B"), ("#271209", "#1D0D07")]
        haze = [0.35, 0.24, 0.15, 0.07, 0.02]
    gcol, gstr, (gx, gy), gr = glow
    d = np.sqrt(((x - gx) * w / h) ** 2 + (y - gy) ** 2)
    img = over(img, hexrgb(gcol), np.exp(-(d / gr) ** 2) * gstr)

    xs = np.linspace(0, 1, w, dtype=np.float32)
    rows = np.arange(h, dtype=np.float32)[:, None]
    shapes = [(0.58, [(0.05, 0.9, 0.6), (0.014, 2.6, 2.0)], 0.6), (0.65, [(0.06, 0.75, 2.4), (0.016, 2.1, 0.4)], 0.62),
              (0.73, [(0.065, 0.62, 4.0), (0.018, 1.8, 2.7)], 0.65), (0.81, [(0.07, 0.55, 1.1), (0.016, 1.5, 4.1)], 0.68),
              (0.90, [(0.06, 0.48, 3.2), (0.014, 1.3, 1.3)], 0.7)]
    haze_col = img[int(h * 0.6), w // 2].copy()
    for i, (base, waves, skew) in enumerate(shapes):
        edge = np.full(w, base, np.float32)
        for a, f, ph in waves:
            edge += a * _skewed(xs, f, ph + rng.random() * 0.3, skew)
        slope = np.gradient(edge)
        depth = rows - edge[None, :] * h
        alpha = smooth(-1.0, 1.0, depth)
        t = smooth(0, 1, np.clip(depth / (h * 0.3), 0, 1))[..., None]
        l0, l1 = (hexrgb(c) for c in lit[i])
        s0, s1 = (hexrgb(c) for c in shd[i])
        lc, sc = l0 + (l1 - l0) * t, s0 + (s1 - s0) * t
        sl = slope / (np.abs(slope).max() + 1e-6)
        ker = np.exp(-np.linspace(-3, 3, max(9, w // 14 | 1)) ** 2)
        sl = np.convolve(np.pad(sl, len(ker)), ker / ker.sum(), "same")[len(ker):-len(ker)]
        k = smooth(-0.6, 0.6, -sl)[None, :]                           # Licht von rechts
        reach = np.exp(-np.clip(depth, 0, None) / (h * (0.06 + 0.03 * i)))
        col = lc + (sc - lc) * (k * reach)[..., None]
        crest = np.exp(-np.clip(depth, 0, None) / (h * 0.005)) * (1 - k) * (0.25 if not dark else 0.18)
        col = over(col, hexrgb(gcol), crest)
        col = col + (haze_col - col) * haze[i]
        img = over(img, col, alpha)
    return vignette(img, x, y, 0.25 if dark else 0.14)


# ------------------------------------------------------------------ Mars (Rot + Braun)
def mars(dark, w, h, rng):
    x, y = grid(w, h)
    X = x * w / h
    if not dark:
        img = ramp(y, ["#C9826A", "#DFA184", "#ECBFA2", "#F0C9AE"], [0, 0.3, 0.5, 0.56])
        layers = ["#D9895E", "#C7704A", "#B45A3A", "#9C4630", "#7F3526"]
        rim, haze, sun = "#FFD9C2", 0.28, ("#FFE6D6", 0.5)
    else:
        img = ramp(y, ["#0A0507", "#1A0A0C", "#3A1512", "#5A2418"], [0, 0.3, 0.5, 0.56])
        layers = ["#6A2A1C", "#5A2218", "#4A1B14", "#3A1510", "#2A0F0B"]
        rim, haze, sun = "#E07A4E", 0.25, ("#7FA8D8", 0.30)       # Marsdämmerung: bläuliches Licht
    # Dunst um die tief stehende Sonne
    d = np.sqrt(((x - 0.28) * w / h) ** 2 + (y - 0.50) ** 2)
    img = over(img, hexrgb(sun[0]), np.exp(-(d / 0.20) ** 2) * sun[1])
    if dark:
        img = over(img, hexrgb("#CFE2FF"), (d < 0.012) * 0.8 + np.exp(-(d / 0.02) ** 2) * 0.4)
    xs = X[0]
    rows = np.arange(h, dtype=np.float32)[:, None]
    hazecol = img[int(h * 0.5), w // 2].copy()
    bases = [0.55, 0.62, 0.70, 0.79, 0.90]
    for i, base in enumerate(bases):
        n = noise2(w, 1, 3 + 2 * i, rng, 4)[0] if False else None
        # Hochebenen: flache Kanten mit steilen Abbrüchen
        prof = 0.0
        for f, a in ((0.35 + 0.1 * i, 0.035), (0.9 + 0.2 * i, 0.012), (2.4, 0.004)):
            prof = prof + a * np.sin(xs * f * 2 * np.pi / (w / h) + rng.random() * 6.28)
        prof = np.round(prof / 0.012) * 0.012 * 0.7 + prof * 0.3                 # terrassiert
        prof = np.convolve(prof, np.ones(max(3, w // 160)) / max(3, w // 160), "same")
        edge = base + prof
        depth = rows - edge[None, :] * h
        alpha = smooth(-1.0, 1.0, depth)
        col = np.broadcast_to(hexrgb(layers[i]), (h, w, 3)).copy()
        tex = noise2(w, h, 6 + 3 * i, rng, 4)
        col *= (0.88 + 0.24 * tex)[..., None]
        col = over(col, hexrgb(rim), np.exp(-np.clip(depth, 0, None) / (h * 0.004)) * 0.35)   # helle Kante
        col *= (1 - 0.25 * smooth(0, h * 0.25, depth))[..., None]                            # nach unten dunkler
        col = col + (hazecol - col) * (haze * (1 - i / len(bases)))
        img = over(img, col, alpha)
    # flache Krater im Vordergrund
    for _ in range(7):
        cx, cy = rng.random() * w / h, 0.84 + rng.random() * 0.13
        rx = 0.03 + rng.random() * 0.06
        e = ((X - cx) / rx) ** 2 + ((y - cy) / (rx * 0.28)) ** 2
        img *= (1 - 0.22 * np.exp(-e * 1.5) * smooth(-0.2, 0.2, (y - cy)))[..., None]
        img = over(img, hexrgb(rim), np.exp(-((np.sqrt(e) - 1) / 0.12) ** 2) * (y < cy) * 0.12)
    return vignette(img, x, y, 0.3 if dark else 0.16)


# ------------------------------------------------------------------ Dschungel (Grün + Petrol + Cyan)
def _leaf(X, y, cx, cy, length, width, angle, w_aa):
    ca, sa = np.cos(angle), np.sin(angle)
    u = ((X - cx) * ca + (y - cy) * sa) / length          # entlang des Blatts 0..1
    v = (-(X - cx) * sa + (y - cy) * ca) / length          # quer
    prof = width * np.clip(np.sin(np.pi * np.clip(u, 0, 1)), 0, 1) ** 0.75 * (1 - 0.25 * u)
    inside = smooth(-w_aa, w_aa, prof - np.abs(v)) * (u > 0) * (u < 1)
    rib = np.exp(-(v / (0.006 + 0.004 * (1 - u))) ** 2) * inside
    across = np.clip(np.abs(v) / np.maximum(prof, 1e-4), 0, 1)
    side = np.sign(v)
    return inside, rib, across, side


def dschungel(dark, w, h, rng):
    x, y = grid(w, h)
    X = x * w / h
    if not dark:
        img = ramp(y, ["#BFE9E2", "#9ADCD4", "#7CCFC8", "#5EBDB8"])
        img = over(img, hexrgb("#E9FFF6"), np.exp(-(((X - 1.2) ** 2 + (y - 0.15) ** 2) / 0.25)) * 0.6)
        depth_cols = [("#7CCFC8", "#9FE0D8"), ("#4FB9B0", "#7DD6CB"), ("#2FA58E", "#5FCB9F"),
                      ("#1F8F62", "#3FBF6E"), ("#14784A", "#30A85A")]
        rimc = "#E8FFF4"
    else:
        img = ramp(y, ["#031210", "#052019", "#073027", "#0A3A31"])
        img = over(img, hexrgb("#145C62"), np.exp(-(((X - 1.2) ** 2 + (y - 0.15) ** 2) / 0.25)) * 0.6)
        depth_cols = [("#072826", "#0A3634"), ("#08322E", "#0C433C"), ("#08392B", "#0E4D39"),
                      ("#073322", "#0C472F"), ("#05281A", "#0A3A25")]
        rimc = "#64D2FF"
    aa = 1.5 / h
    blurs = [10, 6, 3, 1.2, 0.6]             # hinten unscharf, vorne scharf (Tiefenwirkung)
    counts = [7, 6, 5, 4, 3]
    for layer, (c0, c1) in enumerate(depth_cols):
        acc_a = np.zeros((h, w), np.float32)
        acc_c = np.zeros((h, w, 3), np.float32)
        for _ in range(counts[layer]):
            # Blätter wachsen von den Rändern ins Bild
            side = rng.integers(0, 4)
            if side == 0:   cx, cy, ang = -0.1, rng.uniform(0.1, 1.0), rng.uniform(-0.6, 0.3)
            elif side == 1: cx, cy, ang = w / h + 0.1, rng.uniform(0.1, 1.0), np.pi + rng.uniform(-0.3, 0.6)
            elif side == 2: cx, cy, ang = rng.uniform(0, w / h), 1.12, -np.pi / 2 + rng.uniform(-0.7, 0.7)
            else:           cx, cy, ang = rng.uniform(0, w / h), -0.12, np.pi / 2 + rng.uniform(-0.7, 0.7)
            length = rng.uniform(0.55, 0.95) * (0.75 + 0.1 * layer)
            inside, rib, across, sgn = _leaf(X, y, cx, cy, length, rng.uniform(0.17, 0.26), ang, aa / length)
            col = hexrgb(c0) + (hexrgb(c1) - hexrgb(c0)) * smooth(0, 1, (1 - across) * (0.6 + 0.4 * (sgn > 0)))[..., None]
            col = over(col, hexrgb(c0) * 0.75, rib * 0.6)
            col = over(col, hexrgb(rimc), np.exp(-((1 - across) / 0.05) ** 2) * inside * (0.18 if dark else 0.22))
            acc_c = over(acc_c, col, inside)
            acc_a = np.maximum(acc_a, inside)
        # leichter Schatten der Ebene auf alles dahinter
        sh = gauss(acc_a, 6 + 3 * layer) * (0.25 if dark else 0.18)
        img *= (1 - sh)[..., None]
        if blurs[layer] > 0.8:
            acc_c = gauss(acc_c * acc_a[..., None], blurs[layer])
            acc_a = gauss(acc_a, blurs[layer])
            acc_c = acc_c / np.maximum(acc_a, 1e-4)[..., None]
        img = over(img, acc_c, acc_a)
    return vignette(img, x, y, 0.3 if dark else 0.15)


# ------------------------------------------------------------------ Seide (Grau + Graphit)
def seide(dark, w, h, rng):
    x, y = grid(w, h)
    X = x * w / h
    u = X * 1.15 + y * 0.55
    v = y - X * 0.25
    warp = 0.22 * np.sin(v * 3.1 + 0.8) + 0.10 * np.sin(u * 2.3 + 2.0)
    hgt = (np.sin((u + warp) * 7.0) * 0.55 + np.sin((u * 0.6 - v * 0.9 + warp * 1.5) * 3.0 + 1.3) * 0.35 +
           np.sin((u * 1.7 + v * 0.4) * 2.0 + 4.0) * 0.18)
    band = np.exp(-((v - 0.30 + 0.12 * np.sin(u * 1.4)) / 0.46) ** 2)
    hgt = np.tanh(hgt * 1.6) / np.tanh(1.6) * band
    gy, gx = np.gradient(hgt, 1.0 / h, 1.0 / h)
    nx, ny = -gx * 0.11, -gy * 0.11
    nl = np.sqrt(nx ** 2 + ny ** 2 + 1)
    nx, ny, nz = nx / nl, ny / nl, 1 / nl
    L = np.array([-0.45, -0.55, 0.70]); L /= np.linalg.norm(L)
    diff = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    Hh = L + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
    spec = np.clip(nx * Hh[0] + ny * Hh[1] + nz * Hh[2], 0, 1) ** 50
    shade = smooth(0.15, 1.0, diff)
    if not dark:
        col = ramp(shade, ["#8E8E93", "#B8B8BE", "#DCDCE0", "#F2F2F4"])
        col = over(col, hexrgb("#FFFFFF"), spec * 0.55)
        col = over(col, hexrgb("#D9DCE6"), np.clip(0.5 + 0.5 * np.sin(X * 1.3 - y * 2.0), 0, 1) * 0.25)
    else:
        col = ramp(shade, ["#0E0E10", "#1E1E21", "#3A3A3C", "#5A5A5F"])
        col = over(col, hexrgb("#B9BCC8"), spec * 0.45)
        col = over(col, hexrgb("#2A2C34"), np.clip(0.5 + 0.5 * np.sin(X * 1.3 - y * 2.0), 0, 1) * 0.3)
    return vignette(col, x, y, 0.28 if dark else 0.14)


# ------------------------------------------------------------------ Blüte (Lila + Pink)
def _petal(X, y, cx, cy, length, width, angle, aa):
    """Blütenblatt: breit und rund am Ende, schmal am Ansatz"""
    ca, sa = np.cos(angle), np.sin(angle)
    u = ((X - cx) * ca + (y - cy) * sa) / length
    v = (-(X - cx) * sa + (y - cy) * ca) / length
    uc = np.clip(u, 0, 1)
    k = 0.6                                               # breiteste Stelle
    taper = width * (uc / k) ** 0.75                      # zum Ansatz hin schmal
    tip = width * np.sqrt(np.clip(1 - ((uc - k) / (1 - k)) ** 2, 0, 1))   # rundes Ende
    prof = np.where(uc < k, taper, tip)
    inside = smooth(-aa, aa, prof - np.abs(v)) * smooth(-aa, aa, u) * smooth(-aa, aa, 1.0 - u)
    across = np.clip(np.abs(v) / np.maximum(prof, 1e-4), 0, 1)
    return inside, uc, across


def bluete(dark, w, h, rng):
    x, y = grid(w, h)
    X = x * w / h
    cx, cy = 0.66 * w / h, 0.58                       # Blütenmitte rechts der Bildmitte
    if not dark:
        img = ramp(y, ["#F3E6F8", "#F6DDEE", "#F9D6E6", "#F4CFE4"])
        img = over(img, hexrgb("#FFFFFF"), np.exp(-(((X - 0.3) ** 2 + (y - 0.2) ** 2) / 0.3)) * 0.5)
        rings = [  # (Anzahl, Länge, Breite, Basis, Spitze, Deckkraft, Unschärfe)
            (7, 1.05, 0.30, "#C98BE6", "#F9C6DE", 0.55, 10),
            (6, 0.80, 0.29, "#B567E0", "#FFA3C2", 0.62, 4),
            (5, 0.56, 0.28, "#A24DD8", "#FF7AA2", 0.70, 1.5),
        ]
        rim, core = "#FFFFFF", "#FFE6F0"
    else:
        img = ramp(y, ["#0E0614", "#170A22", "#22102E", "#2A1236"])
        img = over(img, hexrgb("#4A1C5E"), np.exp(-(((X - cx) ** 2 + (y - cy) ** 2) / 0.35)) * 0.6)
        rings = [
            (7, 1.05, 0.30, "#3A1450", "#64285F", 0.55, 10),
            (6, 0.80, 0.29, "#521C70", "#962A60", 0.62, 4),
            (5, 0.56, 0.28, "#6C2496", "#C23264", 0.70, 1.5),
        ]
        rim, core = "#FF9ACB", "#FFC2DC"
    aa = 1.5 / h
    for r, (n, length, width, c0, c1, op, bl) in enumerate(rings):
        acc_a = np.zeros((h, w), np.float32)
        acc_c = np.zeros((h, w, 3), np.float32)
        a0 = rng.random() * 6.28
        for k in range(n):
            ang = a0 + k * 2 * np.pi / n + rng.uniform(-0.12, 0.12)
            L = length * rng.uniform(0.9, 1.1)
            inside, u, across = _petal(X, y, cx, cy, L, width, ang, aa / L)
            col = hexrgb(c0) + (hexrgb(c1) - hexrgb(c0)) * smooth(0, 1, u ** 0.8)[..., None]
            col = over(col, hexrgb(rim), np.exp(-((1 - across) / 0.06) ** 2) * smooth(0.2, 0.9, u) * 0.35)   # helle Kante
            col = over(col, hexrgb(c0) * 0.8, np.exp(-(across / 0.05) ** 2) * (1 - u) * 0.25)               # Mittelader
            acc_c = over(acc_c, col, inside)
            acc_a = np.maximum(acc_a, inside)
        if bl > 0.8:
            acc_c = gauss(acc_c * acc_a[..., None], bl)
            acc_a = gauss(acc_a, bl)
            acc_c = acc_c / np.maximum(acc_a, 1e-4)[..., None]
        img *= (1 - gauss(acc_a, 8) * 0.12)[..., None]          # weicher Schatten der Ebene
        img = over(img, acc_c, acc_a * op)
    # leuchtende Mitte
    d = np.sqrt((X - cx) ** 2 + (y - cy) ** 2)
    img = over(img, hexrgb(core), np.exp(-(d / 0.09) ** 2) * (0.75 if not dark else 0.55))
    return vignette(img, x, y, 0.3 if dark else 0.12)


RENDER = {"Bluete": bluete, "Himmel": himmel, "Wueste": wueste, "Mars": mars, "Dschungel": dschungel, "Seide": seide}
# Tonwert: hell etwas gedämpft (angenehmer für die Augen), dunkel etwas tiefer
TONE = {"Hell": 0.92, "Dunkel": 0.95}


def render(motiv, dark, w=W, h=H, seed=7):
    rng = np.random.default_rng(seed + MOTIVE.index(motiv) * 17)
    ww, hh = w // WORK, h // WORK
    img = RENDER[motiv](dark, ww, hh, rng)
    img = gauss(np.clip(img, 0, 1), hh * 0.0025)            # weich, ohne harte Kanten
    img = np.clip(img * TONE["Dunkel" if dark else "Hell"], 0, 1)
    up = np.stack([np.asarray(Image.fromarray(img[..., c].astype(np.float32), "F").resize((w, h), Image.BICUBIC))
                   for c in range(3)], -1)
    grain = rng.normal(0, 0.006 if dark else 0.004, (h, w)).astype(np.float32)[..., None]
    out = np.clip(up + grain, 0, 1) * 255 + rng.uniform(-0.5, 0.5, (h, w, 3)).astype(np.float32)
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), "RGB")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = Path(args[0]); out.mkdir(parents=True, exist_ok=True)
    preview = "--preview" in sys.argv
    sel = [m for m in MOTIVE if m.lower() in [a.lower() for a in args[1:]]] or MOTIVE
    for m in sel:
        for v, dark in (("Hell", False), ("Dunkel", True)):
            w, h = (960, 540) if preview else (W, H)
            im = render(m, dark, w, h)
            p = out / f"Monterra-{m}-{v}.jpg"
            im.save(p, quality=95 if not preview else 90, subsampling=0, optimize=True)
            print(p)
