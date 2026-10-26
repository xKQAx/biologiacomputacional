/* Panel izquierdo y lienzo: el clic elige el bloque y el texto se ve al escribir. */
(function () {
  var ORIGEN = window.location.origin;
  var form = document.getElementById("form-portada");
  var marco = document.getElementById("lienzo-inicio");
  var aviso = document.getElementById("aviso-editor");
  var titulo = document.getElementById("titulo-propiedades");
  if (!form || !marco) return;

  var listo = false;
  var editado = form.hasAttribute("data-pendiente");
  var cola = [];
  var seleccion = { tipo: "parte", grupo: grupoInicial(), clave: "" };

  function grupoInicial() {
    var boton = document.querySelector("[data-grupo-btn]");
    return boton ? boton.getAttribute("data-grupo-btn") : "";
  }

  function claveValida(clave) {
    return typeof clave === "string" && /^[a-z0-9_-]+$/.test(clave);
  }

  function fieldset(clave) {
    return form.querySelector('fieldset[data-clave="' + CSS.escape(clave) + '"]');
  }

  function post(mensaje) {
    if (!listo || !marco.contentWindow) {
      cola.push(mensaje);
      return;
    }
    marco.contentWindow.postMessage(mensaje, ORIGEN);
  }

  function mensajeCampo(fs) {
    var enlace = fs.querySelector("[data-campo=enlace]");
    return {
      tipo: "actualizar",
      clave: fs.getAttribute("data-clave"),
      texto: fs.querySelector("[data-campo=texto]").value,
      enlace: enlace ? enlace.value : "",
    };
  }

  function sincronizar() {
    form.querySelectorAll("fieldset[data-clave]").forEach(function (fs) {
      post(mensajeCampo(fs));
    });
  }

  function marcarVista(vista) {
    document.querySelectorAll("[data-vista-btn]").forEach(function (boton) {
      var activa = boton.getAttribute("data-vista-btn") === vista;
      boton.classList.toggle("activa", activa);
      boton.setAttribute("aria-pressed", activa ? "true" : "false");
    });
  }

  function pintar() {
    document.querySelectorAll("[data-grupo-btn]").forEach(function (boton) {
      var activa = boton.getAttribute("data-grupo-btn") === seleccion.grupo;
      boton.classList.toggle("activa", activa);
      if (activa) boton.setAttribute("aria-current", "true");
      else boton.removeAttribute("aria-current");
    });

    form.querySelectorAll("fieldset[data-clave]").forEach(function (fs) {
      var visible =
        seleccion.tipo === "bloque"
          ? fs.getAttribute("data-clave") === seleccion.clave
          : fs.getAttribute("data-grupo") === seleccion.grupo;
      fs.hidden = !visible;
    });

    if (seleccion.tipo === "bloque") {
      var fs = fieldset(seleccion.clave);
      titulo.textContent = fs ? fs.getAttribute("data-etiqueta") : "Propiedades";
    } else {
      var boton = form.querySelector(
        '[data-grupo-btn="' + CSS.escape(seleccion.grupo) + '"]'
      );
      titulo.textContent = boton ? boton.textContent : "Propiedades";
    }
  }

  function elegirParte(grupo) {
    seleccion = { tipo: "parte", grupo: grupo, clave: "" };
    pintar();
    post({ tipo: "mostrar-grupo", grupo: grupo });
  }

  function elegirBloque(clave, desdeLienzo) {
    if (!claveValida(clave)) return;
    var fs = fieldset(clave);
    if (!fs) return;
    var vista = fs.getAttribute("data-vista");
    seleccion = { tipo: "bloque", grupo: fs.getAttribute("data-grupo"), clave: clave };
    if (vista === "visitante" || vista === "sesion") marcarVista(vista);
    pintar();
    post({
      tipo: "resaltar",
      clave: clave,
      vista: vista === "visitante" || vista === "sesion" ? vista : "",
      desplazar: !desdeLienzo,
    });
    if (desdeLienzo) {
      var campo = fs.querySelector("[data-campo=texto]");
      if (campo) campo.focus();
      fs.scrollIntoView({ block: "nearest" });
    }
  }

  document.querySelectorAll("[data-grupo-btn]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      elegirParte(boton.getAttribute("data-grupo-btn"));
    });
  });

  document.querySelectorAll("[data-vista-btn]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      var vista = boton.getAttribute("data-vista-btn");
      marcarVista(vista);
      post({ tipo: "vista", vista: vista });
    });
  });

  form.addEventListener("input", function (event) {
    var fs = event.target.closest("fieldset[data-clave]");
    if (!fs) return;
    editado = true;
    aviso.textContent = "El lienzo ya muestra el cambio. Guarda el borrador para no perderlo.";
    if (listo) post(mensajeCampo(fs));
  });

  form.addEventListener("submit", function (event) {
    var boton = event.submitter;
    if (boton && boton.value === "descartar") {
      if (!window.confirm("¿Descartar el borrador? Lo publicado no cambia.")) {
        event.preventDefault();
      }
    }
  });

  function documentoListo() {
    try {
      var doc = marco.contentDocument;
      return !!(
        doc &&
        doc.readyState === "complete" &&
        doc.URL.indexOf("/admin/pagina/inicio/lienzo/") !== -1
      );
    } catch (error) {
      return false;
    }
  }

  function marcarListo() {
    if (listo) return;
    listo = true;
    if (editado) sincronizar();
    var pendientes = cola.splice(0, cola.length);
    pendientes.forEach(post);
  }

  // El iframe puede haber terminado antes de que este script (defer) escuche.
  marco.addEventListener("load", function () {
    if (documentoListo()) marcarListo();
  });
  if (documentoListo()) marcarListo();

  window.addEventListener("message", function (event) {
    if (event.origin !== ORIGEN || event.source !== marco.contentWindow) return;
    var data = event.data || {};
    if (data.tipo === "seleccionar") elegirBloque(data.clave, true);
  });

  pintar();
})();
