# Torneko no Daibōken: Fushigi no Dungeon — Spanish Fan Translation

A complete Spanish translation of the SNES roguelike
*Torneko no Daibōken: Fushigi no Dungeon* (Chunsoft / Enix, 1993), built on top
of the English fan patch by **Magic Destiny (v0.75a)** + **DD099**.

## Status

- **Translation: 100%** — all 1,197 message strings of the game script are
  translated and validated (control tokens, message length, and per-line pixel
  width against the English original).
- **New glyphs added to the game's font**: lowercase accents (á é í ó ú ü),
  ñ, opening punctuation (¿ ¡) and accented capitals (Á Í Ó).
- **Verified on emulator** (Mesen): battle messages, dialog and item text render
  correctly, including accents and inverted punctuation.

## Repository contents

| Path | Description |
| --- | --- |
| `scripts/` | Python 3 build pipeline and reverse-engineering tools (standard library only) |
| `scripts/translation_part*.txt` | The Spanish translation itself — the editable source of truth |
| `docs/README.md` | Technical notes: text encoding, font format, pointer tables, tooling |

## What is *not* in this repository

To respect the game's copyright, this repository ships **no ROMs, no IPS
patches, no extracted original text and no screenshots**. To build the
translation you need your own legally obtained copy of:

1. The SNES ROM of *Torneko no Daibōken: Fushigi no Dungeon*.
2. The English fan patch (Magic Destiny 0.75a + DD099) applied to that ROM.

The scripts expect the patched ROM at the repository root, named:

```
Torneko_(base_inglesa_075a)_ingles_DD099.sfc
```

## How to use

1. **Get the base ROM**: your own copy of *Torneko no Daibōken: Fushigi no
   Dungeon* with the English fan patch (Magic Destiny 0.75a + DD099) applied.
2. **Build the Spanish ROM**: follow [Building](#building) below.
   `scripts/insert.py` produces `out/rom_es.sfc`, ready to play in any SNES
   emulator (verified with Mesen).
3. **Or share it as a patch**: `scripts/make_ips.py` generates
   `parches/Taloon_ESP_traduccion.ips`, which can be applied to the
   English-patched ROM with any standard IPS patcher, e.g.
   [Flips](https://github.com/Alcaro/Flips)
   (`flips --apply patch.ips base.sfc out.sfc`) or Lunar IPS.

## Building

```bash
mkdir -p out parches
python3 scripts/insert.py       # rebuilds the ROM with the Spanish text -> out/rom_es.sfc
python3 scripts/translate.py    # (optional) validates the translation -> out/strings_es.txt
python3 scripts/make_ips.py     # (optional) generates a distribution IPS patch -> parches/
```

Only the Python 3 standard library is required.

## Tools

- `scripts/escodes.py` — message encoder/decoder and the 12 new Spanish glyphs.
- `scripts/extract.py` — static extraction of all text from the ROM.
- `scripts/insert.py` — repacks the translated strings and rebuilds the ROM.
- `scripts/make_ips.py` — generates and validates an IPS patch against the base ROM.
- `scripts/make_testrom.py` — builds a test ROM with crafted messages for tracing.
- `scripts/readscreen.py` — OCR: transcribes emulator screenshots back to text.
- `scripts/d65.py` — minimal 65816 disassembler used during the research.

## Credits & legal

- *Torneko no Daibōken: Fushigi no Dungeon* © Chunsoft / Enix. All game assets,
  characters and original text belong to their respective owners.
- English base patch: **Magic Destiny** (v0.75a) and **DD099**.
- This is a non-commercial fan project, not affiliated with or endorsed by the
  copyright holders. It is shared for preservation and accessibility purposes
  only — please own the game before using it.
