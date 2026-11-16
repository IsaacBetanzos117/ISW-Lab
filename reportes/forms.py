from django import forms

# Esta clase define un formulario para filtrar los reportes gerenciales por fecha de inicio, fecha de fin y grupo académico. Se utiliza en la vista ManagementReportsView para capturar los filtros ingresados por el usuario.
class ReportFilterForm(forms.Form):\
    # Campos del formulario para filtrar los reportes gerenciales
    start_date = forms.DateField(
        required=False,
        label='Fecha de inicio',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        label='Fecha de fin',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    group_id = forms.IntegerField(
        required=False,
        label='ID del grupo (Opcional)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 1'})
    )
    
    # Este método asegura que la fecha final no sea menor a la de inicio
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin.")
        
        return cleaned_data