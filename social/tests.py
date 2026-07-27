from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Friendship

User = get_user_model()

class SocialGraphTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            email = 'usera@example.com' , password = 'newpassword123!', username='usera'
        )
        self.user_b = User.objects.create_user(
                    email = 'userb@example.com' , password = 'newpassword123!', username='userb'
                )
        self.user_c = User.objects.create_user(
                    email = 'userc@example.com' , password = 'newpassword123!', username='userc'
                )   

        self.send_request_url = reverse('social:send-friend-request')
        self.friend_list_url = reverse('social:friend-list')

    def test_prevent_self_friend_request(self):
        self.client.force_authenticate(user = self.user_a)

        data = {
            'receiver_id': str(self.user_a.id)
        }

        response = self.client.post(self.send_request_url,data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_and_accept_friend_request(self):
        self.client.force_authenticate(user = self.user_a)
        data = {
                    'receiver_id': str(self.user_b.id)
        }

        send_response = self.client.post(self.send_request_url,data)
        self.assertEqual(send_response.status_code, status.HTTP_201_CREATED)

        request_id = send_response.data['id']

        self.client.force_authenticate(user = self.user_b)
        respond_url = reverse('social:friend-request-respond',kwargs={'pk': request_id})
        respond_response = self.client.patch(respond_url, {'action':'accept'})

        self.assertEqual(respond_response.status_code, status.HTTP_200_OK)

    def test_dualcolumn_friend_listing(self):
        Friendship.objects.create(user = self.user_a,friend = self.user_b)
        Friendship.objects.create(user = self.user_c, friend = self.user_a)

        self.client.force_authenticate(user = self.user_a)
        response = self.client.get(self.friend_list_url)

        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertEqual(len(response.data),2)

    def test_get_friend_detail(self):
        Friendship.objects.create(user = self.user_a, friend = self.user_b)

        self.client.force_authenticate(user = self.user_a)
        detail_url = reverse('social:friend-detail',kwargs = {'pk':str(self.user_b.id)})

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user_b.username)

    def test_unfriend_user(self):
        Friendship.objects.create(user = self.user_a, friend = self.user_b)
        self.client.force_authenticate(user = self.user_a)

        unfriend_url = reverse('social:friend-detail',kwargs = {'pk':str(self.user_b.id)})
        response = self.client.delete(unfriend_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Friendship.objects.count(), 0)


