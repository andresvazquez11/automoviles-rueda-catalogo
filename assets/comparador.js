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

  const en = () => (window.rdIdiomaActual && window.rdIdiomaActual() === 'en') || document.documentElement.lang === 'en';
  const t = (es, eng) => (en() ? eng : es);
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
  const valorTxt = v => (en() && TRAD[v]) ? TRAD[v] : v;

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
        cols.forEach(c => (c.eq || []).forEach(([es_, en_]) => { if (!todos.has(es_)) todos.set(es_, en_); }));
        [...todos].sort((a, b) => a[0].localeCompare(b[0], 'es')).forEach(([es_, en_]) => {
          const tiene = cols.map(c => (c.eq || []).some(x => x[0] === es_));
          const celdas = tiene.map(s => s ? '<td class="rd-cx-si">✓</td>' : '<td class="rd-cx-no">—</td>');
          cuerpo += fila(t(es_, en_), celdas, nCols > 1 && tiene.every(Boolean));
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
