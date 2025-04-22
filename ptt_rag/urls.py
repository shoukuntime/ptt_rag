from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from drf_spectacular.utils import extend_schema_view, extend_schema
@extend_schema_view(get=extend_schema(exclude=True))
class CustomSpectacularAPIView(SpectacularAPIView):
    pass
urlpatterns = [
    path('api/admin/', admin.site.urls),
    path('api/', include('article_app.urls')),
    path('api/schema/', CustomSpectacularAPIView.as_view(), name='schema'),
    path('api/schema/doc/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]