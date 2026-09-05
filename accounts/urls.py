from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import ScopedRateThrottle
from .views import UserRegistrationView, LogoutView, UpdateConsentView

app_name = 'accounts'


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'anon_auth'


class ThrottledRegistrationView(UserRegistrationView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'anon_auth'


urlpatterns = [
    path('register/', ThrottledRegistrationView.as_view(), name='register'),
    path('login/', ThrottledTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('consent/', UpdateConsentView.as_view(), name='update_consent'),

]