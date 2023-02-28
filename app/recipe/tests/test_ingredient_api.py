"""
Tests for the Ingredient API.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient
from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse("recipe:ingredient-list")


def detail_url(ingredient_id):
    """Create and return a ingredient detail url."""

    return reverse("recipe:ingredient-detail", args=[ingredient_id])


def create_user(email="user@example.com", password="Test1234"):
    """Create and return a user."""

    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()

    def test_auth_required(self):
        """Test auth is required for retrieving ingredients."""

        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving a list of ingredients."""

        for num in range(1, 4):
            Ingredient.objects.create(user=self.user, name=f"Ingredient {num}")

        response = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by("-name")
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test list of ingredients is limited to authenticated user."""

        another_user = create_user(
            email="another_user@example.com",
            password="Test1234",
        )
        Ingredient.objects.create(user=another_user, name="Ingredient another")
        ingredient = Ingredient.objects.create(user=self.user, name="Ingredient")

        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], ingredient.name)
        self.assertEqual(response.data[0]["id"], ingredient.id)

    def test_update_ingredient(self):
        """Test updating an ingredient."""

        ingredient = Ingredient.objects.create(user=self.user, name="Ingredient")

        payload = {
            "name": "Ingredient updated",
        }
        url = detail_url(ingredient.id)
        response = self.client.patch(url, payload)
        ingredient.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ingredient.name, payload["name"])

    def test_delete_ingredient(self):
        """Test deleting an ingredient."""

        ingredient = Ingredient.objects.create(user=self.user, name="Ingredient")

        url = detail_url(ingredient.id)
        response = self.client.delete(url)
        ingredients = Ingredient.objects.filter(user=self.user)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ingredients.exists())
