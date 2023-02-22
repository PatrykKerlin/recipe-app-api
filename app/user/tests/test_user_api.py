"""
Tests for the user API.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


USER_URL = reverse("user:create")
TOKEN_URL = reverse("user:token")
ME_URL = reverse("user:me")


def create_user(**kwargs):
    """Create and return a new user."""

    return get_user_model().objects.create_user(**kwargs)


class PublicUserAPITests(TestCase):
    """Test the public features of the user API."""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test if creating a user is successful."""

        payload = {
            "email": "test@example.com",
            "password": "test1234",
            "name": "Test Name",
        }
        response = self.client.post(USER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(email=payload["email"])

        self.assertTrue(user.check_password(payload["password"]))

        self.assertNotIn("password", response.data)

    def test_user_with_email_exists_error(self):
        """Test error returned if user with given email exists."""

        payload = {
            "email": "test@example.com",
            "password": "test1234",
            "name": "Test Name",
        }
        create_user(**payload)
        response = self.client.post(USER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """Test error returned if password is less than 5 chars."""

        payload = {
            "email": "test@example.com",
            "password": "test",
            "name": "Test Name",
        }
        response = self.client.post(USER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        user_exists = get_user_model().objects.filter(email=payload["email"]).exists()

        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test token generation for valid credentials."""

        user_data = {
            "email": "test@example.com",
            "password": "Test1234",
            "name": "Test Name",
        }
        create_user(**user_data)

        payload = {
            "email": user_data["email"],
            "password": user_data["password"],
        }
        response = self.client.post(TOKEN_URL, payload)

        self.assertIn("token", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """Test error returned for invalid credentials."""

        user_data = {
            "email": "test@example.com",
            "password": "goodpass",
            "name": "Test Name",
        }
        create_user(**user_data)

        payload = {
            "email": user_data["email"],
            "password": "badpass",
        }
        response = self.client.post(TOKEN_URL, payload)

        self.assertNotIn("token", response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """Test error returned for blank password given."""

        payload = {
            "email": "test@example.com",
            "password": "",
        }
        response = self.client.post(TOKEN_URL, payload)

        self.assertNotIn("token", response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """Test if authentication is required for users."""

        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserAPITest(TestCase):
    """Test API requests that require authentication."""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="Test1234",
            name="Test Name",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in user."""

        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "email": self.user.email,
                "name": self.user.name,
            },
        )

    def test_post_me_not_allowed(self):
        """Test POST is not allowed for the 'me' endpoint."""

        response = self.client.post(ME_URL, {})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test updating user profile for the authenticated user."""

        payload = {
            "name": "Updated name",
            "password": "newTest1234",
        }

        response = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload["name"])
        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
