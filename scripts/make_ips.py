#!/usr/bin/env python3
"""Genera parches/Taloon_ESP_traduccion.ips comparando la ROM base EN con out/rom_es.sfc.

IPS clasico (solo stdlib): cabecera "PATCH", registros de offset 3 B big-endian +
tamano 2 B big-endian + datos, fin "EOF". Fusiona diferencias separadas por huecos
<= GAP bytes. Valida aplicando el parche a una copia de la base y comparando.

Uso: python3 scripts/make_ips.py
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, '..')
EN = os.path.join(ROOT, 'Torneko_(base_inglesa_075a)_ingles_DD099.sfc')
ES = os.path.join(ROOT, 'out', 'rom_es.sfc')
IPS = os.path.join(ROOT, 'parches', 'Taloon_ESP_traduccion.ips')
GAP = 16


def diff_runs(a, b, gap=GAP):
    """[(offset, longitud)] de tramos distintos, fusionando huecos <= gap."""
    runs = []
    for i in range(len(a)):
        if a[i] == b[i]:
            continue
        if runs and i - (runs[-1][0] + runs[-1][1]) <= gap:
            runs[-1][1] = i + 1 - runs[-1][0]
        else:
            runs.append([i, 1])
    return runs


def build(a, b):
    out = bytearray(b'PATCH')
    for off, ln in diff_runs(a, b):
        while ln:
            n = min(ln, 0xFFFF)
            out += off.to_bytes(3, 'big') + n.to_bytes(2, 'big') + b[off:off + n]
            off += n
            ln -= n
    out += b'EOF'
    return bytes(out)


def apply_ips(rom, ips):
    rom = bytearray(rom)
    pos = 0
    assert ips[pos:pos + 5] == b'PATCH', 'falta cabecera PATCH'
    pos += 5
    while True:
        hdr = ips[pos:pos + 3]
        if len(hdr) < 3 or hdr == b'EOF':
            break
        off = int.from_bytes(hdr, 'big')
        sz = int.from_bytes(ips[pos + 3:pos + 5], 'big')
        pos += 5
        if sz == 0:  # registro RLE
            rl = int.from_bytes(ips[pos:pos + 2], 'big')
            pos += 2
            rom[off:off + rl] = ips[pos:pos + 1] * rl
            pos += 1
        else:
            rom[off:off + sz] = ips[pos:pos + sz]
            pos += sz
    return bytes(rom)


def main():
    a = open(EN, 'rb').read()
    b = open(ES, 'rb').read()
    if len(a) != len(b):
        print('ERROR: tamanos distintos (%d vs %d); sin soporte de expansion'
              % (len(a), len(b)))
        return 1
    ips = build(a, b)
    with open(IPS, 'wb') as f:
        f.write(ips)
    patched = apply_ips(a, ips)
    ok = patched == b
    print('escrito %s (%d bytes); base %d, ES %d' % (IPS, len(ips), len(a), len(b)))
    print('validacion IPS: %s' % ('OK (identico a out/rom_es.sfc)' if ok else 'FALLO'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
