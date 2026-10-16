/* El mismo control de mostrar/ocultar en login, registro, cambio y restablecimiento. */
(function () {
    function bind(button) {
        var input = document.getElementById(button.getAttribute('data-toggle-password'));
        if (!input) {
            return;
        }
        var icon = button.querySelector('i');
        button.addEventListener('click', function () {
            var show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            if (icon) {
                icon.classList.toggle('fa-eye', !show);
                icon.classList.toggle('fa-eye-slash', show);
            }
            button.setAttribute('aria-pressed', show ? 'true' : 'false');
            var hideLabel = button.getAttribute('data-label-hide') || 'Ocultar contraseña';
            var showLabel = button.getAttribute('data-label-show') || 'Mostrar contraseña';
            button.setAttribute('aria-label', show ? hideLabel : showLabel);
        });
    }

    function init() {
        document.querySelectorAll('[data-toggle-password]').forEach(bind);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
