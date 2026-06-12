"""
Actualización automática del catálogo Automóviles Rueda
- Scraping en vivo de Das WeltAuto
- Comparación con datos anteriores
- Informe de cambios (nuevos, vendidos, reservados, bajadas de precio)
- Historial diario: acumula todos los cambios del día aunque actualices varias veces
- Regeneración de PDF, fotos y prompts solo de los coches afectados
"""
import asyncio, json, shutil
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright
from catalogo_rueda_v2 import (
    obtener_coches_del_listado, enriquecer_coche,
    crear_pdf, get_foto_principal, nombre_carpeta,
    sincronizar_estado_carpeta,
    PHOTOS_DIR, OUTPUT_DIR, PDF_PATH
)

CACHE           = OUTPUT_DIR / "datos_coches.json"
CACHE_BAK       = OUTPUT_DIR / "datos_coches_anterior.json"
INFORME         = OUTPUT_DIR / "informe_cambios.txt"

# ── Historial diario ───────────────────────────────────────────
# Snapshot del inicio del día — se toma una vez por día
SNAPSHOT_DIA       = OUTPUT_DIR / "datos_coches_ayer.json"
SNAPSHOT_DIA_FECHA = OUTPUT_DIR / "datos_coches_ayer_fecha.txt"
CAMBIOS_HOY_FILE   = OUTPUT_DIR / "cambios_hoy.json"
HISTORIAL_PRECIOS  = OUTPUT_DIR / "historial_precios.json"
CONTADOR_HOY_FILE  = OUTPUT_DIR / "actualizaciones_hoy.txt"

def hoy_str():
    return datetime.now().strftime("%Y-%m-%d")

def gestionar_snapshot_diario(anteriores: list, cache_bak: Path):
    """
    Gestiona el snapshot del inicio del día para comparaciones diarias.
    - Si es un día nuevo: guarda el estado actual como 'inicio del día'
    - Si es el mismo día: carga el snapshot existente
    - Si el snapshot tiene los mismos datos que el actual (inicialización incorrecta):
      intenta usar el backup anterior como línea base
    Devuelve (baseline: list, n_actualizacion: int)
    """
    fecha_guardada = ""
    if SNAPSHOT_DIA_FECHA.exists():
        fecha_guardada = SNAPSHOT_DIA_FECHA.read_text(encoding="utf-8").strip()

    hoy = hoy_str()
    n_act = 1

    if fecha_guardada != hoy:
        # Día nuevo: guardar el estado ANTERIOR como baseline del día
        # Usamos 'anteriores' (datos antes de esta actualización = "ayer")
        if anteriores:
            SNAPSHOT_DIA.write_text(
                json.dumps(anteriores, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        SNAPSHOT_DIA_FECHA.write_text(hoy, encoding="utf-8")
        CAMBIOS_HOY_FILE.write_text(
            json.dumps({"nuevos": [], "vendidos": [], "cambios": [], "actualizaciones": 0},
                       ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        CONTADOR_HOY_FILE.write_text("1", encoding="utf-8")
        n_act = 1
        print(f"  📅 Nuevo día — baseline guardado ({len(anteriores)} coches)")
    else:
        # Mismo día: incrementar contador
        if CONTADOR_HOY_FILE.exists():
            try:
                n_act = int(CONTADOR_HOY_FILE.read_text(encoding="utf-8").strip()) + 1
            except ValueError:
                n_act = 1
        CONTADOR_HOY_FILE.write_text(str(n_act), encoding="utf-8")
        print(f"  📅 Actualización #{n_act} del día {datetime.now().strftime('%d/%m/%Y')}")

    # Cargar el baseline del día
    baseline = []
    if SNAPSHOT_DIA.exists():
        try:
            baseline = json.loads(SNAPSHOT_DIA.read_text(encoding="utf-8"))
        except Exception:
            baseline = []

    # Si el baseline del día es idéntico al estado actual (problema de inicialización),
    # intentar usar el backup anterior como referencia más antigua
    if baseline and anteriores and n_act > 1:
        ids_baseline = {id_coche(c) for c in baseline}
        ids_ant = {id_coche(c) for c in anteriores}
        if ids_baseline == ids_ant:
            # Baseline = anteriores (mismo estado), intentar usar backup
            if cache_bak.exists():
                try:
                    bak = json.loads(cache_bak.read_text(encoding="utf-8"))
                    ids_bak = {id_coche(c) for c in bak}
                    if ids_bak != ids_baseline:
                        baseline = bak
                        print(f"  ℹ️  Usando backup anterior como baseline del día (más antiguo)")
                except Exception:
                    pass

    return baseline, n_act


def acumular_cambios_hoy(nuevos, vendidos, cambios):
    """
    Acumula los cambios del día en cambios_hoy.json.
    Los cambios de precio se actualizan (si el mismo coche ya tenía cambio,
    se mantiene el precio original del día y se actualiza el precio nuevo).
    """
    acum = {"nuevos": [], "vendidos": [], "cambios": [], "actualizaciones": 0}
    if CAMBIOS_HOY_FILE.exists():
        try:
            acum = json.loads(CAMBIOS_HOY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    acum["actualizaciones"] = acum.get("actualizaciones", 0) + 1

    # Nuevos: agregar si no está ya
    ids_nuevos = {id_coche(c) for c in acum["nuevos"]}
    for c in nuevos:
        if id_coche(c) not in ids_nuevos:
            acum["nuevos"].append(c)

    # Vendidos: agregar si no está ya
    ids_vendidos = {id_coche(c) for c in acum["vendidos"]}
    for c in vendidos:
        if id_coche(c) not in ids_vendidos:
            acum["vendidos"].append(c)

    # Cambios: acumular — si el mismo coche ya tiene un cambio registrado hoy,
    # actualizar el precio nuevo (pero conservar el texto descriptivo completo)
    ids_cambios = {id_coche(e["coche"]): i for i, e in enumerate(acum["cambios"])}
    for entry in cambios:
        key = id_coche(entry["coche"])
        if key in ids_cambios:
            # Actualizar descripción de cambios (puede haber nueva bajada)
            acum["cambios"][ids_cambios[key]] = entry
        else:
            acum["cambios"].append(entry)

    CAMBIOS_HOY_FILE.write_text(
        json.dumps(acum, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return acum


# ── Identificador único fiable: URL del coche ──────────────
def id_coche(c):
    return c.get("url") or f"{c['modelo']}_{c['version']}_{c['precio']}"

def actualizar_historial_precios(actuales: list):
    """Actualiza historial_precios.json con los precios actuales.
    Guarda un registro por coche por día durante los últimos 10 días.
    Usado por generar_web.py para detectar bajadas de precio."""
    from datetime import date, timedelta
    hoy = date.today().isoformat()
    corte = (date.today() - timedelta(days=10)).isoformat()

    hist = {}
    if HISTORIAL_PRECIOS.exists():
        try:
            hist = json.loads(HISTORIAL_PRECIOS.read_text(encoding="utf-8"))
        except Exception:
            hist = {}

    for c in actuales:
        key = id_coche(c)
        try:
            precio = int(str(c["precio"]).replace(".", "").replace(",", "").split()[0])
        except Exception:
            continue
        registros = hist.get(key, [])
        # Purgar entradas más viejas de 10 días
        registros = [r for r in registros if r["fecha"] >= corte]
        # Solo añadir entrada si es un día nuevo o el precio cambió
        if not registros or registros[-1]["precio"] != precio:
            registros.append({"fecha": hoy, "precio": precio})
        hist[key] = registros

    # Purgar claves de coches que ya no están en el catálogo
    keys_activos = {id_coche(c) for c in actuales}
    hist = {k: v for k, v in hist.items() if k in keys_activos}

    HISTORIAL_PRECIOS.write_text(
        json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  📊 Historial de precios actualizado ({len(hist)} coches)")

def comparar(anteriores: list, actuales: list):
    ant_map = {id_coche(c): c for c in anteriores}
    act_map = {id_coche(c): c for c in actuales}

    nuevos    = [c for k, c in act_map.items() if k not in ant_map]
    vendidos  = [c for k, c in ant_map.items() if k not in act_map]
    cambios   = []

    for k, act in act_map.items():
        if k in ant_map:
            ant = ant_map[k]
            diffs = []
            # Estado: disponible → reservado
            if ant["estado"] != act["estado"]:
                diffs.append(f"Estado: '{ant['estado']}' -> '{act['estado']}'")
            # Precio bajado o subido
            try:
                p_ant = float(ant["precio"].replace(".","").replace(",","."))
                p_act = float(act["precio"].replace(".","").replace(",","."))
                if p_ant != p_act:
                    diff_e = p_act - p_ant
                    if diff_e > 0:
                        cambio_txt = f"SUBE +{abs(diff_e):,.0f} EUR  ({ant['precio']}€ -> {act['precio']}€)"
                    else:
                        cambio_txt = f"BAJA -{abs(diff_e):,.0f} EUR  ({ant['precio']}€ -> {act['precio']}€)"
                    diffs.append(f"Precio: {cambio_txt}")
            except Exception:
                pass
            if diffs:
                cambios.append({"coche": act, "cambios": diffs})

    return nuevos, vendidos, cambios

def generar_informe(nuevos, vendidos, cambios, anteriores, actuales,
                    cambios_hoy_acum=None, n_actualizacion=1):
    lines = []
    now   = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines += [
        "=" * 60,
        f"  INFORME DE CAMBIOS — AUTOMÓVILES RUEDA",
        f"  Generado: {now}  (actualizacion #{n_actualizacion} del dia)",
        f"  Anterior: {len(anteriores)} coches  ->  Actual: {len(actuales)} coches",
        "=" * 60, ""
    ]

    # ── Cambios de ESTA actualización ───────────────────────
    if not nuevos and not vendidos and not cambios:
        lines += ["  OK Sin cambios respecto a la actualizacion anterior.", ""]
    else:
        lines += [f"  CAMBIOS EN ESTA ACTUALIZACION:"]
        if nuevos:
            lines += [f"  NUEVO ({len(nuevos)}):"]
            for c in nuevos:
                lines.append(f"     + {c['modelo']} {c['version'][:50]}  |  {c['precio']}EUR  |  {c['ubicacion']}")
            lines.append("")
        if vendidos:
            lines += [f"  YA NO APARECE / VENDIDO ({len(vendidos)}):"]
            for c in vendidos:
                lines.append(f"     - {c['modelo']} {c['version'][:50]}  |  {c['precio']}EUR")
            lines.append("")
        if cambios:
            lines += [f"  CON CAMBIOS ({len(cambios)}):"]
            for entry in cambios:
                c = entry["coche"]
                lines.append(f"     ~ {c['modelo']} {c['version'][:45]}")
                for d in entry["cambios"]:
                    lines.append(f"       . {d}")
            lines.append("")

    # ── Resumen acumulado del día ────────────────────────────
    if cambios_hoy_acum and (cambios_hoy_acum.get("nuevos") or
                              cambios_hoy_acum.get("vendidos") or
                              cambios_hoy_acum.get("cambios")):
        n_hoy = cambios_hoy_acum.get("actualizaciones", n_actualizacion)
        lines += [
            "-" * 60,
            f"  RESUMEN DEL DIA (acumulado — {n_hoy} actualizaciones):",
            ""
        ]
        nuevos_hoy   = cambios_hoy_acum.get("nuevos", [])
        vendidos_hoy = cambios_hoy_acum.get("vendidos", [])
        cambios_hoy  = cambios_hoy_acum.get("cambios", [])

        if nuevos_hoy:
            lines += [f"  NUEVOS HOY ({len(nuevos_hoy)}):"]
            for c in nuevos_hoy:
                lines.append(f"     + {c['modelo']} {c['version'][:50]}  |  {c['precio']}EUR")
            lines.append("")
        if vendidos_hoy:
            lines += [f"  VENDIDOS/DESAPARECIDOS HOY ({len(vendidos_hoy)}):"]
            for c in vendidos_hoy:
                lines.append(f"     - {c['modelo']} {c['version'][:50]}  |  {c['precio']}EUR")
            lines.append("")
        if cambios_hoy:
            lines += [f"  CAMBIOS DE PRECIO/ESTADO HOY ({len(cambios_hoy)}):"]
            for entry in cambios_hoy:
                c = entry["coche"]
                lines.append(f"     ~ {c['modelo']} {c['version'][:45]}")
                for d in entry["cambios"]:
                    lines.append(f"       . {d}")
            lines.append("")
    else:
        lines += ["-" * 60, f"  Sin cambios acumulados en el dia de hoy.", ""]

    lines += [
        "-" * 60,
        f"  RESUMEN ACTUAL ({len(actuales)} coches):",
        f"  Disponibles:    {sum(1 for c in actuales if c['estado']=='Disponible')}",
        f"  No disponibles: {sum(1 for c in actuales if c['estado']!='Disponible')}",
        f"  SEAT:           {sum(1 for c in actuales if 'SEAT' in c['modelo'])}",
        f"  CUPRA:          {sum(1 for c in actuales if 'CUPRA' in c['modelo'])}",
        f"  Volkswagen:     {sum(1 for c in actuales if 'Volkswagen' in c['modelo'])}",
        "=" * 60,
    ]
    return "\n".join(lines)

async def main():
    print()
    print("=" * 60)
    print("  AUTOMÓVILES RUEDA — Actualización automática")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 60)

    # 1) Cargar datos anteriores (última actualización)
    anteriores = []
    if CACHE.exists():
        anteriores = json.loads(CACHE.read_text(encoding="utf-8"))
        shutil.copy(CACHE, CACHE_BAK)
        print(f"\n  Datos anteriores cargados: {len(anteriores)} coches")

    # 1b) Gestionar snapshot diario
    ayer, n_actualizacion = gestionar_snapshot_diario(anteriores, CACHE_BAK)

    # 2) Scraping en vivo
    print("\n  Conectando a Das WeltAuto...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx     = await browser.new_context(
            viewport   ={"width":1400,"height":900},
            user_agent =("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 Chrome/120 Safari/537.36")
        )
        page = await ctx.new_page()
        actuales_vivos = await obtener_coches_del_listado(page)
        total    = len(actuales_vivos)
        for c in actuales_vivos:
            c["_total"] = total

        # Los coches "fuente=motorflash" no tienen URL de DWA, así que nunca
        # coinciden con actuales_vivos (scrapeados de DWA) → integrar_motorflash.py
        # (paso 5c) gestiona su ciclo de vida de forma independiente. Se excluyen
        # aquí para que no aparezcan como "vendidos" en cada actualización.
        anteriores_dwa = [c for c in anteriores if c.get("fuente") != "motorflash"]

        # 3a) Comparar SOLO coches vivos (detección de nuevos/cambios/vendidos reales)
        nuevos, vendidos, cambios = comparar(anteriores_dwa, actuales_vivos)

        # Construir lista completa: vivos + anteriores que desaparecieron → No disponible
        # Se preservan en JSON para mostrarse como RESERVADO en la web
        vivos_ids = {id_coche(c) for c in actuales_vivos}

        # Identidad física del coche (independiente del URL): misma versión, km y precio
        # DWA a veces re-publica el mismo coche físico con un nuevo anuncio (nuevo URL/ID).
        # Si el coche "desaparecido" coincide en identidad física con uno vivo, NO se preserva.
        def _id_fisico(c):
            return (c.get("modelo",""), c.get("version",""), c.get("km",""), c.get("precio",""))

        vivos_fisicos = {_id_fisico(c) for c in actuales_vivos}

        # Caducidad: un coche "No disponible" se muestra máximo 2 días, luego desaparece
        from datetime import date, timedelta
        hoy_str   = date.today().isoformat()
        limite_str = (date.today() - timedelta(days=2)).isoformat()

        preservados = []
        preservados_vistos = set()  # deduplicar preservados por identidad física
        expirados = 0
        for ant in anteriores_dwa:
            if id_coche(ant) in vivos_ids:
                continue  # URL aún activo, ya está en actuales_vivos
            fis = _id_fisico(ant)
            if fis in vivos_fisicos:
                continue  # mismo coche físico re-publicado con nuevo URL
            if fis in preservados_vistos:
                continue  # evitar preservados duplicados entre sí

            copia = dict(ant)
            if copia.get("estado") == "Disponible":
                copia["estado"] = "No disponible"

            # Registrar cuándo desapareció de DWA (solo la primera vez)
            if not copia.get("fecha_reservado"):
                copia["fecha_reservado"] = hoy_str

            # Expirar coches que llevan más de 2 días sin aparecer en DWA
            if copia["fecha_reservado"] < limite_str:
                expirados += 1
                continue

            preservados_vistos.add(fis)
            preservados.append(copia)

        if expirados:
            print(f"  🗑️  {expirados} coche(s) expirado(s) eliminados (>2 días sin aparecer en DWA)")

        actuales = actuales_vivos + preservados
        coches_a_regenerar = {id_coche(c) for c in nuevos}
        coches_a_regenerar |= {id_coche(e["coche"]) for e in cambios}

        hay_cambios = bool(nuevos or vendidos or cambios)

        # Añadir a regenerar cualquier coche que no tenga foto_01.jpg
        # (foto principal puede haberse borrado o no haberse descargado correctamente)
        for _car in actuales:
            _key = id_coche(_car)
            if _key not in coches_a_regenerar:
                _n, _modelo = _car['n'], _car['modelo']
                _prefijo = f"{_n:02d} - {_modelo}"
                for _carp in PHOTOS_DIR.iterdir():
                    if _carp.is_dir() and _carp.name.startswith(_prefijo):
                        if not (_carp / 'foto_01.jpg').exists():
                            coches_a_regenerar.add(_key)
                        break

        # 3b) Comparar contra el snapshot de AYER (para acumular historial diario)
        ayer_dwa = [c for c in ayer if c.get("fuente") != "motorflash"]
        nuevos_vs_ayer, vendidos_vs_ayer, cambios_vs_ayer = comparar(ayer_dwa, actuales)
        cambios_hoy_acum = acumular_cambios_hoy(
            nuevos_vs_ayer, vendidos_vs_ayer, cambios_vs_ayer
        )

        # Informe rápido en consola
        print(f"\n  Comparacion completada:")
        print(f"     Nuevos vs ultima actualiz.:    {len(nuevos)}")
        print(f"     Desaparecidos vs ultima:       {len(vendidos)}")
        print(f"     Con cambios vs ultima:         {len(cambios)}")
        print(f"     Cambios acumulados hoy:        "
              f"{len(cambios_hoy_acum.get('cambios',[]))} precios / "
              f"{len(cambios_hoy_acum.get('nuevos',[]))} nuevos / "
              f"{len(cambios_hoy_acum.get('vendidos',[]))} vendidos")

        if not hay_cambios:
            print("\n  OK El catalogo no ha cambiado desde la ultima actualizacion.")

        # 3c) Sincronizar nombres de carpetas con el estado actual de cada coche
        # Renombra: 'SEAT Arona - 22.900€' ↔ 'SEAT Arona - 22.900€ · RESERVADO'
        renombradas = 0
        for car in actuales:
            resultado = sincronizar_estado_carpeta(
                car["n"], car["modelo"], car.get("precio", ""), car.get("estado", "Disponible")
            )
            if resultado:
                nombre_esperado = resultado.name
                # Solo reportar si cambió el estado
                key = id_coche(car)
                if key in {id_coche(c) for c in anteriores}:
                    ant = next((c for c in anteriores if id_coche(c) == key), {})
                    if ant.get("estado") != car.get("estado"):
                        sufijo = " · RESERVADO" if car["estado"] != "Disponible" else " (vuelve a disponible)"
                        print(f"  🔴 [{car['n']:02d}] {car['modelo']} {car.get('precio','')}€{sufijo}")
                        renombradas += 1
        if renombradas:
            print(f"  → {renombradas} carpeta(s) renombrada(s) por cambio de estado")

        # 4) Enriquecer: foto + equipamiento
        ant_map = {id_coche(c): c for c in anteriores}

        print(f"\n  Visitando fichas ({total} coches vivos)...")
        for car in actuales_vivos:
            key = id_coche(car)
            fin_ant = ant_map.get(key, {}).get("financiacion")
            necesita_financiacion = not fin_ant or not fin_ant.get('tipo')  # sin financiación o sin tipo/ejemplo

            if key not in coches_a_regenerar and key in ant_map and not necesita_financiacion:
                # Reutilizar equipamiento y financiación anteriores
                car["equipamiento"] = ant_map[key].get("equipamiento", [])
                car["fotos"]        = ant_map[key].get("fotos", [])
                car["financiacion"] = fin_ant

                # Renombrar carpeta si el número cambió
                n_ant   = ant_map[key]["n"]
                n_new   = car["n"]
                modelo  = car["modelo"]
                if n_ant != n_new:
                    nombre_nuevo = nombre_carpeta(n_new, modelo, car.get("precio", ""), car.get("estado", "Disponible"))
                    dir_new = PHOTOS_DIR / nombre_nuevo
                    prefijo_modelo = f"{n_ant:02d} - {modelo}"
                    for candidata in PHOTOS_DIR.iterdir():
                        if candidata.is_dir() and candidata.name.startswith(prefijo_modelo):
                            if not dir_new.exists():
                                candidata.rename(dir_new)
                                # Actualizar rutas de fotos al nuevo nombre de carpeta
                                car["fotos"] = sorted(
                                    str(f) for f in dir_new.glob("foto_*.jpg")
                                )
                            else:
                                # La carpeta destino ya existe — usar sus fotos
                                car["fotos"] = sorted(
                                    str(f) for f in dir_new.glob("foto_*.jpg")
                                )
                            break
            else:
                # Visitar ficha: coche nuevo, con cambios, o sin financiación aún
                if key not in ant_map:
                    tag = "NUEVO"
                elif key in coches_a_regenerar:
                    tag = "CAMBIO"
                else:
                    tag = "FIN"  # solo falta la financiación
                print(f"  [{tag}] [{car['n']:02d}/{total}] {car['modelo']} {car['version'][:40]}")
                await enriquecer_coche(page, car)

        await browser.close()

    # 5) Guardar JSON actualizado
    CACHE.write_text(json.dumps(actuales, ensure_ascii=False, indent=2), encoding="utf-8")
    actualizar_historial_precios(actuales)   # registro rolling 10 días para web

    # 5c) Integrar coches exclusivos de MotorFlash
    print("\n" + "─" * 60)
    try:
        import subprocess, sys as _sys
        _base = Path.home() / "Desktop" / "catalogo_automoviles_rueda"
        result = subprocess.run(
            [_sys.executable, str(_base / "integrar_motorflash.py")],
            check=False, capture_output=False
        )
        if result.returncode != 0:
            print("  ⚠️  integrar_motorflash.py terminó con error — continuando sin MF")
    except Exception as _e:
        print(f"  ⚠️  Error al integrar MotorFlash: {_e} — continuando sin MF")
    print("─" * 60)

    # 5d) Recargar actuales desde disco: integrar_motorflash.py puede haber
    # añadido/renumerado coches (fuente=motorflash) que no estaban en el
    # `actuales` en memoria. El PDF debe reflejar el estado final en disco.
    actuales = json.loads(CACHE.read_text(encoding="utf-8"))

    # 5b) Verificar integridad de fotos SIEMPRE y ANTES del PDF
    # Esto garantiza que el PDF y la web nunca usen fotos de otro coche,
    # independientemente de si hubo cambios en el catálogo o no.
    import subprocess, sys
    base = Path.home() / "Desktop" / "catalogo_automoviles_rueda"
    print("\n  Verificando integridad de fotos (siempre, antes del PDF)...")
    subprocess.run([sys.executable, str(base / "reparar_fotos_contaminadas.py")], check=False)

    # 6) Regenerar PDF completo con resumen de cambios del día
    resumen = {
        "nuevos":   nuevos,
        "vendidos": vendidos,
        "cambios":  cambios,
        "cambios_hoy": cambios_hoy_acum,   # historial acumulado del día
        "n_actualizacion": n_actualizacion,
        "totales": {
            "actual":      len(actuales),
            "disponibles": sum(1 for c in actuales if c["estado"] == "Disponible"),
            "no_disp":     sum(1 for c in actuales if c["estado"] != "Disponible"),
        }
    }
    crear_pdf(actuales, resumen)

    # Copiar PDF a la carpeta de ejecutables
    ejecutables_dir = Path.home() / "Desktop" / "ejecutable redes"
    if ejecutables_dir.exists():
        shutil.copy2(PDF_PATH, ejecutables_dir / "catalogo_automoviles_rueda.pdf")
        print(f"  PDF copiado -> ejecutable redes/catalogo_automoviles_rueda.pdf")

    # 7) Regenerar todos los prompts y archivos de contenido
    if hay_cambios:
        print("\n  Regenerando prompts y textos...")
        subprocess.run([sys.executable, str(base / "generar_prompts_gemini.py")], check=False)
        subprocess.run([sys.executable, str(base / "generar_textos_redes.py")],   check=False)
        subprocess.run([sys.executable, str(base / "generar_prompts_video.py")],  check=False)

    # Siempre regenerar archivos Freepik Spaces (actualizados con cada cambio de catálogo)
    print("  Actualizando archivos Freepik Spaces...")
    subprocess.run([sys.executable, str(base / "generar_spaces_freepik.py")], check=False)

    # 7b) Limpiar carpetas huérfanas (siempre — evita mezcla de fotos tras cambio de números)
    import shutil as _shutil
    _archivo = PHOTOS_DIR / "_archivo_carpetas_viejas"
    _archivo.mkdir(exist_ok=True)
    _valid = set()
    for _c in actuales:
        _n  = _c["n"]; _p = _c.get("precio", "")
        _nm = f"{_n:02d} - {_c['modelo']} - {_p}€" if _p else f"{_n:02d} - {_c['modelo']}"
        # Solo añadir la versión correcta según el estado (no ambas)
        if _c.get("estado", "Disponible") == "Disponible":
            _valid.add(_nm)               # disponible → carpeta sin RESERVADO
        else:
            _valid.add(_nm + " · RESERVADO")  # reservado → carpeta con RESERVADO
    _archivadas = 0
    for _d in list(PHOTOS_DIR.iterdir()):
        if _d.is_dir() and not _d.name.startswith("_") and _d.name not in _valid:
            _destino = _archivo / _d.name
            if _destino.exists():
                _destino = _archivo / f"{_d.name} ({hoy_str})"
            _shutil.move(str(_d), str(_destino))
            _archivadas += 1
    if _archivadas:
        print(f"  🗂  {_archivadas} carpeta(s) huérfana(s) archivadas automáticamente")

    # 8) Escribir informe
    informe_txt = generar_informe(
        nuevos, vendidos, cambios, anteriores, actuales,
        cambios_hoy_acum=cambios_hoy_acum,
        n_actualizacion=n_actualizacion
    )
    INFORME.write_text(informe_txt, encoding="utf-8")
    print()
    print(informe_txt)
    print(f"\n  Informe guardado en: {INFORME}")

    print()

if __name__ == "__main__":
    asyncio.run(main())
