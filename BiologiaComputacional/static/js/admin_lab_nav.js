/* El filtro de Django esconde filas. Aquí se esconde también el título
   del grupo si no quedó ningún enlace visible. */
(function () {
  function actualizarGrupos() {
    document.querySelectorAll("#nav-sidebar .admin-lab-nav-grupo").forEach(function (grupo) {
      var filas = grupo.querySelectorAll("tbody tr");
      var visible = false;
      filas.forEach(function (fila) {
        if (fila.style.display !== "none") {
          visible = true;
        }
      });
      grupo.hidden = filas.length > 0 && !visible;
    });
  }

  var filtro = document.getElementById("nav-filter");
  if (!filtro) {
    return;
  }
  filtro.addEventListener("input", actualizarGrupos);
  filtro.addEventListener("change", actualizarGrupos);
  filtro.addEventListener("keyup", actualizarGrupos);
  actualizarGrupos();
})();
