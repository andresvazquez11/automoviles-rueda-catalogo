// Núcleo del modo asesor (portada y fichas): obtiene los datos de stock/gestión y permite cargar el Excel en este dispositivo.
// Orden de datos: 1) los cargados en este dispositivo desde el Excel (localStorage, nunca se suben); 2) los publicados CIFRADOS en /gestion.enc.json
// (se descifran con la contraseña recordada de la zona privada). Nada del precio de compra ni del margen va en claro en la web.
(function () {
  var LS = 'rd_stock_local', KEY = 'vn_clave', cache = null;
  var norm = function (t) { return String(t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); };
  var familia = function (d) { var t = norm(d).replace(/\b(nuevo|seat|cupra)\b/g, '').trim(); return t.split(/\s+/)[0] || ''; };
  var mediana = function (a) { a = a.slice().sort(function (x, y) { return x - y; }); var m = a.length >> 1; return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; };
  // MARGEN NETO: el del Excel (venta − compra − gastos, con IVA) → sin IVA (21/121 del margen; en REBU un margen negativo no lleva IVA) → menos la transferencia (110 €) = margen final. % sobre la venta sin IVA.
  var TRANSF = 110;
  var margenNeto = function (venta, compra, gastos, regimen, bruto) {
    if (bruto == null) { if (venta == null || compra == null) return null; bruto = venta - compra - (gastos || 0); }
    var rebu = /rebu/i.test(regimen || ''), iva = (rebu && bruto < 0) ? 0 : bruto * 21 / 121, neto = bruto - iva, fin = neto - TRANSF;
    var vn = venta ? (rebu ? venta - iva : venta / 1.21) : null;
    return { bruto: bruto, iva: iva, neto: neto, transf: TRANSF, final: fin, pct: vn ? fin / vn * 100 : null, ventaNeta: vn };
  };
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
  var EXTRA = { color: 'Color', combustible: 'Combustible', cambio: 'Tipo de Cambio', model_vo: 'Model VO', id_ocasion: 'Id_ocasion', eurotax: 'Eurotax NatCode:', modelo_year: 'Vehículo: Modelo Year', garantia: 'Garantía', f_creacion: 'Fecha de creación', f_compra: 'Fecha de Compra', cpo: 'CPO', destacado: 'Destacado', atencion: 'Requires Attention', pub_marca: 'IsPublisedWebMarca', f_disp: 'Fecha Disponibilidad', zona: 'Dealer: Zona', pub_mf: 'Publish Motorflash Date', g_garantia: 'Gastos de garantía y certificación', g_reacond: 'Gastos totales de reacondicionamiento', g_gestoria: 'Gastos de gestoría', g_gestoria_int: 'Gastos Internos gestoría', margen_pct: 'Margen de Venta (%)' };
  function extra(g, H) { var x = {}; Object.keys(EXTRA).forEach(function (k) { if (H[EXTRA[k]] == null) return; var v = g(EXTRA[k]); if (v === null || v === undefined || v === '' || v === 'Nº de error') return; x[k] = typeof v === 'number' ? Math.round(v * 100) / 100 : v; }); return x; }
  function filaStockDe(g, H) {
    var gastos = ['Gastos de garantía y certificación', 'Gastos totales de reacondicionamiento', 'Gastos de gestoría', 'Gastos Internos gestoría'].reduce(function (s, k) { return s + (Number(g(k)) || 0); }, 0);
    return { bastidor: g('Bastidor'), matricula: g('Matrícula'), estado: g('Estado'), origen: g('Origen'), denominacion: g('Denominación Comercial') || '', id_anuncio: String(g('Id Anuncio') || ''),
      km: g('Kilometraje'), f_matric: g('Fecha de Matriculación'), tmaimg: g('TMAIMG Code'), dias: g('Días en Stock'), compra: Number(g('Precio de compra')) || 0, gastos: gastos,
      venta: Number(g('Precio de venta')) || 0, margen: g('Margen de Venta'), regimen: g('Regimen') || '', x: extra(g, H) };
  }
  async function importar(files, tarjetas) {
    await cargarXLSX();
    var stock = [], vistos = {}, generado = new Date().toISOString().slice(0, 10);
    for (var fi = 0; fi < files.length; fi++) {
      var wb = window.XLSX.read(await files[fi].arrayBuffer(), { type: 'array' });
      var rows = window.XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: null });
      var cab = rows.findIndex(function (r) { return r && r[1] === 'Nombre Inventario VO'; });
      if (cab < 0) {
        var esVentas = rows.some(function (r) { return r && r.indexOf('Quote Name') >= 0; });
        throw new Error(esVentas ? '«' + files[fi].name + '» es un Excel de VENTAS (Entregas VO), no de stock. Cárgalo con el botón «📥 Cargar Excel de ventas».'
          : '«' + files[fi].name + '» no es un Excel de stock (Stock Inventory). Comprueba que has elegido el archivo correcto.');
      }
      var m = String((rows[2] || [])[1] || '').match(/(\d{4}-\d{2}-\d{2})/); if (m && m[1] > '0') generado = m[1];
      var H = {}; rows[cab].forEach(function (v, j) { if (v) H[v] = j; });
      rows.slice(cab + 1).forEach(function (r) {
        var g = function (k) { return r[H[k]]; };
        if (!r[1] || !g('Matrícula') || vistos[g('Bastidor')]) return;
        vistos[g('Bastidor')] = 1;
        stock.push(filaStockDe(g, H));
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
      var mn = f.margen != null ? margenNeto(f.venta, s.compra, s.gastos, f.regimen, f.margen) : null;
      f.margen_sin_iva = mn ? Math.round(mn.neto) : null; f.margen_final = mn ? Math.round(mn.final) : null; f.margen_pct = mn && mn.pct != null ? Math.round(mn.pct * 10) / 10 : null;
      return f;
    });
    var coches = {};
    filas.forEach(function (f) { if (f.publicado) { var rec = { origen: f.origen, estado: f.estado, compra: f.compra, gastos: f.gastos, venta: f.venta, margen: f.margen, margen_sin_iva: f.margen_sin_iva, margen_final: f.margen_final, margen_pct: f.margen_pct, regimen: f.regimen, dias: f.dias, matricula: f.matricula, bastidor: f.bastidor, tmaimg: f.tmaimg, f_matric: f.f_matric, x: f.x }; coches['n' + f.n] = rec; if (f.id_anuncio) coches['a' + f.id_anuncio] = rec; } });
    var data = { generado: generado, coches: coches, stock: filas };
    try { localStorage.setItem(LS, JSON.stringify(data)); } catch (e) { throw new Error('No cabe en la memoria de este navegador.'); }
    cache = null; return data;
  }

  // ---- Excel «Entregas VO» (uno de CUPRA y uno del resto, filtrados por mes) → almacén común CIFRADO (Worker rueda-historial).
  // El navegador cifra cada archivo con la contraseña de la zona privada (AES-GCM) y lo guarda como un «lote»; solo se tratan las filas NUEVAS
  // (clave = bastidor + fecha de entrega contable). Claude y la página /historial/ leen los lotes y los descifran con la misma contraseña.
  var ALM = 'https://rueda-historial.andrescovidelpi.workers.dev';
  var CAB = { presupuesto: 'Quote Name', vendedor: 'Creado por: Nombre completo', modelo_vo: 'Inventory VO: Model VO', coche: 'Inventory VO: Denominación Comercial', combustible: 'Inventory VO: Combustible',
    cambio: 'Inventory VO: Tipo de Cambio', color: 'Inventory VO: Color', bastidor: 'Inventory VO: Bastidor', matricula: 'Inventory VO: Matrícula', id_ocasion: 'Inventory VO: Id_ocasion', km: 'Inventory VO: Kilometraje',
    f_matric: 'Inventory VO: Fecha de Matriculación', tmaimg: 'Inventory VO: TMAIMG Code', origen: 'Inventory VO: Origen', tipo_venta: 'Inventory VO: Tipo de Venta', cliente: 'Quote: Client Type VO',
    f_creacion: 'Inventory VO: Fecha de creación', f_compra: 'Inventory VO: Fecha de Compra', cpo: 'Inventory VO: CPO', garantia: 'Inventory VO: Garantía', compra: 'Inventory VO: Precio de compra',
    venta: 'Inventory VO: Precio de venta', regimen: 'Inventory VO: Regimen', f_entrega: 'Quote: Fecha de entrega', f_entrega_contable: 'Quote: Fecha de Entrega Contable', concesionario: 'Quote: Concesionario SEAT: Código de Seat' };
  var fechaISO = function (t) { var m = String(t == null ? '' : t).split(',')[0].trim().split('/'); if (m.length !== 3) return null; return ('0000' + m[2]).slice(-4) + '-' + ('0' + m[1]).slice(-2) + '-' + ('0' + m[0]).slice(-2); };
  var hex = function (buf) { return Array.prototype.map.call(new Uint8Array(buf), function (x) { return ('0' + x.toString(16)).slice(-2); }).join(''); };
  var unb64 = function (s) { return Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); }); };
  function clavePriv() { try { return localStorage.getItem(KEY) || ''; } catch (e) { return ''; } }
  async function token(pwd) { var base = await crypto.subtle.importKey('raw', new TextEncoder().encode(pwd), 'PBKDF2', false, ['deriveBits']); return hex(await crypto.subtle.deriveBits({ name: 'PBKDF2', salt: new TextEncoder().encode('rueda-acceso'), iterations: 100000, hash: 'SHA-256' }, base, 256)); }
  async function cifrarObj(obj, pwd) {
    var salt = crypto.getRandomValues(new Uint8Array(16)), iv = crypto.getRandomValues(new Uint8Array(12)), n = 600000;
    var base = await crypto.subtle.importKey('raw', new TextEncoder().encode(pwd), 'PBKDF2', false, ['deriveKey']);
    var key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: salt, iterations: n, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['encrypt']);
    var ct = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, new TextEncoder().encode(JSON.stringify(obj))));
    var b = function (u) { var s = ''; u.forEach(function (c) { s += String.fromCharCode(c); }); return btoa(s); };
    return { s: b(salt), i: b(iv), c: b(ct), n: n };
  }
  async function descifrarObj(D, pwd) {
    var base = await crypto.subtle.importKey('raw', new TextEncoder().encode(pwd), 'PBKDF2', false, ['deriveKey']);
    var key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: unb64(D.s), iterations: D.n, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
    return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(D.i) }, key, unb64(D.c))));
  }
  async function almacen(metodo, ruta, cuerpo, pwd) {
    var r = await fetch(ALM + ruta, { method: metodo, headers: { 'X-Acceso': await token(pwd), 'Content-Type': 'application/json' }, body: cuerpo ? JSON.stringify(cuerpo) : undefined });
    if (r.status === 401) throw new Error('El almacén no acepta la contraseña de este dispositivo. Entra en /nuevos/ y márcala como «Recordar».');
    if (!r.ok) throw new Error('Almacén: error ' + r.status);
    return r.json();
  }
  async function ventasAlmacen() {   // todas las filas de todos los lotes, sin duplicados
    var pwd = clavePriv(); if (!pwd) return [];
    var lotes = await almacen('GET', '/lotes/ventas', null, pwd), vistas = {}, out = [];
    for (var i = 0; i < lotes.length; i++) { var filas = await descifrarObj(lotes[i].d, pwd); filas.forEach(function (f) { if (!vistas[f.clave]) { vistas[f.clave] = 1; out.push(f); } }); }
    return out;
  }
  async function importarVentas(files) {
    var pwd = clavePriv(); if (!pwd) throw new Error('Primero entra una vez en /nuevos/ con la contraseña y marca «Recordar en este dispositivo».');
    await cargarXLSX();
    var existentes = {}; (await ventasAlmacen()).forEach(function (f) { existentes[f.clave] = 1; });
    var res = { nuevas: 0, leidas: 0, archivos: 0, detalle: [] };
    for (var fi = 0; fi < files.length; fi++) {
      var buf = await files[fi].arrayBuffer();
      var wb = window.XLSX.read(buf, { type: 'array' });
      var rows = window.XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: null });
      var ic = rows.findIndex(function (r) { return r && r.indexOf('Quote Name') >= 0; });
      if (ic < 0 && rows.slice(0, 8).some(function (r) { return r && /cartera/i.test(r.join(' ')); })) {   // «Cartera VO vigente» sin ninguna fila (p. ej. CUPRA sin coches pendientes): se guarda como foto vacía
        var mv = rows.slice(0, 8).map(function (r) { return (r || []).join(' '); }).join(' ').match(/(\d{4}-\d{2}-\d{2})/), fv = mv ? mv[1] : new Date().toISOString().slice(0, 10);
        var idv = 'c-' + fv + '-' + hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode('|' + files[fi].name + files[fi].size))).slice(0, 12);
        await almacen('PUT', '/lote/cartera/' + idv, await cifrarObj({ fecha: fv, nombre: files[fi].name, filas: [] }, pwd), pwd);
        res.archivos++; res.detalle.push({ nombre: files[fi].name, tipo: 'cartera', fecha: fv, coches: 0, leidas: 0, nuevas: 0 });
        continue;
      }
      if (ic < 0) {
        var esStock = rows.some(function (r) { return r && r.indexOf('Nombre Inventario VO') >= 0; });
        throw new Error(esStock ? '«' + files[fi].name + '» es un Excel de STOCK, no de ventas. Cárgalo con el botón «📥 Cargar Excel de stock». No se ha guardado nada.'
          : '«' + files[fi].name + '» no es un Excel de ventas (Entregas VO). Comprueba que has elegido el archivo correcto. No se ha guardado nada.');
      }
      var pos = {}; rows[ic].forEach(function (v, j) { if (v) pos[String(v).trim()] = j; });
      if (pos[CAB.f_entrega_contable] == null) {   // «Cartera VO vigente»: coches vendidos con pedido aún NO entregados (foto del momento)
        var mf = String((rows[2] || [])[1] || '').match(/(\d{4}-\d{2}-\d{2})/), fcar = mf ? mf[1] : new Date().toISOString().slice(0, 10), filasC = [];
        rows.slice(ic + 1).forEach(function (r) {
          var g = function (k) { var j = pos[CAB[k]]; return j == null ? null : r[j]; };
          if (!g('bastidor') && !g('matricula')) return;
          var f = {}; Object.keys(CAB).forEach(function (k) { if (k !== 'f_entrega' && k !== 'f_entrega_contable') f[k] = g(k); });
          ['f_matric', 'f_creacion', 'f_compra'].forEach(function (k) { f[k] = fechaISO(f[k]); });
          ['km', 'compra', 'venta', 'garantia'].forEach(function (k) { f[k] = f[k] == null || f[k] === '' ? null : Number(f[k]); });
          f.marca = String(f.presupuesto || f.coche || '').split(' ')[0].toUpperCase();
          f.margen = f.venta != null && f.compra != null ? Math.round((f.venta - f.compra) * 100) / 100 : null;
          f.clave = (f.bastidor || f.matricula) + '|' + fcar; filasC.push(f);
        });
        var idc = 'c-' + fcar + '-' + hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(filasC.map(function (f) { return f.clave; }).sort().join(',') + (filasC.length ? '' : '|' + files[fi].name + files[fi].size)))).slice(0, 12);
        await almacen('PUT', '/lote/cartera/' + idc, await cifrarObj({ fecha: fcar, nombre: files[fi].name, filas: filasC }, pwd), pwd);
        res.archivos++; res.detalle.push({ nombre: files[fi].name, tipo: 'cartera', fecha: fcar, coches: filasC.length, leidas: filasC.length, nuevas: 0 });
        continue;
      }
      var nuevasFilas = [], leidasArch = 0;
      rows.slice(ic + 1).forEach(function (r) {
        var g = function (k) { var j = pos[CAB[k]]; return j == null ? null : r[j]; };
        if (!g('bastidor') && !g('matricula')) return;
        var f = {}; Object.keys(CAB).forEach(function (k) { f[k] = g(k); });
        ['f_matric', 'f_creacion', 'f_compra', 'f_entrega', 'f_entrega_contable'].forEach(function (k) { f[k] = fechaISO(f[k]); });
        ['km', 'compra', 'venta', 'garantia'].forEach(function (k) { f[k] = f[k] == null || f[k] === '' ? null : Number(f[k]); });
        f.marca = String(f.presupuesto || f.coche || '').split(' ')[0].toUpperCase();
        f.fecha = f.f_entrega_contable || f.f_entrega;
        f.margen = f.venta != null && f.compra != null ? Math.round((f.venta - f.compra) * 100) / 100 : null;
        if (f.fecha && f.f_creacion) f.dias_stock = Math.round((new Date(f.fecha) - new Date(f.f_creacion)) / 864e5);
        f.clave = (f.bastidor || f.matricula) + '|' + f.fecha;
        res.leidas++; leidasArch++; if (existentes[f.clave]) return; existentes[f.clave] = 1; nuevasFilas.push(f);
      });
      res.archivos++; res.detalle.push({ nombre: files[fi].name, leidas: leidasArch, nuevas: nuevasFilas.length });
      if (nuevasFilas.length) {
        var id = hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(nuevasFilas.map(function (f) { return f.clave; }).sort().join(',')))).slice(0, 20);
        await almacen('PUT', '/lote/ventas/' + id, await cifrarObj(nuevasFilas, pwd), pwd);
        res.nuevas += nuevasFilas.length;
      }
    }
    return res;
  }

  // ---- BOTÓN ÚNICO: stock + entregas + cartera (6 archivos: SEAT y CUPRA de cada uno). Detecta tipo y marca de cada archivo, lo guarda cifrado en el
  // almacén común, apunta qué se cargó y cuándo (registro) y avisa de lo que falta o se queda sin cargar demasiados días.
  var NOM_T = { stock: 'Stock', entregas: 'Entregas VO', cartera: 'Cartera VO' }, NOM_G = { seat: 'SEAT y resto', cupra: 'CUPRA' }, UMBRAL = { stock: 2, cartera: 2, entregas: 3 };
  var hoyISO = function () { return new Date().toISOString().slice(0, 10); };
  async function clasificar(file) {
    var wb = window.XLSX.read(await file.arrayBuffer(), { type: 'array' });
    var rows = window.XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: null });
    var tex = rows.slice(0, 8).map(function (r) { return (r || []).join(' '); }).join(' '), fm = tex.match(/(\d{4}-\d{2}-\d{2})/), fecha = fm ? fm[1] : hoyISO();
    var cs = rows.findIndex(function (r) { return r && r[1] === 'Nombre Inventario VO'; });
    if (cs >= 0) {
      var H = {}; rows[cs].forEach(function (v, j) { if (v) H[v] = j; });
      var filas = [], vistos = {}, cod = '';
      rows.slice(cs + 1).forEach(function (r) { var g = function (k) { return r[H[k]]; }; if (!r[1] || !g('Matrícula') || vistos[g('Bastidor')]) return; vistos[g('Bastidor')] = 1; if (!cod) cod = String(g('Dealer: Código de Seat') || ''); filas.push(filaStockDe(g, H)); });
      return { file: file, tipo: 'stock', grupo: filas.length ? (/^c/i.test(cod) ? 'cupra' : 'seat') : null, fecha: fecha, filas: filas };
    }
    var cq = rows.findIndex(function (r) { return r && r.indexOf('Quote Name') >= 0; });
    var esEnt = cq >= 0 ? rows[cq].indexOf('Quote: Fecha de Entrega Contable') >= 0 : /entregas/i.test(tex), esCar = cq >= 0 ? !esEnt : /cartera/i.test(tex);
    if (!esEnt && !esCar) return { file: file, tipo: null };
    var cod2 = '', n = 0;
    if (cq >= 0) { var jc = rows[cq].indexOf('Quote: Concesionario SEAT: Código de Seat'), jb = rows[cq].indexOf('Inventory VO: Bastidor'), jm = rows[cq].indexOf('Inventory VO: Matrícula');
      rows.slice(cq + 1).forEach(function (r) { if (r && ((jb >= 0 && r[jb]) || (jm >= 0 && r[jm]))) { n++; if (!cod2) cod2 = String(r[jc] || ''); } }); }
    return { file: file, tipo: esEnt ? 'entregas' : 'cartera', grupo: n ? (/^c/i.test(cod2) ? 'cupra' : 'seat') : null, fecha: fecha, filas: n };
  }
  async function registroLeer(pwd) {
    var l = await almacen('GET', '/lotes/otros', null, pwd), out = {};
    for (var i = 0; i < l.length; i++) { if (!/^reg-/.test(l[i].id)) continue; try { var d = await descifrarObj(l[i].d, pwd); out[d.tipo + '|' + d.grupo] = d; } catch (e) {} }
    return out;
  }
  function estadoCargas(reg) {
    var out = [], hoy = new Date(hoyISO());
    ['stock', 'entregas', 'cartera'].forEach(function (t) { ['seat', 'cupra'].forEach(function (g) {
      var r = reg[t + '|' + g], dias = r ? Math.round((hoy - new Date(r.cargado.slice(0, 10))) / 864e5) : null;
      var nivel = !r ? 'falta' : dias > UMBRAL[t] ? 'aviso' : 'ok';
      out.push({ tipo: t, grupo: g, nivel: nivel, dias: dias, nombre: NOM_T[t] + ' · ' + NOM_G[g], texto: !r ? 'nunca cargado' : dias === 0 ? 'cargado hoy' : dias === 1 ? 'cargado ayer' : 'hace ' + dias + ' días' });
    }); });
    return out;
  }
  async function estadoActual() { var pwd = clavePriv(); if (!pwd) return null; return estadoCargas(await registroLeer(pwd)); }
  async function cargarTodo(files, tarjetas) {
    var pwd = clavePriv(); if (!pwd) throw new Error('Primero entra una vez en /nuevos/ con la contraseña y marca «Recordar en este dispositivo».');
    await cargarXLSX();
    var cls = []; for (var i = 0; i < files.length; i++) cls.push(await clasificar(files[i]));
    var reg = {}; try { reg = await registroLeer(pwd); } catch (e) { if (/contraseña/.test(e.message)) throw e; }
    ['stock', 'entregas', 'cartera'].forEach(function (t) {   // archivos sin coches: no se puede ver su marca; se deduce
      var mios = cls.filter(function (c) { return c.tipo === t; }), conocidos = mios.filter(function (c) { return c.grupo; }).map(function (c) { return c.grupo; });
      mios.filter(function (c) { return !c.grupo; }).forEach(function (c) {
        var libres = ['cupra', 'seat'].filter(function (g) { return conocidos.indexOf(g) < 0; });
        libres.sort(function (a, b) { var x = reg[t + '|' + a], y = reg[t + '|' + b]; return (x ? x.cargado : '') < (y ? y.cargado : '') ? -1 : 1; });
        c.grupo = libres[0] || 'cupra'; c.inferido = true; conocidos.push(c.grupo);
      });
    });
    var informe = [], stockF = cls.filter(function (c) { return c.tipo === 'stock'; }), ventasF = cls.filter(function (c) { return c.tipo === 'entregas' || c.tipo === 'cartera'; });
    cls.filter(function (c) { return !c.tipo; }).forEach(function (c) { informe.push({ nombre: c.file.name, ok: false, texto: 'No reconozco este archivo (no es Stock Inventory, Entregas VO ni Cartera VO). No se ha guardado.' }); });
    var datosStock = null;
    if (stockF.length) {
      datosStock = await importar(stockF.map(function (c) { return c.file; }), tarjetas || []);   // para este dispositivo (fichas y portada)
      for (var k = 0; k < stockF.length; k++) { var c = stockF[k];
        await almacen('PUT', '/lote/stock/s-' + c.fecha + '-' + c.grupo, await cifrarObj({ fecha: c.fecha, nombre: c.file.name, grupo: c.grupo, filas: c.filas }, pwd), pwd);
        informe.push({ nombre: c.file.name, tipo: 'stock', grupo: c.grupo, inferido: c.inferido, ok: true, texto: c.filas.length ? c.filas.length + ' coches en stock' : 'sin coches' }); }
    }
    var det = {};
    if (ventasF.length) { var r = await importarVentas(ventasF.map(function (c) { return c.file; })); r.detalle.forEach(function (d) { det[d.nombre] = d; }); }
    ventasF.forEach(function (c) { var d = det[c.file.name] || {};
      informe.push({ nombre: c.file.name, tipo: c.tipo, grupo: c.grupo, inferido: c.inferido, ok: true,
        texto: c.tipo === 'cartera' ? (c.filas ? c.filas + ' coche(s) vendido(s) pendiente(s) de entrega' : 'sin coches pendientes de entrega') : (d.nuevas || 0) + ' venta(s) nueva(s)' + (d.leidas - d.nuevas ? ', ' + (d.leidas - d.nuevas) + ' ya estaban' : '') }); });
    for (var q = 0; q < cls.length; q++) { var z = cls[q]; if (!z.tipo) continue;
      var info = { tipo: z.tipo, grupo: z.grupo, fecha: z.fecha, cargado: new Date().toISOString(), nombre: z.file.name, filas: typeof z.filas === 'number' ? z.filas : z.filas.length };
      await almacen('PUT', '/lote/otros/reg-' + z.tipo + '-' + z.grupo, await cifrarObj(info, pwd), pwd); reg[z.tipo + '|' + z.grupo] = info; }
    return { informe: informe, estado: estadoCargas(reg), datosStock: datosStock };
  }
  function borrarLocal() { try { localStorage.removeItem(LS); } catch (e) {} cache = null; }
  function buscar(data, cochePag) {
    var id = (String(cochePag.url || '').match(/(\d{6,})\/?$/) || [])[1];
    return (id && data.coches['a' + id]) || data.coches['n' + cochePag.n] || null;
  }
  window.RD_ASESOR = { cargarTodo: cargarTodo, estadoActual: estadoActual, importarVentas: importarVentas, ventasAlmacen: ventasAlmacen, obtener: obtener, importar: importar, local: local, borrarLocal: borrarLocal, familia: familia, buscar: buscar, eur: eur, num: num, margenNeto: margenNeto, TRANSF: TRANSF };
})();
