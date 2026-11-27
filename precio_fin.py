"""Precio financiando (variante B): precio de contado MENOS la mayor bonificación de financiación disponible para ese coche.
 · Fuente 1: ejemplo oficial de Das WeltAuto / Volkswagen Bank que ya guardamos en car['financiacion']['ejemplo'] («Bonificación de X €»).
 · Fuente 2: campañas VWFS VO vigentes (las mismas reglas que usa la calculadora de la ficha, assets/calculadora.js → cv2GetRules): SEAT GAMA 750 (VS ≤24 m) / 500 (VO 25–60 m) / 300 (VU >60 m),
   CUPRA GAMA 1.200 €, Otras marcas 200/400/500 € según importe. Las de activación manual (DEMOS+REMA y SALONES Arona) entran solo si están en campanas_manuales.json, que genera el proceso privado a partir de la procedencia del coche en el stock.
 Se aplica la MAYOR. Si no hay bonificación (o el coche no llega al capital mínimo a financiar) → None: la web y el folleto enseñan UN SOLO precio (el de contado).
Fuentes de las reglas (comprobadas el 27-nov-2026 con los PDF de financiacion/): «Campaña comercial SEAT VO · Noviembre 2026» págs. 2, 8, 10, 15-17 (GAMA: VS 0-24 m 750 €, VO 25-60 m 500 €, VU >60 m 300 € LINEAL 36-48 m crédito mín. 15.000 €;
 Otras Marcas LINEAL 48-120 m: Entry 200 € desde 10.000, Premium 400 € desde 15.000, TOP 500 € desde 20.000; TIN 8,99 %; comisión de apertura 2,99 %) y «Campaña comercial CUPRA VO · Noviembre 2026» págs. 2, 4 (GAMA solo VS-VO 0-5 años:
 FLEX 1.200 € crédito mín. 16.500 € 36-60 m; LINEAL 1.000 € 48-71 m / 1.200 € 72-120 m crédito mín. 13.500 €).
Los números de cuota y TAE solo se muestran cuando la bonificación aplicada es la del ejemplo oficial (son los de ese ejemplo)."""
import json
import re
from datetime import date
from pathlib import Path

FINANCIERA = "Volkswagen Bank GmbH S.E."
_MANUAL = None


def _manual():
    """campanas_manuales.json (lo genera el proceso privado con la procedencia del stock): ids con DEMOS+REMA e interruptor SALONES Arona."""
    global _MANUAL
    if _MANUAL is None:
        f = Path(__file__).resolve().parent / 'campanas_manuales.json'
        try:
            _MANUAL = json.loads(f.read_text()) if f.exists() else {}
        except Exception:
            _MANUAL = {}
    return _MANUAL


def _id(car):
    return (car.get('url') or '').rstrip('/').split('/')[-1]


def _eur_txt(t):
    return float(t.replace('.', '').replace(',', '.'))


def _precio(car):
    return int(re.sub(r'[^\d]', '', str(car.get('precio', '')).split(',')[0]) or 0)


def _antig_meses(fecha):
    m = re.match(r'(\d{1,2})/(\d{4})', str(fecha or ''))
    if not m:
        return None
    hoy = date.today()
    return max(0, (hoy.year - int(m.group(2))) * 12 + (hoy.month - int(m.group(1))))


def _oficial(car):
    f = car.get('financiacion') or {}
    e = f.get('ejemplo') or ''
    b = re.search(r'Bonificaci[oó]n de\s*([\d.]+,\d\d)', e)
    cm = re.search(r'capital m[ií]nimo de\s*([\d.]+,\d\d)', e)
    pm = re.search(r'permanencia m[ií]nima[^.]*?(\d+)\s*meses', e)
    return dict(bonif=_eur_txt(b.group(1)) if b else 0.0, cap_min=_eur_txt(cm.group(1)) if cm else None, perm=int(pm.group(1)) if pm else None,
                tin=f.get('tin'), tae=f.get('tae'), cuota=f.get('cuota'), meses=f.get('meses'))


def _campana(car, precio, ant):
    """Mejor bonificación de nuestras campañas para este coche → (bonif, capital_min, producto, plazos, tin) o None."""
    marca = (str(car.get('modelo', '')).split() or [''])[0].upper()
    if ant is None:
        return None   # sin fecha de matriculación no se puede saber la campaña
    cat = 'VS' if ant <= 24 else 'VO' if ant <= 60 else 'VU'
    man = _manual()
    cands = []   # (bonificación, crédito mínimo, producto, plazos, TIN)
    if marca == 'SEAT':
        if cat == 'VU':
            cands.append((300, 15000, 'LINEAL', '36-48 meses', '8.99'))
        elif cat == 'VO':
            cands.append((500, 10000, 'FLEX', '36-60 meses', '8.99'))
        else:
            cands.append((750, 10000, 'FLEX', '36-60 meses', '8.99'))
        # Campaña especial SEAT VS DEMOS + REMA (Noviembre 2026, págs. 3 y 7): solo VS (≤24 m), la procedencia (Demo/REMA/KM 0) la sabemos por el stock
        if cat == 'VS' and _id(car) in set(man.get('demos_rema') or []):
            cands.append((950, 10000, 'FLEX', '36-60 meses', '7.99'))
        # Campaña SALONES VO (Arona), págs. 4 y 9: solo los ids que lista campanas_manuales.json (según el modo elegido en campanas_config.json: apagado, buyback o todos)
        if _id(car) in set(man.get('salones_arona') or []) and 'arona' in str(car.get('modelo', '')).lower() and cat in ('VS', 'VO'):
            if cat == 'VS':
                cands += [(2000, 13500, 'FLEX', '60 meses', '8.99'), (2000, 13500, 'LINEAL', '84-120 meses', '8.99')]
            else:
                cands += [(1500, 13500, 'FLEX', '60 meses', '8.99'), (2000, 12000, 'LINEAL', '84-120 meses', '8.99')]
    elif marca == 'CUPRA':
        # Campaña CUPRA VO Noviembre 2026 (pág. 4): GAMA «VS-VO (0-5 años)»: no vale para coches de más de 60 meses
        if cat != 'VU':
            cands += [(1200, 16500, 'FLEX', '36-60 meses', '8.99'), (1200, 13500, 'LINEAL', '72-120 meses', '8.99')]
    else:
        for b, mn in ((500, 20000), (400, 15000), (200, 10000)):
            if precio >= mn:
                cands.append((b, mn, 'LINEAL', '48-120 meses', '8.99'))
                break
    ok = [c for c in cands if precio - c[0] >= c[1]]
    if not ok:
        return None
    ok.sort(key=lambda c: (-c[0], 0 if c[2] == 'FLEX' else 1))
    b, mn, prod, plz, tin = ok[0]
    return dict(bonif=float(b), cap_min=float(mn), producto=prod, plazos=plz, tin=tin)


def calcular(car):
    """→ dict {pf, contado, bonif, cap_min, perm, tin, tae, cuota, meses, origen, financiera} o None si no hay descuento por financiar."""
    if car.get('estado') in ('Retirado',):
        return None
    precio = _precio(car)
    if not precio:
        return None
    ant = _antig_meses(car.get('fecha'))
    of, ca = _oficial(car), _campana(car, precio, ant)
    b_of = of['bonif'] if of['bonif'] and (of['cap_min'] is None or precio - of['bonif'] >= of['cap_min']) else 0.0
    b_ca = ca['bonif'] if ca else 0.0
    if max(b_of, b_ca) <= 0:
        return None
    if b_of >= b_ca:   # gana (o empata) el ejemplo oficial: sus condiciones y su cuota/TAE son las válidas
        return dict(pf=precio - int(b_of), contado=precio, bonif=int(b_of), cap_min=int(of['cap_min'] or 0) or None, perm=of['perm'] or 36, tin=of['tin'], tae=of['tae'],
                    cuota=of['cuota'], meses=of['meses'], origen='oficial', producto='FLEX', plazos='36-60 meses', financiera=FINANCIERA)
    return dict(pf=precio - int(b_ca), contado=precio, bonif=int(b_ca), cap_min=int(ca['cap_min']), perm=36 if ca['producto'] == 'FLEX' else None, tin=ca['tin'], tae=None,
                cuota=None, meses=None, origen='campana', producto=ca['producto'], plazos=ca['plazos'], financiera=FINANCIERA)


def _m(n):
    return f"{int(n):,}".replace(",", ".")


def pie_legal(pfs):
    """Texto legal corto (folleto y pie de la web) a partir de las ofertas del listado."""
    if not pfs:
        return ''
    bmin, bmax = min(p['bonif'] for p in pfs), max(p['bonif'] for p in pfs)
    mins = [p['cap_min'] for p in pfs if p.get('cap_min')]
    return (f"Precio financiando: precio de contado menos la bonificación de {FINANCIERA} ({_m(bmin)} a {_m(bmax)} € según coche y campaña, IVA incluido), "
            f"solo para particulares y autónomos que financien con {FINANCIERA} (según condiciones contractuales). Capital mínimo a financiar desde {_m(min(mins))} € según campaña; "
            "plazo de 36 a 120 meses según coche y producto (FLEX o LINEAL, el plazo exacto de cada coche figura en su ficha); TIN 7,99 % u 8,99 % según campaña; comisión de apertura 2,99 %. "
            "TAE y cuota de cada coche, en su ficha. El seguro de protección es opcional.")
