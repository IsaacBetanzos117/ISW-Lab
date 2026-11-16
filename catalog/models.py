from django.db import models
from django.contrib.auth.models import User

# Create your models here.

# Esta clase representa una tabla de referencias científicas en la base de datos. Contiene información sobre nebulosas, su tipo morfológico, la fuente bibliográfica, valores teóricos y el autor que creó la referencia. Además, registra la fecha de creación de cada registro.
class Scientific_reference(models.Model):
    MORPHOLOGICAL_CHOICES = [
        ('esferica', 'Esférica'),
        ('eliptica', 'Elíptica'),
        ('bipolar', 'Bipolar'),
        ('multipolar', 'Multipolar'),
        ('proto-planetaria', 'Proto-planetaria'),
    ]
    
    nebula_name = models.CharField(max_length=150, verbose_name='Nombre de la nebulosa')
    morphological_type = models.CharField(max_length=50, choices=MORPHOLOGICAL_CHOICES, verbose_name='Tipo morfológico')
    bibliographic_source = models.CharField(max_length=255, verbose_name='bibliografia')
    theoretical_values = models.TextField(verbose_name='valores teoricos')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scientific_references')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nebula_name}, {self.morphological_type}"