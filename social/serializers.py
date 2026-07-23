from rest_framework import serializers
from .models import Friendship, FriendRequest
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['id', 'username', 'email']

class SendFriendRequestSerializer(serializers.ModelSerializer):
    receiver_id = serializers.UUIDField(write_only=True)
    receiver = UserMinimalSerializer(read_only=True)

    class Meta:
        model = FriendRequest
        fields = ['id', 'receiver_id','receiver', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'created_at']

    def validate_receiver_id(self, value):
        sender = self.context['request'].user

        if sender.id == value:
            raise serializers.ValidationError("You cannot send a friend request to yourself.")

        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("The user you are trying to send a friend request to does not exist.")

        receiver = User.objects.get(id=value)

        u1_id,u2_id = sorted([sender.id, receiver.id])
        if Friendship.objects.filter(user_id=u1_id, friend_id=u2_id).exists():
            raise serializers.ValidationError("You are already friends with this user.")

        existing_request = FriendRequest.objects.filter(
            Q(sender = sender, receiver = receiver) | Q(sender = receiver, receiver = sender), status = 'pending'
        ).first()

        if existing_request:
            if existing_request and existing_request.sender == sender:
                raise serializers.ValidationError("You have already sent a friend request to this user.")
            else:
                raise serializers.ValidationError("This user has already sent you a friend request. Please respond to it.")
        return value

    def create(self, validated_data):
        sender = self.context['request'].user
        reciever_id = validated_data.pop('receiver_id')
        receiver = User.objects.get(id=reciever_id)

        friend_request,created = FriendRequest.objects.update_or_create(
            sender = sender,
            receiver = receiver,
            defaults = {'status':'pending'}
        )
        return friend_request

class FriendRequestRespondSerializer (serializers.Serializer):
    action = serializers.ChoiceField(choices = ['accept','reject'])

class FriendRequestDetailSerializer(serializers.ModelSerializer):
    sender = UserMinimalSerializer(read_only = True)
    receiver = UserMinimalSerializer(read_only = True)

    class Meta:
        fields = ['id','sender','receiver','status','created_at']
