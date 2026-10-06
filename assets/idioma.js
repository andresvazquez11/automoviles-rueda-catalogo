(function() {
  var KEY = 'rd_idioma';

  function idiomaActual() {
    try { var v = localStorage.getItem(KEY); return (v === 'en' || v === 'de') ? v : 'es'; } catch (e) { return 'es'; }
  }

  // Idiomas: es (base), en, de. Si a un texto le falta el alemán (aún no
  // traducido), se muestra en inglés antes que dejarlo en el idioma anterior.
  var IDIOMAS = ['es', 'en', 'de'];
  function leer(el, idioma, sufijo) {
    var texto = el.getAttribute('data-' + idioma + sufijo);
    if (texto === null && idioma === 'de') texto = el.getAttribute('data-en' + sufijo);
    return texto;
  }

  function aplicar(idioma) {
    if (IDIOMAS.indexOf(idioma) === -1) idioma = 'es';
    document.querySelectorAll('.rd-i18n').forEach(function(el) {
      var texto = leer(el, idioma, '');
      if (texto !== null) el.textContent = texto;
    });
    document.querySelectorAll('[data-es-placeholder]').forEach(function(el) {
      var texto = leer(el, idioma, '-placeholder');
      if (texto !== null) el.placeholder = texto;
    });
    document.querySelectorAll('.rd-lang-btn').forEach(function(btn) {
      btn.classList.toggle('activo', btn.dataset.lang === idioma);
    });
    document.documentElement.setAttribute('lang', idioma);
    if (typeof window.rdAlCambiarIdioma === 'function') window.rdAlCambiarIdioma(idioma);
  }

  function cambiar(idioma) {
    try { localStorage.setItem(KEY, idioma); } catch (e) {}
    aplicar(idioma);
  }

  // Expuesto para que otros scripts de la misma página (la franja de
  // destacados, la ficha de coche vía calculadora.js) puedan re-aplicar el
  // idioma actual a contenido que insertan después de la carga inicial.
  window.rdAplicarIdioma = aplicar;
  window.rdIdiomaActual = idiomaActual;
  window.rdCambiarIdioma = cambiar;

  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.rd-lang-btn').forEach(function(btn) {
      btn.addEventListener('click', function() { cambiar(btn.dataset.lang); });
    });
    aplicar(idiomaActual());
  });
})();
