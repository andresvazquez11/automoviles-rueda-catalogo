"""
Descargar galería completa de fotos exteriores por coche
=========================================================
- Migra las fotos planas existentes (coche_NN.jpg) a subcarpetas (coche_NN/foto_01.jpg)
- Visita la ficha de cada coche en Das WeltAuto
- Descarga hasta 8 fotos exteriores por coche
- Guarda todo en fotos/coche_NN/foto_01.jpg … foto_08.jpg
"""

import asyncio, json, requests
from pathlib import Path
from playwright.async_api import async_playwright

BASE       = Path(__file__).parent
CACHE      = BASE / "datos_coches.json"
PHOTOS_DIR = BASE / "fotos"
MAX_FOTOS  = 8   # máximo fotos exteriores por coche

def _nombre(car: dict) -> str:
    precio = car.get("precio", "")
    return f"{car['n']:02d} - {car['modelo']} - {precio}€" if precio else f"{car['n']:02d} - {car['modelo']}"

def migrar_foto_plana(car: dict) -> Path:
    """Migra a la estructura final 'NN - Modelo - Precio€/'. Devuelve la carpeta."""
    n             = car["n"]
    carpeta_nueva = PHOTOS_DIR / _nombre(car)

    # Migrar solo si MISMO modelo (evita traer fotos de otro coche con mismo número)
    prefijo_modelo = f"{n:02d} - {car['modelo']}"
    if not carpeta_nueva.exists():
        for candidata in sorted(PHOTOS_DIR.iterdir()):
            if (candidata.is_dir()
                    and candidata.name.startswith(prefijo_modelo)
                    and candidata != carpeta_nueva):
                candidata.rename(carpeta_nueva)
                print(f"  [{n:02d}] Renombrada → {carpeta_nueva.name}/")
                break
        for viejo in [f"Coche {n:02d}", f"coche_{n:02d}"]:
            vieja = PHOTOS_DIR / viejo
            if vieja.exists():
                vieja.rename(carpeta_nueva)
                break

    carpeta_nueva.mkdir(exist_ok=True)

    foto_plana = PHOTOS_DIR / f"coche_{n:02d}.jpg"
    if foto_plana.exists() and not (carpeta_nueva / "foto_01.jpg").exists():
        foto_plana.rename(carpeta_nueva / "foto_01.jpg")

    return carpeta_nueva

async def descargar_galeria(page, car: dict) -> int:
    """Visita la ficha y descarga las fotos que faltan. Devuelve nº de fotos en carpeta."""
    n        = car["n"]
    url      = car.get("url")
    foto_dir = PHOTOS_DIR / _nombre(car)
    foto_dir.mkdir(exist_ok=True)

    # ¿Cuántas fotos tiene ya?
    existentes = sorted(foto_dir.glob("foto_*.jpg"))
    if len(existentes) >= MAX_FOTOS:
        print(f"  [{n:02d}] Ya tiene {len(existentes)} fotos — omitido")
        return len(existentes)

    if not url:
        print(f"  [{n:02d}] Sin URL — omitido")
        return len(existentes)

    try:
        await page.goto("https://www.dasweltauto.es" + url,
                        wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(1500)

        # Cerrar cookies si aparecen
        await page.evaluate("""
            const btns = document.querySelectorAll('button');
            const btn  = Array.from(btns).find(b =>
                b.textContent.includes('Rechazar') || b.textContent.includes('Aceptar'));
            if (btn) btn.click();
        """)
        await page.wait_for_timeout(400)

        # Recopilar todas las URLs de la galería
        gallery_urls = await page.evaluate("""
            () => {
                const seen = new Set();
                const urls = [];
                document.querySelectorAll('img').forEach(img => {
                    ['src','data-src','data-lazy','data-original'].forEach(attr => {
                        const s = img.getAttribute(attr) || '';
                        if (s.includes('motorflash') && s.length > 50 && !seen.has(s)) {
                            seen.add(s);
                            urls.push(s);
                        }
                    });
                });
                return urls;
            }
        """)

        # Descargar las que faltan
        urls_existentes = {f.read_bytes() for f in existentes}  # evitar duplicados por contenido
        descargadas = len(existentes)

        for src in gallery_urls:
            if descargadas >= MAX_FOTOS:
                break
            try:
                r = requests.get(src, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200 and len(r.content) > 20000:
                    # Evitar duplicado por contenido
                    if r.content in urls_existentes:
                        continue
                    idx = descargadas + 1
                    destino = foto_dir / f"foto_{idx:02d}.jpg"
                    destino.write_bytes(r.content)
                    urls_existentes.add(r.content)
                    descargadas += 1
            except Exception:
                pass

        total = len(list(foto_dir.glob("foto_*.jpg")))
        nuevas = total - len(existentes)
        if nuevas > 0:
            print(f"  [{n:02d}] {car['modelo']} {car['version'][:35]}")
            print(f"        +{nuevas} fotos nuevas → total {total} en coche_{n:02d}/")
        else:
            print(f"  [{n:02d}] {car['modelo'][:25]} — sin fotos nuevas ({total} ya existían)")
        return total

    except Exception as e:
        print(f"  [{n:02d}] ⚠️  Error: {e}")
        return len(existentes)

async def main():
    if not CACHE.exists():
        print("❌  No se encontró datos_coches.json. Ejecuta primero el catálogo completo.")
        return

    all_cars = json.loads(CACHE.read_text(encoding="utf-8"))
    # SOLO coches "Disponible": un coche "No disponible" ya no existe como
    # anuncio en DWA, y su URL puede haber sido RECICLADA por DWA para OTRO
    # coche. Si lo procesáramos aquí, una carpeta vacía/recién renombrada
    # acabaría descargando la galería de ESE OTRO coche y contaminando las
    # fotos. Para "No disponible" las fotos locales existentes son la fuente
    # de verdad y no se tocan.
    cars = [c for c in all_cars
            if c.get("url", "").strip()
            and c.get("estado", "").lower() == "disponible"]
    total = len(cars)

    print()
    print("=" * 60)
    print("  AUTOMÓVILES RUEDA — Descarga galería de fotos")
    print(f"  {total} disponibles con URL · máximo {MAX_FOTOS} fotos/coche")
    print("=" * 60)

    # 1) Migrar fotos planas existentes (sin conexión)
    print("\n  Paso 1/2 — Migrando fotos existentes a subcarpetas...")
    for car in cars:
        migrar_foto_plana(car)

    # 2) Descargar fotos adicionales desde Das WeltAuto
    print("\n  Paso 2/2 — Descargando ángulos adicionales de Das WeltAuto...")
    print("  (esto puede tardar varios minutos)\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 Chrome/120 Safari/537.36")
        )
        page = await ctx.new_page()

        totales = []
        for car in cars:
            n_fotos = await descargar_galeria(page, car)
            totales.append(n_fotos)
            car["fotos"] = sorted(
                str(f) for f in (PHOTOS_DIR / _nombre(car)).glob("foto_*.jpg")
            )

        await browser.close()

    # 3) Guardar JSON — TODOS los coches (disponibles + reservados)
    # solo actualizamos las rutas de fotos de los disponibles procesados
    CACHE.write_text(json.dumps(all_cars, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4) Generar prompt_gemini.txt dentro de cada carpeta Coche NN/
    print("\n  Generando prompts Gemini en cada carpeta...")
    import subprocess, sys
    subprocess.run([sys.executable, str(BASE / "generar_prompts_gemini.py")], check=False)

    # 5) Resumen
    print()
    print("=" * 60)
    print(f"  ✅  ¡Completado!")
    print(f"  Coches procesados: {total}")
    print(f"  Total fotos: {sum(totales)}")
    print(f"  Media por coche: {sum(totales)/total:.1f} fotos")
    print(f"  Cada carpeta tiene: fotos + prompt_gemini.txt")
    print(f"  Carpeta: catalogo_automoviles_rueda/fotos/")
    print("=" * 60)
    print()

if __name__ == "__main__":
    asyncio.run(main())
