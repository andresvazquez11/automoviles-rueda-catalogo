/* Movimiento compartido por todas las páginas con cabecera:
   1) Cabecera compacta al bajar (barra fina con efecto cristal).
   2) Transición de la foto tarjeta → ficha (View Transitions entre páginas).
   Se carga en el <head> SIN defer: el aviso 'pagereveal' tiene que estar
   escuchando antes del primer pintado de la página. */
(function () {
  var reducir = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── 1) Cabecera compacta ─────────────────────────────────────────
     Arriba del todo la cabecera es la de siempre (sticky, ocupa su sitio:
     nunca tapa nada, p. ej. "Volver al catálogo"). Solo al compactarse pasa
     a position:fixed y deja en su lugar un hueco con su altura completa,
     medida JUSTO antes de compactar: así el contenido de debajo no salta.
     (Antes el hueco se medía al cargar; en Safari a veces quedaba más bajo
     que la cabecera y esta tapaba el enlace de volver.) */
  function iniciarCabecera() {
    var header = document.querySelector('.rd-header');
    if (!header) return;
    var hueco = document.createElement('div');
    hueco.className = 'rd-header-hueco';
    header.insertAdjacentElement('afterend', hueco);

    var compacta = false;
    function actualizar() {
      var y = window.scrollY || window.pageYOffset;
      // Histéresis: se compacta al pasar 120px y no se expande hasta volver
      // por debajo de 40px — sin ella parpadea al parar justo en el umbral.
      var nueva = compacta ? y > 40 : y > 120;
      if (nueva === compacta) return;
      compacta = nueva;
      if (compacta) hueco.style.height = header.offsetHeight + 'px';
      document.body.classList.toggle('rd-header-fijo', compacta);
      header.classList.toggle('rd-header--compacto', compacta);
      // Reinicia el fundido de entrada del contenido de la cabecera.
      header.classList.remove('rd-header-cambia');
      void header.offsetWidth;
      header.classList.add('rd-header-cambia');
    }
    actualizar();
    window.addEventListener('scroll', actualizar, { passive: true });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciarCabecera);
  } else {
    iniciarCabecera();
  }

  /* ── 2) Foto tarjeta → ficha ──────────────────────────────────────
     La ficha nombra su galería 'rd-coche-foto' por CSS (estilos.css).
     En el catálogo solo se nombra la foto de la tarjeta PULSADA (dos
     elementos con el mismo nombre anulan la transición). Al volver
     atrás, se nombra la tarjeta de ese coche si está a la vista. */
  var NOMBRE = 'rd-coche-foto';
  var CLAVE = 'rd_vt_coche';

  function limpiarNombres() {
    var nombrados = document.querySelectorAll('.rd-card-media[style*="view-transition-name"]');
    for (var i = 0; i < nombrados.length; i++) nombrados[i].style.viewTransitionName = '';
    document.documentElement.classList.remove('rd-vt-saliendo');
  }

  function aLaVista(el) {
    var r = el.getBoundingClientRect();
    return r.bottom > 0 && r.top < window.innerHeight && r.width > 0;
  }

  if (reducir || !('onpagereveal' in window)) return;

  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var card = e.target.closest && e.target.closest('a.rd-card');
    if (!card || e.target.closest('button')) return;
    var media = card.querySelector('.rd-card-media');
    if (!media) return;
    limpiarNombres();
    // Congela la tarjeta en su estado normal (sin el efecto "el coche sale
    // de la tarjeta" a medias) para que la foto que vuela salga limpia.
    document.documentElement.classList.add('rd-vt-saliendo');
    media.style.viewTransitionName = NOMBRE;
    try { sessionStorage.setItem(CLAVE, card.dataset.id || ''); } catch (_) {}
  });

  // Si el navegador se salta la transición (pestaña en segundo plano, etc.)
  // rechaza sus promesas: se marcan como atendidas para no ensuciar la consola.
  function silenciar(vt) {
    if (!vt) return;
    vt.ready.catch(function () {});
    vt.updateCallbackDone.catch(function () {});
  }
  window.addEventListener('pageswap', function (e) { silenciar(e.viewTransition); });

  window.addEventListener('pagereveal', function (e) {
    limpiarNombres();
    if (!e.viewTransition) return;
    silenciar(e.viewTransition);
    var id;
    try { id = sessionStorage.getItem(CLAVE); } catch (_) {}
    if (!id || !document.getElementById('rd-grid')) return;
    var candidatas = document.querySelectorAll('.rd-card[data-id="' + id.replace(/"/g, '') + '"] .rd-card-media');
    for (var i = 0; i < candidatas.length; i++) {
      if (aLaVista(candidatas[i])) {
        var media = candidatas[i];
        media.style.viewTransitionName = NOMBRE;
        var soltar = function () { media.style.viewTransitionName = ''; };
        // then(ok, error): si el navegador se salta la transición, la promesa
        // se rechaza y, sin el manejador de error, saldría en la consola.
        e.viewTransition.finished.then(soltar, soltar);
        return;
      }
    }
  });

  // Vuelta con el botón "atrás" desde la caché (bfcache): quitar el estado congelado.
  window.addEventListener('pageshow', function (e) { if (e.persisted) limpiarNombres(); });
})();
