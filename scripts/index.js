// Simulación de datos para las estadísticas
document.addEventListener('DOMContentLoaded', function() {
    // Simular carga de estadísticas
    setTimeout(() => {
        document.getElementById('total-vehiculos').textContent = '12';
        document.getElementById('en-taller').textContent = '8';
    }, 1000);

    // Efectos de hover mejorados
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
});