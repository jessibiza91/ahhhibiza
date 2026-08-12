from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('recargar/', views.recharge_start, name='recharge_start'),
    path('recargar/resultado/<int:order_id>/', views.recharge_result, name='recharge_result'),
    path('recargar/cancelar/<int:order_id>/', views.recharge_cancel, name='recharge_cancel'),
    path('dummy-checkout/<int:order_id>/', views.dummy_checkout, name='dummy_checkout'),
    path('webhook/', views.payment_webhook, name='payment_webhook'),
]
