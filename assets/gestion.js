// Solo asesor: datos de gestión de este coche (compra, margen, régimen, origen…).
// Los datos viajan CIFRADOS en /gestion.enc.json (AES-256-GCM, misma contraseña que /nuevos/): nada va en claro en la web.
(function () {
  var det = document.getElementById('rd-gestion');
  if (!det || typeof COCHE === 'undefined') return;
  var KEY = 'vn_clave', cuerpo = document.getElementById('rd-gestion-cuerpo'), datos = null, resolver;
  window.RD_GESTION_LISTO = new Promise(function (ok) { resolver = ok; });
  var b64 = function (s) { return Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); }); };
  var eur = function (n) { return n == null ? '—' : Math.round(n).toLocaleString('es-ES', { useGrouping: true }).replace(/,/g, '.') + ' €'; };
  async function cargar(clave) {
    var D = await (await fetch('/gestion.enc.json', { cache: 'no-store' })).json();
    var base = await crypto.subtle.importKey('raw', new TextEncoder().encode(clave), 'PBKDF2', false, ['deriveKey']);
    var key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: b64(D.s), iterations: D.n, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
    return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64(D.i) }, key, b64(D.c))));
  }
  function buscar(d) {
    var id = (String(COCHE.url || '').match(/(\d{6,})\/?$/) || [])[1];
    return (id && d.coches['a' + id]) || d.coches['n' + COCHE.n] || null;
  }
  function pintar(rec) {
    window.RD_GESTION = rec; resolver(rec);
    if (!rec) { cuerpo.innerHTML = '<p class="rd-gest-nota">Este coche no está en el stock cargado (Excel de stock del ' + datos.generado.split('-').reverse().join('/') + ').</p>'; return; }
    var web = parseInt(String(COCHE.precio).replace(/[^\d]/g, ''), 10) || 0, dif = rec.venta && web && Math.abs(rec.venta - web) > 1;
    var neg = rec.margen != null && rec.margen < 0;
    var fila = function (a, b, c) { return '<tr><td>' + a + '</td><td class="n">' + b + '</td>' + (c ? '<td>' + c + '</td>' : '<td></td>') + '</tr>'; };
    var campana = /^(demo|rema|km ?0)/i.test(rec.origen || '') ? 'Origen ' + rec.origen + ': aplica la campaña de VWFS «DEMOS + REMA» (TIN 5,99 %)' : /buy ?back/i.test(rec.origen || '') ? 'Origen Buy Back: campaña GAMA / ENTRY estándar' : '';
    cuerpo.innerHTML = '<table class="rd-gest-tabla">' +
      fila('Precio de compra', eur(rec.compra)) + fila('Gastos (garantía, reacondicionamiento, gestoría)', eur(rec.gastos)) +
      fila('Precio de venta en stock', eur(rec.venta), dif ? '<b class="rd-gest-alerta">⚠ la web publica ' + eur(web) + '</b>' : '') +
      fila('<b>Margen</b> (precios con IVA)', '<b class="' + (neg ? 'rd-gest-neg' : '') + '">' + eur(rec.margen) + '</b>' + (rec.venta ? ' <small>(' + (rec.margen / rec.venta * 100).toFixed(1).replace('.', ',') + ' %)</small>' : '')) +
      fila('Margen sin IVA (estimado, ÷ 1,21)', eur(rec.margen_sin_iva)) +
      '</table><table class="rd-gest-tabla rd-gest-ficha">' +
      fila('Origen', rec.origen || '—', campana) + fila('Régimen', rec.regimen || '—', rec.regimen === 'REBU' ? 'IVA solo sobre el margen' : rec.regimen === 'IVA' ? 'IVA sobre el precio completo' : '') +
      fila('Días en stock', rec.dias != null ? Math.round(rec.dias) : '—') + fila('Estado en stock', rec.estado || '—') +
      fila('Matrícula · matriculación', (rec.matricula || '—') + ' · ' + (rec.f_matric || '—')) + fila('Bastidor', rec.bastidor || '—') + fila('TMAIMG', rec.tmaimg || '—') + '</table>' +
      '<p class="rd-gest-nota"><a href="/stock/" target="_blank" rel="noopener">Ver todo el stock (incluido lo que aún no está publicado) ↗</a> · datos del Excel de stock del ' + datos.generado.split('-').reverse().join('/') + '</p>';
  }
  function pedir(msg) {
    cuerpo.innerHTML = '<form class="rd-gest-form"><label>Contraseña de la zona privada</label><input type="password" autocomplete="current-password"><label class="rd-gest-rec"><input type="checkbox" checked> Recordar en este dispositivo</label><button type="submit" class="rd-btn rd-btn-secondary">Desbloquear</button><div class="rd-gest-nota">' + (msg || '') + '</div></form>';
    var f = cuerpo.querySelector('form');
    f.onsubmit = async function (ev) {
      ev.preventDefault();
      var pw = f.querySelector('input[type=password]').value, rec = f.querySelector('input[type=checkbox]').checked;
      try { datos = await cargar(pw); try { if (rec) localStorage.setItem(KEY, pw); } catch (e) {} pintar(buscar(datos)); }
      catch (e) { pedir('Contraseña incorrecta.'); }
    };
  }
  async function abrir() {
    if (datos) return pintar(buscar(datos));
    var g = null; try { g = localStorage.getItem(KEY); } catch (e) {}
    if (g) { try { cuerpo.textContent = 'Descifrando…'; datos = await cargar(g); return pintar(buscar(datos)); } catch (e) { try { localStorage.removeItem(KEY); } catch (x) {} } }
    pedir('');
  }
  det.addEventListener('toggle', function () { if (det.open) abrir(); });
  // con la contraseña recordada, los datos (p. ej. el origen) se cargan solos en modo asesor y los usa la comparación con el nuevo
  if (document.documentElement.classList.contains('rd-asesor')) {
    var g = null; try { g = localStorage.getItem(KEY); } catch (e) {}
    if (g) cargar(g).then(function (d) { datos = d; pintar(buscar(d)); }).catch(function () { resolver(null); }); else resolver(null);
  } else resolver(null);
})();
