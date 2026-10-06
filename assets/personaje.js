/* Muñeco de palitos del catálogo: aparece como mucho 2 veces por visita
   (sessionStorage) sobre coches en oferta / destacados y recomienda el coche
   con un cartel. 1ª vez: cae del cielo sobre la tarjeta. 2ª vez: se asoma por
   detrás de la tarjeta, saluda y se esconde.
   Nunca recibe clics (pointer-events:none) y no sale con "reducir movimiento". */
(function () {
  var MAX_VECES = 2;
  var PAUSA_MS = 8000;           // mínimo entre una aparición y la siguiente
  var CLAVE = 'rd_personaje_veces';

  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  function veces() {
    try { return parseInt(sessionStorage.getItem(CLAVE) || '0', 10) || 0; } catch (_) { return MAX_VECES; }
  }
  function sumarVez() {
    try { sessionStorage.setItem(CLAVE, String(veces() + 1)); } catch (_) {}
  }
  if (veces() >= MAX_VECES) return;

  var FIGURA =
    '<svg viewBox="0 0 44 70" aria-hidden="true">' +
    '<circle class="rd-pj-cabeza" cx="22" cy="12" r="8"/>' +
    '<line x1="22" y1="20" x2="22" y2="46"/>' +
    '<line class="rd-pj-brazo-i" x1="22" y1="28" x2="10" y2="40"/>' +
    '<line class="rd-pj-brazo-d" x1="22" y1="28" x2="34" y2="40"/>' +
    '<line x1="22" y1="46" x2="13" y2="66"/>' +
    '<line x1="22" y1="46" x2="31" y2="66"/>' +
    '</svg>';

  var TEXTOS = {
    es: { oferta: '¡OFERTA!', destacado: '¡OPORTUNIDAD!', otros: ['¡APROVECHA!', '¡FINANCIA!'] },
    en: { oferta: 'DEAL!', destacado: 'OPPORTUNITY!', otros: ["DON'T MISS IT!", 'FINANCE IT!'] },
    de: { oferta: 'ANGEBOT!', destacado: 'CHANCE!', otros: ['ZUGREIFEN!', 'FINANZIEREN!'] }
  };

  function textoCartel(card) {
    var t = TEXTOS[document.documentElement.lang] || TEXTOS.es;
    if (card.dataset.oferta === '1') return t.oferta;
    if (card.classList.contains('rd-card-featured')) return t.destacado;
    return t.otros[veces() % t.otros.length];
  }

  function crearFigura(conCartel) {
    var fig = document.createElement('div');
    fig.className = 'rd-pj';
    fig.innerHTML = FIGURA + '<div class="rd-pj-polvo"></div>' +
      (conCartel ? '<div class="rd-pj-cartel"></div>' : '');
    return fig;
  }

  // Coloca un elemento en coordenadas de documento sobre la esquina superior
  // derecha de la tarjeta (las tarjetas tienen overflow:hidden, así que el
  // muñeco vive fuera de ellas, en el <body>).
  function colocar(el, card, ancho, alto) {
    var r = card.getBoundingClientRect();
    el.style.left = (r.right + window.scrollX - ancho - 14) + 'px';
    el.style.top = (r.top + window.scrollY - alto) + 'px';
  }

  var ocupado = false;
  var ultimaVez = 0;
  var actual = null;   // { quitar: fn, card: el }
  var usadas = [];

  function quitarActual() {
    if (actual) { actual.quitar(); actual = null; }
  }

  /* 1ª aparición: cae del cielo, aterriza con rebote, levanta el cartel. */
  function caer(card) {
    var fig = crearFigura(true);
    fig.classList.add('rd-pj-cae');
    fig.querySelector('.rd-pj-cartel').textContent = textoCartel(card);
    document.body.appendChild(fig);
    colocar(fig, card, fig.offsetWidth, fig.offsetHeight);
    var timers = [];
    function quitar() {
      timers.forEach(clearTimeout);
      fig.classList.add('rd-pj-fuera');
      setTimeout(function () { fig.remove(); ocupado = false; }, 300);
    }
    requestAnimationFrame(function () { fig.classList.add('rd-pj-cayendo'); });
    timers.push(setTimeout(function () { fig.classList.add('rd-pj-aterriza'); }, 650));
    timers.push(setTimeout(function () { fig.classList.add('rd-pj-cartel-arriba'); }, 850));
    timers.push(setTimeout(function () { fig.classList.add('rd-pj-saluda'); }, 3800));
    timers.push(setTimeout(function () { if (actual && actual.fig === fig) { actual = null; } quitar(); }, 5200));
    return { quitar: quitar, card: card, fig: fig };
  }

  /* 2ª aparición: se asoma por encima del borde de la tarjeta y se esconde. */
  function asomarse(card) {
    var marco = document.createElement('div');
    marco.className = 'rd-pj-marco';
    var fig = crearFigura(true);
    fig.classList.add('rd-pj-asoma');
    fig.querySelector('.rd-pj-cartel').textContent = textoCartel(card);
    marco.appendChild(fig);
    document.body.appendChild(marco);
    colocar(marco, card, marco.offsetWidth, marco.offsetHeight);
    var timers = [];
    function quitar() {
      timers.forEach(clearTimeout);
      fig.classList.remove('rd-pj-arriba', 'rd-pj-cartel-arriba');
      setTimeout(function () { marco.remove(); ocupado = false; }, 450);
    }
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { fig.classList.add('rd-pj-arriba', 'rd-pj-saluda'); });
    });
    timers.push(setTimeout(function () { fig.classList.add('rd-pj-cartel-arriba'); }, 300));
    timers.push(setTimeout(function () { if (actual && actual.fig === fig) { actual = null; } quitar(); }, 3400));
    return { quitar: quitar, card: card, fig: fig };
  }

  function candidata(card) {
    if (usadas.indexOf(card) !== -1) return false;
    if (card.dataset.estado && card.dataset.estado !== 'Disponible') return false;
    if (card.offsetParent === null) return false;   // oculta por un filtro
    return true;
  }
  function preferida(card) {
    return card.dataset.oferta === '1' || card.classList.contains('rd-card-featured');
  }

  function intentar(visibles) {
    if (ocupado || veces() >= MAX_VECES) return;
    if (Date.now() - ultimaVez < PAUSA_MS) return;
    // No antes de que el cliente haya dejado atrás la portada (hero).
    var hero = document.querySelector('.rd-hero');
    if (hero && hero.getBoundingClientRect().bottom > window.innerHeight * 0.35) return;
    var lista = visibles.filter(candidata);
    if (!lista.length) return;
    var hayPreferidas = document.querySelector('#rd-grid .rd-card[data-oferta="1"], .rd-card-featured');
    var elegida = lista.filter(preferida)[0] || (hayPreferidas ? null : lista[0]);
    if (!elegida) return;

    ocupado = true;
    ultimaVez = Date.now();
    usadas.push(elegida);
    var n = veces();
    sumarVez();
    actual = n === 0 ? caer(elegida) : asomarse(elegida);
    if (veces() >= MAX_VECES && observador) {
      // Última aparición: deja de vigilar tarjetas cuando termine.
      setTimeout(function () { observador.disconnect(); }, 4000);
    }
  }

  var enVista = [];
  var observador = null;

  function iniciar() {
    if (!('IntersectionObserver' in window)) return;
    observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (en) {
        var i = enVista.indexOf(en.target);
        if (en.isIntersecting && i === -1) enVista.push(en.target);
        if (!en.isIntersecting && i !== -1) enVista.splice(i, 1);
        // Si la tarjeta del muñeco sale de la vista, se va con ella.
        if (!en.isIntersecting && actual && actual.card === en.target) quitarActual();
      });
      intentar(enVista.slice());
    }, { rootMargin: '-25% 0px -15% 0px', threshold: 0.6 });

    function vigilar() {
      document.querySelectorAll('#rd-grid .rd-card, .rd-card-featured').forEach(function (c) {
        if (!c.dataset.rdPj) { c.dataset.rdPj = '1'; observador.observe(c); }
      });
    }
    vigilar();
    // Los destacados y las ofertas se añaden después (fetch); reintenta un poco más tarde.
    setTimeout(vigilar, 1500);
    setTimeout(vigilar, 4000);
    // Si la última comprobación se quedó en pausa, vuelve a intentarlo al hacer scroll.
    window.addEventListener('scroll', function () {
      if (!ocupado && enVista.length) intentar(enVista.slice());
    }, { passive: true });
    // Ordenar/filtrar mueve las tarjetas: el muñeco se retira.
    var grid = document.getElementById('rd-grid');
    if (grid && window.MutationObserver) {
      new MutationObserver(function () { quitarActual(); }).observe(grid, { childList: true });
    }
    window.addEventListener('resize', quitarActual, { passive: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
