from django import forms
from django.db import transaction
from django.utils import timezone

from .models import Ad, PromotionProduct, ServiceTag
from apps.accounts.forms import MultipleFileInput
from apps.accounts.media_validators import validate_uploaded_file
from apps.accounts.models import CustomUser

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
        widget=MultipleFileInput(attrs={'multiple': True, 'accept': 'image/*,video/*'}),
        required=False,
        label="Galeria Publica (Visible para todos)",
        validators=[validate_uploaded_file],
    )

    hot_media = MultipleFileField(
        widget=MultipleFileInput(attrs={'multiple': True, 'accept': 'image/*,video/*'}),
        required=False,
        label="Galeria HOT (Privada)",
        validators=[validate_uploaded_file],
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

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._ad_owner = owner
        # Se captura antes de validar: ModelForm escribe los datos limpios en
        # self.instance durante is_valid(), lo que enmascara el plan previo.
        self._original_promotion_product_id = self.instance.promotion_product_id
        self.fields['promotion_product'].queryset = PromotionProduct.objects.filter(is_active=True)

    def _is_exempt(self):
        return bool(
            self.instance.pk
            and self.instance.tangas_charge_exempt
        )

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('promotion_product')
        # El primer dia de un plan de pago se cobra al elegirlo (ver save()).
        # Solo se exige saldo cuando el plan cambia: mantener el plan actual
        # nunca vuelve a cobrar.
        if (
            product is not None
            and product.price_tangas > 0
            and product.id != self._original_promotion_product_id
            and not self._is_exempt()
        ):
            owner = self._ad_owner or self.instance.owner
            if owner and owner.tangas_balance < product.price_tangas:
                self.add_error(
                    'promotion_product',
                    f'Saldo insuficiente de Tangas para este plan '
                    f'(coste por dia: {product.price_tangas} T).',
                )
        return cleaned_data

    def save(self, commit=True):
        ad = super().save(commit=False)
        if self._ad_owner is not None:
            ad.owner = self._ad_owner
        product = self.cleaned_data.get('promotion_product')
        ad.promotion_product = product
        ad.price_tangas = product.price_tangas if product else 0

        # Primer dia de un plan de pago: se descuenta al elegirlo (no al
        # renovar un plan ya activo). Marca last_tangas_charged_at para que el
        # cron diario no vuelva a cobrar el mismo dia. Los anuncios exentos de
        # cobro no pagan el primer dia ni se exige saldo.
        first_day_charge = (
            product is not None
            and product.price_tangas > 0
            and product.id != self._original_promotion_product_id
            and not self._is_exempt()
        )

        if commit:
            with transaction.atomic():
                if first_day_charge:
                    owner = CustomUser.objects.select_for_update().get(pk=ad.owner_id)
                    owner.tangas_balance -= product.price_tangas
                    owner.save(update_fields=['tangas_balance'])
                    ad.last_tangas_charged_at = timezone.localdate()
                ad.save()
                self.save_m2m()
        else:
            if first_day_charge:
                ad.last_tangas_charged_at = timezone.localdate()
        return ad


class ControlAdForm(forms.ModelForm):
    public_media = MultipleFileField(
        widget=MultipleFileInput(attrs={'multiple': True, 'accept': 'image/*,video/*'}),
        required=False,
        label="Anadir fotos publicas",
        validators=[validate_uploaded_file],
    )

    hot_media = MultipleFileField(
        widget=MultipleFileInput(attrs={'multiple': True, 'accept': 'image/*,video/*'}),
        required=False,
        label="Anadir fotos privadas",
        validators=[validate_uploaded_file],
    )

    services = forms.ModelMultipleChoiceField(
        queryset=Ad.services.rel.model.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox h-5 w-5 text-fuchsia-600'}),
        required=False,
        label="Servicios"
    )

    class Meta:
        model = Ad
        fields = ['title', 'public_description', 'hot_description', 'services', 'promotion_product', 'price_tangas', 'status', 'tangas_charge_exempt', 'tangas_exempt_reason']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500'}),
            'public_description': forms.Textarea(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'rows': 5}),
            'hot_description': forms.Textarea(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500 border-fuchsia-200 bg-fuchsia-50', 'rows': 5}),
            'promotion_product': forms.Select(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500 bg-white'}),
            'price_tangas': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'min': '0'}),
            'status': forms.Select(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500 bg-white'}),
            'tangas_charge_exempt': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded text-fuchsia-600'}),
            'tangas_exempt_reason': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'placeholder': 'P.ej. cortesia para lanzamiento'}),
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
