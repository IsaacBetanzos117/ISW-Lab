from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from grupos.models import Academic_group

# Create your models here.
# Esta clase representa la configuración de parámetros físicos de una simulación que un estudiante o docente puede crear, actualizar y guardar en su historial privado.
class Simulation_configuration(models.Model):
    MORPHOLOGICAL_CHOISES = [
        ('esferica', 'Esférica'),
        ('eliptica', 'Elíptica'),
        ('bipolar', 'Bipolar'),
        ('multipolar', 'Multipolar'),
        ('proto-planetaria', 'Proto-planetaria'),
    ]
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='configuraciones')
    configuration_name = models.CharField(max_length=150, verbose_name='Nombre de la configuración')
    morphological_type = models.CharField(max_length=50, choices=MORPHOLOGICAL_CHOISES, verbose_name='Tipo morfológico')
    gas_temperature = models.FloatField(verbose_name='Temperatura del gas')
    particle_density = models.FloatField(verbose_name='Densidad de partículas')
    expansion_velocity = models.FloatField(verbose_name='Velocidad de expansión')
    nebula_radius = models.FloatField(verbose_name='Radio de la nebulosa')
    mass_loss_rate = models.FloatField(verbose_name='Tasa de pérdida de masa')
    evolution_time = models.IntegerField(verbose_name='Tiempo de evolución')
    saved_date = models.DateTimeField(auto_now_add=True)
    academic_group = models.ForeignKey(Academic_group, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"{self.configuration_name}, {self.author.username}"

# Esta clase representa el historial de simulaciones que un estudiante o docente ha ejecutado, incluyendo el estado de estabilidad, tiempo de ejecución y notas personales. Cada registro está vinculado a una configuración específica de simulación.
class Simulation_history(models.Model):
    STATUS_CHOICES = [
        ('estable', 'Estable'),
        ('divergente', 'Error numérico'),
    ]
    
    # Llave foránea hacia la configuración que se usó para esta simulación
    configuration = models.ForeignKey(Simulation_configuration, on_delete=models.CASCADE, related_name='historial_simulaciones')
    
    # Campos que ya tienes en tu diagrama
    stability_status = models.CharField(max_length=50, choices=STATUS_CHOICES, verbose_name='Estado de estabilidad')
    execution_time_sec = models.FloatField(verbose_name='Tiempo de ejecución (segundos)')
    student_notes = models.TextField(blank=True, null=True, verbose_name='Notas personales')
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Resultado de {self.configuration.configuration_name} - {self.stability_status}"
