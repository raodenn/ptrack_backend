from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserLocationView, AnalyticsView, VenueView, SessionReadViewSet, SessionUpdateView

app_name = 'gatherings'

router = DefaultRouter()
router.register(r'sessions', SessionReadViewSet, basename='session')

urlpatterns = [
    path('locations/', UserLocationView.as_view(), name="user-location-create"),
    path('venues/', VenueView.as_view(), name="venue-lookup"),
    path('analytics/<str:period_type>/', AnalyticsView.as_view(), name="analytics"),
    path('sessions/<uuid:pk>/update/', SessionUpdateView.as_view(), name="session-update"),
    path('', include(router.urls)),
]
