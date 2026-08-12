from django.contrib import admin

from .models import RechargeOrder, TangasPackage, Transaction, WebhookLog


@admin.register(TangasPackage)
class TangasPackageAdmin(admin.ModelAdmin):
    list_display = ("name", "tangas_amount", "price_eur", "is_active", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    list_editable = ("price_eur", "tangas_amount", "is_active", "sort_order")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Datos del paquete",
            {
                "description": (
                    "Aqui puedes crear o modificar los paquetes de Tangas que los "
                    "profesionales ven en su cartera. 'Cantidad de Tangas' es lo que "
                    "recibira el usuario al pagar, y 'Precio (EUR)' es lo que se le "
                    "cobra. Marca 'Activo' para que el paquete se vea en la web y "
                    "recuerda pulsar 'Guardar'."
                ),
                "fields": ("name", "tangas_amount", "price_eur", "is_active", "sort_order"),
            },
        ),
        (
            "Fechas",
            {
                "description": "Estos datos se rellenan solos y son solo informativos.",
                "fields": ("created_at", "updated_at"),
            },
        ),
    )


@admin.register(RechargeOrder)
class RechargeOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "package",
        "tangas_amount",
        "amount_eur",
        "currency",
        "status",
        "gateway",
        "paid_at",
        "created_at",
    )
    list_filter = ("status", "gateway", "currency", "created_at")
    search_fields = ("id", "user__username", "user__email", "gateway_order_id")
    list_select_related = ("user", "package")
    readonly_fields = (
        "user",
        "package",
        "tangas_amount",
        "amount_eur",
        "currency",
        "status",
        "gateway",
        "gateway_order_id",
        "error_message",
        "created_at",
        "paid_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Informacion de la recarga",
            {
                "description": (
                    "Aqui ves cada recarga que un profesional intento pagar. No hace falta "
                    "tocar nada: estos datos se generan solos cuando alguien paga. Sirve "
                    "para consultar en que estado quedo cada pago y, si hay un problema, "
                    "para saber cual fue el motivo."
                ),
                "fields": readonly_fields,
            },
        ),
    )


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ("gateway", "status", "created_at")
    list_filter = ("gateway", "status", "created_at")
    search_fields = ("payload", "error_message")
    readonly_fields = ("gateway", "payload", "status", "error_message", "created_at")
    fieldsets = (
        (
            "Registro tecnico",
            {
                "description": (
                    "Estos son avisos internos automaticos que envia la pasarela de pago. "
                    "Son de consulta tecnica y normalmente puedes ignorarlos: solo sirven "
                    "para comprobar si un pago llego bien, fallo o fue rechazado."
                ),
                "fields": readonly_fields,
            },
        ),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "description", "timestamp")
    list_filter = ("timestamp",)
    search_fields = ("user__username", "user__email", "description")
    readonly_fields = ("timestamp",)
