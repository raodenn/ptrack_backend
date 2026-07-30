from django.urls import path
from .views import UserLocationView

app_name = 'gathering'

urlpatterns = [
    path('locations/', UserLocationView.as_view(), name = "user-location-create")
]
