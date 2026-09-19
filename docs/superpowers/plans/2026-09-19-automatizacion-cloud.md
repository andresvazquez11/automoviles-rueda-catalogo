# Automatización Cloud del Catálogo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the existing daily catalog-update pipeline (scrape → photos → build web → PDF) automatically in GitHub Actions, twice a day (10:00 and 16:00 Spain time, Mon-Sat), with zero dependency on Andrés's computer, and an email either way (success summary + light PDF, or failure alert).

**Architecture:** A new GitHub Actions workflow runs the *same* Python scripts that already run locally via the `.command` file, on GitHub's own servers, on a DST-safe schedule. Two small, targeted code changes make those scripts portable to a CI runner (they currently hardcode `~/Desktop/...`) and add a lightweight PDF variant for email. Photos are cached between runs via `actions/cache`; the repo is small enough for this now that the historical junk folder has been deleted.

**Tech Stack:** GitHub Actions (schedule + `actions/cache` + `dawidd6/action-send-mail`), Python 3 (existing scripts, unchanged behavior on Andrés's Mac), Playwright headless Chromium.

**Spec:** `docs/superpowers/specs/2026-09-19-automatizacion-cloud-design.md`

---

## Already done (no task needed)

These were completed directly during design/investigation — verify they're still true, but no implementation work needed:
- `fotos/_archivo_carpetas_viejas/` deleted (was 4.8 GB of stale sold-car folders). `fotos/` is now ~550 MB.
- GitHub Actions secret `GOOGLE_API_KEY` set (reused from `config.txt`).
- GitHub Actions secret `GMAIL_APP_PASSWORD` set.
- Repo's default Actions workflow permission changed from "read" to "write" (`gh api repos/andresvazquez11/automoviles-rueda-catalogo/actions/permissions/workflow` → `default_workflow_permissions: write`) — required for the workflow's automatic token to `git push`.

## Reference

- Project root: `~/Desktop/catalogo_automoviles_rueda`
- Repo: `andresvazquez11/automoviles-rueda-catalogo`, branch `main`
- No automated test suite — verification is "run it, read the output, check the generated files," same as every other plan in this project.
- The existing `fotos/_archivo/` auto-archiving (in `actualizar_catalogo.py`, near the end of `main()`) already moves photo folders of sold/retired cars out of the way — **no new Python cleanup logic is needed for that**. The only new piece is making sure the *cloud* cache doesn't keep growing forever by discarding that archive at the end of each cloud run (Task 5).

---

### Task 1: Make the scripts portable to a CI runner

**Files:**
- Modify: `catalogo_rueda_v2.py:30`
- Modify: `descargar_fotos_galeria.py:14`
- Modify: `actualizar_catalogo.py:550`
- Modify: `actualizar_catalogo.py:602`

These four lines compute the project's root directory as `Path.home() / "Desktop" / "catalogo_automoviles_rueda"`. On Andrés's Mac that happens to equal the repo's real location, so it works today — but on a GitHub Actions runner, `Path.home()` is something like `/home/runner` with no `Desktop` folder at all, so every one of these would silently point at an empty, disconnected directory instead of the actual checked-out repo. `generar_web.py` already does this correctly with `Path(__file__).parent` — apply the same fix here.

- [ ] **Step 1: Fix `catalogo_rueda_v2.py`**

Change:
```python
OUTPUT_DIR = Path.home() / "Desktop" / "catalogo_automoviles_rueda"
```
to:
```python
OUTPUT_DIR = Path(__file__).parent
```

- [ ] **Step 2: Fix `descargar_fotos_galeria.py`**

Change:
```python
BASE       = Path.home() / "Desktop" / "catalogo_automoviles_rueda"
```
to:
```python
BASE       = Path(__file__).parent
```

- [ ] **Step 3: Fix `actualizar_catalogo.py` (two occurrences)**

Change (around line 550, inside the MotorFlash-integration block):
```python
        _base = Path.home() / "Desktop" / "catalogo_automoviles_rueda"
```
to:
```python
        _base = Path(__file__).parent
```

Change (around line 602, right before the photo-integrity check):
```python
    base = Path.home() / "Desktop" / "catalogo_automoviles_rueda"
```
to:
```python
    base = Path(__file__).parent
```

(Leave `actualizar_catalogo.py:622`'s `Path.home() / "Desktop" / "ejecutable redes"` — that one already has an `if ejecutables_dir.exists():` guard, so on a CI runner where that folder genuinely doesn't exist, it's skipped harmlessly. It refers to a folder outside this repo that only makes sense on Andrés's own Mac.)

- [ ] **Step 4: Verify nothing broke locally**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
python3 -c "
import catalogo_rueda_v2 as c
print(c.OUTPUT_DIR)
assert str(c.OUTPUT_DIR) == '/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda'
print('OK')
"
```
Expected: prints the path and `OK` — confirms the new relative computation lands on the exact same real directory as before, so nothing changes for Andrés's local runs.

- [ ] **Step 5: Commit**

```bash
git add catalogo_rueda_v2.py descargar_fotos_galeria.py actualizar_catalogo.py
git commit -m "Use script-relative paths instead of hardcoded ~/Desktop so scripts run in CI"
```

---

### Task 2: Add a lightweight PDF variant

**Files:**
- Modify: `catalogo_rueda_v2.py`

Today's PDF embeds every photo at full camera resolution (4000×3000) even though it's only ever displayed at postage-stamp size on the page — that's most of its 148 MB. Add a `liviano` (lightweight) mode: resize the main photo down to a sane resolution and skip the two rows of thumbnails entirely. This doesn't touch the existing full-quality path at all.

- [ ] **Step 1: Add the lightweight-PDF output path constant**

Find (near the top of the file):
```python
PDF_PATH   = OUTPUT_DIR / "catalogo_automoviles_rueda.pdf"
```
Change to:
```python
PDF_PATH   = OUTPUT_DIR / "catalogo_automoviles_rueda.pdf"
PDF_PATH_LIVIANO = OUTPUT_DIR / "catalogo_automoviles_rueda_liviano.pdf"
```

- [ ] **Step 2: Add the `liviano` parameter to `crear_pdf`**

Change:
```python
def crear_pdf(cars: list[dict], resumen: dict = None):
```
to:
```python
def crear_pdf(cars: list[dict], resumen: dict = None, liviano: bool = False):
    """`liviano=True` genera una versión mucho más chica para mandar por
    correo: redimensiona la foto principal al tamaño real en que se ve en
    la página (en vez de la resolución de cámara) y omite las miniaturas.
    Sin esto, cada llamada de generación completa (148 MB) sigue igual."""
```

- [ ] **Step 3: Resize the main photo when `liviano=True`**

Find:
```python
        if foto_path.exists():
            try:
                pi        = Image.open(foto_path).convert("RGB")
                img_w, img_h = pi.size
                # Altura proporcional: mantiene ratio sin deformar
                main_h    = MAIN_W * (img_h / img_w)
                buf = BytesIO()
                pi.save(buf, format="JPEG", quality=88)
```
Change to:
```python
        if foto_path.exists():
            try:
                pi        = Image.open(foto_path).convert("RGB")
                if liviano:
                    pi.thumbnail((1000, 1000))
                img_w, img_h = pi.size
                # Altura proporcional: mantiene ratio sin deformar
                main_h    = MAIN_W * (img_h / img_w)
                buf = BytesIO()
                pi.save(buf, format="JPEG", quality=82 if liviano else 88)
```

- [ ] **Step 4: Skip the thumbnail rows when `liviano=True`**

Find:
```python
        if len(todas_fotos) > 1:
            miniaturas = todas_fotos[1:]   # excluir foto_01 (ya mostrada grande)
```
Change to:
```python
        if len(todas_fotos) > 1 and not liviano:
            miniaturas = todas_fotos[1:]   # excluir foto_01 (ya mostrada grande)
```

- [ ] **Step 5: Write to the right output path**

Find:
```python
    pdf.output(str(PDF_PATH))
    print(f"  PDF guardado: {PDF_PATH}")
```
Change to:
```python
    ruta_salida = PDF_PATH_LIVIANO if liviano else PDF_PATH
    pdf.output(str(ruta_salida))
    print(f"  PDF guardado: {ruta_salida}")
```

- [ ] **Step 6: Verify both variants generate correctly**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
python3 -c "
import json
from catalogo_rueda_v2 import crear_pdf
cars = json.loads(open('datos_coches.json', encoding='utf-8').read())
crear_pdf(cars[:3], liviano=True)
"
ls -la catalogo_automoviles_rueda_liviano.pdf
```
Expected: the command prints `PDF guardado: .../catalogo_automoviles_rueda_liviano.pdf`, and `ls` shows a file — for just 3 cars it should be well under 1 MB (full run with all ~56 cars should land in the 8-14 MB range estimated in the design spec).

Clean up the test file:
```bash
rm -f catalogo_automoviles_rueda_liviano.pdf
```

- [ ] **Step 7: Commit**

```bash
git add catalogo_rueda_v2.py
git commit -m "Add lightweight PDF variant (resized photo, no thumbnails) for email"
```

---

### Task 3: Generate the lightweight PDF and a machine-readable daily summary

**Files:**
- Modify: `actualizar_catalogo.py`

`actualizar_catalogo.py` already builds a `resumen` dict (new/sold/price-change counts) and calls `crear_pdf(actuales, resumen)` once for the full PDF. Add a second call for the lightweight version, and save that same `resumen` to a small JSON file the GitHub Actions workflow can read to write the email body — no need to recompute or re-parse anything.

- [ ] **Step 1: Add the lightweight PDF call and the summary file**

Find:
```python
    crear_pdf(actuales, resumen)

    # Copiar PDF a la carpeta de ejecutables
```
Change to:
```python
    crear_pdf(actuales, resumen)
    crear_pdf(actuales, resumen, liviano=True)

    resumen_path = Path(__file__).parent / "resumen_hoy.json"
    resumen_serializable = {
        "nuevos":   [{"n": c["n"], "modelo": c["modelo"]} for c in nuevos],
        "vendidos": [{"n": c["n"], "modelo": c["modelo"]} for c in vendidos],
        "totales":  resumen["totales"],
    }
    resumen_path.write_text(
        json.dumps(resumen_serializable, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Copiar PDF a la carpeta de ejecutables
```

(`resumen["totales"]` already only has plain numbers — see the dict built a few lines above this call — so it's already JSON-safe as-is. `nuevos`/`vendidos` are lists of full car dicts; trimming to just `n`+`modelo` keeps `resumen_hoy.json` small and avoids serializing anything sensitive/irrelevant to an email summary.)

- [ ] **Step 2: Verify by inspection**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
grep -n "crear_pdf(actuales, resumen, liviano=True)" actualizar_catalogo.py
grep -n "resumen_hoy.json" actualizar_catalogo.py
```
Expected: both greps find a match.

(This function only runs as part of the full `actualizar_catalogo.py` scrape — it's not practical to test standalone without hitting the live Das WeltAuto site. Task 6's end-to-end cloud run is the real verification for this step.)

- [ ] **Step 3: Commit**

```bash
git add actualizar_catalogo.py
git commit -m "Generate lightweight PDF and resumen_hoy.json alongside the full daily update"
```

---

### Task 4: Add `requirements.txt` for the CI runner

**Files:**
- Create: `requirements.txt`

The Mac has these packages installed globally already; a fresh GitHub Actions runner starts with nothing, so pin the same versions explicitly.

- [ ] **Step 1: Create the file**

```
playwright==1.59.0
pillow==11.3.0
requests==2.32.5
fpdf2==2.8.4
google-genai==1.47.0
```

- [ ] **Step 2: Commit**

```bash
git add requirements.txt
git commit -m "Add requirements.txt pinning the versions already used locally"
```

---

### Task 5: The GitHub Actions workflow

**Files:**
- Create: `.github/workflows/actualizar-catalogo.yml`

Two jobs: a cheap `check-hora` job that decides whether it's actually 10:00 or 16:00 in Madrid right now (since cron in GitHub Actions is fixed UTC and doesn't shift for daylight saving), and the real `actualizar` job that only runs when that check passes (or when someone manually clicks "Run workflow").

- [ ] **Step 1: Create the workflow file**

```yaml
name: Actualizar catálogo

on:
  schedule:
    - cron: '0 8 * * 1-6'   # 10:00 hora España en verano (CEST, UTC+2)
    - cron: '0 9 * * 1-6'   # 10:00 hora España en invierno (CET, UTC+1)
    - cron: '0 14 * * 1-6'  # 16:00 hora España en verano (CEST, UTC+2)
    - cron: '0 15 * * 1-6'  # 16:00 hora España en invierno (CET, UTC+1)
  workflow_dispatch: {}

jobs:
  check-hora:
    runs-on: ubuntu-latest
    outputs:
      correr: ${{ steps.hora.outputs.correr }}
    steps:
      - id: hora
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            echo "Disparo manual — se ejecuta sin importar la hora."
            echo "correr=si" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          HORA_MADRID=$(TZ=Europe/Madrid date +%H)
          echo "Hora actual en Madrid: ${HORA_MADRID}h"
          if [ "$HORA_MADRID" = "10" ] || [ "$HORA_MADRID" = "16" ]; then
            echo "correr=si" >> "$GITHUB_OUTPUT"
          else
            echo "No es una de las horas objetivo (10h/16h) — se omite esta corrida."
            echo "correr=no" >> "$GITHUB_OUTPUT"
          fi

  actualizar:
    needs: check-hora
    if: needs.check-hora.outputs.correr == 'si'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Instalar dependencias
        run: |
          pip install -r requirements.txt
          playwright install --with-deps chromium

      - name: Restaurar caché de fotos
        uses: actions/cache/restore@v4
        with:
          path: fotos
          key: fotos-${{ github.run_id }}
          restore-keys: |
            fotos-

      - name: Preparar config.txt
        run: echo "GOOGLE_API_KEY=${{ secrets.GOOGLE_API_KEY }}" > config.txt

      - name: Revisar cambios en Das WeltAuto y regenerar PDFs
        run: python3 actualizar_catalogo.py

      - name: Descargar fotos nuevas
        run: python3 descargar_fotos_galeria.py

      - name: Descartar fotos archivadas (coches vendidos) antes de cachear
        run: rm -rf fotos/_archivo

      - name: Generar la web
        run: python3 generar_web.py

      - name: Guardar caché de fotos actualizado
        if: always()
        uses: actions/cache/save@v4
        with:
          path: fotos
          key: fotos-${{ github.run_id }}

      - name: Configurar identidad de git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

      - name: Commitear y subir cambios
        run: |
          git add index.html web_fotos/ coches/ assets/ alejandro/ \
                  datos_coches.json historial_precios.json coches_lista.json \
                  traducciones_cache.json
          git commit -m "Actualización automática del catálogo $(date '+%d/%m/%Y %H:%M')" || echo "Sin cambios que subir"
          git push origin main

      - name: Preparar resumen para el correo
        id: resumen
        if: success()
        run: |
          python3 - <<'PY'
          import json, os
          from pathlib import Path
          ruta = Path("resumen_hoy.json")
          if ruta.exists():
              r = json.loads(ruta.read_text(encoding="utf-8"))
              t = r.get("totales", {})
              cuerpo = (
                  f"Coches disponibles: {t.get('disponibles', '?')}\n"
                  f"Reservados: {t.get('no_disp', '?')}\n"
                  f"Nuevos hoy: {len(r.get('nuevos', []))}\n"
                  f"Vendidos hoy: {len(r.get('vendidos', []))}\n"
              )
          else:
              cuerpo = "(no se encontró resumen_hoy.json — revisar el log de esta corrida)"
          with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
              f.write("cuerpo<<EOF\n")
              f.write(cuerpo + "\n")
              f.write("EOF\n")
          PY

      - name: Calcular fecha para el asunto del correo
        id: fecha
        if: success()
        run: echo "fecha=$(TZ=Europe/Madrid date '+%d/%m/%Y %H:%M')" >> "$GITHUB_OUTPUT"

      - name: Enviar correo de éxito
        if: success()
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.gmail.com
          server_port: 465
          username: andrescovidelpi@gmail.com
          password: ${{ secrets.GMAIL_APP_PASSWORD }}
          from: Catálogo Automóviles Rueda <andrescovidelpi@gmail.com>
          to: andrescovidelpi@gmail.com
          subject: "✅ Catálogo actualizado — ${{ steps.fecha.outputs.fecha }}"
          body: ${{ steps.resumen.outputs.cuerpo }}
          attachments: catalogo_automoviles_rueda_liviano.pdf

      - name: Enviar correo de error
        if: failure()
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.gmail.com
          server_port: 465
          username: andrescovidelpi@gmail.com
          password: ${{ secrets.GMAIL_APP_PASSWORD }}
          from: Catálogo Automóviles Rueda <andrescovidelpi@gmail.com>
          to: andrescovidelpi@gmail.com
          subject: "⚠️ Falló la actualización del catálogo"
          body: |
            Algo falló durante la actualización automática de hoy.

            Revisá el detalle acá:
            ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

- [ ] **Step 2: Create the `.github/workflows` directory and verify the YAML is well-formed**

```bash
mkdir -p ~/Desktop/catalogo_automoviles_rueda/.github/workflows
```
(Write the file from Steps 1-2 above into `.github/workflows/actualizar-catalogo.yml`.)

```bash
cd ~/Desktop/catalogo_automoviles_rueda
python3 -c "import yaml, sys; yaml.safe_load(open('.github/workflows/actualizar-catalogo.yml')); print('YAML válido')"
```
Expected: `YAML válido`. (If `pyyaml` isn't installed: `pip install pyyaml` first — it's only needed for this one-off syntax check, not a project dependency.)

- [ ] **Step 3: Commit and push**

```bash
git add .github/workflows/actualizar-catalogo.yml
git commit -m "Add scheduled GitHub Actions workflow to run the daily update in the cloud"
git push origin main
```

(This push is required before Task 6 — `workflow_dispatch` only becomes available on GitHub once the workflow file exists on the default branch.)

---

### Task 6: End-to-end test run before trusting the schedule

**Files:** none (verification only)

- [ ] **Step 1: Trigger it manually**

```bash
gh workflow run "Actualizar catálogo" --repo andresvazquez11/automoviles-rueda-catalogo
```

- [ ] **Step 2: Watch it run**

```bash
gh run watch --repo andresvazquez11/automoviles-rueda-catalogo
```
Expected: both jobs (`check-hora`, `actualizar`) complete with status `success`. If `actualizar` fails, open the failing step's log (`gh run view --repo andresvazquez11/automoviles-rueda-catalogo --log-failed`) — this is exactly the scenario the design spec flagged as the real unknown (whether Das WeltAuto treats GitHub's cloud IP differently than a home connection). If scraping itself fails here, that needs a follow-up conversation with Andrés — don't guess at a workaround.

- [ ] **Step 3: Confirm the email arrived**

Check `andrescovidelpi@gmail.com` for a message with subject starting `✅ Catálogo actualizado —`, a short summary in the body, and `catalogo_automoviles_rueda_liviano.pdf` attached. Open the PDF — confirm it has one page per car with one photo each (no thumbnail grid) and opens fine.

- [ ] **Step 4: Confirm the site actually updated**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
git fetch origin main
git log origin/main --oneline -3
```
Expected: the newest commit is `Actualización automática del catálogo <fecha> <hora>` from `github-actions[bot]`.

- [ ] **Step 5: Confirm the cache was saved for next time**

```bash
gh cache list --repo andresvazquez11/automoviles-rueda-catalogo
```
Expected: a `fotos-<run-id>` entry from this run.

- [ ] **Step 6: Tell Andrés it's live**

Once all of the above checks out, the schedule (10:00 and 16:00, Mon-Sat, Madrid time) is already active from the moment the workflow file was pushed in Task 5 — there's nothing further to "turn on." Let Andrés know the next scheduled run will happen automatically, and that he can keep using the `.command` file manually any time he wants an immediate update without waiting.

---

## Self-Review Notes

- **Spec coverage:** cloud schedule with DST handling (Task 5) · fotos cache between runs (Task 5, `actions/cache/restore` + `/save`) · orphaned-car photo cleanup already existed, just made cloud-cache-safe by discarding `fotos/_archivo` each run (Task 5) · lightweight PDF for email, full PDF untouched (Task 2, 3) · success/failure emails (Task 5) · secrets and repo write permission (done during design, listed under "Already done") · test-before-trusting rollout (Task 6) — all covered.
- **Placeholder scan:** none found — every step has literal code/commands. The one thing intentionally left open is Task 6 Step 2's "if scraping fails here, that needs a follow-up conversation" — that's a genuine unknown flagged in the spec itself (not something a plan can pre-solve), not a placeholder.
- **Type consistency:** `PDF_PATH_LIVIANO` (Task 2) matches the filename referenced in the workflow's `attachments:` field (Task 5) and Task 6's verification step. `resumen_hoy.json`'s shape (`nuevos`, `vendidos` as lists of `{n, modelo}`, `totales` as the existing dict) matches exactly what the workflow's "Preparar resumen para el correo" step reads (Task 3 vs Task 5).
