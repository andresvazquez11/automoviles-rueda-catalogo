# Traductor ES/EN — Diseño

Fecha: 2026-09-18

## Objetivo

Un ícono de bandera en el header del catálogo (🇪🇸 / 🇬🇧) que traduce al
instante, sin recargar la página, el catálogo y la ficha de cada coche al
inglés. Debe funcionar igual en la página de Andrés (raíz) y en la de
Alejandro (`/alejandro/`), porque ambas comparten el mismo header generado.

## Alcance

**Se traduce:**
- Header, franja de "Destacados", controles de filtro/búsqueda/orden.
- Tarjetas del catálogo (`index.html`): modelo, specs, badges de estado
  ("Disponible" / "Reservado"), badges de oferta.
- Ficha individual de cada coche (`coches/*.html`): versión completa,
  lista de equipamiento, specs.

**No se traduce (queda en español):**
- La calculadora de financiación (texto legal/técnico de campañas VWFS) —
  riesgo de traducir mal un término financiero.

**No se convierte:** precios (€) y kilometraje (km) se muestran igual en
ambos idiomas — es un vehículo que se compra en España.

## Cómo se traduce cada tipo de texto

### 1. Vocabulario fijo (sin IA)

Un diccionario simple en `generar_web.py` para los campos de valores
conocidos y acotados:

- `combustible`: Gasolina/Diésel/Híbrido/Eléctrico → Petrol/Diesel/Hybrid/Electric
- `cambio`: Manual/Automático → Manual/Automatic
- `estado` (display): Disponible/Reservado → Available/Reserved
- Etiquetas de UI fijas (botones, filtros, placeholders del buscador, etc.)

Instantáneo, sin llamadas a IA, sin posibilidad de error de traducción.

### 2. Texto libre (con IA, cacheado)

Para `version` (string largo de cada coche) y cada línea de
`equipamiento[]`, que no tienen un vocabulario fijo:

- Se usa la API de Google Gemini (misma `GOOGLE_API_KEY` ya configurada en
  `.env` para otros scripts del proyecto — no hace falta ninguna cuenta
  nueva).
- El resultado se guarda en `traducciones_cache.json`, indexado por un hash
  del texto en español. Antes de traducir, `generar_web.py` revisa el
  caché — si el texto ya fue traducido antes (no cambió desde la corrida
  anterior), reusa la traducción guardada en vez de volver a llamar a la
  IA.
- Solo se llama a Gemini para texto nuevo o modificado. En una corrida
  típica (pocos coches nuevos por día), la mayoría de las traducciones
  salen del caché.
- `traducciones_cache.json` se versiona en el repo (como
  `historial_precios.json`) para no perder el caché entre ejecuciones.

### 3. Resultado: ambos idiomas quedan en el HTML generado

Cada texto traducible se renderiza con sus dos versiones ya calculadas,
como atributos `data-es="..."` / `data-en="..."` (o el mecanismo equivalente
que decida el plan de implementación). La página sigue siendo 100%
autocontenida: nadie llama a ningún servicio de traducción en el momento en
que un visitante abre la web — todo el trabajo de traducción ya ocurrió al
generar el sitio.

## El botón de bandera

- Aparece en el header (`rd-header`), junto a los datos del asesor —
  mismo lugar en ambos perfiles, ya que el header se genera desde la misma
  función compartida.
- Dos íconos: 🇪🇸 (activo por defecto) y 🇬🇧.
- Al hacer clic en 🇬🇧, un script recorre el DOM y reemplaza cada texto
  traducible por su versión `data-en`; al volver a 🇪🇸, se restaura
  `data-es`. Sin recargar la página.
- La elección se guarda en `localStorage` del visitante. Si cambia a inglés
  en el catálogo y luego entra a la ficha de un coche, esa ficha se abre
  directamente en inglés (cada página lee la preferencia guardada al
  cargar).
- Independiente por visitante/dispositivo — no afecta a otros visitantes ni
  al idioma por defecto de la página (que sigue siendo español).

## Qué NO cambia

- El flujo diario de actualización sigue igual, solo se le suma el paso de
  traducción (con caché, así que el costo/tiempo extra es mínimo salvo la
  primera corrida).
- La calculadora de financiación no se toca.
- El HTML sigue sin dependencias externas para el visitante — Gemini solo
  se usa en tiempo de generación (en el ordenador de Andrés), nunca desde
  el navegador del cliente.

## Fuera de alcance

- Otros idiomas además de inglés.
- Traducción de la calculadora de financiación.
- Conversión de moneda o unidades.
