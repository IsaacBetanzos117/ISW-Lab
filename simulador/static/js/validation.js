document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input[type="number"]');

    inputs.forEach(input => {
        input.addEventListener('input', function() {
            validateField(this);
        });
        
        // Validación al perder el foco (blur)
        input.addEventListener('blur', function() {
            validateField(this);
        });
    });

    function validateField(field) {
        // Ejemplo de regla: No permitir valores negativos en masa o densidad
        if(field.value < 0){
            field.classList.add('is-invalid');
            field.classList.remove('is-valid');
            showFeedback(field, 'error', 'El valor no puede ser negativo.');
        }else if (field.value === ''){
            field.classList.remove('is-invalid', 'is-valid');
            removeFeedback(field);
        }else{
            field.classList.add('is-valid');
            field.classList.remove('is-invalid');
            showFeedback(field, 'success', 'Parámetro aceptado.');
        }
    }

    function showFeedback(field, status, message){
        removeFeedback(field); // Limpiar previo
        const feedback = document.createElement('div');
        feedback.className = `feedback-text feedback-${status}`;
        const iconClass = status === 'error' ? 'fa-solid fa-triangle-exclamation' : 'fa-solid fa-circle-check';
        feedback.innerHTML = `<i class="${iconClass}"></i> ${message}`;
        
        field.parentNode.appendChild(feedback);
    }

    function removeFeedback(field){
        const existingFeedback = field.parentNode.querySelector('.feedback-text');
        if(existingFeedback){
            existingFeedback.remove();
        }
    }
});