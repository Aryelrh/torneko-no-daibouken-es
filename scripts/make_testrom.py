#!/usr/bin/env python3
"""Genera out/test_marcadores.sfc: rom_es.sfc con mensajes de batalla
parcheados con marcadores [S5-S8]/[SE] y filas de iconos {XX}, para
trazar su semantica real en Mesen (tareas 4/5). NO toca translation_part*.txt
ni out/rom_es.sfc; el test ROM se regenera con este script.

Uso: python3 scripts/make_testrom.py
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, '..')
sys.path.insert(0, BASE)
from extract import parse_pointers, foff, decode  # noqa: E402
from escodes import Encoder  # noqa: E402

EN = os.path.join(ROOT, 'Torneko_(base_inglesa_075a)_ingles_DD099.sfc')
ES = os.path.join(ROOT, 'out', 'rom_es.sfc')
OUT = os.path.join(ROOT, 'out', 'test_marcadores.sfc')
GMAP = os.path.join(BASE, 'glyph_map.json')

# Cada mensaje de batalla lleva un patron unico: letra + marcador + letra. Una
# captura identifica el mensaje por sus letras y muestra el efecto del marcador.
ICONOS = '{27}{28}{29}{2A}{2B}{2C}{2D}{2E}{2F}[FIN]'
ICONOS2 = '{A7}{A8}{B0}{B2}[FIN]'
TESTS = {
    '$30:82C0': 'LLMM[FIN]',      # control sin marcador
    '$30:81E9': '[S5]OO[FIN]',    # [S5] inicial
    '$30:8244': 'CC[S6]DD[FIN]',  # [S6] entre letras
    '$30:8255': 'II[S8]JJ[FIN]',  # [S8] entre letras
    '$30:803D': 'GG[S7]HH[FIN]',  # [S7] entre letras
    '$30:804C': 'EE[SE]FF[FIN]',  # [SE] entre letras
    '$30:833C': ICONOS,           # fila de iconos 27-2F
    '$30:8177': ICONOS2,          # iconos A7 A8 B0 B2
    '$30:82D2': ICONOS2,          # iconos A7 A8 B0 B2
    '$30:80B4': 'II[S8]JJ[FIN]',  # [S8] repetido
    '$30:8081': '[S8]II[FIN]',    # [S8] inicial
}


def main():
    en = open(EN, 'rb').read()
    es = bytearray(open(ES, 'rb').read())
    ent_en, _ = parse_pointers(en)
    ent_es, _ = parse_pointers(es)
    if len(ent_en) != len(ent_es):
        print('ERROR: tablas distintas (%d vs %d)' % (len(ent_en), len(ent_es)))
        return 1
    keys = ['$%02X:%04X' % (bk, a) for bk, a in ent_en]
    starts = sorted(foff(bk, a) for bk, a in ent_es)
    enc = Encoder()
    import json
    gmap = json.load(open(GMAP))

    for key in TESTS:
        if key not in keys:
            print('ERROR: %s no esta en tabla A' % key)
            return 1
        i = keys.index(key)
        bk, a = ent_es[i]
        f = foff(bk, a)
        nxt = next(s for s in starts if s > f)
        data = enc.encode(TESTS[key])
        if len(data) > nxt - f:
            print('ERROR: %s no cabe (%d > %d)' % (key, len(data), nxt - f))
            return 1
        es[f:f + len(data)] = data

    open(OUT, 'wb').write(bytes(es))

    ok = True
    for key, exp in TESTS.items():
        i = keys.index(key)
        bk, a = ent_es[i]
        text, _ = decode(es, bk, a, gmap, set())
        good = text == exp
        ok = ok and good
        print('%-9s %s -> %s' % (key, 'OK' if good else 'FALLA', text))
    print('escrito %s' % OUT)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
