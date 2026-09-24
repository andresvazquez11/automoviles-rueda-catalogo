// ── Rebajas: cartel "X € DESCUENTO" + "Antes: X €" tachado ─────────────
// Dos orígenes, el manual tiene prioridad:
//   1) Manual: /rebajas.json ({ "<id estable>": { "descuento": 1500 } }),
//      que se edita desde /admin/ y se aplica al momento, sin regenerar la web.
//      "Antes" = precio actual + descuento.
//   2) Automático: bajada REAL detectada en el historial de precios
//      (data-antes-auto en las tarjetas / COCHE.antes_auto en la ficha),
//      calculada por generar_web.py → precio_antes_auto().
// Solo se muestra en coches Disponibles.
(function() {
  var manuales = {};

  function en() { return !!(window.rdIdiomaActual && window.rdIdiomaActual() === 'en'); }
  function eur(n) { return Math.round(n).toLocaleString('es-ES', { useGrouping: true }).replace(/,/g, '.') + ' €'; }
  function eurEn(n) { return '€' + Math.round(n).toLocaleString('en-GB'); }
  function precioNum(txt) { return parseInt(String(txt).replace(/[^\d]/g, ''), 10) || 0; }

  function antesDe(id, precio, antesAuto) {
    var m = manuales[id];
    if (m && m.descuento > 0) return precio + m.descuento;
    return antesAuto > precio ? antesAuto : 0;
  }

  function badgeHTML(dif) {
    return en() ? eurEn(dif) + ' OFF' : eur(dif) + ' DESCUENTO';
  }
  function antesHTML(antes) {
    return (en() ? 'Before: ' : 'Antes: ') + '<s>' + (en() ? eurEn(antes) : eur(antes)) + '</s>';
  }

  function aplicarTarjetas() {
    document.querySelectorAll('.rd-card[data-id]').forEach(function(card) {
      card.querySelectorAll('.rd-rebaja-badge, .rd-rebaja-antes').forEach(function(el) { el.remove(); });
      delete card.dataset.oferta;
      if (card.dataset.estado !== 'Disponible') return;
      var precio = parseInt(card.dataset.precio, 10) || 0;
      var antes = antesDe(card.dataset.id, precio, parseInt(card.dataset.antesAuto, 10) || 0);
      if (!antes || antes <= precio) return;
      card.dataset.oferta = '1';
      var badge = document.createElement('span');
      badge.className = 'rd-rebaja-badge';
      badge.textContent = badgeHTML(antes - precio);
      card.querySelector('.rd-card-media').appendChild(badge);
      var old = document.createElement('div');
      old.className = 'rd-rebaja-antes';
      old.innerHTML = antesHTML(antes);
      var p = card.querySelector('.rd-card-precio');
      p.parentNode.insertBefore(old, p);
    });
  }

  function aplicarFicha() {
    if (typeof COCHE === 'undefined' || !COCHE.id) return;
    document.querySelectorAll('.rd-rebaja-badge, .rd-rebaja-antes, .rd-oferta-pill').forEach(function(el) { el.remove(); });
    if (COCHE.estado !== 'Disponible' || COCHE.vendido) return;
    var precio = precioNum(COCHE.precio);
    var antes = antesDe(COCHE.id, precio, COCHE.antes_auto || 0);
    if (!antes || antes <= precio) return;
    var frame = document.querySelector('.rd-gallery-frame');
    if (frame) {
      var badge = document.createElement('span');
      badge.className = 'rd-rebaja-badge';
      badge.textContent = badgeHTML(antes - precio);
      frame.appendChild(badge);
      // "🔥 OFERTA" debajo del descuento, mismo naranja que el filtro Ofertas
      var pill = document.createElement('span');
      pill.className = 'rd-oferta-pill';
      pill.textContent = en() ? '🔥 DEAL' : '🔥 OFERTA';
      frame.appendChild(pill);
    }
    var p = document.getElementById('m-precio');
    if (p) {
      var old = document.createElement('div');
      old.className = 'rd-rebaja-antes';
      old.innerHTML = antesHTML(antes);
      p.parentNode.insertBefore(old, p);
    }
  }

  // Botón "🔥 Ofertas" de los filtros: contador y visible solo si hay alguna
  function actualizarFiltroOfertas() {
    var btn = document.querySelector('.rd-filter-oferta');
    if (!btn) return;
    var n = document.querySelectorAll('#rd-grid .rd-card[data-oferta="1"]').length;
    document.getElementById('rd-cnt-oferta').textContent = n;
    btn.hidden = !n;
    if (!n && btn.classList.contains('activo')) {
      var todos = document.querySelector('.rd-filter-btn[data-filter="todos"]');
      if (todos) todos.click();
    }
    if (window.rdAplicarFiltros) window.rdAplicarFiltros();
  }

  function aplicar() { aplicarTarjetas(); aplicarFicha(); actualizarFiltroOfertas(); }
  window.rdAplicarRebajas = aplicar;

  // Al cambiar de idioma la ficha se vuelve a pintar → re-aplicar encima.
  var previo = window.rdAlCambiarIdioma;
  window.rdAlCambiarIdioma = function() {
    if (typeof previo === 'function') previo.apply(this, arguments);
    aplicar();
  };

  aplicar(); // bajadas automáticas, sin esperar a la red
  fetch('/rebajas.json', { cache: 'no-store' })
    .then(function(r) { return r.ok ? r.json() : {}; })
    .catch(function() { return {}; })
    .then(function(data) { manuales = data || {}; aplicar(); });
})();
