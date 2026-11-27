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

  var pc = function (x) { return x == null ? '' : x.toFixed(1).replace('.', ',') + ' %'; };
  var sg = function (n) { return (n < 0 ? '−' : '') + eur(Math.abs(n)); };
  // Cuenta del margen, paso a paso: Excel (con IVA) → IVA → sin IVA → transferencia → FINAL
  function desgloseMargen(r) {
    var m = A.margenNeto(r.venta, r.compra, r.gastos, r.regimen, r.margen); if (!m) return fila('Margen', '—');
    var rebu = /rebu/i.test(r.regimen || ''), ng = m.final < 0;
    return fila('Margen del Excel <small>(venta − compra − gastos, con IVA)</small>', sg(m.bruto), r.venta ? pc(m.bruto / r.venta * 100) + ' de la venta' : '') +
      fila('− IVA del margen <small>(21/121' + (rebu ? ', REBU: solo sobre el margen' : '') + ')</small>', sg(-m.iva)) +
      fila('= Margen sin IVA', '<b>' + sg(m.neto) + '</b>') +
      fila('− Gasto de transferencia', sg(-m.transf)) +
      fila('<b>= MARGEN FINAL</b> <small>(sin IVA, tras transferencia)</small>', '<b class="' + (ng ? 'rd-gest-neg' : '') + '" style="font-size:1.15em">' + sg(m.final) + '</b>', m.pct != null ? '<b>' + pc(m.pct) + '</b> <small>de la venta sin IVA (' + eur(m.ventaNeta) + ')</small>' : '');
  }

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
  // Tarjeta con TODO lo del Excel de stock que la web no muestra (solo asesor; no se imprime ni se enseña al cliente)
  function tarjetaStock(r) {
    var x = r.x || {}, si = function (v) { return v === true ? 'Sí' : v === false ? 'No' : v; }, g = function (k) { return x[k] != null ? esc(si(x[k])) : ''; };
    var f = function (t, v) { return v !== '' && v != null ? '<div class="rd-tk-f"><span>' + t + '</span><b>' + v + '</b></div>' : ''; };
    var gastos = ['g_garantia', 'g_reacond', 'g_gestoria', 'g_gestoria_int'].filter(function (k) { return x[k]; }).map(function (k) { return ({ g_garantia: 'garantía y certificación', g_reacond: 'reacondicionamiento', g_gestoria: 'gestoría', g_gestoria_int: 'gestoría interna' })[k] + ' ' + eur(x[k]); }).join(' · ');
    var cuerpo = f('Matrícula', esc(r.matricula)) + f('Bastidor', esc(r.bastidor)) + f('Origen', esc(r.origen)) + f('Estado', esc(r.estado)) + f('Régimen', esc(r.regimen)) +
      f('Matriculación', esc(r.f_matric)) + f('Año modelo', g('modelo_year')) + f('Color', g('color')) + f('Combustible', g('combustible')) + f('Cambio', g('cambio')) +
      f('Modelo (VO)', g('model_vo')) + f('TMAIMG', esc(r.tmaimg)) + f('Eurotax', g('eurotax')) + f('Id ocasión', g('id_ocasion')) +
      f('Garantía (meses)', g('garantia')) + f('Programa', g('cpo')) + f('Destacado', g('destacado')) +
      f('Alta en inventario', g('f_creacion')) + f('Fecha de compra', g('f_compra')) + f('Disponible desde', g('f_disp')) + f('Publicado en la marca', g('pub_marca')) + f('Publicado en Motorflash', g('pub_mf')) +
      f('Requiere atención', g('atencion')) + f('Zona', g('zona')) + f('Días en stock', r.dias != null ? Math.round(r.dias) : '') + f('Gastos', gastos);
    if (!cuerpo) return '';
    return '<details class="rd-tk"><summary>🗂️ Datos del stock <small>(solo asesor · no se imprime)</small></summary><div class="rd-tk-g">' + cuerpo + '</div></details>';
  }
  // Aviso GRANDE arriba de la ficha (solo modo asesor, no se imprime): el coche está publicado pero en el stock NO está disponible para la venta
  function bannerEstado(r) {
    var b = document.getElementById('rd-gest-banner'); if (!b) return;
    var e = r ? String(r.estado || '').toLowerCase() : '', d = r ? r.dias : null, h = '', cls = '';
    if (/^alta/.test(e)) { cls = 'rojo'; h = '<b>⛔ COCHE NO DISPONIBLE PARA LA VENTA · ESTADO «ALTA»</b><span>Posible reserva en otra web (Das WeltAuto, Motorflash…). <u>CONSULTAR antes de ofrecerlo al cliente.</u></span>'; }
    else if (/reacond/.test(e)) { cls = 'ambar'; h = '<b>🔧 EN REACONDICIONAMIENTO · NO DISPONIBLE PARA LA VENTA TODAVÍA</b><span>Consultar fecha de entrega antes de ofrecerlo.</span>'; }
    else if (/disponible/.test(e) && d != null && d < 0) { cls = 'ambar'; h = '<b>⏳ AÚN NO SE PUEDE VENDER COMO OCASIÓN</b><span>Faltan ' + Math.round(-d) + ' días (3 meses desde la matriculación). Consultar.</span>'; }
    if (!h) { b.hidden = true; b.innerHTML = ''; return; }
    b.className = 'rd-gest-banner ' + cls; b.innerHTML = h; b.hidden = false;
  }

  // ---- «Comparar con el mercado» (enlaces ya filtrados, sin rastrear nada) y «Cómo vendimos coches parecidos» (con nuestras entregas). Solo asesor.
  var sa = function (t) { return String(t == null ? '' : t).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim(); };
  var redondea = function (n, m) { return Math.round(n / m) * m; };
  function perfil(r) {
    var mm = String(COCHE.modelo || '').split(' '), marca = sa(mm[0]), modelo = sa(mm.slice(1).join(' ')).replace(/ /g, '_');
    var anio = parseInt((String(r.f_matric || '').match(/(\d{4})\s*$/) || String(COCHE.fecha || '').match(/(\d{4})\s*$/) || [])[1], 10);
    var km = r.km != null && r.km !== '' ? Number(r.km) : A.num(COCHE.km);
    var kf = km < 2500 ? 0 : Math.floor(km * 0.65 / 5000) * 5000, kt = Math.max(kf + (km < 2500 ? 5000 : 10000), Math.ceil(km * 1.35 / 5000) * 5000);
    return { marca: marca, modelo: modelo, anio: anio, km: km, kf: kf, kt: kt, precio: web };
  }
  function tarjetaMercado(r) {
    var p = perfil(r); if (!p.marca || !p.modelo || !p.anio) return '';
    var as = 'https://www.autoscout24.es/lst/' + p.marca + '/' + p.modelo.replace(/_/g, '-') + '/re_' + p.anio + '?cy=E&kmfrom=' + p.kf + '&kmto=' + p.kt + '&sort=price&desc=0&ustate=N%2CU&atype=C&powertype=kw';
    var dwa = (p.marca === 'seat' || p.marca === 'cupra') ? 'https://www.dasweltauto.es/esp/' + p.marca + '-' + p.modelo + '-segunda-mano' : '';
    var btn = 'style="display:inline-block;margin:0 8px 6px 0;padding:7px 12px;border:1px solid rgba(0,0,0,.25);border-radius:8px;text-decoration:none;font-weight:600"';
    return '<details class="rd-tk"><summary>🔎 Comparar con el mercado <small>(solo asesor)</small></summary>' +
      '<p class="rd-gest-nota">Cada botón abre una pestaña nueva con la búsqueda ya filtrada: <b>' + esc(COCHE.modelo) + ' de ' + p.anio + '</b>, entre <b>' + p.kf.toLocaleString('es-ES') + '</b> y <b>' + p.kt.toLocaleString('es-ES') + ' km</b>, del más barato al más caro. Nuestro precio: <b>' + eur(p.precio) + '</b>.</p>' +
      '<a ' + btn + ' href="' + esc(as) + '" target="_blank" rel="noopener">AutoScout24 ↗</a>' + (dwa ? '<a ' + btn + ' href="' + esc(dwa) + '" target="_blank" rel="noopener">Das WeltAuto, toda España ↗</a>' : '') +
      '<p class="rd-gest-nota">Ojo: casi todos los portales destacan el <b>precio financiado</b> (más bajo); compara con el precio de contado que sale dentro de cada ficha. En Das WeltAuto el año y los km se ajustan con sus filtros.</p></details>';
  }
  function parecidos(r, E, amplio) {
    var p = perfil(r), marcaN = p.marca, fam = sa(p.modelo).split('_')[0];
    return (E || []).filter(function (v) {
      var tk = sa(v.coche).split(' '), m = sa(v.marca || tk[0]), f = tk[0] === m ? tk[1] : tk[0], y = parseInt(String(v.f_matric || '').slice(0, 4), 10), k = Number(v.km);
      if (m !== marcaN || f !== fam || !v.venta) return false;
      var okY = amplio ? Math.abs(y - p.anio) <= 1 : y === p.anio, okK = amplio ? (k >= p.km * 0.4 - 2000 && k <= p.km * 2.2 + 3000) : (k >= p.kf && k <= p.kt);
      return okY && okK;
    });
  }
  function tarjetaVendidos(r, E) {
    var p = perfil(r), L = parecidos(r, E, false), amplio = false;
    if (L.length < 2) { L = parecidos(r, E, true); amplio = true; }
    var med = function (a, k) { var b = a.filter(function (x) { return x[k] != null; }); return b.length ? b.reduce(function (s, x) { return s + Number(x[k]); }, 0) / b.length : null; };
    var pm = med(L, 'venta'), dm = med(L, 'dias'), mm = med(L.map(function (x) { var q = x.margen != null ? A.margenNeto(null, null, 0, '', Number(x.margen)) : null; return { margen: q ? q.final : null }; }), 'margen');
    var iguales = (datos && datos.stock ? datos.stock : []).filter(function (s) { return s.publicado && s.bastidor !== r.bastidor && s.coche === rec_coche(r) && s.venta && p.precio && Math.abs(s.venta - p.precio) <= 500; });
    var caja = function (t, v, sub) { return '<div style="background:rgba(0,0,0,.04);border-radius:8px;padding:8px 12px"><div style="font-size:11px;opacity:.65;text-transform:uppercase">' + t + '</div><div style="font-size:20px;font-weight:700">' + v + '</div><div style="font-size:12px;opacity:.7">' + sub + '</div></div>'; };
    var cab = '<details class="rd-tk"><summary>📊 Cómo vendimos coches parecidos <small>(solo asesor)</small></summary>';
    if (!L.length) return cab + '<p class="rd-gest-nota">Todavía no hay entregas de ' + esc(COCHE.modelo) + ' parecidas en nuestro historial (se va llenando con cada carga de «Entregas VO»).</p>' + avisoIguales(iguales) + '</details>';
    var dif = p.precio && pm != null ? p.precio - pm : null;
    return cab + '<p class="rd-gest-nota">' + esc(COCHE.modelo) + ', ' + (amplio ? 'año ±1 y km parecidos (ampliado porque había pocos)' : 'de ' + p.anio + ' y entre ' + p.kf.toLocaleString('es-ES') + ' y ' + p.kt.toLocaleString('es-ES') + ' km') + '. <b>Muestra: ' + L.length + ' coche(s)</b>' + (L.length < 5 ? ' — poca, tómalo como orientación' : '') + '.</p>' +
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:8px 0">' +
      caja('Precio al que se fueron', eur(pm), dif == null ? '' : (dif === 0 ? 'igual que el nuestro' : 'este está ' + eur(Math.abs(dif)) + (dif < 0 ? ' por debajo' : ' por encima'))) +
      caja('Días hasta vender', dm == null ? '—' : Math.round(dm) + ' días', 'media') + caja('Margen final medio', eur(mm), 'sin IVA, tras transferencia') + '</div>' +
      '<table class="rd-gest-tabla"><tr><th>Coche vendido</th><th>Km</th><th>Venta</th><th>Días</th><th>Origen</th></tr>' +
      L.sort(function (a, b) { return String(b.fecha).localeCompare(String(a.fecha)); }).slice(0, 8).map(function (v) { return '<tr><td>' + esc(String(v.coche || '').replace(/^(SEAT|CUPRA|KIA|RENAULT|SKODA) /i, '')).slice(0, 42) + '</td><td class="n">' + Number(v.km).toLocaleString('es-ES') + '</td><td class="n">' + eur(v.venta) + '</td><td class="n">' + (v.dias != null ? v.dias : '—') + '</td><td>' + esc(v.origen || '') + '</td></tr>'; }).join('') + '</table>' + avisoIguales(iguales) + '</details>';
  }
  function rec_coche(r) { var x = (datos && datos.stock || []).filter(function (s) { return s.bastidor === r.bastidor; })[0]; return x ? x.coche : ''; }
  function avisoIguales(ig) { return ig.length >= 2 ? '<div class="rd-gest-aviso ambar">⚠ Tenemos <b>' + (ig.length + 1) + '</b> iguales publicados a precio casi idéntico (±500 €): se compiten entre sí.</div>' : ''; }
  function mercadoYVendidos(r) {
    if (!r) return;
    var a = document.getElementById('rd-merc'), b = document.getElementById('rd-vend');
    if (a) a.innerHTML = tarjetaMercado(r);
    var E = (datos && datos.entregas ? datos.entregas : []).slice();
    if (b) b.innerHTML = tarjetaVendidos(r, E);
    if (A.ventasAlmacen) A.ventasAlmacen().then(function (rows) {   // entregas cargadas desde el botón (almacén común), por si son más recientes que los datos cifrados
      var cl = {}; E.forEach(function (x) { cl[(x.matricula || '') + '|' + x.fecha] = 1; }); var n = 0;
      rows.forEach(function (x) { var k = (x.matricula || '') + '|' + x.fecha; if (!cl[k]) { cl[k] = 1; E.push({ matricula: x.matricula, coche: x.coche, marca: x.marca, f_matric: x.f_matric, km: x.km, venta: x.venta, compra: x.compra, margen: x.margen, dias: x.dias_stock, origen: x.origen, fecha: x.fecha }); n++; } });
      if (n && b) { var abierto = b.querySelector('details') && b.querySelector('details').open; b.innerHTML = tarjetaVendidos(r, E); if (abierto) b.querySelector('details').open = true; }
    }).catch(function () {});
  }
  function pintar() {
    window.RD_GESTION = rec; resolver(rec);
    bannerEstado(rec);
    if (!datos) return;
    var f = datos.generado.split('-').reverse().join('/'), pie = '<p class="rd-gest-nota"><a href="/stock/" target="_blank" rel="noopener">Ver todo el stock ↗</a> · <a href="/comparativa/" target="_blank" rel="noopener">Comparativa ocasión/nuevo ↗</a> · datos de ' + esc(datos.fuente) + ' del ' + f + '</p>';
    if (!rec) { cuerpo.innerHTML = '<p class="rd-gest-nota">Este coche no está en el stock cargado.</p>' + similares() + pie; return; }
    var dif = rec.venta && web && Math.abs(rec.venta - web) > 1, neg = rec.margen != null && rec.margen < 0;
    var campana = /^(demo|rema|km ?0)/i.test(rec.origen || '') ? 'Origen ' + rec.origen + ': aplica la campaña de VWFS «DEMOS + REMA» (TIN 5,99 %)' : /buy ?back/i.test(rec.origen || '') ? 'Origen Buy Back: campaña GAMA / ENTRY estándar' : '';
    cuerpo.innerHTML = avisos(rec) + '<table class="rd-gest-tabla">' +
      fila('Precio de compra', eur(rec.compra)) + fila('Gastos (garantía, reacondicionamiento, gestoría)', eur(rec.gastos)) +
      fila('Precio de venta en stock', eur(rec.venta), dif ? '<b class="rd-gest-alerta">⚠ la web publica ' + eur(web) + '</b>' : '') +
      desgloseMargen(rec) + '</table>' +
      '<div class="rd-gest-neg-box"><b>Negociar:</b> si el cliente paga <input type="number" id="rd-gest-precio" step="100" value="' + (web || rec.venta || '') + '"> € → margen <b id="rd-gest-res"></b> <span class="rd-gest-nota" id="rd-gest-dto"></span></div>' +
      '<table class="rd-gest-tabla rd-gest-ficha">' + fila('Origen', esc(rec.origen) || '—', campana) + fila('Régimen', esc(rec.regimen) || '—', rec.regimen === 'REBU' ? 'IVA solo sobre el margen' : rec.regimen === 'IVA' ? 'IVA sobre el precio completo' : '') +
      fila('Días en stock', rec.dias != null ? Math.round(rec.dias) : '—') + fila('Estado en stock', esc(rec.estado) || '—') + fila('Matrícula · matriculación', esc(rec.matricula) + ' · ' + esc(rec.f_matric)) + fila('Bastidor', esc(rec.bastidor)) + fila('TMAIMG', esc(rec.tmaimg)) + '</table>' + tarjetaStock(rec) + '<div id="rd-merc"></div><div id="rd-vend"></div>' +
      similares() + pie;
    mercadoYVendidos(rec);
    var inp = document.getElementById('rd-gest-precio');
    var calc = function () { var p = parseFloat(inp.value) || 0, m = A.margenNeto(p, rec.compra, rec.gastos, rec.regimen), el = document.getElementById('rd-gest-res'), mw = web && rec.compra ? A.margenNeto(web, rec.compra, rec.gastos, rec.regimen) : null;
      el.textContent = m ? sg(m.final) + (m.pct != null ? ' (' + pc(m.pct) + ')' : '') + ' final · ' + sg(m.neto) + ' sin IVA antes de la transferencia' : '—'; el.className = m && m.final < 0 ? 'rd-gest-neg' : '';
      document.getElementById('rd-gest-dto').textContent = web ? 'Descuento sobre el precio web: ' + eur(web - p) + (mw ? ' · margen final al precio web: ' + sg(mw.final) : '') : ''; };
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
