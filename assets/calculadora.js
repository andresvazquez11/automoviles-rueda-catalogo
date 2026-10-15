/* ══════════════════════════════════════════════════════════════════
   Automóviles Rueda — Motor de calculadora de financiación (compartido)
   Extraído de generar_web.py — condiciones VWFS Octubre 2026.
   NO modificar la lógica de cv2* / initCalc a mano: si cambian las
   condiciones, se actualiza generar_web.py y se re-ejecuta la
   extracción (Task 1 de docs/superpowers/plans/2026-08-08-fichas-individuales-fase2-generalizacion.md).
   ══════════════════════════════════════════════════════════════════ */

function estadoLabel(estado) {
  return estado === 'No disponible' ? 'Reservado' : estado;
}
function fmtCuota(v) {
  if (!v && v !== 0) return '';
  return Number(v).toLocaleString('es-ES', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

function esReservado(estado) {
  return estado === 'No disponible';
}


const VR_TABLE = {
  24: {10000:79,15000:75,20000:70,25000:65,30000:60},
  36: {10000:75,15000:71,20000:66,25000:61,30000:56},
  48: {10000:71,15000:67,20000:62,25000:57,30000:52},
  60: {10000:67,15000:63,20000:58,25000:53,30000:48},
  72: {10000:63,15000:59,20000:54,25000:49,30000:44},
};

// ── Estado CV2 ────────────────────────────────────────────────────────────────
const CV2 = {
  precio:        0,
  entrada:       0,
  meses:         60,
  tab:           'lineal',    // 'lineal' | 'flex'
  km:            15000,
  marca:         'SEAT',      // 'SEAT' | 'CUPRA' | 'OTRA'
  matriculaMes:  null,
  matriculaAnio: null,
  campana:       'ENTRY',     // 'ENTRY' | 'GAMA' | 'APPROVED'
  tinOverride:   null,
  mantAnios:     0,
  cupraTipo:     'TERMICO',   // 'TERMICO' | 'ELECTRICO'
  modelo:        '',
  demosRema:     false,       // toggle manual — campaña especial SEAT VS DEMOS + REMA (Octubre 2026)
  salones:       false,       // toggle manual — campaña SALONES VO (solo SEAT Arona), Octubre 2026 v2
  auto:          true,        // modo automático: elige la campaña VW con la cuota más baja (modo asesor)
};


const CV2_ALL_PLAZOS = [24, 36, 48, 60, 72, 84, 96, 108, 120];
// Comisión de apertura VWFS (financiada): 2,99% desde Octubre 2026 (antes 3,50%)
const CV2_COMISION = 0.0299;

const CV2_MANT = {
  SEAT:                 { 2: 250,  4: 499, mandatory: false },
  CUPRA_APPROVED:       { 2: 0,    4: 400, mandatory: true  },
  CUPRA_GAMA_TERMICO:   { 2: 350,  4: 750, mandatory: true  },
  CUPRA_GAMA_ELECTRICO: { 2: 100,  4: 540, mandatory: true  },
};

function cv2GetMantKey() {
  const { marca, campana, cupraTipo } = CV2;
  if (marca === 'SEAT')  return 'SEAT';
  if (marca === 'OTRA')  return null;
  if (campana === 'APPROVED') return 'CUPRA_APPROVED';
  return cupraTipo === 'ELECTRICO' ? 'CUPRA_GAMA_ELECTRICO' : 'CUPRA_GAMA_TERMICO';
}

function cv2GetMantInfo() {
  const { meses } = CV2;
  const rules = cv2GetRules();
  const key   = cv2GetMantKey();
  const tbl   = key ? CV2_MANT[key] : null;
  const isVU  = rules.categoria === 'VU';
  const isAvail = !!tbl && !isVU;
  if (!isAvail) return { precioTotal:0, mensual:0, label:'', isAvail:false, mandatory:false, has4y:false, free:false, activeMeses:0 };
  if (tbl.mandatory && CV2.mantAnios === 0) CV2.mantAnios = 2;
  const activeMeses = CV2.mantAnios > 0 ? CV2.mantAnios : 0;
  const precioTotal = activeMeses > 0 ? (tbl[activeMeses] ?? 0) : 0;
  const mensual     = activeMeses > 0 && meses > 0 ? Math.round(precioTotal / meses * 100) / 100 : 0;
  const kms         = activeMeses === 4 ? '60.000' : '40.000';
  const label       = activeMeses > 0 ? `Mantenimiento ${activeMeses} años / ${kms} km` : '';
  const free        = activeMeses > 0 && precioTotal === 0;
  const has4y       = tbl[4] !== null && tbl[4] !== undefined;
  return { precioTotal, mensual, label, isAvail:true, mandatory:tbl.mandatory, has4y, free, activeMeses, key };
}

// ── Formato números ───────────────────────────────────────────────────────────
const cv2Fmt  = n => Math.round(n).toLocaleString('es-ES');
const cv2Fmt2 = n => n.toLocaleString('es-ES', { minimumFractionDigits:2, maximumFractionDigits:2 });

// ── Motor de reglas VWFS ──────────────────────────────────────────────────────
function cv2GetRules() {
  const { marca, matriculaMes, matriculaAnio, tab, precio, entrada, campana } = CV2;

  let antigMeses = null;
  if (matriculaMes && matriculaAnio && matriculaAnio >= 2000) {
    const now = new Date();
    const diff = (now.getFullYear() - matriculaAnio) * 12 + (now.getMonth() + 1 - matriculaMes);
    antigMeses = Math.max(0, diff);
  }

  const categoria = antigMeses === null ? null
    : antigMeses <= 24 ? 'VS'
    : antigMeses <= 60 ? 'VO' : 'VU';

  const producto   = tab === 'lineal' ? 'LINEAL' : 'FLEX';
  const importeNeto = Math.max(0, precio - entrada);
  // FLEX: 1ª matrícula + plazo ≤ 120 meses. LINEAL (Octubre 2026): antigüedad +
  // plazo hasta 15 años (2º y 3er ciclo) → 180 meses.
  const maxGlobal  = producto === 'FLEX' ? 120 : 180;

  let plazosDisp = [...CV2_ALL_PLAZOS];
  if (antigMeses !== null) {
    plazosDisp = plazosDisp.filter(p => antigMeses + p <= maxGlobal);
  }

  if (producto === 'FLEX') {
    if (categoria === 'VU') {
      plazosDisp = [];
    } else {
      // FLEX: 36-60 meses en todas las campañas (SEAT, CUPRA y DEMOS + REMA)
      plazosDisp = plazosDisp.filter(p => p >= 36 && p <= 60);
    }
  } else {
    // Octubre 2026: LINEAL VS hasta 120 meses, VO hasta 108 (antes 96 / 84)
    if (categoria === 'VS') { plazosDisp = plazosDisp.filter(p => p <= 120); }
    else if (categoria === 'VO') { plazosDisp = plazosDisp.filter(p => p <= 108); }
    else if (categoria === 'VU') { plazosDisp = plazosDisp.filter(p => p <= 48); }
  }

  let creditoMinimo = 0, bonificacion = 0, tin_auto = 7.50, campanaLabel = '';

  if (marca === 'SEAT') {
    // VWFS Campaña comercial SEAT VO · Octubre 2026 (págs. 2-8)
    if (campana === 'ENTRY' && categoria !== 'VU') {
      // ENTRY: TIN 7,99% (antes 7,50%), sin bonificación. LINEAL VS 48-120 / VO 48-108
      tin_auto = 7.99; bonificacion = 0; creditoMinimo = 10000; campanaLabel = 'ENTRY · SEAT';
      if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 48);
    } else {
      tin_auto = 8.99;
      if (categoria === 'VU') {
        // VU: bonificación 300€ (antes 400€), crédito mínimo 15.000€ (antes 7.000€)
        bonificacion = 300; creditoMinimo = 15000; campanaLabel = 'GAMA · SEAT · VU';
        plazosDisp = plazosDisp.filter(p => p >= 36 && p <= 48);
      } else if (categoria === 'VO') {
        // VO: bonificación 500€ (antes 750€). LINEAL 60-108 meses (antes 60-84)
        bonificacion = 500; creditoMinimo = producto === 'LINEAL' ? 9500 : 10000; campanaLabel = 'GAMA · SEAT · VO';
        if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 60 && p <= 108);
      } else {
        // VS: bonificación 750€ (sin cambios). LINEAL 60-120 meses (antes 60-96)
        bonificacion = 750; creditoMinimo = producto === 'LINEAL' ? 13000 : 10000;
        campanaLabel = categoria ? 'GAMA · SEAT · VS' : 'GAMA · SEAT';
        if (producto === 'LINEAL' && categoria === 'VS') plazosDisp = plazosDisp.filter(p => p >= 60 && p <= 120);
      }
    }
  } else if (marca === 'CUPRA') {
    if (campana === 'APPROVED' && (categoria === 'VS' || categoria === null)) {
      // VWFS Campaña CUPRA VO · Octubre 2026 (pág. 5): TIN 6,45% (antes 5,95%). LINEAL 36-120 meses
      tin_auto = 6.45; bonificacion = 0;
      creditoMinimo = producto === 'FLEX' ? 13500 : 10000; campanaLabel = 'APPROVED · CUPRA';
      if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 36);
    } else {
      // VWFS Campaña CUPRA VO · Octubre 2026 (pág. 4): FLEX 1.200€ (antes 1.300€) ·
      // LINEAL 1.000€ (48-71 meses) / 1.200€ (72-120 meses, antes 1.300€ hasta 96)
      tin_auto = 8.99;
      bonificacion = producto === 'FLEX' ? 1200 : (CV2.meses >= 72 ? 1200 : 1000);
      creditoMinimo = producto === 'FLEX' ? 16500 : 13500;
      campanaLabel = categoria ? 'GAMA · CUPRA · ' + (categoria || '') : 'GAMA · CUPRA';
      if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 48);
    }
  } else {
    // Campaña Otras Marcas · Octubre 2026: Básica TIN 8,25% · bonificaciones 200/400/500€
    // Plazo 48-120 meses (documento SEAT VO Octubre 2026 del 15/10, pág. 10; antes 48-96)
    plazosDisp = plazosDisp.filter(p => p >= 48 && p <= 120);
    if (importeNeto >= 20000) { tin_auto = 8.99; bonificacion = 500; creditoMinimo = 20000; campanaLabel = 'TOP · Otras Marcas'; }
    else if (importeNeto >= 15000) { tin_auto = 8.99; bonificacion = 400;  creditoMinimo = 15000; campanaLabel = 'Premium · Otras Marcas'; }
    else if (importeNeto >= 10000) { tin_auto = 8.99; bonificacion = 200;  creditoMinimo = 10000; campanaLabel = 'Entry · Otras Marcas'; }
    else { tin_auto = 8.25; bonificacion = 0; creditoMinimo = 6000; campanaLabel = 'Básica · Otras Marcas'; }
  }

  // ── Campaña especial SEAT VS DEMOS + REMA (Octubre 2026, pág. 6) ───────
  // Sustituye a la campaña Arona Buy Back/REMA (ya no existe). Toda la gama SEAT,
  // solo VS, activación manual (no se puede saber desde el anuncio si el coche
  // es demo o REMA). FLEX 36-60m TIN 7,99% + 950€ · LINEAL 48-120m TIN 5,99%.
  if (CV2.demosRema && marca === 'SEAT' && (categoria === 'VS' || categoria === null)) {
    creditoMinimo = 10000;
    if (producto === 'FLEX') { tin_auto = 7.99; bonificacion = 950; }
    else {
      // Desde los plazos por antigüedad, no desde los de ENTRY/GAMA (GAMA empezaba en 60)
      tin_auto = 5.99; bonificacion = 0;
      plazosDisp = CV2_ALL_PLAZOS.filter(p => (antigMeses === null || antigMeses + p <= maxGlobal) && p >= 48 && p <= 120);
    }
    campanaLabel = 'DEMOS + REMA · SEAT VS';
  }

  // ── Campaña SALONES VO (ARONA) · SEAT VO Octubre 2026 (págs. 4 y 9) ────────
  // Solo SEAT Arona, activación manual. Con «ENTRY» seleccionado aplica SALONES TIN
  // BAJO (VS+VO) y con «GAMA», SALONES GAMA con bonificación. Bonificación según plazo.
  if (CV2.salones && marca === 'SEAT' && /arona/i.test(CV2.modelo || '')) {
    const porAntig = CV2_ALL_PLAZOS.filter(p => antigMeses === null || antigMeses + p <= maxGlobal);
    const m = CV2.meses;
    if (campana === 'ENTRY' && categoria !== 'VU') {
      tin_auto = 7.99; campanaLabel = 'SALONES TIN BAJO · Arona';
      if (producto === 'FLEX') { creditoMinimo = 12000; bonificacion = 1000; plazosDisp = porAntig.filter(p => p >= 36 && p <= 60); }
      else { creditoMinimo = 13500; bonificacion = m >= 60 ? 1000 : 500; plazosDisp = porAntig.filter(p => p >= 48 && p <= 120); }
    } else {
      tin_auto = 8.99; campanaLabel = 'SALONES GAMA · Arona' + (categoria ? ' · ' + categoria : '');
      if (producto === 'FLEX') {
        plazosDisp = porAntig.filter(p => p >= 36 && p <= 60);
        if (categoria === 'VO') { creditoMinimo = 12000; bonificacion = m >= 60 ? 1500 : 1000; }
        else { creditoMinimo = 13500; bonificacion = m >= 60 ? 2000 : m >= 48 ? 1750 : 1000; }
      } else {
        creditoMinimo = 13500; bonificacion = m >= 84 ? 2000 : 1000;
        plazosDisp = porAntig.filter(p => p >= 60 && p <= 120);
      }
    }
  }

  const tinFinal = CV2.tinOverride !== null ? CV2.tinOverride : tin_auto;
  const codigo = cv2CodigoCampana(marca, campana, producto, categoria, importeNeto);
  return { tinFinal, tin_auto, bonificacion, creditoMinimo, campanaLabel, plazosDisp, categoria, antigMeses, codigo };
}

// ── Claves de campaña VWFS (Octubre 2026) ─────────────────────────────────────
// Las pide la web de la financiera al dar de alta la operación. Solo se muestran
// en modo asesor. SEAT VO págs. 6-10 · CUPRA VO págs. 4-6. En las parejas de
// SALONES TIN BAJO («AYRI / AYRE») la primera es VS y la segunda VO.
const CV2_CODIGOS = {
  SEAT_ENTRY:    { VS: { FLEX: 'AYKQ', LINEAL: 'AYKK' }, VO: { FLEX: 'AYKS', LINEAL: 'AYKM' } },
  SEAT_GAMA:     { VS: { FLEX: 'AYKC', LINEAL: 'AYKG' }, VO: { FLEX: 'AYKE', LINEAL: 'AYKI' }, VU: { LINEAL: 'AYKO' } },
  SAL_TIN:       { VS: { FLEX: 'AYRI', LINEAL: 'AYRK' }, VO: { FLEX: 'AYRE', LINEAL: 'AYRG' } },
  SAL_GAMA:      { VS: { FLEX: 'AYRQ', LINEAL: 'AYRS' }, VO: { FLEX: 'AYRM', LINEAL: 'AYRO' }, VU: { LINEAL: 'AYRU' } },
  CUPRA_APPROVED:{ VS: { FLEX: 'AYJV', LINEAL: 'AYJZ' }, VO: { FLEX: 'AYJT', LINEAL: 'AYJX' } },
  CUPRA_GAMA:    { VS: { FLEX: 'AYI7', LINEAL: 'AYJB' }, VO: { FLEX: 'AYI5', LINEAL: 'AYI9' } },
  // Otras Marcas: Básica · Entry · Premium · TOP
  OTRA:          { VS: ['AYKX', 'AYKY', 'AYK1', 'AYK2'], VO: ['AYKT', 'AYKU', 'AYK9', 'AYLA'], VU: ['AYLK', 'AYLL', 'AYK5', 'AYK6'] },
};

function cv2CampanaActiva(marca, campana, categoria) {
  if (marca === 'OTRA') return 'OTRA';
  if (marca === 'CUPRA') return campana === 'APPROVED' && (categoria === 'VS' || categoria === null) ? 'CUPRA_APPROVED' : 'CUPRA_GAMA';
  if (CV2.salones && /arona/i.test(CV2.modelo || '')) return campana === 'ENTRY' && categoria !== 'VU' ? 'SAL_TIN' : 'SAL_GAMA';
  if (CV2.demosRema && (categoria === 'VS' || categoria === null)) return 'DEMOS';
  return campana === 'ENTRY' && categoria !== 'VU' ? 'SEAT_ENTRY' : 'SEAT_GAMA';
}

function cv2CodigoCampana(marca, campana, producto, categoria, importeNeto) {
  const id  = cv2CampanaActiva(marca, campana, categoria);
  const cat = categoria || 'VS';
  if (id === 'DEMOS') return producto === 'FLEX' ? 'AYJ5' : (CV2.meses >= 96 ? 'AYJ8' : 'AYJ7');
  if (id === 'OTRA') {
    const nivel = importeNeto >= 20000 ? 3 : importeNeto >= 15000 ? 2 : importeNeto >= 10000 ? 1 : 0;
    return CV2_CODIGOS.OTRA[cat][nivel];
  }
  const t = CV2_CODIGOS[id] && CV2_CODIGOS[id][cat];
  return (t && t[producto]) || '';
}

// Campañas a las que puede optar el coche (tarjetas del modo asesor). `set` es
// el estado que deja la calculadora fija en esa campaña al pinchar la tarjeta.
const CV2_OPCIONES = [
  { id: 'SEAT_ENTRY', marca: 'SEAT', nombre: 'ENTRY · TIN bajo',        set: { campana: 'ENTRY', demosRema: false, salones: false }, ok: c => c !== 'VU' },
  { id: 'SEAT_GAMA',  marca: 'SEAT', nombre: 'GAMA · con bonificación', set: { campana: 'GAMA',  demosRema: false, salones: false } },
  { id: 'DEMOS',      marca: 'SEAT', nombre: 'DEMOS + REMA', nota: 'solo si el coche es demo o REMA',
    set: { campana: 'GAMA', demosRema: true, salones: false }, ok: c => c === 'VS' || c === null },
  { id: 'SAL_TIN',    marca: 'SEAT', arona: true, nombre: 'SALONES Arona · TIN bajo',
    set: { campana: 'ENTRY', demosRema: false, salones: true }, ok: c => c !== 'VU' },
  { id: 'SAL_GAMA',   marca: 'SEAT', arona: true, nombre: 'SALONES Arona · GAMA',
    set: { campana: 'GAMA', demosRema: false, salones: true } },
  { id: 'CUPRA_APPROVED', marca: 'CUPRA', nombre: 'APPROVED', set: { campana: 'APPROVED' }, ok: c => c === 'VS' || c === null },
  { id: 'CUPRA_GAMA',     marca: 'CUPRA', nombre: 'GAMA · con bonificación', set: { campana: 'GAMA' } },
];
const CV2_OTRA_NIVELES = [
  { nombre: 'Básica',  tin: 8.25, bonif: 0,   min: 6000,  hasta: 10000 },
  { nombre: 'Entry',   tin: 8.99, bonif: 200, min: 10000, hasta: 15000 },
  { nombre: 'Premium', tin: 8.99, bonif: 400, min: 15000, hasta: 20000 },
  { nombre: 'TOP',     tin: 8.99, bonif: 500, min: 20000, hasta: Infinity },
];

// Resumen de una campaña para este coche: se simula la calculadora con esa
// campaña en Flex y en Lineal y en cada plazo, y se restaura el estado.
// Miles con punto también en 4 cifras (toLocaleString es-ES no agrupa 1000)
const cv2Miles = v => String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');

function cv2ResumenOpcion(op) {
  const guard = { campana: CV2.campana, demosRema: CV2.demosRema, salones: CV2.salones,
                  tab: CV2.tab, meses: CV2.meses, tinOverride: CV2.tinOverride };
  Object.assign(CV2, op.set, { tinOverride: null });
  const out = {};
  ['flex', 'lineal'].forEach(tab => {
    CV2.tab = tab;
    const base = cv2GetRules();
    if (tab === 'flex' && base.categoria === 'VU') return;
    if (!base.plazosDisp.length) return;
    // Bonificación por tramos de plazo consecutivos con el mismo importe
    const tramos = [], cod = new Set();
    base.plazosDisp.forEach(m => {
      CV2.meses = m; const r = cv2GetRules(); if (r.codigo) cod.add(r.codigo);
      const ult = tramos[tramos.length - 1];
      if (ult && ult.bonif === r.bonificacion) ult.hasta = m; else tramos.push({ desde: m, hasta: m, bonif: r.bonificacion });
    });
    const tramoTxt = t => (t.desde === t.hasta ? t.desde : t.desde + '–' + t.hasta) + ' m: ' + (t.bonif ? cv2Miles(t.bonif) + ' €' : 'sin bonif.');
    out[tab] = {
      tin: base.tin_auto, min: base.creditoMinimo,
      cumple: CV2.precio - base.bonificacion - CV2.entrada >= base.creditoMinimo,
      plazos: base.plazosDisp.length === 1 ? base.plazosDisp[0] + ' m' : base.plazosDisp[0] + '–' + base.plazosDisp[base.plazosDisp.length - 1] + ' m',
      bonif: tramos.length === 1 ? (tramos[0].bonif ? cv2Miles(tramos[0].bonif) + ' €' : 'sin bonif.') : 'bonif. ' + tramos.map(tramoTxt).join(' / '),
      codigos: [...cod].join(' / '),
    };
  });
  Object.assign(CV2, guard);
  return out;
}

function cv2RenderCampanas(rules) {
  const box = document.getElementById('cv2-camps');
  if (!box) return;
  const cat = rules.categoria;
  const pct = v => v.toFixed(2).replace('.', ',') + '%';
  let html = '';
  if (CV2.marca === 'OTRA') {
    const codes = CV2_CODIGOS.OTRA[cat || 'VS'];
    const neto = Math.max(0, CV2.precio - CV2.entrada);
    CV2_OTRA_NIVELES.forEach((n, i) => {
      const act = neto >= n.min && neto < n.hasta;
      html += `<div class="cv2-cc${act ? ' active' : ''} fija">
        <div class="cv2-cc-top"><span class="cv2-cc-nom">Otras Marcas · ${n.nombre}</span><span class="cv2-cc-cod">${codes[i]}</span></div>
        <div class="cv2-cc-txt">Lineal · TIN ${pct(n.tin)} · ${n.bonif ? cv2Miles(n.bonif) + ' € bonif.' : 'sin bonif.'} · 48–120 m · a financiar ${cv2Miles(n.min)}${n.hasta < Infinity ? '–' + cv2Miles(n.hasta - 1) : ' o más'} €</div>
      </div>`;
    });
    html += `<div class="cv2-cc-nota">Otras Marcas se aplica sola según el importe a financiar (precio − entrada).</div>`;
  } else {
    html += CV2.auto
      ? `<div class="cv2-auto on">⚡ <b>Automático:</b> se elige sola la campaña VW con la cuota más baja para esta entrada y plazo. Pincha una tarjeta para fijarla a mano.</div>`
      : `<button type="button" class="cv2-auto off" onclick="cv2VolverAuto()">✋ Campaña fijada a mano · <b>⚡ volver a automático</b></button>`;
    const activa = cv2CampanaActiva(CV2.marca, CV2.campana, cat);
    const arona  = /arona/i.test(CV2.modelo || '');
    CV2_OPCIONES.filter(o => o.marca === CV2.marca && (!o.arona || arona) && (!o.ok || o.ok(cat))).forEach(o => {
      const r = cv2ResumenOpcion(o);
      const linea = (k, nom) => r[k] ? `<div class="cv2-cc-txt"><b>${nom}</b> <span class="cv2-cc-cod2">${r[k].codigos || 'sin clave'}</span> · TIN ${pct(r[k].tin)} · ${r[k].bonif} · ${r[k].plazos} · mín. ${cv2Miles(r[k].min)} €</div>` : '';
      const act = r[CV2.tab] || r.lineal;
      const noLlega = act && !act.cumple && o.id !== activa;
      html += `<button type="button" class="cv2-cc${o.id === activa ? ' active' : ''}${noLlega ? ' nollega' : ''}" onclick="cv2ElegirCampana('${o.id}')">
        <div class="cv2-cc-top"><span class="cv2-cc-nom">${o.nombre}</span>${o.nota ? `<span class="cv2-cc-nota2">${o.nota}</span>` : ''}${noLlega ? `<span class="cv2-cc-nota3">no llega al mínimo con esta entrada (se bajará la entrada)</span>` : ''}</div>
        ${linea('lineal', 'Lineal')}${linea('flex', 'Flex')}
      </button>`;
    });
    if (CV2.marca === 'CUPRA' && cat === 'VU')
      html += `<div class="cv2-cc-nota">Las campañas CUPRA son para coches de 0 a 5 años: este no tiene clave de campaña. Consúltalo con la financiera.</div>`;
  }
  box.innerHTML = html;
  const codEl = document.getElementById('cv2-codigo');
  if (codEl) {
    codEl.style.display = rules.codigo ? '' : 'none';
    const v = document.getElementById('cv2-codigo-val');
    if (v) v.textContent = rules.codigo;
  }
}

// ── Comparativa VW (Lineal) con BBVA y CaixaBank · modo asesor ───────────────
// Misma entrada y plazo. Se compara la cuota de financiación sin mantenimiento
// (los bancos no lo incluyen); el total suma entrada + cuotas. En Flex no se
// muestra: la cuota final hace que no sea comparable con un préstamo lineal.
function cv2RenderComparativa() {
  const box = document.getElementById('cv2-comp');
  if (!box) return;
  if (CV2.tab !== 'lineal' || !CV2.precio) { box.innerHTML = ''; box.style.display = 'none'; return; }
  const res = cv2Calc();
  const f2 = v => { const [e, d] = Math.abs(v).toFixed(2).split('.'); return cv2Miles(+e) + ',' + d; };
  const m = CV2.meses, entrada = CV2.entrada, importe = Math.max(0, CV2.precio - entrada);
  const filas = [{ nom: 'VW · ' + res.rules.campanaLabel + (res.rules.codigo ? ' (' + res.rules.codigo + ')' : ''),
                   tin: res.rules.tinFinal.toFixed(2).replace('.', ','), cuota: res.cuota, vw: true }];
  const tb = bbvaTarifa();
  filas.push(tb.coef[m] && m <= tb.max
    ? { nom: 'BBVA', tin: tb.tin, cuota: Math.round(tb.coef[m] * importe * 100) / 100 }
    : { nom: 'BBVA', tin: tb.tin, no: true });
  const tc = caixaTarifa();
  filas.push(tc.disponible && tc.plazos.includes(m)
    ? { nom: 'CaixaBank', tin: CAIXA_TIN, cuota: Math.round(CAIXA_COEF[m] * importe * 100) / 100 }
    : { nom: 'CaixaBank', tin: CAIXA_TIN, no: true });
  filas.forEach(f => { if (!f.no) f.total = Math.round((f.cuota * m + entrada) * 100) / 100; });
  const validas = filas.filter(f => !f.no);
  const mejor = validas.reduce((a, b) => (b.cuota < a.cuota ? b : a), validas[0]);
  const vw = filas[0];
  const sg = v => (v > 0 ? '+' : v < 0 ? '−' : '') + f2(Math.abs(v));
  let html = `<div class="cv2-comp-tit">Comparativa con bancos · ${m} meses · entrada ${cv2Miles(entrada)} €</div>
    <div class="cv2-comp-row cv2-comp-head"><span>Financiera</span><span>Cuota/mes</span><span>Total a pagar</span><span>Diferencia con VW</span></div>`;
  filas.forEach(f => {
    const cls = 'cv2-comp-row' + (f === mejor ? ' mejor' : '') + (f.no ? ' no' : '');
    if (f.no) { html += `<div class="${cls}"><span>${f.nom} · ${f.tin}%</span><span class="cv2-comp-na">no disponible a ${m} meses para este coche</span></div>`; return; }
    const dif = f.vw ? '—' : `${sg(f.cuota - vw.cuota)} €/mes · ${sg(f.total - vw.total)} € total`;
    html += `<div class="${cls}"><span>${f.nom} · ${f.tin}%</span><span>${f2(f.cuota)} €</span><span>${f2(f.total)} €</span><span>${dif}</span></div>`;
  });
  if (mejor) {
    const otras = validas.filter(f => f !== mejor);
    const ahorro = otras.length ? Math.min(...otras.map(f => f.total - mejor.total)) : 0;
    html += `<div class="cv2-comp-best">La más conveniente: <b>${mejor.vw ? 'VW' : mejor.nom}</b>${ahorro > 0 ? ` · ahorra al menos ${f2(ahorro)} € en total frente a la siguiente` : ''}</div>`;
  }
  html += `<div class="cv2-comp-nota">Cuota de financiación sin mantenimiento. VW con la bonificación ya descontada.</div>`;
  box.innerHTML = html;
  box.style.display = '';
}

// ── Mapa de conveniencia (modo asesor, Lineal) ───────────────────────────────
// Para cada plazo y entrada de ejemplo, qué financiera da la cuota más baja:
// VW (la mejor campaña a la que puede optar el coche; DEMOS + REMA solo si está
// activada), BBVA o CaixaBank. Mismo criterio que la comparativa.
const CV2_MAPA_COLORES = { VW: '#C8232B', BBVA: '#2563EB', CaixaBank: '#0D9488' };

function cv2MapaCelda(m, e) {
  const precio = CV2.precio, cands = [];
  const ops = CV2.marca === 'OTRA' ? [{ id: 'OTRA', nombre: 'Otras Marcas', set: {} }]
    : CV2_OPCIONES.filter(o => o.marca === CV2.marca && (!o.arona || /arona/i.test(CV2.modelo || ''))
        && (o.id !== 'DEMOS' || CV2.demosRema));
  ops.forEach(o => {
    Object.assign(CV2, o.set, { tab: 'lineal', meses: m, entrada: e, tinOverride: null });
    const r = cv2GetRules();
    if (o.ok && !o.ok(r.categoria)) return;
    if (!r.plazosDisp.includes(m)) return;
    const min = CV2.marca === 'OTRA' ? CV2_OTRA_NIVELES[0].min : r.creditoMinimo;
    if (precio - r.bonificacion - e < min) return;
    cands.push({ fin: 'VW', camp: o.nombre, id: o.id, cuota: cv2Calc().cuota });
  });
  const tb = bbvaTarifa();
  if (tb.coef[m] && m <= tb.max && precio - e >= 500) cands.push({ fin: 'BBVA', cuota: Math.round(tb.coef[m] * (precio - e) * 100) / 100 });
  const tc = caixaTarifa();
  if (tc.disponible && tc.plazos.includes(m) && precio - e >= 500) cands.push({ fin: 'CaixaBank', cuota: Math.round(CAIXA_COEF[m] * (precio - e) * 100) / 100 });
  // Por financiera, su mejor opción; luego ganador y ahorro frente a la segunda financiera
  const porFin = {};
  cands.forEach(c => { if (!porFin[c.fin] || c.cuota < porFin[c.fin].cuota) porFin[c.fin] = c; });
  const orden = Object.values(porFin).sort((a, b) => a.cuota - b.cuota);
  if (!orden.length) return null;
  // alcanzable: alguna campaña VW admite este plazo y entrada (si no, la calculadora no puede ponerse ahí)
  return { alcanzable: !!porFin.VW, vwId: porFin.VW ? porFin.VW.id : '', gana: orden[0], ahorroMes: orden[1] ? orden[1].cuota - orden[0].cuota : 0, ahorroTotal: orden[1] ? (orden[1].cuota - orden[0].cuota) * m : 0 };
}

function cv2RenderMapa() {
  const box = document.getElementById('cv2-mapa');
  if (!box) return;
  if (CV2.tab !== 'lineal' || !CV2.precio) { box.innerHTML = ''; box.style.display = 'none'; return; }
  const guard = { campana: CV2.campana, demosRema: CV2.demosRema, salones: CV2.salones, tab: CV2.tab,
                  meses: CV2.meses, entrada: CV2.entrada, tinOverride: CV2.tinOverride };
  const maxE = Math.max(0, Math.floor((CV2.precio - 10000) / 1000) * 1000);
  const paso = Math.max(1000, Math.ceil(maxE / 5 / 1000) * 1000);
  const entradas = [];
  for (let e = 0; e <= maxE; e += paso) entradas.push(e);
  const plazos = CV2_ALL_PLAZOS.filter(p => p >= 24);
  const tabla = plazos.map(m => entradas.map(e => cv2MapaCelda(m, e)));
  Object.assign(CV2, guard);

  const nomGana = g => g.fin === 'VW' ? 'VW · ' + g.camp : g.fin;
  const f0 = v => cv2Miles(v);
  const f2 = v => { const [a, d] = Math.abs(v).toFixed(2).split('.'); return cv2Miles(+a) + ',' + d; };
  // Frases: por cada entrada, tramos de plazo consecutivos con el mismo ganador
  let frases = '';
  entradas.forEach((e, j) => {
    const tramos = [];
    plazos.forEach((m, i) => {
      const c = tabla[i][j]; if (!c) return;
      const n = nomGana(c.gana), ult = tramos[tramos.length - 1];
      if (ult && ult.n === n && ult.fin === c.gana.fin) ult.hasta = m; else tramos.push({ n, fin: c.gana.fin, desde: m, hasta: m });
    });
    if (!tramos.length) return;
    const txt = tramos.map(t => `${t.desde === t.hasta ? t.desde : t.desde + '–' + t.hasta} m → <b style="color:${CV2_MAPA_COLORES[t.fin]}">${t.n}</b>`).join(' · ');
    frases += `<div class="cv2-mapa-frase"><span>${e ? 'Entrada ' + f0(e) + ' €' : 'Sin entrada'}:</span> ${txt}</div>`;
  });
  // Casilla más cercana a lo que hay puesto ahora
  const jAct = entradas.reduce((b, e, j) => Math.abs(e - CV2.entrada) < Math.abs(entradas[b] - CV2.entrada) ? j : b, 0);
  let html = `<div class="cv2-comp-tit">Mapa de conveniencia · ¿qué financiera conviene según plazo y entrada?</div>
    <div class="cv2-mapa-leyenda">${Object.entries(CV2_MAPA_COLORES).map(([k, c]) => `<span><i style="background:${c}"></i>${k}</span>`).join('')}</div>
    ${frases}
    <div class="cv2-mapa-wrap"><table class="cv2-mapa-tbl"><thead><tr><th>Plazo \\ Entrada</th>${entradas.map(e => `<th>${f0(e)} €</th>`).join('')}</tr></thead><tbody>`;
  plazos.forEach((m, i) => {
    html += `<tr><th>${m} m</th>`;
    entradas.forEach((e, j) => {
      const c = tabla[i][j];
      if (!c) { html += `<td class="na">—</td>`; return; }
      const act = m === CV2.meses && j === jAct && c.alcanzable;
      const clic = c.alcanzable ? `onclick="cv2MapaElegir(${m},${e},'${c.vwId}')"` : '';
      html += `<td class="${act ? 'act' : ''}${c.alcanzable ? '' : ' solo-banco'}" style="background:${CV2_MAPA_COLORES[c.gana.fin]}"
        title="${c.alcanzable ? nomGana(c.gana) : nomGana(c.gana) + ' · VW no permite este plazo o entrada: calcúlalo en la pestaña del banco'}" ${clic}>
        <b>${c.gana.fin === 'CaixaBank' ? 'Caixa' : c.gana.fin}</b><span>${f2(c.gana.cuota)} €</span>${c.ahorroTotal > 0 ? `<small>−${f0(c.ahorroTotal)} €</small>` : ''}</td>`;
    });
    html += `</tr>`;
  });
  html += `</tbody></table></div>
    <div class="cv2-comp-nota">Cada casilla: financiera más barata, su cuota y lo que ahorra en total frente a la siguiente. Pincha una casilla para ponerla en la calculadora. Las atenuadas no las permite VW (plazo o entrada): calcúlalas en la pestaña del banco.</div>`;
  box.innerHTML = html;
  box.style.display = '';
}

// ── Buscar por cuota (la inversa) · modo asesor ──────────────────────────────
// El asesor pone la cuota que quiere el cliente y su entrada; para cada plazo se
// busca la financiación más barata (VW con su mejor campaña, BBVA o CaixaBank,
// en Lineal) y se recomienda el plazo más corto que no pasa de esa cuota.
let cv2InvClave = '';
function cv2RenderInversa(forzar) {
  const box = document.getElementById('cv2-inv-res');
  if (!box) return;
  const objetivo = parseFloat((document.getElementById('cv2-inv-cuota') || {}).value) || 0;
  const e = Math.max(0, parseFloat((document.getElementById('cv2-inv-entrada') || {}).value) || 0);
  const clave = [CV2.precio, objetivo, e, CV2.demosRema, CV2.modelo, CV2.matriculaMes, CV2.matriculaAnio].join('|');
  if (!forzar && clave === cv2InvClave) return;
  cv2InvClave = clave;
  if (!objetivo) { box.innerHTML = `<div class="cv2-comp-nota">Escribe la cuota que quiere pagar el cliente y su entrada.</div>`; return; }
  const f2 = v => { const [a, d] = Math.abs(v).toFixed(2).split('.'); return cv2Miles(+a) + ',' + d; };
  const nom = g => g.fin === 'VW' ? 'VW · ' + g.camp : g.fin;
  const plazos = CV2_ALL_PLAZOS;
  const filas = cv2ConEstado(() => plazos.map(m => ({ m, c: cv2MapaCelda(m, e) }))).filter(x => x.c);
  if (!filas.length) { box.innerHTML = `<div class="cv2-comp-nota">Con ${cv2Miles(e)} € de entrada no queda importe que financiar.</div>`; return; }
  const cumple = filas.filter(x => x.c.gana.cuota <= objetivo);
  const reco = cumple[0] || null;   // el plazo más corto que no pasa de la cuota: menos intereses
  const cerca = filas.reduce((a, b) => Math.abs(b.c.gana.cuota - objetivo) < Math.abs(a.c.gana.cuota - objetivo) ? b : a);
  let html = '';
  if (reco) {
    html += `<div class="cv2-inv-reco">✓ Recomendada: <b>${reco.m} meses con ${nom(reco.c.gana)}</b> · ${f2(reco.c.gana.cuota)} €/mes (${f2(objetivo - reco.c.gana.cuota)} € por debajo de lo que quiere) · total ${f2(reco.c.gana.cuota * reco.m + e)} €</div>`;
  } else {
    // No se llega: buscar la entrada necesaria
    let necesaria = null;
    cv2ConEstado(() => {
      for (let ee = Math.ceil(e / 100) * 100 + 100; ee <= CV2.precio - 500 && !necesaria; ee += 100)
        for (const m of plazos) { const c = cv2MapaCelda(m, ee); if (c && c.gana.cuota <= objetivo) { necesaria = { e: ee, m, c }; break; } }
    });
    const minima = filas.reduce((a, b) => b.c.gana.cuota < a.c.gana.cuota ? b : a);
    html += `<div class="cv2-inv-aviso">Con ${cv2Miles(e)} € de entrada no se llega a ${f2(objetivo)} €/mes: lo más bajo es ${f2(minima.c.gana.cuota)} € a ${minima.m} meses con ${nom(minima.c.gana)}.`
      + (necesaria ? ` Para llegar haría falta unos <b>${cv2Miles(necesaria.e)} € de entrada</b> (${necesaria.m} meses con ${nom(necesaria.c.gana)}, ${f2(necesaria.c.gana.cuota)} €/mes).` : '') + `</div>`;
  }
  html += `<div class="cv2-comp-row cv2-comp-head"><span>Plazo · financiera más barata</span><span>Cuota/mes</span><span>Total a pagar</span><span>Frente a ${f2(objetivo)} €</span></div>`;
  filas.forEach(x => {
    const g = x.c.gana, dif = g.cuota - objetivo;
    const cls = 'cv2-comp-row cv2-inv-fila' + (x === reco ? ' mejor' : '') + (x === cerca && x !== reco ? ' cerca' : '') + (x.c.alcanzable ? '' : ' no');
    const clic = x.c.alcanzable ? ` onclick="cv2MapaElegir(${x.m},${e},'${x.c.vwId}')" title="Poner en la calculadora"` : ` title="VW no permite este plazo o entrada: calcúlalo en la pestaña del banco"`;
    html += `<div class="${cls}"${clic}><span>${x.m} m · <b style="color:${CV2_MAPA_COLORES[g.fin]}">${nom(g)}</b>${x === cerca && x !== reco ? ' · la más cercana' : ''}</span>`
      + `<span>${f2(g.cuota)} €</span><span>${f2(g.cuota * x.m + e)} €</span>`
      + `<span class="${dif <= 0 ? 'cv2-inv-ok' : 'cv2-inv-ko'}">${dif <= 0 ? '−' : '+'}${f2(dif)} €/mes</span></div>`;
  });
  html += `<div class="cv2-comp-nota">Lineal, sin mantenimiento. Pincha un plazo para ponerlo en la calculadora (en VW se aplica su mejor campaña).</div>`;
  box.innerHTML = html;
}

function cv2MapaElegir(m, e, id) {
  if (id) { const o = CV2_OPCIONES.find(x => x.id === id); if (o) { CV2.demosRema = !!o.set.demosRema; CV2.salones = !!o.set.salones; CV2.campana = o.set.campana; } }
  if (CV2.tab !== 'lineal') cv2SetMode('lineal');
  CV2.entrada = e;
  const slider = document.getElementById('cv2-sl-entrada'); if (slider) slider.value = e;
  const dispE = document.getElementById('cv2-entrada-input'); if (dispE) dispE.value = e;
  cv2SetMeses(m);
}

// ── Plegar / desplegar las herramientas internas del asesor ──────────────────
// Plegadas, el cliente solo ve la calculadora (cuota, entrada, desglose).
// Se recuerda en este navegador.
function cv2ToggleInterno(forzar) {
  const off = typeof forzar === 'boolean' ? forzar : !document.documentElement.classList.contains('cv2-int-off');
  document.documentElement.classList.toggle('cv2-int-off', off);
  try { localStorage.setItem('rd_cv2_int', off ? '0' : '1'); } catch (e) {}
}
(function () { try { if (localStorage.getItem('rd_cv2_int') === '0') document.documentElement.classList.add('cv2-int-off'); } catch (e) {} })();

function cv2ElegirCampana(id) {
  const o = CV2_OPCIONES.find(x => x.id === id);
  if (!o) return;
  CV2.auto = false;   // elegida a mano: deja de elegir sola
  CV2.demosRema = !!o.set.demosRema;
  CV2.salones   = !!o.set.salones;
  cv2SetCampana(o.set.campana);
}

function cv2CopiarCodigo() {
  const cod = cv2GetRules().codigo;
  if (!cod) return;
  const btn = document.getElementById('cv2-codigo-btn');
  const ok = () => { if (btn) { btn.textContent = '✓ copiado'; setTimeout(() => { btn.textContent = 'Copiar'; }, 1500); } };
  if (navigator.clipboard) navigator.clipboard.writeText(cod).then(ok, ok); else ok();
}

// ── Cálculo cuota ─────────────────────────────────────────────────────────────
function cv2Calc() {
  const { precio, entrada, meses, tab, km } = CV2;
  const rules = cv2GetRules();
  const tin   = rules.tinFinal;
  const bonif = rules.bonificacion;
  const r = tin / 100 / 12;
  const rn = Math.pow(1 + r, meses);
  const precioEf = Math.max(0, precio - bonif);
  const neto     = Math.max(0, precioEf - entrada);
  const seg0     = precioEf * 0.061545;
  const seg      = precioEf > 0 ? Math.round(seg0 * Math.pow(neto / precioEf, 1.5) * 100) / 100 : 0;
  const base     = neto + seg;
  const capital  = Math.round(base * (1 + CV2_COMISION) * 100) / 100;
  const comision = Math.round((capital - base) * 100) / 100;
  let vr = 0, cuota = 0;
  if (tab === 'flex') {
    const tbl = VR_TABLE[meses] || VR_TABLE[60];
    const pct = tbl[km] !== undefined ? tbl[km] : 46;
    vr = Math.round(precio * pct / 100);
    cuota = (rn > 1 && r > 0) ? (capital * r * rn - vr * r) / (rn - 1) : capital / meses;
  } else {
    cuota = (rn > 1 && r > 0) ? capital * r / (1 - 1 / rn) : capital / meses;
  }
  cuota = Math.round(cuota * 100) / 100;
  const total = Math.round((cuota * meses + entrada + vr) * 100) / 100;
  return { seg, comision, capital, cuota, total, vr, bonif, precioEf, rules };
}

// ── Actualizar UI de campaña ──────────────────────────────────────────────────
function cv2UpdateCampanaUI() {
  const { marca, campana } = CV2;
  const rules = cv2GetRules();
  const cat   = rules.categoria;

  document.getElementById('cv2-camp-seat').style.display  = marca === 'SEAT'  ? 'flex' : 'none';
  document.getElementById('cv2-camp-cupra').style.display = marca === 'CUPRA' ? 'flex' : 'none';
  document.getElementById('cv2-camp-otra').style.display  = marca === 'OTRA'  ? 'block' : 'none';

  if (marca === 'SEAT') {
    const entryBtn = document.getElementById('cv2-entry');
    const gamaBtn  = document.getElementById('cv2-gama-seat');
    const isVU     = cat === 'VU';
    entryBtn.disabled = isVU;
    if (isVU && campana === 'ENTRY') CV2.campana = 'GAMA';
    const ac = CV2.campana;
    entryBtn.classList.toggle('active', ac === 'ENTRY' && !isVU);
    gamaBtn.classList.toggle('active', ac === 'GAMA' || isVU);
  }
  if (marca === 'CUPRA') {
    const gamaBtn     = document.getElementById('cv2-gama-cupra');
    const approvedBtn = document.getElementById('cv2-approved');
    const canApproved = cat === 'VS' || cat === null;
    approvedBtn.disabled = !canApproved;
    if (!canApproved && campana === 'APPROVED') CV2.campana = 'GAMA';
    const ac = CV2.campana;
    gamaBtn.classList.toggle('active', ac === 'GAMA');
    approvedBtn.classList.toggle('active', ac === 'APPROVED' && canApproved);
  }
  if (marca === 'OTRA') {
    const r2 = cv2GetRules();
    document.getElementById('cv2-otra-label').textContent = r2.campanaLabel + ' · mín. ' + cv2Fmt(r2.creditoMinimo) + ' €';
  }
}

// ── Actualizar TIN display ────────────────────────────────────────────────────
function cv2UpdateTinUI(rules) {
  const tinDisp = rules.tinFinal.toFixed(2).replace('.', ',');
  document.getElementById('cv2-tin-val').textContent = tinDisp;
  document.getElementById('cv2-tin-lbl').textContent = rules.campanaLabel;
  const inp = document.getElementById('cv2-tin-input');
  if (inp) inp.value = rules.tinFinal.toFixed(2);
}

// ── Actualizar pills de plazo ─────────────────────────────────────────────────
function cv2UpdatePlazoPills(plazosDisp) {
  CV2_ALL_PLAZOS.forEach(p => {
    const el = document.getElementById('cv2-pl-' + p);
    if (!el) return;
    const avail = plazosDisp.includes(p);
    el.disabled = !avail;
    el.classList.toggle('active', CV2.meses === p);
    el.style.opacity = avail ? '' : '0.25';
    el.style.cursor  = avail ? '' : 'not-allowed';
    el.style.pointerEvents = avail ? '' : 'none';
  });
  if (!plazosDisp.includes(CV2.meses) && plazosDisp.length > 0) {
    const newMeses = plazosDisp[plazosDisp.length - 1];
    CV2.meses = newMeses;
    document.getElementById('cv2-disp-meses').textContent = newMeses + ' meses';
    CV2_ALL_PLAZOS.forEach(p => {
      const el = document.getElementById('cv2-pl-' + p);
      if (el) el.classList.toggle('active', p === newMeses);
    });
  }
  // Note FLEX no disponible para VU
  const isVU = cv2GetRules().categoria === 'VU';
  const flexNote = document.getElementById('cv2-flex-note');
  if (flexNote) flexNote.classList.toggle('visible', CV2.tab === 'lineal' && isVU);
}

// ── Render principal ──────────────────────────────────────────────────────────
// Tope de la entrada según el mínimo a financiar de la campaña elegida: no se
// puede dejar menos financiado que ese mínimo (precio − bonificación − entrada).
// En Otras Marcas el nivel depende del importe, así que el suelo es el de Básica.
function cv2AjustarTopeEntrada() {
  const slider = document.getElementById('cv2-sl-entrada');
  if (!slider) return;
  const r   = cv2GetRules();
  let min = CV2.marca === 'OTRA' ? CV2_OTRA_NIVELES[0].min : (r.creditoMinimo || 10000);
  let max = Math.max(0, Math.floor((CV2.precio - r.bonificacion - min) / 100) * 100);
  if (CV2.auto && CV2.marca !== 'OTRA') {
    // Automático: la entrada solo la limita la campaña que más deja (las demás se descartan solas)
    cv2ConEstado(() => cv2OpcionesAuto().forEach(o => {
      Object.assign(CV2, { demosRema: false, salones: false }, o.set);
      const ro = cv2GetRules();
      if (!ro.plazosDisp.includes(CV2.meses)) return;
      const mx = Math.max(0, Math.floor((CV2.precio - ro.bonificacion - ro.creditoMinimo) / 100) * 100);
      if (mx > max || (mx === max && ro.creditoMinimo < min)) { max = mx; min = ro.creditoMinimo; }
    }));
  }
  slider.max = max;
  if (CV2.entrada > max) {
    CV2.entrada = max;
    slider.value = max;
    const dispE = document.getElementById('cv2-entrada-input');
    if (dispE) dispE.value = max;
  }
  slider.style.setProperty('--pct', (max > 0 ? (CV2.entrada / max * 100) : 0) + '\%');
  const maxLbl = document.getElementById('cv2-lbl-max');
  if (maxLbl) maxLbl.innerHTML = max > 0 ? `máx. ${cv2Miles(max)} €<span class="cv2-interno"> (mín. a financiar ${cv2Miles(min)} €)</span>` : 'máx. — €';
}

// ── Modo automático: campaña VW con la cuota más baja ────────────────────────
// Candidatas: las campañas a las que puede optar el coche, sin DEMOS + REMA
// (depende de que el coche sea demo o REMA: se elige a mano con su tarjeta).
function cv2OpcionesAuto() {
  if (CV2.marca === 'OTRA') return [];
  const cat = cv2GetRules().categoria;
  const arona = /arona/i.test(CV2.modelo || '');
  return CV2_OPCIONES.filter(o => o.marca === CV2.marca && (!o.arona || arona) && o.id !== 'DEMOS' && (!o.ok || o.ok(cat)));
}

// Ejecuta fn y deja la calculadora como estaba (para simular otras campañas/plazos)
function cv2ConEstado(fn) {
  const g = { campana: CV2.campana, demosRema: CV2.demosRema, salones: CV2.salones, tab: CV2.tab,
              meses: CV2.meses, entrada: CV2.entrada, tinOverride: CV2.tinOverride };
  try { return fn(); } finally { Object.assign(CV2, g); }
}

// Plazos que admite al menos una campaña candidata (pastillas en automático)
function cv2PlazosAuto() {
  const set = new Set();
  cv2ConEstado(() => cv2OpcionesAuto().forEach(o => {
    Object.assign(CV2, { demosRema: false, salones: false }, o.set);
    cv2GetRules().plazosDisp.forEach(p => set.add(p));
  }));
  return CV2_ALL_PLAZOS.filter(p => set.has(p));
}

function cv2ElegirAuto() {
  if (!CV2.auto) return;
  const ops = cv2OpcionesAuto();
  if (!ops.length) return;
  let mejor = null, reserva = null;
  cv2ConEstado(() => ops.forEach(o => {
    Object.assign(CV2, { demosRema: false, salones: false }, o.set, { tinOverride: null });
    const r = cv2GetRules();
    if (!r.plazosDisp.includes(CV2.meses)) return;
    const cuota = cv2Calc().cuota;
    if (CV2.precio - r.bonificacion - CV2.entrada >= r.creditoMinimo) { if (!mejor || cuota < mejor.cuota) mejor = { o, cuota }; }
    else if (!reserva || r.creditoMinimo < reserva.min) reserva = { o, min: r.creditoMinimo };
  }));
  const el = (mejor || reserva || {}).o;
  if (el) { CV2.campana = el.set.campana; CV2.demosRema = false; CV2.salones = !!el.set.salones; }
}

function cv2PrepararAuto() {
  if (!CV2.auto || CV2.marca === 'OTRA') return;
  const union = cv2PlazosAuto();
  if (union.length && !union.includes(CV2.meses)) {
    CV2.meses = union.reduce((a, b) => Math.abs(b - CV2.meses) < Math.abs(a - CV2.meses) ? b : a);
    const d = document.getElementById('cv2-disp-meses'); if (d) d.textContent = CV2.meses + ' meses';
  }
  cv2ElegirAuto();
}

function cv2VolverAuto() {
  CV2.auto = true;
  CV2.demosRema = false;
  cv2Render();
}

function cv2Render() {
  cv2PrepararAuto();
  cv2AjustarTopeEntrada();
  cv2ElegirAuto();   // por si la entrada se ha recortado
  const { precio, entrada, meses, tab, km, marca, campana, mantAnios, cupraTipo } = CV2;
  const res      = cv2Calc();
  const rules    = res.rules;
  const mantInfo = cv2GetMantInfo();
  const cuotaTotal = Math.round((res.cuota + mantInfo.mensual) * 100) / 100;

  cv2UpdateCampanaUI();
  cv2UpdateTinUI(rules);
  cv2UpdatePlazoPills(CV2.auto && CV2.marca !== 'OTRA' ? cv2PlazosAuto() : rules.plazosDisp);
  cv2RenderCampanas(cv2GetRules());   // tras ajustar plazo/campaña, para que el código sea el definitivo
  cv2RenderComparativa();
  cv2RenderMapa();
  cv2RenderInversa();

  // DEMOS + REMA: el botón solo se puede usar en SEAT VS; muestra las condiciones aplicadas
  const drWrap = document.getElementById('cv2-arona-wrap');
  if (drWrap) {
    const puede = marca === 'SEAT' && (rules.categoria === 'VS' || rules.categoria === null);
    drWrap.classList.toggle('visible', puede);
    if (!puede && CV2.demosRema) CV2.demosRema = false;
    const aBtn = document.getElementById('cv2-arona-btn');
    if (aBtn) aBtn.classList.toggle('active', CV2.demosRema);
    const aLbl = document.getElementById('cv2-arona-lbl');
    if (aLbl) aLbl.textContent = CV2.demosRema
      ? 'activo · TIN ' + rules.tinFinal.toFixed(2).replace('.', ',') + '%' + (rules.bonificacion > 0 ? ' · −' + cv2Fmt(rules.bonificacion) + ' €' : '')
      : 'solo si el coche es demo o REMA';
  }

  // SALONES (Arona): botón visible solo en SEAT Arona; muestra las condiciones aplicadas
  const saWrap = document.getElementById('cv2-salones-wrap');
  if (saWrap) {
    const puedeSa = marca === 'SEAT' && /arona/i.test(CV2.modelo || '');
    saWrap.classList.toggle('visible', puedeSa);
    if (!puedeSa && CV2.salones) CV2.salones = false;
    const sBtn = document.getElementById('cv2-salones-btn');
    if (sBtn) sBtn.classList.toggle('active', CV2.salones);
    const sLbl = document.getElementById('cv2-salones-lbl');
    if (sLbl) sLbl.textContent = CV2.salones
      ? 'activo · TIN ' + rules.tinFinal.toFixed(2).replace('.', ',') + '%' + (rules.bonificacion > 0 ? ' · −' + cv2Fmt(rules.bonificacion) + ' €' : '')
        + ' · ENTRY = TIN bajo / GAMA = bonificación'
      : 'campaña Salones VO para Arona';
  }

  // FLEX tab disabled si VU
  const flexTab = document.getElementById('cv2-tab-flex');
  if (rules.categoria === 'VU') {
    flexTab.disabled = true;
    if (tab === 'flex') {
      CV2.tab = 'lineal';
      document.getElementById('cv2-tab-lineal').classList.add('active');
      flexTab.classList.remove('active');
      document.getElementById('cv2-field-km').style.display = 'none';
    }
  } else {
    flexTab.disabled = false;
  }

  // Categoria badge (car bar)
  const catEl = document.getElementById('cv2-cat-badge');
  if (rules.categoria) {
    const catNames = { VS:'VS · '+rules.antigMeses+'m', VO:'VO · '+rules.antigMeses+'m', VU:'VU · '+rules.antigMeses+'m' };
    catEl.textContent = catNames[rules.categoria];
    catEl.className   = 'cv2-cat-badge ' + rules.categoria.toLowerCase();
  } else {
    catEl.textContent = '';
    catEl.className   = 'cv2-cat-badge';
  }

  // ── Mantenimiento UI ──────────────────────────────────────────────────────
  const mantKey  = cv2GetMantKey();
  const mantTbl  = mantKey ? CV2_MANT[mantKey] : null;
  const isVU     = rules.categoria === 'VU';
  const mantAvail = !!mantTbl && !isVU;

  if (!mantAvail) CV2.mantAnios = 0;

  const showCupraTipo = marca === 'CUPRA' && campana !== 'APPROVED';
  const cupraTipoWrap = document.getElementById('cv2-cupra-tipo-wrap');
  if (cupraTipoWrap) cupraTipoWrap.style.display = showCupraTipo ? 'block' : 'none';
  const ctTerm = document.getElementById('cv2-ct-termico');
  const ctElec = document.getElementById('cv2-ct-electrico');
  if (ctTerm) ctTerm.classList.toggle('active', cupraTipo === 'TERMICO');
  if (ctElec) ctElec.classList.toggle('active', cupraTipo === 'ELECTRICO');

  const isApprovedFixed = marca === 'CUPRA' && campana === 'APPROVED' && mantAvail;

  // APPROVED free badge
  const mantBadge = document.getElementById('cv2-mant-badge');
  if (mantBadge) mantBadge.classList.toggle('visible', isApprovedFixed && CV2.mantAnios === 2);

  if (!isApprovedFixed && mantAvail && mantTbl) {
    const p0 = document.getElementById('cv2-mt-0');
    const p2 = document.getElementById('cv2-mt-2');
    const p4 = document.getElementById('cv2-mt-4');
    if (p2) { p2.style.display = ''; p2.textContent = mantTbl[2] === 0 ? '2 años · GRATIS' : `2 años · ${cv2Fmt(mantTbl[2])} €`; }
    if (p4) { p4.textContent = mantTbl[4] != null ? `4 años · ${cv2Fmt(mantTbl[4])} €` : '4 años'; p4.disabled = mantTbl[4] == null; p4.style.opacity = p4.disabled ? '0.3' : ''; p4.style.pointerEvents = p4.disabled ? 'none' : ''; }
    if (p0) p0.style.display = mantTbl.mandatory ? 'none' : '';
  } else if (isApprovedFixed) {
    const p0 = document.getElementById('cv2-mt-0');
    const p2 = document.getElementById('cv2-mt-2');
    const p4 = document.getElementById('cv2-mt-4');
    if (p2) p2.style.display = 'none';
    if (p0) p0.style.display = 'none';
    if (p4) { p4.textContent = `4 años · ${cv2Fmt(CV2_MANT.CUPRA_APPROVED[4])} € (ampliar)`; p4.disabled = false; p4.style.opacity = ''; p4.style.pointerEvents = ''; }
  }

  [0, 2, 4].forEach(v => {
    const el2 = document.getElementById('cv2-mt-' + v);
    if (el2) el2.classList.toggle('active', v === CV2.mantAnios);
  });

  const mantUnavail = document.getElementById('cv2-mant-unavail');
  if (mantUnavail) mantUnavail.classList.toggle('visible', !mantAvail);

  const mantInfoEl = document.getElementById('cv2-mant-info');
  const dispMant   = document.getElementById('cv2-disp-mant');
  if (!isApprovedFixed && mantInfo.precioTotal > 0) {
    if (mantInfoEl) { mantInfoEl.classList.add('visible'); mantInfoEl.innerHTML = `<strong style="color:#F59E0B">${cv2Fmt2(mantInfo.mensual)} €/mes</strong> durante ${CV2.meses} meses · Total: ${cv2Fmt2(mantInfo.precioTotal)} €`; }
    if (dispMant) dispMant.textContent = `+${cv2Fmt2(mantInfo.mensual)} €/mes`;
  } else if (isApprovedFixed && CV2.mantAnios === 2) {
    if (mantInfoEl) mantInfoEl.classList.remove('visible');
    if (dispMant) dispMant.textContent = '✓ 2 años gratis';
  } else {
    if (mantInfoEl) mantInfoEl.classList.remove('visible');
    if (dispMant) dispMant.textContent = '';
  }

  // Cuota hero label
  const heroLbl = document.getElementById('cv2-cuota-lbl');
  if (heroLbl) heroLbl.textContent = mantInfo.mensual > 0 ? 'Cuota total (financiación + mantenimiento)' : 'Cuota mensual estimada';

  // Hero cuota (flash)
  const cuotaEl = document.getElementById('cv2-cuota-val');
  if (cuotaEl) { cuotaEl.classList.remove('cv2-updating'); void cuotaEl.offsetWidth; cuotaEl.textContent = cv2Fmt2(cuotaTotal); cuotaEl.classList.add('cv2-updating'); }

  // Cuota final FLEX
  const cfRow = document.getElementById('cv2-cuota-final');
  if (cfRow) {
    cfRow.classList.toggle('visible', tab === 'flex' && res.vr > 0);
    const cfLbl = document.getElementById('cv2-cf-lbl');
    const cfVal = document.getElementById('cv2-cf-val');
    if (cfLbl) cfLbl.textContent = 'Cuota final mes ' + CV2.meses;
    if (cfVal) cfVal.textContent = cv2Fmt2(res.vr) + ' €';
  }

  // Info chips
  const chipCat  = document.getElementById('cv2-chip-cat');
  const chipCamp = document.getElementById('cv2-chip-camp');
  const chipTin  = document.getElementById('cv2-chip-tin');
  if (chipCat) {
    if (rules.categoria) {
      chipCat.textContent = rules.categoria + ' · ' + rules.antigMeses + 'm';
      chipCat.style.display = '';
      chipCat.className = 'cv2-chip ' + (rules.categoria === 'VS' ? 'green' : rules.categoria === 'VO' ? 'amber' : '');
    } else {
      chipCat.style.display = 'none';
    }
  }
  if (chipCamp) chipCamp.textContent = rules.campanaLabel;
  if (chipTin)  chipTin.textContent  = 'TIN ' + rules.tinFinal.toFixed(2).replace('.', ',') + '%';

  // Breakdown
  const gId = id => document.getElementById(id);
  if (gId('cv2-br-precio'))   gId('cv2-br-precio').textContent   = cv2Fmt(precio) + ' €';
  if (gId('cv2-br-entrada'))  gId('cv2-br-entrada').textContent  = cv2Fmt(entrada) + ' €';
  if (gId('cv2-br-tin'))      gId('cv2-br-tin').textContent      = rules.tinFinal.toFixed(2).replace('.', ',') + ' %';
  if (gId('cv2-br-ncuotas')) gId('cv2-br-ncuotas').textContent  = CV2.meses;
  const totalConMant = Math.round((res.total + mantInfo.precioTotal) * 100) / 100;
  if (gId('cv2-br-total'))    gId('cv2-br-total').textContent    = cv2Fmt2(totalConMant) + ' €';

  // Mant row
  const mantRow = gId('cv2-br-mant-row');
  if (mantRow) {
    mantRow.classList.toggle('hidden', mantInfo.precioTotal <= 0);
    if (gId('cv2-br-mant-lbl')) gId('cv2-br-mant-lbl').textContent = mantInfo.label;
    if (gId('cv2-br-mant-v'))   gId('cv2-br-mant-v').textContent   = '+' + cv2Fmt2(mantInfo.mensual) + ' €/mes';
  }

  // Bonif row
  const bonifRow = gId('cv2-br-bonif-row');
  if (bonifRow) {
    bonifRow.classList.toggle('hidden', res.bonif <= 0);
    if (gId('cv2-br-bonif')) gId('cv2-br-bonif').textContent = '−' + cv2Fmt(res.bonif) + ' €';
  }

  // Crédito mínimo warning
  const importeFinanciado = Math.max(0, res.precioEf - entrada);
  const warnEl = gId('cv2-credit-warn');
  if (warnEl) {
    if (rules.creditoMinimo > 0 && importeFinanciado < rules.creditoMinimo) {
      warnEl.classList.add('visible');
      warnEl.textContent = '⚠ Importe financiado (' + cv2Fmt(importeFinanciado) + ' €) inferior al mínimo de la campaña ' + rules.campanaLabel + ' (' + cv2Fmt(rules.creditoMinimo) + ' €). Consulta condiciones con ' + ASESOR.nombreCorto + '.';
    } else {
      warnEl.classList.remove('visible');
    }
  }

  // Texto legal
  const modeStr2 = tab === 'lineal' ? 'francés' : 'francés con cuota final';
  let legalTxt = `Ejemplo de cuota a ${CV2.meses} meses: ${cv2Fmt2(res.cuota)} €`;
  if (tab === 'flex' && res.vr > 0) {
    const anos = Math.round(CV2.meses / 12);
    legalTxt += `, y si lo deseas, al cabo de ${anos} año${anos !== 1 ? 's' : ''} podrás cambiarlo, devolverlo o quedártelo pagando una cuota final en el mes ${CV2.meses} de ${cv2Fmt2(res.vr)} € (calculada con ${Math.round(km/1000)}.000 km anuales)`;
  }
  legalTxt += `. Campaña: ${rules.campanaLabel}. `;
  if (res.bonif > 0) legalTxt += `Bonificación VWFS: ${cv2Fmt(res.bonif)} €. `;
  legalTxt += `Entrada inicial: ${cv2Fmt(entrada)} €. Seguro de Protección Plus opcional y financiado: ${cv2Fmt2(res.seg)} €. Comisión de apertura financiada: ${cv2Fmt2(res.comision)} €. Importe total financiado: ${cv2Fmt2(res.capital)} €. TIN ${rules.tinFinal.toFixed(2).replace('.', ',')}\%. Precio total a plazos: ${cv2Fmt2(res.total)} €. Sistema de amortización ${modeStr2}. `;
  if (mantInfo.precioTotal > 0) {
    legalTxt += `${mantInfo.label}: ${cv2Fmt2(mantInfo.precioTotal)} € (${cv2Fmt2(mantInfo.mensual)} €/mes dividido en ${CV2.meses} cuotas). Cuota total mensual incluyendo mantenimiento: ${cv2Fmt2(cuotaTotal)} €. `;
  }
  legalTxt += `Condiciones exactas con ${ASESOR.nombreCorto} · ${ASESOR.telefonoDisplay}.`;
  const legalEl = gId('cv2-legal');
  if (legalEl) legalEl.textContent = legalTxt;

  // WhatsApp link
  cv2BuildWaLink(res, rules, mantInfo, cuotaTotal);
}

// ── WhatsApp mensaje ──────────────────────────────────────────────────────────
function cv2BuildWaLink(res, rules, mantInfo, cuotaTotal) {
  const { precio, entrada, marca, tab } = CV2;
  const modeStr = tab === 'lineal' ? 'LINEAL' : 'FLEX';
  const modeloStr = CV2.modelo || 'el vehículo';
  let msg = `🚗 *Simulación Financiación — ${modeloStr}*\n`;
  msg += `━━━━━━━━━━━━━━━\n`;
  msg += `Marca: *${marca}*${rules.categoria ? ' · ' + rules.categoria : ''}\n`;
  msg += `Campaña: *${rules.campanaLabel}*\n`;
  msg += `Precio al contado: *${cv2Fmt(precio)} €*\n`;
  if (res.bonif > 0) msg += `Bonificación VWFS: *−${cv2Fmt(res.bonif)} €*\n`;
  msg += `Entrada inicial: *${cv2Fmt(entrada)} €*\n`;
  msg += `Modalidad: *${modeStr}*\n`;
  msg += `Plazo: *${CV2.meses} meses*\n`;
  msg += `TIN: *${rules.tinFinal.toFixed(2).replace('.', ',')}\%*\n`;
  msg += `Seguro Protección Plus: *${cv2Fmt2(res.seg)} €*\n`;
  msg += `Comisión apertura (2,99\%): *${cv2Fmt2(res.comision)} €*\n`;
  msg += `Importe financiado: *${cv2Fmt2(res.capital)} €*\n`;
  msg += `━━━━━━━━━━━━━━━\n`;
  msg += `📅 *Cuota financiación: ${cv2Fmt2(res.cuota)} €/mes*\n`;
  if (tab === 'flex' && res.vr > 0) msg += `🔑 Cuota final mes ${CV2.meses}: *${cv2Fmt2(res.vr)} €*\n`;
  if (mantInfo && mantInfo.precioTotal > 0) {
    msg += `🔧 ${mantInfo.label}: *+${cv2Fmt2(mantInfo.mensual)} €/mes* (${cv2Fmt2(mantInfo.precioTotal)} € total)\n`;
    msg += `📅 *CUOTA TOTAL: ${cv2Fmt2(cuotaTotal)} €/mes*\n`;
  }
  const totalConMant = Math.round(((res.total || 0) + (mantInfo ? mantInfo.precioTotal : 0)) * 100) / 100;
  msg += `💰 Total a plazos: *${cv2Fmt2(totalConMant)} €*\n`;
  msg += `━━━━━━━━━━━━━━━\n`;
  msg += `_Cálculo orientativo. Condiciones exactas con ${ASESOR.nombreCorto} · ${ASESOR.telefonoDisplay}_`;
  const waEl = document.getElementById('cv2-btn-wa');
  if (waEl) waEl.href = `https://wa.me/${ASESOR.telefonoWa}?text=${encodeURIComponent(msg)}`;
}

// ── Handlers de usuario ───────────────────────────────────────────────────────
function cv2SetMode(m) {
  if (m === 'flex') {
    const rules = cv2GetRules();
    if (rules.categoria === 'VU') return;
    if (CV2.marca === 'OTRA') return;
  }
  CV2.tab = m;
  document.getElementById('cv2-tab-lineal').classList.toggle('active', m === 'lineal');
  document.getElementById('cv2-tab-flex').classList.toggle('active', m === 'flex');
  document.getElementById('cv2-field-km').style.display = m === 'flex' ? 'block' : 'none';
  cv2Render();
}

function cv2SetCampana(c) {
  CV2.campana = c;
  CV2.tinOverride = null;
  if (CV2.marca === 'CUPRA') {
    if (CV2.mantAnios === 0) CV2.mantAnios = 2;
    if (c === 'APPROVED' && CV2.mantAnios === 4) CV2.mantAnios = 2;
  }
  const manualWrap = document.getElementById('cv2-tin-manual');
  if (manualWrap) manualWrap.classList.remove('visible');
  const tinBtn = document.getElementById('cv2-tin-btn');
  if (tinBtn) tinBtn.textContent = '✎ personalizar TIN';
  cv2Render();
}

function cv2SetMeses(m) {
  CV2.meses = m;
  CV2_ALL_PLAZOS.forEach(p => {
    const el = document.getElementById('cv2-pl-' + p);
    if (el) el.classList.toggle('active', p === m);
  });
  const dispMeses = document.getElementById('cv2-disp-meses');
  if (dispMeses) dispMeses.textContent = m + ' meses';
  cv2Render();
}

function cv2SetKm(k) {
  CV2.km = k;
  document.querySelectorAll('#cv2-pills-km .cv2-pill').forEach((el, i) => {
    el.classList.toggle('active', [10000,15000,20000,25000,30000][i] === k);
  });
  const dispKm = document.getElementById('cv2-disp-km');
  if (dispKm) dispKm.textContent = k.toLocaleString('es-ES') + ' km';
  cv2Render();
}

function cv2SetMant(n) {
  CV2.mantAnios = n;
  [0,2,4].forEach(v => {
    const el = document.getElementById('cv2-mt-' + v);
    if (el) el.classList.toggle('active', v === n);
  });
  cv2Render();
}

function cv2SetCupraTipo(t) {
  CV2.cupraTipo = t;
  cv2Render();
}

function cv2ToggleSalones() {
  CV2.salones = !CV2.salones;
  if (CV2.salones) CV2.demosRema = false;   // no se combinan
  cv2Render();
}

function cv2ToggleDemosRema() {
  CV2.demosRema = !CV2.demosRema;
  if (CV2.demosRema) CV2.salones = false;
  cv2Render();
}

function cv2SliderMove(val) {
  const slider = document.getElementById('cv2-sl-entrada');
  const eur = parseInt(val) || 0;
  const max = parseInt(slider.max) || 1;
  const pct = max > 0 ? (eur / max * 100) : 0;
  slider.style.setProperty('--pct', pct + '\%');
  CV2.entrada = eur;
  const dispE = document.getElementById('cv2-entrada-input');
  if (dispE) dispE.value = eur;
  cv2Render();
}

function cv2EntradaInput(val) {
  const slider = document.getElementById('cv2-sl-entrada');
  const max = parseInt(slider.max) || 0;
  let eur = parseInt(val) || 0;
  if (eur < 0) eur = 0;
  if (eur > max) eur = max;
  CV2.entrada = eur;
  slider.value = eur;
  slider.style.setProperty('--pct', (max > 0 ? (eur / max * 100) : 0) + '\%');
  cv2Render();
}

function cv2ToggleTin() {
  const manualWrap = document.getElementById('cv2-tin-manual');
  const btn = document.getElementById('cv2-tin-btn');
  const restore = document.getElementById('cv2-tin-restore');
  if (manualWrap.classList.contains('visible')) {
    manualWrap.classList.remove('visible');
    if (restore) restore.style.display = 'none';
    if (btn) btn.textContent = '✎ personalizar TIN';
    CV2.tinOverride = null;
    cv2Render();
  } else {
    manualWrap.classList.add('visible');
    if (restore) restore.style.display = '';
    if (btn) btn.textContent = '✕ cerrar personalización';
    const rules = cv2GetRules();
    const inp = document.getElementById('cv2-tin-input');
    if (inp) inp.value = rules.tin_auto.toFixed(2);
    CV2.tinOverride = rules.tin_auto;
    cv2Render();
  }
}

function cv2TinInput(val) {
  const v = parseFloat(val);
  if (!isNaN(v) && v >= 0 && v <= 30) { CV2.tinOverride = v; cv2Render(); }
}

function cv2RestoreTin() {
  CV2.tinOverride = null;
  const manualWrap = document.getElementById('cv2-tin-manual');
  const btn = document.getElementById('cv2-tin-btn');
  const restore = document.getElementById('cv2-tin-restore');
  if (manualWrap) manualWrap.classList.remove('visible');
  if (restore) restore.style.display = 'none';
  if (btn) btn.textContent = '✎ personalizar TIN';
  cv2Render();
}

// ── Bootstrap por coche ───────────────────────────────────────────────────────

function initCalc(c) {
  const precio = typeof c.precio === 'number' ? c.precio : (parseInt(String(c.precio||'0').replace(/[^\d]/g,''))||0);
  CV2.precio   = precio;
  CV2.entrada  = 0;
  CV2.km       = 15000;
  CV2.tab      = 'lineal';
  CV2.tinOverride = null;
  CV2.modelo   = ((c.modelo||'') + ' ' + (c.version||'')).trim();
  CV2.demosRema = false;  // siempre empieza desactivado
  CV2.salones = false;
  CV2.auto = true;        // empieza eligiendo sola la campaña VW más barata

  // Auto-detect marca
  const modeloStr = c.modelo || '';
  if (modeloStr.includes('CUPRA')) {
    CV2.marca   = 'CUPRA';
    CV2.campana = 'GAMA';
    CV2.mantAnios = 2;
  } else if (modeloStr.includes('SEAT')) {
    CV2.marca   = 'SEAT';
    CV2.campana = 'ENTRY';
    CV2.mantAnios = 2;
  } else {
    CV2.marca   = 'OTRA';
    CV2.campana = 'GAMA';
    CV2.mantAnios = 0;
  }

  // Auto-detect cupraTipo
  const comb = (c.combustible||'').toLowerCase();
  CV2.cupraTipo = /el[eé]ctric/.test(comb) ? 'ELECTRICO' : 'TERMICO';

  // Auto-detect fecha matrícula desde fin_fecha_iso ("YYYY-MM")
  CV2.matriculaMes  = null;
  CV2.matriculaAnio = null;
  if (c.fin_fecha_iso && c.fin_fecha_iso.includes('-')) {
    const parts = c.fin_fecha_iso.split('-').map(Number);
    if (parts.length === 2 && parts[0] >= 2000) {
      CV2.matriculaAnio = parts[0];
      CV2.matriculaMes  = parts[1];
    }
  }

  // Car bar
  const modeloEl = document.getElementById('cv2-modelo');
  const precioEl = document.getElementById('cv2-precio');
  if (modeloEl) modeloEl.textContent = c.modelo || '—';
  if (precioEl) precioEl.textContent = Number(precio).toLocaleString('es-ES') + ' €';

  // Slider entrada
  const slider = document.getElementById('cv2-sl-entrada');
  const maxEntrada = Math.max(0, Math.floor((precio - 10000) / 100) * 100);
  slider.min   = 0;
  slider.max   = maxEntrada;
  slider.step  = 100;
  slider.value = 0;
  slider.style.setProperty('--pct', '0\%');
  const dispE = document.getElementById('cv2-entrada-input');
  if (dispE) dispE.value = 0;
  const maxLbl = document.getElementById('cv2-lbl-max');
  if (maxLbl) maxLbl.textContent = maxEntrada > 0 ? `máx. ${Number(maxEntrada).toLocaleString('es-ES')} €` : 'máx. — €';

  // Plazo por defecto: 60m si disponible
  const rules0 = cv2GetRules();
  const pd0    = rules0.plazosDisp;
  CV2.meses    = pd0.includes(60) ? 60 : pd0.includes(48) ? 48 : (pd0[pd0.length-1] || 60);
  const dispM  = document.getElementById('cv2-disp-meses');
  if (dispM) dispM.textContent = CV2.meses + ' meses';

  // km display
  const dispKm = document.getElementById('cv2-disp-km');
  if (dispKm) dispKm.textContent = '15.000 km';

  // Botón DEMOS + REMA: su visibilidad (solo SEAT VS) la gestiona cv2Render()

  // FLEX tab: hide km row initially (lineal mode)
  const kmRow = document.getElementById('cv2-field-km');
  if (kmRow) kmRow.style.display = 'none';

  // Tab UI reset
  const tabLin = document.getElementById('cv2-tab-lineal');
  const tabFlex = document.getElementById('cv2-tab-flex');
  if (tabLin) { tabLin.classList.add('active'); }
  if (tabFlex) { tabFlex.classList.remove('active'); tabFlex.disabled = false; }

  // TIN manual reset
  const manualWrap = document.getElementById('cv2-tin-manual');
  const tinBtn     = document.getElementById('cv2-tin-btn');
  const tinRestore = document.getElementById('cv2-tin-restore');
  if (manualWrap) manualWrap.classList.remove('visible');
  if (tinBtn) tinBtn.textContent = '✎ personalizar TIN';
  if (tinRestore) tinRestore.style.display = 'none';

  cv2Render();
}


function goSlide(i) {
  if (!fotosModal.length) return;
  slideActual = (i + fotosModal.length) % fotosModal.length;
  slides.style.transform = `translateX(${-slideActual * 100}%)`;
  dotsEl.querySelectorAll('.gallery-dot').forEach((d,idx) =>
    d.classList.toggle('active', idx === slideActual));
}

const slides   = document.getElementById('gallery-slides');
const dotsEl   = document.getElementById('gallery-dots');
const prevBtn  = document.getElementById('gallery-prev');
const nextBtn  = document.getElementById('gallery-next');
let fotosModal = [];
let slideActual = 0;

let touchStartX = 0;
slides.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; }, {passive:true});
slides.addEventListener('touchend', e => {
  const dx = e.changedTouches[0].clientX - touchStartX;
  if (Math.abs(dx) > 50) goSlide(slideActual + (dx < 0 ? 1 : -1));
});

// Rellena la ficha con los datos del único coche embebido en la página (COCHE).
// Si el coche está Retirado (vendido), oculta precio/CTA y muestra el aviso.
function cargarFicha(c) {
  fotosModal = c.fotos.length ? c.fotos : [];
  slideActual = 0;

  slides.innerHTML = fotosModal.length
    ? fotosModal.map((f,i) => `<div class="gallery-slide"><img src="${f}" alt="Foto ${i+1}" ${i === 0 ? 'fetchpriority="high"' : 'loading="lazy"'}></div>`).join('')
    : `<div class="gallery-slide" style="display:grid;place-items:center;color:var(--muted);width:100%;height:100%">Sin fotos</div>`;
  slides.style.transform = 'translateX(0)';

  dotsEl.innerHTML = fotosModal.length > 1
    ? fotosModal.map((_,i) => `<div class="gallery-dot ${i===0?'active':''}" data-i="${i}"></div>`).join('') : '';
  dotsEl.querySelectorAll('.gallery-dot').forEach(d =>
    d.addEventListener('click', () => goSlide(+d.dataset.i)));

  const showNav = fotosModal.length > 1;
  prevBtn.style.display = showNav ? '' : 'none';
  nextBtn.style.display = showNav ? '' : 'none';

  const idioma = (window.rdIdiomaActual ? window.rdIdiomaActual() : 'es');
  const en = idioma === 'en';
  const de = idioma === 'de';
  // Texto del coche en el idioma actual: el alemán (campo *_de) cae al inglés si falta.
  const tr = (es, eng, ger) => en ? (eng || es) : de ? (ger || eng || es) : es;

  document.getElementById('m-modelo').textContent = c.modelo;
  document.getElementById('m-version').textContent = tr(c.version, c.version_en, c.version_de);

  const specsLabelsEn = { 'Combustible': 'Fuel', 'Kilómetros': 'Mileage', 'Matrícula': 'Registered', 'Cambio': 'Gearbox', 'Color': 'Color', 'Ubicación': 'Location' };
  const specsLabelsDe = { 'Combustible': 'Kraftstoff', 'Kilómetros': 'Kilometerstand', 'Matrícula': 'Erstzulassung', 'Cambio': 'Getriebe', 'Color': 'Farbe', 'Ubicación': 'Standort' };
  const combustibleEn = { 'Gasolina': 'Petrol', 'Diésel': 'Diesel', 'Híbrido': 'Hybrid', 'Eléctrico': 'Electric' };
  const combustibleDe = { 'Gasolina': 'Benzin', 'Diésel': 'Diesel', 'Híbrido': 'Hybrid', 'Eléctrico': 'Elektro' };
  const cambioEn = { 'Manual': 'Manual', 'Automático': 'Automatic' };
  const cambioDe = { 'Manual': 'Schaltgetriebe', 'Automático': 'Automatik' };
  const specs = [
    ['Combustible', tr(c.combustible, combustibleEn[c.combustible], combustibleDe[c.combustible])],
    ['Kilómetros', c.km + ' km'],
    ['Matrícula', c.fecha],
    ['Cambio', tr(c.cambio, cambioEn[c.cambio], cambioDe[c.cambio])],
    ['Color', tr(c.color, c.color_en, c.color_de)],
    ['Ubicación', c.ubicacion],
  ].filter(([,v]) => v);
  document.getElementById('m-specs').innerHTML = specs.map(([l,v]) =>
    `<div class="rd-spec-badge"><div class="lbl">${tr(l, specsLabelsEn[l], specsLabelsDe[l])}</div><div class="val">${v}</div></div>`).join('');

  const nEquip = (c.equipamiento || []).length;
  const equip = (de && c.equipamiento_de && c.equipamiento_de.length === nEquip) ? c.equipamiento_de
    : ((en || de) && c.equipamiento_en && c.equipamiento_en.length === nEquip) ? c.equipamiento_en
    : (c.equipamiento || []);
  const equipSection = document.getElementById('equip-section');
  if (equip.length) {
    document.getElementById('m-equip').innerHTML = equip.map(e =>
      `<div class="equip-item"><span class="equip-check">✓</span><span>${e}</span></div>`).join('');
    equipSection.style.display = '';
  } else { equipSection.style.display = 'none'; }

  if (c.vendido) {
    document.getElementById('m-precio').textContent = '';
    document.getElementById('m-precio-sticky').textContent = '';
    const pill = document.getElementById('m-estado-pill');
    pill.textContent = tr('🚫 Vendido', '🚫 Sold', '🚫 Verkauft');
    pill.classList.add('reservado');
    document.getElementById('m-financiacion').style.display = 'none';
    const finTabs = document.getElementById('financiera-tabs');
    const bbvaPanel = document.getElementById('bbva-financiacion');
    if (finTabs) finTabs.style.display = 'none';
    if (bbvaPanel) bbvaPanel.style.display = 'none';
    const caixaPanel = document.getElementById('caixa-financiacion');
    if (caixaPanel) caixaPanel.style.display = 'none';
    document.getElementById('m-vendido-banner').style.display = '';
    document.getElementById('m-vendido-sticky').style.display = 'flex';
    document.getElementById('m-sticky-financiacion').style.display = 'none';
    return;
  }

  document.getElementById('m-precio').textContent = c.precio + ' €';
  document.getElementById('m-precio-sticky').textContent = c.precio + ' €';
  const pill = document.getElementById('m-estado-pill');
  const reservado = esReservado(c.estado);
  pill.textContent = reservado ? tr('🟠 Reservado', '🟠 Reserved', '🟠 Reserviert') : tr('✅ Disponible', '✅ Available', '✅ Verfügbar');
  pill.classList.add(reservado ? 'reservado' : 'disponible');

  initCalc(c);
  bbvaRender();
  caixaRender();

  const link = document.getElementById('m-link');
  if (c.url) { link.href = c.url; link.style.display = ''; } else { link.style.display = 'none'; }
}

prevBtn.addEventListener('click', () => goSlide(slideActual - 1));
nextBtn.addEventListener('click', () => goSlide(slideActual + 1));

// ── BBVA — Préstamo Vehículo Nuevo/Seminuevo, TIN 5,75% fijo (Zona 1032 R3) ──
// Fuente: "VN - VSN PACK 1032 R-3" (Tarifa N.21.ST.1032), fila 1 T.I.N. 5,75%,
// "Coef. con Seg. PPP". Coeficiente = cuota mensual por cada 1€ financiado (ya
// incluye comisión de apertura 3,95% y seguro PPP). Cuota = coef × (precio - entrada).
const BBVA_COEF = {
  24:  0.046614,
  36:  0.032219,
  48:  0.025071,
  60:  0.020828,
  72:  0.018042,
  84:  0.016092,
  96:  0.014670,
  108: 0.013605,
  120: 0.012796,
};
// ── BBVA — Préstamo Vehículo Usado (más de 72 meses), TIN 7,99% fijo ──
// Fuente: "VO PACK 1032 R-3" (Tarifa U.21.ST.1032), fila 1 T.I.N. 7,99%,
// "Coef. con Seg. PPP". Plazo máximo 96 meses.
const BBVA_COEF_VO = {
  24: 0.047684,
  36: 0.033306,
  48: 0.026184,
  60: 0.021971,
  72: 0.019218,
  84: 0.017305,
  96: 0.015923,
};
const BBVA_PLAZOS = [24, 36, 48, 60, 72, 84, 96, 108, 120];
const BBVA = { meses: 60, entrada: 0 };

// Tarifa y plazo máximo según antigüedad (tabla "Antigüedad / Plazo máximo" de BBVA):
// hasta 60 meses → 120 cuotas; 61-72 meses → 108 cuotas (tarifa VN-VSN);
// más de 72 meses → tarifa VO, máximo 96 cuotas. Sin fecha → VN-VSN, 120.
function bbvaTarifa() {
  let antig = null;
  if (CV2.matriculaMes && CV2.matriculaAnio && CV2.matriculaAnio >= 2000) {
    const now = new Date();
    antig = Math.max(0, (now.getFullYear() - CV2.matriculaAnio) * 12 + (now.getMonth() + 1 - CV2.matriculaMes));
  }
  if (antig !== null && antig > 72) return { antig, vo: true,  tin: '7,99', coef: BBVA_COEF_VO, max: 96 };
  if (antig !== null && antig > 60) return { antig, vo: false, tin: '5,75', coef: BBVA_COEF,    max: 108 };
  return { antig, vo: false, tin: '5,75', coef: BBVA_COEF, max: 120 };
}

function bbvaFmt(n) { return Math.round(n).toLocaleString('es-ES'); }
function bbvaFmt2(n) { return n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

function bbvaRender() {
  const precio = CV2.precio || 0;
  const maxEntrada = Math.max(0, Math.floor((precio - 500) / 100) * 100);
  BBVA.entrada = Math.min(Math.max(0, BBVA.entrada), maxEntrada);

  const slider = document.getElementById('bbva-sl-entrada');
  if (!slider) return; // panel BBVA no presente en esta página
  slider.min = 0; slider.max = maxEntrada; slider.step = 100; slider.value = BBVA.entrada;
  slider.style.setProperty('--pct', (maxEntrada > 0 ? (BBVA.entrada / maxEntrada * 100) : 0) + '\%');
  const entradaInput = document.getElementById('bbva-entrada-input');
  if (entradaInput) entradaInput.value = BBVA.entrada;
  const lblMax = document.getElementById('bbva-lbl-max');
  if (lblMax) lblMax.textContent = maxEntrada > 0 ? ('máx. ' + bbvaFmt(maxEntrada) + ' €') : 'máx. — €';

  const tarifa = bbvaTarifa();
  if (BBVA.meses > tarifa.max) BBVA.meses = tarifa.max;

  BBVA_PLAZOS.forEach(p => {
    const el = document.getElementById('bbva-pl-' + p);
    if (!el) return;
    el.style.display = p > tarifa.max ? 'none' : '';
    el.classList.toggle('active', p === BBVA.meses);
  });
  const dispMeses = document.getElementById('bbva-disp-meses');
  if (dispMeses) dispMeses.textContent = BBVA.meses + ' meses';

  // TIN visible (pastilla + fila del desglose) y subtítulo según la tarifa aplicada
  const tinPill = document.querySelector('#bbva-financiacion .bbva-tin-pill');
  if (tinPill) tinPill.innerHTML = tarifa.tin + '<span>% TIN</span>';
  document.querySelectorAll('#bbva-financiacion .bbva-br-row').forEach(row => {
    const s = row.querySelectorAll('span');
    if (s.length === 2 && s[0].textContent.trim() === 'T.I.N.') s[1].textContent = tarifa.tin + ' %';
  });
  const barSub = document.querySelector('#bbva-financiacion .bbva-bar-sub');
  if (barSub) barSub.textContent = tarifa.vo
    ? 'Vehículo usado · más de 72 meses de antigüedad'
    : 'Nuevo / Seminuevo hasta 72 meses de antigüedad';

  // Aviso de plazo limitado por antigüedad (se crea bajo las pastillas de plazo)
  const pills = document.getElementById('bbva-pills-meses');
  let aviso = document.getElementById('bbva-aviso-plazo');
  if (pills && !aviso) {
    aviso = document.createElement('div');
    aviso.id = 'bbva-aviso-plazo';
    aviso.style.cssText = 'font-size:11px;line-height:1.5;color:#f5b041;margin-top:8px;';
    pills.insertAdjacentElement('afterend', aviso);
  }
  if (aviso) {
    aviso.textContent = tarifa.vo
      ? `Vehículo con ${tarifa.antig} meses de antigüedad: se aplica la tarifa BBVA de vehículo usado (TIN 7,99%), plazo máximo 96 meses.`
      : tarifa.max < 120
        ? `Vehículo con ${tarifa.antig} meses de antigüedad: BBVA permite un plazo máximo de 108 meses.`
        : '';
    aviso.style.display = aviso.textContent ? '' : 'none';
  }

  const importe = Math.max(0, precio - BBVA.entrada);
  const cuota   = Math.round(tarifa.coef[BBVA.meses] * importe * 100) / 100;
  const total   = Math.round((cuota * BBVA.meses + BBVA.entrada) * 100) / 100;

  const cuotaVal = document.getElementById('bbva-cuota-val');
  if (cuotaVal) cuotaVal.textContent = bbvaFmt2(cuota);
  const brPrecio = document.getElementById('bbva-br-precio');
  if (brPrecio) brPrecio.textContent = bbvaFmt(precio) + ' €';
  const brEntrada = document.getElementById('bbva-br-entrada');
  if (brEntrada) brEntrada.textContent = bbvaFmt(BBVA.entrada) + ' €';
  const brImporte = document.getElementById('bbva-br-importe');
  if (brImporte) brImporte.textContent = bbvaFmt(importe) + ' €';
  const brNcuotas = document.getElementById('bbva-br-ncuotas');
  if (brNcuotas) brNcuotas.textContent = BBVA.meses;
  const brTotal = document.getElementById('bbva-br-total');
  if (brTotal) brTotal.textContent = bbvaFmt2(total) + ' €';

  const modeloEl = document.getElementById('cv2-modelo');
  const modelo = modeloEl && modeloEl.textContent !== '—' ? modeloEl.textContent : 'un vehículo';
  const waBtn = document.getElementById('bbva-btn-wa');
  if (waBtn) {
    const msg = `Hola ${ASESOR.nombreCorto}, te escribo desde la calculadora de financiación. Me interesa ${modelo} de ${bbvaFmt(precio)} € financiado con BBVA a ${BBVA.meses} meses (TIN ${tarifa.tin}%). Cuota estimada: ${bbvaFmt2(cuota)} €/mes.`;
    waBtn.href = 'https://wa.me/' + ASESOR.telefonoWa + '?text=' + encodeURIComponent(msg);
  }

  const legalEl = document.getElementById('bbva-legal');
  if (legalEl) {
    legalEl.textContent =
      `Ejemplo de cuota a ${BBVA.meses} meses: ${bbvaFmt2(cuota)} €. TIN ${tarifa.tin}% fijo. Entrada inicial: ${bbvaFmt(BBVA.entrada)} €. Importe financiado: ${bbvaFmt(importe)} €. Comisión de apertura financiada en la cuota. Precio total a plazos: ${bbvaFmt2(total)} €. Condiciones sujetas a modificación por parte de BBVA. Condiciones exactas con ${ASESOR.nombreCorto} · ${ASESOR.telefonoDisplay}.`;
  }
}

function bbvaSetMeses(m) { BBVA.meses = m; bbvaRender(); }
function bbvaSliderMove(v) { BBVA.entrada = parseFloat(v) || 0; bbvaRender(); }
function bbvaEntradaInput(val) {
  const slider = document.getElementById('bbva-sl-entrada');
  const max = parseInt(slider.max) || 0;
  let eur = parseInt(val) || 0;
  if (eur < 0) eur = 0;
  if (eur > max) eur = max;
  BBVA.entrada = eur;
  slider.value = eur;
  slider.style.setProperty('--pct', (max > 0 ? (eur / max * 100) : 0) + '\%');
  bbvaRender();
}

// ── CaixaBank — Préstamo Vehículo VN y VO, tarifa "COM 07 26 AND" (+0,50% TIN) ──
// Fuente: "Tarifa (+0,50% Tin) COM 07 26 AND V2.pdf", fila RMN · T.I.N. 5,99%, coeficiente
// "PB" (Pack Vida, la tarifa de referencia). Coeficiente = cuota mensual por cada 1€
// financiado: ya incluye los gastos financiados del 3,99% y el seguro Pack Vida.
// Cuota = coef × (precio - entrada). RMN solo tiene plazos de 48 a 120 meses.
// Válida para vehículos de hasta 96 meses de antigüedad; antigüedad + plazo ≤ 156 meses.
const CAIXA_COEF = {
  48:  0.025417,
  60:  0.021099,
  72:  0.018229,
  84:  0.016186,
  96:  0.014661,
  108: 0.013480,
  120: 0.012540,
};
const CAIXA_TIN = '5,99';
const CAIXA_PLAZOS = [24, 36, 48, 60, 72, 84, 96, 108, 120];
const CAIXA = { meses: 60, entrada: 0 };

function caixaTarifa() {
  let antig = null;
  if (CV2.matriculaMes && CV2.matriculaAnio && CV2.matriculaAnio >= 2000) {
    const now = new Date();
    antig = Math.max(0, (now.getFullYear() - CV2.matriculaAnio) * 12 + (now.getMonth() + 1 - CV2.matriculaMes));
  }
  const disponible = antig === null || antig <= 96;
  const plazos = Object.keys(CAIXA_COEF).map(Number)
    .filter(p => antig === null || antig + p <= 156);
  return { antig, disponible: disponible && plazos.length > 0, plazos, max: plazos.length ? plazos[plazos.length - 1] : 0 };
}

function caixaRender() {
  const precio = CV2.precio || 0;
  const maxEntrada = Math.max(0, Math.floor((precio - 500) / 100) * 100);
  CAIXA.entrada = Math.min(Math.max(0, CAIXA.entrada), maxEntrada);

  const slider = document.getElementById('caixa-sl-entrada');
  if (!slider) return; // panel CaixaBank no presente en esta página
  slider.min = 0; slider.max = maxEntrada; slider.step = 100; slider.value = CAIXA.entrada;
  slider.style.setProperty('--pct', (maxEntrada > 0 ? (CAIXA.entrada / maxEntrada * 100) : 0) + '%');
  const entradaInput = document.getElementById('caixa-entrada-input');
  if (entradaInput) entradaInput.value = CAIXA.entrada;
  const lblMax = document.getElementById('caixa-lbl-max');
  if (lblMax) lblMax.textContent = maxEntrada > 0 ? ('máx. ' + bbvaFmt(maxEntrada) + ' €') : 'máx. — €';

  const tarifa = caixaTarifa();
  if (tarifa.disponible && !tarifa.plazos.includes(CAIXA.meses)) {
    CAIXA.meses = tarifa.plazos.includes(60) ? 60 : tarifa.max;
  }
  CAIXA_PLAZOS.forEach(p => {
    const el = document.getElementById('caixa-pl-' + p);
    if (!el) return;
    el.style.display = tarifa.plazos.includes(p) ? '' : 'none';
    el.classList.toggle('active', p === CAIXA.meses);
  });
  const dispMeses = document.getElementById('caixa-disp-meses');
  if (dispMeses) dispMeses.textContent = CAIXA.meses + ' meses';

  // Aviso por antigüedad (se crea bajo las pastillas de plazo)
  const pills = document.getElementById('caixa-pills-meses');
  let aviso = document.getElementById('caixa-aviso-plazo');
  if (pills && !aviso) {
    aviso = document.createElement('div');
    aviso.id = 'caixa-aviso-plazo';
    aviso.style.cssText = 'font-size:11px;line-height:1.5;color:#f5b041;margin-top:8px;';
    pills.insertAdjacentElement('afterend', aviso);
  }
  if (aviso) {
    aviso.textContent = !tarifa.disponible
      ? `Vehículo con ${tarifa.antig} meses de antigüedad: la tarifa CaixaBank solo admite vehículos de hasta 96 meses. Consulta otras opciones con ${ASESOR.nombreCorto}.`
      : tarifa.max < 120
        ? `Vehículo con ${tarifa.antig} meses de antigüedad: CaixaBank permite un plazo máximo de ${tarifa.max} meses (antigüedad + plazo ≤ 156 meses).`
        : '';
    aviso.style.display = aviso.textContent ? '' : 'none';
  }

  const importe = Math.max(0, precio - CAIXA.entrada);
  const coef = tarifa.disponible ? CAIXA_COEF[CAIXA.meses] : 0;
  const cuota = Math.round(coef * importe * 100) / 100;
  const total = Math.round((cuota * CAIXA.meses + CAIXA.entrada) * 100) / 100;

  const set = (id, txt) => { const el = document.getElementById(id); if (el) el.textContent = txt; };
  set('caixa-cuota-val', tarifa.disponible ? bbvaFmt2(cuota) : '—');
  set('caixa-br-precio', bbvaFmt(precio) + ' €');
  set('caixa-br-entrada', bbvaFmt(CAIXA.entrada) + ' €');
  set('caixa-br-importe', bbvaFmt(importe) + ' €');
  set('caixa-br-ncuotas', tarifa.disponible ? CAIXA.meses : '—');
  set('caixa-br-total', tarifa.disponible ? bbvaFmt2(total) + ' €' : '—');

  const modeloEl = document.getElementById('cv2-modelo');
  const modelo = modeloEl && modeloEl.textContent !== '—' ? modeloEl.textContent : 'un vehículo';
  const waBtn = document.getElementById('caixa-btn-wa');
  if (waBtn) {
    const msg = tarifa.disponible
      ? `Hola ${ASESOR.nombreCorto}, te escribo desde la calculadora de financiación. Me interesa ${modelo} de ${bbvaFmt(precio)} € financiado con CaixaBank a ${CAIXA.meses} meses (TIN ${CAIXA_TIN}%). Cuota estimada: ${bbvaFmt2(cuota)} €/mes.`
      : `Hola ${ASESOR.nombreCorto}, te escribo desde la calculadora de financiación. Me interesa ${modelo} de ${bbvaFmt(precio)} € y quiero ver opciones de financiación.`;
    waBtn.href = 'https://wa.me/' + ASESOR.telefonoWa + '?text=' + encodeURIComponent(msg);
  }

  const legalEl = document.getElementById('caixa-legal');
  if (legalEl) {
    legalEl.textContent = tarifa.disponible
      ? `Ejemplo de cuota a ${CAIXA.meses} meses: ${bbvaFmt2(cuota)} €. TIN ${CAIXA_TIN}% fijo. Entrada inicial: ${bbvaFmt(CAIXA.entrada)} €. Importe financiado: ${bbvaFmt(importe)} €. Gastos de formalización (3,99%) y seguro Pack Vida incluidos en la cuota. Precio total a plazos: ${bbvaFmt2(total)} €. Financiación sujeta a aprobación de CaixaBank Payments & Consumer. Condiciones exactas con ${ASESOR.nombreCorto} · ${ASESOR.telefonoDisplay}.`
      : '';
  }
}

function caixaSetMeses(m) { CAIXA.meses = m; caixaRender(); }
function caixaSliderMove(v) { CAIXA.entrada = parseFloat(v) || 0; caixaRender(); }
function caixaEntradaInput(val) {
  const slider = document.getElementById('caixa-sl-entrada');
  const max = parseInt(slider.max) || 0;
  let eur = parseInt(val) || 0;
  if (eur < 0) eur = 0;
  if (eur > max) eur = max;
  CAIXA.entrada = eur;
  slider.value = eur;
  slider.style.setProperty('--pct', (max > 0 ? (eur / max * 100) : 0) + '%');
  caixaRender();
}

function setFinanciera(f, btn) {
  document.querySelectorAll('#financiera-tabs .financiera-tab').forEach(el => el.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const vwfsPanel = document.getElementById('m-financiacion');
  const bbvaPanel = document.getElementById('bbva-financiacion');
  const caixaPanel = document.getElementById('caixa-financiacion');
  if (vwfsPanel) vwfsPanel.style.display = f === 'VWFS' ? '' : 'none';
  if (bbvaPanel) bbvaPanel.style.display = f === 'BBVA' ? '' : 'none';
  if (caixaPanel) caixaPanel.style.display = f === 'CAIXA' ? '' : 'none';
  if (f === 'BBVA') bbvaRender();
  if (f === 'CAIXA') caixaRender();
}
