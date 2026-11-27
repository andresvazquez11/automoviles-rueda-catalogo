// Solo asesor, en la portada: barra de herramientas (nuevos, stock, cargar Excel). El margen de cada coche va DENTRO de la ficha (más discreto), no en la portada.
(function () {
  var barra = document.getElementById('rd-asesor-barra'), A = window.RD_ASESOR;
  if (!barra || !A) return;
  var esc = function (t) { return String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
  var tarjetas = function () { return Array.prototype.map.call(document.querySelectorAll('#rd-grid .rd-card'), function (c) {
    return { el: c, href: c.getAttribute('href') || '', n: c.dataset.n, id: ((c.getAttribute('href') || '').match(/(\d{6,})\.html/) || [])[1] || '', km: parseFloat(c.dataset.km) || 0, precio: parseFloat(c.dataset.precio) || 0 }; }); };
  async function pintar() {
    var d = await A.obtener();
    var estado = d ? 'Datos de ' + esc(d.fuente) + ' del ' + d.generado.split('-').reverse().join('/') + ' · ' + d.stock.length + ' coches' : 'Sin datos de stock: carga el Excel o desbloquea los publicados';
    barra.innerHTML = '<b>🧰 Herramientas del asesor</b><a href="/nuevos/" target="_blank" rel="noopener">Vehículos nuevos ↗</a><a href="/stock/" target="_blank" rel="noopener">Stock completo ↗</a><a href="/comparativa/" target="_blank" rel="noopener">Comparativa ocasión/nuevo ↗</a><a href="/historial/" target="_blank" rel="noopener">Historial ↗</a>' +
      '<button type="button" id="rd-ab-excel">📥 Cargar Excel (stock, entregas y cartera)</button><input type="file" id="rd-ab-file" accept=".xlsx" multiple hidden>' +
      (d ? '' : '<button type="button" id="rd-ab-unlock">🔓 Desbloquear publicados</button>') + (A.local() ? '<button type="button" id="rd-ab-borrar">Borrar datos de este dispositivo</button>' : '') +
      '<span class="rd-ab-estado" id="rd-ab-estado">' + estado + '</span><div class="rd-ab-resumen" id="rd-ab-resumen"></div>';
    var inp = document.getElementById('rd-ab-file'), st = document.getElementById('rd-ab-estado');
    document.getElementById('rd-ab-excel').onclick = function () { inp.click(); };
    var res = document.getElementById('rd-ab-resumen');
    var tabla = function (estado) {
      return '<div class="rd-ab-est">' + estado.map(function (e) { var ic = e.nivel === 'ok' ? '✅' : e.nivel === 'aviso' ? '⚠️' : '❌';
        return '<span class="rd-ab-chip ' + e.nivel + '">' + ic + ' ' + esc(e.nombre) + ' · ' + esc(e.texto) + (e.nivel === 'aviso' ? ' — toca sacarlo' : e.nivel === 'falta' ? ' — falta cargarlo' : '') + '</span>'; }).join('') + '</div>'; };
    A.estadoActual().then(function (e) { if (e && res && !res.innerHTML) res.innerHTML = '<b>Estado de las cargas</b>' + tabla(e); }).catch(function () {});
    inp.onchange = async function () {
      if (!inp.files.length) return; st.textContent = 'Leyendo y guardando los archivos…';
      try {
        var r = await A.cargarTodo(Array.prototype.slice.call(inp.files), tarjetas());
        var nm = { stock: 'Stock', entregas: 'Entregas VO', cartera: 'Cartera VO' }, gr = { seat: 'SEAT y resto', cupra: 'CUPRA' };
        var ok = r.informe.filter(function (i) { return i.ok; }).length, mal = r.informe.length - ok;
        res.innerHTML = '<b>' + (mal ? '⚠ Cargados ' + ok + ' de ' + r.informe.length + ' archivos' : '✓ Cargados correctamente ' + ok + ' archivo(s)') + '</b> (guardados cifrados en el almacén común)<ul>' +
          r.informe.map(function (i) { return '<li>' + (i.ok ? '✅' : '❌') + ' «' + esc(i.nombre) + '» → ' + (i.ok ? '<b>' + nm[i.tipo] + ' · ' + gr[i.grupo] + '</b>' + (i.inferido ? ' <i>(no trae coches: deduzco que es ' + gr[i.grupo] + ')</i>' : '') + ': ' + esc(i.texto) : esc(i.texto)) + '</li>'; }).join('') +
          '</ul><b>Estado de las cargas</b>' + tabla(r.estado) + '<small>Si ves «toca sacarlo», ese Excel lleva varios días sin cargarse. Las ventas nuevas aparecen en «Historial ↗» (si no, espera 1 minuto y recarga).</small>';
        if (r.datosStock) { await pintar(); res = document.getElementById('rd-ab-resumen'); }
        st = document.getElementById('rd-ab-estado');
      } catch (e) { st.textContent = '⚠ ' + e.message; }
    };
    var u = document.getElementById('rd-ab-unlock'); if (u) u.onclick = async function () { var pw = window.prompt('Contraseña de la zona privada'); if (!pw) return; try { await A.obtener(pw); await pintar(); } catch (e) { st.textContent = '⚠ Contraseña incorrecta'; } };
    var b = document.getElementById('rd-ab-borrar'); if (b) b.onclick = async function () { A.borrarLocal(); await pintar(); };
  }
  if (document.documentElement.classList.contains('rd-asesor')) pintar();
  // al activar el modo asesor (5 toques) se pinta sin recargar
  new MutationObserver(function () { if (document.documentElement.classList.contains('rd-asesor')) pintar(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
})();
