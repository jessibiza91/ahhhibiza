from django.urls import path
from . import views

urlpatterns = [
    path('crear/', views.ad_create, name='ad_create'),
    path('<int:ad_id>/', views.ad_detail, name='ad_detail'),
    path('anuncio/editar/<int:pk>/', views.ad_edit, name='ad_edit'),
    path('anuncio/eliminar/<int:pk>/', views.ad_delete, name='ad_delete'),
    path('control/promociones/', views.control_promotion_products, name='control_promotion_products'),
    path('control/anuncios/', views.control_ads, name='control_ads'),
    path('control/servicios/', views.control_service_tags, name='control_service_tags'),
    path('control/promociones/crear/', views.control_promotion_product_edit, name='control_promotion_product_create'),
    path('control/promociones/<int:pk>/editar/', views.control_promotion_product_edit, name='control_promotion_product_edit'),
    path('control/promociones/<int:pk>/eliminar/', views.control_promotion_product_delete, name='control_promotion_product_delete'),
    path('control/usuario/<int:user_id>/anuncio/crear/', views.control_ad_create_for_user, name='control_ad_create_for_user'),
    path('control/anuncio/<int:pk>/', views.control_ad_detail, name='control_ad_detail'),
    path('ads/imagen/delete/<int:image_id>/', views.delete_ad_image, name='delete_ad_image'),
]
