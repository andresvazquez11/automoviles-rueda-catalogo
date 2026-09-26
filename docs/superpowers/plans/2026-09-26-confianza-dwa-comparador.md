# Confianza DWA, comparador completo, pruebas en vídeo y Quiénes somos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar en el generador (`generar_web.py`) los 4 bloques aprobados en `docs/superpowers/specs/2026-09-26-confianza-dwa-comparador-design.md`.

**Architecture:** Módulos pequeños al estilo de `prensa.py` (cada uno devuelve HTML o datos, sin efectos): `confianza_dwa.py`, `pruebas.py` (+ `pruebas.json`), `comparador.py`, `quienes_somos.py`. `generar_web.py` solo los llama. JS nuevo en archivos estáticos `assets/comparador.js` y `assets/confianza.js`; CSS nuevo al final de `assets/estilos.css`. Se trabaja en la rama `mejoras-confianza` (worktree `../catalogo_rueda_mejoras`); nada se publica sin OK de Andrés.

**Tech Stack:** Python 3.9 (local) / 3.11 (CI), HTML/CSS/JS sin dependencias, `unittest` (no hay pytest).

---

## Archivos
- Crear: `confianza_dwa.py` — garantía corta, sello del header, nav, pastilla de tarjeta, banners, tarjeta final de ficha.
- Crear: `pruebas.py`, `pruebas.json` — vídeos por modelo (reales, verificados).
- Crear: `comparador.py` — datos compactos por coche para el comparador.
- Crear: `quienes_somos.py` — página Quiénes somos.
- Crear: `assets/comparador.js`, `assets/confianza.js`, `assets/sedes/*.jpg`.
- Crear: `tests/test_confianza.py`, `tests/test_pruebas.py`, `tests/test_comparador.py`.
- Modificar: `generar_web.py` (headers ×3, `build_card_html`, `build_coche_html`, `build_index_html`, `main`, sitemap), `assets/estilos.css`.

### Task 1: confianza_dwa.garantia_corta (TDD)
- [ ] Test: `"33 meses (de fábrica)"`→`"33 meses de garantía"`; `"21 meses (de fábrica) + 24 meses de extensión"`→`"21 meses de garantía + 24 de extensión"`; `"12 meses desde la compra (Das WeltAuto)"`→`"12 meses de garantía"`; `""`/`None`→`""`.
- [ ] Run `python3 -m unittest tests.test_confianza -v` → FAIL; implementar con regex `(\d+) meses` y `\+ (\d+) meses de extensión`; → PASS; commit.

### Task 2: sello + nav del header (3 headers)
- [ ] `confianza_dwa.sello_html()` → `<a class="rd-dwa-sello" href="https://www.dasweltauto.es/..."><img src="/assets/dasweltauto-logo.svg" alt="Das WeltAuto"><span>{i18n Concesionario oficial / Official dealer}</span></a>`.
- [ ] `confianza_dwa.nav_html(base, activo)` → botones "Coches" (`{base}/`) y "Quiénes somos" (`{base}/quienes-somos/`), `activo` ∈ {"coches","quienes"}.
- [ ] En `build_coche_html`, `build_index_html`, `build_historial_precios_html`: envolver `<strong>Automóviles Rueda</strong>` + sello en `<div class="rd-marca">`, añadir nav antes de `lang_toggle_html()`.
- [ ] CSS `.rd-dwa-sello`, `.rd-marca`, `.rd-nav` (+ móvil compacto). Commit.

### Task 3: pastilla de garantía en la tarjeta
- [ ] `confianza_dwa.pastilla_tarjeta_html(ficha, i18n_span)` → `<span class="rd-card-dwa">🛡 {garantía corta o "Garantía oficial"} · Revisado 126 puntos</span>`.
- [ ] `build_card_html(..., ficha=None)` la pinta tras `.rd-card-pills`; `build_index_html` recibe `fichas` y pasa `fichas.get(clave_ficha(car))`. Commit.

### Task 4: banners entre filas
- [ ] `confianza_dwa.banners_template_html(i18n_span, href_quienes)` → `<template id="rd-banners">` con 5 `<aside class="rd-banner">` (4 DWA + 1 `rd-banner-rueda` con CTA).
- [ ] `assets/confianza.js`: coloca clones antes de la tarjeta visible nº `max(cols,4)+i*max(cols*2,4)`; recoloca con MutationObserver sobre `#rd-grid` y en `resize`; ignora tarjetas ocultas (`offsetParent===null`).
- [ ] Incluir template + `<script src=asset("confianza.js")>` en index. CSS `.rd-banner*`. Commit.

### Task 5: pruebas en vídeo (TDD)
- [ ] `pruebas.json`: `{"_nota":..., "CUPRA Formentor": {"videos":[{"youtube":"97rquY9Z0SY","titulo":"...","medio":"...","anio":2021,"desde":2020,"hasta":2024}]}}` — solo IDs comprobados (oEmbed de YouTube responde 200 y el título coincide con el modelo).
- [ ] Test `pruebas.bloque_html`: modelo sin datos → `""`; filtros `desde/hasta/version_contiene` excluyen; máximo 3; contiene `img.youtube.com/vi/<id>/hqdefault.jpg` y enlace `youtube.com/watch?v=<id>`.
- [ ] Implementar reutilizando `prensa._clave`, `prensa._aplica`, `prensa._anio_matriculacion`. Commit.

### Task 6: final de la ficha
- [ ] `confianza_dwa.tarjeta_ficha_html(ficha, i18n_span)` (6 pastillas; la garantía real destacada; sin ficha → "Garantía oficial").
- [ ] En `build_coche_html`: insertar `pruebas.bloque_html(...) + tarjeta_ficha_html(...)` justo antes de `<div class="rd-footnote">` (no en vendidos). Commit.

### Task 7: comparador completo (TDD datos + JS)
- [ ] `comparador.datos(car, ficha)` → dict compacto: `precio,km,fecha,garantia,comb,dgt,cv,par,cambio,acel,vmax,consumo,co2,aut_el,aut,maletero,largo,ancho,alto,peso,extras(list),serie(list)` con números parseados (`_n("1.717 Kg")→1717`, `_n("7,9 s")→7.9`).
- [ ] Tests de `_n` y de `datos` con una ficha real de `fichas_tecnicas.json` (dwa-193600528 → cv 204, maletero 345, largo 4451).
- [ ] `build_index_html` incrusta `<script>window.RD_CMP={json}</script>` (claves = `id_estable_coche`).
- [ ] `assets/comparador.js`: mueve la lógica de bandeja actual (sin cambios de comportamiento) y dibuja la tabla (grupos, ★ mejor dato con reglas de la spec, barra de maletero, "solo lo que cambia", "equipamiento completo").
- [ ] Quitar el `<script>` inline del comparador de `build_index_html`; overlay HTML nuevo. CSS `.rd-cx*`. Commit.

### Task 8: Quiénes somos
- [ ] Copiar fotos a `assets/sedes/` (malaga-seat, malaga-ocasion, velez, antequera, taller).
- [ ] `quienes_somos.build_html(perfil, total_coches, header_html, footer_html)`; `main()` escribe `{out_dir}/quienes-somos/index.html` por perfil; añadir URL al sitemap. Commit.

### Task 9: verificación
- [ ] `python3 -m unittest discover tests -v` → todo PASS.
- [ ] Previsualización: script en scratchpad que importa `generar_web` y escribe index + fichas + quiénes somos en una carpeta aparte (sin copiar fotos ni tocar producción); servir en localhost; revisar consola, ordenador y móvil, modo oscuro, inglés; capturas para Andrés.
- [ ] Con OK de Andrés: merge a `main` y push (se publica).
