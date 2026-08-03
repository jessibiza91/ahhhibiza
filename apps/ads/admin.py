from django.contrib import admin

from .models import Ad, AdImage, PromotionProduct, ServiceTag


def image_size_mb(image_field):
    if not image_field:
        return 0
    try:
        return image_field.size / (1024 * 1024)
    except OSError:
        return 0


class AdImageInline(admin.TabularInline):
    model = AdImage
    extra = 0
    readonly_fields = ("created_at", "size_mb")
    fields = ("image", "is_private", "size_mb", "created_at")

    @admin.display(description="MB")
    def size_mb(self, obj):
        return f"{image_size_mb(obj.image):.2f}"


@admin.action(description="Activar anuncios seleccionados")
def activate_ads(modeladmin, request, queryset):
    queryset.update(status=Ad.Status.ACTIVE)


@admin.action(description="Cerrar anuncios seleccionados")
def close_ads(modeladmin, request, queryset):
    queryset.update(status=Ad.Status.CERRADO)


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    inlines = (AdImageInline,)
    list_display = (
        "title",
        "owner",
        "promotion_product",
        "status",
        "price_tangas",
        "gallery_count",
        "private_gallery_count",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "services", "created_at", "updated_at")
    search_fields = ("title", "owner__username", "owner__email", "public_description", "hot_description")
    filter_horizontal = ("services",)
    actions = (activate_ads, close_ads)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Imagenes")
    def gallery_count(self, obj):
        return obj.gallery.filter(trashed_at__isnull=True).count()

    @admin.display(description="HOT")
    def private_gallery_count(self, obj):
        return obj.gallery.filter(is_private=True, trashed_at__isnull=True).count()

    def delete_model(self, request, obj):
        obj.send_to_trash(by_user=request.user, note="Enviado a papelera desde Django Admin")

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.send_to_trash(by_user=request.user, note="Enviado a papelera desde Django Admin")


@admin.register(AdImage)
class AdImageAdmin(admin.ModelAdmin):
    list_display = ("ad", "is_private", "size_mb", "created_at")
    list_filter = ("is_private", "created_at")
    search_fields = ("ad__title", "ad__owner__username", "image")
    readonly_fields = ("created_at", "size_mb")

    @admin.display(description="MB")
    def size_mb(self, obj):
        return f"{image_size_mb(obj.image):.2f}"

    def delete_model(self, request, obj):
        obj.send_to_trash(by_user=request.user, note="Enviado a papelera desde Django Admin")

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.send_to_trash(by_user=request.user, note="Enviado a papelera desde Django Admin")


@admin.register(ServiceTag)
class ServiceTagAdmin(admin.ModelAdmin):
    list_display = ("name", "ads_count")
    search_fields = ("name",)

    @admin.display(description="Anuncios")
    def ads_count(self, obj):
        return obj.ads.count()


@admin.register(PromotionProduct)
class PromotionProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price_tangas", "visibility", "priority_weight", "duration_days", "is_active", "updated_at")
    list_filter = ("visibility", "is_active")
    search_fields = ("name", "description")
