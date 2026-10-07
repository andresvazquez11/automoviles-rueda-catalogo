/* ══════════════════════════════════════════════════════════════════
   Automóviles Rueda — "Imprimir simulación · A4" e "Imprimir ficha · A4"
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
/* ── Hoja "Imprimir ficha · A4" (características del coche) ── */
.rdp-ficha .rdp-coche { grid-template-columns: 92mm 1fr; }
.rdp-ficha .rdp-foto { width: 92mm; height: 60mm; }
.rdp-tiles { display: grid; grid-template-columns: repeat(4, 1fr); border: 1pt solid #000; }
.rdp-tile { padding: 2mm 2.5mm; border-right: .5pt solid #999; border-bottom: .5pt solid #999; min-height: 12mm; }
.rdp-tile:nth-child(4n) { border-right: 0; }
.rdp-tile span { display: block; font-size: 6.8pt; font-weight: 700; letter-spacing: .6pt; text-transform: uppercase; color: #333; }
.rdp-tile b { display: block; font-size: 9.2pt; font-weight: 600; margin-top: .6mm; line-height: 1.2; }
.rdp-cols2 { display: grid; grid-template-columns: 1fr 1fr; column-gap: 6mm; }
.rdp-dl { margin: 0; }
.rdp-dl div { display: flex; justify-content: space-between; gap: 3mm; padding: .9mm 0; border-bottom: .5pt solid #999; font-size: 8.3pt; }
.rdp-dl dt { color: #333; }
.rdp-dl dd { margin: 0; font-weight: 600; text-align: right; }
.rdp-equip-ficha { display: flex; flex-direction: column; }
.rdp-grupos { flex: 1; min-height: 0; overflow: hidden; columns: 3; column-gap: 5mm; }
.rdp-grupo { margin-bottom: 2.5mm; }
.rdp-grupo h3 { break-after: avoid; }
.rdp-grupo h3 { margin: 0 0 1.2mm; font-size: 8pt; font-weight: 700; letter-spacing: .7pt; text-transform: uppercase;
  border-bottom: .5pt solid #000; padding-bottom: .6mm; }
.rdp-grupo ul { list-style: none; margin: 0; padding: 0; columns: 1; }
.rdp-grupo li { position: relative; padding: 0 0 1mm 3.2mm; font-size: 8pt; line-height: 1.28; break-inside: avoid; }
.rdp-grupo li::before { content: ''; position: absolute; left: 0; top: 1.2mm; width: 1.5mm; height: 1.5mm; background: #000; }
.rdp-chips { display: flex; gap: 6mm; font-size: 8.3pt; margin-bottom: 2.5mm; }
.rdp-chips b { font-weight: 700; }
.rdp-pie-contacto { display: grid; grid-template-columns: 1.1fr 1.4fr; gap: 6mm; align-items: end; }
.rdp-contacto { font-size: 8.6pt; line-height: 1.45; text-align: right; }
.rdp-contacto b { font-weight: 700; }
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
    const corte = String(s).split(/,|\s\(|\s[Cc]on\s|\s[Ww]ith\s|\s[Mm]it\s/)[0].trim();
    return recorta(corte.length >= 12 ? corte : String(s), 70);
  };

  /* ── Idioma de la hoja: el que tenga elegido la web (es / en / de) ── */
  const idioma = () => {
    const l = (window.rdIdiomaActual && window.rdIdiomaActual()) || document.documentElement.lang || 'es';
    return (l === 'en' || l === 'de') ? l : 'es';
  };
  // Textos fijos de las hojas: español → [inglés, alemán]
  const I18N = {
    'Concesionario oficial SEAT · CUPRA · Das WeltAuto': ['Official SEAT · CUPRA · Das WeltAuto dealer', 'Offizieller SEAT · CUPRA · Das WeltAuto Händler'],
    'Simulación de financiación': ['Finance quote', 'Finanzierungsbeispiel'],
    'Ficha del vehículo': ['Vehicle spec sheet', 'Fahrzeugdatenblatt'],
    'Fecha de impresión': ['Printed on', 'Gedruckt am'],
    'Precio al contado': ['Cash price', 'Barpreis'],
    'Precio': ['Price', 'Preis'],
    'Combustible': ['Fuel', 'Kraftstoff'], 'Kilómetros': ['Mileage', 'Kilometerstand'],
    'Matriculación': ['Registered', 'Erstzulassung'], 'Cambio': ['Gearbox', 'Getriebe'],
    'Potencia': ['Power', 'Leistung'], 'Color': ['Colour', 'Farbe'], 'Consumo': ['Consumption', 'Verbrauch'],
    'Tracción': ['Drive', 'Antrieb'], 'Autonomía eléctrica': ['Electric range', 'Elektrische Reichweite'],
    'Garantía': ['Warranty', 'Garantie'],
    'Financiación elegida': ['Selected finance', 'Gewählte Finanzierung'],
    'Equipamiento destacado': ['Key equipment', 'Ausstattungs-Highlights'],
    'Características principales': ['Key features', 'Wichtigste Merkmale'],
    'Dimensiones': ['Dimensions', 'Abmessungen'],
    'Motor y consumo': ['Engine and consumption', 'Motor und Verbrauch'],
    'Equipamiento extra': ['Optional equipment', 'Sonderausstattung'],
    'Equipamiento': ['Equipment', 'Ausstattung'],
    'Pintura': ['Paint', 'Lackierung'], 'Tapicería': ['Upholstery', 'Polsterung'],
    'Tu asesor comercial': ['Your sales advisor', 'Ihr Verkaufsberater'],
    'Ficha informativa sin valor contractual. Precio, disponibilidad y equipamiento sujetos a cambios; consulta con tu asesor.':
      ['Information sheet with no contractual value. Price, availability and equipment subject to change; please check with your advisor.',
       'Informationsblatt ohne Vertragscharakter. Preis, Verfügbarkeit und Ausstattung können sich ändern; bitte fragen Sie Ihren Berater.'],
    'Simulación orientativa sin valor contractual, sujeta a aprobación de la entidad financiera. Precio y condiciones vigentes a fecha de emisión.':
      ['Indicative quote with no contractual value, subject to approval by the finance provider. Price and conditions valid on the date of issue.',
       'Unverbindliches Finanzierungsbeispiel ohne Vertragscharakter, vorbehaltlich der Genehmigung durch das Finanzinstitut. Preis und Konditionen gültig am Ausstellungsdatum.'],
    'Texto legal de la entidad (versión vinculante en español):': ['Legal text of the finance provider (binding Spanish version):', 'Rechtstext des Finanzinstituts (verbindliche spanische Fassung):'],
    // Financiación
    'Bonificación VWFS': ['VWFS discount', 'VWFS-Bonus'], 'Entrada inicial': ['Down payment', 'Anzahlung'],
    'Seguro de Protección Plus (opcional, financiado)': ['Protection Plus insurance (optional, financed)', 'Protection-Plus-Versicherung (optional, finanziert)'],
    'Comisión de apertura financiada (2,99 %)': ['Financed opening fee (2.99 %)', 'Finanzierte Bearbeitungsgebühr (2,99 %)'],
    'Importe total financiado': ['Total amount financed', 'Finanzierter Gesamtbetrag'],
    'Importe financiado': ['Amount financed', 'Finanzierter Betrag'],
    'T.I.N.': ['Nominal rate (TIN)', 'Sollzins (TIN)'], 'T.I.N. fijo': ['Fixed nominal rate (TIN)', 'Fester Sollzins (TIN)'],
    'Nº de cuotas': ['Number of instalments', 'Anzahl der Raten'],
    'Cuota de financiación': ['Finance instalment', 'Finanzierungsrate'],
    'Incluido gratis': ['Included free', 'Kostenlos inklusive'],
    'Cuota final mes': ['Final instalment, month', 'Schlussrate, Monat'],
    'Precio total a plazos': ['Total price in instalments', 'Gesamtpreis in Raten'],
    'Plazo': ['Term', 'Laufzeit'], 'Entrada': ['Down payment', 'Anzahlung'],
    'Financiación lineal': ['Standard finance', 'Klassische Finanzierung'],
    'Financiación FLEX (cuota final)': ['FLEX finance (final instalment)', 'FLEX-Finanzierung (Schlussrate)'],
    'Cuota mensual (incl. mantenimiento)': ['Monthly instalment (incl. maintenance)', 'Monatsrate (inkl. Wartung)'],
    'Cuota mensual': ['Monthly instalment', 'Monatsrate'],
    'Tarifa vehículo usado (más de 72 meses)': ['Used-car rate (over 72 months)', 'Gebrauchtwagentarif (über 72 Monate)'],
    'Tarifa nuevo / seminuevo': ['New / nearly-new rate', 'Tarif Neu- / Jahreswagen'],
    'Comisión de apertura y seguro PPP': ['Opening fee and PPI insurance', 'Bearbeitungsgebühr und Restschuldversicherung'],
    'Incluidos en la cuota': ['Included in the instalment', 'In der Rate enthalten'],
    'BBVA · Préstamo Vehículo': ['BBVA · Car loan', 'BBVA · Autokredit'],
    'CaixaBank · Préstamo Vehículo': ['CaixaBank · Car loan', 'CaixaBank · Autokredit'],
    'Tarifa nuevo y ocasión · con Pack Vida': ['New and used-car rate · with life cover', 'Tarif Neu- und Gebrauchtwagen · mit Lebensversicherung'],
    'Gastos (3,99 %) y seguro Pack Vida': ['Fees (3.99 %) and life cover', 'Gebühren (3,99 %) und Lebensversicherung'],
    'meses': ['months', 'Monate'], 'cuotas': ['instalments', 'Raten'], 'financiación': ['finance', 'Finanzierung'],
    '/ mes': ['/ month', '/ Monat'],
    'de': ['of', 'von'], 'resto en la ficha online': ['see the online listing for the rest', 'Rest im Online-Datenblatt'], '€/mes': ['€/month', '€/Monat'], 'km/año': ['km/year', 'km/Jahr'],
  };
  const L = s => {
    const l = idioma();
    if (l === 'es') return s;
    const t = I18N[s];
    return t ? t[l === 'en' ? 0 : 1] : s;
  };
  // Textos que genera la calculadora (mantenimiento, nombre de campaña)
  const traducirDinamico = s => {
    const l = idioma();
    if (l === 'es' || !s) return s;
    const en = l === 'en';
    return String(s)
      .replace(/Mantenimiento (\d+) años/, (_, n) => en ? `Maintenance ${n} years` : `Wartung ${n} Jahre`)
      .replace(/Otras Marcas/g, en ? 'Other brands' : 'Andere Marken')
      .replace(/Básica/g, en ? 'Basic' : 'Basis');
  };
  // Texto del coche en el idioma de la hoja: [español, inglés, alemán] con alemán → inglés → español.
  const tri = (es, en, de) => { const l = idioma(); return l === 'en' ? (en || es) : l === 'de' ? (de || en || es) : es; };
  // Texto de la ficha técnica (diccionario tr: {es: [en, de]} que manda la página)
  // Valores básicos del anuncio (combustible, cambio) que no siempre están en la ficha técnica
  const BASICOS = {
    'Gasolina': ['Petrol', 'Benzin'], 'Diésel': ['Diesel', 'Diesel'], 'Diesel': ['Diesel', 'Diesel'],
    'Híbrido': ['Hybrid', 'Hybrid'], 'Híbrido enchufable': ['Plug-in hybrid', 'Plug-in-Hybrid'],
    'Eléctrico': ['Electric', 'Elektro'], 'Automático': ['Automatic', 'Automatik'], 'Manual': ['Manual', 'Schaltgetriebe'],
  };
  const trFicha = (s, tr) => { const p = (tr || {})[s] || BASICOS[s]; return p ? tri(s, p[0], p[1]) : s; };

  function fechaImpresion() {
    const loc = { es: 'es-ES', en: 'en-GB', de: 'de-DE' }[idioma()];
    const d = new Date();
    const fecha = d.toLocaleDateString(loc, { day: '2-digit', month: '2-digit', year: 'numeric' });
    const hora = d.toLocaleTimeString(loc, { hour: '2-digit', minute: '2-digit' });
    return fecha + ' · ' + hora;
  }

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
    const meses = CV2.meses + ' ' + L('meses');
    const filas = [[L('Precio al contado'), eur(CV2.precio)]];
    if (res.bonif > 0) filas.push([L('Bonificación VWFS'), '−' + eur(res.bonif)]);
    filas.push([L('Entrada inicial'), eur(CV2.entrada)]);
    filas.push([L('Seguro de Protección Plus (opcional, financiado)'), eur2(res.seg)]);
    filas.push([L('Comisión de apertura financiada (2,99 %)'), eur2(res.comision)]);
    filas.push([L('Importe total financiado'), eur2(res.capital), 'sep']);
    filas.push([L('T.I.N.'), pct(rules.tinFinal)]);
    filas.push([L('Nº de cuotas'), meses]);
    filas.push([L('Cuota de financiación'), eur2(res.cuota) + ' ' + L('/ mes')]);
    if (mant.precioTotal > 0) filas.push([traducirDinamico(mant.label), '+' + eur2(mant.mensual) + ' ' + L('/ mes')]);
    else if (mant.free) filas.push([traducirDinamico(mant.label), L('Incluido gratis')]);
    if (flex) filas.push([L('Cuota final mes') + ' ' + CV2.meses + ' (' + Math.round(CV2.km / 1000) + '.000 ' + L('km/año') + ')', eur2(res.vr)]);
    filas.push([L('Precio total a plazos'), eur2(totalConMant), 'total']);

    const claves = [[L('Plazo'), meses], [L('Entrada'), eur(CV2.entrada)], [L('T.I.N.'), pct(rules.tinFinal)]];
    if (flex) claves.push([L('Cuota final mes') + ' ' + CV2.meses, eur2(res.vr), 'fuerte']);

    const legal = (document.getElementById('cv2-legal') || {}).textContent || '';
    return {
      entidad: 'VWFS · Volkswagen Financial Services',
      detalle: (CV2.tab === 'lineal' ? L('Financiación lineal') : L('Financiación FLEX (cuota final)')) + ' · ' + traducirDinamico(rules.campanaLabel),
      cuota: cuotaTotal,
      cuotaLbl: mant.mensual > 0 ? L('Cuota mensual (incl. mantenimiento)') : L('Cuota mensual'),
      cuotaSub: CV2.meses + ' ' + L('cuotas') + (mant.mensual > 0 ? ' · ' + L('financiación') + ' ' + eur2(res.cuota) : ''),
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
      entidad: L('BBVA · Préstamo Vehículo'),
      detalle: t.vo ? L('Tarifa vehículo usado (más de 72 meses)') : L('Tarifa nuevo / seminuevo'),
      cuota, cuotaLbl: L('Cuota mensual'), cuotaSub: meses + ' ' + L('cuotas'),
      claves: [[L('Plazo'), meses + ' ' + L('meses')], [L('Entrada'), eur(BBVA.entrada)], [L('T.I.N. fijo'), pct(tin)]],
      filas: [
        [L('Precio al contado'), eur(precio)],
        [L('Entrada inicial'), eur(BBVA.entrada)],
        [L('Importe financiado'), eur(importe), 'sep'],
        [L('T.I.N. fijo'), pct(tin)],
        [L('Comisión de apertura y seguro PPP'), L('Incluidos en la cuota')],
        [L('Nº de cuotas'), meses + ' ' + L('meses')],
        [L('Cuota mensual'), eur2(cuota) + ' ' + L('/ mes')],
        [L('Precio total a plazos'), eur2(total), 'total'],
      ],
      legal,
    };
  }

  function datosCaixa() {
    const t = caixaTarifa();
    const precio = CV2.precio || 0;
    const meses = CAIXA.meses;
    const importe = Math.max(0, precio - CAIXA.entrada);
    const cuota = Math.round((CAIXA_COEF[meses] || 0) * importe * 100) / 100;
    const total = Math.round((cuota * meses + CAIXA.entrada) * 100) / 100;
    const tin = parseFloat(CAIXA_TIN.replace(',', '.'));
    const legal = (document.getElementById('caixa-legal') || {}).textContent || '';
    return {
      entidad: L('CaixaBank · Préstamo Vehículo'),
      detalle: L('Tarifa nuevo y ocasión · con Pack Vida'),
      cuota, cuotaLbl: L('Cuota mensual'), cuotaSub: meses + ' ' + L('cuotas'),
      claves: [[L('Plazo'), meses + ' ' + L('meses')], [L('Entrada'), eur(CAIXA.entrada)], [L('T.I.N. fijo'), pct(tin)]],
      filas: [
        [L('Precio al contado'), eur(precio)],
        [L('Entrada inicial'), eur(CAIXA.entrada)],
        [L('Importe financiado'), eur(importe), 'sep'],
        [L('T.I.N. fijo'), pct(tin)],
        [L('Gastos (3,99 %) y seguro Pack Vida'), L('Incluidos en la cuota')],
        [L('Nº de cuotas'), meses + ' ' + L('meses')],
        [L('Cuota mensual'), eur2(cuota) + ' ' + L('/ mes')],
        [L('Precio total a plazos'), eur2(total), 'total'],
      ],
      legal,
      disponible: t.disponible,
    };
  }

  // ── Piezas comunes a las dos hojas ──
  function coche() { return typeof COCHE !== 'undefined' ? COCHE : {}; }   // const de la página, no está en window
  function asesor() { return typeof ASESOR !== 'undefined' ? ASESOR : {}; }

  function cabeceraHTML(titulo) {
    const c = coche();
    return `
  <div class="rdp-head">
    <div>
      <div class="rdp-marca rdp-osw">Automóviles Rueda</div>
      <div class="rdp-marca-sub">${esc(L('Concesionario oficial SEAT · CUPRA · Das WeltAuto'))}</div>
    </div>
    <div class="rdp-doc">
      <div class="rdp-doc-tit rdp-osw">${esc(L(titulo))}</div>
      <div class="rdp-doc-meta">${esc(L('Fecha de impresión'))}: <b>${esc(fechaImpresion())}</b>${c.id ? ' · Ref. ' + esc(c.id) : ''}</div>
    </div>
  </div>`;
  }

  function pieHTML(aviso) {
    const a = asesor();
    const lineas = [
      a.email ? esc(a.email) : '',
      a.direccion ? esc(a.direccion) : '',
      a.web ? esc(a.web) : '',
    ].filter(Boolean).join('<br>');
    return `
  <div class="rdp-pie">
    <div class="rdp-pie-contacto">
      <div>
        <div class="rdp-asesor-lbl">${esc(L('Tu asesor comercial'))}</div>
        <div class="rdp-asesor-nom rdp-osw">${esc(a.nombre || a.nombreCorto || '')}</div>
        <div class="rdp-asesor-tel">${esc(a.telefonoDisplay || '')}</div>
      </div>
      <div class="rdp-contacto">${lineas}</div>
    </div>
  </div>
  <div class="rdp-aviso">${esc(L(aviso))}</div>`;
  }

  // ── Hoja A4: simulación de financiación ──
  function hojaHTML(fin) {
    const c = coche();
    const ex = c.imprimir || {};
    const tr = ex.tr || {};
    const foto = (c.fotos || [])[0];

    const specs = [
      ['Combustible', trFicha(c.combustible, tr)], ['Kilómetros', c.km ? c.km + ' km' : ''],
      ['Matriculación', c.fecha], ['Cambio', trFicha(c.cambio, tr)],
      ['Potencia', trFicha(ex.potencia, tr)], ['Color', trFicha(ex.pintura, tr) || tri(c.color, c.color_en, c.color_de)],
      ['Consumo', trFicha(ex.consumo, tr)], ['Tracción', trFicha(ex.traccion, tr)],
      ['Autonomía eléctrica', trFicha(ex.autonomia, tr)], ['Garantía', trFicha(ex.garantia, tr)],
    ].filter(([, v]) => v).slice(0, 10);

    let equip = (ex.extras && ex.extras.length)
      ? ex.extras.map(e => trFicha(e, tr))
      : equipamientoCoche(c);
    equip = equip.filter(e => !/^velocidad m[aá]xima/i.test(e)).slice(0, 14).map(nombreCorto);
    const legalPrefijo = idioma() === 'es' ? '' : L('Texto legal de la entidad (versión vinculante en español):') + ' ';

    return `
<div class="rdp">
  ${cabeceraHTML('Simulación de financiación')}

  <div class="rdp-coche">
    <div class="rdp-foto">${foto ? `<img src="${esc(foto)}" alt="">` : ''}</div>
    <div>
      <div class="rdp-modelo rdp-osw">${esc(c.modelo)}</div>
      <div class="rdp-version">${esc(tri(c.version, c.version_en, c.version_de))}</div>
      <div class="rdp-precio-row">
        <span class="rdp-precio-lbl">${esc(L('Precio al contado'))}</span>
        <span class="rdp-precio rdp-osw">${eur(CV2.precio || 0)}</span>
      </div>
      <div class="rdp-specs">
        ${specs.map(([l, v]) => `<div class="rdp-spec"><span>${esc(L(l))}</span><b>${esc(v)}</b></div>`).join('')}
      </div>
    </div>
  </div>

  <div class="rdp-sec">
    <div class="rdp-sec-tit"><h2 class="rdp-osw">${esc(L('Financiación elegida'))}</h2><small>${esc(fin.entidad)} · ${esc(fin.detalle)}</small></div>
    <div class="rdp-fin">
      <div>
        <div class="rdp-cuota">
          <div class="rdp-cuota-lbl">${esc(fin.cuotaLbl)}</div>
          <div class="rdp-cuota-val rdp-osw">${eur2(fin.cuota).replace(' €', '')}<small> ${esc(L('€/mes'))}</small></div>
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
    <div class="rdp-sec-tit"><h2 class="rdp-osw">${esc(L('Equipamiento destacado'))}</h2></div>
    <ul>${equip.map(e => `<li>${esc(e)}</li>`).join('')}</ul>
  </div>` : '<div style="flex:1"></div>'}

  <div class="rdp-legal">${esc(legalPrefijo + fin.legal)}</div>
  ${pieHTML('Simulación orientativa sin valor contractual, sujeta a aprobación de la entidad financiera. Precio y condiciones vigentes a fecha de emisión.')}
</div>`;
  }

  function equipamientoCoche(c) {
    const n = (c.equipamiento || []).length;
    const l = idioma();
    if (l === 'de' && (c.equipamiento_de || []).length === n) return c.equipamiento_de;
    if (l !== 'es' && (c.equipamiento_en || []).length === n) return c.equipamiento_en;
    return c.equipamiento || [];
  }

  // ── Hoja A4: ficha del vehículo (características, sin financiación) ──
  function hojaFichaHTML() {
    const c = coche();
    const ex = c.imprimir || {};
    const tr = ex.tr || {};
    const gen = ex.gen || {};
    const dims = ex.dims || {};
    const etq = ex.etq || {};
    const foto = (c.fotos || [])[0];
    const lab = (clave, es) => { const e = etq[clave]; return e ? tri(e[0], e[1], e[2]) : L(es); };
    const precioTxt = c.vendido ? '' : (c.precio ? c.precio + ' €' : '');

    // Características principales (mismo orden que la ficha web)
    const valores = Object.assign({}, gen);
    if (!valores.matriculacion && c.fecha) valores.matriculacion = c.fecha;
    if (!valores.combustible && c.combustible) valores.combustible = c.combustible;
    if (!valores.cambio && c.cambio) valores.cambio = c.cambio;
    if (c.km) valores.km = (c.km + ' km').replace(' km km', ' km');
    if (ex.pintura) valores.color = ex.pintura;
    else if (c.color) valores.color = c.color;
    const ordenTiles = ['matriculacion', 'km', 'combustible', 'potencia', 'cambio', 'traccion',
      'puertas', 'plazas', 'color', 'carroceria', 'maletero', 'garantia'];
    const tiles = ordenTiles.filter(k => valores[k]).slice(0, 12).map(k => {
      const v = k === 'color' && !ex.pintura ? tri(c.color, c.color_en, c.color_de) : trFicha(valores[k], tr);
      return `<div class="rdp-tile"><span>${esc(lab(k, k))}</span><b>${esc(v)}</b></div>`;
    }).join('');

    const filas = (claves, fuente) => claves.filter(k => fuente[k])
      .map(k => `<div><dt>${esc(lab(k, k))}</dt><dd>${esc(trFicha(fuente[k], tr))}</dd></div>`).join('');
    const dimsHTML = filas(['largo', 'ancho', 'alto', 'batalla', 'peso', 'maletero', 'deposito'],
      Object.assign({}, dims, { maletero: gen.maletero, deposito: dims.deposito || gen.deposito }));
    const motorHTML = filas(['potencia', 'par', 'vmax', 'aceleracion', 'consumo', 'co2', 'autonomia_electrica', 'bateria', 'etiqueta'], gen);

    // Equipamiento extra por grupos; sin ficha técnica, el equipamiento del anuncio
    const grupos = ex.grupos || {};
    const grp = ex.grp || {};
    let gruposHTML = Object.keys(grupos).map(g => {
      const n = grp[g] ? tri(grp[g][0], grp[g][1], grp[g][2]) : g;
      return `<div class="rdp-grupo"><h3>${esc(n)}</h3><ul>${grupos[g].map(e => `<li>${esc(nombreCorto(trFicha(e, tr)))}</li>`).join('')}</ul></div>`;
    }).join('');
    let tituloEquip = 'Equipamiento extra';
    if (!gruposHTML) {
      const lista = equipamientoCoche(c).filter(e => !/^velocidad m[aá]xima/i.test(e));
      if (lista.length) {
        tituloEquip = 'Equipamiento';
        gruposHTML = `<div class="rdp-grupo"><ul>${lista.map(e => `<li>${esc(nombreCorto(e))}</li>`).join('')}</ul></div>`;
      }
    }
    const chips = [['Pintura', ex.pintura], ['Tapicería', ex.tapizado]].filter(([, v]) => v)
      .map(([l, v]) => `<span><b>${esc(L(l))}:</b> ${esc(trFicha(v, tr))}</span>`).join('');

    return `
<div class="rdp rdp-ficha">
  ${cabeceraHTML('Ficha del vehículo')}

  <div class="rdp-coche">
    <div class="rdp-foto">${foto ? `<img src="${esc(foto)}" alt="">` : ''}</div>
    <div>
      <div class="rdp-modelo rdp-osw">${esc(c.modelo)}</div>
      <div class="rdp-version">${esc(tri(c.version, c.version_en, c.version_de))}</div>
      ${precioTxt ? `<div class="rdp-precio-row">
        <span class="rdp-precio-lbl">${esc(L('Precio'))}</span>
        <span class="rdp-precio rdp-osw">${esc(precioTxt)}</span>
      </div>` : ''}
    </div>
  </div>

  ${tiles ? `<div class="rdp-sec">
    <div class="rdp-sec-tit"><h2 class="rdp-osw">${esc(L('Características principales'))}</h2></div>
    <div class="rdp-tiles">${tiles}</div>
  </div>` : ''}

  ${(dimsHTML || motorHTML) ? `<div class="rdp-sec rdp-cols2">
    ${dimsHTML ? `<div><div class="rdp-sec-tit"><h2 class="rdp-osw">${esc(L('Dimensiones'))}</h2></div><dl class="rdp-dl">${dimsHTML}</dl></div>` : '<div></div>'}
    ${motorHTML ? `<div><div class="rdp-sec-tit"><h2 class="rdp-osw">${esc(L('Motor y consumo'))}</h2></div><dl class="rdp-dl">${motorHTML}</dl></div>` : ''}
  </div>` : ''}

  ${gruposHTML ? `<div class="rdp-sec rdp-equip rdp-equip-ficha">
    <div class="rdp-sec-tit"><h2 class="rdp-osw">${esc(L(tituloEquip))}</h2><small class="rdp-mas"></small></div>
    ${chips ? `<div class="rdp-chips">${chips}</div>` : ''}
    <div class="rdp-grupos">${gruposHTML}</div>
  </div>` : '<div style="flex:1"></div>'}

  ${pieHTML('Ficha informativa sin valor contractual. Precio, disponibilidad y equipamiento sujetos a cambios; consulta con tu asesor.')}
</div>`;
  }

  // La hoja mide 274 mm fijos: quita los últimos elementos de la lista que no
  // quepan para que nunca salga una línea cortada a medias (se mide fuera de
  // pantalla, en mm = papel).
  function ajustarEquipamiento(hoja) {
    const prev = hoja.getAttribute('style');
    hoja.style.cssText = 'display:block;position:absolute;left:-10000px;top:0;';
    const caja = hoja.querySelector('.rdp-equip');
    if (caja) {
      const marco = caja.querySelector('.rdp-grupos') || caja;
      const sobra = () => marco === caja
        ? caja.scrollHeight > caja.clientHeight + 1
        : (marco.scrollWidth > marco.clientWidth + 1 || caja.scrollHeight > caja.clientHeight + 1);
      const ultimoItem = () => {
        const items = caja.querySelectorAll('li');
        return items.length ? items[items.length - 1] : null;
      };
      const total = caja.querySelectorAll('li').length;
      let li;
      while (sobra() && (li = ultimoItem())) {
        const ul = li.parentElement;
        li.remove();
        if (!ul.children.length) (ul.closest('.rdp-grupo') || ul).remove();
      }
      const quedan = caja.querySelectorAll('li').length;
      const aviso = caja.querySelector('.rdp-mas');
      if (aviso && quedan && quedan < total) {
        aviso.textContent = quedan + ' ' + L('de') + ' ' + total + ' · ' + L('resto en la ficha online');
      }
      if (!quedan) caja.innerHTML = '';
    }
    if (prev === null) hoja.removeAttribute('style'); else hoja.setAttribute('style', prev);
  }

  function imprimirHoja(html) {
    asegurarEstilos();
    let hoja = document.getElementById('rd-print-sheet');
    if (!hoja) {
      hoja = document.createElement('div');
      hoja.id = 'rd-print-sheet';
      document.body.appendChild(hoja);
    }
    hoja.innerHTML = html;
    ajustarEquipamiento(hoja);

    // Espera a la foto y a las fuentes (máx. 2,5 s) para que salgan en el papel.
    const img = hoja.querySelector('img');
    const foto = img && !img.complete
      ? new Promise(ok => { img.onload = img.onerror = ok; })
      : Promise.resolve();
    const fuentes = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    const limite = new Promise(ok => setTimeout(ok, 2500));
    Promise.race([Promise.all([foto, fuentes]), limite]).then(() => window.print());
  }

  const datosFin = f => (f === 'BBVA' ? datosBBVA() : f === 'CAIXA' ? datosCaixa() : datosVWFS());

  // Para assets/enviar.js: las mismas hojas, para el PDF y para el enlace que se manda al cliente.
  window.rdHojas = {
    simulacion: f => { const fin = datosFin(f); return fin.disponible === false ? null : { html: hojaHTML(fin), fin }; },
    ficha: () => ({ html: hojaFichaHTML() }),
    preparar: el => { asegurarEstilos(); ajustarEquipamiento(el); },
  };

  window.rdImprimirSimulacion = function (financiera) {
    const fin = datosFin(financiera);
    if (fin.disponible === false) { alert('La tarifa CaixaBank no admite este vehículo por antigüedad.'); return; }
    imprimirHoja(hojaHTML(fin));
  };
  window.rdImprimirFicha = function () {
    imprimirHoja(hojaFichaHTML());
  };
})();
