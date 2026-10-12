#!/usr/bin/env python3
"""Extractor estatico de cadenas de Torneko (base inglesa DD099).

- Tabla A: 0x38000, registros de 3 bytes [lo,hi,bank] a $30-$33:8000+
  (1197 entradas; se detecta el fin por la racha de punteros +1 de la tabla B).
- Tabla B: racha de punteros +1 (mismo formato) a un sub-pool en $32:BA4B+.
- Pool banco 7: 0x39869-0x3FFFF, mensajes separados por FF / FE FF (sin tabla).

Decodificacion (ver LEEME #3):
  00 = espacio; F5-FD xx = control con 1 parametro; FE FF o FF = fin;
  cualquier otro byte = glifo (indice = byte-1), texto en glyph_map.json
  (los no mapeados salen como {XX}).

Salidas en ../out/: strings_en.txt, strings_pool_bank7.txt, codes.tsv, codes_atlas.txt
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROM_PATH = os.path.join(BASE, '..', 'Torneko_(base_inglesa_075a)_ingles_DD099.sfc')
OUT_DIR = os.path.join(BASE, '..', 'out')
MAP_PATH = os.path.join(BASE, 'glyph_map.json')

PTR_BASE = 0x38000
POOL_START = 0x39869          # file offset; banco 7
POOL_BANK = 0x07
T, S, DB = 0x150000, 0x150606, 0x150C0C
NG = 771

ANCHORS = [
    (0x30, 0x804C, 'Inflicted [F9 10] damage.[SE][FIN]'),
    (0x30, 0x82C0, '[FB 00] whomped [FB 00]![SE][FIN]'),
    # en pantalla: "Equipped Steel⬡..." ("Steel" viene de la ref [FB 84])
    (0x30, 0x8177, 'Equipped [FB 84].[FD 29 00]..[SE][FIN]'),
]


def foff(bank, addr):
    return (bank & 0x3F) * 0x8000 + (addr - 0x8000)


def load(rom):
    offs = [rom[T + i * 2] | (rom[T + i * 2 + 1] << 8) for i in range(NG)]
    sizes = [rom[S + i * 2] | (rom[S + i * 2 + 1] << 8) for i in range(NG)]

    def glyph(code):
        """(ancho_px, filas, [filas de pixeles 0/1]) del codigo de mensaje."""
        i = code - 1
        o = offs[i]
        o = DB + o  # el juego siempre usa $2A8C0C + T (ver $02:CC2C-CC3D)
        w, rows = sizes[i] & 0xFF, sizes[i] >> 8
        img = []
        for r in range(rows):
            b0, b1 = rom[o + r * 2], rom[o + r * 2 + 1]
            word = b0 | (b1 << 8)  # little-endian; píxel 0 = bit 15 (MSB)
            img.append([(word >> (15 - b)) & 1 for b in range(min(w, 16))])
        return w, rows, img

    return glyph


def parse_pointers(rom):
    """Devuelve (tabla A, tabla B) como listas de (banco, direccion)."""
    recs = []
    o = PTR_BASE
    while o + 3 <= len(rom):
        lo, hi, bk = rom[o], rom[o+1], rom[o+2]
        a = lo | (hi << 8)
        if not (0x30 <= bk <= 0x3F and a >= 0x8000):
            break
        recs.append((bk, a))
        o += 3
    # tabla B = primera racha larga de +1 consecutivos
    cut = None
    i = 1
    while i < len(recs):
        if recs[i][0] == recs[i-1][0] and recs[i][1] == recs[i-1][1] + 1:
            j = i
            while j < len(recs) and recs[j][0] == recs[j-1][0] and recs[j][1] == recs[j-1][1] + 1:
                j += 1
            if j - (i - 1) >= 50:
                cut = i - 1
                break
            i = j
        else:
            i += 1
    if cut is None:
        return recs, []
    return recs[:cut], recs[cut:]


STYLE = {0xF5: '[S5]', 0xF6: '[S6]', 0xF7: '[S7]', 0xF8: '[S8]', 0xFE: '[SE]'}


def decode(rom, bank, addr, gmap, used):
    """Gramatica de la ROM (verificada en handlers $02:C5BE+):
       00 espacio; 01-EF glifo; F0-F3 +1B glifo extendido; F4 +2B glifo;
       F5-F8/FE marcador de estilo (1B); F9 +1B variable; FA 1B;
       FB +1B cadena referenciada; FC +1B; FD +2B; FF fin.
    """
    f = foff(bank, addr)
    out = []
    p = f
    while p < len(rom) and p - f < 4000:
        b = rom[p]
        if b == 0xFF:
            out.append('[FIN]')
            return ''.join(out), rom[f:p + 1]
        if b in STYLE:
            out.append(STYLE[b])
            p += 1
            continue
        if 0xF0 <= b <= 0xF3:
            out.append('[F%d %02X]' % (b - 0xF0, rom[p+1]))
            p += 2
            continue
        if b == 0xF4:
            out.append('[F4 %02X %02X]' % (rom[p+1], rom[p+2]))
            p += 3
            continue
        if b in (0xF9, 0xFB, 0xFC):
            out.append('[%02X %02X]' % (b, rom[p+1]))
            p += 2
            continue
        if b == 0xFD:
            out.append('[FD %02X %02X]' % (rom[p+1], rom[p+2]))
            p += 3
            continue
        if b == 0xFA:
            out.append('[FA]')
            p += 1
            continue
        if b == 0x00:
            out.append(' ')
        else:
            used.add(b)
            out.append(gmap.get('%02X' % b, '{%02X}' % b))
        p += 1
    out.append('[SIN FIN]')
    return ''.join(out), rom[f:p]


def table_b_starts(rom, entriesB):
    """Inicios reales de mensajes en la tabla B (+1): solo tras un terminador."""
    out = []
    for bk, a in sorted(set(entriesB), key=lambda x: x[1]):
        if rom[foff(bk, a) - 1] == 0xFF:
            out.append((bk, a))
    return out


def split_pool(rom, start, end):
    out = []
    s = start
    p = start
    while p < end:
        b = rom[p]
        if b == 0xFF:
            out.append((s, p + 1))
            s = p + 1
        elif b == 0xFE and p + 1 < end and rom[p+1] == 0xFF:
            out.append((s, p + 2))
            s = p + 2
            p += 1
        p += 1
    return [(a, b) for a, b in out if b > a]


def main():
    rom = open(ROM_PATH, 'rb').read()
    glyph = load(rom)
    gmap = json.load(open(MAP_PATH)) if os.path.exists(MAP_PATH) else {}
    used = set()

    entriesA, entriesB = parse_pointers(rom)

    rows = []  # (bank, addr, texto)
    for bk, a in entriesA:
        text, _ = decode(rom, bk, a, gmap, used)
        rows.append((bk, a, text))
    setA = set(entriesA)
    for bk, a in table_b_starts(rom, entriesB):
        if (bk, a) not in setA:
            text, _ = decode(rom, bk, a, gmap, used)
            rows.append((bk, a, text))

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, 'strings_en.txt'), 'w') as fh:
        fh.write('# cadenas de mensajes: direccion CPU + texto\n')
        fh.write('# [F9 10] control con parametro; {XX} codigo sin mapear; [FIN] fin\n')
        fh.write('# F5-F8/FE xx imprimen el glifo xx (variante de estilo); F9/FB/FC/FD son refs/variables/iconos\n')
        for bk, a, text in rows:
            fh.write('$%02X:%04X\t%s\n' % (bk, a, text))

    pool = []
    for a, b in split_pool(rom, POOL_START, 0x40000):
        text, _ = decode(rom, POOL_BANK, a - 0x38000 + 0x8000, gmap, used)
        pool.append((a - 0x38000 + 0x8000, text))
    with open(os.path.join(OUT_DIR, 'strings_pool_bank7.txt'), 'w') as fh:
        fh.write('# pool banco 7 (0x39869+): mensajes sin tabla de punteros conocida\n')
        for a, text in pool:
            fh.write('$07:%04X\t%s\n' % (a, text))

    icon_path = os.path.join(BASE, 'icon_codes.json')
    icons = json.load(open(icon_path, encoding='utf-8')) if os.path.exists(icon_path) else {}
    codes = sorted(used)
    with open(os.path.join(OUT_DIR, 'codes.tsv'), 'w') as fh:
        fh.write('codigo\ttexto\tancho_px\tfilas\tdescripcion\n')
        for c in codes:
            w, h, _ = glyph(c)
            key = '%02X' % c
            if key in gmap:
                desc = 'letra'
            elif key in icons:
                desc = icons[key]
            else:
                desc = 'pool muerto'
            fh.write('%02X\t%s\t%d\t%d\t%s\n' % (c, gmap.get(key, ''), w, h, desc))

    with open(os.path.join(OUT_DIR, 'codes_atlas.txt'), 'w') as fh:
        fh.write('# glifos de los codigos usados; texto conocido tras los tamanos\n')
        for c in codes:
            w, h, img = glyph(c)
            art = '|'.join(''.join('#' if v else ' ' for v in row).rstrip() or ' ' for row in img)
            fh.write('%02X w=%02d h=%02d %s  %s\n' % (c, w, h, gmap.get('%02X' % c, ''), art))

    print('tabla A: %d cadenas; tabla B: %d nuevas; pool banco 7: %d' % (
        len(entriesA), len(rows) - len(entriesA), len(pool)))
    print('codigos usados: %d; mapeados: %d; sin mapear: %d' % (
        len(codes), len([c for c in codes if '%02X' % c in gmap]), 
        len([c for c in codes if '%02X' % c not in gmap])))

    ok = True
    for bk, a, exp in ANCHORS:
        text, _ = decode(rom, bk, a, gmap, set())
        if exp is None:
            print('ancla $%02X:%04X = %s' % (bk, a, text))
            continue
        good = text == exp
        ok = ok and good
        print('ancla $%02X:%04X %s: %s' % (bk, a, 'OK' if good else 'FALLA', text))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
