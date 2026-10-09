/* ══════════════════════════════════════════════════════════════════
   Automóviles Rueda — "Imprimir folleto" (solo modo asesor, portada)

   Hoja A4 a doble cara, en blanco y negro, con TODOS los coches
   disponibles en este momento, para dejar en la puerta del concesionario:
   cara 1 con marca, contacto del asesor, dirección de la web y un QR al
   catálogo; luego una ficha pequeña por coche (foto, modelo, versión,
   matriculación, km, combustible, cambio y precio).

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
.rd-folleto-btn { position: fixed; left: 14px; bottom: 18px; z-index: 9991; display: flex; align-items: center; gap: 8px;
  padding: 11px 16px; border: 0; border-radius: 999px; background: #14110f; color: #fff; cursor: pointer;
  font: 700 13px 'Work Sans', sans-serif; letter-spacing: .5px; box-shadow: 0 6px 20px rgba(0,0,0,.25); }
.rd-folleto-btn[disabled] { opacity: .6; cursor: wait; }
.rd-folleto-btn small { font-weight: 600; opacity: .7; font-size: 10px; letter-spacing: .6px; text-transform: uppercase; }

#rd-folleto-sheet { display: none; }
@media print {
  @page { size: A4 portrait; margin: 10mm; }
  html, body { background: #fff !important; margin: 0 !important; padding: 0 !important; }
  body > *:not(#rd-folleto-sheet) { display: none !important; }
  #rd-folleto-sheet { display: block !important; }
}
#rd-folleto-sheet, #rd-folleto-sheet * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.flp { width: 190mm; height: 276mm; overflow: hidden; display: flex; flex-direction: column; background: #fff; color: #000;
  font-family: 'Work Sans', Arial, sans-serif; font-size: 8.5pt; line-height: 1.3; }
.flp + .flp { break-before: page; page-break-before: always; }
.fl-osw { font-family: 'Oswald', 'Arial Narrow', Arial, sans-serif; }

.fl-head { display: grid; grid-template-columns: 1fr 34mm; gap: 6mm; align-items: center; border-bottom: 2.5pt solid #000; padding-bottom: 3mm; }
.fl-marca { font-size: 26pt; font-weight: 700; text-transform: uppercase; line-height: 1; letter-spacing: .5pt; }
.fl-lema { font-size: 9pt; font-weight: 600; margin-top: 1.5mm; letter-spacing: .3pt; }
.fl-contacto { margin-top: 2.5mm; font-size: 9.5pt; line-height: 1.45; }
.fl-contacto b { font-size: 11pt; }
.fl-qr { text-align: center; }
.fl-qr svg { width: 30mm; height: 30mm; display: block; margin: 0 auto; }
.fl-qr span { display: block; font-size: 6.8pt; line-height: 1.25; margin-top: 1mm; }
.fl-web { margin: 3mm 0 0; border: 2pt solid #000; padding: 2.2mm 4mm; display: flex; justify-content: space-between; align-items: baseline; gap: 4mm; }
.fl-web span { font-size: 8.5pt; font-weight: 700; letter-spacing: .6pt; text-transform: uppercase; }
.fl-web b { font-size: 16pt; letter-spacing: .3pt; }

.fl-head2 { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 2pt solid #000; padding-bottom: 1.5mm; font-size: 8.5pt; }
.fl-head2 .fl-marca { font-size: 13pt; }

.fl-grid { flex: 1; min-height: 0; margin-top: 3mm; display: grid; grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: 28mm; gap: 2.5mm 3mm; align-content: start; }
.fl-card { border: .8pt solid #000; display: grid; grid-template-columns: 25mm 1fr; overflow: hidden; }
.fl-foto { background: #ddd; overflow: hidden; }
.fl-foto img { width: 100%; height: 100%; object-fit: cover; display: block; filter: grayscale(1) contrast(1.08); }
.fl-txt { padding: 1.4mm 2mm 1.2mm; display: flex; flex-direction: column; min-width: 0; }
.fl-mod { font-size: 10pt; font-weight: 700; text-transform: uppercase; line-height: 1.05; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fl-ver { font-size: 6.6pt; line-height: 1.2; margin-top: .4mm; color: #222; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.fl-dat { font-size: 7.4pt; margin-top: .6mm; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fl-dat b { font-weight: 700; }
.fl-pre { margin-top: auto; font-size: 13pt; font-weight: 700; line-height: 1; text-align: right; }

.fl-pie { margin-top: 2mm; border-top: 1pt solid #000; padding-top: 1.5mm; display: flex; justify-content: space-between; gap: 4mm; font-size: 7pt; }
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

  // Cara 1: 7 filas de 3 (debajo de la cabecera); siguientes caras: 8 filas de 3
  const POR_CARA = [21, 24];

  function folletoHTML(qr) {
    const a = D.asesor || {};
    const coches = D.coches || [];
    const caras = [];
    let i = 0, n = 0;
    while (i < coches.length || n === 0) {
      const cap = POR_CARA[Math.min(n, POR_CARA.length - 1)];
      caras.push(coches.slice(i, i + cap));
      i += cap; n++;
    }
    const total = caras.length;
    const pie = p => `<div class="fl-pie"><span>Precios y disponibilidad a ${hoy()} · sujetos a cambios · Fotos e información completa en la web</span><span>${esc(a.web)} · ${esc(a.telefono)}${total > 1 ? ' · ' + p + '/' + total : ''}</span></div>`;
    return caras.map((lista, p) => {
      const cabecera = p === 0 ? `
  <div class="fl-head">
    <div>
      <div class="fl-marca fl-osw">Automóviles Rueda</div>
      <div class="fl-lema">Coches de ocasión seleccionados · SEAT · CUPRA · Das WeltAuto · ${coches.length} coches disponibles</div>
      <div class="fl-contacto">
        <b>${esc(a.nombre)} · ${esc(a.telefono)}</b> (llamadas y WhatsApp)<br>
        ${esc(a.email)}<br>${esc(a.direccion)}
      </div>
    </div>
    <div class="fl-qr">${qr}<span>Escanéame: fotos, equipamiento y financiación</span></div>
  </div>
  <div class="fl-web"><span>Todo el stock actualizado cada día en</span><b class="fl-osw">${esc(a.web)}</b></div>` : `
  <div class="fl-head2"><span class="fl-marca fl-osw">Automóviles Rueda</span><span>${esc(a.nombre)} · <b>${esc(a.telefono)}</b> · <b>${esc(a.web)}</b></span></div>`;
      return `<div class="flp">${cabecera}
  <div class="fl-grid">${lista.map(tarjeta).join('')}</div>
  ${pie(p + 1)}
</div>`;
    }).join('');
  }

  async function imprimir(btn) {
    btn.disabled = true;
    try {
      estilos();
      await cargarQR().catch(() => null);
      let hoja = document.getElementById('rd-folleto-sheet');
      if (!hoja) {
        hoja = document.createElement('div');
        hoja.id = 'rd-folleto-sheet';
        document.body.appendChild(hoja);
      }
      hoja.innerHTML = folletoHTML(qrSVG((D.asesor || {}).url || location.origin + '/'));
      // Esperar a las fotos (máx. 4 s) y a las fuentes antes de abrir la impresión
      const fotos = Array.from(hoja.querySelectorAll('img')).map(img => img.complete ? null
        : new Promise(ok => { img.onload = img.onerror = ok; })).filter(Boolean);
      const fuentes = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
      await Promise.race([Promise.all([Promise.all(fotos), fuentes]), new Promise(ok => setTimeout(ok, 4000))]);
      window.print();
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
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();
