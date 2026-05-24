# Automóviles Rueda — Memoria Completa del Proyecto

## Propietario
**Andrés Vázquez** — Comercial en Automóviles Rueda (concesionario SEAT · CUPRA · Volkswagen · Das WeltAuto)
- Teléfono: 610 02 90 56
- Email: andres.vazquez@automovilesrueda.com
- GitHub: andresvazquez11
- Web publicada: https://andresvazquez11.github.io/automoviles-rueda-catalogo/

## Cómo trabajamos bien juntos
- Andrés no es técnico — instrucciones siempre en español y muy visuales
- Le gustan los cambios incrementales con verificación visual antes de confirmar
- Flujo ideal: proponer → ejecutar → verificar → confirmar → publicar
- Si algo no le gusta estéticamente, lo dice directamente ("me pareció horrible") — hay que escucharlo y revisar desde la raíz, no parchar
- Responde bien al visual companion del brainstorming para tomar decisiones de diseño
- Cuando dice "continúa", quiere acción inmediata sin más preguntas

---

## Sistema 1 — Catálogo Web de Clientes

### Qué hace
Genera una página web pública con todos los coches seminuevos Das WeltAuto para compartir por WhatsApp Business con clientes.

### URL pública
https://andresvazquez11.github.io/automoviles-rueda-catalogo/

### Fuente de datos
`datos_coches.json` — campos por coche:
- `n`: número (1-45+)
- `modelo`: "SEAT León", "CUPRA Born", "Volkswagen T-Cross"
- `version`: string largo con la versión completa
- `combustible`: "Gasolina" / "Diésel" / "Híbrido" / "Eléctrico"
- `km`: kilómetros
- `fecha`: año de matriculación
- `cambio`: "Manual" / "Automático"
- `color`: string en español ("Azul", "Gris", "Blanco")
- `precio`: número entero en euros
- `ubicacion`: ubicación física
- `estado`: "Disponible" / "No disponible" (= Reservado en pantalla)
- `url`: ruta relativa a dasweltauto.es para construir la URL del anuncio
- `equipamiento[]`: lista de strings

### Fotos locales
`fotos/{N:02d} - {MODELO} - {PRECIO}€/foto_01.jpg ... foto_08.jpg`

### Foto exterior principal (CDN Das WeltAuto)
Construida desde la `url` del anuncio:
1. Extraer el ID numérico de la URL (ej: `140460837`)
2. Padear a 11 dígitos con zfill: `00140460837`
3. Dividir en pares de 2: `00/14/04/60/83/7`
4. URL final: `https://www.dasweltauto.es/esp/fotos_anuncios/00/14/04/60/83/7/x01.jpg`

### Archivos clave del catálogo web
| Archivo | Función |
|---|---|
| `generar_web.py` | Lee JSON → copia fotos a `web_fotos/` → genera `index.html` |
| `actualizar_catalogo.py` | Scraping Das WeltAuto → actualiza JSON + PDF |
| `descargar_fotos_galeria.py` | Descarga fotos nuevas de Das WeltAuto |
| `datos_coches.json` | Inventario actual (fuente de verdad) |
| `index.html` | Catálogo web generado (NO editar manualmente) |
| `web_fotos/{n:02d}/foto_XX.jpg` | Fotos sin caracteres especiales para GitHub Pages |

### Ejecutables (en `/Desktop/ejecutable redes/`)
- `1️⃣ Actualizar Todo — Cambios + Fotos.command`: scraping + fotos + PDF + web + git push (todo en uno, ~2 min)
- `🌐 Generar Web Clientes.command`: solo regenera la web sin scrapear
- `🎯 Generar Marketing Coches.command`: genera paquete de marketing para todos los coches
- `🎬 Reels Épicos Virales.command`: abre el generador interactivo de reels por coche

### Git / GitHub
- Repo: `git@github.com:andresvazquez11/automoviles-rueda-catalogo.git`
- SSH key: `~/.ssh/github_rueda`
- Solo se commitean `index.html` y `web_fotos/` (no scripts ni JSON)
- GitHub Pages: rama `main`, raíz `/`

### Estilo visual de la web
- Header: `#0d1b35` (azul marino oscuro) con borde rojo `#C8232B`
- Fondo: `#eef1f7` (gris-azulado claro, estilo Das WeltAuto)
- Tarjetas: blancas con sombra suave
- Acento: rojo `#C8232B` (marca Rueda)
- Fuente: Inter
- Header muestra: "Automóviles Rueda" + "Andrés Vázquez · 610 02 90 56"
- Botón WhatsApp flotante en móvil: `https://wa.me/34610029056`

### Decisiones técnicas importantes (web)
1. Foto principal = CDN DWA (`x01.jpg`), no la local → siempre exterior
2. Búsqueda normalizada con `String.normalize('NFD')` → "leon" encuentra "León"
3. "No disponible" → "Reservado" solo en display (el JSON mantiene el valor original)
4. HTML 100% autocontenido — todo CSS/JS inline, sin dependencias externas salvo Google Fonts
5. Fotos en `web_fotos/{n:02d}/foto_XX.jpg` — nombres sin caracteres especiales

---

## Sistema 2 — Generador de Marketing por Coche

### Qué hace
Para cada coche disponible/reservado, genera carpeta `marketing/` con prompts listos para copiar y pegar en Gemini 3.1 Flash Image y Kling AI.

### Script
`generar_marketing_paquete.py`

### Estructura de carpetas generada
```
fotos/XX - MODELO - PRECIO€/
  marketing/
    stories-916/
      v1_humor_viral/
        prompt_imagen.txt       ← copiar y pegar en Gemini 3.1
        instrucciones.txt       ← pasos numerados
      v2_humor_sorpresa/
      v3_emocional_viaje/
      v4_emocional_logro/
      v5_combo_viral/
    carrusel/
      v1_humor_viral/ ... v5_combo_viral/
    reel-15s/
      shot_01_apertura/
      shot_02_detalle/
      shot_03_movimiento/
      shot_04_cta/
      storyboard.md
      guia_montaje_capcut.txt
      musica_viral.txt
```

### Los 5 tonos creativos
| # | Tono | Concepto |
|---|---|---|
| V1 | Humor viral | Auto-ironía, "no te mentimos", meme-friendly |
| V2 | Humor sorpresa | Twist inesperado, "lo que nadie te dice" |
| V3 | Emocional viaje | Road trip, familia, nostalgia, Axarquía |
| V4 | Emocional logro | "Te lo mereces", sueño cumplido |
| V5 | Combo viral | Humor hook → punchline emocional (más viral) |

### Plantilla DWA "Comprobadísimo" — la que funciona
Los prompts buenos siguen el estilo de campaña Das WeltAuto original con:
- ROLE ASSIGNMENT para las fotos de referencia
- Franja naranja vertical `#FF5000` a la izquierda
- Tipografía brush lettering + sans serif
- Zonas numeradas ①②③④⑤ en el layout
- El texto overlay integrado en la imagen (no en archivo separado)

---

## Sistema 3 — Generador de Reels Épicos Virales

### Qué hace
CLI interactivo: el usuario elige el coche y el tipo de reel → genera storyboard + todos los prompts (Gemini 3.1 + Kling) listos para producir.

### Script
`generar_reel_epico.py`

### 4 tipos de reel
1. **ROMPE LA PARED** — Frigiliana (pared encalada explota)
2. **HELICÓPTERO** — Pantano Viñuela + Castillo Bentomiz
3. **EL SALTO** — Puerto del Collado → Costa de Nerja
4. **REVEALED** — Alcazaba de Vélez-Málaga

### Herramientas de producción
| Herramienta | Uso | Acceso |
|---|---|---|
| Gemini 3.1 Flash Image | Generar imágenes start/end frames | aistudio.google.com |
| Kling 2.5 | Vídeo con solo start frame + prompt | klingai.com |
| Kling 3.0 | Vídeo con start frame + end frame | klingai.com |
| CapCut | Montaje final del reel | App |

### Estilos cinematográficos por tipo de coche (auto-detectado)
```
CUPRA        → BMW Films (Arri Alexa Mini LF, anamórfica Panavision 50mm, blue hour, Teal & Orange)
SEAT FR/Sport → Fast & Furious (RED V-Raptor, Sigma 24mm, noche, asfalto mojado, contraste extremo)
SEAT Familiar → Mediterráneo SEAT España (Sony FX9, Zeiss 35mm, golden hour, Axarquía)
```

Detección en código:
```python
def get_estilo_cine(modelo: str) -> str:
    m = modelo.upper()
    if "CUPRA" in m:     return "cupra"
    elif "FR" in m or "SPORT" in m: return "seat_sport"
    else:                return "seat_family"
```

### Regla crítica del color en los prompts de imagen
**NUNCA especificar el color del coche en el prompt de Gemini.**
El color lo da la foto de referencia (Image 1). Si se especifica en texto, Gemini lo interpreta a su manera y cambia el color.

Fórmula correcta:
```
→ COLOR Y PINTURA: Reproduce EXACTAMENTE el color y acabado de Image 1.
No interpretes el color — ya está en la foto.
Si el color final difiere del de Image 1, la imagen es INCORRECTA.
```

### Estructura de los prompts Gemini (gemini_img_prompt)
```python
gemini_img_prompt(scene: str, modelo: str, angulo: str = None, fmt: str = "9:16 (1080×1920px)")
```
- `scene`: descripción de la escena en español
- `modelo`: nombre del coche (para detectar estilo automáticamente)
- `angulo`: override del ángulo de cámara (opcional)
- El color NO es un parámetro — viene de la foto

### Estructura narrativa de cada reel (arco emocional)
Cada reel tiene:
- **[HOOK]**: Shot 0-2s que para el scroll (misterio, in medias res, o vértigo)
- **[CLÍMAX]**: El momento de máxima acción
- **[MONEY SHOT]**: El frame más impactante y compartible — digno de cartel de cine
- **[LIBERACIÓN]**: La resolución emocional
- **[BEAUTY]**: Close-up íntimo
- **[CTA]**: Precio + modelo + 610 02 90 56 + Andrés Vázquez + Automóviles Rueda

### Los 4 money shots diseñados
1. Rompe la Pared → el coche perfecto dentro de la nube de polvo blanco, faros cortando el yeso
2. Helicóptero → la rueda del coche suspendida a 40cm del suelo (James Bond)
3. El Salto → el valle de la Axarquía reflejado en el capó del coche en pleno vuelo
4. Revealed → coche + Alcazaba + Vélez-Málaga + Mediterráneo todo en un plano

### Localizaciones reales de la Axarquía usadas
- Frigiliana — pueblo encalado más bello de España
- Pantano de la Viñuela — embalse turquesa entre montañas
- Castillo de Bentomiz — ruinas moriscas con vistas 360°
- Puerto del Collado (Cómpeta) — paso de montaña con precipicio
- Costa de Nerja — acantilados blancos y Mediterráneo
- Alcazaba de Vélez-Málaga — fortaleza morisca sobre la ciudad

---

## Errores cometidos y cómo los resolvimos

### Error 1 — Calidad de los prompts de marketing
**Problema:** Los primeros prompts generados eran genéricos y el usuario los calificó de "horribles". Las imágenes no tenían la calidad de la campaña original Das WeltAuto.
**Causa:** Los nuevos prompts describían la escena sin estructura de campaña.
**Solución:** Revertir a la plantilla del archivo `_archivo/prompt_stories.txt` original y crear `_dwa_base_template()` que replica exactamente el estilo "Comprobadísimo" con franja naranja, ROLE ASSIGNMENT, zonas numeradas y tipografía brush.

### Error 2 — Color cambiante en imágenes generadas
**Problema:** Gemini 3.1 Flash Image cambiaba el color del coche aunque se especificara en el prompt.
**Causa:** Al escribir "azul profundo metálico" o similar, Gemini interpreta su propia versión del color en lugar de usar la foto de referencia.
**Solución:** Eliminar completamente la especificación de color del prompt. Reemplazar por: "Reproduce EXACTAMENTE el color de Image 1. Si el color difiere, la imagen es INCORRECTA."

### Error 3 — Referencias a "Freepik" en instrucciones
**Problema:** El código tenía referencias a "Freepik Space" pero la herramienta correcta es Gemini 3.1 Flash Image.
**Solución:** Reemplazar todas las referencias. Crear helper `gemini_img_prompt()` y funciones `gemini_instrucciones_single()` / `gemini_instrucciones_dual()` que solo referencian Gemini 3.1.

### Error 4 — Python 3.9 incompatibilidad
**Problema:** Anotaciones de tipo `Path | None` no funcionan en Python 3.9.
**Solución:** Eliminar anotaciones de tipo en las funciones o usar `Optional[Path]`.

### Error 5 — Guiones sin energía
**Problema:** Los storyboards describían "qué pasa" pero no "cómo se siente". Resultado: prompts planos sin gancho viral.
**Solución:** Rediseñar con arco emocional explícito (hook → clímax → money shot → liberación), apertura in medias res, y un "money shot" central digno de cartel de cine.

---

## Reglas de producción que funcionan

### Para Gemini 3.1 Flash Image
1. **Adjuntar siempre foto_01.jpg + foto_02.jpg** del coche como referencia
2. **NO especificar el color en texto** — el color viene de la foto
3. **SÍ especificar cámara, ángulo, iluminación, color grade** — Gemini los respeta bien
4. **Un solo coche en la imagen** — especificarlo explícitamente en CRITICAL RULES
5. **"Fotografiado en la localización, no compuesto en estudio"** — esta frase mejora mucho el realismo
6. **Calidad €500.000** — esta referencia de presupuesto funciona para subir el nivel

### Para Kling 2.5 (un frame)
- Start frame = imagen generada por Gemini
- Duración: 2-4 segundos por shot
- Ratio: 9:16
- El prompt de Kling describe el MOVIMIENTO, no la imagen estática

### Para Kling 3.0 (dos frames)
- Start frame + End frame = dos imágenes de Gemini (el antes y el después)
- Kling interpola el movimiento entre los dos estados
- Ideal para: impactos, elevaciones, reveals, transiciones físicas
- El prompt de Kling describe la TRANSICIÓN entre los dos estados

### Para CapCut
- Siempre exportar 1080×1920 a 30fps
- Drop musical = inicio del money shot
- Slow motion (0.7x) en los money shots
- Hard cut entre shots de acción, dissolve suave entre emocionales

---

## Estructura de archivos del proyecto

```
~/Desktop/catalogo_automoviles_rueda/
├── datos_coches.json              ← fuente de verdad del inventario
├── generar_web.py                 ← genera index.html + web_fotos/
├── actualizar_catalogo.py         ← scraping Das WeltAuto
├── descargar_fotos_galeria.py     ← descarga fotos
├── generar_marketing_paquete.py   ← genera marketing/ por coche
├── generar_reel_epico.py          ← CLI interactivo de reels épicos
├── CLAUDE.md                      ← este archivo de memoria
├── index.html                     ← web generada (no editar)
├── web_fotos/                     ← fotos para GitHub Pages
└── fotos/
    └── 01 - SEAT León - 22.900€/
        ├── foto_01.jpg ... foto_08.jpg
        ├── marketing/             ← generado por generar_marketing_paquete.py
        └── reels-epicos/          ← generado por generar_reel_epico.py
            ├── reel_rompe_pared/
            ├── reel_helicoptero/
            ├── reel_el_salto/
            └── reel_revealed/

~/Desktop/ejecutable redes/
├── 1️⃣ Actualizar Todo — Cambios + Fotos.command
├── 🌐 Generar Web Clientes.command
├── 🎯 Generar Marketing Coches.command
└── 🎬 Reels Épicos Virales.command
```

---

## Flujo de actualización completo

```
Actualizar Todo.command
  → actualizar_catalogo.py   (scraping DWA → JSON + PDF)
  → descargar_fotos_galeria.py (descarga fotos nuevas)
  → generar_web.py           (genera index.html + copia fotos)
  → git add + commit + push  (publica en GitHub Pages)
  ≈ 2 min después → URL pública actualizada automáticamente
```

## Para regenerar el marketing después de añadir coches
```
Ejecutar: 🎯 Generar Marketing Coches.command
→ Lee datos_coches.json
→ Para cada coche: archiva marketing/ anterior → genera nuevo con 5 tonos × 3 formatos
→ Abre la carpeta fotos/ al terminar
```

## Para generar un reel épico de un coche específico
```
Ejecutar: 🎬 Reels Épicos Virales.command
→ Seleccionar número de coche
→ Seleccionar tipo de reel (1-4) o 0 para todos
→ Abrir la carpeta reels-epicos/ del coche
→ Seguir storyboard.md shot a shot
```

---

## Sistema 4 — Calculadora de Financiación Interactiva (en la web)

### Qué hace
Dentro del modal de detalle de cada coche en `index.html`, hay una calculadora interactiva que replica exactamente la financiación de Das WeltAuto. El usuario puede cambiar entrada, plazo y km/año en tiempo real y ver la cuota recalculada al instante.

### Dos tipos de financiación (tabs)
- **Lineal**: amortización francesa estándar (PMT)
- **Autocredit**: crédito balloon — el coche se financia completo y al final se paga el valor residual (VR) o se devuelve/cambia

### Fórmulas exactas que usa DWA (verificadas con datos reales)

```
neto     = precio - entrada
base     = neto + seguro                  ← seguro de protección plus
capital  = base × 1.035                   ← comisión 3,5% circular
comision = capital - base                 ← = base × 0.035

LINEAL:     cuota = capital × r / (1 - (1+r)^-n)
AUTOCREDIT: cuota = (capital × r × rn - vr × r) / (rn - 1)   ← true balloon loan

total_plazos = cuota × n + entrada + vr   ← comision ya está dentro del capital
```

### Seguro de Protección Plus
- **Valor real**: 6,15% del precio del coche (consistente en todos los coches DWA)
- **Extracción**: del texto verbatim `fin_ejemplo` → `importe_total_financiado - precio - comision_apertura`
- **Fallback**: `precio × 0.0615` si no hay texto scrapeado
- **Función Python**: `extract_seguro_eur(ejemplo, precio)` en `generar_web.py`
- **CRÍTICO**: sin este seguro la cuota calculada difiere ~34€/mes de DWA

### Valor Residual (Autocredit)
- **Fuente primaria**: extraído del campo `fin_ejemplo` (texto verbatim DWA) → función `extract_vr_eur()`
- **Regex**: `cuota final en el mes \d+ de ([0-9.,]+)`
- **Fallback**: tabla `VR_TABLE` calibrada con datos reales (60m/15k → ~61% del precio)
- **Escalado**: si hay VR real de DWA (60m/15k), se ajusta por km y plazo con `VR_KM_ADJ` y `VR_MES_ADJ`

### Campos del JSON por coche (financiación)
```json
"financiacion": {
  "cuota":    "314,42",    ← cuota scrapeada de DWA (la más fiable)
  "tin":      "6,99",
  "tae":      "8,31",
  "meses":    "60",
  "entrada":  "0",
  "tipo":     "Autocredit",  ← o "Lineal"
  "ejemplo":  "Ejemplo de cuota a 60 meses..."  ← texto verbatim DWA
}
```

### Campos extra en cars_js (para la calculadora)
```javascript
fin_vr:     float   // valor residual en EUR (de fin_ejemplo)
fin_seguro: float   // seguro protección plus en EUR (de fin_ejemplo o 6.15%)
fin_fuente: "dwa"   // "dwa" si hay cuota scrapeada, "calc" si es estimada
```

### Desglose mostrado (mismo orden que DWA)
1. Precio al contado
2. Descuento por financiar → siempre "—"
3. Entrada inicial
4. **Seguro de Protección Plus** ← nuevo campo
5. Comisión de apertura (3,5%)
6. Importe total financiado
7. T.I.N.
8. T.A.E.
9. Nº de cuotas
10. ── (separador) ──
11. **CUOTA MENSUAL** (destacada en rojo `#C8232B`, 30px)
12. Cuota final mes N (solo Autocredit, en ámbar)
13. Precio total a plazos

### Verificación de exactitud
```
SEAT León 27.900€, Autocredit 60m/15k, 0 entrada:
  seguro   = 1.717,10 € (6,15%)
  capital  = (27.900 + 1.717,10) × 1,035 = 30.653,70 €
  cuota    = 314,42 €/mes
  DWA real = 314,42 €/mes  ✓  (diferencia: 0,00 €)
```

### Tablas de ajuste VR (en generar_web.py → JS)
```javascript
const VR_TABLE = {   // % del precio como VR fallback
  24: {10000:79, 15000:74, 20000:68, 25000:63, 30000:58},
  36: {10000:73, 15000:68, 20000:62, 25000:57, 30000:52},
  48: {10000:68, 15000:63, 20000:57, 25000:52, 30000:47},
  60: {10000:66, 15000:61, 20000:55, 25000:50, 30000:45},
  72: {10000:60, 15000:55, 20000:49, 25000:44, 30000:39},
  84: {10000:54, 15000:49, 20000:43, 25000:38, 30000:33}
};
const VR_KM_ADJ  = {10000:+5, 15000:0, 20000:-6, 25000:-11, 30000:-16};
const VR_MES_ADJ = {24:+18, 36:+11, 48:+5, 60:0, 72:-6, 84:-12};
```

### Errores corregidos en la calculadora (historia)
| Error | Síntoma | Fix |
|---|---|---|
| Fórmula Autocredit incorrecta | 139€ en vez de 314€ | Cambiar a true balloon loan |
| Comisión 1% en vez de 3,5% | Cuota baja | `capital = neto / 0.965` |
| Sin seguro de protección | Falta ~34€/mes | `base = neto + seguro; capital = base × 1.035` |
| VR tabla incorrecta | % demasiado bajo | Calibrar con datos reales DWA |
| Total doble-contaba comisión | Total inflado | `total = cuota×n + entrada + vr` (sin sumar comision) |
| Texto legal estático | No reflejaba los parámetros actuales | Generar dinámicamente en `renderCalc()` |

### Arquitectura del código (generar_web.py)
- **Python f-string**: todo el HTML/CSS/JS está dentro de un f-string → `{{` = `{`, `}}` = `}`, `${{var}}` = `${var}`
- `extract_vr_eur(ejemplo)` → float (regex sobre texto DWA)
- `extract_seguro_eur(ejemplo, precio)` → float (regex o fallback 6.15%)
- `calcFinanciacion(precio, tin, entradaPct, meses, tab, km, vrBase, seguro)` → objeto con resultados
- `renderCalc()` → actualiza el DOM con los valores calculados
- `initCalc(c)` → inicializa la calculadora al abrir el modal de un coche
