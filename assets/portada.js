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
      '<button type="button" id="rd-ab-excel">📥 Cargar Excel de stock</button><input type="file" id="rd-ab-file" accept=".xlsx" multiple hidden>' +
      '<button type="button" id="rd-ab-ventas">📥 Cargar Excel de ventas</button><input type="file" id="rd-ab-fventas" accept=".xlsx" multiple hidden>' +
      (d ? '' : '<button type="button" id="rd-ab-unlock">🔓 Desbloquear publicados</button>') + (A.local() ? '<button type="button" id="rd-ab-borrar">Borrar datos de este dispositivo</button>' : '') +
      '<span class="rd-ab-estado" id="rd-ab-estado">' + estado + '</span>';
    var inp = document.getElementById('rd-ab-file'), st = document.getElementById('rd-ab-estado');
    document.getElementById('rd-ab-excel').onclick = function () { inp.click(); };
    inp.onchange = async function () {
      if (!inp.files.length) return; st.textContent = 'Leyendo el Excel…';
      try { var data = await A.importar(Array.prototype.slice.call(inp.files), tarjetas()); await pintar(); st = document.getElementById('rd-ab-estado'); st.textContent += ' · ✓ cargado (' + data.stock.length + ' coches, ' + Object.keys(data.coches).filter(function (k) { return k[0] === 'n'; }).length + ' publicados emparejados). Se queda solo en este dispositivo.'; }
      catch (e) { st.textContent = '⚠ ' + e.message; }
    };
    var iv = document.getElementById('rd-ab-fventas');
    document.getElementById('rd-ab-ventas').onclick = function () { iv.click(); };
    iv.onchange = async function () {
      if (!iv.files.length) return; st.textContent = 'Leyendo y guardando…';
      try { var r = await A.importarVentas(Array.prototype.slice.call(iv.files));
        st.innerHTML = '✓ <b>Guardado correctamente</b> en el almacén común (cifrado). ' + r.detalle.map(function (d) { return d.tipo === 'cartera' ? '«' + esc(d.nombre) + '»: <b>CARTERA</b> del ' + d.fecha.split('-').reverse().join('/') + ', ' + d.coches + ' coche(s) vendido(s) pendiente(s) de entrega' + (d.coches ? '' : ' (vacío: normal si no hay cartera de esa marca)') : '«' + esc(d.nombre) + '»: <b>ENTREGAS</b>, ' + d.nuevas + ' nueva(s)' + (d.leidas - d.nuevas ? ', ' + (d.leidas - d.nuevas) + ' ya estaban' : ''); }).join(' · ') + '. Total ventas nuevas: ' + r.nuevas + '. Puedes cargar los dos archivos juntos o de uno en uno. Mira «Historial ↗» (si no aparecen, espera 1 minuto y recarga).'; }
      catch (e) { st.textContent = '⚠ ' + e.message; }
    };
    var u = document.getElementById('rd-ab-unlock'); if (u) u.onclick = async function () { var pw = window.prompt('Contraseña de la zona privada'); if (!pw) return; try { await A.obtener(pw); await pintar(); } catch (e) { st.textContent = '⚠ Contraseña incorrecta'; } };
    var b = document.getElementById('rd-ab-borrar'); if (b) b.onclick = async function () { A.borrarLocal(); await pintar(); };
  }
  if (document.documentElement.classList.contains('rd-asesor')) pintar();
  // al activar el modo asesor (5 toques) se pinta sin recargar
  new MutationObserver(function () { if (document.documentElement.classList.contains('rd-asesor')) pintar(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
})();
