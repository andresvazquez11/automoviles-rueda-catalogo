// Banners de confianza (Das WeltAuto + taller Rueda) entre las filas del catálogo.
// Ordenador: el primero tras la 1ª fila y luego cada 2 filas. Móvil: cada 4 coches.
// Solo cuentan las tarjetas visibles. El filtro/buscador/orden de la portada
// (aplicar() en generar_web.py) llama a window.rdColocarBanners() después de
// reordenar las tarjetas, y aquí se recolocan también al cambiar el ancho.
(function () {
  const plantilla = document.getElementById('rd-banners');
  const grid = document.getElementById('rd-grid');
  if (!plantilla || !grid) return;
  const banners = [...plantilla.content.children];

  // Texto en el idioma actual sin llamar a rdAplicarIdioma (que re-dispara los filtros).
  function traducir(nodo) {
    const idioma = (window.rdIdiomaActual && window.rdIdiomaActual()) || 'es';
    nodo.querySelectorAll('.rd-i18n').forEach(el => {
      const txt = el.getAttribute('data-' + idioma);
      if (txt !== null) el.textContent = txt;
    });
    return nodo;
  }

  function colocar() {
    grid.querySelectorAll(':scope > .rd-banner').forEach(b => b.remove());
    const visibles = [...grid.querySelectorAll(':scope > .rd-card')].filter(c => c.style.display !== 'none');
    const cols = Math.max(1, getComputedStyle(grid).gridTemplateColumns.split(' ').length);
    const primero = Math.max(cols, 4);
    const paso = Math.max(cols * 2, 4);
    banners.forEach((b, i) => {
      const destino = visibles[primero + i * paso];
      if (destino) destino.before(traducir(b.cloneNode(true)));
    });
  }

  let pendiente = null;
  let colsPrevias = 0;
  window.addEventListener('resize', () => {
    clearTimeout(pendiente);
    pendiente = setTimeout(() => {
      const cols = getComputedStyle(grid).gridTemplateColumns.split(' ').length;
      if (cols !== colsPrevias) { colsPrevias = cols; colocar(); }
    }, 150);
  });
  // Al cambiar de idioma, traducir también los banners ya colocados.
  const previo = window.rdAlCambiarIdioma;
  window.rdAlCambiarIdioma = function () {
    if (typeof previo === 'function') previo.apply(this, arguments);
    grid.querySelectorAll(':scope > .rd-banner').forEach(traducir);
  };
  window.rdColocarBanners = colocar;
  colsPrevias = getComputedStyle(grid).gridTemplateColumns.split(' ').length;
  colocar();
})();
