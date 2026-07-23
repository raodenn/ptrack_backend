from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction

from .models import Friendship, FriendRequest
from .serializers import (
    UserMinimalSerializer, 
    SendFriendRequestSerializer, 
    FriendRequestRespondSerializer,
    FriendRequestDetailSerializer,
    )

User = get_user_model()

class SendFriendRequestView(generics.CreateAPIView):
    serializer_class = SendFriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

class PendingFriendRequestsView(generics.ListAPIView):
    serializer_class = FriendRequestDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return FriendRequest.objects.filter(receiver=user, status='pending')

class RespondToFriendRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self,request,pk):
        serializer = FriendRequestRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']

        friend_request = get_object_or_404(
            FriendRequest,
            id = pk,
            receiver = request.user,
            status = 'pending'
        )

        if action == 'reject':
            friend_request.status = 'rejected'
            friend_request.save()
            return Response({"detail": "Friend request rejected."}, status=status.HTTP_200_OK)

        with transaction.atomic():
            friend_request.status = 'accepted'
            friend_request.save()

            Friendship.objects.get_or_create(
                user = friend_request.sender,
                friend = friend_request.receiver
            )
        return Response({"detail": "Friend request accepted."}, status=status.HTTP_200_OK)

class ListFriendsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self,request):
        user = request.user
        friendships = Friendship.objects.filter(Q(user=user)|Q(friend=user))

        friends_id = [f.friend.id if f.user_id == user.id else f.user.id for f in friendships]
        friends = User.objects.filter(id__in = friends_id)
        serializer = UserMinimalSerializer(friends, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
