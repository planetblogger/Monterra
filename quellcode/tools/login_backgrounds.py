#!/usr/bin/env python3
"""
Anmelde-Hintergründe für Monterra: zu jedem Desktop-Hintergrund eine stark
weichgezeichnete, leicht abgedunkelte Variante (ruhig und gut lesbar).

usage: login_backgrounds.py SRC_DIR OUT_DIR      (SRC: Monterra-*.png/.jpg, 3840x2160)
       -> OUT_DIR/Monterra-Login-<Motiv>-<Variante>.jpg  + farben.txt (Ersatzfarbe je Bild)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

# helle Bilder etwas stärker abdunkeln, damit weiße Schrift gut lesbar bleibt
DIM = {"Day": 0.74, "Light": 0.74, "Hell": 0.76, "Night": 0.92, "Dark": 0.92, "Dunkel": 0.95}


def login(src):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    f = 8                                            # blur in a smaller copy – fast and very smooth
    small = im.resize((w // f, h // f), Image.LANCZOS).filter(ImageFilter.GaussianBlur(60 / f))
    big = np.asarray(small.resize((w, h), Image.BICUBIC), dtype=np.float32)
    variant = Path(src).stem.split("-")[-1]
    big *= DIM.get(variant, 0.85)
    rng = np.random.default_rng(1)
    big += rng.uniform(-1.2, 1.2, big.shape).astype(np.float32)   # dither: no banding in JPEG
    out = Image.fromarray(np.clip(big + 0.5, 0, 255).astype(np.uint8))
    mean = tuple(int(v) for v in np.asarray(small, dtype=np.float32).reshape(-1, 3).mean(0) * DIM.get(variant, 0.85))
    return out, "#%02X%02X%02X" % mean


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    lines = []
    for f in sorted(list(src.glob("Monterra-*.png")) + list(src.glob("Monterra-*.jpg"))):
        if f.stem.startswith("Monterra-Login"):
            continue
        name = "Monterra-Login-" + f.stem[len("Monterra-"):] + ".jpg"
        im, col = login(f)
        im.save(dst / name, quality=90, subsampling=0, optimize=True)
        lines.append(f"{name} {col}")
        print("written", name, col)
    (dst / "farben.txt").write_text("\n".join(lines) + "\n")
