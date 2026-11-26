// Núcleo del modo asesor (portada y fichas): obtiene los datos de stock/gestión y permite cargar el Excel en este dispositivo.
// Orden de datos: 1) los cargados en este dispositivo desde el Excel (localStorage, nunca se suben); 2) los publicados CIFRADOS en /gestion.enc.json
// (se descifran con la contraseña recordada de la zona privada). Nada del precio de compra ni del margen va en claro en la web.
(function () {
  var LS = 'rd_stock_local', KEY = 'vn_clave', cache = null;
  var norm = function (t) { return String(t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); };
  var familia = function (d) { var t = norm(d).replace(/\b(nuevo|seat|cupra)\b/g, '').trim(); return t.split(/\s+/)[0] || ''; };
  var mediana = function (a) { a = a.slice().sort(function (x, y) { return x - y; }); var m = a.length >> 1; return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; };
  var eur = function (n) { return n == null ? '—' : Math.round(n).toLocaleString('es-ES', { useGrouping: true }).replace(/,/g, '.') + ' €'; };
  var num = function (t) { var d = String(t == null ? '' : t).split(',')[0].replace(/[^\d]/g, ''); return d ? parseFloat(d) : 0; };
  var b64 = function (s) { return Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); }); };
  function local() { try { return JSON.parse(localStorage.getItem(LS) || 'null'); } catch (e) { return null; } }
  async function descifrar(clave) {
    var D = await (await fetch('/gestion.enc.json', { cache: 'no-store' })).json();
    var base = await crypto.subtle.importKey('raw', new TextEncoder().encode(clave), 'PBKDF2', false, ['deriveKey']);
    var key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: b64(D.s), iterations: D.n, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
    return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64(D.i) }, key, b64(D.c))));
  }
  // Devuelve {generado, fuente, coches, stock} o null. Si hay datos locales y publicados, gana el más reciente.
  function obtener(pw) {
    if (cache && !pw) return cache;
    cache = (async function () {
      var l = local(), r = null, g = pw; if (!g) { try { g = localStorage.getItem(KEY); } catch (e) {} }
      if (g) { try { r = await descifrar(g); r.fuente = 'publicado (cifrado)'; if (pw) { try { localStorage.setItem(KEY, pw); } catch (e) {} } } catch (e) { if (pw) throw e; try { localStorage.removeItem(KEY); } catch (x) {} } }
      if (l && (!r || (l.generado || '') >= (r.generado || ''))) { l.fuente = 'cargado en este dispositivo'; return l; }
      return r;
    })();
    return cache;
  }
  function cargarXLSX() {
    if (window.XLSX) return Promise.resolve();
    return new Promise(function (ok, ko) { var s = document.createElement('script'); s.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js'; s.onload = ok; s.onerror = function () { ko(new Error('No se pudo cargar el lector de Excel (¿sin internet?)')); }; document.head.appendChild(s); });
  }
  // files: lista de File (.xlsx «Stock Inventory»); tarjetas: [{n, id, km, precio}] de los coches publicados en esta página
  async function importar(files, tarjetas) {
    await cargarXLSX();
    var stock = [], vistos = {}, generado = new Date().toISOString().slice(0, 10);
    for (var fi = 0; fi < files.length; fi++) {
      var wb = window.XLSX.read(await files[fi].arrayBuffer(), { type: 'array' });
      var rows = window.XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: null });
      var cab = rows.findIndex(function (r) { return r && r[1] === 'Nombre Inventario VO'; });
      if (cab < 0) throw new Error('«' + files[fi].name + '» no parece un Excel «Stock Inventory».');
      var m = String((rows[2] || [])[1] || '').match(/(\d{4}-\d{2}-\d{2})/); if (m && m[1] > '0') generado = m[1];
      var H = {}; rows[cab].forEach(function (v, j) { if (v) H[v] = j; });
      rows.slice(cab + 1).forEach(function (r) {
        var g = function (k) { return r[H[k]]; };
        if (!r[1] || !g('Matrícula') || vistos[g('Bastidor')]) return;
        vistos[g('Bastidor')] = 1;
        var gastos = ['Gastos de garantía y certificación', 'Gastos totales de reacondicionamiento', 'Gastos de gestoría', 'Gastos Internos gestoría'].reduce(function (s, k) { return s + (Number(g(k)) || 0); }, 0);
        stock.push({ bastidor: g('Bastidor'), matricula: g('Matrícula'), estado: g('Estado'), origen: g('Origen'), denominacion: g('Denominación Comercial') || '', id_anuncio: String(g('Id Anuncio') || ''),
          km: g('Kilometraje'), f_matric: g('Fecha de Matriculación'), tmaimg: g('TMAIMG Code'), dias: g('Días en Stock'), compra: Number(g('Precio de compra')) || 0, gastos: gastos,
          venta: Number(g('Precio de venta')) || 0, margen: g('Margen de Venta'), regimen: g('Regimen') || '' });
      });
    }
    var usados = {}, pubs = {};
    tarjetas.forEach(function (t) {
      var s = t.id && stock.filter(function (x) { return x.id_anuncio === t.id; })[0];
      if (!s) { var c = stock.filter(function (x) { return !usados[x.bastidor] && x.km && Math.abs(Number(x.km) - t.km) <= 1 && x.venta && Math.abs(x.venta - t.precio) <= 1; }); if (c.length === 1) s = c[0]; }
      if (s) { usados[s.bastidor] = 1; pubs[s.bastidor] = t; }
    });
    var razones = {};
    stock.filter(function (s) { return pubs[s.bastidor] && s.compra > 1000 && s.venta > 1000; }).forEach(function (s) {
      var r = s.venta / s.compra; [familia(s.denominacion) + '|' + s.origen, '*|' + s.origen, '*|*'].forEach(function (k) { (razones[k] = razones[k] || []).push(r); });
    });
    var filas = stock.map(function (s) {
      var f = { publicado: !!pubs[s.bastidor], n: pubs[s.bastidor] ? pubs[s.bastidor].n : '', estado: s.estado, origen: s.origen, coche: s.denominacion, matricula: s.matricula, bastidor: s.bastidor, km: s.km, f_matric: s.f_matric,
        tmaimg: s.tmaimg, dias: s.dias, compra: s.compra > 1 ? s.compra : null, gastos: s.gastos, venta: s.venta > 1000 ? s.venta : null, estimado: false, base_est: '', regimen: s.regimen, id_anuncio: s.id_anuncio, ficha: pubs[s.bastidor] ? pubs[s.bastidor].href : '' };
      if (f.venta && s.compra > 1000) f.margen = Math.round(s.margen != null ? Number(s.margen) : s.venta - s.compra - s.gastos);
      else if (!f.venta && s.compra > 1000) {
        var ks = [familia(s.denominacion) + '|' + s.origen, '*|' + s.origen, '*|*'], k = ks.filter(function (x) { return (razones[x] || []).length >= 3; })[0];
        if (k) { var r = mediana(razones[k]); f.venta = Math.round(s.compra * r / 100) * 100; f.estimado = true; f.base_est = 'compra × ' + r.toFixed(3) + ' (mediana de ' + razones[k].length + ' coches parecidos)'; f.margen = Math.round(f.venta - s.compra - s.gastos); }
      }
      f.margen_sin_iva = f.margen != null ? Math.round(f.margen / 1.21) : null;
      return f;
    });
    var coches = {};
    filas.forEach(function (f) { if (f.publicado) { var rec = { origen: f.origen, estado: f.estado, compra: f.compra, gastos: f.gastos, venta: f.venta, margen: f.margen, margen_sin_iva: f.margen_sin_iva, regimen: f.regimen, dias: f.dias, matricula: f.matricula, bastidor: f.bastidor, tmaimg: f.tmaimg, f_matric: f.f_matric }; coches['n' + f.n] = rec; if (f.id_anuncio) coches['a' + f.id_anuncio] = rec; } });
    var data = { generado: generado, coches: coches, stock: filas };
    try { localStorage.setItem(LS, JSON.stringify(data)); } catch (e) { throw new Error('No cabe en la memoria de este navegador.'); }
    cache = null; return data;
  }

  // ---- Excel de ventas (uno de CUPRA y uno del resto). Formato aún sin ver: se buscan las columnas por su título; se guarda también la fila entera.
  // Solo se añaden las filas NUEVAS (clave bastidor o matrícula + fecha). Se queda en este dispositivo; /historial/ lo lee de aquí.
  var LSV = 'rd_ventas_local';
  function ventasLocal() { try { return JSON.parse(localStorage.getItem(LSV) || 'null') || { filas: [], archivos: [] }; } catch (e) { return { filas: [], archivos: [] }; } }
  var COLS = { bastidor: /bastidor|vin|chasis/, matricula: /matr[ií]cula/, vendedor: /vendedor|comercial|asesor/, fecha: /fecha.*(venta|factura|entrega|matric)|^fecha/, precio: /precio|importe|pvp|total/, modelo: /modelo|descrip|veh[ií]culo|denominaci/ };
  async function importarVentas(files) {
    await cargarXLSX();
    var V = ventasLocal(), claves = {}, nuevas = 0, leidas = 0;
    V.filas.forEach(function (f) { claves[f.clave] = 1; });
    for (var fi = 0; fi < files.length; fi++) {
      var wb = window.XLSX.read(await files[fi].arrayBuffer(), { type: 'array', cellDates: true });
      var rows = window.XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: null, raw: false });
      var cab = rows.findIndex(function (r, i) { return i < 25 && r && r.some(function (c) { return c && /matr[ií]cula|bastidor/.test(norm(c)); }); });
      if (cab < 0) throw new Error('«' + files[fi].name + '»: no encuentro la columna de matrícula o bastidor. Pásame el archivo y lo ajusto.');
      var H = {}; rows[cab].forEach(function (v, j) { if (v) H[String(v).trim()] = j; });
      var map = {}; Object.keys(COLS).forEach(function (k) { var h = Object.keys(H).find(function (t) { return COLS[k].test(norm(t)); }); if (h) map[k] = H[h]; });
      rows.slice(cab + 1).forEach(function (r) {
        if (!r || !r.some(function (c) { return c != null && c !== ''; })) return;
        var f = { archivo: files[fi].name, cargado: new Date().toISOString().slice(0, 10), crudo: {} };
        Object.keys(H).forEach(function (t) { if (r[H[t]] != null && r[H[t]] !== '') f.crudo[t] = r[H[t]]; });
        Object.keys(map).forEach(function (k) { f[k] = r[map[k]]; });
        if (!f.bastidor && !f.matricula) return;
        leidas++;
        f.clave = String(f.bastidor || f.matricula).trim().toUpperCase() + '|' + String(f.fecha || '');
        if (claves[f.clave]) return; claves[f.clave] = 1; V.filas.push(f); nuevas++;
      });
      V.archivos.push({ nombre: files[fi].name, fecha: new Date().toISOString().slice(0, 10), columnas: Object.keys(map) });
    }
    localStorage.setItem(LSV, JSON.stringify(V));
    return { nuevas: nuevas, leidas: leidas, total: V.filas.length };
  }
  function borrarLocal() { try { localStorage.removeItem(LS); } catch (e) {} cache = null; }
  function buscar(data, cochePag) {
    var id = (String(cochePag.url || '').match(/(\d{6,})\/?$/) || [])[1];
    return (id && data.coches['a' + id]) || data.coches['n' + cochePag.n] || null;
  }
  window.RD_ASESOR = { importarVentas: importarVentas, ventasLocal: ventasLocal, obtener: obtener, importar: importar, local: local, borrarLocal: borrarLocal, familia: familia, buscar: buscar, eur: eur, num: num };
})();
