// Variables globales
let dataTable;
let dataTableIsInitialized = false;

const dataTableOptions = {
    columnDefs: [
        { className: "centered", targets: [0, 1, 2, 3] },
        { orderable: false, targets: [2, 3] }
    ],
    pageLength: 5,
    destroy: true,
    autoWidth: false,
    lengthMenu: [[5, 25, 50, -1], [5, 25, 50, "Todos"]],
    language: {
        decimal: ",",
        emptyTable: "No hay datos disponibles",
        info: "Mostrando _START_ a _END_ de _TOTAL_ registros",
        infoEmpty: "Mostrando 0 a 0 de 0 registros",
        infoFiltered: "(filtrado de _MAX_ registros)",
        lengthMenu: "Mostrar _MENU_ registros",
        loadingRecords: "Cargando...",
        processing: "Procesando...",
        search: "Buscar:",
        zeroRecords: "No se encontraron resultados",
        paginate: {
            first: "Primero",
            last: "Último",
            next: "Siguiente",
            previous: "Anterior"
        }
    }
};

const infoUsers = async () => {
    try {

        const response = await fetch("/identity/info_usuarios/");
        const data = await response.json();

        let content = ``;

        data.info_users.forEach((info) => {
            content += `
                <tr>
                    <td data-label="Usuario">${info.username}</td>
                    <td data-label="Nombre">${info.first_name + " " + info.last_name}</td>
                    <td data-label="Permisos">
                        ${info.is_superuser ? '<span class="badge rounded-1 text-bg-success">Super usuario</span>' : ''}
                        ${info.is_staff ? '<span class="badge rounded-1 text-bg-primary">Administrador</span>' : ''}
                        ${!info.is_superuser && !info.is_staff ? '<span class="badge rounded-1 text-bg-secondary">Estudiante</span>' : ''}
                    </td>
                    <td data-label="Ver detalles">
                        <button class = 'btn btn-sm view-button' style = 'color: #38B7E0' data-id='${info.id}'><i class = 'fa-solid fa-arrow-right'></i></button>
                    </td>
                </tr>
            `;
        });
        tableBody.innerHTML = content;

        $('.view-button').click(function () {

            const userID = $(this).data('id');

            window.location.href = `/identity/detalle_usuarios/id=${userID}/`;

        });
    } catch (ex) {
        alert(ex);
    }
};

const initDataTable = async () => {
    if (dataTableIsInitialized) {
        dataTable.destroy();
    }

    await infoUsers();

    dataTable = $('#info').dataTable(dataTableOptions);

    dataTableIsInitialized = true;
};

window.addEventListener("load", async () => {
    await initDataTable();
});

