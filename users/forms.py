from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True, label='Nombre')
    last_name = forms.CharField(max_length=150, required=True, label='Apellidos')
    email = forms.EmailField(required=True, label='Correo electrónico')
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True, label='Nombre')
    last_name = forms.CharField(max_length=150, required=True, label='Apellidos')
    email = forms.EmailField(required=True, label='Correo electrónico')
    
    class Meta:
            model = User
            fields = ['username', 'first_name', 'last_name', 'email']

'''
class LoginForm(forms.Form):
    class Meta:
        model = User
        fields = ['username', 'password'] '''