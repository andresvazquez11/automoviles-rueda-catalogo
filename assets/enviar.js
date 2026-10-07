/* ══════════════════════════════════════════════════════════════════
   Automóviles Rueda — "Enviar al cliente por WhatsApp" (solo asesores)

   1) MODO ASESOR (botón secreto): los botones de enviar Y los de imprimir
      (simulación y ficha A4) solo aparecen en los dispositivos de los
      asesores, con un marco ámbar "Modo asesor" alrededor de la página. Se activa tocando 5 veces seguidas
      el nombre "Automóviles Rueda" de la cabecera (y otras 5 lo quitan).
      Queda guardado en ese navegador (localStorage 'rd_asesor').

   2) ENVIAR (panel del asesor), dos maneras:
      · Enlace: se escribe el teléfono del cliente y se abre WhatsApp en su
        chat con un mensaje + un enlace a la hoja (simulación o ficha).
      · PDF: genera el PDF de la hoja y abre el menú "Compartir" del móvil
        (WhatsApp → contacto). En ordenador, descarga el PDF y abre el chat
        para arrastrarlo.

   3) VISTA DEL CLIENTE: cuando el cliente abre el enlace (?ver=sim… o
      ?ver=ficha), la ficha reproduce la misma financiación y muestra la hoja
      A4 encima, con "Descargar PDF" y "Ver el coche".

   Depende de imprimir.js (window.rdHojas) y calculadora.js. El PDF usa
   html2canvas + jsPDF (cdnjs), que solo se descargan al pulsar.
   ══════════════════════════════════════════════════════════════════ */

(function () {
  const LS_ASESOR = 'rd_asesor';
  const LS_ENVIOS = 'rd_envios';
  const lsGet = k => { try { return localStorage.getItem(k); } catch (_) { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (_) {} };
  const lsDel = k => { try { localStorage.removeItem(k); } catch (_) {} };

  const esc = s => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const miles = s => s.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const eur  = n => miles(String(Math.round(n))) + ' €';
  const eur2 = n => { const [e, d] = Math.abs(Number(n)).toFixed(2).split('.'); return miles(e) + ',' + d + ' €'; };

  const coche  = () => (typeof COCHE !== 'undefined' ? COCHE : null);
  const asesor = () => (typeof ASESOR !== 'undefined' ? ASESOR : {});

  // ── 1) Modo asesor ──────────────────────────────────────────────────────
  function aviso(txt) {
    estilos();
    const t = document.createElement('div');
    t.className = 'rde-toast';
    t.textContent = txt;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 4000);
  }
  const esAsesor = () => lsGet(LS_ASESOR) === '1';

  // 5 toques seguidos (menos de 1,5 s entre uno y otro) en el nombre de la cabecera
  let toques = 0, ultimoToque = 0;
  document.addEventListener('click', e => {
    if (!e.target.closest || !e.target.closest('.rd-marca strong')) return;
    const ahora = Date.now();
    toques = ahora - ultimoToque < 1500 ? toques + 1 : 1;
    ultimoToque = ahora;
    if (toques < 5) return;
    toques = 0;
    if (esAsesor()) {
      lsDel(LS_ASESOR);
      modoAsesor(false);
      aviso('Modo asesor desactivado en este dispositivo');
    } else {
      lsSet(LS_ASESOR, '1');
      modoAsesor(true);
      aviso('✅ Modo asesor activado en este dispositivo');
    }
  });

  // Modo asesor = clase rd-asesor en <html>: enseña los botones de imprimir
  // (ocultos para el cliente en estilos.css), los de enviar y el marco ámbar.
  function modoAsesor(on) {
    estilos();
    document.documentElement.classList.toggle('rd-asesor', on);
    let marca = document.getElementById('rde-marco');
    if (on && !marca) {
      marca = document.createElement('div');
      marca.id = 'rde-marco';
      marca.innerHTML = '<span>Modo asesor</span>';
      document.body.appendChild(marca);
    }
    if (!on && marca) marca.remove();
    if (on) ponerBotones();
    else document.querySelectorAll('.rde-btn-enviar').forEach(b => b.remove());
  }

  // En el ordenador no hay app de WhatsApp: se usa WhatsApp Web directamente.
  const esOrdenador = () => !/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)
    && !(navigator.maxTouchPoints > 1 && /Macintosh/.test(navigator.userAgent));   // iPad "de escritorio"
  function abrirChat(tel, texto) {
    const t = texto ? encodeURIComponent(texto) : '';
    if (esOrdenador()) {
      const url = 'https://web.whatsapp.com/send?' + (tel ? 'phone=' + tel + '&' : '') + (t ? 'text=' + t : '');
      window.open(url, 'rd-whatsapp');   // reutiliza la pestaña de WhatsApp Web si ya está abierta
    } else {
      window.open('https://wa.me/' + (tel || '') + (t ? '?text=' + t : ''), '_blank', 'noopener');
    }
  }

  // ── Estilos ─────────────────────────────────────────────────────────────
  const CSS = `
#rde-marco { position: fixed; inset: 0; z-index: 9990; pointer-events: none; border: 5px solid #F5A623; }
#rde-marco span { position: absolute; top: 0; left: 50%; transform: translateX(-50%); background: #F5A623; color: #14110f;
  font: 700 11px 'Work Sans', sans-serif; letter-spacing: 1.5px; text-transform: uppercase; padding: 3px 14px 5px;
  border-radius: 0 0 8px 8px; }
.rde-toast { position: fixed; left: 50%; bottom: 90px; transform: translateX(-50%); z-index: 10001;
  background: #14110f; color: #fff; padding: 12px 18px; border-radius: 10px; font: 600 14px 'Work Sans', sans-serif;
  box-shadow: 0 8px 30px rgba(0,0,0,.3); max-width: calc(100% - 32px); text-align: center; }
.rde-btn-enviar { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%;
  padding: 13px 20px; border: 1.5px dashed #25D366; background: rgba(37,211,102,.08); color: #25D366;
  font: 700 13px 'Work Sans', sans-serif; letter-spacing: 1.2px; text-transform: uppercase; cursor: pointer; border-radius: 6px; }
.rde-btn-enviar:hover { background: rgba(37,211,102,.16); }
.rde-btn-enviar small { font-size: 9px; letter-spacing: .8px; opacity: .8; font-weight: 600; }
.rd-btn-imprimir-ficha + .rde-btn-enviar { margin: -8px 0 18px; }

.rde-fondo { position: fixed; inset: 0; z-index: 10000; background: rgba(20,17,15,.62);
  display: flex; align-items: flex-end; justify-content: center; }
@media (min-width: 640px) { .rde-fondo { align-items: center; } }
.rde-panel { background: #fff; color: #14110f; width: 100%; max-width: 460px; max-height: 92vh; overflow: auto;
  border-radius: 16px 16px 0 0; padding: 20px 18px 22px; font-family: 'Work Sans', sans-serif; }
@media (min-width: 640px) { .rde-panel { border-radius: 14px; } }
.rde-panel h3 { margin: 0; font: 700 20px 'Oswald', sans-serif; text-transform: uppercase; letter-spacing: .5px; }
.rde-sub { font-size: 13px; color: #6b645e; margin: 3px 0 16px; }
.rde-cerrar { float: right; border: 0; background: #f2f1ed; width: 34px; height: 34px; border-radius: 50%;
  font-size: 18px; cursor: pointer; color: #14110f; }
.rde-lbl { display: block; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
  color: #6b645e; margin: 14px 0 6px; }
.rde-tipos { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.rde-tipo { border: 1.5px solid #d9d5ce; border-radius: 10px; padding: 10px; cursor: pointer; font-size: 13px; line-height: 1.3; background: #fff; text-align: left; color: #14110f; }
.rde-tipo b { display: block; font-size: 14px; }
.rde-tipo.activo { border-color: #14110f; background: #14110f; color: #fff; }
.rde-input { width: 100%; box-sizing: border-box; padding: 12px 14px; font: 600 17px 'Work Sans', sans-serif;
  border: 1.5px solid #d9d5ce; border-radius: 10px; color: #14110f; background: #fff; }
.rde-input:focus { outline: none; border-color: #25D366; }
.rde-fila { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.rde-err { color: #C8232B; font-size: 12.5px; margin-top: 6px; min-height: 0; }
.rde-acc { display: flex; align-items: center; justify-content: center; gap: 9px; width: 100%; margin-top: 10px;
  padding: 14px 16px; border-radius: 10px; border: 0; cursor: pointer; font: 700 14px 'Work Sans', sans-serif;
  letter-spacing: .6px; text-transform: uppercase; text-decoration: none; }
.rde-acc.verde { background: #25D366; color: #fff; margin-top: 18px; }
.rde-acc.negro { background: #14110f; color: #fff; }
.rde-acc[disabled] { opacity: .55; cursor: wait; }
.rde-nota { font-size: 12px; color: #6b645e; margin-top: 6px; line-height: 1.45; }
.rde-hist { margin-top: 18px; border-top: 1px solid #ece9e4; padding-top: 10px; }
.rde-hist a { display: flex; justify-content: space-between; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f2f1ed;
  color: #14110f; text-decoration: none; font-size: 13px; }
.rde-hist a span:last-child { color: #6b645e; white-space: nowrap; }

.rdv { position: fixed; inset: 0; z-index: 9999; background: #8a857f; overflow: auto; -webkit-overflow-scrolling: touch; }
.rdv-barra { position: sticky; top: 0; z-index: 2; display: flex; gap: 8px; padding: 10px 12px; background: #14110f;
  box-shadow: 0 2px 12px rgba(0,0,0,.35); }
.rdv-barra button { flex: 1; padding: 12px 10px; border-radius: 8px; border: 0; cursor: pointer;
  font: 700 13px 'Work Sans', sans-serif; letter-spacing: .6px; text-transform: uppercase; }
.rdv-pdf { background: #C8232B; color: #fff; }
.rdv-ver { background: #fff; color: #14110f; }
.rdv-papel { background: #fff; width: 210mm; min-height: 297mm; box-sizing: border-box; padding: 11mm 12mm;
  margin: 16px auto 30px; box-shadow: 0 6px 30px rgba(0,0,0,.35); }
.rdv-papel .rdp-foto img, .rde-captura .rdp-foto img { filter: grayscale(1) contrast(1.08); }
.rde-captura { position: fixed; left: -10000px; top: 0; width: 210mm; height: 297mm; box-sizing: border-box;
  padding: 11mm 12mm; background: #fff; }
/* html2canvas dibuja el texto grande de Oswald más abajo que el navegador: más aire en el PDF */
.rde-captura .rdp-cuota-val { line-height: 1.3; margin-top: 0; }
.rde-captura .rdp-cuota-sub { margin-top: 1.5mm; }
.rde-captura .rdp-precio, .rde-captura .rdp-modelo { line-height: 1.2; }
`;
  function estilos() {
    if (document.getElementById('rde-css')) return;
    const st = document.createElement('style');
    st.id = 'rde-css';
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  // ── Estado de la calculadora → parámetros del enlace (y al revés) ─────────
  function estadoActual(f) {
    if (f === 'BBVA')  return { f, e: BBVA.entrada, m: BBVA.meses };
    if (f === 'CAIXA') return { f, e: CAIXA.entrada, m: CAIXA.meses };
    const s = { f: 'VWFS', e: CV2.entrada, m: CV2.meses, t: CV2.tab, k: CV2.km, c: CV2.campana,
      a: CV2.mantAnios, ct: CV2.cupraTipo, dr: CV2.demosRema ? 1 : 0 };
    if (CV2.tinOverride != null) s.tin = CV2.tinOverride;
    return s;
  }

  function aplicarEstado(p) {
    const n = k => parseFloat(p.get(k)) || 0;
    const f = p.get('f') || 'VWFS';
    const tab = document.getElementById(f === 'BBVA' ? 'fin-bbva' : f === 'CAIXA' ? 'fin-caixa' : 'fin-vwfs');
    if (typeof setFinanciera === 'function') setFinanciera(f, tab);
    if (f === 'BBVA')  { bbvaSetMeses(n('m') || 60); bbvaEntradaInput(n('e')); return f; }
    if (f === 'CAIXA') { caixaSetMeses(n('m') || 60); caixaEntradaInput(n('e')); return f; }
    if (p.get('c') && p.get('c') !== CV2.campana) cv2SetCampana(p.get('c'));
    if (p.get('ct')) cv2SetCupraTipo(p.get('ct'));
    if ((p.get('dr') === '1') !== !!CV2.demosRema && typeof cv2ToggleDemosRema === 'function') cv2ToggleDemosRema();
    cv2SetMode(p.get('t') === 'flex' ? 'flex' : 'lineal');
    if (p.get('t') === 'flex' && n('k')) cv2SetKm(n('k'));
    if (n('m')) cv2SetMeses(n('m'));
    if (p.has('a')) cv2SetMant(n('a'));
    cv2EntradaInput(n('e'));
    if (p.has('tin')) { CV2.tinOverride = n('tin'); cv2Render(); }
    return f;
  }

  function enlace(tipo, f) {
    const url = new URL(location.origin + location.pathname);
    if (tipo === 'ficha') {
      url.searchParams.set('ver', 'ficha');
    } else {
      url.searchParams.set('ver', 'sim');
      const s = estadoActual(f);
      Object.keys(s).forEach(k => url.searchParams.set(k, s[k]));
    }
    return url.toString();
  }

  // ── Mensaje de WhatsApp ───────────────────────────────────────────────────
  function mensaje(tipo, f, nombre, link) {
    const c = coche() || {};
    const a = asesor();
    const modelo = ((c.modelo || '') + ' ' + (c.version || '')).trim();
    let m = `Hola${nombre ? ' ' + nombre : ''}, soy ${a.nombreCorto || a.nombre || ''} de Automóviles Rueda.\n\n`;
    if (tipo === 'ficha') {
      m += `Te paso la ficha del *${modelo}*` + (c.precio ? ` (${c.precio} €)` : '') + '.\n\n';
      m += `Aquí la tienes completa, también la puedes descargar en PDF:\n${link}`;
    } else {
      const h = window.rdHojas.simulacion(f);
      const fin = h.fin;
      const claves = Object.fromEntries(fin.claves.map(([l, v]) => [l, v]));
      m += `Te paso la simulación de financiación del *${modelo}*:\n\n`;
      m += `• Cuota: *${eur2(fin.cuota)}/mes*\n`;
      if (claves['Plazo']) m += `• Plazo: ${claves['Plazo']}\n`;
      if (claves['Entrada']) m += `• Entrada: ${claves['Entrada']}\n`;
      const cf = fin.claves.find(([l]) => /^Cuota final/.test(l));
      if (cf) m += `• ${cf[0]}: ${cf[1]}\n`;
      m += `• ${fin.entidad}\n\n`;
      m += `Aquí la tienes completa, con todo el desglose (la puedes descargar en PDF):\n${link}`;
    }
    m += `\n\nCualquier duda me dices. ${a.telefonoDisplay || ''}`.trimEnd();
    return m;
  }

  // Teléfono → formato internacional para wa.me ("612 34 56 78" → 34612345678)
  function normalizarTel(t) {
    let d = String(t || '').trim();
    const mas = d.startsWith('+');
    d = d.replace(/\D/g, '');
    if (!d) return '';
    if (d.startsWith('00')) d = d.slice(2);
    else if (!mas && d.length === 9 && /^[6789]/.test(d)) d = '34' + d;
    return d.length >= 10 && d.length <= 15 ? d : null;
  }

  function guardarEnvio(e) {
    let lista = [];
    try { lista = JSON.parse(lsGet(LS_ENVIOS) || '[]'); } catch (_) {}
    lista.unshift(e);
    lsSet(LS_ENVIOS, JSON.stringify(lista.slice(0, 40)));
  }
  function ultimosEnvios() {
    try { return JSON.parse(lsGet(LS_ENVIOS) || '[]').slice(0, 6); } catch (_) { return []; }
  }

  // ── PDF (html2canvas + jsPDF, cargados solo al pulsar) ─────────────────────
  const cargado = {};
  function cargarScript(src) {
    if (!cargado[src]) cargado[src] = new Promise((ok, ko) => {
      const s = document.createElement('script');
      s.src = src; s.onload = ok; s.onerror = () => ko(new Error('No se pudo cargar ' + src));
      document.head.appendChild(s);
    });
    return cargado[src];
  }
  async function librerias() {
    await Promise.all([
      cargarScript('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js'),
      cargarScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'),
    ]);
  }
  // html2canvas no aplica el filtro CSS de escala de grises: se convierte la foto a mano.
  function fotoEnGrises(img) {
    return new Promise(ok => {
      const hecho = () => {
        try {
          const cv = document.createElement('canvas');
          cv.width = img.naturalWidth; cv.height = img.naturalHeight;
          const cx = cv.getContext('2d');
          cx.filter = 'grayscale(1) contrast(1.08)';
          cx.drawImage(img, 0, 0);
          if (cx.filter === 'none' || cx.filter === undefined) {   // Safari antiguo: a mano
            const d = cx.getImageData(0, 0, cv.width, cv.height), p = d.data;
            for (let i = 0; i < p.length; i += 4) { const g = p[i] * .299 + p[i + 1] * .587 + p[i + 2] * .114; p[i] = p[i + 1] = p[i + 2] = g; }
            cx.putImageData(d, 0, 0);
          }
          img.style.filter = 'none';
          img.src = cv.toDataURL('image/jpeg', 0.9);
          img.onload = ok;
        } catch (_) { ok(); }
      };
      if (img.complete && img.naturalWidth) hecho(); else { img.onload = hecho; img.onerror = ok; }
    });
  }
  async function generarPDF(html) {
    await librerias();
    const caja = document.createElement('div');
    caja.className = 'rde-captura';
    caja.innerHTML = html;
    document.body.appendChild(caja);
    try {
      window.rdHojas.preparar(caja);
      caja.style.cssText = '';            // preparar() la devuelve a su sitio (fuera de pantalla)
      const img = caja.querySelector('.rdp-foto img');
      if (img) await fotoEnGrises(img);
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
      const lienzo = await window.html2canvas(caja, { scale: 2, backgroundColor: '#ffffff', useCORS: true, logging: false });
      const pdf = new window.jspdf.jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
      pdf.addImage(lienzo.toDataURL('image/jpeg', 0.92), 'JPEG', 0, 0, 210, 297);
      return pdf.output('blob');
    } finally {
      caja.remove();
    }
  }
  function nombrePDF(tipo) {
    const c = coche() || {};
    const base = (c.modelo || 'coche').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^\w]+/g, '-').replace(/^-|-$/g, '');
    return (tipo === 'ficha' ? 'Ficha-' : 'Simulacion-') + base + '.pdf';
  }
  function descargar(blob, nombre) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = nombre;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000);
  }
  function htmlHoja(tipo, f) {
    if (tipo === 'ficha') return window.rdHojas.ficha().html;
    const h = window.rdHojas.simulacion(f);
    return h ? h.html : null;
  }

  // ── 2) Panel del asesor ───────────────────────────────────────────────────
  const ICONO_WA = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.9 9.9 0 004.74 1.21h.01c5.46 0 9.91-4.45 9.91-9.91A9.85 9.85 0 0012.04 2zm5.8 14.03c-.25.69-1.43 1.32-1.99 1.41-.51.08-1.15.11-1.86-.12-.43-.13-.98-.32-1.69-.62-2.98-1.29-4.92-4.29-5.07-4.49-.15-.2-1.21-1.61-1.21-3.07 0-1.46.77-2.18 1.04-2.48.27-.3.6-.37.79-.37h.57c.18 0 .43-.07.67.51.25.6.84 2.06.92 2.21.07.15.12.32.02.52-.1.2-.15.32-.3.5-.15.17-.31.39-.45.52-.15.15-.3.31-.13.6.17.3.77 1.27 1.65 2.06 1.14 1.01 2.09 1.33 2.39 1.48.3.15.47.12.64-.07.17-.2.74-.87.94-1.17.2-.3.39-.25.67-.15.27.1 1.73.82 2.03.97.3.15.49.22.57.34.07.13.07.72-.18 1.42z"/></svg>';

  function abrirPanel(tipoInicial, f) {
    estilos();
    const c = coche() || {};
    let tipo = tipoInicial;
    const nombreFin = { VWFS: 'VWFS', BBVA: 'BBVA', CAIXA: 'CaixaBank' }[f] || 'VWFS';
    const hist = ultimosEnvios();
    const fondo = document.createElement('div');
    fondo.className = 'rde-fondo';
    fondo.innerHTML = `
<div class="rde-panel" role="dialog" aria-label="Enviar al cliente">
  <button class="rde-cerrar" type="button" aria-label="Cerrar">✕</button>
  <h3>Enviar al cliente</h3>
  <div class="rde-sub">${esc(c.modelo || '')} · ${esc(c.precio || '')} €</div>

  <span class="rde-lbl">Qué le envías</span>
  <div class="rde-tipos">
    ${f ? `<button type="button" class="rde-tipo" data-tipo="sim"><b>Financiación</b>Simulación ${esc(nombreFin)} tal como la tienes</button>` : ''}
    <button type="button" class="rde-tipo" data-tipo="ficha"><b>Ficha del coche</b>Características, sin financiación</button>
  </div>

  <div class="rde-fila">
    <div><span class="rde-lbl">Teléfono del cliente</span>
      <input class="rde-input" id="rde-tel" type="tel" inputmode="tel" autocomplete="off" placeholder="612 345 678"></div>
    <div><span class="rde-lbl">Nombre (opcional)</span>
      <input class="rde-input" id="rde-nom" type="text" autocomplete="off" placeholder="Juan"></div>
  </div>
  <div class="rde-err" id="rde-err"></div>

  <button type="button" class="rde-acc verde" id="rde-wa">${ICONO_WA} Abrir su chat con el enlace</button>
  <div class="rde-nota">Se abre WhatsApp en el chat de ese número con el mensaje escrito y el enlace a la hoja. Solo tienes que darle a enviar.</div>

  <button type="button" class="rde-acc negro" id="rde-pdf">📄 Enviar el PDF</button>
  <div class="rde-nota" id="rde-pdf-nota">${esOrdenador()
    ? 'Se descarga el PDF y se abre WhatsApp Web en el chat del cliente: arrastra el PDF al chat (o pulsa el clip 📎 → Documento).'
    : 'Se abre "Compartir": elige WhatsApp y el cliente.'}</div>

  ${hist.length ? `<div class="rde-hist"><span class="rde-lbl" style="margin-top:0">Últimos envíos desde este dispositivo</span>
    ${hist.map(h => `<a href="${esOrdenador() ? 'https://web.whatsapp.com/send?phone=' + esc(h.tel) : 'https://wa.me/' + esc(h.tel)}" target="${esOrdenador() ? 'rd-whatsapp' : '_blank'}" rel="noopener">
      <span>${esc(h.nombre || '+' + h.tel)} · ${esc(h.coche)}</span><span>${esc(h.fecha)}</span></a>`).join('')}</div>` : ''}
</div>`;
    document.body.appendChild(fondo);

    const $ = s => fondo.querySelector(s);
    const marcarTipo = () => fondo.querySelectorAll('.rde-tipo').forEach(b => b.classList.toggle('activo', b.dataset.tipo === tipo));
    marcarTipo();
    fondo.querySelectorAll('.rde-tipo').forEach(b => b.addEventListener('click', () => { tipo = b.dataset.tipo; marcarTipo(); }));
    const cerrar = () => fondo.remove();
    $('.rde-cerrar').addEventListener('click', cerrar);
    fondo.addEventListener('click', e => { if (e.target === fondo) cerrar(); });

    const leerTel = obligatorio => {
      const bruto = $('#rde-tel').value;
      const tel = normalizarTel(bruto);
      $('#rde-err').textContent = '';
      if (tel === null || (obligatorio && !tel)) {
        $('#rde-err').textContent = bruto.trim() ? 'Revisa el número (ej. 612 345 678 o +44 7700 900123).' : 'Escribe el teléfono del cliente.';
        $('#rde-tel').focus();
        return null;
      }
      return tel;
    };
    const apuntar = tel => {
      if (!tel) return;
      guardarEnvio({ tel, nombre: $('#rde-nom').value.trim(), coche: c.modelo || '', tipo,
        fecha: new Date().toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' }) });
    };
    const textoMensaje = () => mensaje(tipo, f, $('#rde-nom').value.trim(), enlace(tipo, f));

    // Opción 1: chat del cliente con mensaje + enlace
    $('#rde-wa').addEventListener('click', () => {
      if (tipo === 'sim' && !window.rdHojas.simulacion(f)) { $('#rde-err').textContent = 'Esta financiación no está disponible para este coche.'; return; }
      const tel = leerTel(true);
      if (!tel) return;
      apuntar(tel);
      abrirChat(tel, textoMensaje());
      cerrar();
    });

    // Opción 2: PDF por el menú Compartir (móvil) o descarga + chat (ordenador)
    let pdfListo = null;
    const btnPdf = $('#rde-pdf');
    const compartir = async () => {
      const file = new File([pdfListo], nombrePDF(tipo), { type: 'application/pdf' });
      const datos = { files: [file], text: textoMensaje() };
      const conTexto = navigator.canShare && navigator.canShare(datos);
      await navigator.share(conTexto ? datos : { files: [file] });
    };
    btnPdf.addEventListener('click', async () => {
      const html = htmlHoja(tipo, f);
      if (!html) { $('#rde-err').textContent = 'Esta financiación no está disponible para este coche.'; return; }
      const tel = leerTel(false);
      if (tel === null) return;
      try {
        if (!pdfListo) {
          btnPdf.disabled = true;
          btnPdf.textContent = 'Preparando PDF…';
          pdfListo = await generarPDF(html);
          btnPdf.disabled = false;
          btnPdf.textContent = '📄 Enviar el PDF';
        }
        const probe = new File([pdfListo], nombrePDF(tipo), { type: 'application/pdf' });
        if (!esOrdenador() && navigator.canShare && navigator.canShare({ files: [probe] })) {
          try {
            await compartir();
            apuntar(tel);
            cerrar();
          } catch (e) {
            if (e && e.name === 'NotAllowedError') {
              // El navegador pide otro toque tras preparar el PDF
              btnPdf.textContent = '📤 Pulsa para compartir el PDF';
              $('#rde-pdf-nota').textContent = 'PDF listo. Pulsa otra vez para abrir Compartir → WhatsApp.';
            }
            // AbortError = el asesor cerró el menú: no se hace nada
          }
        } else {
          descargar(pdfListo, nombrePDF(tipo));
          apuntar(tel);
          abrirChat(tel, textoMensaje());
          $('#rde-pdf-nota').textContent = '✓ PDF descargado («' + nombrePDF(tipo) + '»). Arrástralo al chat de WhatsApp Web que se ha abierto, o usa el clip 📎 → Documento.';
        }
      } catch (err) {
        btnPdf.disabled = false;
        btnPdf.textContent = '📄 Enviar el PDF';
        $('#rde-err').textContent = 'No se pudo crear el PDF (' + (err && err.message || err) + '). Usa la opción del enlace.';
      }
    });

    setTimeout(() => $('#rde-tel').focus(), 50);
  }

  function botonEnviar(tipo, f) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'rde-btn-enviar';
    b.innerHTML = `${ICONO_WA} Enviar al cliente <small>· solo asesor</small>`;
    b.addEventListener('click', () => abrirPanel(tipo, f));
    return b;
  }

  function ponerBotones() {
    if (!coche() || coche().vendido || !window.rdHojas || document.querySelector('.rde-btn-enviar')) return;
    estilos();
    document.querySelectorAll('.btn-print').forEach(bp => {
      const m = /rdImprimirSimulacion\('(\w+)'\)/.exec(bp.getAttribute('onclick') || '');
      if (m) bp.insertAdjacentElement('afterend', botonEnviar('sim', m[1]));
    });
    const bf = document.querySelector('.rd-btn-imprimir-ficha');
    if (bf) bf.insertAdjacentElement('afterend', botonEnviar('ficha', null));
  }

  // ── 3) Vista del cliente (abre el enlace) ─────────────────────────────────
  function vistaCliente() {
    const p = new URLSearchParams(location.search);
    const ver = p.get('ver');
    if (!coche() || !window.rdHojas || (ver !== 'sim' && ver !== 'ficha')) return;
    if (coche().vendido) return;   // la ficha ya enseña el aviso de vendido
    let f = null;
    if (ver === 'sim') f = aplicarEstado(p);
    const tipo = ver;
    const html = htmlHoja(tipo, f);
    if (!html) return;
    estilos();

    const capa = document.createElement('div');
    capa.className = 'rdv';
    capa.innerHTML = `
<div class="rdv-barra">
  <button type="button" class="rdv-pdf">⬇ Descargar PDF</button>
  <button type="button" class="rdv-ver">Ver el coche ›</button>
</div>
<div class="rdv-papel"><div class="rdv-hoja">${html}</div></div>`;
    document.body.appendChild(capa);
    document.documentElement.style.overflow = 'hidden';
    window.rdHojas.preparar(capa.querySelector('.rdv-hoja'));

    const papel = capa.querySelector('.rdv-papel');
    // zoom (no transform) para que la hoja reduzca también su hueco y quede centrada en el móvil
    const escalar = () => {
      papel.style.zoom = '';
      papel.style.zoom = Math.min(1, (window.innerWidth - 16) / papel.offsetWidth);
    };
    escalar();
    window.addEventListener('resize', escalar);

    capa.querySelector('.rdv-ver').addEventListener('click', () => {
      capa.remove();
      document.documentElement.style.overflow = '';
      const destino = document.getElementById(tipo === 'sim' ? 'financiera-tabs' : 'm-modelo');
      if (destino) destino.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    const btn = capa.querySelector('.rdv-pdf');
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      btn.textContent = 'Preparando…';
      try {
        descargar(await generarPDF(html), nombrePDF(tipo));
        btn.textContent = '✓ PDF descargado';
      } catch (_) {
        btn.textContent = 'Imprimir / guardar PDF';
        btn.onclick = () => { capa.remove(); document.documentElement.style.overflow = '';
          tipo === 'sim' ? rdImprimirSimulacion(f) : rdImprimirFicha(); };
      }
      btn.disabled = false;
    });
  }

  function iniciar() {
    vistaCliente();
    if (esAsesor()) modoAsesor(true);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();
