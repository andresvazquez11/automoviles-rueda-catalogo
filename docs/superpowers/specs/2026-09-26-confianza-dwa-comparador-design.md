# Confianza Das WeltAuto, comparador completo, pruebas en vídeo y "Quiénes somos" — diseño

Fecha: 26/09/2026 · Aprobado por Andrés con maquetas visuales (v1–v4).

## Objetivo
Generar más confianza al comprar: que se vea claramente que Rueda es concesionario
oficial Das WeltAuto, que el cliente encuentre las ventajas mientras navega, que
pueda ver pruebas en vídeo del modelo, comparar fichas completas y conocer la empresa.

## 1. Presencia Das WeltAuto
- **Sello en el encabezado** (todas las páginas: portada, fichas, historial, quiénes somos):
  pastilla blanca con el logo `assets/dasweltauto-logo.svg` grande (≈34 px alto) y
  debajo, en letra pequeña, "CONCESIONARIO OFICIAL". Va junto a "Automóviles Rueda".
- **Banners entre las filas de coches (portada)**: blancos, filo izquierdo naranja
  `#e8501e`, icono en círculo azul `#1c2f6e`, título azul Oswald, frase gris, logo DWA
  a color a la derecha. Orden:
  1. Garantía oficial en cada coche
  2. Revisado en 126 puntos
  3. Kilómetros certificados
  4. Asistencia 24 h en toda Europa
  5. Taller oficial propio (variante Rueda: filo e icono rojo `#C8232B`, botón "Conócenos" → Quiénes somos)
  Posición: ordenador cada 2 filas (la primera tras la 1ª fila); móvil cada 4 coches.
  Se recolocan por JS al filtrar/buscar/ordenar (solo cuentan tarjetas visibles).
  Móvil: una sola línea (sin frase), ≈ mitad de alto.
- **Pastilla en cada tarjeta**: "🛡 {garantía real} · Revisado 126 puntos". La garantía sale de
  `fichas_tecnicas.json` → `gen.garantia` ("33 meses (de fábrica)" → "33 meses de garantía";
  "+ 24 meses de extensión" → "+ 24 de extensión"). Sin ficha: "Garantía oficial".
- **Tarjeta al final de la ficha** (después de la calculadora y de los vídeos):
  "Comprando este coche en Das WeltAuto" con 6 pastillas: garantía real de la unidad
  (destacada), revisado 126 puntos, km certificados, asistencia 24 h en Europa,
  taller oficial Rueda, financiación a medida.
- **NO se publica**: "hasta 24 meses de garantía", "15 días / 1.000 km", garantía de batería.

## 2. Comparador completo (reemplaza al actual)
Mismo flujo (+ Comparar, hasta 3, bandeja, "Ver comparación"). La vista pasa a una tabla
con cabecera fija (foto, modelo, versión, precio) y grupos:
Precio y uso · Motor y prestaciones · Consumo y autonomía · Medidas y maletero · Equipamiento.
- Mejor dato por fila en verde con ★ (menor precio/km/consumo/CO₂/0-100/peso; mayor
  potencia/par/vmax/autonomía/maletero/garantía/nº extras; etiqueta DGT CERO>ECO>C>B).
- Barra visual en maletero. Casilla "Mostrar solo lo que cambia" (activa por defecto).
- "Ver equipamiento completo": lista de serie + extras lado a lado con ✓ / —.
- Datos: se incrustan en la portada como JSON compacto por id de tarjeta (`data-id`),
  construido desde `fichas_tecnicas.json` + `datos_coches.json`. Coche sin ficha técnica:
  muestra lo básico y "—".

## 3. Pruebas en vídeo (ficha)
- Nuevo `pruebas.json` (editado a mano, igual filosofía que `prensa.json`): por modelo,
  lista de vídeos de YouTube REALES y verificados (id, título, medio, año) con filtros
  `desde`/`hasta`/`version_contiene` para no mezclar generaciones. Modelo sin vídeos → no hay bloque.
- Tarjeta "Míralo en acción · pruebas en vídeo" (miniaturas con ▶, abre YouTube en pestaña nueva)
  + nota "Pruebas del modelo publicadas por medios especializados, no de esta unidad".
- Posición: al final de la ficha, justo antes de la tarjeta Das WeltAuto.
- Los "A favor / A tener en cuenta" de la maqueta NO se publican en esta fase (tendrían que
  salir literalmente de pruebas publicadas; se añadirán después si Andrés lo pide).

## 4. Página "Quiénes somos"
`/quienes-somos/` (y `/alejandro/quienes-somos/`), enlazada desde un botón en el encabezado
("Coches" | "Quiénes somos"). Contenido: hero con foto de la sede de Málaga, cifras (1995 ·
3 ciudades · 3 marcas · coches disponibles hoy), historia, línea de tiempo, 4 sedes con foto
y "Cómo llegar", bloque del taller propio (C. Esteban Salazar Chapela 9, Pol. Guadalhorce),
marcas oficiales y CTA WhatsApp del asesor.
- Direcciones (Google Maps): Málaga SEAT/CUPRA Av. de Velázquez 105 · Das WeltAuto Av. de
  Velázquez 103 · Vélez-Málaga Av. del Rey Juan Carlos I · Antequera C. Papabellotas 7
  (posventa C. Torre del Hacho 23).
- **Fotos**: las de Google Maps son de usuarios (no del propietario). Se usan para la prueba;
  antes de publicar Andrés decide si se sustituyen por fotos propias.
- Móvil: los botones del encabezado se compactan para no alargar la cabecera.

## Técnico
- Todo se genera desde `generar_web.py` (funciones nuevas pequeñas y separadas); CSS nuevo en
  `assets/estilos.css`; JS del comparador y banners en `assets/` (se regeneran, no a mano).
- Traducción EN: textos fijos nuevos con `i18n_span` (es/en).
- Modo oscuro: los componentes nuevos respetan `body.rd-dark`.
- Verificación: previsualización local generada en carpeta aparte (sin tocar producción),
  capturas ordenador + móvil, sin errores de consola. Publicación solo con OK de Andrés.
