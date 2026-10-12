#!/usr/bin/env python3
"""Reinsercion del texto ES en la ROM (base inglesa DD099).

- Reempaqueta las 1197 cadenas de tabla A (0x38000, registros de 3 B
  [lo,hi,bank]) empezando en $30:8000, dentro de los 4 bancos $30-$33.
- Actualiza tabla A y tabla B (0x38E07, 886 punteros por caracter de las
  9 cadenas $32:BA03-$32:BDBF; se regenera por indice de glifo).
- Anade los 9 glifos ES a la fuente (banco $2A): offsets T@0x150000,
  tamanos S@0x150606, bitmaps al final del banco (0x154A00+).
- Traducciones: scripts/translation_part*.txt / scripts/trans_es.tsv
  (lineas "$XX:YYYY<TAB>texto ES"); lo no traducido cae al ingles.

Uso: python3 scripts/insert.py [salida.sfc]
"""
import glob
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from escodes import Encoder, build_es_glyphs, ES_CODES  # noqa: E402

ROMPATH = os.path.join(BASE, '..', 'Torneko_(base_inglesa_075a)_ingles_DD099.sfc')
OUT_DEF = os.path.join(BASE, '..', 'out', 'rom_es.sfc')

PTR = 0x38000
NMSG = 1197
TB_START = 0x38E07
TB_N = 886
TB_OLD = 0x32 * 0x8000 + (0xBA4B - 0x8000)
BLOB_START = 0x180000
BLOB_LIMIT = 0x1A0000
FONT_FREE = 0x154A00
T, S = 0x150000, 0x150606


def foff(bank, addr):
    return (bank & 0x3F) * 0x8000 + (addr - 0x8000)


def msg_len(rom, bank, addr):
    f = foff(bank, addr)
    p = f
    while p < len(rom):
        b = rom[p]
        if b == 0xFF:
            return p - f + 1
        if b in (0xF5, 0xF6, 0xF7, 0xF8, 0xFE):
            p += 1
        elif 0xF0 <= b <= 0xF3 or b in (0xF9, 0xFB, 0xFC):
            p += 2
        elif b == 0xF4:
            p += 3
        elif b == 0xFD:
            p += 3
        elif b == 0xFA:
            p += 1
        else:
            p += 1
    return p - f


def load_translations():
    trans = {}
    paths = sorted(glob.glob(os.path.join(BASE, 'translation_part*.txt')))
    paths += sorted(glob.glob(os.path.join(BASE, 'trans_es.tsv')))
    for p in paths:
        for line in open(p, encoding='utf-8'):
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            if '\t' not in line:
                continue
            a, t = line.split('\t', 1)
            a = a.strip()
            if not a.startswith('$'):
                continue
            trans[a] = t
    return trans


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else OUT_DEF
    rom = bytearray(open(ROMPATH, 'rb').read())
    enc = Encoder()
    trans = load_translations()

    old = []       # (bank, addr, len)
    new = []       # bytes
    for k in range(NMSG):
        o = PTR + k * 3
        bk, lo, hi = rom[o+2], rom[o], rom[o+1]
        addr = lo | (hi << 8)
        old.append((bk, addr, msg_len(rom, bk, addr)))
        key = '$%02X:%04X' % (bk, addr)
        txt = trans.get(key)
        b = enc.encode(txt) if txt is not None else bytes(
            rom[foff(bk, addr):foff(bk, addr) + old[-1][2]])
        if not b or b[-1] != 0xFF:
            b = b + b'\xFF'
        new.append(b)

    blob = b''.join(new)
    if BLOB_START + len(blob) > BLOB_LIMIT:
        print('ERROR: el texto ES no cabe: %d bytes (max %d)' % (
            len(blob), BLOB_LIMIT - BLOB_START))
        return 1

    pos = BLOB_START
    new_addr = []
    for b in new:
        new_addr.append(pos)
        pos += len(b)

    rom[BLOB_START:BLOB_START + len(blob)] = blob

    for k in range(NMSG):
        na = new_addr[k]
        bank, addr = 0x30 + (na - BLOB_START) // 0x8000, \
            0x8000 + (na - BLOB_START) % 0x8000
        o = PTR + k * 3
        rom[o], rom[o+1], rom[o+2] = addr & 0xFF, addr >> 8, bank

    # tabla B: puntero por caracter de las 9 cadenas contiguas BA03-BDC6
    span = [(k, old[k][1], old[k][1] + old[k][2])
            for k in range(NMSG) if old[k][0] == 0x32
            and 0xBA03 <= old[k][1] < 0xBDC6]
    span.sort(key=lambda x: x[1])
    for i in range(TB_N):
        x = TB_OLD + i
        m = None
        for j, (k, s, e) in enumerate(span):
            if s <= x < e:
                m = j
                break
        if m is None:
            continue
        k = span[m][0]
        loc = x - span[m][1]
        if loc >= len(new[k]):
            loc = len(new[k]) - 1
        na = new_addr[k] + loc
        bank, addr = 0x30 + (na - BLOB_START) // 0x8000, \
            0x8000 + (na - BLOB_START) % 0x8000
        o = TB_START + i * 3
        rom[o], rom[o+1], rom[o+2] = addr & 0xFF, addr >> 8, bank

    # fuente: glifos ES al final del banco $2A
    glyphs = build_es_glyphs(rom)
    fo = FONT_FREE
    for ch, code in ES_CODES.items():
        w, h, img = glyphs[ch]
        i = code - 1
        off = fo
        for r in img:
            word = 0
            for b in range(min(w, 16)):
                if r[b]:
                    word |= 1 << (15 - b)
            rom[fo] = word & 0xFF
            rom[fo+1] = word >> 8
            fo += 2
        v = off - 0x150C0C
        rom[T + i*2] = v & 0xFF
        rom[T + i*2 + 1] = (v >> 8) & 0xFF
        rom[S + i*2] = w & 0xFF
        rom[S + i*2 + 1] = h & 0xFF

    open(out_path, 'wb').write(rom)
    print('escrito %s: %d cadenas, %d bytes de texto (%.1f%% del hueco)'
          % (out_path, NMSG, len(blob), 100.0 * len(blob) / (BLOB_LIMIT - BLOB_START)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
