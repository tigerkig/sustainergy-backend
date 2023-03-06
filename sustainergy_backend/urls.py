"""sustainergy_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from rest_framework import routers
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from sustainergy_dashboard import views

from sustainergy_dashboard.views import (
    JwtObtainPairView,
    JwtRefreshView,
    CustomTokenObtainPairView
)

from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView
)


router = routers.DefaultRouter()
router.register(r'panels', views.PanelViewSet)
router.register(r'circuits', views.CircuitViewSet, basename='circuits')
router.register(r'buildings', views.BuildingViewSet, basename='buildings')
router.register(r'operatingHours', views.OperatingHoursViewSet, basename='operatingHours')
router.register(r'panel_report', views.DownloadReports, basename='panel_report')
router.register(r'circuit_categories', views.CircuitCategoryViewSet, basename='circuit_categories')
router.register(r'panel_expansions', views.PanelMeterChannelViewSet, basename='panel_expansions')
router.register(r'panel_meters', views.PanelMeterViewSet, basename='panel_meters')


urlpatterns = [
    path('', include(router.urls)),
    path('grappelli/', include('grappelli.urls')),
    path('grapelli-docs/', include('grappelli.urls_docs')),
    path('admin/', admin.site.urls),
    path('auth/token/', JwtObtainPairView.as_view(), name='token_attain'),
    path('auth/token/refresh/', JwtRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('dashboard/', include('rest_framework.urls', namespace='rest_framework')),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path(r'password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('new_model_id/<model>/', views.new_model_id, name='new_model_id'),
    path('bulk_import_circuits',views.import_xlsx, name="import_xlsx"),
    path('utility_bills', views.show_utility_bills, name="utility_bills"),
    path('create_utility_bills', views.create_utility_bills, name="create_utility_bill"),
    path(r'building/<building_id>/schedule/', views.BuildingScheduleView.as_view(), name='building_schedule'),
    path('__debug__/', include('debug_toolbar.urls')),
    path('utilities/', views.UtilityDetailsView.as_view(), name='utility_usage'),
    # path('_nested_admin/', include('nested_admin.urls')),
    path('panel_expansions/', views.PanelMeterChannelViewSet.as_view({
        'post': 'create',
        'get': 'list'
    })),
    path('panel_expansions/<str:panel_id>/', views.PanelMeterChannelViewSet.as_view({
        'patch': 'partial_update'
    }), name='panel_expansions-detail')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
