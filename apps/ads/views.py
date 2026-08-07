from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, F, Q
from django.core.files import File
from .models import Ad, AdImage, PromotionProduct, ServiceTag
from .forms import AdForm, ControlAdForm, PromotionProductForm, ServiceTagForm
from apps.accounts.models import CustomUser, FavoriteAd, ProfileMedia
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST


def copy_profile_media_to_ad(ad, media_id, is_private):
    media = get_object_or_404(ProfileMedia, id=media_id, profile__user=ad.owner, is_video=False)
    if not media.file:
        return
    media.file.open('rb')
    try:
        ad_image = AdImage(ad=ad, is_private=is_private)
        ad_image.image.save(media.file.name.split('/')[-1], File(media.file), save=True)
    finally:
        media.file.close()

def ad_detail(request, ad_id):
    ad = get_object_or_404(
        Ad.objects.select_related('owner__profile').prefetch_related('gallery', 'services'),
        id=ad_id,
        trashed_at__isnull=True,
        owner__trashed_at__isnull=True,
    )
    
    # Increment Profile Visits (if not owner)
    if not request.user.is_authenticated or request.user != ad.owner:
        ad.owner.profile.profile_visits = F('profile_visits') + 1
        ad.owner.profile.save(update_fields=['profile_visits'])

    # Curiosity Wall Logic
    can_view_private = False
    
    # 1. Base Access (Registered Users)
    if request.user.is_authenticated:
        if request.user.type in [CustomUser.Types.CLIENT, CustomUser.Types.PROFESSIONAL] or request.user.is_superuser:
            can_view_private = True
            
    # 2. CRITICAL: Owner Vision - Owner sees everything
    if request.user.is_authenticated and (request.user == ad.owner or request.user.is_superuser):
        can_view_private = True

    is_favorite = False
    if request.user.is_authenticated and request.user.type == CustomUser.Types.CLIENT:
        is_favorite = FavoriteAd.objects.filter(user=request.user, ad=ad).exists()
            
    context = {
        'ad': ad,
        'can_view_private': can_view_private,
        'is_favorite': is_favorite,
    }
    return render(request, 'ads/ad_detail.html', context)

@login_required
def ad_create(request):
    if request.user.type != CustomUser.Types.PROFESSIONAL:
        return redirect('user_dispatch')

    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.owner = request.user
            ad.save()
            form.save_m2m()
            
            # Handle Public Media (is_private=False)
            for f in form.cleaned_data['public_media']:
                AdImage.objects.create(ad=ad, image=f, is_private=False)

            # Handle Hot Media (is_private=True)
            for f in form.cleaned_data['hot_media']:
                AdImage.objects.create(ad=ad, image=f, is_private=True)
                
            if 'save_and_preview' in request.POST:
                return redirect('ad_detail', ad_id=ad.id)
            return redirect('professional_dashboard')
    else:
        form = AdForm()
    return render(request, 'ads/ad_form.html', {'form': form})

@login_required
def ad_edit(request, pk):
    if request.user.type != CustomUser.Types.PROFESSIONAL:
        return redirect('user_dispatch')

    ad = get_object_or_404(Ad.objects.prefetch_related('gallery'), pk=pk, trashed_at__isnull=True)
    if ad.owner != request.user:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES, instance=ad)
        if form.is_valid():
            form.save()
            
            # Handle Public Media
            for f in form.cleaned_data['public_media']:
                AdImage.objects.create(ad=ad, image=f, is_private=False)

            # Handle Hot Media
            for f in form.cleaned_data['hot_media']:
                AdImage.objects.create(ad=ad, image=f, is_private=True)

            if 'save_and_preview' in request.POST:
                return redirect('ad_detail', ad_id=ad.id)
            return redirect('professional_dashboard')
    else:
        form = AdForm(instance=ad)
    return render(request, 'ads/ad_form.html', {'form': form, 'ad': ad})

@login_required
@require_POST
def delete_ad_image(request, image_id):
    img = get_object_or_404(AdImage, id=image_id)
    if img.ad.owner != request.user and not request.user.is_staff:
         return JsonResponse({'status': 'error'}, status=403)
    img.send_to_trash(by_user=request.user, note='Imagen retirada de anuncio')
    if request.POST.get('from_control') and request.user.is_staff:
        messages.success(request, 'Imagen enviada a la papelera.')
        return redirect('control_media')
    return JsonResponse({'status': 'success'})


@staff_member_required
def control_promotion_products(request):
    products = PromotionProduct.objects.order_by('-is_active', '-priority_weight', 'price_tangas')
    return render(request, 'dashboard/control_promotion_products.html', {
        'products': products,
    })


@staff_member_required
def control_ads(request):
    query = request.GET.get('q', '').strip()[:100]
    status = request.GET.get('status', '').strip()
    owner_id = request.GET.get('owner', '').strip()

    ads = (
        Ad.objects
        .filter(trashed_at__isnull=True, owner__trashed_at__isnull=True)
        .select_related('owner__profile', 'promotion_product')
        .prefetch_related('gallery', 'services')
        .order_by('-updated_at')
    )

    if query:
        ads = ads.filter(
            Q(title__icontains=query)
            | Q(owner__username__icontains=query)
            | Q(public_description__icontains=query)
        )
    if status in {Ad.Status.ACTIVE, Ad.Status.CERRADO}:
        ads = ads.filter(status=status)
    else:
        status = ''
    try:
        owner_id = int(owner_id)
    except (TypeError, ValueError):
        owner_id = None
    if owner_id:
        ads = ads.filter(owner_id=owner_id)

    owners = CustomUser.objects.filter(
        type=CustomUser.Types.PROFESSIONAL,
        trashed_at__isnull=True,
    ).order_by('username')

    return render(request, 'dashboard/control_ads.html', {
        'ads': ads[:150],
        'query': query,
        'status': status,
        'owner_id': owner_id,
        'owners': owners,
        'ads_count': ads.count(),
    })


@staff_member_required
def control_service_tags(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        tag = None
        if request.POST.get('tag_id'):
            tag = get_object_or_404(ServiceTag, pk=request.POST.get('tag_id'))

        if action == 'delete' and tag:
            tag.delete()
            messages.success(request, 'Servicio eliminado de la plataforma.')
            return redirect('control_service_tags')

        form = ServiceTagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Servicio actualizado.' if tag else 'Servicio creado.',
            )
            return redirect('control_service_tags')
    else:
        form = ServiceTagForm()

    tags = ServiceTag.objects.annotate(ad_count=Count('ads')).order_by('name')
    return render(request, 'dashboard/control_service_tags.html', {
        'form': form,
        'tags': tags,
    })


@staff_member_required
def control_promotion_product_edit(request, pk=None):
    product = get_object_or_404(PromotionProduct, pk=pk) if pk else None
    saved = False

    if request.method == 'POST':
        form = PromotionProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            saved = True
    else:
        form = PromotionProductForm(instance=product)

    return render(request, 'dashboard/control_promotion_product_form.html', {
        'form': form,
        'product': product,
        'saved': saved,
    })


@staff_member_required
@require_POST
def control_promotion_product_delete(request, pk):
    product = get_object_or_404(PromotionProduct, pk=pk)
    if product.ads.exists():
        product.is_active = False
        product.save(update_fields=['is_active', 'updated_at'])
    else:
        product.delete()
    return redirect('control_promotion_products')


@staff_member_required
def control_ad_detail(request, pk):
    ad = get_object_or_404(
        Ad.objects.select_related('owner__profile', 'promotion_product').prefetch_related('gallery', 'services'),
        pk=pk,
        trashed_at__isnull=True,
    )
    saved = False

    if request.method == 'POST':
        if request.POST.get('action') == 'delete_ad':
            owner_id = ad.owner.id
            ad.send_to_trash(by_user=request.user, note='Borrado desde control de anuncio')
            return redirect('control_user_detail', user_id=owner_id)

        if request.POST.get('action') in ['attach_profile_media_public', 'attach_profile_media_private']:
            copy_profile_media_to_ad(
                ad=ad,
                media_id=request.POST.get('media_id'),
                is_private=request.POST.get('action') == 'attach_profile_media_private'
            )
            return redirect('control_ad_detail', pk=ad.id)

        form = ControlAdForm(request.POST, request.FILES, instance=ad)
        if form.is_valid():
            form.save()

            for f in form.cleaned_data['public_media']:
                AdImage.objects.create(ad=ad, image=f, is_private=False)

            for f in form.cleaned_data['hot_media']:
                AdImage.objects.create(ad=ad, image=f, is_private=True)


            if 'save_and_preview' in request.POST:
                return redirect('ad_detail', ad_id=ad.id)
            saved = True
            ad = Ad.objects.select_related('owner__profile', 'promotion_product').prefetch_related('gallery', 'services').get(pk=ad.pk)
    else:
        form = ControlAdForm(instance=ad)

    return render(request, 'dashboard/control_ad_detail.html', {
        'ad': ad,
        'form': form,
        'owner': ad.owner,
        'saved': saved,
        'public_images': ad.gallery.filter(is_private=False, trashed_at__isnull=True),
        'private_images': ad.gallery.filter(is_private=True, trashed_at__isnull=True),
        'owner_gallery': ad.owner.profile.media.filter(is_video=False, trashed_at__isnull=True).order_by('-created_at')[:24],
    })


@staff_member_required
def control_ad_create_for_user(request, user_id):
    owner = get_object_or_404(CustomUser, pk=user_id)
    ad = Ad(owner=owner)
    saved = False

    if request.method == 'POST':
        form = ControlAdForm(request.POST, request.FILES, instance=ad)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.owner = owner
            ad.save()
            form.save_m2m()

            for f in form.cleaned_data['public_media']:
                AdImage.objects.create(ad=ad, image=f, is_private=False)

            for f in form.cleaned_data['hot_media']:
                AdImage.objects.create(ad=ad, image=f, is_private=True)


            if 'save_and_preview' in request.POST:
                return redirect('ad_detail', ad_id=ad.id)
            return redirect('control_ad_detail', pk=ad.id)
    else:
        form = ControlAdForm(instance=ad)

    return render(request, 'dashboard/control_ad_detail.html', {
        'ad': ad,
        'form': form,
        'owner': owner,
        'saved': saved,
        'public_images': [],
        'private_images': [],
        'is_create': True,
        'owner_gallery': owner.profile.media.filter(is_video=False, trashed_at__isnull=True).order_by('-created_at')[:24],
    })

@login_required
@require_POST
def ad_delete(request, pk):
    if request.user.type != CustomUser.Types.PROFESSIONAL:
        return redirect('user_dispatch')

    ad = get_object_or_404(Ad, pk=pk, trashed_at__isnull=True)
    if ad.owner != request.user:
        return HttpResponseForbidden()
    
    ad.send_to_trash(by_user=request.user, note='Borrado por profesional')
    return redirect('professional_dashboard')
