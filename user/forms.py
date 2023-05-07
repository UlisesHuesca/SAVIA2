from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


#Esta "form" fue creada heredando (inherit) las características de la "UserCreationForm" pero agregándole el "email"
class UserForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username','email','password1','password2']


