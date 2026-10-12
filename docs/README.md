# Torneko no Daibouken — proyecto de traducción al español

## Estado actual (oct 2026)

**Traducción al español completada y verificada en pantalla.** Las 1197
cadenas de tabla A están traducidas (`scripts/translation_part*.txt`), validadas
(tokens/controles/anchos) y reinsertadas (`out/rom_es.sfc`). Ver §9.

**Sistema de texto inglés completamente resuelto.** Se usa la ROM inglesa de
referencia (`Torneko_(base_inglesa_075a)_ingles_DD099.sfc`). El esquema de
codificación final quedó descifrado y verificado en pantalla: **1 byte = 1
glifo** (índice de fuente + 1), sin diccionario ni bitstream.

### 1. Parche inglés 0.99 funcional (material de referencia)

(igual que antes, sin cambios)

- `parches/Taloon_ESP_base_inglesa_DD099_fix.ips` — IPS corregido (aplicar a
  la ROM inglesa base "Magic Destiny 0.75a" 2 MB, NO a la japonesa).
- `Torneko_(base_inglesa_075a)_ingles_DD099.sfc` — ROM de referencia (2 MB).

### 2. Arquitectura del sistema de texto (ROM inglesa) — DESCUBIERTO

**La traducción inglesa vive en la expansión de 512 KB** (banco de archivo
`0x180000-0x1FFFFF` = bancos CPU `$30-$3F`). No toca los bancos japoneses.

- **Tablas de punteros** en el banco 7 (archivo `0x38000+`): registros
  consecutivos de **3 bytes** `[addr_lo, addr_hi, bank]` que apuntan a las
  cadenas en `$30-$32:8000+` (ver §3; la traza antigua leía 4 bytes y el
  cuarto era el `lo` del registro siguiente).
  Segunda tabla con otro formato desde `0x39627` (`[lo,hi,id]` sucesivos).
- **Cola de mensajes**: el juego lee los mensajes 60-100 frames ANTES de
  mostrarlos. Durante un diálogo se ve claramente cómo el renderizador
  (PC `$00CBC0`) lee la cadena y ejecuta controles.
- **Códigos de control** (verificados por traza):
  - `FE FF` = fin de cadena
  - `F9 xx`, `FD xx` = controles con parámetro (variables/números)
  - `FB xx` = "imprimir cadena referenciada" (las refs están también en el
    tail, p.ej. `$32:F900`, `$32:F792`, `$32:F7CF`)
  - `00` = separador/espacio, `B3` = '.', `B4` = '!', `B3B3B3` = "..."
- **Fuente de mapa de bits** en banco `$2A` (archivo `0x150000+`):
  - Tabla de offsets T de 16 bits (771 entradas) en CPU `$2A8000`
    (archivo `0x150000`).
  - Base de datos de glifos: archivo **`0x150C0C`** (CPU `$2A8C0C`).
  - Glifos = registros 2bpp entrelazados (fila = 2 bytes: plano0, plano1),
    ancho 8 px, alto variable (10-13 filas, 20-26 bytes).
  - Corrección (oct 2026): T es **siempre** offset relativo a la BD
    (`archivo = 0x150C0C + T`), también para T≥`0x1000`. El dibujante
    (`$02:CC2C-CC3D`, copia en `$00CC3D`) hace `LDA $2A8000,X` (T) y
    `LDA $2A8C0C,X` (bitmap) sin caso especial. T[13]=`0x1070` → archivo
    `0x151C7C`, T[25]=`0x108C` → `0x151C98`. La hipótesis previa de
    "punteros absolutos" era un error de las herramientas y causó el bug de
    acentos (ver §9).
- **Renderizador**: PC `$00CBC0` (bucle de lectura de cadena, banco 0
  parcheado por DD), dispatcher de controles en PC `$00C920` (tabla de
  punteros de handlers en `$00C92E`), handlers en CPU `$02:C6xx+`.
  Los glifos se leen por ráfagas de 20-24 bytes desde `$2A8xxx-$2A9xxx`;
  el truco de extracción (dirección de ráfaga → índice vía T → bitmap)
  **produce texto legible** (p.ej. "Picked up Steel", "Inflicted 70 damage",
  "Mummy attacked!"). Herramientas: ver scripts.

### 3. La codificación del texto — **RESUELTO** (oct 2026, corregido)

- **NO hay diccionario ni bitstream. Es 1 byte = 1 glifo.** El código de un
  glifo es su índice en la fuente **+ 1** (`codigo = indice + 1`); el
  `0x00` en las cadenas es espacio (no un separador).
- La "compresión" aparente (fragmentos tipo `ke`, `ed`, `te`, `al`,
  variable-length y "contexto-dependiente") era una falsa alarma: el parche
  inglés añadió a la fuente **glifos compuestos de 16 px para bigramas
  frecuentes**. Un byte puede renderizar 1 o 2 letras:
  - `0x3D`="ke", `0x45`="ed", `0x48`="te", `0x4A`="al", `0x3C`="ag",
    `0x3A`="li", `0x88`="oo", `0xA3`="to", `0x80`="ic", etc.
  - El experimento antiguo de insertar `00` entre códigos alteraba la
    segmentación y hacía parecer el esquema dependiente del contexto.
- **Gramática REAL de los bytes** (reconstruida de los handlers $02:C5BE+
  en oct 2026; la versión anterior de este §3 era incorrecta):
  - `00` = espacio; `01-EF` = glifo (`indice = b-1`).
  - `F0-F3 xx` = glifo extendido: `indice = ((b&3)<<8 | xx) - 1`
    (banco alternativo de la fuente, p. ej. iconos beso `[F1 32]`).
  - `F4 lo hi` = glifo directo: `indice = (hi<<8|lo) - 1`.
  - **`F5`,`F6`,`F7`,`F8`,`FE` = marcadores de control de 1 byte**
    (reinicio de caja / pausa-página / salto de línea; semántica verificada
    en §9, no son color). NO consumen parámetro: `[F5 15]t's` = marcador F5 +
    glifo 0x15 ("I") + "t's".
  - `F9 xx` = número variable (2 B); `FB xx` = cadena referenciada (2 B);
    `FC xx` = estilo/icono (2 B); `FD lo hi` = icono/posición (3 B);
    `FA` = variable especial (1 B); `FF` = fin (y `FE FF` = marcador+fin).
  - `[SE]` (FE) = salto de línea; `[S6]`/`[S7]`/`[S8]` = pausa/página y
    `[S5]` = reinicio de caja (detalle y pruebas en §9). El inglés ya viene
    pre-cortado a ~28-30 caracteres por línea con `[SE]`.
- Fuente de mapa de bits (banco `$2A`), formato exacto:
  - offsets T (771 entradas × 2 B) en `$2A8000` (archivo `0x150000`);
  - **tabla de tamaños** en `$2A8606` (archivo `0x150606`): byte bajo =
    ancho en px, byte alto = nº de filas (bytes de bitmap = filas × 2);
  - bitmaps en `$2A8C0C` (archivo `0x150C0C`): 2 B por fila, palabra
    **little-endian**; píxel 0 = bit 15 (MSB). Vale para todos los anchos.
  - T es siempre relativo a 0x150C0C (archivo = 0x150C0C + T), sin
    excepciones (verificado en el código del dibujante y por traza Mesen).
  - El mayor bitmap usado termina en 0x15528A. Los glifos ES nuevos ocupan
    0x154A00-0x154B1C, hueco de bitmaps de los códigos 0x28B-0x298 (kanji
    muerto, no usados en cadenas); verificado que ningún código usado se pisa.
- **Tabla de referencias FB** (nombres de objetos 0x80-0xFF):
  es una *rebanada de tabla A*: `[FB 0x80+n]` → registro `813+0x80+n`
  (archivo 0x38987 + índice*3). Al repackear tabla A se actualizan solas.
  `[FB 00]` (nombre de monstruo) se resuelve vía WRAM pero a partir de las
  cadenas de tabla A (verificado: "Momia" en pantalla).
- **Tabla B** (0x38E07, 886 registros de 3 B): punteros **por carácter** de
  las 9 cadenas contiguas $32:BA03-$32:BDBF. insert.py la regenera mapeando
  el índice de glifo (si el juego no la usa, no molesta).
- El pool del banco 7 (0x39869+) y los borradores del banco $08
  (0x42000-0x46000, con "T" en vez de ":") son **material viejo/copias
  muertas** de traducciones previas: la traza de lecturas de Mesen no los
  toca; no se traducen.
- Flujo del renderizador:
  - expansores/handlers en `$02:C616+` copian el mensaje ROM a WRAM
    `$7EAF4C` como unidades de 16 bits (`0xFE00|b` texto, `0xFD00|b`
    variantes, `00` → espacio);
  - dibujante `$02:CBF5`: por unidad `<0xFC00` → índice = unidad−1; tamaño
    vía `$2A8606`, bitmap vía `$2A8000` → `$2A8C0C`.
- Almacenamiento y punteros: tail `$30:8000+`; tabla en banco 7 (`0x38000+`)
  con registros consecutivos de **3 bytes** `[lo,hi,bank]` (el supuesto
  "byte extra" de 4 B en las trazas era el `lo` del registro siguiente).
  El banco 7 `0x39876+` **no** es diccionario: son más mensajes con el mismo
  formato (p.ej. `20 4a 3d 64 00 a3 00 20 4a 88 73 b4` = "Talked to Taloon!").
- **Decodificación verificada en pantalla** (Mesen, ROM de referencia, sin
  `.srm`): `15 73 63 3a 5f 48 64 00 f9 10 00 64 5d 71 3c 62 b3 fe ff` =
  **"Inflicted 7 damage."** (`f9 10` inserta el número de daño; 7 en esa
  batalla). Confirmado además parcheando el propio mensaje con sus códigos
  separados por `00` (renderizó `li c te ag e .`).

### 4. Entorno de trabajo (Mesen headless) — CORREGIDO Y VERIFICADO

```bash
cp ROM /tmp/scratch/test.sfc && rm -f /tmp/scratch/test.srm   # ¡imprescindible!
Mesen --testRunner script.lua --timeout=600 /tmp/scratch/test.sfc
```

- Sin `--timeout=600` el testRunner mata la ejecución a los ~100 s.
- **Borrar el `.srm` antes de cada corrida** o el demo/estado cambia y las
  trazas no son reproducibles.
- Firma correcta del callback:
  `emu.addMemoryCallback(cb, tipo, ini, fin, emu.cpuType.snes, emu.memType.xxx)`
  (cpuType ANTES de memType; los scripts viejos los tenían cambiados).
- `emu.memType.snesPrgRom` sólo dispara en lecturas de datos (no en fetch de
  código) y reporta direcciones CPU de 24 bits.
- `emu.takeScreenshot()`, `emu.getCpuState().pc`, `io.open` funcionan en
  testRunner; `emu.createSavestate/loadSavestate` sólo dentro de callback exec.

### 5. Herramientas en `scripts/`

- `d65.py` — desensamblador 65816 mínimo (rastrea REP/SEP para M/X).
  Uso: `python3 d65.py código.bin <base_cpu_hex> <ini_hex> <fin_hex>`.
- `recon.py` — localización de bloques de fuente/gráficos (original).
- `make_ips.py` — genera `parches/Taloon_ESP_traduccion.ips` (solo stdlib) y lo
  valida aplicándolo a la base y comparando con `out/rom_es.sfc`.
- `readscreen.py` — "OCR" de capturas de Mesen: empareja los glifos de la
  fuente contra el fotograma y transcribe la caja de texto
  (`python3 scripts/readscreen.py --frames 18000:20000 --dir out/trace4`).
- `make_testrom.py` — ROM de prueba con mensajes de batalla parcheados
  (marcadores/iconos); nunca toca `translation_part*.txt` ni `rom_es.sfc`.
- Lua de traza: `trace_rom.lua` (lecturas de ROM + escrituras WRAM,
  screenshots), `trace_unidades*.lua` (buffer de unidades $7EAF4C), además de
  `combo.lua`/`dlg2.lua`/`buf.lua`/`full.lua` (trazas históricas).

### 6. Próximos pasos concretos

1. ~~Extraer todas las cadenas~~ **HECHO** (§8).
2. ~~Traducir al español~~ **HECHO** (§9, `scripts/translation_part*.txt`).
3. ~~Reinsertar~~ **HECHO** (§9, `out/rom_es.sfc`).
4. ~~Añadir 'ñ' y vocales acentuadas~~ **HECHO** (§9, 12 glifos nuevos).
5. El título de la intro (glifo/dibujo) NO se toca, como se pidió.
6. Pendiente opcional: probar partidas guardadas/menús con la ROM ES.
   Los 12 avisos de ancho ya están corregidos (§9) y los marcadores no son de
   color: no hay nada que "restaurar" (semántica real en §9).

### 7. Hallazgos verificados que sirven de ancla

- Mensajes visibles y sus lecturas (frames deterministas sin .srm):
  - frame ~19949/19979: lecturas de `$30:81A4`, `$30:8177` (refs `$32:F900`…)
  - frame ~20068: `$30:82C0` + refs `$32:F792`/`$32:F7CF`; `$30:804C`
  - frame ~19687: carga de la cola de mensajes completa (varias cadenas)
- Secuencia de ráfagas de glifos legible para calibrar el mapeo
  (p.ej. frame 20077 = "Taloon whomped Mummy!" → índices
  `[31,73,135,114,130,102,116,112,118,68,24,128,112,112,132,179]`,
  con glitches de extracción en algunos índices).
- La mensajería tiene tipografía fija: 2 líneas de diálogo, iconos de
  ítem/cursor como glifos especiales dentro del texto.

### 8. Extracción estática completada (oct 2026)

- `scripts/extract.py` (+ `scripts/glyph_map.json`) extrae todo el texto sin
  Mesen: tabla A (0x38000, 1197 punteros de 3 B a `$30-$33:8000+`), tabla B
  (racha de punteros +1 a `$32:BA4B+`; puntero por carácter, redundante) y
  pool del banco 7 (0x39869-0x3FFFF, sin tabla). Salidas:
  - `out/strings_en.txt` — 1197 cadenas con dirección + texto.
  - `out/strings_pool_bank7.txt` — 258 fragmentos del pool.
  - `out/codes.tsv` — 208 códigos usados (140 mapeados; el resto son iconos
    del pool japonés; los iconos inline de tabla A se conservan como `{XX}`).
  - `out/codes_atlas.txt` — glifos en ASCII.
- Decodificador corregido en oct 2026 (ver §3): F5-F8/FE son marcadores de
  1 byte, FD tiene 2 parámetros y F0-F3 son glifos extendidos. Verificado
  contra las 3 anclas (`$30:804C`, `$30:82C0`, `$30:8177`).
- **Iconos inline** (`scripts/icon_codes.json`; columna `descripcion` de
  `out/codes.tsv`): hay 13 códigos de icono usados dentro del texto real de
  tabla A, identificados por contexto (listas de nombres de objeto de la ROM),
  arte del atlas y lectura de capturas con `scripts/readscreen.py`:
  `27`=cofre (Joya/Felicidad/Misterio), `28`=espada (variante: Oro/Cobre/
  Dragón/Metal Babble/Ábaco), `29`=anillo (Fuerza/Antídoto/Vigilia/Ladrón/
  Visión…), `2A`=espada (Madera/Acero/Plata), `2B`=hierba, `2C`=escudo
  (Cuero/Bronce/Escama/Espejo/Acero…), `2D`=hacha (solo `Acero{2D}`; el
  diálogo habla del Hacha de Acero), `2E`=bastón (Rayo/Lentitud/Sueño… y
  bastones de madera/metal), `2F`=pergamino (Poder/Identificar/Azar…),
  `A7`=símbolo "Sigh!" (adorno de suspiro), `A8`=semilla (Fuerza/Suerte/
  Agilidad), `B0`/`B2`=sin usar (solo en la cadena de prueba de la fuente).
  Los 55 códigos sin mapear restantes solo aparecen en el pool japonés muerto
  del banco 7 → marcados "pool muerto" en `codes.tsv`.

### 9. Traducción al español (oct 2026) — COMPLETADA

- **Flujo**: `scripts/escodes.py` (codificador/decodificador ES + glifos
  nuevos) → `scripts/translation_part*.txt` (traducciones, `$dir<TAB>texto`) →
  `scripts/translate.py` (genera `out/strings_es.txt` y valida) →
  `scripts/insert.py` (reinserción).
- **Validación de translate.py**: mismos tokens de control que el inglés
  (salvo `[SE]`, que puede moverse/añadirse para reencuadrar), orden de
  `[FB]/[F9]/[FC]/[FD]/[F*]` idéntico, ≤1024 unidades por mensaje, y ancho
  de línea ≤ ancho EN de la misma cadena +8 px. Los 12 avisos de +2..+9 px
  quedaron corregidos reencuadrando con `[SE]`/espacios; `translate.py` sale
  sin problemas.
- **Glifos nuevos ES** (12, en huecos libres del rango kanji):
  `C3`=ñ `C8`=á `CD`=é `D5`=í `D9`=ó `E2`=ú `E5`=ü `E7`=¿ `EB`=¡
  `EC`=Á `E0`=Í `EF`=Ó. Se construyen del glifo base + acento/tilde/diéresis
  y se escriben al final del banco $2A (0x154A00+; T = archivo − 0x150C0C,
  siempre relativo a la BD, + tabla de tamaños). Sin Ñ/Ü mayúsculas: el texto
  no las necesita.
  - **Bug de acentos (oct 2026, corregido)**: `insert.py` escribía
    T = archivo − 0x150000, así que el juego calculaba 0x150C0C + T =
    archivo + 0xC0C (0x15560C para los glifos de 0x154A00) y leía basura;
    los caracteres se veían "bugueados" en pantalla.
    Con T = archivo − 0x150C0C quedó verificado en Mesen: "¡Momia atacó!",
    "Recibió 6 de daño." y "¡Taloon golpeó a Deranger!" (capturas
    out/marcadores_evidencia/es_acentos_1.png y es_acentos_2.png).
  - **¿ corregido (oct 2026)**: el glifo era solo un volteo vertical de `?`;
    ahora es rotación 180° (vertical + horizontal) en `escodes.py` (`rot180`;
    para `¡` es indiferente, `!` es simétrico). Verificado en pantalla con
    ROM de prueba (`ñáéíóúü¿¡ÁÍÓ`, out/marcadores_evidencia/es_rot180.png).
- **Reinserción** (`insert.py`): reempaqueta las 1197 cadenas desde
  `$30:8000` (102.5 KB, 78% de los 4 bancos $30-$33), actualiza tabla A y
  regenera tabla B; el texto queda contiguo y todos los punteros válidos.
- **Verificado en Mesen** (demo de batalla, sin `.srm`): mensajes en español
  ("Taloon golpeó a Momia!", "Causó 7 de daño.", "Equipó Acero⬡...",
  "Taloon lanzó un golpe y falló."), acentos y `¿¡` renderizando bien, y los
  nombres de monstruo de `[FB 00]` salen de tabla A (ya traducidos).
- **Marcadores [S5-S8]/[SE]: NO se descartan** (la nota anterior era falsa).
  Se conservan byte a byte; la secuencia `[S5]-[S8]` del ES es idéntica a la
  del EN en las 1197 cadenas (verificado) y `[SE]` solo puede moverse/añadirse
  para reencuadrar. Semántica real determinada en oct 2026 desensamblando el
  parser (`$02:C5BE`, tabla de handlers `$02:C5FD`) y el renderizador
  (`$04:92xx`), y confirmada en pantalla con `make_testrom.py` +
  `readscreen.py`:
  - Parser: `F5`→unidad `FFF6`, `F6`→`FFF9`, `F7`→`FFFA`, `F8`→`FFFC`,
    `FE`→`FFFE`. Los `[FC 01..06]` son alias de la misma familia:
    FC01=FFFC, FC02=FFFB, FC03=FFFA, FC04=FFF9, FC05=FFF8, FC06=FFF7.
  - `[SE]`/FE = **salto de línea**: el renderizador incrementa el contador de
    línea (WRAM `$1A6A`) y limpia los buffers de línea (`$04923F`).
    Verificado: `EE[SE]FF` pinta `EE` en la línea 1 y `FF` en la 2.
  - `[S5]` = **abrir/reiniciar la caja**: al empezar una cadena con `[S5]`
    desaparece el texto anterior (verificado: `LLMM`+`EE` se borran cuando
    entra `[S5]OO`).
  - `[S6]`/`[S7]`/`[S8]` = **marcas de pausa/página**: se dibuja el texto
    previo y el siguiente ya no se dibuja hasta que el juego avanza la página
    (verificado con `CC[S6]DD`, `GG[S7]HH`, `II[S8]JJ`: `DD`/`HH`/`JJ` no
    aparecen en ninguna captura; en el demo la escena se reinicia ahí).
  - Ninguno cambia el color ni se dibuja como glifo: no hay escrituras a CGRAM
    al procesarlos, las letras salen del mismo blanco `#DEDEDE` y `$02:CBF5`
    devuelve "no dibujable" para unidades ≥`FF00`.
- **IPS de distribución**: `parches/Taloon_ESP_traduccion.ips` (106.6 KB),
  generado por `scripts/make_ips.py` comparando la base inglesa con
  `out/rom_es.sfc`; validado aplicándolo a la base y con `cmp` (idéntico).
- **Limitaciones conocidas/pendientes**:
  - `out/rom_es.sfc` es la ROM jugable con el español; el título de la
    intro no se toca.
  - El libro de la intro usa otro renderizador que omite el espacio en
    ciertos pares de glifos: la base EN muestra lo mismo ("Anda fine /
    familyman."), así que es un defecto preexistente del parche inglés,
    idéntico en EN y ES (capturas en `out/marcadores_evidencia/`).
  - No se tocaron los borradores muertos (pool banco 7 / banco $08) ni la
    tabla de nombres de monstruos del banco $08 (esa ruta no se usa).

## Archivos del proyecto
- `parches/` — IPS inglés corregido + `Taloon_ESP_traduccion.ips` (parche ES).
- `Torneko_(base_inglesa_075a)_ingles_DD099.sfc` — ROM de referencia (inglesa).
- `out/rom_es.sfc` — **ROM con la traducción al español** (reinserción final).
- `out/strings_en.txt` / `out/strings_es.txt` — cadenas con dirección.
- `out/codes.tsv` / `out/codes_atlas.txt` — inventario de glifos usados.
- `out/test_marcadores.sfc` — ROM de prueba (marcadores/iconos, regenerable).
- `scripts/translation_part*.txt` — traducción ES editable (fuente de verdad).
- `scripts/escodes.py` — codificador ES (glifos nuevos incluidos).
- `scripts/translate.py` — genera `out/strings_es.txt` y valida.
- `scripts/insert.py` — reconstruye la ROM ES (repack + punteros + fuente).
- `scripts/extract.py` — extracción estática EN (decodificador corregido).
- `scripts/make_ips.py` / `make_testrom.py` / `readscreen.py` — IPS, ROM de
  prueba y lectura de capturas (ver §5).
- `scripts/icon_codes.json` — nombres de los 13 iconos inline (ver §8).
- `docs/` — capturas de fuente, desensamblados parciales.
- `scripts/` — también análisis previo (d65, recon, trazas Lua).
