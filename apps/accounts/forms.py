from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Profile, SiteConfiguration

class ClientSignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + ('email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.type = CustomUser.Types.CLIENT
        if commit:
            user.save()
        return user

class ProfessionalSignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + ('email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.type = CustomUser.Types.PROFESSIONAL
        if commit:
            user.save()
        return user

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class ProfileForm(forms.ModelForm):
    # media_files REMOVED to avoid validation blocking. Processed manually in View.
    phone = forms.CharField(
        required=False,
        label="Telefono de llamada",
        widget=forms.TextInput(attrs={'class': 'w-full pl-12 py-2 border rounded-lg focus:ring-fuchsia-500', 'placeholder': '+34 600 000 000'})
    )
    whatsapp_id = forms.CharField(
        required=False,
        label="WhatsApp",
        widget=forms.TextInput(attrs={'class': 'w-full pl-12 py-2 border rounded-lg focus:ring-fuchsia-500', 'placeholder': '+34 600 000 000'})
    )
    telegram_id = forms.CharField(
        required=False,
        label="Telegram",
        widget=forms.TextInput(attrs={'class': 'w-full pl-12 py-2 border rounded-lg focus:ring-fuchsia-500', 'placeholder': '@usuario o https://t.me/usuario'})
    )

    def clean(self):
        cleaned_data = super().clean()
        
        # 1. Base Usage (Existing Media + Existing Avatar)
        current_usage = 0
        if self.instance.pk:
            # Existing Avatar
            if self.instance.avatar:
                try:
                    current_usage += self.instance.avatar.size
                except: pass
            
            # Existing Media Gallery
            for media in self.instance.media.all():
                try:
                    if media.file:
                        current_usage += media.file.size
                except: pass
        
        # 2. Add New Uploads
        new_usage = 0
        
        # New Gallery Files - DIRECTLY FROM RAW FILES
        # We don't rely on cleaned_data['media_files'] because the field is gone
        new_files = self.files.getlist('media_files')
        new_usage += sum([f.size for f in new_files])
        
        # New Avatar
        avatar = cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size'):
             new_usage += avatar.size
             # Strict 1MB for Avatar if desired, but Global Quota is the law.
             if avatar.size > 2 * 1024 * 1024: # Let's give 2MB slack for avatar if inside global quota
                 self.add_error('avatar', "El avatar no puede superar 2 MB.")

        # 3. Validation
        TOTAL_LIMIT = 35 * 1024 * 1024 # 35 MB
        projected_total = current_usage + new_usage
        
        if projected_total > TOTAL_LIMIT:
             msg = f"Has superado la cuota global de 35MB permitida por perfil profesional. (Uso: {projected_total/(1024*1024):.2f} MB)"
             raise forms.ValidationError(msg)

        return cleaned_data

    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-fuchsia-500', 'type': 'date'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
        required=False,
        label="Fecha de Nacimiento"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['birth_date'].widget.format = '%Y-%m-%d'
        if self.instance and self.instance.pk:
            self.fields['phone'].initial = self.instance.user.phone
            self.fields['whatsapp_id'].initial = self.instance.user.whatsapp_id
            self.fields['telegram_id'].initial = self.instance.user.telegram_id

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.phone = self.cleaned_data.get('phone', '')
        user.whatsapp_id = self.cleaned_data.get('whatsapp_id', '')
        user.telegram_id = self.cleaned_data.get('telegram_id', '')
        if commit:
            user.save(update_fields=['phone', 'whatsapp_id', 'telegram_id'])
            profile.save()
            self.save_m2m()
        return profile

    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'zone', 'origin', 'birth_date', 'instagram_url', 'facebook_url', 'twitter_url']
        labels = {
            'bio': 'Nombre y descripción'
        }
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-fuchsia-500', 'rows': 3}),
            'zone': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-fuchsia-500'}),
            'origin': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-fuchsia-500'}),
            'birth_date': forms.DateInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:ring-fuchsia-500', 'type': 'date'}, format='%Y-%m-%d'),
            'instagram_url': forms.URLInput(attrs={'class': 'w-full pl-12 py-2 border rounded-lg focus:ring-fuchsia-500', 'placeholder': 'https://instagram.com/...'}),
            'facebook_url': forms.URLInput(attrs={'class': 'w-full pl-12 py-2 border rounded-lg focus:ring-fuchsia-500', 'placeholder': 'https://facebook.com/...'}),
            'twitter_url': forms.URLInput(attrs={'class': 'w-full pl-12 py-2 border rounded-lg focus:ring-fuchsia-500', 'placeholder': 'https://x.com/...'}),
        }


class ControlUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'type',
            'is_active',
            'tangas_balance',
            'phone',
            'whatsapp_id',
            'telegram_id',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500'}),
            'type': forms.Select(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500 bg-white'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-fuchsia-600 rounded'}),
            'tangas_balance': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'step': '0.01'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'placeholder': '+34 600 000 000'}),
            'whatsapp_id': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'placeholder': '+34 600 000 000'}),
            'telegram_id': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'placeholder': '@usuario'}),
        }


class ControlProfileForm(forms.ModelForm):
    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'type': 'date'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
        required=False,
        label="Fecha de nacimiento"
    )

    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'zone', 'origin', 'birth_date', 'instagram_url', 'facebook_url', 'twitter_url']
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-3 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-fuchsia-50 file:text-fuchsia-700'}),
            'bio': forms.Textarea(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'rows': 4}),
            'zone': forms.Select(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500 bg-white'}),
            'origin': forms.Select(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500 bg-white'}),
            'instagram_url': forms.URLInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'placeholder': 'https://instagram.com/...'}),
            'facebook_url': forms.URLInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'placeholder': 'https://facebook.com/...'}),
            'twitter_url': forms.URLInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'placeholder': 'https://x.com/...'}),
        }


class ManualTangaRechargeForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        required=False,
        label="Tangas a recargar",
        widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'step': '0.01', 'min': '0.01'})
    )
    description = forms.CharField(
        required=False,
        label="Concepto",
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-3 border rounded-xl focus:ring-fuchsia-500', 'placeholder': 'Recarga manual superadmin'})
    )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError("Indica cuantos Tangas quieres recargar.")
        return amount


class SiteConfigurationForm(forms.ModelForm):
    class Meta:
        model = SiteConfiguration
        fields = ['support_email', 'maintenance_mode']
        widgets = {
            'support_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border rounded-lg focus:ring-fuchsia-500',
                'placeholder': 'soporte@ahhh-ibiza.com',
            }),
            'maintenance_mode': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 rounded text-fuchsia-600',
            }),
        }
