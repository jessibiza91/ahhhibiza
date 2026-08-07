from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from apps.ads.models import Ad
from apps.accounts.models import CustomUser, FavoriteAd, Profile


def health(request):
    return JsonResponse({'status': 'ok'})

def home(request):
    ads = (
        Ad.objects
        .filter(status=Ad.Status.ACTIVE, trashed_at__isnull=True, owner__trashed_at__isnull=True)
        .select_related('owner__profile', 'promotion_product')
        .prefetch_related('gallery', 'services')
    )

    query = request.GET.get('q', '').strip()[:100]
    selected_zone = request.GET.get('zone', '').strip()

    if query:
        ads = ads.filter(
            Q(title__icontains=query)
            | Q(public_description__icontains=query)
            | Q(services__name__icontains=query)
            | Q(owner__username__icontains=query)
        )

    valid_zones = {value for value, _label in Profile.MUNICIPIOS}
    if selected_zone in valid_zones:
        ads = ads.filter(owner__profile__zone=selected_zone)
    else:
        selected_zone = ''

    ads = ads.distinct().order_by('-promotion_product__priority_weight', '-created_at')

    favorite_ids = set()
    if request.user.is_authenticated and request.user.type == CustomUser.Types.CLIENT:
        favorite_ids = set(FavoriteAd.objects.filter(user=request.user).values_list('ad_id', flat=True))

    return render(request, 'home.html', {
        'services': ads,
        'favorite_ids': favorite_ids,
        'zones': Profile.MUNICIPIOS,
        'query': query,
        'selected_zone': selected_zone,
        'filters_active': bool(query or selected_zone),
    })
