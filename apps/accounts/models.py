import re

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver

def user_directory_path(instance, filename):
    # Universal path handler
    if hasattr(instance, 'user'):
        uid = instance.user.id
    elif hasattr(instance, 'profile'):
        uid = instance.profile.user.id
    else:
        uid = 'unknown'
    return f'user_{uid}/{filename}'

class CustomUser(AbstractUser):
    class Types(models.TextChoices):
        CLIENT = 'CLIENT', _('Cliente')
        PROFESSIONAL = 'PROFESSIONAL', _('Profesional')

    type = models.CharField(
        max_length=20, 
        choices=Types.choices, 
        default=Types.CLIENT,
        verbose_name=_('Tipo de Usuario')
    )
    tangas_balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name=_('Saldo de Tangas')
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    telegram_id = models.CharField(max_length=50, blank=True, null=True)
    whatsapp_id = models.CharField(max_length=50, blank=True, null=True)
    
    # Legacy/Transition fields
    legal_terms_accepted = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)
    trashed_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='trashed_users',
    )
    trash_note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_type_display()})"

    @property
    def is_trashed(self):
        return self.trashed_at is not None

    def send_to_trash(self, by_user=None, note=""):
        self.trashed_at = timezone.now()
        self.trashed_by = by_user
        self.trash_note = note
        self.is_active = False
        self.save(update_fields=['trashed_at', 'trashed_by', 'trash_note', 'is_active'])

    def restore_from_trash(self):
        self.trashed_at = None
        self.trashed_by = None
        self.trash_note = ""
        self.is_active = True
        self.save(update_fields=['trashed_at', 'trashed_by', 'trash_note', 'is_active'])

    @property
    def phone_call_url(self):
        if not self.phone:
            return ""
        compact_phone = re.sub(r"[\s().-]+", "", self.phone)
        return f"tel:{compact_phone}"

    @property
    def whatsapp_url(self):
        value = self.whatsapp_id or self.phone
        if not value:
            return ""
        digits = re.sub(r"\D+", "", value)
        if not digits:
            return ""
        return f"https://wa.me/{digits}"

    @property
    def telegram_url(self):
        if not self.telegram_id:
            return ""
        value = self.telegram_id.strip()
        if value.startswith(("http://", "https://")):
            return value
        return f"https://t.me/{value.lstrip('@')}"

class Profile(models.Model):
    MUNICIPIOS = [
        ('EIVISSA', 'Eivissa'),
        ('SANT_ANTONI', 'Sant Antoni de Portmany'),
        ('SANTA_EULARIA', 'Santa Eulalia'),
        ('SANT_JOSEP', 'Sant Josep de sa Talaia'),
        ('SANT_JOAN', 'Sant Joan de Labritja'),
    ]

    ORIGENES = [
        ('EUR', 'Europea'),
        ('LAT', 'Latina'),
        ('BRA', 'Brasileña'),
        ('ASI', 'Asiatica'),
        ('RUS', 'Rusa/Slavic'),
        ('OTRO', 'Otro'),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to=user_directory_path, null=True, blank=True)
    bio = models.TextField(blank=True, verbose_name=_('Biografía'))
    zone = models.CharField(
        max_length=50, 
        choices=MUNICIPIOS, 
        default='EIVISSA'
    )
    origin = models.CharField(
        max_length=20, 
        choices=ORIGENES, 
        default='EUR',
        verbose_name=_('Origen')
    )
    birth_date = models.DateField(null=True, blank=True, verbose_name=_('Fecha de Nacimiento'))
    instagram_url = models.URLField(blank=True, help_text="Enlace a Instagram")
    facebook_url = models.URLField(blank=True, help_text="Enlace a Facebook")
    twitter_url = models.URLField(blank=True, help_text="Enlace a X (Twitter)")
    
    profile_visits = models.PositiveIntegerField(default=0, verbose_name=_('Visitas al Perfil'))

    def get_age(self):
        if self.birth_date:
            from datetime import date
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None

    def __str__(self):
        return f"Perfil de {self.user.username}"

class ProfileMedia(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to=user_directory_path)
    is_video = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    trashed_at = models.DateTimeField(null=True, blank=True)
    trashed_by = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='trashed_profile_media',
    )
    trash_note = models.CharField(max_length=255, blank=True)

    @property
    def is_trashed(self):
        return self.trashed_at is not None

    def send_to_trash(self, by_user=None, note=""):
        self.trashed_at = timezone.now()
        self.trashed_by = by_user
        self.trash_note = note
        self.save(update_fields=['trashed_at', 'trashed_by', 'trash_note'])

    def restore_from_trash(self):
        self.trashed_at = None
        self.trashed_by = None
        self.trash_note = ""
        self.save(update_fields=['trashed_at', 'trashed_by', 'trash_note'])

    def save(self, *args, **kwargs):
        # We enforce limits in views/forms to ensure user feedback
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Media for {self.profile.user.username}"


class FavoriteAd(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='favorite_ads')
    ad = models.ForeignKey('ads.Ad', on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'ad')
        ordering = ['-created_at']
        verbose_name = "Anuncio favorito"
        verbose_name_plural = "Anuncios favoritos"

    def __str__(self):
        return f"{self.user.username} -> {self.ad.title}"

class SiteConfiguration(models.Model):
    support_email = models.EmailField(default='soporte@ahhh-ibiza.com', help_text="Correo de soporte para usuarios")
    maintenance_mode = models.BooleanField(default=False, help_text="Activar modo mantenimiento")

    def __str__(self):
        return "Configuración del Sitio"

    class Meta:
        verbose_name = "Configuración Global"
        verbose_name_plural = "Configuración Global"

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    Profile.objects.get_or_create(user=instance)
