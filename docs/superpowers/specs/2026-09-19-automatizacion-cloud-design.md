# Automatización en la nube del catálogo — Diseño

Fecha: 2026-09-19

## Objetivo

Hoy Andrés actualiza el catálogo dando doble clic a
`1️⃣ Actualizar Todo — Cambios + Fotos.command` en su Mac, todos los días.
Quiere que esto ocurra solo, dos veces al día, **sin depender de él ni de que
su computadora esté encendida**, y enterarse por correo si salió bien o si
algo falló.

## Arquitectura

Todo corre dentro de GitHub, la misma cuenta que ya aloja el repo y publica
la web — sin servicios nuevos que pagar ni mantener. Un flujo de trabajo de
**GitHub Actions** programado corre en servidores de GitHub, ejecuta
exactamente los mismos scripts Python que corren hoy en el Mac de Andrés, y
sube los cambios al repo (que GitHub Pages ya publica automáticamente).

```
┌─────────────────────────┐
│ GitHub Actions (cron)    │   10:00 y 16:00 hora España, lun-sáb
│ .github/workflows/       │──────────────────────────────────────┐
│ actualizar-catalogo.yml  │                                       │
└─────────────────────────┘                                       │
        │                                                          │
        │ 1. Restaura caché de fotos/ (de la corrida anterior)     │
        │ 2. actualizar_catalogo.py  (scraping DWA + JSON)         │
        │ 3. descargar_fotos_galeria.py  (fotos nuevas)            │
        │ 4. Borra carpetas de fotos de coches ya no activos       │
        │ 5. generar_web.py  (web + traducción + coches_lista.json)│
        │ 6. Genera PDF liviano (1 foto/coche, imágenes redimens.) │
        │ 7. Guarda caché de fotos/ actualizado                    │
        │ 8. git commit + push (token automático del workflow)     │
        │ 9. Envía correo (éxito con PDF adjunto, o error)         │
        ▼                                                          ▼
┌─────────────────────┐                                  ┌──────────────────┐
│ GitHub Pages         │  publica solo tras el push       │ Gmail de Andrés   │
│ (sin cambios)         │◀─────────────────────────────── │ (correo diario)  │
└─────────────────────┘                                  └──────────────────┘
```

## Horario (a prueba de cambio de horario)

España cambia entre CET (invierno) y CEST (verano), pero los horarios de
GitHub Actions son siempre en UTC fijo y no se ajustan solos. Para que
siempre dispare a las 10:00 y 16:00 hora española real, sin importar la
época del año, el workflow define **4 disparadores por cron** (cubriendo
ambos husos posibles) y cada corrida empieza revisando la hora real en
Madrid — si no es exactamente una de las horas objetivo, termina al toque
sin hacer nada (corrida "vacía", instantánea, sin costo real).

```yaml
on:
  schedule:
    - cron: '0 8 * * 1-6'   # 10:00 CEST (verano)
    - cron: '0 9 * * 1-6'   # 10:00 CET (invierno)
    - cron: '0 14 * * 1-6'  # 16:00 CEST (verano)
    - cron: '0 15 * * 1-6'  # 16:00 CET (invierno)
  workflow_dispatch: {}     # botón "Run workflow" para pruebas manuales
```

Domingo queda libre, como pediste ("de lunes a sábado").

## Las fotos entre corridas (sin depender de disco local)

- **Limpieza ya hecha:** se borró `fotos/_archivo_carpetas_viejas/`
  (4.8 GB de coches vendidos hace tiempo, nunca limpiados). `fotos/` pasó de
  5.3 GB a **548 MB**.
- **Nuevo paso, automático, en cada corrida:** después de descargar fotos
  nuevas, se borra la carpeta de `fotos/` de cualquier coche que ya no esté
  en `datos_coches.json` (vendido/retirado). Esto evita que la basura vuelva
  a acumularse, tanto en tu Mac como en la nube.
- **Persistencia en la nube:** GitHub Actions no tiene disco permanente
  entre corridas — se usa su función de **caché** (`actions/cache`, gratis,
  hasta 10 GB por repositorio) para guardar `fotos/` entre una corrida y la
  siguiente, así nunca hay que re-descargar todo desde cero. Con `fotos/` en
  ~550 MB y creciendo lento (solo coches realmente nuevos), entra sobrado.

## PDF — versión completa (manual) + versión liviana (automática)

- El botón de tu escritorio sigue funcionando exactamente igual que hoy —
  genera el PDF completo (8 fotos por coche, ~148 MB) cuando vos lo pidas.
  Nada cambia ahí.
- Para el correo automático, se agrega una **versión liviana** del mismo
  generador de PDF: 1 foto principal por coche, redimensionada al tamaño
  real en que se ve en la página (no a resolución de cámara). Estimado:
  **8-14 MB**, entra sin problema como adjunto de Gmail.
- Esta versión liviana es la que se genera y se adjunta en cada corrida
  automática — nunca se commitea al repo (sigue la misma regla que el PDF
  completo: es un archivo de salida, no se versiona).

## Correos (éxito y error)

Usando el Gmail de Andrés (`andrescovidelpi@gmail.com`) vía SMTP con una
contraseña de aplicación — ya generada y guardada como secreto encriptado
de GitHub (`GMAIL_APP_PASSWORD`), nunca visible en el código ni en el repo.

- **Si todo sale bien:** correo con asunto tipo
  `✅ Catálogo actualizado — 18/09/2026 10:00` y cuerpo con un resumen corto
  (coches disponibles, nuevos, vendidos desde la corrida anterior) + el PDF
  liviano adjunto.
- **Si algo falla** (en cualquier paso — scraping, fotos, traducción, etc.):
  correo con asunto `⚠️ Falló la actualización del catálogo` con el motivo
  del error y un enlace directo a los logs de esa corrida en GitHub, para
  poder revisar qué pasó.
- Como red de seguridad adicional y gratuita, GitHub también manda un aviso
  propio (más técnico, en inglés) cuando un workflow falla, a quien esté
  seleccionado como "Watching" el repositorio — queda de respaldo, sin
  esfuerzo extra.

## Credenciales (ya configuradas)

Guardadas como secretos encriptados en GitHub (Settings → Secrets and
variables → Actions), nunca en el código:
- `GOOGLE_API_KEY` — la misma que ya usás en `config.txt` para las
  traducciones (reutilizada, no es una nueva).
- `GMAIL_APP_PASSWORD` — la contraseña de aplicación generada para el envío
  de correos.
- El `git push` de cada corrida usa el token automático que GitHub le da a
  cada workflow (con permiso de escritura sobre este mismo repositorio) —
  no hace falta el Personal Access Token que sí se usa en `/admin/`, porque
  ahí quien escribe es un navegador externo; acá quien escribe es el propio
  GitHub.

## Qué NO cambia

- El botón `.command` del escritorio sigue funcionando igual, para cuando
  Andrés quiera correrlo a mano (ej. si necesita el catálogo actualizado
  ya mismo, sin esperar al próximo horario automático).
- Los prompts/carpetas de marketing (`generar_prompts_storyboard.py`, las
  carpetas "agente storyboard") siguen siendo 100% manuales, en su Mac,
  igual que hoy — no forman parte del proceso automático en la nube.
- El PDF completo (148 MB, 8 fotos/coche) sigue siendo manual, bajo pedido.
- Los coches destacados y el traductor ES/EN no se tocan.

## Puesta en marcha (con prueba antes de activar el horario)

1. Se sube el workflow con el disparador manual (`workflow_dispatch`)
   activo desde el día uno.
2. Antes de confiar en el horario automático, se dispara manualmente una
   vez desde GitHub ("Run workflow") para confirmar que el scraping
   funciona igual de bien desde la nube (posible riesgo real, no
   verificable de antemano: que Das WeltAuto trate distinto el tráfico que
   viene de servidores de Google/GitHub vs. la conexión normal de Andrés).
3. Se revisa el resultado: ¿llegó el correo?, ¿se ve bien la web?, ¿el PDF
   liviano abre bien?
4. Recién ahí se confirma que el horario automático (10:00 y 16:00,
   lunes a sábado) queda activo sin supervisión.

## Fuera de alcance

- Rediseñar cómo se identifican las carpetas de fotos (por número de
  anuncio en vez de número+modelo) — no hace falta, el problema real era
  solo la falta de limpieza, ya resuelta.
- Limpieza de `web_fotos/` (las fotos ya publicadas en la web) — pesa 468
  MB, no es un problema hoy; se puede revisar aparte en el futuro si crece.
- Envío del PDF completo (148 MB) por correo.
