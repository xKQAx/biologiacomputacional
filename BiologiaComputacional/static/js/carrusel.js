/* Carrusel de la portada con desplazamiento lateral (scroll-snap).
   El mismo HTML vale en el lienzo y en lo publicado: al sustituir una sección
   no hay que reiniciar una librería. En escritorio se ven unas tres tarjetas;
   el paso es de una. El avance automático es lento y se detiene con el mouse
   o el teclado. */
(function () {
  var INTERVALO = 9000;

  function reducido() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function pistaDe(carrusel) {
    return carrusel.querySelector("[data-carrusel-pista]");
  }

  function diasDe(carrusel) {
    return carrusel.querySelectorAll(".carrusel-dia");
  }

  function medidasDe(carrusel) {
    var caja = pistaDe(carrusel);
    var dias = diasDe(carrusel);
    if (!caja || !dias.length) return null;
    var ancho = dias[0].getBoundingClientRect().width;
    var estilo = window.getComputedStyle(caja);
    var hueco = parseFloat(estilo.columnGap || estilo.gap);
    if (!isFinite(hueco)) hueco = 0;
    var paso = ancho + hueco;
    if (paso < 1) paso = caja.clientWidth || 1;
    var visibles = Math.max(1, Math.round((caja.clientWidth + hueco) / paso));
    return {
      caja: caja,
      paso: paso,
      maximo: Math.max(0, dias.length - visibles),
    };
  }

  function indiceDe(carrusel) {
    var medidas = medidasDe(carrusel);
    if (!medidas) return 0;
    return Math.max(0, Math.min(medidas.maximo, Math.round(medidas.caja.scrollLeft / medidas.paso)));
  }

  function marcar(carrusel, n) {
    carrusel.querySelectorAll("[data-carrusel-punto]").forEach(function (punto, i) {
      if (i === n) punto.setAttribute("aria-current", "true");
      else punto.removeAttribute("aria-current");
    });
  }

  function ir(carrusel, n) {
    var medidas = medidasDe(carrusel);
    if (!medidas) return;
    var destino = n;
    if (destino > medidas.maximo) destino = 0;
    if (destino < 0) destino = medidas.maximo;
    medidas.caja.scrollTo({
      left: destino * medidas.paso,
      behavior: reducido() ? "auto" : "smooth",
    });
    marcar(carrusel, destino);
  }

  function pararReloj(carrusel) {
    if (!carrusel._temporizador) return;
    window.clearInterval(carrusel._temporizador);
    carrusel._temporizador = 0;
  }

  function pausar(carrusel, motivo) {
    carrusel.dataset["pausa" + motivo] = "1";
    pararReloj(carrusel);
  }

  function arrancar(carrusel) {
    var medidas = medidasDe(carrusel);
    if (!carrusel.isConnected || reducido() || !medidas || medidas.maximo < 1) return;
    if (carrusel.dataset.pausaMouse || carrusel.dataset.pausaTeclado) return;
    if (carrusel._temporizador) return;
    carrusel._temporizador = window.setInterval(function () {
      if (!carrusel.isConnected) {
        pararReloj(carrusel);
        return;
      }
      ir(carrusel, indiceDe(carrusel) + 1);
    }, INTERVALO);
  }

  function reanudar(carrusel, motivo) {
    delete carrusel.dataset["pausa" + motivo];
    arrancar(carrusel);
  }

  function carruselDe(nodo) {
    return nodo && nodo.closest ? nodo.closest("[data-carrusel]") : null;
  }

  document.addEventListener("click", function (event) {
    var anterior = event.target.closest("[data-carrusel-anterior]");
    var siguiente = event.target.closest("[data-carrusel-siguiente]");
    var punto = event.target.closest("[data-carrusel-punto]");
    var control = anterior || siguiente || punto;
    if (!control) return;
    var carrusel = carruselDe(control);
    if (!carrusel) return;
    event.preventDefault();
    if (punto) ir(carrusel, Number(punto.getAttribute("data-carrusel-punto")));
    else ir(carrusel, indiceDe(carrusel) + (anterior ? -1 : 1));
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    var carrusel = carruselDe(event.target);
    if (!carrusel) return;
    event.preventDefault();
    pausar(carrusel, "Teclado");
    ir(carrusel, indiceDe(carrusel) + (event.key === "ArrowLeft" ? -1 : 1));
  });

  document.addEventListener(
    "scroll",
    function (event) {
      var caja = event.target;
      if (!caja || !caja.matches || !caja.matches("[data-carrusel-pista]")) return;
      var carrusel = carruselDe(caja);
      if (carrusel) marcar(carrusel, indiceDe(carrusel));
    },
    true
  );

  document.addEventListener("mouseover", function (event) {
    var carrusel = carruselDe(event.target);
    if (!carrusel || carrusel.contains(event.relatedTarget)) return;
    pausar(carrusel, "Mouse");
  });

  document.addEventListener("mouseout", function (event) {
    var carrusel = carruselDe(event.target);
    if (!carrusel || carrusel.contains(event.relatedTarget)) return;
    if (carrusel.contains(document.activeElement)) return;
    reanudar(carrusel, "Mouse");
  });

  document.addEventListener("focusin", function (event) {
    var carrusel = carruselDe(event.target);
    if (carrusel) pausar(carrusel, "Teclado");
  });

  document.addEventListener("focusout", function (event) {
    var carrusel = carruselDe(event.target);
    if (!carrusel || carrusel.contains(event.relatedTarget)) return;
    if (carrusel.matches(":hover")) {
      delete carrusel.dataset.pausaTeclado;
      return;
    }
    reanudar(carrusel, "Teclado");
  });

  function vigilar(raiz) {
    raiz.querySelectorAll("[data-carrusel]").forEach(arrancar);
  }

  vigilar(document);

  var contenido = document.getElementById("contenido-inicio");
  if (contenido && window.MutationObserver) {
    new MutationObserver(function () {
      vigilar(contenido);
    }).observe(contenido, { childList: true, subtree: true });
  }
})();
