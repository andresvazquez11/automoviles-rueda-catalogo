/* ══════════════════════════════════════════════════════════════════
   Automóviles Rueda — Motor de calculadora de financiación (compartido)
   Extraído de generar_web.py — condiciones VWFS Agosto 2026.
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
  aronaBB:       false,       // toggle manual — campaña especial Arona BB/REMA
};


const CV2_ALL_PLAZOS = [24, 36, 48, 60, 72, 84, 96];

const CV2_MANT = {
  SEAT:                 { 2: 250,  4: 499, mandatory: false },
  CUPRA_APPROVED:       { 2: 0,    4: 400, mandatory: true  },
  CUPRA_GAMA_TERMICO:   { 2: 350,  4: 750, mandatory: true  },
  CUPRA_GAMA_ELECTRICO: { 2: 100,  4: 450, mandatory: true  },
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
  const maxGlobal  = producto === 'FLEX' ? 120 : 144;

  let plazosDisp = [...CV2_ALL_PLAZOS];
  if (antigMeses !== null) {
    plazosDisp = plazosDisp.filter(p => antigMeses + p <= maxGlobal);
  }

  if (producto === 'FLEX') {
    if (categoria === 'VU') {
      plazosDisp = [];
    } else {
      plazosDisp = plazosDisp.filter(p => p <= 60);
    }
  } else {
    if (categoria === 'VS') { plazosDisp = plazosDisp.filter(p => p <= 96); }
    else if (categoria === 'VO') { plazosDisp = plazosDisp.filter(p => p <= 84); }
    else if (categoria === 'VU') { plazosDisp = plazosDisp.filter(p => p <= 48); }
  }

  let creditoMinimo = 0, bonificacion = 0, tin_auto = 7.50, campanaLabel = '';

  if (marca === 'SEAT') {
    if (campana === 'ENTRY' && categoria !== 'VU') {
      tin_auto = 7.50; bonificacion = 0; creditoMinimo = 10000; campanaLabel = 'ENTRY · SEAT';
      if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 48);
    } else {
      tin_auto = 8.99;
      if (categoria === 'VU') {
        bonificacion = 400; creditoMinimo = 7000; campanaLabel = 'GAMA · SEAT · VU';
        plazosDisp = plazosDisp.filter(p => p <= 48);
      } else if (categoria === 'VO') {
        bonificacion = 750; creditoMinimo = producto === 'LINEAL' ? 9500 : 10000; campanaLabel = 'GAMA · SEAT · VO';
        if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 60 && p <= 84);
      } else {
        bonificacion = 750; creditoMinimo = producto === 'LINEAL' ? 13000 : 10000;
        campanaLabel = categoria ? 'GAMA · SEAT · VS' : 'GAMA · SEAT';
        if (producto === 'LINEAL' && categoria === 'VS') plazosDisp = plazosDisp.filter(p => p >= 60 && p <= 96);
      }
    }
  } else if (marca === 'CUPRA') {
    if (campana === 'APPROVED' && (categoria === 'VS' || categoria === null)) {
      // VWFS Campaña CUPRA VO · Agosto 2026 (pág. 5) + confirmado en vivo en dasweltauto.es: TIN 5,95% (antes 5,50%)
      tin_auto = 5.95; bonificacion = 0;
      creditoMinimo = producto === 'FLEX' ? 13500 : 10000; campanaLabel = 'APPROVED · CUPRA';
      if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 36);
    } else {
      // VWFS Campaña CUPRA VO · Agosto 2026 (pág. 4): bonificación pasó de 1.800€ fijo a escalonada
      // FLEX: 1.300€ · LINEAL: 1.000€ (48-71 meses) / 1.300€ (72-96 meses)
      tin_auto = 8.99;
      bonificacion = producto === 'FLEX' ? 1300 : (CV2.meses >= 72 ? 1300 : 1000);
      creditoMinimo = producto === 'FLEX' ? 16500 : 13500;
      campanaLabel = categoria ? 'GAMA · CUPRA · ' + (categoria || '') : 'GAMA · CUPRA';
      if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 48);
    }
  } else {
    plazosDisp = plazosDisp.filter(p => p >= 48 && p <= 96);
    if (importeNeto >= 20000) { tin_auto = 8.99; bonificacion = 1200; creditoMinimo = 20000; campanaLabel = 'TOP · Otras Marcas'; }
    else if (importeNeto >= 15000) { tin_auto = 8.99; bonificacion = 800;  creditoMinimo = 15000; campanaLabel = 'Premium · Otras Marcas'; }
    else if (importeNeto >= 10000) { tin_auto = 8.99; bonificacion = 400;  creditoMinimo = 10000; campanaLabel = 'Entry · Otras Marcas'; }
    else { tin_auto = 7.50; bonificacion = 0; creditoMinimo = 6000; campanaLabel = 'Básica · Otras Marcas'; }
  }

  // ── Arona BB/REMA override (solo SEAT Arona, activado manualmente) ────────
  if (CV2.aronaBB && CV2.modelo && CV2.modelo.toLowerCase().includes('arona') && marca === 'SEAT') {
    if (campana === 'ENTRY') {
      // ENTRY Arona BB: 1.000€ VS+VO
      if (categoria !== 'VU') bonificacion = 1000;
    } else if (producto === 'FLEX') {
      // GAMA Arona BB FLEX: 2.000€ VS / 1.650€ VO (VWFS Agosto 2026, pág. 8)
      if (categoria === 'VS' || categoria === null) bonificacion = 2000;
      else if (categoria === 'VO') bonificacion = 1650;
    } else {
      // GAMA Arona BB LINEAL: 2.000€ VS / 1.600€ VO (VWFS Agosto 2026, pág. 8)
      if (categoria === 'VS' || categoria === null) bonificacion = 2000;
      else if (categoria === 'VO') bonificacion = 1600;
    }
    campanaLabel = campanaLabel + ' · Arona BB/REMA';
  }

  const tinFinal = CV2.tinOverride !== null ? CV2.tinOverride : tin_auto;
  return { tinFinal, tin_auto, bonificacion, creditoMinimo, campanaLabel, plazosDisp, categoria, antigMeses };
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
  const capital  = Math.round(base * 1.035 * 100) / 100;
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
function cv2Render() {
  const { precio, entrada, meses, tab, km, marca, campana, mantAnios, cupraTipo } = CV2;
  const res      = cv2Calc();
  const rules    = res.rules;
  const mantInfo = cv2GetMantInfo();
  const cuotaTotal = Math.round((res.cuota + mantInfo.mensual) * 100) / 100;

  cv2UpdateCampanaUI();
  cv2UpdateTinUI(rules);
  cv2UpdatePlazoPills(rules.plazosDisp);

  // Arona BB label: actualiza el descuento mostrado si está activo
  if (CV2.aronaBB) {
    const aLbl = document.getElementById('cv2-arona-lbl');
    if (aLbl) {
      const bonifStr = rules.bonificacion > 0 ? '−' + cv2Fmt(rules.bonificacion) + ' €' : '—';
      aLbl.textContent = 'activo · descuento ' + bonifStr;
    }
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
      warnEl.textContent = '⚠ Importe financiado (' + cv2Fmt(importeFinanciado) + ' €) inferior al mínimo de la campaña ' + rules.campanaLabel + ' (' + cv2Fmt(rules.creditoMinimo) + ' €). Consulta condiciones con Andrés.';
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
  legalTxt += `Condiciones exactas con Andrés · 610 02 90 56.`;
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
  msg += `Comisión apertura (3,5\%): *${cv2Fmt2(res.comision)} €*\n`;
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
  msg += `_Cálculo orientativo. Condiciones exactas con Andrés · 610 02 90 56_`;
  const waEl = document.getElementById('cv2-btn-wa');
  if (waEl) waEl.href = `https://wa.me/34610029056?text=${encodeURIComponent(msg)}`;
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

function cv2ToggleAronaBB() {
  CV2.aronaBB = !CV2.aronaBB;
  const btn = document.getElementById('cv2-arona-btn');
  const lbl = document.getElementById('cv2-arona-lbl');
  if (CV2.aronaBB) {
    btn.classList.add('active');
    // Calcular bonificación que aplica según campaña/categoría actual
    const rules = cv2GetRules(); // ya incluye el override activo
    const bonifStr = rules.bonificacion > 0 ? '−' + cv2Fmt(rules.bonificacion) + ' €' : '—';
    if (lbl) lbl.textContent = 'activo · descuento ' + bonifStr;
  } else {
    btn.classList.remove('active');
    if (lbl) lbl.textContent = 'descuento especial inactivo';
  }
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
  CV2.aronaBB  = false;  // siempre empieza desactivado

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

  // Arona BB/REMA toggle — visible solo si es SEAT Arona
  const aronaBBWrap = document.getElementById('cv2-arona-wrap');
  const aronaBBBtn  = document.getElementById('cv2-arona-btn');
  const aronaBBLbl  = document.getElementById('cv2-arona-lbl');
  const isArona = (c.modelo||'').toLowerCase().includes('arona') && (c.modelo||'').toLowerCase().includes('seat');
  if (aronaBBWrap) aronaBBWrap.classList.toggle('visible', isArona);
  if (aronaBBBtn)  aronaBBBtn.classList.remove('active');
  if (aronaBBLbl)  aronaBBLbl.textContent = 'descuento especial inactivo';

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
    ? fotosModal.map((f,i) => `<div class="gallery-slide"><img src="${f}" alt="Foto ${i+1}" loading="lazy"></div>`).join('')
    : `<div class="gallery-slide" style="display:grid;place-items:center;color:var(--muted);width:100%;height:100%">Sin fotos</div>`;
  slides.style.transform = 'translateX(0)';

  dotsEl.innerHTML = fotosModal.length > 1
    ? fotosModal.map((_,i) => `<div class="gallery-dot ${i===0?'active':''}" data-i="${i}"></div>`).join('') : '';
  dotsEl.querySelectorAll('.gallery-dot').forEach(d =>
    d.addEventListener('click', () => goSlide(+d.dataset.i)));

  const showNav = fotosModal.length > 1;
  prevBtn.style.display = showNav ? '' : 'none';
  nextBtn.style.display = showNav ? '' : 'none';

  document.getElementById('m-modelo').textContent = c.modelo;
  document.getElementById('m-version').textContent = c.version;

  const specs = [
    ['Combustible', c.combustible], ['Kilómetros', c.km + ' km'],
    ['Matrícula', c.fecha], ['Cambio', c.cambio],
    ['Color', c.color], ['Ubicación', c.ubicacion],
  ].filter(([,v]) => v);
  document.getElementById('m-specs').innerHTML = specs.map(([l,v]) =>
    `<div class="rd-spec-badge"><div class="lbl">${l}</div><div class="val">${v}</div></div>`).join('');

  const equip = c.equipamiento || [];
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
    pill.textContent = '🚫 Vendido';
    pill.classList.add('reservado');
    document.getElementById('m-financiacion').style.display = 'none';
    const finTabs = document.getElementById('financiera-tabs');
    const bbvaPanel = document.getElementById('bbva-financiacion');
    if (finTabs) finTabs.style.display = 'none';
    if (bbvaPanel) bbvaPanel.style.display = 'none';
    document.getElementById('m-vendido-banner').style.display = '';
    document.getElementById('m-vendido-sticky').style.display = 'flex';
    document.getElementById('m-sticky-financiacion').style.display = 'none';
    return;
  }

  document.getElementById('m-precio').textContent = c.precio + ' €';
  document.getElementById('m-precio-sticky').textContent = c.precio + ' €';
  const pill = document.getElementById('m-estado-pill');
  const reservado = esReservado(c.estado);
  pill.textContent = reservado ? '🟠 Reservado' : '✅ Disponible';
  pill.classList.add(reservado ? 'reservado' : 'disponible');

  initCalc(c);
  bbvaRender();

  const link = document.getElementById('m-link');
  if (c.url) { link.href = c.url; link.style.display = ''; } else { link.style.display = 'none'; }
}

prevBtn.addEventListener('click', () => goSlide(slideActual - 1));
nextBtn.addEventListener('click', () => goSlide(slideActual + 1));

// ── BBVA — Préstamo Vehículo Nuevo/Seminuevo, TIN 5,50% fijo (Zona 1032 R2) ──
// Fuente: SIMULADOR en TARIFA -ZONA 1032 -R2, hoja "VN-VSN" / "Dat VN".
// Coeficiente = cuota mensual por cada 1€ financiado (ya incluye comisión de
// apertura y seguro Vida-PPP). Cuota = coeficiente × (precio - entrada).
const BBVA_COEF = {
  24:  0.0464956463856695,
  36:  0.03209879220957684,
  48:  0.024948740818316117,
  60:  0.0207026547831431,
  72:  0.017912982448589146,
  84:  0.015959816476707085,
  96:  0.014534102300133184,
  108: 0.013465001026338819,
  120: 0.012650941824302054,
};
const BBVA_PLAZOS = [24, 36, 48, 60, 72, 84, 96, 108, 120];
const BBVA = { meses: 60, entrada: 0 };

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

  BBVA_PLAZOS.forEach(p => {
    const el = document.getElementById('bbva-pl-' + p);
    if (el) el.classList.toggle('active', p === BBVA.meses);
  });
  const dispMeses = document.getElementById('bbva-disp-meses');
  if (dispMeses) dispMeses.textContent = BBVA.meses + ' meses';

  const importe = Math.max(0, precio - BBVA.entrada);
  const cuota   = Math.round(BBVA_COEF[BBVA.meses] * importe * 100) / 100;
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
    const msg = `Hola Andrés, te escribo desde la calculadora de financiación. Me interesa ${modelo} de ${bbvaFmt(precio)} € financiado con BBVA a ${BBVA.meses} meses (TIN 5,50%). Cuota estimada: ${bbvaFmt2(cuota)} €/mes.`;
    waBtn.href = 'https://wa.me/34610029056?text=' + encodeURIComponent(msg);
  }

  const legalEl = document.getElementById('bbva-legal');
  if (legalEl) {
    legalEl.textContent =
      `Ejemplo de cuota a ${BBVA.meses} meses: ${bbvaFmt2(cuota)} €. TIN 5,50% fijo. Entrada inicial: ${bbvaFmt(BBVA.entrada)} €. Importe financiado: ${bbvaFmt(importe)} €. Comisión de apertura financiada en la cuota. Precio total a plazos: ${bbvaFmt2(total)} €. Condiciones sujetas a modificación por parte de BBVA. Condiciones exactas con Andrés · 610 02 90 56.`;
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

function setFinanciera(f, btn) {
  document.querySelectorAll('#financiera-tabs .financiera-tab').forEach(el => el.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const vwfsPanel = document.getElementById('m-financiacion');
  const bbvaPanel = document.getElementById('bbva-financiacion');
  if (vwfsPanel) vwfsPanel.style.display = f === 'VWFS' ? '' : 'none';
  if (bbvaPanel) bbvaPanel.style.display = f === 'BBVA' ? '' : 'none';
  if (f === 'BBVA') bbvaRender();
}
