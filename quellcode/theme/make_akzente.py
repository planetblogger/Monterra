#!/usr/bin/env python3
"""
Baut Monterra in allen 13 Akzentfarben und legt für jede Farbe nur die Dateien ab,
die sich von der blauen Grundfassung unterscheiden (spart rund 90 % Platz).

usage: make_akzente.py PAKET_THEMES_DIR      (z. B. …/Monterra/themes)
  -> THEMES/Monterra, THEMES/Monterra-Dark          (Blau, vollständig)
     THEMES/akzente/<Farbe>/Monterra[-Dark]/…       (nur Abweichungen)
"""
import filecmp
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import akzente  # noqa: E402

TMP = Path("/tmp/monterra-akzente")


def build(name):
    env = dict(os.environ, MONTERRA_AKZENT=name, MONTERRA_WORK=str(TMP / "work" / name),
               MONTERRA_DIST=str(TMP / "dist" / name))
    subprocess.run([sys.executable, str(HERE / "build.py")], env=env, check=True,
                   stdout=subprocess.DEVNULL)
    return name


if __name__ == "__main__":
    out = Path(sys.argv[1])
    shutil.rmtree(TMP, ignore_errors=True)
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(build, akzente.NAMES))
    base = TMP / "dist" / "Blau"
    for t in ("Monterra", "Monterra-Dark"):
        shutil.rmtree(out / t, ignore_errors=True)
        shutil.copytree(base / t, out / t, symlinks=True)
    shutil.rmtree(out / "akzente", ignore_errors=True)
    for name in akzente.NAMES:
        if name == "Blau":
            continue
        src = TMP / "dist" / name
        n = 0
        for f in src.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(src)
            b = base / rel
            if b.is_file() and filecmp.cmp(f, b, shallow=False):
                continue
            dst = out / "akzente" / name / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            n += 1
        print(f"{name}: {n} Dateien")
