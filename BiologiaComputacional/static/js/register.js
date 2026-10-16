(function () {
    'use strict';

    var form = document.getElementById('registerForm');
    if (!form) {
        return;
    }

    form.addEventListener('submit', function (event) {
        if (!form.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        form.classList.add('was-validated');
    });

    bindTakenCheck(
        document.getElementById('validationCustomUsername'),
        'username',
        document.getElementById('usernameFeedback'),
        'Este nombre de usuario ya está registrado.',
        form.dataset.signinUrl,
        'Inicia sesión'
    );
    bindTakenCheck(
        document.getElementById('floatingInputGroupEmail'),
        'email',
        document.getElementById('emailFeedback'),
        'Ya existe una cuenta con este correo.',
        form.dataset.resetUrl,
        'Recupera tu contraseña'
    );

    var password1 = document.getElementById('floatingInputGroupPassword1');
    var password2 = document.getElementById('floatingInputGroupPassword2');
    var passwordFeedback = document.getElementById('passwordFeedback');

    function syncPasswords() {
        if (!password2.value) {
            password2.setCustomValidity('');
            if (!passwordFeedback.textContent.trim() || passwordFeedback.dataset.client === '1') {
                hideFeedback(passwordFeedback);
            }
            return;
        }
        if (password1.value !== password2.value) {
            password2.setCustomValidity('Las contraseñas no coinciden.');
            showText(passwordFeedback, 'Las contraseñas no coinciden.');
        } else {
            password2.setCustomValidity('');
            hideFeedback(passwordFeedback);
        }
    }

    password1.addEventListener('input', syncPasswords);
    password2.addEventListener('input', syncPasswords);

    document.getElementById('togglePassword1').addEventListener('click', function () {
        togglePassword(password1, document.getElementById('togglePasswordIcon1'));
    });
    document.getElementById('togglePassword2').addEventListener('click', function () {
        togglePassword(password2, document.getElementById('togglePasswordIcon2'));
    });

    function bindTakenCheck(input, param, feedback, message, linkHref, linkText) {
        var requestId = 0;

        var initial = feedback.textContent.trim();
        if (initial) {
            input.setCustomValidity(initial);
        }

        function clearWhileEditing() {
            input.setCustomValidity('');
            hideFeedback(feedback);
        }

        function lookup() {
            var value = input.value.trim();
            if (!value || (param === 'email' && value.indexOf('@') === -1)) {
                clearWhileEditing();
                return;
            }
            var current = ++requestId;
            var url = new URL(form.dataset.availabilityUrl, window.location.origin);
            url.searchParams.set(param, value);
            fetch(url, { headers: { 'Accept': 'application/json' } })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    if (current !== requestId) {
                        return;
                    }
                    var taken = param === 'username' ? data.username_taken : data.email_taken;
                    if (taken) {
                        input.setCustomValidity(message);
                        showTaken(feedback, message, linkHref, linkText);
                    } else {
                        input.setCustomValidity('');
                        hideFeedback(feedback);
                    }
                })
                .catch(function () {
                    input.setCustomValidity('');
                });
        }

        var timer = null;
        input.addEventListener('input', function () {
            clearWhileEditing();
            window.clearTimeout(timer);
            timer = window.setTimeout(lookup, 350);
        });
        input.addEventListener('blur', function () {
            window.clearTimeout(timer);
            lookup();
        });
    }

    function showTaken(feedback, message, href, linkText) {
        feedback.dataset.client = '1';
        feedback.hidden = false;
        feedback.replaceChildren(document.createTextNode(message + ' '));
        var link = document.createElement('a');
        link.href = href;
        link.className = 'text-link-custom fw-semibold';
        link.textContent = linkText;
        feedback.appendChild(link);
    }

    function showText(feedback, message) {
        feedback.dataset.client = '1';
        feedback.hidden = false;
        feedback.textContent = message;
    }

    function hideFeedback(feedback) {
        feedback.hidden = true;
        feedback.textContent = '';
        delete feedback.dataset.client;
    }

    function togglePassword(input, icon) {
        var visible = input.type === 'password';
        input.type = visible ? 'text' : 'password';
        icon.classList.toggle('fa-eye', !visible);
        icon.classList.toggle('fa-eye-slash', visible);
    }
})();
