/* Panel izquierdo y lienzo: el clic elige el bloque, el texto se ve al escribir y el orden se mueve al instante. */
(function () {
  var ORIGEN = window.location.origin;
  var form = document.getElementById("form-portada");
  var marco = document.getElementById("lienzo");
  var aviso = document.getElementById("aviso-editor");
  var titulo = document.getElementById("titulo-propiedades");
  if (!form || !marco) return;

  var TIPOS_IMAGEN = { "image/jpeg": 1, "image/png": 1, "image/gif": 1, "image/webp": 1 };
  var MAX_IMAGEN = Number(form.getAttribute("data-max-imagen")) || 2 * 1024 * 1024;
  var guardado = leerGuardado();
  var listo = false;
  var editado = form.hasAttribute("data-pendiente");
  var enviando = false;
  var cola = [];
  var seleccion = { tipo: "parte", grupo: grupoInicial(), clave: "", pieza: "" };

  function leerGuardado() {
    var nodo = document.getElementById("estado-guardado");
    if (!nodo) return { textos: {}, enlaces: {}, orden: "" };
    try {
      var datos = JSON.parse(nodo.textContent);
      datos.textos = datos.textos || {};
      datos.enlaces = datos.enlaces || {};
      datos.orden = datos.orden || "";
      datos.nombres = datos.nombres || {};
      return datos;
    } catch (error) {
      return { textos: {}, enlaces: {}, orden: "", nombres: {} };
    }
  }

  function grupoInicial() {
    var boton = document.querySelector("[data-grupo-btn][aria-current='true']");
    if (!boton) boton = document.querySelector("[data-grupo-btn]");
    return boton ? boton.getAttribute("data-grupo-btn") : "";
  }

  function claveValida(clave) {
    return typeof clave === "string" && /^[a-z0-9_-]+$/.test(clave);
  }

  function fieldset(clave) {
    return form.querySelector('fieldset[data-clave="' + CSS.escape(clave) + '"]');
  }

  function campoVisible(fs) {
    return fs.querySelector("[data-campo=texto-rico]") || fs.querySelector("[data-campo=texto]");
  }

  function perfilDe(nodo) {
    var caja = nodo.closest ? nodo.closest("[data-formato]") : null;
    return caja && caja.getAttribute("data-formato") === "linea" ? "linea" : "bloque";
  }

  function escribirValor(caja) {
    if (!window.BiocomSaneo) return;
    var campo = caja.querySelector("[data-campo=texto-rico]");
    var oculto = caja.querySelector("[data-campo=texto]");
    if (!campo || !oculto) return;
    oculto.value = window.BiocomSaneo.valorDesdeDom(campo, caja.getAttribute("data-formato"));
  }

  function pintarCampo(campo, valor) {
    var saneo = window.BiocomSaneo;
    var perfil = perfilDe(campo);
    campo.replaceChildren();
    if (saneo && String(valor || "").indexOf(saneo.PREFIJO) === 0) {
      var plantilla = document.createElement("template");
      plantilla.innerHTML = saneo.sanear(String(valor).slice(saneo.PREFIJO.length), perfil);
      campo.appendChild(plantilla.content);
      return;
    }
    String(valor || "").split("\n").forEach(function (linea, indice) {
      if (indice) campo.appendChild(document.createElement("br"));
      campo.appendChild(document.createTextNode(linea));
    });
  }

  function publicarCampo(campo) {
    var caja = campo.closest("[data-formato]");
    var fs = campo.closest("fieldset[data-clave]");
    if (caja) escribirValor(caja);
    editado = true;
    refrescarAvisoPendiente();
    if (fs) post(mensajeCampo(fs));
  }

  function aplicarEnlace() {
    var escrito = window.prompt(
      "Dirección del enlace. Solo http, https o mailto. Déjala vacía para quitarlo.",
      "https://"
    );
    if (escrito === null || !window.BiocomSaneo) return;
    if (!String(escrito).trim()) {
      document.execCommand("unlink");
      return;
    }
    var href = window.BiocomSaneo.hrefSeguro(escrito);
    if (!href) {
      window.alert("Ese enlace no se puede usar. Escribe uno que empiece por http://, https:// o mailto:.");
      return;
    }
    document.execCommand("createLink", false, href);
  }

  function quitarFormato(campo, perfil) {
    document.execCommand("removeFormat");
    document.execCommand("unlink");
    if (perfil === "bloque") {
      Array.prototype.slice.call(campo.querySelectorAll("li")).reverse().forEach(function (li) {
        var parrafo = document.createElement("p");
        while (li.firstChild) parrafo.appendChild(li.firstChild);
        li.replaceWith(parrafo);
      });
      campo.querySelectorAll("ul, ol").forEach(function (lista) {
        var padre = lista.parentNode;
        while (lista.firstChild) padre.insertBefore(lista.firstChild, lista);
        lista.remove();
      });
    }
    if (window.BiocomSaneo) campo.innerHTML = window.BiocomSaneo.sanear(campo.innerHTML, perfil);
  }

  function refrescarBarra(campo) {
    var caja = campo.closest("[data-formato]");
    if (!caja) return;
    var mapa = {
      strong: "bold",
      em: "italic",
      u: "underline",
      ul: "insertUnorderedList",
      ol: "insertOrderedList",
    };
    caja.querySelectorAll("[data-fmt]").forEach(function (boton) {
      var comando = mapa[boton.getAttribute("data-fmt")];
      if (!comando) return;
      var activo = false;
      try {
        activo = document.queryCommandState(comando);
      } catch (error) {
        activo = false;
      }
      boton.classList.toggle("activa", activo);
      boton.setAttribute("aria-pressed", activo ? "true" : "false");
    });
  }

  function aplicarFormato(campo, fmt) {
    var perfil = perfilDe(campo);
    /* Estrategia del perfil: en un título el botón de lista no hace nada. */
    if ((fmt === "ul" || fmt === "ol") && perfil !== "bloque") return;
    campo.focus();
    try {
      document.execCommand("styleWithCSS", false, false);
    } catch (error) {
      /* El navegador sigue el comando aunque no acepte este ajuste. */
    }
    if (fmt === "strong") document.execCommand("bold");
    else if (fmt === "em") document.execCommand("italic");
    else if (fmt === "u") document.execCommand("underline");
    else if (fmt === "ul") document.execCommand("insertUnorderedList");
    else if (fmt === "ol") document.execCommand("insertOrderedList");
    else if (fmt === "enlace") aplicarEnlace();
    else if (fmt === "limpiar") quitarFormato(campo, perfil);
    publicarCampo(campo);
    refrescarBarra(campo);
  }

  /* El lienzo es el documento del iframe. No hace falta recargarlo ni esperar postMessage. */
  function documentoLienzo() {
    try {
      var doc = marco.contentDocument;
      if (!doc || doc.readyState === "loading") return null;
      if (doc.getElementById("contenido-inicio") || doc.querySelector("[data-edit-id]")) return doc;
    } catch (error) {
      return null;
    }
    return null;
  }

  function post(mensaje) {
    if (!mensaje) return;
    var doc = documentoLienzo();
    if (!doc) {
      cola.push(mensaje);
      return;
    }
    try {
      aplicarMensaje(doc, mensaje);
    } catch (error) {
      /* Un campo mal formado no debe cortar el resto del lienzo. */
    }
  }

  function buscarEnLienzo(doc, clave) {
    if (!claveValida(clave)) return [];
    return doc.querySelectorAll('[data-edit-id="' + CSS.escape(clave) + '"]');
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

  function pintarHtml(doc, destino, texto, perfil) {
    var limpio = window.BiocomSaneo.sanear(
      String(texto).slice(window.BiocomSaneo.PREFIJO.length),
      perfil
    );
    var plantilla = doc.createElement("template");
    plantilla.innerHTML = limpio;
    destino.replaceChildren(plantilla.content);
  }

  function escribirEn(doc, destino, texto, multilinea) {
    if (!multilinea) {
      destino.textContent = texto;
      return;
    }
    destino.textContent = "";
    String(texto || "").split("\n").forEach(function (linea, indice) {
      if (indice) destino.appendChild(doc.createElement("br"));
      destino.appendChild(doc.createTextNode(linea));
    });
  }

  function aplicarUno(doc, el, data) {
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
    var plantilla = doc.getElementById("rico-" + el.getAttribute("data-edit-rico"));
    if (plantilla && data.texto === predeterminado) {
      destino.replaceChildren(plantilla.content.cloneNode(true));
    } else if (esHtmlEnriquecido(el, data.texto)) {
      pintarHtml(doc, destino, data.texto, perfilHtml(el));
    } else {
      escribirEn(doc, destino, data.texto, el.hasAttribute("data-edit-multilinea"));
    }
    if (
      el.getAttribute("data-edit-enlace") === "1" &&
      el.hasAttribute("href") &&
      enlace !== null
    ) {
      el.setAttribute("href", enlace);
    }
  }

  function reordenarLienzo(doc, orden) {
    var contenedor = doc.getElementById("contenido-inicio");
    if (!contenedor || !Array.isArray(orden)) return;
    var vistos = {};
    orden.forEach(function (id) {
      if (!claveValida(id) || vistos[id]) return;
      vistos[id] = true;
      var el = contenedor.querySelector('[data-seccion="' + CSS.escape(id) + '"]');
      if (el) contenedor.appendChild(el);
    });
  }

  /* Escribe la sección en el documento del iframe. El nombre no puede repetirse:
     la que mueve la lista del índice la pisaba y el lienzo no se enteraba. */
  function colocarSeccion(doc, data) {
    var contenedor = doc.getElementById("contenido-inicio");
    if (!contenedor || !claveValida(data.id)) return;
    var win = doc.defaultView;
    var x = win ? win.scrollX : 0;
    var y = win ? win.scrollY : 0;
    var actual = contenedor.querySelector('[data-seccion="' + CSS.escape(data.id) + '"]');
    var html = String(data.html || "").trim();
    var nuevo = null;
    if (!html) {
      if (actual) actual.remove();
    } else {
      var plantilla = doc.createElement("template");
      plantilla.innerHTML = html;
      nuevo = plantilla.content.querySelector("[data-seccion]") || plantilla.content.firstElementChild;
      if (!nuevo) return;
      if (actual) actual.replaceWith(nuevo);
      else contenedor.appendChild(nuevo);
    }
    if (Array.isArray(data.orden)) reordenarLienzo(doc, data.orden);
    if (!actual && nuevo && nuevo.scrollIntoView) {
      nuevo.scrollIntoView({ block: "center" });
      return;
    }
    if (win) win.scrollTo(x, y);
  }

  function aplicarMensaje(doc, data) {
    if (!data || !data.tipo) return;
    if (data.tipo === "actualizar") {
      Array.prototype.forEach.call(buscarEnLienzo(doc, data.clave), function (el) {
        aplicarUno(doc, el, data);
      });
      return;
    }
    if (data.tipo === "previsualizar-imagen") {
      var src = String(data.src || "");
      if (!/^data:image\/(png|jpeg|gif|webp);base64,/i.test(src)) return;
      Array.prototype.forEach.call(buscarEnLienzo(doc, data.clave), function (el) {
        if (el.getAttribute("data-edit-imagen") === "1") el.src = src;
      });
      return;
    }
    if (data.tipo === "reordenar") {
      var win = doc.defaultView;
      var x = win ? win.scrollX : 0;
      var y = win ? win.scrollY : 0;
      reordenarLienzo(doc, data.orden);
      if (win) win.scrollTo(x, y);
      return;
    }
    if (data.tipo === "seccion") {
      colocarSeccion(doc, data);
      return;
    }
    if (data.tipo === "vista") {
      doc.documentElement.dataset.vista = data.vista === "sesion" ? "sesion" : "visitante";
      return;
    }
    if (data.tipo === "resaltar") {
      if (data.vista === "visitante" || data.vista === "sesion") {
        doc.documentElement.dataset.vista = data.vista;
      }
      var nodos = buscarEnLienzo(doc, data.clave);
      if (!nodos.length) return;
      doc.querySelectorAll(".edit-seleccionado").forEach(function (el) {
        el.classList.remove("edit-seleccionado");
      });
      Array.prototype.forEach.call(nodos, function (el) {
        el.classList.add("edit-seleccionado");
      });
      if (!data.desplazar) return;
      var visible = Array.prototype.filter.call(nodos, function (el) {
        return el.getClientRects().length > 0;
      })[0] || nodos[0];
      visible.scrollIntoView({ block: "center", behavior: "smooth" });
      return;
    }
    if (data.tipo === "mostrar-grupo" && claveValida(data.grupo)) {
      doc.querySelectorAll(".edit-seleccionado").forEach(function (el) {
        el.classList.remove("edit-seleccionado");
      });
      var visibles = Array.prototype.filter.call(
        doc.querySelectorAll('[data-edit-grupo="' + CSS.escape(data.grupo) + '"]'),
        function (el) {
          return el.getClientRects().length > 0;
        }
      );
      if (visibles[0]) visibles[0].scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }

  function mensajeCampo(fs) {
    var texto = fs.querySelector("[data-campo=texto]");
    if (!texto) return null;
    var enlace = fs.querySelector("[data-campo=enlace]");
    var imagen = fs.querySelector("[data-campo=imagen]");
    var hayArchivo = !!(imagen && imagen.files && imagen.files.length);
    return {
      tipo: "actualizar",
      clave: fs.getAttribute("data-clave"),
      texto: texto.value,
      enlace: hayArchivo ? "" : enlace ? enlace.value : "",
      conservarImagen: hayArchivo,
    };
  }

  function hayCambios() {
    var distinto = false;
    form.querySelectorAll("fieldset[data-clave]").forEach(function (fs) {
      var clave = fs.getAttribute("data-clave");
      var texto = fs.querySelector("[data-campo=texto]");
      var enlace = fs.querySelector("[data-campo=enlace]");
      var imagen = fs.querySelector("[data-campo=imagen]");
      if (texto && texto.value !== (guardado.textos[clave] || "")) distinto = true;
      if (enlace && enlace.value !== (guardado.enlaces[clave] || "")) distinto = true;
      if (imagen && imagen.files && imagen.files.length) distinto = true;
    });
    var orden = document.getElementById("orden-secciones");
    if (orden && orden.value !== guardado.orden) distinto = true;
    form.querySelectorAll("[data-nombre-seccion]").forEach(function (campo) {
      var id = campo.getAttribute("data-nombre-seccion");
      if (campo.value.trim() !== (guardado.nombres[id] || "")) distinto = true;
    });
    return distinto;
  }

  function refrescarAvisoPendiente() {
    if (!aviso) return;
    var pendiente = hayCambios();
    aviso.hidden = !pendiente;
    aviso.textContent = pendiente
      ? "Hay cambios sin guardar. Guarda el borrador para no perderlos."
      : "";
  }

  function ordenActual() {
    return Array.prototype.map.call(
      document.querySelectorAll("[data-seccion-item]"),
      function (item) {
        return item.getAttribute("data-seccion-item");
      }
    );
  }

  function enviarOrden() {
    var orden = ordenActual();
    if (orden.length) post({ tipo: "reordenar", orden: orden });
  }

  function sincronizar() {
    form.querySelectorAll("fieldset[data-clave]").forEach(function (fs) {
      post(mensajeCampo(fs));
    });
    enviarOrden();
  }

  function comprometerOrden() {
    var campo = document.getElementById("orden-secciones");
    var siguiente = ordenActual().join(",");
    if (campo && campo.value === siguiente) {
      enviarOrden();
      return;
    }
    if (campo) campo.value = siguiente;
    editado = true;
    refrescarAvisoPendiente();
    enviarOrden();
  }

  function moverSeccion(id, delta) {
    var lista = document.getElementById("lista-secciones");
    if (!lista || !claveValida(id)) return;
    var items = Array.prototype.slice.call(lista.querySelectorAll("[data-seccion-item]"));
    var index = -1;
    items.forEach(function (item, indice) {
      if (item.getAttribute("data-seccion-item") === id) index = indice;
    });
    var destino = index + delta;
    if (index < 0 || destino < 0 || destino >= items.length) return;
    var nodo = items[index];
    if (delta < 0) lista.insertBefore(nodo, items[destino]);
    else lista.insertBefore(items[destino], nodo);
    comprometerOrden();
  }

  /* Un solo camino para el orden: el arrastre y las flechas del asa lo usan.
     No se llama colocarSeccion: ese nombre escribe la sección en el iframe. */
  function ubicarEnLista(id, destino, despues) {
    var lista = document.getElementById("lista-secciones");
    if (!lista || !destino) return;
    var nodo = lista.querySelector('[data-seccion-item="' + CSS.escape(id) + '"]');
    if (!nodo || nodo === destino) return;
    var referencia = despues ? destino.nextElementSibling : destino;
    if (referencia === nodo) return;
    if (referencia) lista.insertBefore(nodo, referencia);
    else lista.appendChild(nodo);
    comprometerOrden();
  }

  function limpiarHuecos(lista) {
    lista.querySelectorAll(".hueco-antes, .hueco-despues, .arrastrando").forEach(function (nodo) {
      nodo.classList.remove("hueco-antes", "hueco-despues", "arrastrando");
    });
  }

  function etiquetaGrupo(nodo) {
    if (!nodo) return "Propiedades";
    if (nodo.matches("input, textarea")) {
      return nodo.value.trim() || nodo.getAttribute("placeholder") || "Sección";
    }
    return (nodo.textContent || "").trim() || "Propiedades";
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

    /* Índice e inspector: la lista solo elige; aquí se ve una sección. */
    form.querySelectorAll("[data-inspector]").forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-inspector") !== seleccion.grupo;
    });

    if (titulo) titulo.textContent = "Editando: " + nombreEnEdicion();
    pintarPiezas();
  }

  function nombreEnEdicion() {
    if (seleccion.pieza) {
      var piezaBtn = form.querySelector(
        '[data-inspector="' + CSS.escape(seleccion.grupo) + '"] [data-pieza-btn][data-pieza="' +
          CSS.escape(seleccion.pieza) + '"]'
      );
      if (piezaBtn) return (piezaBtn.textContent || "").trim();
    }
    var control = form.querySelector(
      '[data-grupo-btn="' + CSS.escape(seleccion.grupo) + '"]'
    );
    return etiquetaGrupo(control);
  }

  /* En una sección agregada, la pieza elegida es la única que muestra campos. */
  function pintarPiezas() {
    form.querySelectorAll("[data-inspector]").forEach(function (panel) {
      if (panel.hidden) return;
      var agregada = panel.hasAttribute("data-agregada");
      var pieza = agregada ? seleccion.pieza || "" : "";
      panel.querySelectorAll("fieldset[data-clave]").forEach(function (fs) {
        if (!agregada) {
          fs.hidden = false;
          return;
        }
        fs.hidden = (fs.getAttribute("data-pieza") || "") !== pieza;
      });
      panel.querySelectorAll("[data-pieza-btn]").forEach(function (boton) {
        var activa = !!pieza && boton.getAttribute("data-pieza") === pieza;
        boton.classList.toggle("activa", activa);
        if (activa) boton.setAttribute("aria-current", "true");
        else boton.removeAttribute("aria-current");
      });
      var nota = panel.querySelector("[data-editando]");
      if (!nota) return;
      var nombre = nombreEnEdicion();
      if (!agregada) {
        nota.textContent = "Editando la sección " + nombre + ".";
        return;
      }
      if (pieza) {
        nota.textContent = "Editando la pieza " + nombre + ". Solo se ven sus campos.";
        return;
      }
      nota.textContent =
        "Editando la sección " + nombre + ". Elige una pieza para ver solo sus campos.";
    });
  }

  function elegirParte(grupo) {
    seleccion = { tipo: "parte", grupo: grupo, clave: "", pieza: "" };
    pintar();
    post({ tipo: "mostrar-grupo", grupo: grupo });
  }

  function elegirPieza(grupo, pieza) {
    seleccion = { tipo: "parte", grupo: grupo, clave: "", pieza: pieza || "" };
    pintar();
    if (!pieza) return;
    var panel = form.querySelector('[data-inspector="' + CSS.escape(grupo) + '"]');
    var fs = panel && panel.querySelector('fieldset[data-pieza="' + CSS.escape(pieza) + '"]');
    if (!fs) return;
    post({
      tipo: "resaltar",
      clave: fs.getAttribute("data-clave"),
      desplazar: true,
    });
  }

  function elegirBloque(clave, desdeLienzo) {
    if (!claveValida(clave)) return;
    var fs = fieldset(clave);
    if (!fs) return;
    var vista = fs.getAttribute("data-vista");
    var grupo = fs.getAttribute("data-grupo");
    seleccion = {
      tipo: "parte",
      grupo: grupo,
      clave: clave,
      pieza: fs.getAttribute("data-pieza") || "",
    };
    if (vista === "visitante" || vista === "sesion") marcarVista(vista);
    pintar();
    post({
      tipo: "resaltar",
      clave: clave,
      vista: vista === "visitante" || vista === "sesion" ? vista : "",
      desplazar: !desdeLienzo,
    });
    if (desdeLienzo) {
      var campo = campoVisible(fs);
      if (campo) campo.focus();
      fs.scrollIntoView({ block: "nearest" });
    }
  }

  var listaSecciones = document.getElementById("lista-secciones");
  var arrastreId = "";
  if (listaSecciones) {
    listaSecciones.addEventListener("dragstart", function (event) {
      var asa = event.target.closest("[data-asa]");
      if (!asa) {
        event.preventDefault();
        return;
      }
      var item = asa.closest("[data-seccion-item]");
      if (!item) return;
      arrastreId = item.getAttribute("data-seccion-item");
      item.classList.add("arrastrando");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", arrastreId);
      if (event.dataTransfer.setDragImage) event.dataTransfer.setDragImage(item, 24, 16);
    });
    listaSecciones.addEventListener("dragover", function (event) {
      if (!arrastreId) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      var item = event.target.closest("[data-seccion-item]");
      listaSecciones.querySelectorAll(".hueco-antes, .hueco-despues").forEach(function (nodo) {
        nodo.classList.remove("hueco-antes", "hueco-despues");
      });
      if (!item || item.getAttribute("data-seccion-item") === arrastreId) return;
      var rect = item.getBoundingClientRect();
      var despues = event.clientY > rect.top + rect.height / 2;
      item.classList.add(despues ? "hueco-despues" : "hueco-antes");
    });
    listaSecciones.addEventListener("drop", function (event) {
      event.preventDefault();
      var item = event.target.closest("[data-seccion-item]");
      var id = event.dataTransfer.getData("text/plain") || arrastreId;
      var despues = !!(item && item.classList.contains("hueco-despues"));
      limpiarHuecos(listaSecciones);
      arrastreId = "";
      if (!item || !claveValida(id)) return;
      ubicarEnLista(id, item, despues);
    });
    listaSecciones.addEventListener("dragend", function () {
      arrastreId = "";
      limpiarHuecos(listaSecciones);
    });
    listaSecciones.addEventListener("keydown", function (event) {
      var asa = event.target.closest("[data-asa]");
      if (!asa) return;
      if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
      event.preventDefault();
      var item = asa.closest("[data-seccion-item]");
      if (!item) return;
      moverSeccion(item.getAttribute("data-seccion-item"), event.key === "ArrowUp" ? -1 : 1);
    });
  }

  /* La cuadrícula y las diapositivas se sueltan por el mismo envío que escribe el iframe. */
  var arrastrePieza = null;
  var arrastreDia = null;

  function diasDelCarrusel(grupo, trozo) {
    var ids = [];
    form.querySelectorAll("[data-dia-item]").forEach(function (nodo) {
      if (nodo.getAttribute("data-dia-grupo") !== grupo) return;
      if ((nodo.getAttribute("data-dia-trozo") || "") !== (trozo || "")) return;
      ids.push(nodo.getAttribute("data-dia-item"));
    });
    return ids;
  }

  function accionDia(grupo, trozo, ids) {
    var orden = ids.join(",");
    if (trozo) return "dia-orden:" + grupo + ":" + trozo + ":" + orden;
    return "dia-orden:" + grupo + ":" + orden;
  }

  function quitarMarcasArrastre() {
    var caja = document.getElementById("propiedades");
    if (!caja) return;
    caja.querySelectorAll(".hueco-casilla, .hueco-dia, .arrastrando, .arrastrando-dia").forEach(function (nodo) {
      nodo.classList.remove("hueco-casilla", "hueco-dia", "arrastrando", "arrastrando-dia");
    });
  }

  function indiceDePieza(item) {
    var lista = item.parentElement;
    if (!lista) return 0;
    return Array.prototype.indexOf.call(lista.querySelectorAll("[data-pieza-item]"), item);
  }

  function colocarPieza(item, casilla, event) {
    var lista = casilla.querySelector("[data-casilla-lista]");
    if (!lista) return;
    var sobre = event.target.closest("[data-pieza-item]");
    if (sobre === item) return;
    if (sobre && lista.contains(sobre)) {
      var rect = sobre.getBoundingClientRect();
      var despues = event.clientY > rect.top + rect.height / 2;
      var referencia = despues ? sobre.nextElementSibling : sobre;
      if (referencia) lista.insertBefore(item, referencia);
      else lista.appendChild(item);
    } else {
      lista.appendChild(item);
    }
  }

  function enviarPieza(item, casilla) {
    if (!item || !casilla || !arrastrePieza) return;
    var celda = casilla.getAttribute("data-casilla");
    var indice = indiceDePieza(item);
    if (celda === arrastrePieza.celda && indice === arrastrePieza.indice) return;
    enviarEstructura(
      "pieza-ubicar:" + arrastrePieza.seccion + ":" + arrastrePieza.ref + ":" + celda + ":" + indice
    );
  }

  function moverDiaNodo(origen, destino, despues) {
    if (!origen || !destino || origen === destino) return false;
    var referencia = despues ? destino.nextElementSibling : destino;
    if (referencia === origen) return false;
    var padre = destino.parentElement;
    if (!padre) return false;
    if (referencia) padre.insertBefore(origen, referencia);
    else padre.appendChild(origen);
    return true;
  }

  form.addEventListener("dragstart", function (event) {
    var asaDia = event.target.closest("[data-asa-dia]");
    var asaPieza = event.target.closest("[data-asa-pieza]");
    if (!asaDia && !asaPieza) return;
    if (asaDia) {
      var dia = asaDia.closest("[data-dia-item]");
      if (!dia) return;
      arrastreDia = {
        grupo: dia.getAttribute("data-dia-grupo") || "",
        trozo: dia.getAttribute("data-dia-trozo") || "",
        dia: dia.getAttribute("data-dia-item") || "",
        orden: diasDelCarrusel(dia.getAttribute("data-dia-grupo") || "", dia.getAttribute("data-dia-trozo") || "").join(","),
      };
      arrastrePieza = null;
      dia.classList.add("arrastrando-dia");
    } else {
      var pieza = asaPieza.closest("[data-pieza-item]");
      var casilla = asaPieza.closest("[data-casilla]");
      if (!pieza || !casilla) return;
      arrastrePieza = {
        seccion: pieza.getAttribute("data-pieza-seccion") || "",
        ref: pieza.getAttribute("data-pieza") || "",
        celda: casilla.getAttribute("data-casilla") || "",
        indice: indiceDePieza(pieza),
      };
      arrastreDia = null;
      pieza.classList.add("arrastrando");
    }
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", asaDia ? "dia" : "pieza");
    if (event.dataTransfer.setDragImage) {
      event.dataTransfer.setDragImage(asaDia ? asaDia.closest("[data-dia-item]") : asaPieza.closest("[data-pieza-item]"), 24, 16);
    }
  });

  form.addEventListener("dragover", function (event) {
    if (arrastreDia) {
      var dia = event.target.closest("[data-dia-item]");
      if (!dia || dia.getAttribute("data-dia-grupo") !== arrastreDia.grupo) return;
      if ((dia.getAttribute("data-dia-trozo") || "") !== arrastreDia.trozo) return;
      event.preventDefault();
      form.querySelectorAll(".hueco-dia").forEach(function (nodo) {
        nodo.classList.remove("hueco-dia");
      });
      if (dia.getAttribute("data-dia-item") !== arrastreDia.dia) dia.classList.add("hueco-dia");
      return;
    }
    if (!arrastrePieza) return;
    var casilla = event.target.closest("[data-casilla]");
    if (!casilla || casilla.getAttribute("data-casilla-seccion") !== arrastrePieza.seccion) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    form.querySelectorAll(".hueco-casilla").forEach(function (nodo) {
      nodo.classList.remove("hueco-casilla");
    });
    casilla.classList.add("hueco-casilla");
  });

  form.addEventListener("drop", function (event) {
    if (arrastreDia) {
      event.preventDefault();
      var destino = event.target.closest("[data-dia-item]");
      var origen = null;
      form.querySelectorAll("[data-dia-item]").forEach(function (nodo) {
        if (nodo.getAttribute("data-dia-grupo") === arrastreDia.grupo && nodo.getAttribute("data-dia-item") === arrastreDia.dia && (nodo.getAttribute("data-dia-trozo") || "") === arrastreDia.trozo) {
          origen = nodo;
        }
      });
      var grupo = arrastreDia.grupo;
      var trozo = arrastreDia.trozo;
      var previo = arrastreDia.orden;
      if (destino && origen && destino.getAttribute("data-dia-grupo") === grupo && (destino.getAttribute("data-dia-trozo") || "") === trozo) {
        var rect = destino.getBoundingClientRect();
        moverDiaNodo(origen, destino, event.clientY > rect.top + rect.height / 2);
      }
      quitarMarcasArrastre();
      arrastreDia = null;
      var ids = diasDelCarrusel(grupo, trozo);
      if (ids.join(",") !== previo) enviarEstructura(accionDia(grupo, trozo, ids));
      return;
    }
    if (!arrastrePieza) return;
    event.preventDefault();
    var casilla = event.target.closest("[data-casilla]");
    var item = null;
    form.querySelectorAll("[data-pieza-item]").forEach(function (nodo) {
      if (nodo.getAttribute("data-pieza-seccion") === arrastrePieza.seccion && nodo.getAttribute("data-pieza") === arrastrePieza.ref) {
        item = nodo;
      }
    });
    if (casilla && item && casilla.getAttribute("data-casilla-seccion") === arrastrePieza.seccion) {
      colocarPieza(item, casilla, event);
      enviarPieza(item, casilla);
    }
    quitarMarcasArrastre();
    arrastrePieza = null;
  });

  form.addEventListener("dragend", function () {
    arrastreDia = null;
    arrastrePieza = null;
    quitarMarcasArrastre();
  });

  form.addEventListener("keydown", function (event) {
    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    var asaDia = event.target.closest && event.target.closest("[data-asa-dia]");
    if (asaDia) {
      event.preventDefault();
      var actual = asaDia.closest("[data-dia-item]");
      if (!actual) return;
      var grupo = actual.getAttribute("data-dia-grupo") || "";
      var trozo = actual.getAttribute("data-dia-trozo") || "";
      var hermanos = [];
      form.querySelectorAll("[data-dia-item]").forEach(function (nodo) {
        if (nodo.getAttribute("data-dia-grupo") === grupo && (nodo.getAttribute("data-dia-trozo") || "") === trozo) hermanos.push(nodo);
      });
      var posicion = hermanos.indexOf(actual);
      var vecino = hermanos[posicion + (event.key === "ArrowUp" ? -1 : 1)];
      if (!vecino) return;
      var antes = diasDelCarrusel(grupo, trozo).join(",");
      moverDiaNodo(actual, vecino, event.key === "ArrowDown");
      var ids = diasDelCarrusel(grupo, trozo);
      if (ids.join(",") !== antes) enviarEstructura(accionDia(grupo, trozo, ids));
      return;
    }
    var asaPieza = event.target.closest && event.target.closest("[data-asa-pieza]");
    if (!asaPieza) return;
    event.preventDefault();
    var piezaItem = asaPieza.closest("[data-pieza-item]");
    var casillaActual = asaPieza.closest("[data-casilla]");
    if (!piezaItem || !casillaActual) return;
    var seccion = piezaItem.getAttribute("data-pieza-seccion") || "";
    var casillas = Array.prototype.filter.call(
      form.querySelectorAll('[data-casilla][data-casilla-seccion="' + CSS.escape(seccion) + '"]'),
      function () { return true; }
    );
    var lista = casillaActual.querySelector("[data-casilla-lista]");
    var locales = lista ? Array.prototype.slice.call(lista.querySelectorAll("[data-pieza-item]")) : [];
    var local = locales.indexOf(piezaItem);
    var delta = event.key === "ArrowUp" ? -1 : 1;
    var destinoCasilla = casillaActual;
    if (delta < 0 && local <= 0) {
      var anterior = casillas[casillas.indexOf(casillaActual) - 1];
      if (!anterior) return;
      destinoCasilla = anterior;
      var listaAnterior = anterior.querySelector("[data-casilla-lista]");
      if (listaAnterior) listaAnterior.appendChild(piezaItem);
    } else if (delta > 0 && local >= locales.length - 1) {
      var siguiente = casillas[casillas.indexOf(casillaActual) + 1];
      if (!siguiente) return;
      destinoCasilla = siguiente;
      var listaSiguiente = siguiente.querySelector("[data-casilla-lista]");
      var primero = listaSiguiente && listaSiguiente.querySelector("[data-pieza-item]");
      if (primero) listaSiguiente.insertBefore(piezaItem, primero);
      else if (listaSiguiente) listaSiguiente.appendChild(piezaItem);
    } else if (lista && locales[local + delta]) {
      var vecinoPieza = locales[local + delta];
      if (delta < 0) lista.insertBefore(piezaItem, vecinoPieza);
      else lista.insertBefore(vecinoPieza, piezaItem);
    } else {
      return;
    }
    arrastrePieza = {
      seccion: seccion,
      ref: piezaItem.getAttribute("data-pieza") || "",
      celda: casillaActual.getAttribute("data-casilla") || "",
      indice: local,
    };
    enviarPieza(piezaItem, destinoCasilla);
    arrastrePieza = null;
  });

  form.addEventListener("focusin", function (event) {
    var campo = event.target.closest("[data-nombre-seccion]");
    if (!campo || seleccion.grupo === campo.getAttribute("data-grupo-btn")) return;
    elegirParte(campo.getAttribute("data-grupo-btn"));
  });

  document.querySelectorAll("[data-vista-btn]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      var vista = boton.getAttribute("data-vista-btn");
      marcarVista(vista);
      post({ tipo: "vista", vista: vista });
    });
  });

  function avisoImagen(archivo) {
    if (archivo.size > MAX_IMAGEN) {
      return "la imagen pesa más de 2 MB. Elige un archivo más liviano.";
    }
    if (!TIPOS_IMAGEN[archivo.type]) {
      return "el archivo no es una imagen JPG, PNG, GIF o WEBP.";
    }
    return "";
  }

  form.addEventListener("mousedown", function (event) {
    if (event.target.closest("[data-fmt]")) event.preventDefault();
  });

  form.addEventListener("click", function (event) {
    var vivo = event.target.closest("[data-vivo]");
    if (vivo) {
      event.preventDefault();
      dispararVivo(vivo.getAttribute("data-vivo"));
      return;
    }
    var boton = event.target.closest("[data-fmt]");
    if (boton) {
      event.preventDefault();
      var caja = boton.closest("[data-formato]");
      var campo = caja && caja.querySelector("[data-campo=texto-rico]");
      if (campo) aplicarFormato(campo, boton.getAttribute("data-fmt"));
      return;
    }
    var piezaBtn = event.target.closest("[data-pieza-btn]");
    if (piezaBtn) {
      event.preventDefault();
      var panelPieza = piezaBtn.closest("[data-inspector]");
      var grupoPieza = panelPieza ? panelPieza.getAttribute("data-inspector") : seleccion.grupo;
      elegirPieza(grupoPieza, piezaBtn.getAttribute("data-pieza") || "");
      return;
    }
    var parte = event.target.closest("[data-grupo-btn]");
    if (parte && parte.tagName === "BUTTON") elegirParte(parte.getAttribute("data-grupo-btn"));
  });

  form.addEventListener("keydown", function (event) {
    var nombre = event.target.closest && event.target.closest("[data-nombre-seccion]");
    if (nombre && event.key === "Enter") {
      event.preventDefault();
      return;
    }
    var campo = event.target.closest && event.target.closest("[data-campo=texto-rico]");
    if (!campo) return;
    if (event.key === "Enter" && campo.getAttribute("aria-multiline") !== "true") {
      event.preventDefault();
      return;
    }
    if (event.altKey || !(event.ctrlKey || event.metaKey)) return;
    var tecla = String(event.key || "").toLowerCase();
    var fmt = tecla === "b" ? "strong" : tecla === "i" ? "em" : tecla === "u" ? "u" : "";
    if (!fmt) return;
    event.preventDefault();
    aplicarFormato(campo, fmt);
  });

  form.addEventListener("keyup", function (event) {
    var campo = event.target.closest && event.target.closest("[data-campo=texto-rico]");
    if (campo) refrescarBarra(campo);
  });

  form.addEventListener("mouseup", function (event) {
    var campo = event.target.closest && event.target.closest("[data-campo=texto-rico]");
    if (campo) refrescarBarra(campo);
  });

  document.addEventListener("selectionchange", function () {
    var seleccion = document.getSelection();
    if (!seleccion || !seleccion.anchorNode) return;
    var nodo = seleccion.anchorNode.nodeType === 1 ? seleccion.anchorNode : seleccion.anchorNode.parentElement;
    var campo = nodo && nodo.closest && nodo.closest("[data-campo=texto-rico]");
    if (campo && form.contains(campo)) refrescarBarra(campo);
  });

  form.addEventListener("paste", function (event) {
    var campo = event.target.closest && event.target.closest("[data-campo=texto-rico]");
    if (!campo || !window.BiocomSaneo || !event.clipboardData) return;
    event.preventDefault();
    var html = event.clipboardData.getData("text/html");
    var plano = event.clipboardData.getData("text/plain");
    if (html) document.execCommand("insertHTML", false, window.BiocomSaneo.sanear(html, perfilDe(campo)));
    else document.execCommand("insertText", false, plano || "");
    publicarCampo(campo);
  });

  form.addEventListener("input", function (event) {
    var objetivo = event.target && event.target.closest ? event.target : event.target && event.target.parentElement;
    if (!objetivo || !objetivo.closest) return;
    var nombre = objetivo.closest("[data-nombre-seccion]");
    if (nombre) {
      editado = true;
      refrescarAvisoPendiente();
      var item = nombre.closest("[data-seccion-item]");
      var asa = item && item.querySelector("[data-asa]");
      if (asa) {
        asa.setAttribute(
          "aria-label",
          "Arrastrar " + etiquetaGrupo(nombre) + ". Flechas para subir o bajar."
        );
      }
      /* El nombre de la lista solo rotula el índice y la cabecera. No se pinta en el lienzo. */
      if (
        !seleccion.pieza &&
        seleccion.tipo === "parte" &&
        seleccion.grupo === nombre.getAttribute("data-grupo-btn")
      ) {
        titulo.textContent = "Editando: " + etiquetaGrupo(nombre);
        var nota = form.querySelector(
          '[data-inspector="' + CSS.escape(seleccion.grupo) + '"] [data-editando]'
        );
        if (nota) {
          nota.textContent =
            "Editando la sección " +
            etiquetaGrupo(nombre) +
            ". Elige una pieza para ver solo sus campos.";
        }
      }
      return;
    }
    var caja = objetivo.closest("[data-formato]");
    if (caja) escribirValor(caja);
    var fs = objetivo.closest("fieldset[data-clave]");
    if (!fs || (objetivo.getAttribute && objetivo.getAttribute("data-campo") === "imagen")) return;
    editado = true;
    refrescarAvisoPendiente();
    post(mensajeCampo(fs));
  });

  function mostrarNombreArchivo(input) {
    var caja = input.closest && input.closest(".editor-archivo");
    if (!caja) return;
    var nombre = caja.querySelector("[data-archivo-nombre]");
    if (!nombre) return;
    var archivo = input.files && input.files[0];
    nombre.textContent = archivo ? archivo.name : "";
  }

  form.addEventListener("change", function (event) {
    var input = event.target;
    if (input.getAttribute("data-campo") !== "imagen") return;
    mostrarNombreArchivo(input);
    var fs = input.closest("fieldset[data-clave]");
    if (!fs) return;
    var error = fs.querySelector("[data-error-imagen]");
    var archivo = input.files && input.files[0];
    if (!archivo) {
      if (error) error.textContent = "";
      refrescarAvisoPendiente();
      post(mensajeCampo(fs));
      return;
    }
    var detalle = avisoImagen(archivo);
    if (detalle) {
      rechazarImagen(fs, error, detalle);
      return;
    }
    if (error) error.textContent = "";
    editado = true;
    refrescarAvisoPendiente();
    var lector = new FileReader();
    lector.onload = function () {
      var prueba = new Image();
      prueba.onload = function () {
        post({
          tipo: "previsualizar-imagen",
          clave: fs.getAttribute("data-clave"),
          src: lector.result,
        });
      };
      prueba.onerror = function () {
        rechazarImagen(fs, error, "el archivo no es una imagen JPG, PNG, GIF o WEBP.");
      };
      prueba.src = lector.result;
    };
    lector.readAsDataURL(archivo);
  });

  function rechazarImagen(fs, error, detalle) {
    if (error) {
      error.textContent = "«" + fs.getAttribute("data-nombre") + "»: " + detalle;
    }
    refrescarAvisoPendiente();
    var enlace = fs.querySelector("[data-campo=enlace]");
    post({
      tipo: "actualizar",
      clave: fs.getAttribute("data-clave"),
      texto: fs.querySelector("[data-campo=texto]").value,
      enlace: enlace ? enlace.value : "",
      conservarImagen: false,
    });
  }

  form.addEventListener("submit", function (event) {
    form.querySelectorAll("[data-formato]").forEach(escribirValor);
    var boton = event.submitter;
    if (boton && boton.value === "descartar") {
      if (!window.confirm("¿Descartar el borrador? Lo publicado no cambia.")) {
        event.preventDefault();
        return;
      }
    }
    if (boton && boton.value.indexOf("quitar:") === 0) {
      if (!window.confirm("¿Quitar esta sección del borrador? La página pública no cambia hasta que publiques.")) {
        event.preventDefault();
        return;
      }
    }
    if (boton && boton.value.indexOf("dia-quitar:") === 0) {
      if (!window.confirm("¿Quitar esta diapositiva del borrador? La página pública no cambia hasta que publiques.")) {
        event.preventDefault();
        return;
      }
    }
    if (boton && boton.value.indexOf("restaurar:") === 0) {
      if (!window.confirm("¿Copiar esta versión al borrador? La página pública no cambia hasta que publiques.")) {
        event.preventDefault();
        return;
      }
    }
    enviando = true;
  });

  window.addEventListener("beforeunload", function (event) {
    if (enviando || !hayCambios()) return;
    event.preventDefault();
    event.returnValue = "Hay cambios sin guardar. Si sales, se pierden; el borrador ya guardado se conserva.";
  });

  function documentoListo() {
    return !!documentoLienzo();
  }

  function marcarListo() {
    if (listo || !documentoLienzo()) return;
    listo = true;
    var pendientes = cola.splice(0, cola.length);
    pendientes.forEach(post);
    if (editado) sincronizar();
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

  form.querySelectorAll("[data-formato]").forEach(function (caja) {
    var oculto = caja.querySelector("[data-campo=texto]");
    var campo = caja.querySelector("[data-campo=texto-rico]");
    if (oculto && campo) pintarCampo(campo, oculto.value);
  });

  var vivoActivo = false;
  var vivoPendiente = "";

  function tokenCsrf() {
    var input = form.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  function confirmarVivo(accion) {
    if (accion.indexOf("quitar:") === 0) {
      return window.confirm("¿Eliminar esta sección del borrador? La página pública no cambia hasta que publiques.");
    }
    if (accion.indexOf("pieza-quitar:") === 0) {
      return window.confirm("¿Quitar esta pieza del borrador? La página pública no cambia hasta que publiques.");
    }
    if (accion.indexOf("dia-quitar:") === 0) {
      return window.confirm("¿Quitar esta diapositiva del borrador? La página pública no cambia hasta que publiques.");
    }
    return true;
  }

  function dispararVivo(accion) {
    if (!accion) return;
    if (accion.indexOf("pieza-agregar:") === 0 && accion.split(":").length < 3) {
      var id = accion.split(":")[1];
      var select = form.querySelector('[data-tipo-interna="' + CSS.escape(id) + '"]');
      accion = accion + ":" + (select ? select.value : "texto");
    }
    if (!confirmarVivo(accion)) return;
    enviarEstructura(accion);
  }

  function avisoVivo(texto, error) {
    var caja = document.getElementById("avisos-editor");
    if (!caja) return;
    var nodo = document.getElementById("aviso-vivo");
    if (!nodo) {
      nodo = document.createElement("p");
      nodo.id = "aviso-vivo";
      nodo.setAttribute("role", "status");
      caja.appendChild(nodo);
    }
    nodo.className = error ? "aviso aviso-error" : "aviso aviso-success";
    nodo.textContent = texto || "";
  }

  function htmlNodo(html) {
    var plantilla = document.createElement("template");
    plantilla.innerHTML = String(html || "").trim();
    return plantilla.content.firstElementChild;
  }

  function conScrollDePanel(fn) {
    var panel = document.querySelector(".editor-panel");
    var arriba = panel ? panel.scrollTop : 0;
    fn();
    if (panel) panel.scrollTop = arriba;
  }

  function sustituirItem(id, html) {
    conScrollDePanel(function () {
      var lista = document.getElementById("lista-secciones");
      var nuevo = htmlNodo(html);
      if (!lista || !nuevo) return;
      var actual = lista.querySelector('[data-seccion-item="' + CSS.escape(id) + '"]');
      if (actual) actual.replaceWith(nuevo);
      else lista.appendChild(nuevo);
    });
  }

  function pintarRicos(raiz) {
    (raiz || form).querySelectorAll("[data-formato]").forEach(function (caja) {
      var oculto = caja.querySelector("[data-campo=texto]");
      var campo = caja.querySelector("[data-campo=texto-rico]");
      if (oculto && campo && !campo.childNodes.length) pintarCampo(campo, oculto.value);
    });
  }

  function sustituirInspector(id, html) {
    conScrollDePanel(function () {
      var caja = document.getElementById("propiedades");
      var nuevo = htmlNodo(html);
      if (!caja || !nuevo) return;
      var actual = caja.querySelector('[data-inspector="' + CSS.escape(id) + '"]');
      if (actual) actual.replaceWith(nuevo);
      else caja.appendChild(nuevo);
      pintarRicos(nuevo);
    });
  }

  function aplicarEstructura(data) {
    if (!data || !data.ok) {
      avisoVivo((data && data.aviso) || "No se pudo guardar el cambio.", true);
      return;
    }
    avisoVivo(data.aviso || "", false);
    if (data.estado) {
      guardado = data.estado;
      guardado.textos = guardado.textos || {};
      guardado.enlaces = guardado.enlaces || {};
      guardado.nombres = guardado.nombres || {};
      guardado.orden = guardado.orden || "";
    }
    var campoOrden = document.getElementById("orden-secciones");
    if (campoOrden && Array.isArray(data.orden)) campoOrden.value = data.orden.join(",");
    if (data.quitar && data.id) {
      var item = document.querySelector('[data-seccion-item="' + CSS.escape(data.id) + '"]');
      if (item) item.remove();
      var inspector = form.querySelector('[data-inspector="' + CSS.escape(data.id) + '"]');
      if (inspector) inspector.remove();
      if (seleccion.grupo === data.id) {
        seleccion = { tipo: "parte", grupo: ordenActual()[0] || "", clave: "", pieza: "" };
      }
    } else {
      if (data.html_item) sustituirItem(data.id, data.html_item);
      if (data.html_campos) sustituirInspector(data.id, data.html_campos);
      if (data.seleccionar) {
        seleccion = { tipo: "parte", grupo: data.seleccionar, clave: "", pieza: "" };
      }
    }
    if (typeof data.pieza === "string") seleccion.pieza = data.pieza;
    form.querySelectorAll("[data-campo=imagen]").forEach(function (input) {
      if (input.files && input.files.length) input.value = "";
      mostrarNombreArchivo(input);
    });
    pintar();
    /* El iframe sigue siendo el mismo documento: el inspector nuevo no lo desengancha. */
    post({
      tipo: "seccion",
      id: data.id,
      html: data.html_lienzo || "",
      orden: data.orden || [],
    });
    if (data.seleccionar && titulo) titulo.scrollIntoView({ block: "nearest" });
    refrescarAvisoPendiente();
  }

  function enviarEstructura(accion) {
    if (vivoActivo) {
      vivoPendiente = accion;
      return;
    }
    vivoActivo = true;
    var datos = new FormData(form);
    datos.set("accion", accion);
    fetch(form.action, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-Editor-Vivo": "1",
        Accept: "application/json",
        "X-CSRFToken": tokenCsrf(),
      },
      body: datos,
    })
      .then(function (respuesta) {
        return respuesta.json();
      })
      .then(aplicarEstructura)
      .catch(function () {
        avisoVivo("No se pudo guardar el cambio. Inténtalo otra vez.", true);
      })
      .then(function () {
        vivoActivo = false;
        var siguiente = vivoPendiente;
        vivoPendiente = "";
        if (siguiente) enviarEstructura(siguiente);
      });
  }

  pintar();
  prepararAncho();

  var primerError = null;
  form.querySelectorAll(".error-campo").forEach(function (nodo) {
    if (!primerError && nodo.textContent.trim()) primerError = nodo;
  });
  if (primerError) {
    var fsError = primerError.closest("fieldset[data-clave]");
    if (fsError) {
      elegirBloque(fsError.getAttribute("data-clave"), false);
      var destino = campoVisible(fsError);
      if (primerError.hasAttribute("data-error-imagen")) {
        destino = fsError.querySelector("[data-campo=imagen]");
      } else if (primerError.hasAttribute("data-error-enlace")) {
        destino = fsError.querySelector("[data-campo=enlace]");
      }
      if (destino) destino.focus();
      fsError.scrollIntoView({ block: "nearest" });
    }
  }
  refrescarAvisoPendiente();

  /* El ancho vive en el navegador: no es parte del borrador ni de lo publicado. */
  function prepararAncho() {
    var columnas = document.querySelector(".editor-columnas");
    var divisor = document.querySelector("[data-divisor]");
    if (!columnas || !divisor) return;
    var CLAVE = "biocom.editor.ancho-panel";
    var MIN = 256;
    var MIN_LIENZO = 320;
    var TOPE = 640;
    var preferido = null;

    function divisorVisible() {
      return divisor.getClientRects().length > 0;
    }

    function tope() {
      return Math.max(MIN, Math.min(TOPE, columnas.clientWidth - MIN_LIENZO));
    }

    function aplicar(px, guardar) {
      var ancho = Math.round(Math.max(MIN, Math.min(tope(), px)));
      if (guardar) preferido = ancho;
      if (!divisorVisible()) {
        columnas.style.removeProperty("--ancho-panel");
        return;
      }
      columnas.style.setProperty("--ancho-panel", ancho + "px");
      divisor.setAttribute("aria-valuemin", String(MIN));
      divisor.setAttribute("aria-valuemax", String(Math.round(tope())));
      divisor.setAttribute("aria-valuenow", String(ancho));
      if (!guardar) return;
      try {
        localStorage.setItem(CLAVE, String(ancho));
      } catch (error) {
        /* Sin almacenamiento el ajuste vale solo para esta visita. */
      }
    }

    try {
      var bruto = localStorage.getItem(CLAVE);
      var leido = Number(bruto);
      if (bruto && isFinite(leido)) preferido = leido;
    } catch (error) {
      preferido = null;
    }

    if (divisorVisible() && columnas.clientWidth >= MIN + MIN_LIENZO) {
      var inicial = preferido;
      if (inicial == null) {
        var panel = columnas.querySelector(".editor-panel");
        inicial = panel ? panel.getBoundingClientRect().width : 448;
      }
      aplicar(inicial, false);
    }

    var activo = false;
    divisor.addEventListener("pointerdown", function (event) {
      if (event.button !== 0) return;
      activo = true;
      divisor.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    divisor.addEventListener("pointermove", function (event) {
      if (!activo) return;
      var rect = columnas.getBoundingClientRect();
      aplicar(event.clientX - rect.left, false);
    });
    function soltar() {
      if (!activo) return;
      activo = false;
      var ancho = parseFloat(columnas.style.getPropertyValue("--ancho-panel"));
      if (isFinite(ancho)) aplicar(ancho, true);
    }
    divisor.addEventListener("pointerup", soltar);
    divisor.addEventListener("pointercancel", soltar);
    divisor.addEventListener("keydown", function (event) {
      var actual = preferido;
      if (!isFinite(actual)) {
        actual = parseFloat(columnas.style.getPropertyValue("--ancho-panel"));
      }
      if (!isFinite(actual)) return;
      var paso = event.shiftKey ? 48 : 16;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        aplicar(actual - paso, true);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        aplicar(actual + paso, true);
      }
    });
    window.addEventListener("resize", function () {
      if (!divisorVisible()) {
        columnas.style.removeProperty("--ancho-panel");
        return;
      }
      var deseado = preferido;
      if (!isFinite(deseado)) {
        deseado = parseFloat(columnas.style.getPropertyValue("--ancho-panel"));
      }
      if (!isFinite(deseado)) {
        var panel = columnas.querySelector(".editor-panel");
        deseado = panel ? panel.getBoundingClientRect().width : 448;
      }
      aplicar(deseado, false);
    });
  }
})();
