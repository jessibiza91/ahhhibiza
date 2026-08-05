from django import forms

from .models import Ad, PromotionProduct, ServiceTag
from apps.accounts.forms import MultipleFileInput

# Campo que permite subir multiples archivos
class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        if not data:
            return []

        if isinstance(data, (list, tuple)):
            return [
                super().clean(file, initial)
                for file in data
            ]

        return [super().clean(data, initial)]

class AdForm(forms.ModelForm):
    STATUS_CHOICES = [
        ('ACTIVE', 'Activo'),
        ('CERRADO', 'Cerrado'),
    ]

    promotion_product = forms.ModelChoiceField(
        queryset=PromotionProduct.objects.none(),
        required=False,
        empty_label="Basico - sin promocion",
        widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-fuchsia-500 bg-white'}),
        label="Producto de promocion"
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-fuchsia-500 bg-white'}),
        label="Estado del Anuncio"
    )

    public_media = MultipleFileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        label="Galeria Publica (Visible para todos)"
    )

    hot_media = MultipleFileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        label="Galeria HOT (Privada)"
    )

    services = forms.ModelMultipleChoiceField(
        queryset=Ad.services.rel.model.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox h-5 w-5 text-fuchsia-600'}),
        required=False,
        label="Servicios Disponibles"
    )

    class Meta:
        model = Ad
        fields = ['title', 'public_description', 'hot_description', 'services', 'promotion_product', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-fuchsia-500', 'placeholder': 'Titulo atractivo...'}),
            'public_description': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-fuchsia-500', 'rows': 4, 'placeholder': 'Descripcion visible para todos...'}),
            'hot_description': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-fuchsia-500 border-fuchsia-200 bg-fuchsia-50', 'rows': 4, 'placeholder': 'Contenido exclusivo para clientes registrados...'}),
        }
        labels = {
            'hot_description': 'Descripcion Privada HOT (Solo Clientes Registrados)',
        }
        help_texts = {
            'public_description': 'Este material es visible sin registro. Evita desnudos o textos explicitos en la parte publica.',
            'hot_description': 'Contenido reservado para usuarios registrados.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['promotion_product'].queryset = PromotionProduct.objects.filter(is_active=True)

    def save(self, commit=True):
        ad = super().save(commit=False)
        product = self.cleaned_data.get('promotion_product')
        ad.promotion_product = product
        ad.price_tangas = product.price_tangas if product else 0
        if commit:
            ad.save()
            self.save_m2m()
        return ad


class ControlAdForm(forms.ModelForm):
    public_media = MultipleFileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        label="Anadir fotos publicas"
    )

    hot_media = MultipleFileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        required=False,
        label="Anadir fotos privadas"
    )

    services = forms.ModelMultipleChoiceField(
        queryset=Ad.services.rel.model.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox h-5 w-5 text-fuchsia-600'}),
        required=False,
        label="Servicios"
    )

    class Meta:
        model = Ad
        fields = ['title', 'public_description', 'hot_description', 'services', 'promotion_product', 'price_tangas', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500'}),
            'public_description': forms.Textarea(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'rows': 5}),
            'hot_description': forms.Textarea(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500 border-fuchsia-200 bg-fuchsia-50', 'rows': 5}),
            'promotion_product': forms.Select(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500 bg-white'}),
            'price_tangas': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'min': '0'}),
            'status': forms.Select(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500 bg-white'}),
        }


class PromotionProductForm(forms.ModelForm):
    class Meta:
        model = PromotionProduct
        fields = ['name', 'description', 'price_tangas', 'visibility', 'priority_weight', 'duration_days', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'rows': 3}),
            'price_tangas': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'min': '0'}),
            'visibility': forms.Select(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500 bg-white'}),
            'priority_weight': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'min': '0'}),
            'duration_days': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'min': '1'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded text-fuchsia-600'}),
        }


class ServiceTagForm(forms.ModelForm):
    class Meta:
        model = ServiceTag
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border rounded-lg focus:ring-fuchsia-500',
                'placeholder': 'Nombre del servicio',
            }),
        }
