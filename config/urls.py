from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.auths.urls')),
    path('api/v1/rental/', include('apps.rental.urls')),
    path('api/v1/finance/', include('apps.finance.urls')),
]
