import re
from django import forms


class ReservationForm(forms.Form):
    token = forms.UUIDField()
    resource = forms.IntegerField(min_value=1)
    service = forms.SlugField(max_length=50)
    date = forms.CharField(max_length=10)
    time = forms.CharField(max_length=5)
    customer = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=20)
    vehicle = forms.ChoiceField(
        choices=[("", ""), ("sedan", "سيدان"), ("suv", "دفع رباعي")], required=False
    )
    wax = forms.BooleanField(required=False)
    scent = forms.BooleanField(required=False)
    notes = forms.CharField(max_length=500, required=False)

    def clean_phone(self):
        value = self.cleaned_data["phone"].translate(
            str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        )
        value = re.sub(r"[ ()-]", "", value)
        if not re.fullmatch(r"(?:05[0-9]{8}|\+?9665[0-9]{8})", value):
            raise forms.ValidationError("أدخل رقم جوال سعودي صحيحًا.")
        return value
