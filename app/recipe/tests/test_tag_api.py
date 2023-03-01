"""
Tests for the Tag API.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer


TAGS_URL = reverse("recipe:tag-list")


def detail_url(tag_id):
    """Create and return a tag detail url."""

    return reverse("recipe:tag-detail", args=[tag_id])


def create_user(email="user@example.com", password="Test1234"):
    """Create and return a user."""

    return get_user_model().objects.create_user(email=email, password=password)


class PublicTagAPITest(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags."""

        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagAPITest(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags."""

        names = ["Vegan", "Dessert", "Low Fat"]
        for name in names:
            Tag.objects.create(user=self.user, name=name)

        response = self.client.get(TAGS_URL)
        tags = Tag.objects.all().order_by("-name")
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user."""

        new_user = create_user(email="new-user@example.com", password="Test1234")
        Tag.objects.create(user=new_user, name="Fruity")
        tag = Tag.objects.create(user=self.user, name="Dietary")

        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], tag.name)
        self.assertEqual(response.data[0]["id"], tag.id)

    def test_update_tag(self):
        """Test updating a tag."""

        tag = Tag.objects.create(user=self.user, name="After Dinner")
        payload = {
            "name": "Dessert",
        }
        url = detail_url(tag.id)

        response = self.client.patch(url, payload)
        tag.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(tag.name, payload["name"])

    def test_delete_tag(self):
        """Test deleting a tag."""

        tag = Tag.objects.create(user=self.user, name="Dessert")
        url = detail_url(tag.id)

        response = self.client.delete(url)
        tags = Tag.objects.filter(user=self.user).exists()

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(tags)

    def test_filter_tags_assigned_to_recipes(self):
        """Test listing tags by those assigned to recipes."""

        tag_1 = Tag.objects.create(user=self.user, name="Tag 1")
        tag_2 = Tag.objects.create(user=self.user, name="Tag 2")
        recipe = Recipe.objects.create(
            title="Sample recipe",
            time_minutes=5,
            price=Decimal("5.50"),
            user=self.user,
        )
        recipe.tags.add(tag_1)

        response = self.client.get(TAGS_URL, {"assigned_only": 1})

        tag_1_serialized = TagSerializer(tag_1)
        tag_2_serialized = TagSerializer(tag_2)

        self.assertIn(tag_1_serialized.data, response.data)
        self.assertNotIn(tag_2_serialized.data, response.data)

    def test_filter_tags_unique(self):
        """Test filtered tags returns a unique list."""

        tag = Tag.objects.create(user=self.user, name="Tag 1")
        Tag.objects.create(user=self.user, name="Tag 2")
        recipe_1 = Recipe.objects.create(
            title="Sample recipe 1",
            time_minutes=5,
            price=Decimal("5.50"),
            user=self.user,
        )
        recipe_2 = Recipe.objects.create(
            title="Sample recipe 2",
            time_minutes=7,
            price=Decimal("2.45"),
            user=self.user,
        )
        recipe_1.tags.add(tag)
        recipe_2.tags.add(tag)

        response = self.client.get(TAGS_URL, {"assigned_only": 1})

        self.assertEqual(len(response.data), 1)
