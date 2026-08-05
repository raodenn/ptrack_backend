from django.urls import path
from .views import UserLocationView

app_name = 'gathering'

urlpatterns = [
    path('locations/', UserLocationView[8].as_view(), name = "user-location-create")
]
