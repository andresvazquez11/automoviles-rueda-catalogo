// Solo asesor, en la ficha: datos de gestión del coche (compra, margen, negociación, origen) y stock parecido aunque no esté publicado.
// Usa assets/asesor.js (datos cargados del Excel en este dispositivo o publicados cifrados).
(function () {
  var det = document.getElementById('rd-gestion');
  if (!det || typeof COCHE === 'undefined' || !window.RD_ASESOR) return;
  var A = window.RD_ASESOR, cuerpo = document.getElementById('rd-gestion-cuerpo'), resolver, datos = null, rec = null;
  window.RD_GESTION_LISTO = new Promise(function (ok) { resolver = ok; });
  var eur = A.eur, web = A.num(COCHE.precio);
  var esc = function (t) { return String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
  var fila = function (a, b, c) { return '<tr><td>' + a + '</td><td class="n">' + b + '</td><td>' + (c || '') + '</td></tr>'; };

  // Estado del coche en el stock: avisos para el asesor
  function avisos(r) {
    var e = String(r.estado || '').toLowerCase(), d = r.dias, o = [];
    if (/cartera/.test(e)) o.push(['rojo', '🔴 <b>En cartera: ya está vendido</b> (falta finalizar la operación).']);
    else if (/^alta/.test(e)) o.push(['ambar', '🟠 <b>Alta:</b> aún no está disponible ni publicado; puede estar reservado fuera de la web.']);
    else if (/disponible/.test(e)) o.push(['verde', '🟢 <b>Disponible para la venta.</b>']);
    else if (/reacond/.test(e)) o.push(['azul', '🔧 <b>En reacondicionamiento.</b>']);
    if (d != null && d < 0) o.push(['ambar', '⏳ <b>Aún no se puede vender como ocasión:</b> faltan ' + Math.round(-d) + ' días (la marca exige 3 meses desde la matriculación). Algunos se venden igual.']);
    return o.map(function (a) { return '<div class="rd-gest-aviso ' + a[0] + '">' + a[1] + '</div>'; }).join('');
  }
  function punto(s) { var e = String(s.estado || '').toLowerCase(); return (/cartera/.test(e) ? '🔴' : /^alta/.test(e) ? '🟠' : /disponible/.test(e) ? '🟢' : '🔧') + ((s.dias != null && s.dias < 0) ? '⏳' : '') + ' '; }
  function similares() {
    if (!datos || !datos.stock) return '';
    var t = (rec && rec.tmaimg) || '', fam = A.familia(COCHE.modelo);
    var xs = datos.stock.filter(function (s) { return s.bastidor !== (rec && rec.bastidor) && A.familia(s.coche) === fam; }).map(function (s) {
      var p = (s.tmaimg && s.tmaimg === t ? 4 : (s.tmaimg && t && s.tmaimg.slice(0, 3) === t.slice(0, 3) ? 2 : 0)) - (s.venta && web ? Math.abs(s.venta - web) / 5000 : 1); return { s: s, p: p };
    }).sort(function (a, b) { return b.p - a.p; }).slice(0, 8);
    if (!xs.length) return '<p class="rd-gest-nota">No hay más ' + esc(COCHE.modelo) + ' en el stock cargado.</p>';
    return '<h4>Parecidos en stock <small>(aunque no estén publicados: busca por matrícula)</small></h4><table class="rd-gest-tabla rd-gest-sim"><tr><th>Coche (🟢 disponible · 🔴 vendido · 🟠 alta · ⏳ aún no vendible)</th><th>Matrícula</th><th>Km</th><th>Matric.</th><th>TMAIMG</th><th class="n">Venta</th><th>Estado</th></tr>' +
      xs.map(function (x) { var s = x.s; return '<tr class="' + (s.publicado ? '' : 'rd-gest-nopub') + '"><td>' + punto(s) + (s.publicado && s.ficha ? '<a href="' + esc(s.ficha) + '">' + esc(s.coche).slice(0, 44) + ' ↗</a>' : esc(s.coche).slice(0, 44)) + (s.publicado ? '' : ' <b>· sin publicar</b>') + '</td><td><b>' + esc(s.matricula) + '</b></td><td>' + (s.km != null ? Number(s.km).toLocaleString('es-ES') : '') +
        '</td><td>' + esc(s.f_matric) + '</td><td>' + esc(s.tmaimg) + '</td><td class="n">' + (s.venta ? eur(s.venta) + (s.estimado ? ' <span title="' + esc(s.base_est) + '">*</span>' : '') : 'sin precio') + '</td><td>' + esc(s.estado) + '</td></tr>'; }).join('') +
      '</table><p class="rd-gest-nota">* precio de venta estimado (compra × razón mediana de coches parecidos).</p>';
  }
  function pintar() {
    window.RD_GESTION = rec; resolver(rec);
    if (!datos) return;
    var f = datos.generado.split('-').reverse().join('/'), pie = '<p class="rd-gest-nota"><a href="/stock/" target="_blank" rel="noopener">Ver todo el stock ↗</a> · <a href="/comparativa/" target="_blank" rel="noopener">Comparativa ocasión/nuevo ↗</a> · datos de ' + esc(datos.fuente) + ' del ' + f + '</p>';
    if (!rec) { cuerpo.innerHTML = '<p class="rd-gest-nota">Este coche no está en el stock cargado.</p>' + similares() + pie; return; }
    var dif = rec.venta && web && Math.abs(rec.venta - web) > 1, neg = rec.margen != null && rec.margen < 0;
    var campana = /^(demo|rema|km ?0)/i.test(rec.origen || '') ? 'Origen ' + rec.origen + ': aplica la campaña de VWFS «DEMOS + REMA» (TIN 5,99 %)' : /buy ?back/i.test(rec.origen || '') ? 'Origen Buy Back: campaña GAMA / ENTRY estándar' : '';
    cuerpo.innerHTML = avisos(rec) + '<table class="rd-gest-tabla">' +
      fila('Precio de compra', eur(rec.compra)) + fila('Gastos (garantía, reacondicionamiento, gestoría)', eur(rec.gastos)) +
      fila('Precio de venta en stock', eur(rec.venta), dif ? '<b class="rd-gest-alerta">⚠ la web publica ' + eur(web) + '</b>' : '') +
      fila('<b>Margen</b> (precios con IVA)', '<b class="' + (neg ? 'rd-gest-neg' : '') + '">' + eur(rec.margen) + '</b>' + (rec.venta ? ' <small>(' + (rec.margen / rec.venta * 100).toFixed(1).replace('.', ',') + ' %)</small>' : '')) +
      fila('Margen sin IVA (estimado, ÷ 1,21)', eur(rec.margen_sin_iva)) + '</table>' +
      '<div class="rd-gest-neg-box"><b>Negociar:</b> si el cliente paga <input type="number" id="rd-gest-precio" step="100" value="' + (web || rec.venta || '') + '"> € → margen <b id="rd-gest-res"></b> <span class="rd-gest-nota" id="rd-gest-dto"></span></div>' +
      '<table class="rd-gest-tabla rd-gest-ficha">' + fila('Origen', esc(rec.origen) || '—', campana) + fila('Régimen', esc(rec.regimen) || '—', rec.regimen === 'REBU' ? 'IVA solo sobre el margen' : rec.regimen === 'IVA' ? 'IVA sobre el precio completo' : '') +
      fila('Días en stock', rec.dias != null ? Math.round(rec.dias) : '—') + fila('Estado en stock', esc(rec.estado) || '—') + fila('Matrícula · matriculación', esc(rec.matricula) + ' · ' + esc(rec.f_matric)) + fila('Bastidor', esc(rec.bastidor)) + fila('TMAIMG', esc(rec.tmaimg)) + '</table>' +
      similares() + pie;
    var inp = document.getElementById('rd-gest-precio');
    var calc = function () { var p = parseFloat(inp.value) || 0, m = p - rec.compra - (rec.gastos || 0), el = document.getElementById('rd-gest-res');
      el.textContent = eur(m) + ' (' + (p ? (m / p * 100).toFixed(1).replace('.', ',') : '0') + ' %)'; el.className = m < 0 ? 'rd-gest-neg' : '';
      document.getElementById('rd-gest-dto').textContent = web ? 'Descuento sobre el precio web: ' + eur(web - p) + ' · margen que quedaría para ceder: ' + eur(Math.max(0, rec.compra ? (web - rec.compra - (rec.gastos || 0)) : 0)) : ''; };
    inp.oninput = calc; calc();
  }
  function pedir(msg) {
    cuerpo.innerHTML = '<form class="rd-gest-form"><label>Contraseña de la zona privada</label><input type="password" autocomplete="current-password"><button type="submit" class="rd-btn rd-btn-secondary">Desbloquear</button><div class="rd-gest-nota">' + (msg || 'O carga el Excel de stock en la portada (modo asesor).') + '</div></form>';
    var f = cuerpo.querySelector('form');
    f.onsubmit = async function (ev) { ev.preventDefault(); try { datos = await A.obtener(f.querySelector('input').value); if (!datos) throw 0; rec = A.buscar(datos, COCHE); pintar(); } catch (e) { pedir('Contraseña incorrecta.'); } };
  }
  async function iniciar(visible) {
    datos = await A.obtener();
    if (datos) { rec = A.buscar(datos, COCHE); pintar(); } else { resolver(null); if (visible) pedir(''); }
  }
  det.addEventListener('toggle', function () { if (det.open && !datos) { cuerpo.textContent = 'Cargando…'; iniciar(true); } });
  if (document.documentElement.classList.contains('rd-asesor')) iniciar(false); else resolver(null);
})();
