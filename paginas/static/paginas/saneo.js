/* Misma lista blanca que paginas/saneo.py: el lienzo la aplica al vuelo
   y el servidor vuelve a sanear al guardar y al pintar.
   Estrategia: "linea" es título, botón o etiqueta; "bloque" es párrafo. */
(function () {
  var PREFIJO = "<!--biocom-html-->";
  var ETIQUETAS_LINEA = { br: 1, strong: 1, em: 1, u: 1, a: 1 };
  var ETIQUETAS_BLOQUE = { p: 1, br: 1, strong: 1, em: 1, u: 1, ul: 1, ol: 1, li: 1, a: 1 };
  var ALIAS = { b: "strong", i: "em", ins: "u", div: "p" };
  var DESCARTAR = {
    script: 1, style: 1, iframe: 1, object: 1, embed: 1,
    noscript: 1, template: 1, svg: 1, math: 1,
  };
  var ESQUEMAS = { http: 1, https: 1, mailto: 1 };
  var IGNORADOS = /[\u0000-\u0020\u007f\u00a0\u1680\u2000-\u200d\u2028\u2029\u202f\u205f\u2060\u3000\ufeff]/g;
  var MAX_HREF = 2000;

  function perfilDe(perfil) {
    return perfil === "linea" ? "linea" : "bloque";
  }

  function etiquetasDe(perfil) {
    return perfilDe(perfil) === "linea" ? ETIQUETAS_LINEA : ETIQUETAS_BLOQUE;
  }

  function escapar(texto) {
    return String(texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escaparAttr(texto) {
    return escapar(texto).replace(/"/g, "&quot;");
  }

  function hrefSeguro(valor) {
    if (valor == null) return null;
    var compacto = String(valor).replace(IGNORADOS, "");
    if (!compacto || compacto.indexOf("\\") !== -1 || compacto.length > MAX_HREF) return null;
    var bajo = compacto.toLowerCase();
    if (bajo.indexOf("//") === 0) return null;
    var corte = bajo.indexOf(":");
    if (corte <= 0) return null;
    var esquema = bajo.slice(0, corte);
    if (!ESQUEMAS[esquema] || !bajo.slice(corte + 1)) return null;
    return compacto;
  }

  function walk(nodo, etiquetas) {
    var html = "";
    nodo.childNodes.forEach(function (hijo) {
      if (hijo.nodeType === 3) {
        html += escapar(hijo.nodeValue);
        return;
      }
      if (hijo.nodeType !== 1) return;
      var tag = hijo.tagName.toLowerCase();
      if (DESCARTAR[tag]) return;
      tag = ALIAS[tag] || tag;
      if (tag === "br") {
        if (etiquetas.br) html += "<br>";
        return;
      }
      if (!etiquetas[tag]) {
        if (tag === "li") html += " ";
        html += walk(hijo, etiquetas);
        return;
      }
      if (tag === "a") {
        var href = hrefSeguro(hijo.getAttribute("href"));
        if (!href) {
          html += walk(hijo, etiquetas);
          return;
        }
        html += '<a href="' + escaparAttr(href) + '">' + walk(hijo, etiquetas) + "</a>";
        return;
      }
      html += "<" + tag + ">" + walk(hijo, etiquetas) + "</" + tag + ">";
    });
    return html;
  }

  function sanear(html, perfil) {
    var doc = new DOMParser().parseFromString(String(html || ""), "text/html");
    return walk(doc.body, etiquetasDe(perfil));
  }

  function desescapar(texto) {
    return texto
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/&amp;/g, "&");
  }

  function aPlano(html) {
    if (/<\s*\/?\s*(strong|em|u|ins|ul|ol|li|a)\b/i.test(html)) return null;
    if (/<\s*\/?\s*(?!br\b|p\b)[a-z]/i.test(html)) return null;
    var plano = html
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/p>\s*<p>/gi, "\n")
      .replace(/<\/?p>/gi, "");
    return desescapar(plano).replace(/^\n+|\n+$/g, "");
  }

  function valor(html, perfil) {
    var limpio = sanear(html, perfil);
    var plano = aPlano(limpio);
    if (plano !== null) return plano;
    return PREFIJO + limpio;
  }

  function sinMarcas(html) {
    var limpio = sanear(html, "bloque");
    var doc = new DOMParser().parseFromString(limpio, "text/html");
    return doc.body.textContent || "";
  }

  window.BiocomSaneo = {
    PREFIJO: PREFIJO,
    sanear: sanear,
    hrefSeguro: hrefSeguro,
    valor: valor,
    sinMarcas: sinMarcas,
    valorDesdeDom: function (raiz, perfil) {
      return valor(walk(raiz, etiquetasDe(perfil)), perfil);
    },
  };
})();
