/* ══════════════════════════════════════════════════════════════════
   Automóviles Rueda — "Imprimir folleto" (solo modo asesor, portada)

   Hoja A4 a doble cara EN COLOR (pensada para que también salga bien en
   impresora de blanco y negro: rojo = gris oscuro, sin fondos macizos) con
   TODOS los coches disponibles en este momento, para dejar en la puerta:
   · cara 1: marca, la WEB en grande ("ocasion" en letra hueca: borde rojo /
     oscuro en B/N, relleno blanco) y contacto del asesor;
   · una ficha pequeña por coche (foto, modelo, versión, matriculación, km,
     combustible, cambio y precio), repartidas MIDIENDO lo que cabe;
   · al final de la última cara, recuadro con el QR al catálogo.

   Los datos los escribe generar_web.py en <script id="rd-folleto-datos">
   (coches "Disponible" + datos del asesor del perfil). El botón solo se
   ve con la clase rd-asesor en <html> (5 toques en el nombre, enviar.js).
   ══════════════════════════════════════════════════════════════════ */
(function () {
  const nodo = document.getElementById('rd-folleto-datos');
  if (!nodo) return;
  let D;
  try { D = JSON.parse(nodo.textContent); } catch (_) { return; }

  const esc = s => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  const CSS = `
html:not(.rd-asesor) .rd-folleto-btn { display: none !important; }
body.rd-cx-abierto .rd-folleto-btn { display: none !important; }   /* comparador abierto */
.rd-folleto-btn { position: fixed; left: 14px; bottom: 18px; z-index: 9991; display: flex; align-items: center; gap: 8px;
  padding: 11px 16px; border: 0; border-radius: 999px; background: #14110f; color: #fff; cursor: pointer;
  font: 700 13px 'Work Sans', sans-serif; letter-spacing: .5px; box-shadow: 0 6px 20px rgba(0,0,0,.25); }
.rd-folleto-btn[disabled] { opacity: .6; cursor: wait; }
.rd-folleto-btn small { font-weight: 600; opacity: .7; font-size: 10px; letter-spacing: .6px; text-transform: uppercase; }

#rd-folleto-sheet { display: none; }
@media print {
  @page { size: A4 portrait; margin: 10mm; }
  html, body { background: #fff !important; margin: 0 !important; padding: 0 !important; }
  /* Solo mientras se imprime EL FOLLETO (clase en <body>): en la portada también
     está la impresión del comparador, y si las dos reglas se aplicaban a la vez
     se ocultaba todo y salía la hoja en blanco. */
  body.rd-imp-folleto > *:not(#rd-folleto-sheet) { display: none !important; }
  body.rd-imp-folleto #rd-folleto-sheet { display: block !important; position: static !important; }
}
#rd-folleto-sheet, #rd-folleto-sheet * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.flp { width: 190mm; height: 276mm; overflow: hidden; display: flex; flex-direction: column; background: #fff; color: #14110f;
  font-family: 'Work Sans', Arial, sans-serif; font-size: 8.5pt; line-height: 1.3; }
.flp + .flp { break-before: page; page-break-before: always; }
.fl-osw { font-family: 'Oswald', 'Arial Narrow', Arial, sans-serif; }

/* Dirección web: "automovilesrueda" macizo + "ocasion" en letra hueca (borde rojo; oscuro en B/N) */
.fl-dom { font-family: 'Oswald', 'Arial Narrow', Arial, sans-serif; font-weight: 700; letter-spacing: .3pt; line-height: 1; white-space: nowrap; }
.fl-dom .fl-oc { color: #fff; -webkit-text-stroke: .045em #C8232B; letter-spacing: .04em; }
.fl-dom .fl-tld { font-weight: 600; }
.fl-dom .fl-ruta { font-size: .55em; font-weight: 600; }

/* ── Cabecera de la cara 1 (compacta: marca + contacto, y la web en una franja) ── */
.fl-top { display: flex; justify-content: space-between; align-items: flex-end; gap: 6mm;
  border-bottom: 3pt solid #C8232B; padding-bottom: 2.5mm; }
.fl-marca { font-size: 24pt; font-weight: 700; text-transform: uppercase; line-height: 1; letter-spacing: .5pt; white-space: nowrap; }
.fl-lema { font-size: 8pt; font-weight: 600; margin-top: 1.5mm; letter-spacing: .2pt; color: #C8232B; white-space: nowrap; }
.fl-contacto { text-align: right; font-size: 8.5pt; line-height: 1.45; white-space: nowrap; }
.fl-contacto .fl-tel { font-size: 12.5pt; font-weight: 700; }
.fl-contacto .fl-tel small { font-size: 8pt; font-weight: 600; color: #5d5650; }
.fl-web { margin-top: 2.5mm; border: 2pt solid #C8232B; border-radius: 2mm; padding: 2mm 4mm;
  display: flex; justify-content: space-between; align-items: center; gap: 4mm; }
.fl-web-lbl { font-size: 8pt; font-weight: 700; letter-spacing: .5pt; text-transform: uppercase; line-height: 1.3; }
.fl-web .fl-dom { font-size: 19pt; }

/* ── Cabecera de las demás caras ── */
.fl-head2 { display: flex; justify-content: space-between; align-items: baseline; gap: 4mm;
  border-bottom: 2.5pt solid #C8232B; padding-bottom: 1.5mm; font-size: 8.5pt; }
.fl-head2 .fl-marca { font-size: 13pt; }
.fl-head2 .fl-dom { font-size: 13pt; }

/* ── Franja de garantía (arriba de la 2ª cara) ── */
.fl-garantia { margin-top: 2.5mm; border: 2pt solid #C8232B; border-radius: 2mm; padding: 2mm 4mm;
  display: grid; grid-template-columns: auto 1fr; gap: 4mm; align-items: center; }
.fl-gar-num { font-size: 26pt; font-weight: 700; line-height: .9; color: #C8232B; text-transform: uppercase; white-space: nowrap; }
.fl-gar-tit { font-size: 12.5pt; font-weight: 700; text-transform: uppercase; line-height: 1.1; }
.fl-gar-txt { font-size: 9pt; margin-top: .6mm; }
.fl-gar-nota { font-size: 7pt; color: #5d5650; margin-top: .8mm; }

/* ── Coches ── */
.fl-grid { margin-top: 2.5mm; display: grid; grid-template-columns: repeat(3, 1fr); grid-auto-rows: 23.5mm; gap: 2.2mm 3mm; }
.fl-card { border: .8pt solid #9c958b; border-radius: 1.5mm; display: grid; grid-template-columns: 24mm 1fr; overflow: hidden; }
.fl-foto { background: #f2f1ed; overflow: hidden; }
.fl-foto img { width: 100%; height: 100%; object-fit: cover; display: block; }
.fl-txt { padding: 1.1mm 1.8mm 1mm; display: flex; flex-direction: column; min-width: 0; }
.fl-mod { font-size: 10pt; font-weight: 700; text-transform: uppercase; line-height: 1.05; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fl-ver { font-size: 6.5pt; line-height: 1.15; margin-top: .3mm; color: #222; display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
.fl-dat { font-size: 7.3pt; margin-top: .5mm; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fl-dat b { font-weight: 700; }
.fl-pre { margin-top: auto; font-size: 12.5pt; font-weight: 700; line-height: 1; text-align: right; color: #C8232B; }

/* ── Cierre con QR (final de la última cara) ── */
.fl-cierre { margin-top: auto; border: 2pt solid #C8232B; border-radius: 3mm; padding: 3mm 5mm;
  display: grid; grid-template-columns: 30mm 1fr; gap: 6mm; align-items: center; }
.fl-cierre svg { width: 30mm; height: 30mm; display: block; }
.fl-cierre-tit { font-size: 15pt; font-weight: 700; text-transform: uppercase; line-height: 1.1; }
.fl-cierre-txt { font-size: 9.5pt; margin-top: 1.5mm; }
.fl-cierre .fl-dom { font-size: 22pt; margin-top: 2mm; display: block; }
.fl-cierre-tel { font-size: 10pt; margin-top: 2.5mm; }
.fl-cierre-tel b { font-size: 12pt; }

.fl-pie { margin-top: 2.5mm; border-top: 1.5pt solid #C8232B; padding-top: 1.5mm; display: flex; justify-content: space-between; gap: 4mm; font-size: 7pt; }
.fl-grid + .fl-pie { margin-top: auto; }
`;
  function estilos() {
    if (document.getElementById('rd-folleto-css')) return;
    const st = document.createElement('style');
    st.id = 'rd-folleto-css';
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function cargarQR() {
    if (window.qrcode) return Promise.resolve();
    return new Promise((ok, ko) => {
      const s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/qrcode-generator/1.4.4/qrcode.min.js';
      s.onload = ok; s.onerror = ko;
      document.head.appendChild(s);
    });
  }
  function qrSVG(url) {
    try {
      const q = window.qrcode(0, 'M');
      q.addData(url);
      q.make();
      return q.createSvgTag({ cellSize: 4, margin: 0, scalable: true });
    } catch (_) { return ''; }
  }

  const hoy = () => new Date().toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });

  // "automovilesruedaocasion.com/alejandro" → automovilesrueda + [ocasion hueco] + .com + /alejandro
  function dominioHTML(web) {
    const m = /^(.*?)(ocasion)(\.[a-z.]+)(\/.*)?$/i.exec(web || '');
    if (!m) return `<span class="fl-dom">${esc(web)}</span>`;
    return `<span class="fl-dom">${esc(m[1])}<span class="fl-oc">${esc(m[2])}</span><span class="fl-tld">${esc(m[3])}</span>${
      m[4] && m[4] !== '/' ? `<span class="fl-ruta">${esc(m[4])}</span>` : ''}</span>`;
  }

  function tarjeta(c) {
    const fecha = c.fecha ? `<b>${esc(c.fecha)}</b>` : '';
    const km = c.km ? `<b>${esc(c.km)} km</b>` : '';
    return `<div class="fl-card">
  <div class="fl-foto">${c.foto ? `<img src="${esc(c.foto)}" alt="">` : ''}</div>
  <div class="fl-txt">
    <div class="fl-mod fl-osw">${esc(c.modelo)}</div>
    <div class="fl-ver">${esc(c.version)}</div>
    <div class="fl-dat">${[fecha, km].filter(Boolean).join(' · ')}</div>
    <div class="fl-dat">${esc([c.combustible, c.cambio].filter(Boolean).join(' · '))}</div>
    <div class="fl-pre fl-osw">${esc(c.precio)} €</div>
  </div>
</div>`;
  }

  function cabecera1(a, total) {
    return `
  <div class="fl-top">
    <div>
      <div class="fl-marca fl-osw">Automóviles Rueda</div>
      <div class="fl-lema">Coches de ocasión · SEAT · CUPRA · Das WeltAuto · <b>${total} disponibles hoy</b></div>
    </div>
    <div class="fl-contacto">
      <b>${esc(a.nombre)}</b> · <span class="fl-tel">${esc(a.telefono)}</span> <small>· WhatsApp</small><br>
      ${esc(a.email)}<br>${esc(a.direccion)}
    </div>
  </div>
  <div class="fl-web">
    <span class="fl-web-lbl">Todo el stock actualizado cada día,<br>con fotos, equipamiento y financiación, en</span>
    ${dominioHTML(a.web)}
  </div>`;
  }
  function cabecera2(a) {
    return `
  <div class="fl-head2"><span class="fl-marca fl-osw">Automóviles Rueda</span>${dominioHTML(a.web)}<span>${esc(a.nombre)} · <b>${esc(a.telefono)}</b></span></div>`;
  }
  function garantia() {
    return `
  <div class="fl-garantia">
    <div class="fl-gar-num fl-osw">5 años</div>
    <div>
      <div class="fl-gar-tit fl-osw">de garantía de fábrica*</div>
      <div class="fl-gar-txt">desde la fecha de matriculación en nuestros coches <b>SEAT · CUPRA</b></div>
      <div class="fl-gar-nota">* Disponibilidad según coche y procedencia.</div>
    </div>
  </div>`;
  }
  function cierre(a, qr) {
    return `
  <div class="fl-cierre">
    <div>${qr}</div>
    <div>
      <div class="fl-cierre-tit fl-osw">¿Quieres ver fotos, equipamiento y financiación?</div>
      <div class="fl-cierre-txt">Escanea el código con la cámara del móvil o entra en</div>
      ${dominioHTML(a.web)}
      <div class="fl-cierre-tel">${esc(a.nombre)} · <b>${esc(a.telefono)}</b> · llamadas y WhatsApp</div>
    </div>
  </div>`;
  }
  const pie = (a, p, total) => `<div class="fl-pie"><span>Precios y disponibilidad a ${hoy()} · sujetos a cambios</span><span>${esc(a.web)} · ${esc(a.telefono)}${total > 1 ? ' · ' + p + '/' + total : ''}</span></div>`;

  // Reparto midiendo de verdad (fuera de pantalla): se meten coches en la cara
  // hasta que no caben; la última cara lleva además el cierre con el QR.
  function maquetar(hoja, qr) {
    const a = D.asesor || {};
    const coches = D.coches || [];
    hoja.innerHTML = '';
    hoja.style.cssText = 'display:block;position:absolute;left:-10000px;top:0;';
    const sobra = cara => cara.scrollHeight > cara.clientHeight + 1;
    const nuevaCara = () => {
      const cara = document.createElement('div');
      cara.className = 'flp';
      const n = hoja.children.length;   // 0 = cara 1; la 2ª cara lleva la franja de garantía
      cara.innerHTML = (n ? cabecera2(a) : cabecera1(a, coches.length)) + (n === 1 ? garantia() : '')
        + '<div class="fl-grid"></div><div class="fl-pie"></div>';
      hoja.appendChild(cara);
      return cara;
    };
    let i = 0;
    let cara = nuevaCara();
    for (;;) {
      const grid = cara.querySelector('.fl-grid');
      while (i < coches.length) {
        grid.insertAdjacentHTML('beforeend', tarjeta(coches[i]));
        if (sobra(cara)) { grid.lastElementChild.remove(); break; }
        i++;
      }
      if (i < coches.length) { cara = nuevaCara(); continue; }
      // Todos colocados: el cierre con QR al final de esta cara, o en una cara nueva si no cabe
      cara.querySelector('.fl-pie').insertAdjacentHTML('beforebegin', cierre(a, qr));
      if (sobra(cara) && grid.children.length) {
        cara.querySelector('.fl-cierre').remove();
        // se pasa la última fila de coches a una cara nueva junto con el cierre
        const ultimos = Array.from(grid.children).slice(-3);
        cara = nuevaCara();
        ultimos.forEach(t => cara.querySelector('.fl-grid').appendChild(t));
        cara.querySelector('.fl-pie').insertAdjacentHTML('beforebegin', cierre(a, qr));
      }
      break;
    }
    const caras = Array.from(hoja.children);
    caras.forEach((c, p) => { c.querySelector('.fl-pie').outerHTML = pie(a, p + 1, caras.length); });
    hoja.removeAttribute('style');
  }

  // El folleto se PREPARA antes (al activar el modo asesor): QR, fuentes, reparto
  // medido y fotos cargadas. Así, al pulsar, window.print() se llama en el MISMO
  // clic: Safari (y otros) no abren la impresión si se llama tras esperas.
  let listo = null;        // fecha (dd/mm/aaaa) con la que se preparó
  let preparando = null;   // promesa en curso
  function hojaFolleto() {
    let hoja = document.getElementById('rd-folleto-sheet');
    if (!hoja) {
      hoja = document.createElement('div');
      hoja.id = 'rd-folleto-sheet';
      document.body.appendChild(hoja);
    }
    return hoja;
  }
  function preparar() {
    if (preparando) return preparando;
    preparando = (async () => {
      estilos();
      await cargarQR().catch(() => null);
      if (document.fonts && document.fonts.ready) await document.fonts.ready;   // medir con la letra definitiva
      const hoja = hojaFolleto();
      maquetar(hoja, qrSVG((D.asesor || {}).url || location.origin + '/'));
      const fotos = Array.from(hoja.querySelectorAll('img')).map(img => img.complete ? null
        : new Promise(ok => { img.onload = img.onerror = ok; })).filter(Boolean);
      await Promise.race([Promise.all(fotos), new Promise(ok => setTimeout(ok, 6000))]);
      listo = hoy();
    })().finally(() => { preparando = null; });
    return preparando;
  }
  function lanzarImpresion() {
    document.body.classList.add('rd-imp-folleto');
    window.addEventListener('afterprint', () => document.body.classList.remove('rd-imp-folleto'), { once: true });
    window.print();
  }
  async function imprimir(btn) {
    if (listo === hoy()) { lanzarImpresion(); return; }   // preparado: impresión inmediata
    btn.disabled = true;
    try {
      await preparar();
      lanzarImpresion();
    } finally {
      btn.disabled = false;
    }
  }

  function iniciar() {
    estilos();
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'rd-folleto-btn';
    btn.innerHTML = '🖨 Imprimir folleto <small>· solo asesor</small>';
    btn.addEventListener('click', () => imprimir(btn));
    document.body.appendChild(btn);
    window.rdImprimirFolleto = () => imprimir(btn);
    window.rdFolletoListo = () => listo === hoy();
    // En modo asesor se prepara ya (y al activarlo con los 5 toques)
    const siAsesor = () => {
      if (document.documentElement.classList.contains('rd-asesor') && listo !== hoy()) preparar().catch(() => null);
    };
    siAsesor();
    new MutationObserver(siAsesor).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();
