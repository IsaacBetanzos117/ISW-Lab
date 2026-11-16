from django import forms
from django.contrib.auth.models import User
from .models import Academic_group

# Esta clase genera el formulario HTML para crear y editar grupos académicos y su posterior guardado directo en la base de datos basándose en el modelo.
class AcademicGroupForm(forms.ModelForm):
    
    # Sobrescribe el campo class_name para inyectar clases de CSS (Bootstrap) y definir textos de ayuda visual (placeholder) desde el backend.
    class_name = forms.CharField(label='Nombre de la clase', max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. Modelado de nebulosas planetarias.'
        })
    )
    
    # Configuracion visual de la caja de selección múltiple de alumnos. El queryset inicial se declara vacío (none) por seguridad, ya que 
    # la verdadera consulta filtrada se inyecta dinámicamente en el método __init__.
    students = forms.ModelMultipleChoiceField(
        label='Estudiantes inscritos',
        queryset=User.objects.all(), # Valor inicial obligatorio, se filtra en __init__, consulta SELECT
        required=False, # Permite crear un grupo vacío sin alumnos al principio
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        help_text="Mantén presionado Shift para seleccionar varios estudiantes."
    )
    
    # La clase Meta actúa como el puente de configuración entre el formulario y el modelo,, le indica a Django qué modelo usar y qué campos específicos deben renderizarse.
    class Meta:
        model = Academic_group
        fields = ['class_name', 'students']
    
    # Este método se ejecuta automáticamente cada vez que se crea una instancia del formulario
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['students'].queryset = User.objects.filter(groups__name='Estudiante').order_by('username') # Filtra la consulta para que evalúe la BD en tiempo real al abrir el form