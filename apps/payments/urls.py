from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('recargar/', views.recharge_start, name='recharge_start'),
    path('recargar/resultado/<int:order_id>/', views.recharge_result, name='recharge_result'),
    path('recargar/cancelar/<int:order_id>/', views.recharge_cancel, name='recharge_cancel'),
    path('dummy-checkout/<int:order_id>/', views.dummy_checkout, name='dummy_checkout'),
    path('webhook/', views.payment_webhook, name='payment_webhook'),
    path('control/tangas/', views.control_tangas_packages, name='control_tangas_packages'),
    path('control/tangas/crear/', views.control_tangas_package_edit, name='control_tangas_package_create'),
    path('control/tangas/<int:pk>/editar/', views.control_tangas_package_edit, name='control_tangas_package_edit'),
    path('control/tangas/<int:pk>/eliminar/', views.control_tangas_package_delete, name='control_tangas_package_delete'),
]
