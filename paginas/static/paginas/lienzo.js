/* El clic en el lienzo avisa al editor. El texto, ocultar y mostrar los escribe
   el padre sobre este documento, sin recargar el iframe. */
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

  function textoAtributo(texto) {
    var saneo = window.BiocomSaneo;
    if (!saneo || String(texto || "").indexOf(saneo.PREFIJO) !== 0) {
      return texto == null ? "" : String(texto);
    }
    return saneo.sinMarcas(String(texto).slice(saneo.PREFIJO.length));
  }

  function perfilHtml(el) {
    var perfil = el.getAttribute("data-edit-html");
    if (perfil === "linea" || perfil === "bloque") return perfil;
    return "";
  }

  function esHtmlEnriquecido(el, texto) {
    return (
      !!perfilHtml(el) &&
      window.BiocomSaneo &&
      String(texto || "").indexOf(window.BiocomSaneo.PREFIJO) === 0
    );
  }

  function pintarHtml(destino, texto, perfil) {
    var limpio = window.BiocomSaneo.sanear(
      String(texto).slice(window.BiocomSaneo.PREFIJO.length),
      perfil
    );
    var plantilla = document.createElement("template");
    plantilla.innerHTML = limpio;
    destino.replaceChildren(plantilla.content);
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
    var atributo = textoAtributo(data.texto);
    if (el.hasAttribute("aria-label")) el.setAttribute("aria-label", atributo);
    if (el.hasAttribute("data-bs-title")) el.setAttribute("data-bs-title", atributo);
    if (el.hasAttribute("placeholder")) el.setAttribute("placeholder", atributo);

    if (el.getAttribute("data-edit-imagen") === "1") {
      el.alt = atributo;
      if (!data.conservarImagen && enlace) el.src = enlace;
      return;
    }
    if (el.matches("input, textarea")) return;

    var destino = el.querySelector("[data-edit-texto]") || el;
    var predeterminado = el.getAttribute("data-edit-predeterminado");
    var plantilla = document.getElementById("rico-" + el.getAttribute("data-edit-rico"));
    if (plantilla && data.texto === predeterminado) {
      destino.replaceChildren(plantilla.content.cloneNode(true));
    } else if (esHtmlEnriquecido(el, data.texto)) {
      // El fragmento se arma en el iframe del sitio: no hereda el CSS del admin.
      pintarHtml(destino, data.texto, perfilHtml(el));
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

  function colocarSeccion(data) {
    var contenedor = document.getElementById("contenido-inicio");
    if (!contenedor || !claveValida(data.id)) return;
    var actual = contenedor.querySelector('[data-seccion="' + CSS.escape(data.id) + '"]');
    var html = String(data.html || "").trim();
    if (!html) {
      if (actual) actual.remove();
    } else {
      var plantilla = document.createElement("template");
      plantilla.innerHTML = html;
      var nuevo = plantilla.content.querySelector("[data-seccion]") || plantilla.content.firstElementChild;
      if (!nuevo) return;
      if (actual) actual.replaceWith(nuevo);
      else contenedor.appendChild(nuevo);
    }
    if (Array.isArray(data.orden)) reordenar(data.orden);
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

  function quitarMarcasSeccion() {
    document.querySelectorAll(".seccion-seleccionada, .celda-activa").forEach(function (el) {
      el.classList.remove("seccion-seleccionada", "celda-activa");
    });
  }

  function marcarEdicion(seccion) {
    document.querySelectorAll("[data-seccion]").forEach(function (el) {
      el.classList.toggle("seccion-en-edicion", el === seccion);
    });
    integrarRejilla();
  }

  /* La pieza entra en la celda del dispositivo del botón. Fuera de edición
     vuelve a ser hija directa: el CSS publicado la coloca y no hay guías. */
  function integrarRejilla() {
    var dispositivo = dispositivoActivo();
    document.querySelectorAll(".pieza-mosaico").forEach(function (mosaico) {
      var seccion = mosaico.closest("[data-seccion]");
      var edicion = !!(seccion && seccion.classList.contains("seccion-en-edicion"));
      mosaico.querySelectorAll("[data-elemento]").forEach(function (item) {
        mosaico.appendChild(item);
        item.querySelectorAll("img, a").forEach(function (nodo) {
          nodo.setAttribute("draggable", "false");
        });
      });
      if (!edicion) return;
      mosaico.querySelectorAll(":scope > [data-elemento]").forEach(function (item) {
        var ref = item.getAttribute("data-ref") || "";
        var celda = mosaico.querySelector(
          ':scope > [data-guia="' + dispositivo + '"][data-ocupante="' + ref + '"]'
        );
        if (celda) celda.appendChild(item);
      });
    });
  }

  function elegirCampo(edicion) {
    if (!edicion) return;
    var seccionCampo = edicion.closest("[data-seccion]");
    quitarMarcasSeccion();
    if (seccionCampo) marcarEdicion(seccionCampo);
    var celda = edicion.closest("[data-guia-celda], .pieza-celda");
    if (celda) celda.classList.add("celda-activa");
    quitarSeleccion();
    edicion.classList.add("edit-seleccionado");
    window.parent.postMessage(
      { tipo: "seleccionar", clave: edicion.getAttribute("data-edit-id") },
      ORIGEN
    );
  }

  function seleccionarSeccion(seccion) {
    if (!seccion) return;
    quitarSeleccion();
    quitarMarcasSeccion();
    marcarEdicion(seccion);
    seccion.classList.add("seccion-seleccionada");
    window.parent.postMessage(
      { tipo: "seleccionar-seccion", id: seccion.getAttribute("data-seccion") },
      ORIGEN
    );
  }

  function seleccionarCelda(celda) {
    var seccion = celda.closest("[data-seccion]");
    quitarSeleccion();
    quitarMarcasSeccion();
    if (seccion) marcarEdicion(seccion);
    celda.classList.add("celda-activa");
    window.parent.postMessage(
      {
        tipo: "seleccionar-celda",
        id: seccion ? seccion.getAttribute("data-seccion") : "",
        fila: Number(celda.getAttribute("data-guia-fila")),
        columna: Number(celda.getAttribute("data-guia-columna")),
      },
      ORIGEN
    );
  }

  document.addEventListener(
    "click",
    function (event) {
      if (event.target.closest("a")) event.preventDefault();
      if (event.target.closest("[data-carrusel-anterior], [data-carrusel-siguiente], [data-carrusel-punto]")) {
        return;
      }
      var celda = event.target.closest("[data-guia-celda]");
      if (celda && celda.classList.contains("es-vacia")) {
        event.preventDefault();
        event.stopPropagation();
        seleccionarCelda(celda);
        return;
      }
      var edicion = event.target.closest("[data-edit-id]");
      var ocupada = celda && celda.classList.contains("es-ocupada") ? celda : null;
      var clasica = event.target.closest(".pieza-celda:not(.pieza-celda-vacia)");
      if (!edicion && ocupada) edicion = ocupada.querySelector("[data-edit-id]");
      if (!edicion && clasica) edicion = clasica.querySelector("[data-edit-id]");
      if (edicion) {
        event.preventDefault();
        event.stopPropagation();
        elegirCampo(edicion);
        return;
      }
      var seccion = event.target.closest("[data-seccion]");
      if (!seccion) return;
      event.preventDefault();
      seleccionarSeccion(seccion);
    },
    true
  );

  /* Arrastre sobre el estado del grid. El transform no es la posición guardada. */
  var arrastre = null;
  var arrastreTarjeta = null;
  var cancelado = false;

  function mapaDe(seccion) {
    try {
      return JSON.parse(seccion.getAttribute("data-mapa") || "{}");
    } catch (error) {
      return {};
    }
  }

  function dispositivoActivo() {
    return document.documentElement.dataset.dispositivo || "escritorio";
  }

  function limpiarDestino() {
    document.querySelectorAll(".rejilla-destino, .rejilla-rechazo, .rejilla-arrastrando").forEach(function (nodo) {
      nodo.classList.remove("rejilla-destino", "rejilla-rechazo", "rejilla-arrastrando");
    });
  }

  function ocupa(pos) {
    var celdas = {};
    for (var fila = pos.fila; fila < pos.fila + pos.filas; fila += 1) {
      for (var columna = pos.columna; columna < pos.columna + pos.columnas; columna += 1) {
        celdas[fila + ":" + columna] = true;
      }
    }
    return celdas;
  }

  function cabe(pos, columnas, filas, otras) {
    if (pos.fila < 1 || pos.columna < 1) return false;
    if (pos.fila + pos.filas - 1 > filas || pos.columna + pos.columnas - 1 > columnas) return false;
    var propias = ocupa(pos);
    for (var i = 0; i < otras.length; i += 1) {
      var ajenas = ocupa(otras[i]);
      for (var clave in propias) {
        if (ajenas[clave]) return false;
      }
    }
    return true;
  }

  function evaluar(rejilla, ref, fila, columna) {
    var actual = null;
    (rejilla.posiciones || []).forEach(function (pos) {
      if (pos.id === ref) actual = pos;
    });
    if (!actual) return false;
    var otras = (rejilla.posiciones || []).filter(function (pos) {
      return pos.id !== ref;
    });
    var ocupante = null;
    (rejilla.posiciones || []).forEach(function (pos) {
      if (fila >= pos.fila && fila < pos.fila + pos.filas && columna >= pos.columna && columna < pos.columna + pos.columnas) {
        ocupante = pos;
      }
    });
    if (!ocupante || ocupante.id === ref) {
      return cabe(
        { fila: fila, columna: columna, filas: actual.filas, columnas: actual.columnas },
        rejilla.columnas,
        rejilla.filas,
        otras
      );
    }
    var movida = { fila: ocupante.fila, columna: ocupante.columna, filas: actual.filas, columnas: actual.columnas };
    var otra = { fila: actual.fila, columna: actual.columna, filas: ocupante.filas, columnas: ocupante.columnas };
    var resto = otras.filter(function (pos) {
      return pos.id !== ocupante.id;
    });
    return cabe(movida, rejilla.columnas, rejilla.filas, resto.concat([otra])) &&
      cabe(otra, rejilla.columnas, rejilla.filas, resto.concat([movida]));
  }

  function celdaBajo(event) {
    var nodo = event.target && event.target.closest ? event.target.closest("[data-guia-celda]") : null;
    if (nodo) return nodo;
    if (!event.clientX && event.clientX !== 0) return null;
    var bajo = document.elementFromPoint(event.clientX, event.clientY);
    return bajo && bajo.closest ? bajo.closest("[data-guia-celda]") : null;
  }

  function apuntar(celda) {
    if (!arrastre) return;
    if (
      !celda ||
      celda.closest("[data-seccion]") !== arrastre.seccion ||
      celda.getAttribute("data-guia") !== dispositivoActivo()
    ) {
      limpiarDestino();
      if (arrastre.origen) arrastre.origen.classList.add("rejilla-arrastrando");
      arrastre.valida = false;
      return;
    }
    var fila = Number(celda.getAttribute("data-guia-fila"));
    var columna = Number(celda.getAttribute("data-guia-columna"));
    if (!fila || !columna) {
      arrastre.valida = false;
      return;
    }
    var valida = evaluar(
      mapaDe(arrastre.seccion)[dispositivoActivo()] || {},
      arrastre.ref,
      fila,
      columna
    );
    limpiarDestino();
    arrastre.origen.classList.add("rejilla-arrastrando");
    celda.classList.add(valida ? "rejilla-destino" : "rejilla-rechazo");
    arrastre.fila = fila;
    arrastre.columna = columna;
    arrastre.valida = valida;
    arrastre.misma = celda.getAttribute("data-ocupante") === arrastre.ref;
  }

  document.addEventListener("dragstart", function (event) {
    var asaTarjeta = event.target.closest("[data-arrastrar-tarjeta]");
    if (asaTarjeta) {
      var tarjeta = asaTarjeta.closest("[data-layout-tarjeta]");
      var seccionTarjetas = asaTarjeta.closest(".seccion-en-edicion[data-seccion='encontrar']");
      if (!tarjeta || !seccionTarjetas) {
        event.preventDefault();
        return;
      }
      arrastreTarjeta = {
        item: tarjeta,
        seccion: seccionTarjetas,
        ordenOriginal: Array.prototype.map.call(
          seccionTarjetas.querySelectorAll("[data-layout-tarjeta]"),
          function (item) { return item.getAttribute("data-layout-tarjeta"); }
        ),
      };
      tarjeta.classList.add("tarjeta-arrastrando");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", tarjeta.getAttribute("data-layout-tarjeta") || "");
      }
      return;
    }
    var origen = event.target.closest("[data-elemento]");
    if (!origen) return;
    if (
      event.target.closest(
        "[data-carrusel-anterior], [data-carrusel-siguiente], [data-carrusel-punto], input, textarea, select, [contenteditable='true']"
      )
    ) {
      event.preventDefault();
      return;
    }
    var seccion = origen.closest(".seccion-en-edicion");
    if (!seccion) {
      event.preventDefault();
      return;
    }
    cancelado = false;
    arrastre = {
      ref: origen.getAttribute("data-ref"),
      seccion: seccion,
      origen: origen,
      nombre: origen.getAttribute("data-nombre") || "Pieza",
      valida: false,
    };
    origen.classList.add("rejilla-arrastrando");
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", arrastre.ref || "");
    }
  });

  document.addEventListener("dragover", function (event) {
    if (!arrastreTarjeta) return;
    var destino = event.target.closest("[data-layout-tarjeta]");
    if (!destino || destino === arrastreTarjeta.item || destino.parentElement !== arrastreTarjeta.item.parentElement) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
    var caja = destino.getBoundingClientRect();
    var mitadY = caja.top + caja.height / 2;
    var despues = event.clientY > mitadY || (event.clientY >= caja.top && event.clientY <= caja.bottom && event.clientX > caja.left + caja.width / 2);
    destino.parentElement.insertBefore(arrastreTarjeta.item, despues ? destino.nextSibling : destino);
  });

  document.addEventListener("drop", function (event) {
    if (!arrastreTarjeta) return;
    event.preventDefault();
    var datos = arrastreTarjeta;
    arrastreTarjeta = null;
    datos.item.classList.remove("tarjeta-arrastrando");
    var orden = Array.prototype.map.call(
      datos.seccion.querySelectorAll("[data-layout-tarjeta]"),
      function (item) { return item.getAttribute("data-layout-tarjeta"); }
    );
    if (orden.every(function (id, indice) { return id === datos.ordenOriginal[indice]; })) return;
    window.parent.postMessage({ tipo: "orden-tarjetas", grupo: "encontrar", orden: orden }, ORIGEN);
  });

  document.addEventListener("dragend", function () {
    if (!arrastreTarjeta) return;
    arrastreTarjeta.item.classList.remove("tarjeta-arrastrando");
    arrastreTarjeta = null;
  });

  document.addEventListener("dragenter", function (event) {
    if (!arrastre || cancelado) return;
    event.preventDefault();
  });

  document.addEventListener("dragover", function (event) {
    if (!arrastre || cancelado) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
    apuntar(celdaBajo(event));
  });

  document.addEventListener("drop", function (event) {
    if (!arrastre) return;
    event.preventDefault();
    apuntar(celdaBajo(event));
    var datos = arrastre;
    arrastre = null;
    limpiarDestino();
    if (cancelado || !datos.valida || datos.misma) return;
    window.parent.postMessage(
      {
        tipo: "rejilla-soltar",
        id: datos.seccion.getAttribute("data-seccion"),
        ref: datos.ref,
        fila: datos.fila,
        columna: datos.columna,
      },
      ORIGEN
    );
  });

  document.addEventListener("dragend", function () {
    arrastre = null;
    cancelado = false;
    limpiarDestino();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape" || !arrastre) return;
    cancelado = true;
    limpiarDestino();
  });

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
    if (data.tipo === "seccion") colocarSeccion(data);
    if (data.tipo === "vista") {
      document.documentElement.dataset.vista = data.vista === "sesion" ? "sesion" : "visitante";
    }
    if (data.tipo === "resaltar") {
      if (data.vista === "visitante" || data.vista === "sesion") {
        document.documentElement.dataset.vista = data.vista;
      }
      resaltar(data.clave, !!data.desplazar);
    }
    if (data.tipo === "dispositivo") {
      var dispositivo = data.dispositivo;
      if (dispositivo !== "tablet" && dispositivo !== "movil") dispositivo = "escritorio";
      document.documentElement.dataset.dispositivo = dispositivo;
      integrarRejilla();
    }
    if (data.tipo === "seccion-activa" && claveValida(data.id)) {
      var activa = document.querySelector('[data-seccion="' + CSS.escape(data.id) + '"]');
      if (activa) marcarEdicion(activa);
      else integrarRejilla();
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

  window.BiocomLienzo = { integrar: integrarRejilla };
})();
