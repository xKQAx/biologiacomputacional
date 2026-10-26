/* Recibe la selección y el texto del editor. El lienzo no es un formulario. */
(function () {
  var ORIGEN = window.location.origin;

  function claveValida(clave) {
    return typeof clave === "string" && /^[a-z0-9_-]+$/.test(clave);
  }

  function buscar(clave) {
    if (!claveValida(clave)) return null;
    return document.querySelector('[data-edit-id="' + CSS.escape(clave) + '"]');
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

  function aplicar(data) {
    var el = buscar(data.clave);
    if (!el) return;
    var enlace = enlacePermitido(data.enlace);

    if (el.getAttribute("data-edit-imagen") === "1") {
      el.alt = data.texto;
      if (enlace) el.src = enlace;
      return;
    }

    var destino = el.querySelector("[data-edit-texto]") || el;
    var predeterminado = el.getAttribute("data-edit-predeterminado");
    var plantilla = document.getElementById("rico-" + el.getAttribute("data-edit-rico"));
    if (plantilla && data.texto === predeterminado) {
      destino.replaceChildren(plantilla.content.cloneNode(true));
    } else {
      escribir(destino, data.texto, el.hasAttribute("data-edit-multilinea"));
    }

    if (el.hasAttribute("href") && enlace !== null) el.setAttribute("href", enlace);
  }

  function resaltar(clave, desplazar) {
    var el = buscar(clave);
    if (!el) return;
    quitarSeleccion();
    el.classList.add("edit-seleccionado");
    if (desplazar) el.scrollIntoView({ block: "center", behavior: "smooth" });
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
