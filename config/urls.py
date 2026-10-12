from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.auths.urls')),
    path('api/v1/rental/', include('apps.rental.urls')),
    path('api/v1/finance/', include('apps.finance.urls')),
]
