from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, FavoriteAd, Profile, ProfileMedia, SiteConfiguration


def file_size_mb(file_field):
    if not file_field:
        return 0
    try:
        return file_field.size / (1024 * 1024)
    except OSError:
        return 0


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    fk_name = "user"
    fields = (
        "avatar",
        "bio",
        "zone",
        "origin",
        "birth_date",
        "instagram_url",
        "facebook_url",
        "twitter_url",
        "profile_visits",
    )


@admin.action(description="Marcar seleccionados como profesionales")
def mark_as_professional(modeladmin, request, queryset):
    queryset.update(type=CustomUser.Types.PROFESSIONAL)


@admin.action(description="Marcar seleccionados como clientes")
def mark_as_client(modeladmin, request, queryset):
    queryset.update(type=CustomUser.Types.CLIENT)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "type",
        "tangas_balance",
        "phone",
        "whatsapp_id",
        "telegram_id",
        "ads_count",
        "media_count",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = ("type", "is_active", "is_staff", "is_superuser", "date_joined")
    search_fields = ("username", "email", "phone", "whatsapp_id", "telegram_id")
    actions = (mark_as_professional, mark_as_client)
    fieldsets = UserAdmin.fieldsets + (
        (
            "Ahhh! Ibiza",
            {
                "fields": (
                    "type",
                    "tangas_balance",
                    "phone",
                    "whatsapp_id",
                    "telegram_id",
                    "legal_terms_accepted",
                )
            },
        ),
    )

    @admin.display(description="Anuncios")
    def ads_count(self, obj):
        return obj.ads.count()

    @admin.display(description="Media perfil")
    def media_count(self, obj):
        profile = getattr(obj, "profile", None)
        if not profile:
            return 0
        return profile.media.filter(trashed_at__isnull=True).count()

    def delete_model(self, request, obj):
        if obj.is_superuser:
            return
        obj.send_to_trash(by_user=request.user, note="Enviado a papelera desde Django Admin")

    def delete_queryset(self, request, queryset):
        for obj in queryset.filter(is_superuser=False):
            obj.send_to_trash(by_user=request.user, note="Enviado a papelera desde Django Admin")


class ProfileMediaInline(admin.TabularInline):
    model = ProfileMedia
    extra = 0
    readonly_fields = ("created_at", "size_mb")
    fields = ("file", "is_video", "size_mb", "created_at")

    @admin.display(description="MB")
    def size_mb(self, obj):
        return f"{file_size_mb(obj.file):.2f}"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    inlines = (ProfileMediaInline,)
    list_display = (
        "user",
        "zone",
        "origin",
        "age",
        "profile_visits",
        "media_count",
        "storage_mb",
    )
    list_filter = ("zone", "origin")
    search_fields = ("user__username", "user__email", "bio")
    readonly_fields = ("profile_visits", "storage_mb")

    @admin.display(description="Edad")
    def age(self, obj):
        return obj.get_age() or "-"

    @admin.display(description="Media")
    def media_count(self, obj):
        return obj.media.filter(trashed_at__isnull=True).count()

    @admin.display(description="Almacenamiento MB")
    def storage_mb(self, obj):
        total = file_size_mb(obj.avatar)
        for media in obj.media.all():
            total += file_size_mb(media.file)
        return f"{total:.2f}"


@admin.register(ProfileMedia)
class ProfileMediaAdmin(admin.ModelAdmin):
    list_display = ("profile", "is_video", "size_mb", "created_at")
    list_filter = ("is_video", "created_at")
    search_fields = ("profile__user__username", "file")
    readonly_fields = ("created_at", "size_mb")

    @admin.display(description="MB")
    def size_mb(self, obj):
        return f"{file_size_mb(obj.file):.2f}"

    def delete_model(self, request, obj):
        obj.send_to_trash(by_user=request.user, note="Enviado a papelera desde Django Admin")

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.send_to_trash(by_user=request.user, note="Enviado a papelera desde Django Admin")


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ("support_email", "maintenance_mode")


@admin.register(FavoriteAd)
class FavoriteAdAdmin(admin.ModelAdmin):
    list_display = ("user", "ad", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "user__email", "ad__title", "ad__owner__username")
    readonly_fields = ("created_at",)
