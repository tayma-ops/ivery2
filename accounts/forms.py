from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile


class SignupForm(UserCreationForm):
    first_name = forms.CharField(label="الاسم", max_length=150)
    email = forms.EmailField(label="البريد الإلكتروني")

    class Meta:
        model = User
        fields = ("username", "first_name", "email", "password1", "password2")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("phone", "city", "address")
