from .models import Scientific_reference
from django import forms

class ScientificReferenceForm(forms.ModelForm):
    nebula_name = forms.CharField(max_length=150, required=True, label='Nombre de la nebulosa', widget=forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Ej. Abell 39'}))
    morphological_type = forms.ChoiceField(choices=Scientific_reference.MORPHOLOGICAL_CHOICES, required=True, label='Tipo morfológico', widget=forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary'}))
    bibliographic_source = forms.CharField(max_length=255, required=True, label='Referencia', widget=forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Ej. SIMBAD, VizieR...'}))
    theoretical_values = forms.CharField(required=True, label='Valores teóricos', widget=forms.Textarea(attrs={'class': 'form-control bg-dark text-white border-secondary', 'rows': 4}))
    
    # Este metodo se utiliza para epecificar el modelo asociado al formulario y los campos que se incluirán en el formulario. En este caso, el formulario está asociado al modelo Scientific_reference y se incluyen todos los campos del modelo.
    class Meta:
        model = Scientific_reference
        fields = ['nebula_name', 'morphological_type', 'bibliographic_source', 'theoretical_values']