from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import CustomUser


class PromotionProduct(models.Model):
    class Visibility(models.TextChoices):
        BASIC = 'BASIC', _('Basico')
        FEATURED = 'FEATURED', _('Destacado')
        TOP = 'TOP', _('Siempre arriba')

    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    price_tangas = models.PositiveIntegerField(default=0)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.BASIC)
    priority_weight = models.PositiveIntegerField(default=0, help_text="Mas alto aparece antes.")
    duration_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority_weight', 'price_tangas', 'name']

    def __str__(self):
        return f"{self.name} ({self.price_tangas} Tangas)"


class Ad(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Activo (Consume Tangas)')
        CERRADO = 'CERRADO', _('Cerrado (Sin Consumo)')

    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ads')
    title = models.CharField(max_length=200)
    
    # Descriptions
    public_description = models.TextField(blank=True, verbose_name="Descripción Pública")
    hot_description = models.TextField(blank=True, null=True, verbose_name="Descripción Privada HOT")
    
    # Financials
    promotion_product = models.ForeignKey(
        PromotionProduct,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ads',
    )
    price_tangas = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.ACTIVE,
        verbose_name=_('Estado del Anuncio')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    trashed_at = models.DateTimeField(null=True, blank=True)
    trashed_by = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='trashed_ads',
    )
    trash_note = models.CharField(max_length=255, blank=True)

    # Services (Tags)
    services = models.ManyToManyField('ServiceTag', blank=True, related_name='ads', verbose_name="Servicios Ofrecidos")

    @property
    def cover_image(self):
        public_image = self.gallery.filter(is_private=False, trashed_at__isnull=True).order_by('created_at').first()
        return public_image or self.gallery.filter(trashed_at__isnull=True).order_by('created_at').first()

    @property
    def is_trashed(self):
        return self.trashed_at is not None

    def send_to_trash(self, by_user=None, note=""):
        self.trashed_at = timezone.now()
        self.trashed_by = by_user
        self.trash_note = note
        self.status = self.Status.CERRADO
        self.save(update_fields=['trashed_at', 'trashed_by', 'trash_note', 'status', 'updated_at'])

    def restore_from_trash(self):
        self.trashed_at = None
        self.trashed_by = None
        self.trash_note = ""
        self.status = self.Status.CERRADO
        self.save(update_fields=['trashed_at', 'trashed_by', 'trash_note', 'status', 'updated_at'])

    def __str__(self):
        return self.title

class ServiceTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class AdImage(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='ad_images/')
    is_private = models.BooleanField(default=False, verbose_name="Es HOT (Privada)")
    created_at = models.DateTimeField(auto_now_add=True)
    trashed_at = models.DateTimeField(null=True, blank=True)
    trashed_by = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='trashed_ad_images',
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

    def __str__(self):
        return f"Imagen de {self.ad.title}"
