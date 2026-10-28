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
  var seleccion = { tipo: "parte", grupo: grupoInicial(), clave: "" };

  function leerGuardado() {
    var nodo = document.getElementById("estado-guardado");
    if (!nodo) return { textos: {}, enlaces: {}, orden: "" };
    try {
      var datos = JSON.parse(nodo.textContent);
      datos.textos = datos.textos || {};
      datos.enlaces = datos.enlaces || {};
      datos.orden = datos.orden || "";
      return datos;
    } catch (error) {
      return { textos: {}, enlaces: {}, orden: "" };
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
    if (listo && fs) post(mensajeCampo(fs));
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

  function post(mensaje) {
    if (!listo || !marco.contentWindow) {
      cola.push(mensaje);
      return;
    }
    marco.contentWindow.postMessage(mensaje, ORIGEN);
  }

  function mensajeCampo(fs) {
    var enlace = fs.querySelector("[data-campo=enlace]");
    var imagen = fs.querySelector("[data-campo=imagen]");
    var hayArchivo = !!(imagen && imagen.files && imagen.files.length);
    return {
      tipo: "actualizar",
      clave: fs.getAttribute("data-clave"),
      texto: fs.querySelector("[data-campo=texto]").value,
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

  function actualizarFlechas() {
    var items = document.querySelectorAll("[data-seccion-item]");
    Array.prototype.forEach.call(items, function (item, indice) {
      var subir = item.querySelector("[data-subir]");
      var bajar = item.querySelector("[data-bajar]");
      if (subir) subir.disabled = indice === 0;
      if (bajar) bajar.disabled = indice === items.length - 1;
    });
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
    var campo = document.getElementById("orden-secciones");
    if (campo) campo.value = ordenActual().join(",");
    actualizarFlechas();
    editado = true;
    refrescarAvisoPendiente();
    enviarOrden();
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
      titulo.textContent = fs ? fs.getAttribute("data-nombre") : "Propiedades";
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
      var campo = campoVisible(fs);
      if (campo) campo.focus();
      fs.scrollIntoView({ block: "nearest" });
    }
  }

  var listaSecciones = document.getElementById("lista-secciones");
  if (listaSecciones) {
    listaSecciones.addEventListener("click", function (event) {
      var subir = event.target.closest("[data-subir]");
      var bajar = event.target.closest("[data-bajar]");
      if (!subir && !bajar) return;
      var item = event.target.closest("[data-seccion-item]");
      if (!item) return;
      moverSeccion(item.getAttribute("data-seccion-item"), subir ? -1 : 1);
    });
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
    var boton = event.target.closest("[data-fmt]");
    if (!boton) return;
    event.preventDefault();
    var caja = boton.closest("[data-formato]");
    var campo = caja && caja.querySelector("[data-campo=texto-rico]");
    if (!campo) return;
    aplicarFormato(campo, boton.getAttribute("data-fmt"));
  });

  form.addEventListener("keydown", function (event) {
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
    var caja = event.target.closest("[data-formato]");
    if (caja) escribirValor(caja);
    var fs = event.target.closest("fieldset[data-clave]");
    if (!fs || event.target.getAttribute("data-campo") === "imagen") return;
    editado = true;
    refrescarAvisoPendiente();
    if (listo) post(mensajeCampo(fs));
  });

  form.addEventListener("change", function (event) {
    var input = event.target;
    if (input.getAttribute("data-campo") !== "imagen") return;
    var fs = input.closest("fieldset[data-clave]");
    if (!fs) return;
    var error = fs.querySelector("[data-error-imagen]");
    var archivo = input.files && input.files[0];
    if (!archivo) {
      if (error) error.textContent = "";
      refrescarAvisoPendiente();
      if (listo) post(mensajeCampo(fs));
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
    enviando = true;
  });

  window.addEventListener("beforeunload", function (event) {
    if (enviando || !hayCambios()) return;
    event.preventDefault();
    event.returnValue = "Hay cambios sin guardar. Si sales, se pierden; el borrador ya guardado se conserva.";
  });

  function documentoListo() {
    try {
      var doc = marco.contentDocument;
      if (!doc || doc.readyState !== "complete") return false;
      var actual = new URL(doc.URL, window.location.href);
      var esperado = new URL(marco.getAttribute("src"), window.location.href);
      return actual.pathname === esperado.pathname;
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

  form.querySelectorAll("[data-formato]").forEach(function (caja) {
    var oculto = caja.querySelector("[data-campo=texto]");
    var campo = caja.querySelector("[data-campo=texto-rico]");
    if (oculto && campo) pintarCampo(campo, oculto.value);
  });

  actualizarFlechas();
  pintar();

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
})();
