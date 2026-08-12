from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class TangasPackage(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name=_('Nombre'))
    tangas_amount = models.PositiveIntegerField(default=0, verbose_name=_('Cantidad de Tangas'))
    price_eur = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        verbose_name=_('Precio (EUR)'),
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Activo'))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_('Orden'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'price_eur', 'name']
        verbose_name = _('Paquete de Tangas')
        verbose_name_plural = _('Paquetes de Tangas')

    def __str__(self):
        return f"{self.name} ({self.tangas_amount} T / {self.price_eur:.2f} EUR)"


class RechargeOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pendiente')
        PAID = 'PAID', _('Pagada')
        FAILED = 'FAILED', _('Fallida')
        CANCELLED = 'CANCELLED', _('Cancelada')
        REFUNDED = 'REFUNDED', _('Reembolsada')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recharge_orders',
        verbose_name=_('Usuario'),
    )
    package = models.ForeignKey(
        TangasPackage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='orders',
        verbose_name=_('Paquete'),
    )
    tangas_amount = models.PositiveIntegerField(default=0, verbose_name=_('Cantidad de Tangas'))
    amount_eur = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        verbose_name=_('Importe (EUR)'),
    )
    currency = models.CharField(max_length=3, default='EUR', verbose_name=_('Moneda'))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_('Estado'),
    )
    gateway = models.CharField(max_length=50, default='dummy', verbose_name=_('Pasarela'))
    gateway_order_id = models.CharField(
        max_length=128,
        blank=True,
        db_index=True,
        verbose_name=_('Referencia externa'),
    )
    error_message = models.TextField(blank=True, verbose_name=_('Mensaje de error'))
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Pagada en'))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Orden de recarga')
        verbose_name_plural = _('Ordenes de recarga')

    def __str__(self):
        return f"{self.user.username} · {self.tangas_amount} T · {self.amount_eur:.2f} {self.currency} ({self.get_status_display()})"


class WebhookLog(models.Model):
    gateway = models.CharField(max_length=50, verbose_name=_('Pasarela'))
    payload = models.JSONField(default=dict, blank=True, verbose_name=_('Carga útil'))
    status = models.CharField(max_length=20, default='received', verbose_name=_('Estado'))
    error_message = models.TextField(blank=True, verbose_name=_('Mensaje de error'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Registro de webhook')
        verbose_name_plural = _('Registros de webhook')

    def __str__(self):
        return f"{self.gateway} · {self.status} · {self.created_at}"


class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)
    recharge_order = models.ForeignKey(
        RechargeOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transactions',
        verbose_name=_('Orden de recarga'),
    )

    def __str__(self):
        return f"{self.user.username}: {self.amount}"
