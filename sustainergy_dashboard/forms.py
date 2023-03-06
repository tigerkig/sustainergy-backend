from datetime import date

from django import forms

from sustainergy_dashboard.models import UtilityBill


class UtilityBillForm(forms.ModelForm):
    class Meta:
        model = UtilityBill
        fields = [
            "meter", "statement_date"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['meter'].empty_label = None
        self.fields['statement_date'].widget = forms.TextInput(attrs={'type': 'date'})
        self.fields['statement_date'].label = 'Year'
