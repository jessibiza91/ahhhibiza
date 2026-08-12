from django.contrib import admin
from django.urls import path, include
from core.views import home, health

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('pagos/', include('apps.payments.urls')),
    path('', include('apps.ads.urls')),
    path('', home, name='home'),
]

# /media/ solo lo sirve Django en desarrollo. En produccion lo sirve nginx
# (ver docs/despliegue.md). El helper static() devuelve [] cuando DEBUG=False.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
