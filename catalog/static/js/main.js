/* Interacciones UI y reducción de carga cognitiva (Cumplimiento IN.2) */
document.addEventListener('DOMContentLoaded', function() {
    // Buscar todas las alertas flotantes (mensajes de éxito/error de Django)
    const alerts = document.querySelectorAll('.alert:not(.alert-danger)'); 

    alerts.forEach(alert => {
        // Desaparecer automáticamente después de 5 segundos
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease";
            alert.style.opacity = "0";
            
            // Eliminar del DOM después de la transición
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 5000);
    });
});