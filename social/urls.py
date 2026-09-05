from django.urls import path
from .views import (
    SendFriendRequestView,
    PendingFriendRequestsView,
    ListFriendsView,
    RespondToFriendRequestView,
    FriendDetailView,
    CancelFriendRequestView
)

app_name = 'social'

urlpatterns = [
    path(
        'requests/',
        SendFriendRequestView.as_view(),
        name = 'send-friend-request'
    ),
    path(
        'requests/pending/',
        PendingFriendRequestsView.as_view(),
        name = 'pending-friend-request'
    ),
    path(
        'requests/<uuid:pk>/respond',
        RespondToFriendRequestView.as_view(),
        name = 'friend-request-respond'   
    ),
    path(
        'requests/<uuid:pk>/cancel',
        CancelFriendRequestView.as_view(),
        name = 'friend-request-cancel'
    ),
    path(
        'friends/',
        ListFriendsView.as_view(),
        name = 'friend-list'
    ),
    path(
        'friends/<uuid:pk>',
        FriendDetailView.as_view(),
        name = 'friend-detail'
    )
]
