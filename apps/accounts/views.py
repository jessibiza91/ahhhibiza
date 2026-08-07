import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from django.conf import settings
from .forms import ClientSignUpForm, ProfessionalSignUpForm, ProfileForm, ControlUserForm, ControlProfileForm, ManualTangaRechargeForm, SiteConfigurationForm
from .media_validators import validate_uploaded_file
from .models import CustomUser, FavoriteAd, Profile, ProfileMedia, SiteConfiguration
from .utils import safe_file_size
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from apps.ads.models import Ad, AdImage, PromotionProduct
from apps.payments.models import Transaction

logger = logging.getLogger(__name__)

# ... (Previous register views) ...

def register_selector(request):
    return render(request, 'registration/signup_selection.html')

class RateLimitedLoginView(LoginView):
    template_name = 'registration/login.html'

    @method_decorator(ratelimit(key='ip', rate=settings.AHHH_AUTH_RATE, method='POST', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

@ratelimit(key='ip', rate=settings.AHHH_AUTH_RATE, method='POST', block=True)
def client_register(request):
    if request.method == 'POST':
        form = ClientSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('user_dispatch')
    else:
        form = ClientSignUpForm()
    return render(request, 'registration/signup_form.html', {'form': form, 'user_type': 'Cliente'})

@ratelimit(key='ip', rate=settings.AHHH_AUTH_RATE, method='POST', block=True)
def professional_register(request):
    if request.method == 'POST':
        form = ProfessionalSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('user_dispatch')
    else:
        form = ProfessionalSignUpForm()
    return render(request, 'registration/signup_form.html', {'form': form, 'user_type': 'Profesional'})

def user_dispatch(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.user.is_superuser:
        return redirect('control_panel')

    if request.user.type == CustomUser.Types.PROFESSIONAL:
        return redirect('professional_dashboard')
    else:
        return redirect('client_dashboard')


@login_required
def client_dashboard(request):
    if request.user.is_superuser:
        return redirect('control_panel')

    if request.user.type != CustomUser.Types.CLIENT:
        return redirect('professional_dashboard')

    favorites = (
        FavoriteAd.objects
        .filter(user=request.user, ad__trashed_at__isnull=True, ad__owner__trashed_at__isnull=True)
        .select_related('ad__owner__profile', 'ad__promotion_product')
        .prefetch_related('ad__gallery')
    )
    active_ads = (
        Ad.objects
        .filter(status=Ad.Status.ACTIVE, trashed_at__isnull=True, owner__trashed_at__isnull=True)
        .select_related('owner__profile', 'promotion_product')
        .prefetch_related('gallery')
        .order_by('-promotion_product__priority_weight', '-created_at')[:12]
    )
    favorite_ids = set(favorites.values_list('ad_id', flat=True))

    return render(request, 'dashboard/client_home.html', {
        'favorites': favorites,
        'active_ads': active_ads,
        'favorite_ids': favorite_ids,
    })


@login_required
@require_POST
def toggle_favorite_ad(request, ad_id):
    if request.user.is_superuser:
        return redirect('ad_detail', ad_id=ad_id)

    if request.user.type != CustomUser.Types.CLIENT:
        return redirect('ad_detail', ad_id=ad_id)

    ad = get_object_or_404(Ad, id=ad_id, trashed_at__isnull=True, owner__trashed_at__isnull=True)
    favorite, created = FavoriteAd.objects.get_or_create(user=request.user, ad=ad)
    if not created:
        favorite.delete()

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('ad_detail', ad_id=ad.id)

def professional_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # ROLE SECURITY: Redirect Clients to Home
    if request.user.type != CustomUser.Types.PROFESSIONAL:
        return redirect('home')
        
    # ROBUSTNESS: Ensure Profile Exists (Fix for Pamela/Legacy users)
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    # Ads Logic
    services = request.user.ads.filter(trashed_at__isnull=True).select_related('promotion_product').prefetch_related('gallery') # using related_name='ads' from Ad model
    visits = profile.profile_visits
    admirer_favorites = (
        FavoriteAd.objects
        .filter(ad__owner=request.user, user__trashed_at__isnull=True)
        .select_related('user__profile', 'ad')
        .order_by('-created_at')
    )
    admirer_count = admirer_favorites.values('user_id').distinct().count()

    checklist = [
        {
            'label': 'Foto de perfil',
            'done': bool(profile.avatar),
            'url': 'profile_edit',
            'icon': 'fa-user-circle',
        },
        {
            'label': 'Descripcion y datos basicos',
            'done': bool(profile.bio and profile.birth_date and profile.zone),
            'url': 'profile_edit',
            'icon': 'fa-id-card',
        },
        {
            'label': 'Contacto directo',
            'done': bool(request.user.phone_call_url or request.user.whatsapp_url or request.user.telegram_url),
            'url': 'profile_edit',
            'icon': 'fa-phone',
        },
        {
            'label': 'Galeria profesional',
            'done': profile.media.filter(trashed_at__isnull=True).exists(),
            'url': 'profile_edit',
            'icon': 'fa-images',
        },
        {
            'label': 'Primer anuncio publicado',
            'done': services.exists(),
            'url': 'ad_create',
            'icon': 'fa-bullhorn',
        },
    ]
    completed_steps = sum(1 for item in checklist if item['done'])
    profile_progress = int((completed_steps / len(checklist)) * 100)
    next_step = next((item for item in checklist if not item['done']), None)
    
    return render(request, 'dashboard/professional_home.html', {
        'services': services,
        'visits': visits,
        'profile': profile,
        'checklist': checklist,
        'completed_steps': completed_steps,
        'profile_progress': profile_progress,
        'next_step': next_step,
        'admirer_count': admirer_count,
        'recent_admirers': admirer_favorites[:4],
    })


@login_required
def professional_wallet(request):
    if request.user.type != CustomUser.Types.PROFESSIONAL:
        return redirect('user_dispatch')

    transactions = request.user.transactions.order_by('-timestamp')[:30]
    products = PromotionProduct.objects.filter(is_active=True).order_by(
        'price_tangas',
        '-priority_weight',
    )
    return render(request, 'dashboard/professional_wallet.html', {
        'transactions': transactions,
        'products': products,
    })


@login_required
def professional_favorite_clients(request):
    if request.user.type != CustomUser.Types.PROFESSIONAL:
        return redirect('user_dispatch')

    favorites = (
        FavoriteAd.objects
        .filter(ad__owner=request.user, user__trashed_at__isnull=True)
        .select_related('user__profile', 'ad')
        .prefetch_related('user__profile__media')
        .order_by('-created_at')
    )

    client_cards = {}
    for favorite in favorites:
        client = favorite.user
        if client.id not in client_cards:
            profile, _ = Profile.objects.get_or_create(user=client)
            client_cards[client.id] = {
                'client': client,
                'profile': profile,
                'favorites': [],
                'media': profile.media.filter(trashed_at__isnull=True).order_by('-created_at')[:6],
            }
        client_cards[client.id]['favorites'].append(favorite)

    return render(request, 'dashboard/professional_favorite_clients.html', {
        'client_cards': client_cards.values(),
        'favorites_count': favorites.count(),
    })


@staff_member_required
def control_panel(request):
    professionals = CustomUser.objects.filter(type=CustomUser.Types.PROFESSIONAL, trashed_at__isnull=True).select_related('profile').prefetch_related('ads', 'profile__media')
    clients = CustomUser.objects.filter(type=CustomUser.Types.CLIENT, is_superuser=False, trashed_at__isnull=True)
    ads = Ad.objects.filter(trashed_at__isnull=True, owner__trashed_at__isnull=True).select_related('owner__profile', 'promotion_product').prefetch_related('gallery').order_by('-updated_at')

    total_media = ProfileMedia.objects.filter(trashed_at__isnull=True).count() + AdImage.objects.filter(trashed_at__isnull=True).count()
    active_ads = ads.filter(status=Ad.Status.ACTIVE).count()
    closed_ads = ads.filter(status=Ad.Status.CERRADO).count()
    recent_users = CustomUser.objects.filter(is_superuser=False, trashed_at__isnull=True).order_by('-date_joined')[:6]
    recent_ads = ads[:6]
    recent_transactions = Transaction.objects.select_related('user').order_by('-timestamp')[:6]

    professional_cards = []
    for user in professionals:
        profile = getattr(user, 'profile', None)
        media_count = profile.media.filter(trashed_at__isnull=True).count() if profile else 0
        ads_count = user.ads.filter(trashed_at__isnull=True).count()
        has_contact = bool(user.phone_call_url or user.whatsapp_url or user.telegram_url)
        professional_cards.append({
            'user': user,
            'profile': profile,
            'media_count': media_count,
            'ads_count': ads_count,
            'has_contact': has_contact,
        })

    return render(request, 'dashboard/control_panel.html', {
        'professionals_count': professionals.count(),
        'clients_count': clients.count(),
        'ads_count': ads.count(),
        'active_ads': active_ads,
        'closed_ads': closed_ads,
        'total_media': total_media,
        'professional_cards': professional_cards,
        'recent_users': recent_users,
        'recent_ads': recent_ads,
        'recent_transactions': recent_transactions,
    })


@staff_member_required
def control_professionals(request):
    professionals = (
        CustomUser.objects
        .filter(type=CustomUser.Types.PROFESSIONAL, trashed_at__isnull=True)
        .select_related('profile')
        .prefetch_related('ads', 'profile__media')
        .order_by('username')
    )

    professional_cards = []
    for user in professionals:
        profile = getattr(user, 'profile', None)
        media_count = profile.media.filter(trashed_at__isnull=True).count() if profile else 0
        active_ads_count = user.ads.filter(status=Ad.Status.ACTIVE, trashed_at__isnull=True).count()
        closed_ads_count = user.ads.filter(status=Ad.Status.CERRADO, trashed_at__isnull=True).count()
        has_contact = bool(user.phone_call_url or user.whatsapp_url or user.telegram_url)
        has_profile = bool(profile and profile.bio and profile.avatar)

        professional_cards.append({
            'user': user,
            'profile': profile,
            'media_count': media_count,
            'active_ads_count': active_ads_count,
            'closed_ads_count': closed_ads_count,
            'ads_count': active_ads_count + closed_ads_count,
            'has_contact': has_contact,
            'has_profile': has_profile,
        })

    return render(request, 'dashboard/control_professionals.html', {
        'professional_cards': professional_cards,
        'professionals_count': professionals.count(),
    })


@staff_member_required
def control_clients(request):
    clients = (
        CustomUser.objects
        .filter(type=CustomUser.Types.CLIENT, is_superuser=False, trashed_at__isnull=True)
        .select_related('profile')
        .prefetch_related('profile__media', 'favorite_ads')
        .order_by('username')
    )

    client_cards = []
    for user in clients:
        profile = getattr(user, 'profile', None)
        media_count = profile.media.filter(trashed_at__isnull=True).count() if profile else 0
        favorites_count = user.favorite_ads.filter(ad__trashed_at__isnull=True).count()
        has_profile = bool(profile and (profile.avatar or profile.bio or media_count))
        client_cards.append({
            'user': user,
            'profile': profile,
            'media_count': media_count,
            'favorites_count': favorites_count,
            'has_profile': has_profile,
        })

    return render(request, 'dashboard/control_clients.html', {
        'client_cards': client_cards,
        'clients_count': clients.count(),
    })


@staff_member_required
def control_media(request):
    query = request.GET.get('q', '').strip()[:100]
    media_type = request.GET.get('type', '').strip()

    profile_media = (
        ProfileMedia.objects
        .filter(trashed_at__isnull=True, profile__user__trashed_at__isnull=True)
        .select_related('profile__user')
        .order_by('-created_at')
    )
    ad_images = (
        AdImage.objects
        .filter(
            trashed_at__isnull=True,
            ad__trashed_at__isnull=True,
            ad__owner__trashed_at__isnull=True,
        )
        .select_related('ad__owner')
        .order_by('-created_at')
    )

    if query:
        profile_media = profile_media.filter(profile__user__username__icontains=query)
        ad_images = ad_images.filter(
            Q(ad__owner__username__icontains=query)
            | Q(ad__title__icontains=query)
        )

    if media_type == 'profile':
        ad_images = ad_images.none()
    elif media_type == 'public':
        profile_media = profile_media.none()
        ad_images = ad_images.filter(is_private=False)
    elif media_type == 'hot':
        profile_media = profile_media.none()
        ad_images = ad_images.filter(is_private=True)
    else:
        media_type = ''

    return render(request, 'dashboard/control_media.html', {
        'profile_media_items': profile_media[:120],
        'ad_image_items': ad_images[:120],
        'query': query,
        'media_type': media_type,
        'profile_media_count': profile_media.count(),
        'ad_image_count': ad_images.count(),
    })


@staff_member_required
def control_transactions(request):
    query = request.GET.get('q', '').strip()[:100]
    transactions = Transaction.objects.select_related('user').order_by('-timestamp')
    if query:
        transactions = transactions.filter(
            Q(user__username__icontains=query)
            | Q(description__icontains=query)
        )

    totals = transactions.aggregate(total=Sum('amount'))
    return render(request, 'dashboard/control_transactions.html', {
        'transactions': transactions[:200],
        'query': query,
        'transaction_count': transactions.count(),
        'transaction_total': totals['total'] or 0,
    })


@staff_member_required
def control_site_settings(request):
    configuration = SiteConfiguration.objects.first()
    if configuration is None:
        configuration = SiteConfiguration()

    if request.method == 'POST':
        form = SiteConfigurationForm(request.POST, instance=configuration)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuracion global actualizada.')
            return redirect('control_site_settings')
    else:
        form = SiteConfigurationForm(instance=configuration)

    return render(request, 'dashboard/control_site_settings.html', {
        'form': form,
        'configuration': configuration,
    })


@staff_member_required
def control_user_detail(request, user_id):
    managed_user = get_object_or_404(
        CustomUser.objects.select_related('profile'),
        pk=user_id
    )
    profile, created = Profile.objects.get_or_create(user=managed_user)
    ads = managed_user.ads.filter(trashed_at__isnull=True).prefetch_related('gallery', 'services').order_by('-updated_at')
    transactions = managed_user.transactions.order_by('-timestamp')[:8]
    client_favorites = (
        managed_user.favorite_ads
        .filter(ad__trashed_at__isnull=True, ad__owner__trashed_at__isnull=True)
        .select_related('ad__owner__profile')
        .prefetch_related('ad__gallery')
        .order_by('-created_at')
    )

    media_items = profile.media.filter(trashed_at__isnull=True).order_by('-created_at')
    gallery_bytes = 0
    avatar_bytes = safe_file_size(profile.avatar)
    for media in media_items:
        gallery_bytes += safe_file_size(media.file)

    usage_mb = round((gallery_bytes + avatar_bytes) / (1024 * 1024), 2)
    saved = False
    media_uploaded = False
    recharge_done = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'trash_user':
            if not managed_user.is_superuser and managed_user != request.user:
                managed_user.send_to_trash(by_user=request.user, note='Enviado desde ficha de intervencion')
                for ad in managed_user.ads.filter(trashed_at__isnull=True):
                    ad.send_to_trash(by_user=request.user, note='Usuario enviado a papelera')
                return redirect('control_professionals')
        elif action == 'upload_profile_media':
            invalid_files = 0
            for uploaded_file in request.FILES.getlist('media_files'):
                try:
                    media_kind = validate_uploaded_file(uploaded_file)
                except ValidationError as exc:
                    logger.warning('Archivo rechazado en control_user_detail: %s', exc)
                    invalid_files += 1
                    continue
                ProfileMedia.objects.create(profile=profile, file=uploaded_file, is_video=media_kind == 'video')
            if invalid_files:
                messages.error(request, f'{invalid_files} archivo(s) rechazado(s): no son imagenes o videos permitidos.')
            return redirect('control_user_detail', user_id=managed_user.id)
        elif action == 'manual_tanga_recharge':
            recharge_form = ManualTangaRechargeForm(request.POST)
            user_form = ControlUserForm(instance=managed_user)
            profile_form = ControlProfileForm(instance=profile)
            if recharge_form.is_valid():
                amount = recharge_form.cleaned_data['amount']
                description = recharge_form.cleaned_data.get('description') or 'Recarga manual superadmin'
                managed_user.tangas_balance += amount
                managed_user.save(update_fields=['tangas_balance'])
                Transaction.objects.create(
                    user=managed_user,
                    amount=amount,
                    description=f"{description} · por {request.user.username}",
                )
                recharge_done = True
        else:
            user_form = ControlUserForm(request.POST, instance=managed_user)
            profile_form = ControlProfileForm(request.POST, request.FILES, instance=profile)
            recharge_form = ManualTangaRechargeForm()
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                saved = True
    else:
        user_form = ControlUserForm(instance=managed_user)
        profile_form = ControlProfileForm(instance=profile)
        recharge_form = ManualTangaRechargeForm()

    public_ad_media = AdImage.objects.filter(ad__owner=managed_user, is_private=False, trashed_at__isnull=True, ad__trashed_at__isnull=True).select_related('ad').order_by('-created_at')[:12]
    private_ad_media = AdImage.objects.filter(ad__owner=managed_user, is_private=True, trashed_at__isnull=True, ad__trashed_at__isnull=True).select_related('ad').order_by('-created_at')[:12]

    return render(request, 'dashboard/control_user_detail.html', {
        'managed_user': managed_user,
        'profile': profile,
        'user_form': user_form,
        'profile_form': profile_form,
        'ads': ads,
        'transactions': transactions,
        'client_favorites': client_favorites,
        'media_items': media_items,
        'public_ad_media': public_ad_media,
        'private_ad_media': private_ad_media,
        'usage_mb': usage_mb,
        'gallery_mb': round(gallery_bytes / (1024 * 1024), 2),
        'avatar_mb': round(avatar_bytes / (1024 * 1024), 2),
        'saved': saved,
        'media_uploaded': media_uploaded,
        'recharge_done': recharge_done,
        'recharge_form': recharge_form,
    })


@staff_member_required
@require_POST
def control_bulk_trash_users(request):
    selected_ids = request.POST.getlist('selected_users')
    users = CustomUser.objects.filter(id__in=selected_ids, is_superuser=False, trashed_at__isnull=True).exclude(id=request.user.id)
    for user_obj in users:
        user_obj.send_to_trash(by_user=request.user, note='Seleccion multiple desde panel')
        for ad in user_obj.ads.filter(trashed_at__isnull=True):
            ad.send_to_trash(by_user=request.user, note='Usuario enviado a papelera')
    return redirect('control_professionals')


def file_size_mb(file_field):
    if not file_field:
        return 0
    try:
        return file_field.size / (1024 * 1024)
    except OSError:
        return 0


def purge_user_files(user_obj):
    profile = getattr(user_obj, 'profile', None)
    if profile:
        if profile.avatar:
            profile.avatar.delete(save=False)
        for media in profile.media.filter(trashed_at__isnull=True):
            if media.file:
                media.file.delete(save=False)
    for ad in user_obj.ads.all():
        purge_ad_files(ad)


def purge_ad_files(ad):
    for image in ad.gallery.all():
        if image.image:
            image.image.delete(save=False)


def purge_profile_media(media):
    if media.file:
        media.file.delete(save=False)
    media.delete()


def purge_ad_image(image):
    if image.image:
        image.image.delete(save=False)
    image.delete()


def restore_user_and_dependent_ads(user_obj):
    dependent_ads = list(user_obj.ads.filter(
        trashed_at__isnull=False,
        trash_note='Usuario enviado a papelera',
    ))
    user_obj.restore_from_trash()
    for ad in dependent_ads:
        ad.restore_from_trash()
    return 1 + len(dependent_ads)


def restore_trash_selection(request, restore_all=False):
    restored_count = 0
    blocked_count = 0

    if restore_all:
        users = list(CustomUser.objects.filter(
            trashed_at__isnull=False,
            is_superuser=False,
        ))
        ad_ids = None
        profile_media_ids = None
        ad_image_ids = None
    else:
        user_ids = request.POST.getlist('users')
        ad_ids = request.POST.getlist('ads')
        profile_media_ids = request.POST.getlist('profile_media')
        ad_image_ids = request.POST.getlist('ad_images')

        direct_restore = {
            'restore_user': user_ids,
            'restore_ad': ad_ids,
            'restore_profile_media': profile_media_ids,
            'restore_ad_image': ad_image_ids,
        }
        for field_name, selected_ids in direct_restore.items():
            direct_id = request.POST.get(field_name)
            if direct_id:
                selected_ids.append(direct_id)

        users = list(CustomUser.objects.filter(
            id__in=user_ids,
            trashed_at__isnull=False,
            is_superuser=False,
        ))

    with transaction.atomic():
        for user_obj in users:
            restored_count += restore_user_and_dependent_ads(user_obj)

        ads = Ad.objects.filter(trashed_at__isnull=False)
        if ad_ids is not None:
            ads = ads.filter(id__in=ad_ids)
        for ad in ads.select_related('owner'):
            if ad.owner.trashed_at:
                blocked_count += 1
                continue
            ad.restore_from_trash()
            restored_count += 1

        profile_media = ProfileMedia.objects.filter(trashed_at__isnull=False)
        if profile_media_ids is not None:
            profile_media = profile_media.filter(id__in=profile_media_ids)
        for media in profile_media.select_related('profile__user'):
            if media.profile.user.trashed_at:
                blocked_count += 1
                continue
            media.restore_from_trash()
            restored_count += 1

        ad_images = AdImage.objects.filter(trashed_at__isnull=False)
        if ad_image_ids is not None:
            ad_images = ad_images.filter(id__in=ad_image_ids)
        for image in ad_images.select_related('ad__owner'):
            if image.ad.trashed_at or image.ad.owner.trashed_at:
                blocked_count += 1
                continue
            image.restore_from_trash()
            restored_count += 1

    return restored_count, blocked_count


@staff_member_required
def control_trash(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        is_direct_restore = any(request.POST.get(field_name) for field_name in (
            'restore_user',
            'restore_ad',
            'restore_profile_media',
            'restore_ad_image',
        ))

        if action in {'restore_selected', 'restore_all'} or is_direct_restore:
            restored_count, blocked_count = restore_trash_selection(
                request,
                restore_all=action == 'restore_all',
            )
            if restored_count:
                messages.success(
                    request,
                    f'{restored_count} elemento(s) restaurado(s). Los anuncios quedan cerrados hasta su revision.',
                )
            if blocked_count:
                messages.warning(
                    request,
                    f'{blocked_count} elemento(s) no se restauraron porque dependen de un perfil o anuncio que sigue en papelera.',
                )
            if not restored_count and not blocked_count:
                messages.info(request, 'Selecciona al menos un elemento para restaurar.')
            return redirect('control_trash')

        if action == 'purge_all':
            users = list(CustomUser.objects.filter(trashed_at__isnull=False, is_superuser=False))
            user_ids = [user_obj.id for user_obj in users]
            ads = list(Ad.objects.filter(trashed_at__isnull=False).exclude(owner_id__in=user_ids))
            ad_ids = [ad.id for ad in ads]
            profile_media = list(ProfileMedia.objects.filter(trashed_at__isnull=False).exclude(profile__user_id__in=user_ids))
            ad_images = list(AdImage.objects.filter(trashed_at__isnull=False).exclude(ad_id__in=ad_ids).exclude(ad__owner_id__in=user_ids))
        else:
            users = list(CustomUser.objects.filter(id__in=request.POST.getlist('users'), trashed_at__isnull=False, is_superuser=False))
            user_ids = [user_obj.id for user_obj in users]
            ads = list(Ad.objects.filter(id__in=request.POST.getlist('ads'), trashed_at__isnull=False).exclude(owner_id__in=user_ids))
            ad_ids = [ad.id for ad in ads]
            profile_media = list(ProfileMedia.objects.filter(id__in=request.POST.getlist('profile_media'), trashed_at__isnull=False).exclude(profile__user_id__in=user_ids))
            ad_images = list(AdImage.objects.filter(id__in=request.POST.getlist('ad_images'), trashed_at__isnull=False).exclude(ad_id__in=ad_ids).exclude(ad__owner_id__in=user_ids))

        for user_obj in users:
            purge_user_files(user_obj)
            user_obj.delete()
        for ad in ads:
            purge_ad_files(ad)
            ad.delete()
        for media in profile_media:
            purge_profile_media(media)
        for image in ad_images:
            purge_ad_image(image)
        messages.success(request, 'Los elementos seleccionados se eliminaron definitivamente.')
        return redirect('control_trash')

    trashed_users = CustomUser.objects.filter(trashed_at__isnull=False).select_related('trashed_by', 'profile').order_by('-trashed_at')
    trashed_ads = Ad.objects.filter(trashed_at__isnull=False).select_related('owner', 'trashed_by').order_by('-trashed_at')
    trashed_profile_media = ProfileMedia.objects.filter(trashed_at__isnull=False).select_related('profile__user', 'trashed_by').order_by('-trashed_at')
    trashed_ad_images = AdImage.objects.filter(trashed_at__isnull=False).select_related('ad__owner', 'trashed_by').order_by('-trashed_at')

    trash_mb = 0
    for user_obj in trashed_users:
        profile = getattr(user_obj, 'profile', None)
        if profile:
            trash_mb += file_size_mb(profile.avatar)
            for media in profile.media.all():
                trash_mb += file_size_mb(media.file)
        for ad in user_obj.ads.all():
            for image in ad.gallery.all():
                trash_mb += file_size_mb(image.image)
    for media in trashed_profile_media:
        trash_mb += file_size_mb(media.file)
    for image in trashed_ad_images:
        trash_mb += file_size_mb(image.image)

    return render(request, 'dashboard/control_trash.html', {
        'trashed_users': trashed_users,
        'trashed_ads': trashed_ads,
        'trashed_profile_media': trashed_profile_media,
        'trashed_ad_images': trashed_ad_images,
        'trash_mb': round(trash_mb, 2),
        'trash_count': trashed_users.count() + trashed_ads.count() + trashed_profile_media.count() + trashed_ad_images.count(),
    })

def profile_edit(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    # Calculate Storage Usage for Context
    gallery_bytes = 0
    avatar_bytes = safe_file_size(profile.avatar)
    for media in profile.media.all():
        gallery_bytes += safe_file_size(media.file)
    
    total_bytes = gallery_bytes + avatar_bytes
    total_mb = total_bytes / (1024 * 1024)
    gallery_mb = gallery_bytes / (1024 * 1024)
    avatar_mb = avatar_bytes / (1024 * 1024)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # ---------------------------------------------------------
        # FLOW A: AUTO-UPLOAD (ZERO-CLICK)
        # ---------------------------------------------------------
        if action == 'auto_upload_media':
            # Skip Standard Form Validation (Bio, etc.) to allow quick upload.
            uploaded_count = 0
            skipped_count = 0
            invalid_count = 0

            for f in request.FILES.getlist('media_files'):
                try:
                    media_kind = validate_uploaded_file(f)
                except ValidationError as exc:
                    logger.warning('Archivo rechazado en auto-upload: %s', exc)
                    invalid_count += 1
                    continue

                # Quick Quota Check
                current_usage = sum(
                    safe_file_size(m.file)
                    for m in profile.media.filter(trashed_at__isnull=True)
                )
                current_usage += safe_file_size(profile.avatar)

                if (current_usage + f.size) <= (35 * 1024 * 1024):
                    ProfileMedia.objects.create(profile=profile, file=f, is_video=media_kind == 'video')
                    uploaded_count += 1
                else:
                    skipped_count += 1

            if uploaded_count:
                messages.success(request, f'{uploaded_count} archivo(s) subido(s) a tu galeria.')
            if skipped_count:
                messages.warning(request, 'Algunos archivos superan la cuota de 35 MB y no se subieron.')
            if invalid_count:
                messages.error(request, f'{invalid_count} archivo(s) no son imagenes o videos permitidos y no se subieron.')

            return redirect('profile_edit')

        # ---------------------------------------------------------
        # FLOW B: STANDARD SAVE (Bio, Dates, etc.)
        # ---------------------------------------------------------
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            if request.user.type == CustomUser.Types.CLIENT:
                return redirect('client_dashboard')
            return redirect('professional_dashboard')
    else:
        form = ProfileForm(instance=profile)
    
    return render(request, 'accounts/profile_form.html', {
        'form': form, 
        'profile': profile,
        'profile_media': profile.media.filter(trashed_at__isnull=True).order_by('-created_at'),
        'usage_mb': round(total_mb, 2),
        'gallery_mb': round(gallery_mb, 2),
        'avatar_mb': round(avatar_mb, 2),
        'is_client_profile': request.user.type == CustomUser.Types.CLIENT,
    })

@login_required
@require_POST
def delete_profile_media(request, media_id):
    media = get_object_or_404(ProfileMedia, id=media_id)
    # Security Check
    if media.profile.user != request.user and not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    media.send_to_trash(by_user=request.user, note='Eliminado desde galeria de perfil')
    if request.POST.get('from_control') and request.user.is_staff:
        messages.success(request, 'Material enviado a la papelera.')
        return redirect('control_media')
    return JsonResponse({'status': 'success'})
