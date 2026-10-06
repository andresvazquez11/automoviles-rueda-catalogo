/* ══════════════════════════════════════════════════════════════════
   Automóviles Rueda — "Imprimir simulación · A4"
   Botón dentro de las calculadoras VWFS y BBVA de cada ficha. Monta una
   hoja A4 (coche + financiación elegida + desglose) con el estado ACTUAL
   de la calculadora y lanza la impresión del navegador.
   Pensada para escala de grises: solo negro, blanco y grises, foto en B/N,
   cifras grandes en Oswald y bordes en lugar de fondos de color.
   Depende de calculadora.js (CV2, cv2Calc, cv2GetMantInfo, BBVA, bbvaTarifa…)
   y de las constantes COCHE y ASESOR de la página.
   ══════════════════════════════════════════════════════════════════ */

(function () {
  const CSS = `
#rd-print-sheet { display: none; }
@media print {
  @page { size: A4 portrait; margin: 11mm 12mm; }
  html, body { background: #fff !important; margin: 0 !important; padding: 0 !important; }
  body > *:not(#rd-print-sheet) { display: none !important; }
  #rd-print-sheet { display: block !important; }
}
#rd-print-sheet, #rd-print-sheet * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.rdp { width: 186mm; height: 274mm; overflow: hidden; display: flex; flex-direction: column;
  font-family: 'Work Sans', Arial, sans-serif; color: #000; font-size: 9pt; line-height: 1.35; background: #fff; }
.rdp-osw { font-family: 'Oswald', 'Arial Narrow', Arial, sans-serif; }

.rdp-head { display: flex; justify-content: space-between; align-items: flex-end;
  border-bottom: 2.5pt solid #000; padding-bottom: 3mm; }
.rdp-marca { font-size: 21pt; font-weight: 700; letter-spacing: .5pt; text-transform: uppercase; line-height: 1; }
.rdp-marca-sub { font-size: 7.5pt; letter-spacing: .6pt; text-transform: uppercase; margin-top: 1.5mm; color: #222; }
.rdp-doc { text-align: right; }
.rdp-doc-tit { font-size: 13pt; font-weight: 600; letter-spacing: 1pt; text-transform: uppercase; line-height: 1.1; }
.rdp-doc-meta { font-size: 8pt; margin-top: 1mm; color: #222; }

.rdp-coche { display: grid; grid-template-columns: 84mm 1fr; gap: 6mm; margin-top: 5mm; }
.rdp-foto { width: 84mm; height: 54mm; border: 1pt solid #000; overflow: hidden; background: #e6e6e6; }
.rdp-foto img { width: 100%; height: 100%; object-fit: cover; display: block; filter: grayscale(1) contrast(1.08); }
.rdp-modelo { font-size: 22pt; font-weight: 700; text-transform: uppercase; line-height: 1.02; }
.rdp-version { font-size: 9pt; margin-top: 1.2mm; color: #111; }
.rdp-precio-row { display: flex; align-items: baseline; justify-content: space-between;
  border-top: 1pt solid #000; border-bottom: 1pt solid #000; margin-top: 3mm; padding: 1.5mm 0; }
.rdp-precio-lbl { font-size: 8pt; font-weight: 700; letter-spacing: .8pt; text-transform: uppercase; }
.rdp-precio { font-size: 20pt; font-weight: 700; line-height: 1; }
.rdp-specs { display: grid; grid-template-columns: 1fr 1fr; column-gap: 4mm; margin-top: 2mm; }
.rdp-spec { display: flex; justify-content: space-between; gap: 2mm; padding: .9mm 0; border-bottom: .5pt solid #999; font-size: 8.3pt; }
.rdp-spec b { font-weight: 600; text-align: right; }
.rdp-spec span { color: #333; white-space: nowrap; }

.rdp-sec { margin-top: 4.5mm; }
.rdp-sec-tit { display: flex; justify-content: space-between; align-items: baseline;
  border-bottom: 1.5pt solid #000; padding-bottom: 1mm; margin-bottom: 3mm; }
.rdp-sec-tit h2 { margin: 0; font-size: 12.5pt; font-weight: 600; letter-spacing: 1pt; text-transform: uppercase; }
.rdp-sec-tit small { font-size: 8.3pt; font-weight: 600; }

.rdp-fin { display: grid; grid-template-columns: 70mm 1fr; gap: 6mm; }
.rdp-cuota { border: 2pt solid #000; background: #ececec; padding: 4mm 4mm 3.5mm; text-align: center; }
.rdp-cuota-lbl { font-size: 8pt; font-weight: 700; letter-spacing: 1pt; text-transform: uppercase; }
.rdp-cuota-val { font-size: 36pt; font-weight: 700; line-height: 1.05; margin-top: 1mm; }
.rdp-cuota-val small { font-size: 13pt; font-weight: 600; }
.rdp-cuota-sub { font-size: 9pt; font-weight: 600; margin-top: .5mm; }
.rdp-claves { margin-top: 3mm; border: 1pt solid #000; }
.rdp-clave { display: flex; justify-content: space-between; padding: 1.6mm 3mm; border-bottom: .5pt solid #999; font-size: 9pt; }
.rdp-clave:last-child { border-bottom: 0; }
.rdp-clave b { font-weight: 700; }
.rdp-clave.fuerte { background: #000; color: #fff; }

.rdp-tabla { width: 100%; border-collapse: collapse; font-size: 9pt; }
.rdp-tabla td { padding: 1.55mm 0; border-bottom: .5pt solid #999; }
.rdp-tabla td:last-child { text-align: right; font-weight: 600; white-space: nowrap; padding-left: 3mm; }
.rdp-tabla tr.sep td { border-bottom: 1pt solid #000; }
.rdp-tabla tr.total td { border-top: 1.5pt solid #000; border-bottom: 0; font-weight: 700; font-size: 10.5pt; padding-top: 2.2mm; }

.rdp-equip { flex: 1; min-height: 0; overflow: hidden; }
.rdp-equip ul { list-style: none; margin: 0; padding: 0; columns: 2; column-gap: 6mm; }
.rdp-equip li { break-inside: avoid; position: relative; padding: 0 0 1.3mm 3.2mm; font-size: 8.2pt; line-height: 1.3; }
.rdp-equip li::before { content: ''; position: absolute; left: 0; top: 1.3mm; width: 1.5mm; height: 1.5mm; background: #000; }

.rdp-legal { margin-top: 2mm; font-size: 6.6pt; line-height: 1.4; color: #222; text-align: justify; }
.rdp-pie { margin-top: 4mm; display: grid; grid-template-columns: 1fr; align-items: end;
  border-top: 2.5pt solid #000; padding-top: 3mm; }
.rdp-asesor-lbl { font-size: 7pt; font-weight: 700; letter-spacing: .8pt; text-transform: uppercase; color: #333; }
.rdp-asesor-nom { font-size: 13pt; font-weight: 600; line-height: 1.15; }
.rdp-asesor-tel { font-size: 11pt; font-weight: 700; }
.rdp-aviso { margin-top: 2.5mm; font-size: 6.8pt; text-align: center; color: #222; }
`;

  const esc = s => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  // toLocaleString('es-ES') no pone punto en cifras de 4 dígitos ("3000"): se agrupa a mano.
  const miles = s => s.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const eur  = n => (n < 0 ? '−' : '') + miles(String(Math.round(Math.abs(n)))) + ' €';
  const eur2 = n => { const [e, d] = Math.abs(Number(n)).toFixed(2).split('.'); return (n < 0 ? '−' : '') + miles(e) + ',' + d + ' €'; };
  const pct  = n => Number(n).toFixed(2).replace('.', ',') + ' %';
  const recorta = (s, max) => (s.length > max ? s.slice(0, max - 1).replace(/[\s,;:]+\S*$/, '') + '…' : s);
  // Los extras de DWA son frases largas ("Sistema de aviso de carril, con asistencia…"):
  // en papel basta el nombre principal, lo que va antes de la primera coma / "con" / paréntesis.
  const nombreCorto = s => {
    const corte = String(s).split(/,|\s\(|\s[Cc]on\s/)[0].trim();
    return recorta(corte.length >= 12 ? corte : String(s), 70);
  };

  function asegurarEstilos() {
    if (document.getElementById('rd-print-css')) return;
    const st = document.createElement('style');
    st.id = 'rd-print-css';
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  // ── Datos de la financiación elegida (mismos cálculos que la pantalla) ──
  function datosVWFS() {
    const res = cv2Calc();
    const rules = res.rules;
    const mant = cv2GetMantInfo();
    const cuotaTotal = Math.round((res.cuota + mant.mensual) * 100) / 100;
    const totalConMant = Math.round((res.total + mant.precioTotal) * 100) / 100;
    const flex = CV2.tab === 'flex' && res.vr > 0;
    const filas = [['Precio al contado', eur(CV2.precio)]];
    if (res.bonif > 0) filas.push(['Bonificación VWFS', '−' + eur(res.bonif)]);
    filas.push(['Entrada inicial', eur(CV2.entrada)]);
    filas.push(['Seguro de Protección Plus (opcional, financiado)', eur2(res.seg)]);
    filas.push(['Comisión de apertura financiada (3,5 %)', eur2(res.comision)]);
    filas.push(['Importe total financiado', eur2(res.capital), 'sep']);
    filas.push(['T.I.N.', pct(rules.tinFinal)]);
    filas.push(['Nº de cuotas', CV2.meses + ' meses']);
    filas.push(['Cuota de financiación', eur2(res.cuota) + ' / mes']);
    if (mant.precioTotal > 0) filas.push([mant.label, '+' + eur2(mant.mensual) + ' / mes']);
    else if (mant.free) filas.push([mant.label, 'Incluido gratis']);
    if (flex) filas.push(['Cuota final mes ' + CV2.meses + ' (' + Math.round(CV2.km / 1000) + '.000 km/año)', eur2(res.vr)]);
    filas.push(['Precio total a plazos', eur2(totalConMant), 'total']);

    const claves = [['Plazo', CV2.meses + ' meses'], ['Entrada', eur(CV2.entrada)], ['T.I.N.', pct(rules.tinFinal)]];
    if (flex) claves.push(['Cuota final mes ' + CV2.meses, eur2(res.vr), 'fuerte']);

    const legal = (document.getElementById('cv2-legal') || {}).textContent || '';
    return {
      entidad: 'VWFS · Volkswagen Financial Services',
      detalle: (CV2.tab === 'lineal' ? 'Financiación lineal' : 'Financiación FLEX (cuota final)') + ' · ' + rules.campanaLabel,
      cuota: cuotaTotal,
      cuotaLbl: mant.mensual > 0 ? 'Cuota mensual (incl. mantenimiento)' : 'Cuota mensual',
      cuotaSub: CV2.meses + ' cuotas' + (mant.mensual > 0 ? ' · financiación ' + eur2(res.cuota) : ''),
      claves, filas, legal,
    };
  }

  function datosBBVA() {
    const t = bbvaTarifa();
    const precio = CV2.precio || 0;
    const meses = Math.min(BBVA.meses, t.max);
    const importe = Math.max(0, precio - BBVA.entrada);
    const cuota = Math.round(t.coef[meses] * importe * 100) / 100;
    const total = Math.round((cuota * meses + BBVA.entrada) * 100) / 100;
    const tin = parseFloat(t.tin.replace(',', '.'));
    const legal = (document.getElementById('bbva-legal') || {}).textContent || '';
    return {
      entidad: 'BBVA · Préstamo Vehículo',
      detalle: t.vo ? 'Tarifa vehículo usado (más de 72 meses)' : 'Tarifa nuevo / seminuevo',
      cuota, cuotaLbl: 'Cuota mensual', cuotaSub: meses + ' cuotas',
      claves: [['Plazo', meses + ' meses'], ['Entrada', eur(BBVA.entrada)], ['T.I.N. fijo', pct(tin)]],
      filas: [
        ['Precio al contado', eur(precio)],
        ['Entrada inicial', eur(BBVA.entrada)],
        ['Importe financiado', eur(importe), 'sep'],
        ['T.I.N. fijo', pct(tin)],
        ['Comisión de apertura y seguro PPP', 'Incluidos en la cuota'],
        ['Nº de cuotas', meses + ' meses'],
        ['Cuota mensual', eur2(cuota) + ' / mes'],
        ['Precio total a plazos', eur2(total), 'total'],
      ],
      legal,
    };
  }

  // ── Hoja A4 ──
  function hojaHTML(fin) {
    const c = typeof COCHE !== 'undefined' ? COCHE : {};   // const de la página, no está en window
    const ex = c.imprimir || {};
    const hoy = new Date().toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const foto = (c.fotos || [])[0];

    const specs = [
      ['Combustible', c.combustible], ['Kilómetros', c.km ? c.km + ' km' : ''],
      ['Matriculación', c.fecha], ['Cambio', c.cambio],
      ['Potencia', ex.potencia], ['Color', ex.pintura || c.color],
      ['Consumo', ex.consumo], ['Tracción', ex.traccion],
      ['Autonomía eléctrica', ex.autonomia], ['Garantía', ex.garantia],
    ].filter(([, v]) => v).slice(0, 10);

    let equip = (ex.extras && ex.extras.length) ? ex.extras : (c.equipamiento || []);
    equip = equip.filter(e => !/^velocidad m[aá]xima/i.test(e)).slice(0, 14).map(nombreCorto);

    return `
<div class="rdp">
  <div class="rdp-head">
    <div>
      <div class="rdp-marca rdp-osw">Automóviles Rueda</div>
      <div class="rdp-marca-sub">Concesionario oficial SEAT · CUPRA · Das WeltAuto</div>
    </div>
    <div class="rdp-doc">
      <div class="rdp-doc-tit rdp-osw">Simulación de financiación</div>
      <div class="rdp-doc-meta">Fecha: <b>${hoy}</b>${c.id ? ' · Ref. ' + esc(c.id) : ''}</div>
    </div>
  </div>

  <div class="rdp-coche">
    <div class="rdp-foto">${foto ? `<img src="${esc(foto)}" alt="">` : ''}</div>
    <div>
      <div class="rdp-modelo rdp-osw">${esc(c.modelo)}</div>
      <div class="rdp-version">${esc(c.version)}</div>
      <div class="rdp-precio-row">
        <span class="rdp-precio-lbl">Precio al contado</span>
        <span class="rdp-precio rdp-osw">${eur(CV2.precio || 0)}</span>
      </div>
      <div class="rdp-specs">
        ${specs.map(([l, v]) => `<div class="rdp-spec"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}
      </div>
    </div>
  </div>

  <div class="rdp-sec">
    <div class="rdp-sec-tit"><h2 class="rdp-osw">Financiación elegida</h2><small>${esc(fin.entidad)} · ${esc(fin.detalle)}</small></div>
    <div class="rdp-fin">
      <div>
        <div class="rdp-cuota">
          <div class="rdp-cuota-lbl">${esc(fin.cuotaLbl)}</div>
          <div class="rdp-cuota-val rdp-osw">${eur2(fin.cuota).replace(' €', '')}<small> €/mes</small></div>
          <div class="rdp-cuota-sub">${esc(fin.cuotaSub)}</div>
        </div>
        <div class="rdp-claves">
          ${fin.claves.map(([l, v, cls]) => `<div class="rdp-clave ${cls || ''}"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}
        </div>
      </div>
      <table class="rdp-tabla">
        ${fin.filas.map(([l, v, cls]) => `<tr class="${cls || ''}"><td>${esc(l)}</td><td>${esc(v)}</td></tr>`).join('')}
      </table>
    </div>
  </div>

  ${equip.length ? `
  <div class="rdp-sec rdp-equip">
    <div class="rdp-sec-tit"><h2 class="rdp-osw">Equipamiento destacado</h2></div>
    <ul>${equip.map(e => `<li>${esc(e)}</li>`).join('')}</ul>
  </div>` : '<div style="flex:1"></div>'}

  <div class="rdp-legal">${esc(fin.legal)}</div>

  <div class="rdp-pie">
    <div>
      <div class="rdp-asesor-lbl">Tu asesor comercial</div>
      <div class="rdp-asesor-nom rdp-osw">${esc(ASESOR.nombreCorto)}</div>
      <div class="rdp-asesor-tel">${esc(ASESOR.telefonoDisplay)}</div>
    </div>
  </div>
  <div class="rdp-aviso">Simulación orientativa sin valor contractual, sujeta a aprobación de la entidad financiera. Precio y condiciones vigentes a fecha de emisión.</div>
</div>`;
  }

  // La hoja mide 274 mm fijos: quita los últimos extras que no quepan para que
  // nunca salga una línea cortada a medias (se mide fuera de pantalla, en mm = papel).
  function ajustarEquipamiento(hoja) {
    const prev = hoja.getAttribute('style');
    hoja.style.cssText = 'display:block;position:absolute;left:-10000px;top:0;';
    const caja = hoja.querySelector('.rdp-equip');
    const lista = caja && caja.querySelector('ul');
    while (lista && lista.children.length && caja.scrollHeight > caja.clientHeight + 1) {
      lista.lastElementChild.remove();
    }
    if (caja && lista && !lista.children.length) caja.innerHTML = '';
    if (prev === null) hoja.removeAttribute('style'); else hoja.setAttribute('style', prev);
  }

  window.rdImprimirSimulacion = function (financiera) {
    asegurarEstilos();
    const fin = financiera === 'BBVA' ? datosBBVA() : datosVWFS();
    let hoja = document.getElementById('rd-print-sheet');
    if (!hoja) {
      hoja = document.createElement('div');
      hoja.id = 'rd-print-sheet';
      document.body.appendChild(hoja);
    }
    hoja.innerHTML = hojaHTML(fin);
    ajustarEquipamiento(hoja);

    // Espera a la foto y a las fuentes (máx. 2,5 s) para que salgan en el papel.
    const img = hoja.querySelector('img');
    const foto = img && !img.complete
      ? new Promise(ok => { img.onload = img.onerror = ok; })
      : Promise.resolve();
    const fuentes = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    const limite = new Promise(ok => setTimeout(ok, 2500));
    Promise.race([Promise.all([foto, fuentes]), limite]).then(() => window.print());
  };
})();
