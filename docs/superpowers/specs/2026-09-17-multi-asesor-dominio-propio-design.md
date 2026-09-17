# Multi-asesor + dominio propio — Design Spec

**Fecha:** 2026-09-17
**Estado:** Aprobado, pendiente de implementación

## Contexto

El catálogo (`generar_web.py`) genera `index.html` y `coches/*.html` con los datos
de contacto de Andrés Vázquez fijos en 3 constantes (`COMERCIAL_NOMBRE`,
`COMERCIAL_TELEFONO`, `COMERCIAL_EMAIL`, líneas 22-24). Se publica en GitHub
Pages en `https://andresvazquez11.github.io/automoviles-rueda-catalogo/`
(rama `main`, raíz del repo, sin `CNAME`).

Andrés quiere que su compañero Alejandro Morales Pájaro tenga su propia versión
de la misma página (mismos coches, mismas fotos, actualizados a diario igual
que hoy) pero con sus propios datos de contacto en el header/footer y en el
botón de WhatsApp, accesible desde una dirección distinta — sin duplicar el
trabajo diario de carga de coches.

Se decidió además comprar un dominio propio (`automovilesruedaocasion.com`,
ya adquirido en IONOS) para que la URL del sitio no lleve el nombre de usuario
de GitHub de nadie.

## Objetivo

1. El sitio se sirve en `automovilesruedaocasion.com` (dominio propio) en vez
   de `andresvazquez11.github.io/automoviles-rueda-catalogo/`.
2. La raíz del dominio (`automovilesruedaocasion.com/`) muestra la versión de
   Andrés (como hoy).
3. `automovilesruedaocasion.com/alejandro/` muestra la misma lista de coches y
   las mismas fichas, pero con el nombre, teléfono, email y enlace de WhatsApp
   de Alejandro Morales Pájaro (685 90 77 41, alejandro.morales@automovilesrueda.com)
   en header, footer y botón flotante de WhatsApp.
4. El flujo diario de actualización (correr `generar_web.py`, que hoy genera
   un único sitio) no cambia de pasos: sigue siendo una sola ejecución, que
   ahora produce internamente las dos versiones.
5. Las fotos (`web_fotos/`) no se duplican — ambas versiones referencian los
   mismos archivos.

## Fuera de alcance

- No se agrega la dirección física del concesionario (Avenida Velázquez 103)
  a ningún footer — hoy no se muestra para nadie.
- Los íconos de redes sociales del header (Instagram/Facebook/TikTok) quedan
  compartidos entre ambas versiones — son cuentas del concesionario, no
  personales.
- No se toca el usuario de GitHub `andresvazquez11` ni ningún otro repo de esa
  cuenta (p.ej. `Club-Natacion-Axarquia`).
- No se generan más de dos perfiles por ahora (solo Andrés y Alejandro).

## Diseño

### 1. Dominio y DNS (fuera del código, ya en curso)

- Dominio comprado: `automovilesruedaocasion.com` (IONOS).
- DNS: 4 registros `A` en `@` apuntando a las IPs de GitHub Pages
  (185.199.108/109/110/111.153) + `CNAME` en `www` apuntando a
  `andresvazquez11.github.io`.
- Archivo `CNAME` en la raíz del repo con el contenido `automovilesruedaocasion.com`.
- Una vez propague el DNS, activar "Enforce HTTPS" en Settings → Pages del repo.

### 2. Perfiles de asesor en `generar_web.py`

Reemplazar las 3 constantes sueltas por una lista de perfiles:

```python
PERFILES = [
    {
        "carpeta": "",  # raíz del sitio
        "nombre": "Andrés Vázquez",
        "telefono": "610 02 90 56",
        "email": "andres.vazquez@automovilesrueda.com",
    },
    {
        "carpeta": "alejandro",
        "nombre": "Alejandro Morales Pájaro",
        "telefono": "685 90 77 41",
        "email": "alejandro.morales@automovilesrueda.com",
    },
]
```

Las funciones que hoy leen `COMERCIAL_NOMBRE` / `COMERCIAL_TELEFONO` /
`COMERCIAL_EMAIL` como constantes de módulo (`footer_whatsapp_html`, los dos
bloques de header en línea ~1058 y ~1232) pasan a recibir el perfil como
parámetro.

**Bug a corregir de paso:** el botón de WhatsApp tiene el número
`34610029056` escrito a mano en el `href` (línea 102), independiente de
`COMERCIAL_TELEFONO`. Debe derivarse siempre de `perfil["telefono"]`
(`"34" + telefono.replace(" ", "")`), igual que el texto del mensaje
("Hola {nombre}, ...") ya usa el nombre del perfil.

### 3. Rutas de assets: de relativas a absolutas por dominio

Hoy las fichas de coche referencian imágenes y el índice con rutas relativas
a su propia carpeta (`web_fotos/NN/foto.jpg`, `../index.html`). Si se genera
una segunda copia de `index.html`/`coches/*.html` dentro de `/alejandro/`,
esas rutas relativas apuntarían a `/alejandro/web_fotos/...`, que no existe.

Cambio: las referencias a fotos pasan a ser absolutas desde la raíz del
dominio (`/web_fotos/NN/foto.jpg`, `/coches/NN-slug.html`), independientemente
de en qué carpeta de perfil se esté generando la página. Esto permite que
**ambos perfiles compartan los mismos archivos de fotos sin duplicarlos** —
solo se duplica el HTML generado (liviano, ~50 fichas de pocos KB cada una).

El enlace "Volver al catálogo" / "Ver disponibles" de una ficha sí debe ser
específico del perfil (`/index.html` para las fichas de Andrés,
`/alejandro/index.html` para las de Alejandro), para que el visitante vuelva
al índice correcto.

`DOMINIO_WEB` (usado en `og:url`/`og:image`) se actualiza a
`https://automovilesruedaocasion.com` y se le añade el prefijo de carpeta del
perfil correspondiente al generar cada versión.

### 4. Estructura de salida

```
/                              (dominio → versión Andrés)
  CNAME
  index.html
  coches/
    01-slug.html
    ...
  web_fotos/                   (compartido por ambos perfiles)
    01/...
  alejandro/
    index.html
    coches/
      01-slug.html
      ...
```

### 5. Orquestación

`main()` en `generar_web.py` pasa a iterar sobre `PERFILES`, llamando a la
lógica de generación existente (extraída a una función parametrizada por
perfil y carpeta de salida) una vez por cada uno. Se ejecuta con
`python3 generar_web.py` exactamente igual que hoy — el flujo diario de
scraping + fotos + PDF + git push no cambia de pasos.

## Testing / verificación

- Generar localmente y servir con `python3 -m http.server` desde la raíz del
  repo; abrir `/index.html` y `/alejandro/index.html`.
- Verificar que las fotos cargan en ambas versiones (mismas rutas absolutas).
- Entrar a una ficha de coche desde cada índice y confirmar que "Volver al
  catálogo" lleva al índice correspondiente (no al del otro perfil).
- Verificar que el botón de WhatsApp de cada versión abre con el número y
  nombre correctos en el mensaje prellenado.
- Tras el deploy, verificar HTTPS y que ambas rutas cargan en
  `automovilesruedaocasion.com` y `automovilesruedaocasion.com/alejandro/`.
