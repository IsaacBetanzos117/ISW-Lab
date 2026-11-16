/* Validaciones asíncronas y prevención de errores (Cumplimiento IN.2 e IN.1) */
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            let isValid = true;
            const requiredFields = form.querySelectorAll('[required]');

            // Limpiar errores previos
            form.querySelectorAll('.custom-error-msg').forEach(msg => msg.remove());

            requiredFields.forEach(field => {
                // Validación básica de campos vacíos
                if (!field.value.trim()) {
                    isValid = false;
                    
                    // Modificación visual de alto contraste
                    field.style.borderColor = 'var(--error-border)';
                    field.style.borderWidth = '2px';
                    field.setAttribute('aria-invalid', 'true');

                    // Creación de mensaje de error semántico para lectores de pantalla (IN.1)
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'text-danger mt-1 custom-error-msg fw-bold';
                    errorMsg.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i> Este campo es obligatorio.';
                    errorMsg.setAttribute('role', 'alert');
                    
                    field.parentNode.insertBefore(errorMsg, field.nextSibling);
                } else {
                    // Restaurar estado normal si es válido
                    field.style.borderColor = '';
                    field.style.borderWidth = '';
                    field.removeAttribute('aria-invalid');
                }
            });

            // Si hay errores, detenemos el envío al servidor
            if (!isValid) {
                event.preventDefault();
            }
        });
    });
});