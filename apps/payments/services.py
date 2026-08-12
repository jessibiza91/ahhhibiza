import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .gateways import get_active_gateway
from .models import RechargeOrder, TangasPackage, Transaction

logger = logging.getLogger(__name__)


def create_recharge_order(user, package_id):
    """Crea una orden de recarga PENDING a partir de un paquete activo.

    La cantidad y el precio se copian SIEMPRE de la base de datos, nunca
    de datos enviados por el cliente, para impedir manipular el importe.
    """
    try:
        package = TangasPackage.objects.get(pk=package_id)
    except TangasPackage.DoesNotExist:
        raise ValueError('El paquete de Tangas no existe.')
    if not package.is_active:
        raise ValueError('El paquete de Tangas no está activo.')
    if package.tangas_amount <= 0 or package.price_eur <= 0:
        raise ValueError('El paquete de Tangas no tiene un precio válido.')

    order = RechargeOrder.objects.create(
        user=user,
        package=package,
        tangas_amount=package.tangas_amount,
        amount_eur=package.price_eur,
        currency='EUR',
        status=RechargeOrder.Status.PENDING,
        gateway=get_active_gateway().name,
    )
    logger.info('Orden de recarga creada: %s (%s T)', order, order.tangas_amount)
    return order


def start_checkout(order):
    """Inicia el checkout en la pasarela y guarda la referencia externa.

    Devuelve la URL a la que debe redirigirse al usuario para pagar.
    """
    gateway = get_active_gateway()
    result = gateway.create_checkout(order)
    order.gateway_order_id = result['gateway_order_id']
    order.save(update_fields=['gateway_order_id', 'updated_at'])
    logger.info('Checkout iniciado para la orden %s vía %s', order.id, gateway.name)
    return result['checkout_url']


def get_order_by_gateway_ref(gateway_order_id):
    """Localiza la orden por su referencia externa en la pasarela."""
    try:
        return RechargeOrder.objects.get(gateway_order_id=gateway_order_id)
    except RechargeOrder.DoesNotExist:
        raise ValueError(f'No existe ninguna orden con referencia externa {gateway_order_id!r}.')


@transaction.atomic
def confirm_payment(order, gateway_order_id=None, paid_amount=None, paid_currency=None):
    """Confirma una recarga pagada y acredita el saldo.

    Si la pasarela reporta el importe cobrado (paid_amount/paid_currency),
    se verifica contra la orden antes de acreditar nada: un webhook que
    declare otro importe se rechaza. Idempotente: si la orden ya estaba
    pagada no vuelve a acreditar nada. Devuelve la orden actualizada y si
    se acredito saldo en esta llamada.
    """
    order = RechargeOrder.objects.select_for_update().get(pk=order.pk)

    if paid_amount is not None and Decimal(paid_amount) != order.amount_eur:
        raise ValueError(
            f'Importe pagado ({paid_amount}) no coincide con la orden '
            f'({order.amount_eur} {order.currency}).'
        )
    if paid_currency and paid_currency.upper() != order.currency:
        raise ValueError(
            f'Moneda pagada ({paid_currency}) no coincide con la orden ({order.currency}).'
        )

    if order.status == RechargeOrder.Status.PAID:
        return order, False

    if order.status not in (RechargeOrder.Status.PENDING, RechargeOrder.Status.FAILED):
        raise ValueError(
            f'No se puede confirmar una orden {order.get_status_display()}.'
        )

    if gateway_order_id:
        order.gateway_order_id = gateway_order_id

    user = order.user
    user.tangas_balance += order.tangas_amount
    user.save(update_fields=['tangas_balance'])

    Transaction.objects.create(
        user=user,
        amount=order.tangas_amount,
        description=f'Recarga online de {order.tangas_amount} T ({order.amount_eur:.2f} EUR)',
        recharge_order=order,
    )

    order.status = RechargeOrder.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=['status', 'paid_at', 'gateway_order_id', 'updated_at'])

    logger.info(
        'Recarga confirmada: %s T para %s (orden %s)',
        order.tangas_amount,
        user.username,
        order.id,
    )
    return order, True


@transaction.atomic
def fail_payment(order, reason=''):
    """Marca la orden como fallida registrando el motivo."""
    order = RechargeOrder.objects.select_for_update().get(pk=order.pk)
    if order.status == RechargeOrder.Status.PAID:
        raise ValueError('No se puede fallar una orden ya pagada.')

    order.status = RechargeOrder.Status.FAILED
    order.error_message = reason[:1000]
    order.save(update_fields=['status', 'error_message', 'updated_at'])
    logger.warning('Pago fallido para la orden %s: %s', order.id, reason)
    return order


@transaction.atomic
def cancel_payment(order):
    """Cancela una orden que sigue pendiente."""
    order = RechargeOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != RechargeOrder.Status.PENDING:
        raise ValueError('Solo se pueden cancelar ordenes pendientes.')

    order.status = RechargeOrder.Status.CANCELLED
    order.save(update_fields=['status', 'updated_at'])
    logger.info('Orden %s cancelada', order.id)
    return order


@transaction.atomic
def refund_order(order):
    """Marca la orden como reembolsada (stub).

    PENDIENTE DE DEFINIR: las Tangas ya gastadas en promociones no se
    descuentan automaticamente del saldo. La politica de reembolso debe
    decidirse (roadmap) antes de automatizar la deduccion.
    """
    order = RechargeOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != RechargeOrder.Status.PAID:
        raise ValueError('Solo se pueden reembolsar ordenes pagadas.')

    order.status = RechargeOrder.Status.REFUNDED
    order.save(update_fields=['status', 'updated_at'])
    logger.warning('Orden %s marcada como reembolsada (stub sin deduccion)', order.id)
    return order
