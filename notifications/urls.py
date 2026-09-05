from django.urls import path
from .views import (
    NotificationListView,
    NotificationDetailView,
    MarkAllNotificationsReadView,
)

app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('mark-all-read/', MarkAllNotificationsReadView.as_view(), name='notification-mark-all-read'),
    path('<uuid:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
]
