import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import CustomUser

from .models import Ad, PromotionProduct

logger = logging.getLogger(__name__)


def daily_cost(ad):
    """Coste diario en Tangas del plan asociado a un anuncio (0 sin plan)."""
    product = ad.promotion_product
    return product.price_tangas if product else 0


def get_basic_product():
    """Plan 'Basico' activo (coste 0). Devuelve None si no existe.

    Sirve para degradar un anuncio que no puede pagar su plan.
    """
    return PromotionProduct.objects.filter(
        is_active=True,
        visibility=PromotionProduct.Visibility.BASIC,
        price_tangas=0,
    ).order_by('-priority_weight', 'pk').first()


def downgrade_to_basic(ad, charged_at=None):
    """Devuelve el anuncio al estado basico: plan Basico (o sin plan) y coste 0.

    No toca status (el anuncio sigue activo) ni updated_at (evita reordenar
    los listados que ordenan por esa fecha).
    """
    basic = get_basic_product()
    ad.promotion_product = basic
    ad.price_tangas = 0
    if charged_at is not None:
        ad.last_tangas_charged_at = charged_at
        ad.save(update_fields=['promotion_product', 'price_tangas', 'last_tangas_charged_at'])
    else:
        ad.save(update_fields=['promotion_product', 'price_tangas'])


def charge_daily_tangas(for_date=None, dry_run=False):
    """Cobra el coste diario del plan a cada anuncio activo con plan de pago.

    Un anuncio se cobra una sola vez por fecha (last_tangas_charged_at). Si el
    saldo del propietario no alcanza para el dia, el anuncio se degrada al plan
    basico en lugar de dejar saldo negativo. Los anuncios exentos de cobro de
    Tangas (tangas_charge_exempt=True) se ignoran aunque tengan plan de pago:
    no se cobran ni se degradan y no cuentan en el resumen.

    Devuelve un resumen con el recuento de cargados/degradados y el detalle de
    cada anuncio (id, titulo, accion e importe) para informar.
    """
    if for_date is None:
        for_date = timezone.localdate()

    ads = (
        Ad.objects
        .filter(
            status=Ad.Status.ACTIVE,
            trashed_at__isnull=True,
            owner__trashed_at__isnull=True,
            promotion_product__isnull=False,
            promotion_product__price_tangas__gt=0,
            tangas_charge_exempt=False,
        )
        .filter(
            Q(last_tangas_charged_at__isnull=True)
            | Q(last_tangas_charged_at__lt=for_date)
        )
        .select_related('owner', 'promotion_product')
        .order_by('pk')
    )

    charged = 0
    downgraded = 0
    details = []

    for ad in ads:
        cost = daily_cost(ad)
        if dry_run:
            if ad.owner.tangas_balance >= cost:
                charged += 1
                details.append((ad.pk, ad.title, 'cobrar', cost))
            else:
                downgraded += 1
                details.append((ad.pk, ad.title, 'degradar', cost))
            continue

        with transaction.atomic():
            owner = CustomUser.objects.select_for_update().get(pk=ad.owner_id)
            if owner.tangas_balance >= cost:
                owner.tangas_balance -= cost
                owner.save(update_fields=['tangas_balance'])
                ad.last_tangas_charged_at = for_date
                ad.save(update_fields=['last_tangas_charged_at'])
                charged += 1
                details.append((ad.pk, ad.title, 'cobrar', cost))
                logger.info(
                    'Cargo diario de %s T al anuncio %s (%s, dia %s)',
                    cost, ad.pk, ad.owner.username, for_date,
                )
            else:
                downgrade_to_basic(ad, charged_at=for_date)
                downgraded += 1
                details.append((ad.pk, ad.title, 'degradar', cost))
                logger.warning(
                    'Saldo insuficiente en %s (%s T): anuncio %s degradado a basico',
                    ad.owner.username, ad.owner.tangas_balance, ad.pk,
                )

    return {
        'date': for_date,
        'charged': charged,
        'downgraded': downgraded,
        'details': details,
    }
