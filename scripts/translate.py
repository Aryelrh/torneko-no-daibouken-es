#!/usr/bin/env python3
"""Vuelca out/strings_es.txt a partir de las traducciones y valida.

- Fuente de traducciones: scripts/translation_part*.txt y scripts/trans_es.tsv
  (lineas "$XX:YYYY<TAB>texto ES"). Si falta una traduccion, se usa el
  ingles original (se avisa).
- Valida: mismos tokens de control que el ingles (salvo [SE], que puede
  moverse/anadirse para reencuadrar); tokens [FB]/[F9]/[FC]/[FD]/[F*] en
  el mismo orden; ancho en pixeles por linea <= limite; unidades <= 1024.

Uso: python3 scripts/translate.py
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from escodes import Encoder, build_es_glyphs, ES_CODES  # noqa: E402
from extract import decode, parse_pointers, foff  # noqa: E402

ROMPATH = os.path.join(BASE, '..', 'Torneko_(base_inglesa_075a)_ingles_DD099.sfc')
OUT = os.path.join(BASE, '..', 'out', 'strings_es.txt')
PTR = 0x38000
NMSG = 1197
MAXPX = 232


def load_translations():
    import glob
    trans = {}
    for p in sorted(glob.glob(os.path.join(BASE, 'translation_part*.txt'))) + \
            sorted(glob.glob(os.path.join(BASE, 'trans_es.tsv'))):
        for line in open(p, encoding='utf-8'):
            line = line.rstrip('\n')
            if line and not line.startswith('#') and '\t' in line:
                a, t = line.split('\t', 1)
                a = a.strip()
                if a.startswith('$'):
                    trans[a] = t
    return trans


def tokens(text, drop_se=False):
    import re
    out = []
    for m in re.finditer(r'\[[^\]]+\]|\{[0-9A-F]{2}\}', text):
        t = m.group(0)
        if drop_se and t == '[SE]':
            continue
        if t == '[FIN]':
            continue
        out.append(t)
    return out


def px_widths(text, enc, glyph_w):
    """Anchos en px por linea (saltos en [S5]-[S8]/[SE]); None si token raro."""
    lines = [0]
    i = 0
    while i < len(text):
        c = text[i]
        if c == '[':
            j = text.index(']', i)
            tok = text[i+1:j]
            if tok in ('S5', 'S6', 'S7', 'S8', 'SE'):
                lines.append(0)
            i = j + 1
            continue
        if c == '{':
            j = text.index('}', i)
            w = glyph_w.get(int(text[i+1:j], 16), 8)
            lines[-1] += w
            i = j + 1
            continue
        two = text[i:i+2]
        if i+1 < len(text) and two in enc.rev:
            code = enc.rev[two]
            lines[-1] += glyph_w.get(code, 8)
            i += 2
            continue
        if c in enc.rev:
            lines[-1] += glyph_w.get(enc.rev[c], 8)
            i += 1
            continue
        lines[-1] += 8
        i += 1
    return lines


def main():
    rom = open(ROMPATH, 'rb').read()
    enc = Encoder()
    entradas, _ = parse_pointers(rom)
    trans = load_translations()

    # tabla de anchos de glifos (incluye nuevos)
    from escodes import font_tables
    offs, sizes = font_tables(rom)
    glyph_w = {}
    for i in range(771):
        glyph_w[i + 1] = sizes[i] & 0xFF
    glyphs = build_es_glyphs(rom)
    for ch, code in ES_CODES.items():
        glyph_w[code] = glyphs[ch][0]

    faltan = 0
    problemas = []
    lines_out = []
    for k, (bk, a) in enumerate(entradas):
        en, _ = decode(rom, bk, a, json.load(open(os.path.join(BASE, 'glyph_map.json'))), set())
        key = '$%02X:%04X' % (bk, a)
        es = trans.get(key)
        if es is None:
            faltan += 1
            es = en
        t_en, t_es = tokens(en, True), tokens(es, True)
        if t_en != t_es:
            problemas.append('%s tokens: EN %s != ES %s' % (key, t_en, t_es))
        b = enc.encode(es)
        if len(b) > 1024:
            problemas.append('%s unidades %d > 1024' % (key, len(b)))
        ws_en = px_widths(en, enc, glyph_w)
        ws = px_widths(es, enc, glyph_w)
        lim = max(max(ws_en) + 8, 224)
        if max(ws) > lim:
            problemas.append('%s ancho %dpx > %d (EN %d)' % (key, max(ws), lim, max(ws_en)))
        lines_out.append('%s\t%s' % (key, es))

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('# traduccion ES: direccion CPU + texto\n')
        fh.write('# [FB]/[F9]/[FC]/[FD]/[F0-F4] = refs/iconos; {XX} icono inline; [FIN] fin\n')
        fh.write('# [S5]-[S8] parrafo/color; [SE] salto de linea\n')
        for l in lines_out:
            fh.write(l + '\n')
    print('escrito %s (%d cadenas, %d sin traducir)' % (OUT, len(lines_out), faltan))
    if problemas:
        print('PROBLEMAS (%d):' % len(problemas))
        for p in problemas[:60]:
            print('  ' + p)
        return 1
    print('validacion OK: tokens, unidades y anchos')
    return 0


if __name__ == '__main__':
    sys.exit(main())
