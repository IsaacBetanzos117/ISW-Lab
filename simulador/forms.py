from .models import Simulation_configuration
from django import forms

# Esta clase define un formulario para la configuración de simulaciones, utilizando el modelo Simulation_configuration. Hereda de forms.ModelForm, lo que permite crear un formulario basado en un modelo de Django. Se definen varios campos del formulario, cada uno con sus propias validaciones y etiquetas. Además, se personaliza la apariencia de los campos de entrada numéricos agregando la clase 'form-control' para que tengan un estilo consistente con Bootstrap.
class SimulationConfigurationForm(forms.ModelForm):
    configuration_name = forms.CharField(max_length=150, required=True, label='Nombre de la configuración')
    morphological_type = forms.ChoiceField(choices=Simulation_configuration.MORPHOLOGICAL_CHOISES, required=True, label='Tipo morfológico')
    gas_temperature = forms.FloatField(required=True, label='Temperatura del gas', min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Kelvin (K)'}))
    particle_density = forms.FloatField(required=True, label='Densidad de partículas', min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Partículas por cm³'}))
    expansion_velocity = forms.FloatField(required=True, label='Velocidad de expansión', min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'km/s'}))
    nebula_radius = forms.FloatField(required=True, label='Radio de la nebulosa', min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Parsecs (pc)'}))
    mass_loss_rate = forms.FloatField(required=True, label='Tasa de pérdida de masa', min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Masa por año (M☉/año)'}))
    evolution_time = forms.IntegerField(required=True, label='Tiempo de evolución', min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Años'}))
    
    # La clase Meta se utiliza para especificar el modelo asociado al formulario y los campos que se incluirán en el formulario. En este caso, el formulario está asociado al modelo Simulation_configuration y se incluyen todos los campos del modelo.
    class Meta:
        model = Simulation_configuration
        fields = ['configuration_name', 'morphological_type', 'gas_temperature', 'particle_density', 'expansion_velocity', 'nebula_radius', 'mass_loss_rate', 'evolution_time']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # Llama al método __init__ de la clase padre (forms.ModelForm) para inicializar el formulario
        
        # Este ciclo recorre todos los campos del formulario y agrega la clase 'form-control' a los campos de tipo NumberInput para que tengan un estilo consistente con Bootstrap.
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.NumberInput):
                field.widget.attrs['class'] = 'form-control' # Agrega la clase 'form-control' a todos los campos de tipo NumberInput para que tengan un estilo consistente con Bootstrap
        
        # Solo bloquea los campos si el registro ya existe (estamos en modo edición)
        if self.instance and self.instance.pk:
            if 'configuration_name' in self.fields:
                self.fields['configuration_name'].disabled = True
                self.fields['configuration_name'].help_text = "El nombre de la configuración está fijo para este experimento."

            if 'morphological_type' in self.fields:
                self.fields['morphological_type'].disabled = True
                self.fields['morphological_type'].help_text = "La morfología base no puede alterarse en la fase de ajuste dinámico."