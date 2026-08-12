import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.models import CustomUser
from . import services
from .forms import TangasPackageForm
from .gateways import get_active_gateway
from .models import RechargeOrder, TangasPackage, WebhookLog

logger = logging.getLogger(__name__)


def _is_professional(user):
    return (
        user.is_authenticated
        and user.type == CustomUser.Types.PROFESSIONAL
        and not user.is_superuser
    )


@login_required
@require_POST
@ratelimit(key='user', rate='30/10m', method='POST', block=True)
def recharge_start(request):
    """Inicia una recarga online: crea la orden y redirige a la pasarela."""
    if request.user.type != CustomUser.Types.PROFESSIONAL:
        return redirect('user_dispatch')

    try:
        package_id = int(request.POST.get('package_id', ''))
    except (TypeError, ValueError):
        package_id = None

    try:
        order = services.create_recharge_order(request.user, package_id)
        checkout_url = services.start_checkout(order)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('professional_wallet')
    except Exception:
        logger.exception('Error al iniciar checkout de la orden de recarga')
        messages.error(request, 'No se pudo iniciar el pago. Inténtalo de nuevo.')
        return redirect('professional_wallet')

    return redirect(checkout_url)


@login_required
def dummy_checkout(request, order_id):
    """Checkout simulado de la pasarela dummy (solo desarrollo)."""
    if get_active_gateway().name != 'dummy':
        raise Http404('La pasarela dummy no está activa.')

    order = get_object_or_404(
        RechargeOrder,
        pk=order_id,
        user=request.user,
        status=RechargeOrder.Status.PENDING,
    )
    return render(request, 'payments/dummy_checkout.html', {
        'order': order,
    })


@csrf_exempt
@require_POST
def payment_webhook(request):
    """Recibe notificaciones de la pasarela y acredita o falla el pago.

    La autenticidad se valida con la pasarela activa (firma en las reales).
    Las pasarelas reales no envian CSRF, por eso la vista es csrf_exempt.
    """
    gateway = get_active_gateway()

    if not gateway.verify_webhook(request):
        WebhookLog.objects.create(
            gateway=gateway.name,
            payload={'reason': 'invalid_signature'},
            status='invalid_signature',
        )
        logger.warning('Webhook rechazado: firma invalida (%s)', gateway.name)
        return JsonResponse({'status': 'invalid_signature'}, status=400)

    try:
        event = gateway.parse_event(request)
    except Exception:
        logger.exception('Webhook sin parsear (%s)', gateway.name)
        return JsonResponse({'status': 'error'}, status=400)

    WebhookLog.objects.create(
        gateway=gateway.name,
        payload=event.get('raw') or {},
        status='received',
    )

    try:
        order = services.get_order_by_gateway_ref(event['gateway_order_id'])
    except KeyError:
        logger.warning('Webhook sin gateway_order_id (%s)', gateway.name)
        return JsonResponse({'status': 'invalid_payload'}, status=400)
    except ValueError as exc:
        logger.warning('Webhook con orden desconocida: %s', exc)
        return JsonResponse({'status': 'unknown_order'}, status=400)

    try:
        event_type = event.get('event_type')
        if event_type == 'payment.succeeded':
            services.confirm_payment(
                order,
                paid_amount=event.get('amount'),
                paid_currency=event.get('currency'),
            )
        elif event_type == 'payment.failed':
            services.fail_payment(order, reason=str(event.get('raw', {})))
        else:
            logger.warning('Webhook con tipo de evento no soportado: %s', event_type)
            return JsonResponse({'status': 'unsupported_event'}, status=400)
    except ValueError as exc:
        logger.warning('Webhook procesado con error: %s', exc)
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=400)

    if gateway.name == 'dummy':
        return redirect('payments:recharge_result', order_id=order.id)
    return JsonResponse({'status': 'ok'})


@login_required
@require_GET
def recharge_result(request, order_id):
    """Muestra el resultado de la recarga (pagada, cancelada o fallida)."""
    order = get_object_or_404(RechargeOrder, pk=order_id, user=request.user)
    return render(request, 'payments/recharge_result.html', {'order': order})


@login_required
@require_POST
def recharge_cancel(request, order_id):
    """Cancela una orden de recarga que sigue pendiente."""
    order = get_object_or_404(
        RechargeOrder,
        pk=order_id,
        user=request.user,
        status=RechargeOrder.Status.PENDING,
    )
    services.cancel_payment(order)
    messages.info(request, 'Recarga cancelada. No se ha cobrado nada.')
    return redirect('payments:recharge_result', order_id=order.id)


@staff_member_required
def control_tangas_packages(request):
    packages = (
        TangasPackage.objects
        .annotate(order_count=Count('orders'))
        .order_by('sort_order', 'price_eur', 'name')
    )
    return render(request, 'dashboard/control_tangas_packages.html', {
        'packages': packages,
    })


@staff_member_required
def control_tangas_package_edit(request, pk=None):
    package = get_object_or_404(TangasPackage, pk=pk) if pk else None
    saved = False

    if request.method == 'POST':
        form = TangasPackageForm(request.POST, instance=package)
        if form.is_valid():
            package = form.save()
            saved = True
    else:
        form = TangasPackageForm(instance=package)

    return render(request, 'dashboard/control_tangas_package_form.html', {
        'form': form,
        'package': package,
        'saved': saved,
    })


@staff_member_required
@require_POST
def control_tangas_package_delete(request, pk):
    package = get_object_or_404(TangasPackage, pk=pk)
    if package.orders.exists():
        package.is_active = False
        package.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, 'El paquete tenia compras asociadas y se ha desactivado.')
    else:
        package.delete()
        messages.success(request, 'Paquete eliminado.')
    return redirect('payments:control_tangas_packages')
