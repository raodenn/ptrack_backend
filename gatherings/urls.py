from django.urls import path
from .views import UserLocationView, AnalyticsView, VenueView

app_name = 'gatherings'

urlpatterns = [
    path('locations/', UserLocationView.as_view(), name="user-location-create"),
    path('venues/', VenueView.as_view(), name="venue-lookup"),
    path('analytics/<str:period_type>/', AnalyticsView.as_view(), name="analytics"),
]
