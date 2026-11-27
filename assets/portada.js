// Solo asesor, en la portada: barra de herramientas (nuevos, stock, cargar Excel). El margen de cada coche va DENTRO de la ficha (más discreto), no en la portada.
(function () {
  var barra = document.getElementById('rd-asesor-barra'), A = window.RD_ASESOR;
  if (!barra || !A) return;
  var esc = function (t) { return String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
  var tarjetas = function () { return Array.prototype.map.call(document.querySelectorAll('#rd-grid .rd-card'), function (c) {
    return { el: c, href: c.getAttribute('href') || '', n: c.dataset.n, id: ((c.getAttribute('href') || '').match(/(\d{6,})\.html/) || [])[1] || '', km: parseFloat(c.dataset.km) || 0, precio: parseFloat(c.dataset.precio) || 0 }; }); };
  var LSA = 'rd_ab_abierto', resumenHTML = '', resumenTimer = null, badge = '', forzarAbierto = false;
  var abierto = function () { if (forzarAbierto) return true; try { return localStorage.getItem(LSA) === '1'; } catch (e) { return false; } };
  var nm = { stock: 'Stock', entregas: 'Entregas VO', cartera: 'Cartera VO' }, gr = { seat: 'SEAT y resto', cupra: 'CUPRA' };
  var tabla = function (estado) {
    return '<div class="rd-ab-est">' + estado.map(function (e) { var ic = e.nivel === 'ok' ? '✅' : e.nivel === 'aviso' ? '⚠️' : '❌';
      return '<span class="rd-ab-chip ' + e.nivel + '">' + ic + ' ' + esc(e.nombre) + ' · ' + esc(e.texto) + (e.nivel === 'aviso' ? ' — toca sacarlo' : e.nivel === 'falta' ? ' — falta cargarlo' : '') + '</span>'; }).join('') + '</div>'; };
  var insignia = function (est) { var n = est.filter(function (e) { return e.nivel !== 'ok'; }).length; return n ? '⚠️ ' + n + ' carga(s) pendiente(s)' : '✅ cargas al día'; };
  function cuerpoResumen() { return resumenHTML ? '<button type="button" class="rd-ab-x" id="rd-ab-cerrar">✕ Cerrar</button>' + resumenHTML : ''; }
  async function pintar() {
    var d = await A.obtener();
    var estado = d ? 'Datos de ' + esc(d.fuente) + ' del ' + d.generado.split('-').reverse().join('/') + ' · ' + d.stock.length + ' coches' : 'Sin datos de stock: carga el Excel o desbloquea los publicados';
    var ab = abierto();
    barra.innerHTML = '<div class="rd-ab-cab" id="rd-ab-cab"><b>🧰 Herramientas del asesor</b><span class="rd-ab-insignia" id="rd-ab-insignia">' + esc(badge) + '</span>' + (d && d.alertas_n ? '<a class="rd-ab-alerta" href="/stock/" target="_blank" rel="noopener" onclick="event.stopPropagation()">🚨 ' + d.alertas_n + ' alerta(s) de publicación ↗</a>' : '') + '<span class="rd-ab-flecha" id="rd-ab-flecha">' + (ab ? '▾' : '▸') + '</span></div>' +
      '<div class="rd-ab-cuerpo" id="rd-ab-cuerpo"' + (ab ? '' : ' hidden') + '>' + '<a href="/nuevos/" target="_blank" rel="noopener">Vehículos nuevos ↗</a><a href="/stock/" target="_blank" rel="noopener">Stock completo ↗</a><a href="/comparativa/" target="_blank" rel="noopener">Comparativa ocasión/nuevo ↗</a><a href="/historial/" target="_blank" rel="noopener">Historial ↗</a>' +
      '<button type="button" id="rd-ab-excel">📥 Cargar Excel (stock, entregas y cartera)</button><input type="file" id="rd-ab-file" accept=".xlsx" multiple hidden>' +
      (d ? '' : '<button type="button" id="rd-ab-unlock">🔓 Desbloquear publicados</button>') + (A.local() ? '<button type="button" id="rd-ab-borrar">Borrar datos de este dispositivo</button>' : '') +
      '<span class="rd-ab-estado" id="rd-ab-estado">' + estado + '</span><div class="rd-ab-resumen" id="rd-ab-resumen">' + cuerpoResumen() + '</div></div>';
    var inp = document.getElementById('rd-ab-file'), st = document.getElementById('rd-ab-estado'), res = document.getElementById('rd-ab-resumen');
    document.getElementById('rd-ab-cab').onclick = function () { var c = document.getElementById('rd-ab-cuerpo'), ab2 = c.hidden; c.hidden = !ab2; forzarAbierto = false;
      document.getElementById('rd-ab-flecha').textContent = ab2 ? '▾' : '▸'; try { localStorage.setItem(LSA, ab2 ? '1' : '0'); } catch (e) {} };
    document.getElementById('rd-ab-excel').onclick = function () { inp.click(); };
    var cer = document.getElementById('rd-ab-cerrar'); if (cer) cer.onclick = function () { resumenHTML = ''; res.innerHTML = ''; clearTimeout(resumenTimer); };
    var ins = document.getElementById('rd-ab-insignia');
    A.estadoActual().then(function (e) { if (!e) return; badge = insignia(e); ins.textContent = badge;
      if (!resumenHTML) res.innerHTML = '<b>Estado de las cargas</b>' + tabla(e); }).catch(function () {});
    inp.onchange = async function () {
      if (!inp.files.length) return; st.textContent = 'Leyendo y guardando los archivos…'; forzarAbierto = true;
      try {
        var r = await A.cargarTodo(Array.prototype.slice.call(inp.files), tarjetas());
        var ok = r.informe.filter(function (i) { return i.ok; }).length, mal = r.informe.length - ok;
        resumenHTML = '<div class="rd-ab-ok ' + (mal ? 'mal' : '') + '"><b>' + (mal ? '⚠ Cargados ' + ok + ' de ' + r.informe.length + ' archivos' : '✓ Cargados correctamente ' + ok + ' archivo(s)') + '</b> · guardados cifrados en el almacén común</div><ul>' +
          r.informe.map(function (i) { return '<li>' + (i.ok ? '✅' : '❌') + ' «' + esc(i.nombre) + '» → ' + (i.ok ? '<b>' + nm[i.tipo] + ' · ' + gr[i.grupo] + '</b>' + (i.inferido ? ' <i>(no trae coches: deduzco que es ' + gr[i.grupo] + ')</i>' : '') + ': ' + esc(i.texto) : esc(i.texto)) + '</li>'; }).join('') +
          '</ul><b>Estado de las cargas</b>' + tabla(r.estado) + '<small>Si ves «toca sacarlo», ese Excel lleva varios días sin cargarse. Las ventas nuevas aparecen en «Historial ↗» (si no, espera 1 minuto y recarga). Este aviso se queda 3 minutos o hasta que lo cierres.</small>';
        badge = insignia(r.estado);
        clearTimeout(resumenTimer); resumenTimer = setTimeout(function () { resumenHTML = ''; var x = document.getElementById('rd-ab-resumen'); if (x) x.innerHTML = ''; forzarAbierto = false; }, 180000);
        await pintar();   // vuelve a dibujar la barra (con los datos nuevos) y el resumen se conserva
      } catch (e) { resumenHTML = '<div class="rd-ab-ok mal"><b>⚠ ' + esc(e.message) + '</b></div>'; await pintar(); }
    };
    var u = document.getElementById('rd-ab-unlock'); if (u) u.onclick = async function () { var pw = window.prompt('Contraseña de la zona privada'); if (!pw) return; try { await A.obtener(pw); await pintar(); } catch (e) { st.textContent = '⚠ Contraseña incorrecta'; } };
    var b = document.getElementById('rd-ab-borrar'); if (b) b.onclick = async function () { A.borrarLocal(); await pintar(); };
  }
  if (document.documentElement.classList.contains('rd-asesor')) pintar();
  // al activar el modo asesor (5 toques) se pinta sin recargar
  new MutationObserver(function () { if (document.documentElement.classList.contains('rd-asesor')) pintar(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
})();
