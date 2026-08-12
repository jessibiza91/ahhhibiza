from django import forms

from .models import TangasPackage


class TangasPackageForm(forms.ModelForm):
    class Meta:
        model = TangasPackage
        fields = ['name', 'tangas_amount', 'price_eur', 'sort_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500'}),
            'tangas_amount': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'min': '1'}),
            'price_eur': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'min': '0.01', 'step': '0.01'}),
            'sort_order': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded text-fuchsia-600'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('tangas_amount') is not None and cleaned['tangas_amount'] <= 0:
            self.add_error('tangas_amount', 'La cantidad de Tangas debe ser mayor que cero.')
        if cleaned.get('price_eur') is not None and cleaned['price_eur'] <= 0:
            self.add_error('price_eur', 'El precio debe ser mayor que cero.')
        return cleaned
