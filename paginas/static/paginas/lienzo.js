/* Recibe la selección y el texto del editor. El lienzo no es un formulario. */
(function () {
  var ORIGEN = window.location.origin;

  function claveValida(clave) {
    return typeof clave === "string" && /^[a-z0-9_-]+$/.test(clave);
  }

  function buscarTodos(clave) {
    if (!claveValida(clave)) return [];
    return document.querySelectorAll('[data-edit-id="' + CSS.escape(clave) + '"]');
  }

  function enlacePermitido(valor) {
    var limpio = String(valor || "").trim();
    var bajo = limpio.toLowerCase();
    if (
      limpio.indexOf("//") === 0 ||
      bajo.indexOf("javascript:") === 0 ||
      bajo.indexOf("data:") === 0 ||
      bajo.indexOf("vbscript:") === 0
    ) {
      return null;
    }
    return limpio;
  }

  function escribir(destino, texto, multilinea) {
    if (!multilinea) {
      destino.textContent = texto;
      return;
    }
    destino.textContent = "";
    texto.split("\n").forEach(function (linea, indice) {
      if (indice) destino.appendChild(document.createElement("br"));
      destino.appendChild(document.createTextNode(linea));
    });
  }

  function quitarSeleccion() {
    document.querySelectorAll(".edit-seleccionado").forEach(function (el) {
      el.classList.remove("edit-seleccionado");
    });
  }

  function previsualizar(data) {
    var src = String(data.src || "");
    if (!/^data:image\/(png|jpeg|gif|webp);base64,/i.test(src)) return;
    Array.prototype.forEach.call(buscarTodos(data.clave), function (el) {
      if (el.getAttribute("data-edit-imagen") === "1") el.src = src;
    });
  }

  function aplicarUno(el, data) {
    var enlace = enlacePermitido(data.enlace);
    if (el.hasAttribute("aria-label")) el.setAttribute("aria-label", data.texto);
    if (el.hasAttribute("data-bs-title")) el.setAttribute("data-bs-title", data.texto);
    if (el.hasAttribute("placeholder")) el.setAttribute("placeholder", data.texto);

    if (el.getAttribute("data-edit-imagen") === "1") {
      el.alt = data.texto == null ? "" : data.texto;
      if (!data.conservarImagen && enlace) el.src = enlace;
      return;
    }
    if (el.matches("input, textarea")) return;

    var destino = el.querySelector("[data-edit-texto]") || el;
    var predeterminado = el.getAttribute("data-edit-predeterminado");
    var plantilla = document.getElementById("rico-" + el.getAttribute("data-edit-rico"));
    if (plantilla && data.texto === predeterminado) {
      destino.replaceChildren(plantilla.content.cloneNode(true));
    } else {
      escribir(destino, data.texto, el.hasAttribute("data-edit-multilinea"));
    }

    if (
      el.getAttribute("data-edit-enlace") === "1" &&
      el.hasAttribute("href") &&
      enlace !== null
    ) {
      el.setAttribute("href", enlace);
    }
  }

  function aplicar(data) {
    Array.prototype.forEach.call(buscarTodos(data.clave), function (el) {
      aplicarUno(el, data);
    });
  }

  function reordenar(orden) {
    var contenedor = document.getElementById("contenido-inicio");
    if (!contenedor || !Array.isArray(orden)) return;
    var vistos = {};
    orden.forEach(function (id) {
      if (!claveValida(id) || vistos[id]) return;
      vistos[id] = true;
      var el = contenedor.querySelector('[data-seccion="' + CSS.escape(id) + '"]');
      if (el) contenedor.appendChild(el);
    });
  }

  function resaltar(clave, desplazar) {
    var nodos = buscarTodos(clave);
    if (!nodos.length) return;
    quitarSeleccion();
    Array.prototype.forEach.call(nodos, function (el) {
      el.classList.add("edit-seleccionado");
    });
    if (!desplazar) return;
    var visible = Array.prototype.filter.call(nodos, function (el) {
      return el.getClientRects().length > 0;
    })[0] || nodos[0];
    visible.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  document.addEventListener(
    "click",
    function (event) {
      if (event.target.closest("a")) event.preventDefault();
      var el = event.target.closest("[data-edit-id]");
      if (!el) return;
      event.preventDefault();
      quitarSeleccion();
      el.classList.add("edit-seleccionado");
      window.parent.postMessage(
        { tipo: "seleccionar", clave: el.getAttribute("data-edit-id") },
        ORIGEN
      );
    },
    true
  );

  document.addEventListener(
    "submit",
    function (event) {
      event.preventDefault();
    },
    true
  );

  window.addEventListener("message", function (event) {
    if (event.origin !== ORIGEN || event.source !== window.parent) return;
    var data = event.data || {};
    if (data.tipo === "actualizar") aplicar(data);
    if (data.tipo === "previsualizar-imagen") previsualizar(data);
    if (data.tipo === "reordenar") reordenar(data.orden);
    if (data.tipo === "vista") {
      document.documentElement.dataset.vista = data.vista === "sesion" ? "sesion" : "visitante";
    }
    if (data.tipo === "resaltar") {
      if (data.vista === "visitante" || data.vista === "sesion") {
        document.documentElement.dataset.vista = data.vista;
      }
      resaltar(data.clave, !!data.desplazar);
    }
    if (data.tipo === "mostrar-grupo" && claveValida(data.grupo)) {
      quitarSeleccion();
      var visibles = Array.prototype.filter.call(
        document.querySelectorAll('[data-edit-grupo="' + CSS.escape(data.grupo) + '"]'),
        function (el) {
          return el.getClientRects().length > 0;
        }
      );
      if (visibles[0]) visibles[0].scrollIntoView({ block: "center", behavior: "smooth" });
    }
  });
})();
