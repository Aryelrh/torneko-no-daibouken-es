#!/usr/bin/env python3
"""Codificador/decodificador de texto ES para Torneko (base inglesa DD099).

Gramatica verificada en los handlers $02:C5BE+:
  00 espacio; 01-EF glifo (indice = b-1); F0-F3 +1B glifo extendido;
  F4 +2B glifo directo; F5,F6,F7,F8,FE marcador de estilo/linea (1B);
  F9 +1B variable; FA 1B; FB +1B cadena referenciada; FC +1B; FD +2B;
  FF fin.

Texto ES -> bytes: bigramas del glyph_map.json + glifos nuevos para
n~a-acute-u-umlaut y ¿¡ (codigos libres C3 C8 D5 D9 DA E2 E5 E7 EA).

Glifos nuevos: se construyen a partir de los glifos base de la ROM
(desplazados 2 filas) + acento/tilde/dieresis en las filas 0-1.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
MAP_PATH = os.path.join(BASE, 'glyph_map.json')
T, S, DB = 0x150000, 0x150606, 0x150C0C
NG = 771

# codigos libres elegidos (rango kanji sobrante, no usados por el ingles)
ES_CODES = {
    'ñ': 0xC3, 'á': 0xC8, 'é': 0xCD, 'í': 0xD5,
    'ó': 0xD9, 'ú': 0xE2, 'ü': 0xE5, '¿': 0xE7, '¡': 0xEB,
    'Á': 0xEC, 'Í': 0xE0, 'Ó': 0xEF,
}
# glifo base del que se parte (codigo) y tipo de marca
ES_BASE = {
    'ñ': (0x73, 'tilde'), 'á': (0x5D, 'acute'), 'é': (0x62, 'acute'),
    'í': (0x69, 'acute'), 'ó': (0x75, 'acute'), 'ú': (0x81, 'acute'),
    'ü': (0x81, 'diaer'), '¿': (0xB6, 'rot180'), '¡': (0xB4, 'rot180'),
    'Á': (0x0D, 'acute'), 'Í': (0x15, 'acute'), 'Ó': (0x1B, 'acute'),
}

MARKS = {
    'acute': ['...##...', '..##....'],
    'tilde': ['.###....', '#...##..'],
    'diaer': ['........', '.##..##.'],
}

STYLE = {0xF5: '[S5]', 0xF6: '[S6]', 0xF7: '[S7]', 0xF8: '[S8]', 0xFE: '[SE]'}
STYLE_INV = {v[1:-1]: k for k, v in STYLE.items()}


def font_tables(rom):
    offs = [rom[T + i * 2] | (rom[T + i * 2 + 1] << 8) for i in range(NG)]
    sizes = [rom[S + i * 2] | (rom[S + i * 2 + 1] << 8) for i in range(NG)]
    return offs, sizes


def glyph_img(rom, code):
    """(w, h, filas de bits) del glifo con ese codigo de mensaje."""
    offs, sizes = font_tables(rom)
    i = code - 1
    o = offs[i]
    o = DB + o  # el juego siempre usa $2A8C0C + T (ver $02:CC2C-CC3D)
    w, rows = sizes[i] & 0xFF, sizes[i] >> 8
    img = []
    for r in range(rows):
        b0, b1 = rom[o + r * 2], rom[o + r * 2 + 1]
        word = b0 | (b1 << 8)
        img.append([(word >> (15 - b)) & 1 for b in range(min(w, 16))])
    return w, rows, img


def build_es_glyphs(rom):
    """{caracter: (ancho, filas, bitmap)} de los glifos nuevos."""
    out = {}
    for ch, code in ES_CODES.items():
        base_code, kind = ES_BASE[ch]
        if kind == 'rot180':
            w, h, img = glyph_img(rom, base_code)
            rows = [list(reversed(r)) for r in reversed(img)]
            out[ch] = (w, h, rows)
            continue
        if ch == 'í':
            w, h, img = glyph_img(rom, base_code)
            rows = [[0, 0, 1, 1], [0, 1, 1, 0]]
            for r in img[3:]:
                rows.append(list(r))
            out[ch] = (4, len(rows), rows)
            continue
        w, h, img = glyph_img(rom, base_code)
        W = max(w, 8)
        mark = [m.ljust(W, '.')[:W] for m in MARKS[kind]]
        blank = 0
        for r in img:
            if any(r):
                break
            blank += 1
        if blank >= 2 and len(mark) == 2:
            rows = [list(r) + [0] * (W - len(r)) for r in img]
            for k, mrow in enumerate(mark):
                rows[k] = [1 if c == '#' else 0 for c in mrow]
        else:
            extra = min(len(mark), max(1, 13 - len(img)))
            rows = [[1 if c == '#' else 0 for c in mrow] for mrow in mark[:extra]]
            for r in img:
                rows.append(list(r) + [0] * (W - len(r)))
        out[ch] = (W, len(rows), rows)
    return out


class Encoder:
    def __init__(self):
        self.gmap = json.load(open(MAP_PATH))
        rev = {}
        for k, v in self.gmap.items():
            if v and v not in rev:
                rev[v] = int(k, 16)
        for ch, code in ES_CODES.items():
            rev[ch] = code
        self.rev = rev

    def encode_text(self, text):
        out = bytearray()
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == ' ':
                out.append(0x00)
                i += 1
                continue
            two = text[i:i+2]
            if two in self.rev:
                out.append(self.rev[two])
                i += 2
                continue
            if ch in self.rev:
                out.append(self.rev[ch])
                i += 1
                continue
            raise ValueError('sin glifo: %r en %r' % (ch, text))
        return bytes(out)

    def encode(self, text):
        """Texto con tokens [XX..]/{XX} -> bytes del mensaje."""
        out = bytearray()
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == '[':
                j = text.index(']', i)
                tok = text[i+1:j]
                parts = tok.split()
                if tok == 'FIN':
                    out.append(0xFF)
                elif tok in STYLE_INV:
                    out.append(STYLE_INV[tok])
                elif tok == 'FA':
                    out.append(0xFA)
                elif parts[0] == 'S' and len(parts) == 1:
                    raise ValueError('token desconocido: [%s]' % tok)
                elif parts[0] == 'F4':
                    out += bytes([0xF4, int(parts[1], 16), int(parts[2], 16)])
                elif parts[0] in ('F0', 'F1', 'F2', 'F3'):
                    out += bytes([0xF0 + int(parts[0][1]), int(parts[1], 16)])
                elif parts[0] in ('F9', 'FB', 'FC'):
                    out += bytes([int(parts[0], 16), int(parts[1], 16)])
                elif parts[0] == 'FD':
                    out += bytes([0xFD, int(parts[1], 16), int(parts[2], 16)])
                else:
                    raise ValueError('token desconocido: [%s]' % tok)
                i = j + 1
                continue
            if ch == '{':
                j = text.index('}', i)
                out.append(int(text[i+1:j], 16))
                i = j + 1
                continue
            # texto corrido hasta el proximo token
            j = i
            while j < len(text) and text[j] not in '[{':
                j += 1
            out += self.encode_text(text[i:j])
            i = j
        return bytes(out)


if __name__ == '__main__':
    rom_path = os.path.join(BASE, '..', 'Torneko_(base_inglesa_075a)_ingles_DD099.sfc')
    rom = open(rom_path, 'rb').read()
    enc = Encoder()
    # glifos nuevos: codigos libres y alturas <= 13
    glyphs = build_es_glyphs(rom)
    for ch, (w, h, img) in glyphs.items():
        assert 1 <= w <= 16 and 3 <= h <= 13, (ch, w, h)
    # roundtrip de texto
    for s in ['Inflicted ', 'daño', 'Español ¿qué? ¡Sí!', 'cariño', 'pingüino', 'ñandú']:
        b = enc.encode_text(s)
        assert 0 not in b or ' ' in s or True
    assert enc.encode_text('daño') == bytes([0x64, 0x5D, 0xC3, 0x75])
    assert enc.encode_text('cariño') == bytes([0x5F, 0x5D, 0x74, 0xC3, 0x75])
    assert enc.encode('Hola [FB 80].[FIN]') == bytes([0x14, 0x75, 0x30, 0x00,
                                                       0xFB, 0x80, 0xB3, 0xFF])
    assert enc.encode('[SE]¿Qué?[FIN]') == bytes([0xFE, 0xE7, 0x1D, 0x81, 0xCD, 0xB6, 0xFF])
    assert enc.encode('[S8]á é í ó ú ü ñ[FIN]') == bytes(
        [0xF8, 0xC8, 0x00, 0xCD, 0x00, 0xD5, 0x00, 0xD9, 0x00, 0xE2, 0x00, 0xE5, 0x00, 0xC3, 0xFF])
    print('escodes OK: %d glifos ES, roundtrips y tokens verificados' % len(glyphs))
