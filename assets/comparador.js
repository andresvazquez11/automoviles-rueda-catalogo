// Comparador completo (hasta 3 coches) — portada del catálogo.
// Bandeja "Comparando N" + tabla con la ficha completa lado a lado.
// Los datos de cada coche (comparador.json, lo genera generar_web.py) se
// descargan la primera vez que se pulsa "Ver comparación".
// El clic en "+ Comparar" va por delegación en <body>: así funciona también
// con las tarjetas que clona la franja de Destacados (cloneNode no copia listeners).
(function () {
  const tray = document.getElementById('rd-tray');
  const overlay = document.getElementById('rd-overlay');
  const tabla = document.getElementById('rd-cx-tabla');
  const chkDif = document.getElementById('rd-cx-dif');
  const chkEq = document.getElementById('rd-cx-eq');
  if (!tray || !overlay || !tabla) return;

  const compareIds = new Set();
  let datos = null;           // comparador.json, cargado bajo demanda

  const idioma = () => (window.rdIdiomaActual && window.rdIdiomaActual()) || document.documentElement.lang || 'es';
  const en = () => idioma() === 'en';
  // Alemán: se busca por el texto inglés (así no hay que tocar cada llamada a t()).
  const DE = {
    '✓ Comparing': '✓ Im Vergleich', '+ Compare': '+ Vergleichen', 'Up to 3 cars can be compared': 'Maximal 3 Fahrzeuge vergleichbar',
    'Comparing ': 'Im Vergleich: ', 'See comparison': 'Vergleich ansehen', 'Clear comparison': 'Vergleich leeren',
    'Loading specs…': 'Daten werden geladen…',
    'Price and usage': 'Preis und Nutzung', 'Price': 'Preis', 'Mileage': 'Kilometerstand', 'Registered': 'Erstzulassung',
    'Warranty': 'Garantie', 'Engine and performance': 'Motor und Leistung', 'Fuel': 'Kraftstoff', 'DGT label': 'DGT-Umweltplakette',
    'Power': 'Leistung', 'Torque': 'Drehmoment', 'Gearbox': 'Getriebe', '0-100 km/h': '0-100 km/h', 'Top speed': 'Höchstgeschwindigkeit',
    'Drive': 'Antrieb', 'Consumption and range': 'Verbrauch und Reichweite', 'Average consumption': 'Durchschnittsverbrauch',
    'CO₂ emissions': 'CO₂-Emissionen', 'Electric range': 'Elektrische Reichweite', 'Total range': 'Gesamtreichweite',
    'Dimensions and boot': 'Abmessungen und Kofferraum', 'Boot': 'Kofferraum', 'Length': 'Länge', 'Width': 'Breite',
    'Height': 'Höhe', 'Wheelbase': 'Radstand', 'Weight': 'Gewicht', 'Equipment': 'Ausstattung',
    'Optional extras fitted': 'Verbaute Sonderausstattung',
  };
  const t = (es, eng, de) => {
    const l = idioma();
    return l === 'en' ? eng : l === 'de' ? (de || DE[eng] || eng) : es;
  };
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // Filas: [clave, ES, EN, regla] — regla: 'min' | 'max' | 'dgt' | '' (sin mejor dato)
  const GRUPOS = [
    ['Precio y uso', 'Price and usage', [
      ['precio', 'Precio', 'Price', 'min'], ['km', 'Kilómetros', 'Mileage', 'min'],
      ['fecha', 'Matriculación', 'Registered', ''], ['garantia', 'Garantía', 'Warranty', 'max']]],
    ['Motor y prestaciones', 'Engine and performance', [
      ['comb', 'Combustible', 'Fuel', ''], ['dgt', 'Etiqueta DGT', 'DGT label', 'dgt'],
      ['cv', 'Potencia', 'Power', 'max'], ['par', 'Par motor', 'Torque', 'max'],
      ['cambio', 'Cambio', 'Gearbox', ''], ['acel', '0 a 100 km/h', '0-100 km/h', 'min'],
      ['vmax', 'Velocidad máxima', 'Top speed', 'max'], ['traccion', 'Tracción', 'Drive', '']]],
    ['Consumo y autonomía', 'Consumption and range', [
      ['consumo', 'Consumo medio', 'Average consumption', 'min'], ['co2', 'Emisiones CO₂', 'CO₂ emissions', 'min'],
      ['aut_el', 'Autonomía eléctrica', 'Electric range', 'max'], ['aut', 'Autonomía total', 'Total range', 'max']]],
    ['Medidas y maletero', 'Dimensions and boot', [
      ['maletero', 'Maletero', 'Boot', 'max'], ['largo', 'Largo', 'Length', ''], ['ancho', 'Ancho', 'Width', ''],
      ['alto', 'Alto', 'Height', ''], ['batalla', 'Batalla', 'Wheelbase', ''], ['peso', 'Peso', 'Weight', 'min']]],
    ['Equipamiento', 'Equipment', [
      ['extras', 'Extras montados', 'Optional extras fitted', 'max']]],
  ];
  const RANGO_DGT = { CERO: 4, ECO: 3, C: 2, B: 1 };
  const TRAD = { 'Automático': 'Automatic', 'Delantera': 'Front-wheel drive', 'Trasera': 'Rear-wheel drive',
    'Total': 'All-wheel drive', 'Gasolina': 'Petrol', 'Diésel': 'Diesel', 'Eléctrico': 'Electric',
    'Híbrido': 'Hybrid', 'Híbrido enchufable': 'Plug-in hybrid' };
  const TRAD_DE = { 'Automático': 'Automatik', 'Delantera': 'Frontantrieb', 'Trasera': 'Heckantrieb',
    'Total': 'Allradantrieb', 'Gasolina': 'Benzin', 'Diésel': 'Diesel', 'Eléctrico': 'Elektro',
    'Híbrido': 'Hybrid', 'Híbrido enchufable': 'Plug-in-Hybrid', 'Manual': 'Schaltgetriebe' };
  const valorTxt = v => (en() && TRAD[v]) ? TRAD[v] : (idioma() === 'de' && TRAD_DE[v]) ? TRAD_DE[v] : v;

  function tarjetaConId(id) { return document.querySelector('.rd-grid .rd-card[data-id="' + id + '"]') || document.querySelector('.rd-card[data-id="' + id + '"]'); }

  function marcarBoton(card, activo) {
    const btn = card && card.querySelector('.rd-compare-btn');
    if (!btn) return;
    btn.textContent = activo ? t('✓ Comparando', '✓ Comparing') : t('+ Comparar', '+ Compare');
    btn.classList.toggle('activo', activo);
  }
  function marcarTodas(id, activo) { document.querySelectorAll('.rd-card[data-id="' + id + '"]').forEach(c => marcarBoton(c, activo)); }

  function toggleCompare(card) {
    const id = card.dataset.id;
    if (compareIds.has(id)) { compareIds.delete(id); marcarTodas(id, false); }
    else {
      if (compareIds.size >= 3) { alert(t('Máximo 3 coches para comparar', 'Up to 3 cars can be compared')); return; }
      compareIds.add(id); marcarTodas(id, true);
    }
    renderTray();
  }

  function renderTray() {
    if (compareIds.size === 0) {
      tray.style.display = 'none'; tray.innerHTML = '';
      document.body.classList.remove('rd-has-tray'); return;
    }
    tray.style.display = 'flex';
    document.body.classList.add('rd-has-tray');
    const chips = [...compareIds].map(id => {
      const card = tarjetaConId(id);
      const modelo = card ? card.querySelector('.rd-card-modelo').textContent : id;
      return '<span class="rd-tray-chip">' + esc(modelo) + ' <span data-id="' + esc(id) + '" class="rd-tray-x">✕</span></span>';
    }).join('');
    tray.innerHTML =
      '<span class="rd-tray-label">' + t('Comparando ', 'Comparing ') + compareIds.size + '</span>' +
      '<div class="rd-tray-chips">' + chips + '</div>' +
      '<button id="rd-tray-btn" class="rd-tray-btn" type="button">' + t('Ver comparación', 'See comparison') + '</button>' +
      '<button id="rd-tray-clear" class="rd-tray-clear" type="button" aria-label="' + t('Vaciar comparación', 'Clear comparison') + '">✕</button>';
    tray.querySelectorAll('.rd-tray-x').forEach(x => x.addEventListener('click', e => {
      e.preventDefault();
      const id = e.target.dataset.id;
      compareIds.delete(id); marcarTodas(id, false); renderTray();
    }));
    document.getElementById('rd-tray-clear').addEventListener('click', () => {
      [...compareIds].forEach(id => marcarTodas(id, false));
      compareIds.clear(); cerrar(); renderTray();
    });
    document.getElementById('rd-tray-btn').addEventListener('click', abrir);
    // Alto real de la barra → el botón de WhatsApp se coloca justo encima (móvil)
    document.body.style.setProperty('--rd-tray-h', tray.offsetHeight + 'px');
  }

  function cabecera(id) {
    const card = tarjetaConId(id);
    if (!card) return { foto: '', modelo: id, version: '', precio: '', href: '#' };
    const img = card.querySelector('.rd-card-photos img.activa') || card.querySelector('.rd-card-photos img');
    return {
      foto: img ? img.src : '', href: card.getAttribute('href') || '#',
      modelo: card.querySelector('.rd-card-modelo').textContent,
      version: card.querySelector('.rd-card-version').textContent,
      precio: card.querySelector('.rd-card-precio').textContent,
    };
  }

  // Índices de las columnas con el mejor dato (vacío si no aplica o si empatan todas)
  function mejores(regla, clave, cols) {
    if (!regla) return [];
    const nums = cols.map(c => regla === 'dgt' ? RANGO_DGT[(c.v || {}).dgt] : (c.n || {})[clave]);
    const validos = nums.filter(x => typeof x === 'number');
    if (validos.length < 2) return [];
    const mejor = (regla === 'min') ? Math.min(...validos) : Math.max(...validos);
    if (validos.every(x => x === mejor)) return [];
    return nums.map((x, i) => x === mejor ? i : -1).filter(i => i >= 0);
  }

  function fila(etq, celdas, oculta) {
    return '<tr' + (oculta ? ' class="rd-cx-igual"' : '') + '><th scope="row">' + esc(etq) + '</th>' + celdas.join('') + '</tr>';
  }

  function dibujar() {
    const ids = [...compareIds];
    const cols = ids.map(id => (datos && datos[id]) || { v: {}, n: {}, eq: [] });
    const cab = ids.map(cabecera);
    const nCols = ids.length;
    let h = '<table class="rd-cx-tabla"><thead><tr><th></th>' + cab.map(c =>
      '<th><a class="rd-cx-car" href="' + esc(c.href) + '"><img src="' + esc(c.foto) + '" alt="' + esc(c.modelo) + '">' +
      '<b>' + esc(c.modelo) + '</b><small>' + esc(c.version) + '</small><span class="rd-cx-precio">' + esc(c.precio) + '</span></a></th>'
    ).join('') + '</tr></thead><tbody>';

    GRUPOS.forEach(([gEs, gEn, filas]) => {
      let cuerpo = '';
      filas.forEach(([clave, es, eng, regla]) => {
        const vals = cols.map(c => (c.v || {})[clave]);
        if (vals.every(v => !v)) return;                          // ningún coche tiene el dato
        const gana = mejores(regla, clave, cols);
        const maxMal = clave === 'maletero' ? Math.max(...cols.map(c => (c.n || {}).maletero || 0)) : 0;
        const celdas = vals.map((v, i) => {
          let txt = v ? esc(valorTxt(v)) : '—';
          if (clave === 'maletero' && maxMal && (cols[i].n || {}).maletero) {
            txt += '<span class="rd-cx-barra"><span style="width:' + Math.round(cols[i].n.maletero / maxMal * 100) + '%"></span></span>';
          }
          return '<td class="' + (gana.includes(i) ? 'rd-cx-gana' : '') + '">' + txt + '</td>';
        });
        const iguales = nCols > 1 && vals.every(v => v === vals[0]);
        cuerpo += fila(t(es, eng), celdas, iguales);
      });
      if (gEs === 'Equipamiento' && chkEq && chkEq.checked) {
        const todos = new Map();
        cols.forEach(c => (c.eq || []).forEach(([es_, en_, de_]) => { if (!todos.has(es_)) todos.set(es_, [en_, de_]); }));
        [...todos].sort((a, b) => a[0].localeCompare(b[0], 'es')).forEach(([es_, [en_, de_]]) => {
          const tiene = cols.map(c => (c.eq || []).some(x => x[0] === es_));
          const celdas = tiene.map(s => s ? '<td class="rd-cx-si">✓</td>' : '<td class="rd-cx-no">—</td>');
          cuerpo += fila(t(es_, en_, de_), celdas, nCols > 1 && tiene.every(Boolean));
        });
      }
      if (cuerpo) h += '<tr class="rd-cx-grupo"><td colspan="' + (nCols + 1) + '">' + t(gEs, gEn) + '</td></tr>' + cuerpo;
    });
    h += '</tbody></table>';
    tabla.innerHTML = h;
    tabla.classList.toggle('rd-cx-solo-dif', !!(chkDif && chkDif.checked));
  }

  function abrir() {
    overlay.style.display = 'flex';
    document.body.classList.add('rd-cx-abierto');
    if (datos) { dibujar(); return; }
    tabla.innerHTML = '<p class="rd-cx-cargando">' + t('Cargando fichas…', 'Loading specs…') + '</p>';
    fetch(window.RD_CMP_URL || '/comparador.json')
      .then(r => r.json()).then(j => { datos = j; dibujar(); })
      .catch(() => { datos = {}; dibujar(); });
  }
  function cerrar() { overlay.style.display = 'none'; document.body.classList.remove('rd-cx-abierto'); }

  // ── Imprimir la comparación (solo modo asesor: clase rd-asesor en <html>, ver enviar.js) ──
  // Misma tabla que se ve en pantalla (respeta "solo lo que cambia" y "equipamiento
  // completo"), en A4 y pensada también para impresora en blanco y negro: grupos en rojo
  // sin franja negra, mejor dato con ★ y fondo suave, filas iguales en gris.
  const CSS_IMP = `
html:not(.rd-asesor) .rd-cx-imprimir { display: none !important; }
.rd-cx-imprimir { border: 0; border-radius: 999px; background: #14110f; color: #fff; padding: 8px 14px; cursor: pointer;
  font: 700 12px var(--rd-font, sans-serif); letter-spacing: .4px; }
.rd-cx-imprimir small { opacity: .7; font-size: 9.5px; text-transform: uppercase; letter-spacing: .5px; }
#rd-cx-print { display: none; }
@media print {
  @page { size: A4 portrait; margin: 10mm; }
  html, body { background: #fff !important; margin: 0 !important; padding: 0 !important; overflow: visible !important; }
  body > *:not(#rd-cx-print) { display: none !important; }
  #rd-cx-print { display: block !important; }
}
#rd-cx-print, #rd-cx-print * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
#rd-cx-print { width: 190mm; color: #14110f; font-family: 'Work Sans', Arial, sans-serif; font-size: 8.5pt; line-height: 1.3; background: #fff; }
.cxp-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 6mm; border-bottom: 3pt solid #C8232B; padding-bottom: 2mm; }
.cxp-marca { font: 700 20pt/1 'Oswald', 'Arial Narrow', sans-serif; text-transform: uppercase; }
.cxp-tit { font: 600 11pt 'Oswald', 'Arial Narrow', sans-serif; text-transform: uppercase; letter-spacing: .6pt; color: #C8232B; margin-top: 1mm; }
.cxp-contacto { text-align: right; font-size: 8.5pt; line-height: 1.45; white-space: nowrap; }
.cxp-contacto b { font-size: 11pt; }
#rd-cx-print .rd-cx-tabla { width: 100%; border-collapse: collapse; margin-top: 3mm; table-layout: fixed; }
#rd-cx-print .rd-cx-tabla thead th { position: static; background: #fff; padding: 0 2mm 2mm; vertical-align: top; }
#rd-cx-print .rd-cx-tabla thead th:first-child { width: 56mm; }
#rd-cx-print .rd-cx-car img { width: 100%; height: 30mm; aspect-ratio: auto; object-fit: cover; border-radius: 1.5mm; }
#rd-cx-print .rd-cx-car b { font: 700 11pt 'Oswald', 'Arial Narrow', sans-serif; margin-top: 1.5mm; }
#rd-cx-print .rd-cx-car small { font-size: 7pt; min-height: 0; color: #444; }
#rd-cx-print .rd-cx-precio { font: 700 15pt 'Oswald', 'Arial Narrow', sans-serif; color: #C8232B; }
#rd-cx-print tr { break-inside: avoid; page-break-inside: avoid; }
#rd-cx-print .rd-cx-tabla tr.rd-cx-grupo td { background: #fff; color: #C8232B; font: 700 9.5pt 'Oswald', 'Arial Narrow', sans-serif;
  letter-spacing: .8pt; padding: 3mm 2mm 1mm; border-bottom: 1.5pt solid #C8232B; }
#rd-cx-print .rd-cx-tabla tbody th, #rd-cx-print .rd-cx-tabla tbody td { padding: 1.1mm 2mm; font-size: 8.5pt; border-bottom: .5pt solid #cbc5bc; background: #fff; }
#rd-cx-print .rd-cx-tabla tbody th { color: #5d5650; font-weight: 600; font-size: 7.6pt; line-height: 1.25; text-align: left; }
#rd-cx-print .rd-cx-tabla td.rd-cx-gana { background: #e9f4eb; font-weight: 700; }
#rd-cx-print .rd-cx-tabla td.rd-cx-gana::after { content: ' ★'; color: #14110f; font-size: 8pt; }
#rd-cx-print tr.rd-cx-igual td, #rd-cx-print tr.rd-cx-igual th { color: #8a847c; }
#rd-cx-print .rd-cx-si { color: #14110f; font-weight: 700; }
#rd-cx-print .rd-cx-barra { height: 1.2mm; background: #e2ded7; }
#rd-cx-print .rd-cx-barra span { background: #8a847c; }
.cxp-pie { margin-top: 3mm; border-top: 1.5pt solid #C8232B; padding-top: 1.5mm; display: flex; justify-content: space-between; gap: 4mm; font-size: 7pt; color: #333; }
`;
  if (!document.getElementById('rd-cx-print-css')) {
    const st = document.createElement('style');
    st.id = 'rd-cx-print-css';
    st.textContent = CSS_IMP;
    document.head.appendChild(st);
  }
  const herramientas = chkDif && chkDif.closest('.rd-cx-tools');
  if (herramientas) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'rd-cx-imprimir';
    b.innerHTML = '🖨 Imprimir comparación <small>· solo asesor</small>';
    b.addEventListener('click', imprimirComparacion);
    herramientas.appendChild(b);
  }
  function imprimirComparacion() {
    if (!compareIds.size || !tabla.querySelector('table')) return;
    let asesor = {};
    try { asesor = JSON.parse((document.getElementById('rd-folleto-datos') || {}).textContent || '{}').asesor || {}; } catch (_) {}
    let hoja = document.getElementById('rd-cx-print');
    if (!hoja) { hoja = document.createElement('div'); hoja.id = 'rd-cx-print'; document.body.appendChild(hoja); }
    const hoy = new Date().toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
    hoja.innerHTML = `
  <div class="cxp-head">
    <div><div class="cxp-marca">Automóviles Rueda</div><div class="cxp-tit">${esc(t('Comparativa de coches', 'Car comparison'))} · ${hoy}</div></div>
    <div class="cxp-contacto">${asesor.nombre ? `${esc(asesor.nombre)} · <b>${esc(asesor.telefono)}</b><br>${esc(asesor.email)}<br>${esc(asesor.web)}` : ''}</div>
  </div>
  ${tabla.innerHTML}
  <div class="cxp-pie"><span>★ ${esc(t('mejor dato de la fila', 'best value in the row'))}${chkDif && chkDif.checked ? '' : ' · ' + esc(t('en gris: lo que coincide en todos', 'in grey: identical in all cars'))}</span><span>${esc(t('Datos de la ficha técnica · precios a', 'Spec data · prices on'))} ${hoy}</span></div>`;
    // "Solo lo que cambia": en pantalla se ocultan por CSS; en papel se quitan
    if (chkDif && chkDif.checked) hoja.querySelectorAll('tr.rd-cx-igual').forEach(tr => tr.remove());
    hoja.querySelectorAll('a').forEach(a => a.removeAttribute('href'));
    const fotos = Array.from(hoja.querySelectorAll('img')).filter(i => !i.complete).map(i => new Promise(ok => { i.onload = i.onerror = ok; }));
    Promise.race([Promise.all(fotos), new Promise(ok => setTimeout(ok, 3000))]).then(() => window.print());
  }

  document.getElementById('rd-overlay-close').addEventListener('click', cerrar);
  overlay.addEventListener('click', e => { if (e.target === overlay) cerrar(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && overlay.style.display === 'flex') cerrar(); });
  if (chkDif) chkDif.addEventListener('change', () => tabla.classList.toggle('rd-cx-solo-dif', chkDif.checked));
  if (chkEq) chkEq.addEventListener('change', () => { if (datos) dibujar(); });

  document.body.addEventListener('click', e => {
    const btn = e.target.closest('.rd-compare-btn');
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const card = btn.closest('.rd-card');
    if (card) toggleCompare(card);
  });
})();
