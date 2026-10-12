#!/usr/bin/env python3
"""Lee el texto de una captura de Mesen emparejando los glifos de la fuente.

Uso:
  python3 scripts/readscreen.py out/trace4/m20600.png [...]       # transcribe
  python3 scripts/readscreen.py --frames 20450:20800 --dir out/trace4

Binariza la captura (ImageMagick a escala de grises), detecta las lineas de
texto de la caja inferior (excluyendo el borde) y hace matching greedy contra
los bitmaps de la fuente del ROM. Los codigos sin mapear salen como {XX}.
"""
import glob
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, '..')
sys.path.insert(0, BASE)
from extract import load, ROM_PATH  # noqa: E402
from escodes import build_es_glyphs, ES_CODES  # noqa: E402

W, H = 256, 224
X0, X1 = 12, 246
Y0, Y1 = 173, 210


def pixels(png):
    out = subprocess.run(['magick', png, '-depth', '8', 'gray:-'],
                         capture_output=True, check=True).stdout
    assert len(out) == W * H, len(out)
    return out


def lines_of(px):
    """[(x_ini, filas_bits)] por linea de texto (borde excluido)."""
    rows = []
    for y in range(Y0, Y1):
        n = sum(1 for x in range(X0, X1) if px[y * W + x] > 140)
        rows.append((y, n))
    lines = []
    cur = []
    for y, n in rows:
        if n > 2:
            cur.append(y)
        elif cur:
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return lines


def load_glyphs():
    rom = open(ROM_PATH, 'rb').read()
    glyph = load(rom)
    gmap = json.load(open(os.path.join(BASE, 'glyph_map.json')))
    cands = []  # (ancho, texto, variantes desplazadas)
    for code in range(1, 772):
        try:
            w, h, img = glyph(code)
        except Exception:
            continue
        if not any(any(r) for r in img):
            continue
        txt = gmap.get('%02X' % code, '{%02X}' % code)
        cands.append((w, txt, glyph_ints(w, h, img)))
    for ch, (w, h, img) in build_es_glyphs(rom).items():
        cands.append((w, ch, glyph_ints(w, h, img)))
    return cands


FW, FH = 22, 16   # campo de bits: columnas y filas (base abajo en FH-1)


def glyph_ints(w, h, img):
    """[(bits, area, mask)] del glifo para los 9 desplazamientos (dx, dy)."""
    out = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            bits = 0
            area = 0
            mask = 0
            for r in range(h):
                row = FH - 1 - (h - 1 - r) + dy
                for c in range(min(w, len(img[r]))):
                    mask |= 1 << (row * FW + c + 2 + dx)
                    if img[r][c]:
                        bits |= 1 << (row * FW + c + 2 + dx)
                        area += 1
            out.append((bits, area, mask))
    return out


def screen_int(px, bot, x):
    bits = 0
    for row in range(FH):
        y = bot - (FH - 1) + row
        if not (0 <= y < H):
            continue
        for col in range(FW):
            xx = x - 2 + col
            if 0 <= xx < W and px[y * W + xx] > 140:
                bits |= 1 << (row * FW + col)
    return bits


def match_line(px, rows, cands, thr=0.20):
    """Empareja glifos de izquierda a derecha con la base de la linea."""
    bot = max(rows)
    white = [any(px[y * W + x] > 140 for y in rows) for x in range(W)]
    text = ''
    x = next((xx for xx in range(X0, X1) if white[xx]), X1)
    end = None
    while x < X1 - 4:
        if end is not None:
            nx = end
            while nx < X1 and not white[nx]:
                nx += 1
            if nx >= X1:
                break
            if nx - end >= 3:
                text += ' '
            x = nx
        s = screen_int(px, bot, x)
        best = None
        for w, txt, variants in cands:
            if x + w > X1:
                continue
            for g, area, mask in variants:
                if not area:
                    continue
                score = (g ^ (s & mask)).bit_count() / area
                if best is None or score < best[0]:
                    best = (score, w, txt)
        if best is None or best[0] > thr:
            text += '?'
            break
        text += best[2]
        x += best[1]
        end = x
    return text.strip()


def read_frame(png, cands):
    px = pixels(png)
    out = []
    for rows in lines_of(px):
        out.append((max(rows), match_line(px, rows, cands)))
    return out


def main():
    args = sys.argv[1:]
    cands = load_glyphs()
    if '--frames' in args:
        rng = args[args.index('--frames') + 1]
        d = args[args.index('--dir') + 1] if '--dir' in args else 'out/trace4'
        a, b = rng.split(':')
        pats = []
        for f in sorted(glob.glob(os.path.join(d, 'm*.png'))):
            import re
            m = re.match(r'm(\d+)\.png$', os.path.basename(f))
            if not m:
                continue
            n = int(m.group(1))
            if int(a) <= n <= int(b):
                pats.append((n, f))
    else:
        pats = [(0, p) for p in args]
    for n, p in pats:
        txt = read_frame(p, cands)
        if any(t for _, t in txt):
            print('%s %s' % (n or os.path.basename(p), ' | '.join(t for _, t in txt)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
