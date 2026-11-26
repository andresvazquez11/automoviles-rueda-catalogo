// Solo asesor: comparar este coche de ocasión con un nuevo parecido (desplegable bajo la financiación).
// La comparación la calcula la página privada «Vehículos nuevos» (/nuevos/), cifrada con contraseña;
// aquí solo se le pasa el coche por el enlace y se muestra su resumen dentro de un marco.
(function () {
  var det = document.getElementById('rd-nuevo-cmp');
  if (!det || typeof COCHE === 'undefined') return;
  var marco = document.getElementById('rd-nuevo-if');
  function b64(o) { return btoa(unescape(encodeURIComponent(JSON.stringify(o)))).replace(/\+/g, '-').replace(/\//g, '_'); }
  var c = { n: COCHE.n, modelo: COCHE.modelo, version: COCHE.version, combustible: COCHE.combustible,
            cambio: COCHE.cambio, km: COCHE.km, fecha: COCHE.fecha, precio: COCHE.precio, color: COCHE.color,
            precio_fin: COCHE.precio_fin, tin: COCHE.tin_fin };
  var base = '/nuevos/#oc=' + b64(c);
  var full = document.getElementById('rd-nuevo-full');
  if (full) full.href = base;
  // el marco carga solo al abrir el desplegable; con «Recordar en este dispositivo» no pide contraseña
  det.addEventListener('toggle', function () {
    if (!det.open || marco.getAttribute('src')) return;
    // espera (hasta 3 s) a los datos de gestión: el ORIGEN del coche (Demo, REMA, Buy Back…) decide qué campaña de VWFS le toca
    Promise.race([window.RD_GESTION_LISTO || Promise.resolve(null), new Promise(function (r) { setTimeout(function () { r(null); }, 3000); })]).then(function (rec) {
      if (rec && rec.origen) c.origen = rec.origen;
      marco.setAttribute('src', '/nuevos/#oc=' + b64(c) + '&mini=1');
    });
  });
  // la página de nuevos avisa de su altura para que el marco no tenga barra de desplazamiento
  window.addEventListener('message', function (e) {
    if (e.origin !== location.origin || !e.data || !e.data.rdNuevoAlto) return;
    marco.style.height = Math.min(900, e.data.rdNuevoAlto + 6) + 'px';
  });
})();
