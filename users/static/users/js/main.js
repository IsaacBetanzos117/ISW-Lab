document.addEventListener('DOMContentLoaded', function(){
    // Control de alertas: Ocultar suavemente para minimizar carga cognitiva
    const alertas = document.querySelectorAll('.alert');
    if(alertas.length > 0){
        setTimeout(() => {
            alertas.forEach(alerta => {
                alerta.style.transition = 'opacity 0.5s ease-out';
                alerta.style.opacity = '0';
                setTimeout(() => alerta.remove(), 500);
            });
        }, 5000);
    }

    // Validación de formularios en tiempo real
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event){
            let isValid = true;
            const inputs = form.querySelectorAll('input[required]');

            inputs.forEach(input => {
                if(!input.value.trim()){
                    isValid = false;
                    input.style.borderColor = 'var(--danger-color)';
                    input.style.borderWidth = '2px';
                }
            });

            if (!isValid) {
                event.preventDefault(); // Detiene el envío si hay errores
                // Podrías inyectar un mensaje de error accesible aquí si lo deseas
                print('Error')
            }
        });
    });
});