"""
Test for recipe APIs.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse("recipe:recipe-list")


def detail_url(recipe_id):
    """Create and return a recipe detail URL."""

    return reverse("recipe:recipe-detail", args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe"""

    defaults = {
        "title": "Sample recipe title",
        "time_minutes": 22,
        "price": Decimal("5.25"),
        "description": "Sample description",
        "link": "http://example.com/recipe.pdf",
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a new user."""

    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""

        response = self.client.get(RECIPES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email="user@example.com",
            password="Test1234",
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes."""

        for _ in range(5):
            create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.all().order_by("-id")
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user."""

        other_user = create_user(
            email="other@example.com",
            password="Test1234",
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail."""

        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        response = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(response.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a recipe."""

        payload = {
            "title": "Sample recipe",
            "time_minutes": 30,
            "price": Decimal("5.99"),
        }
        response = self.client.post(RECIPES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data["id"])

        for key, val in payload.items():
            self.assertEqual(getattr(recipe, key), val)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update of a recipe."""

        original_link = "https://example.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user,
            title="Sample recipe title",
            link=original_link,
        )

        payload = {
            "title": "New recipe title",
        }
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload["title"])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of recipe."""

        recipe = create_recipe(
            user=self.user,
            title="Sample recipe title",
            link="https://example.com/recipe.pdf",
            description="Sample recipe description",
        )

        payload = {
            "title": "New recipe title",
            "link": "https://example.com/new-recipe.pdf",
            "description": "New recipe description",
            "time_minutes": 10,
            "price": Decimal("2.50"),
        }

        url = detail_url(recipe.id)
        response = self.client.put(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()

        for key, val in payload.items():
            self.assertEqual(getattr(recipe, key), val)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in an error."""

        new_user = create_user(
            email="new-user@example.com",
            password="Test1234",
        )

        payload = {
            "user": new_user.id,
        }

        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)

        self.client.patch(url, payload)
        recipe.refresh_from_db()

        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successful."""

        recipe = create_recipe(
            user=self.user,
            title="Sample recipe title",
            link="https://example.com/recipe.pdf",
            description="Sample recipe description",
        )
        url = detail_url(recipe.id)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        """Test trying to delete another user recipe gives error."""

        new_user = create_user(
            email="new-user@example.com",
            password="Test1234",
        )

        recipe = create_recipe(
            user=new_user,
            title="Sample recipe title",
            link="https://example.com/recipe.pdf",
            description="Sample recipe description",
        )

        url = detail_url(recipe.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""

        payload = {
            "title": "Sample recipe title",
            "link": "https://example.com/recipe.pdf",
            "description": "Sample recipe description",
            "time_minutes": 10,
            "price": Decimal("2.50"),
            "tags": [
                {"name": "Test 1"},
                {"name": "Test 2"},
            ],
        }
        response = self.client.post(RECIPES_URL, payload, format="json")
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload["tags"]:
            exists = recipe.tags.filter(
                name=tag["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tag(self):
        """Test creating recipe with existing tag."""

        tag_test_name = "Existing tag"
        tag_test = Tag.objects.create(user=self.user, name=tag_test_name)
        payload = {
            "title": "Sample recipe title",
            "link": "https://example.com/recipe.pdf",
            "description": "Sample recipe description",
            "time_minutes": 10,
            "price": Decimal("2.50"),
            "tags": [
                {"name": tag_test_name},
                {"name": "New tag"},
            ],
        }
        response = self.client.post(RECIPES_URL, payload, format="json")
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_test, recipe.tags.all())
        for tag in payload["tags"]:
            exists = recipe.tags.filter(
                name=tag["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating tag when updating recipe."""

        tag_name = "Test create"
        recipe = create_recipe(user=self.user)
        payload = {
            "tags": [
                {"name": tag_name},
            ]
        }
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format="json")
        new_tag = Tag.objects.get(user=self.user, name=tag_name)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe."""

        tag_test_1 = Tag.objects.create(user=self.user, name="Test update 1")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_test_1)

        tag_test_2 = Tag.objects.create(user=self.user, name="Test update 2")
        payload = {
            "tags": [
                {"name": "Test update 2"},
            ]
        }
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(tag_test_2, recipe.tags.all())
        self.assertNotIn(tag_test_1, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing a recipes tags."""

        tag = Tag.objects.create(user=self.user, name="Test")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {"tags": []}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test creating a recipe with new ingredients."""

        payload = {
            "title": "Sample recipe title",
            "link": "https://example.com/recipe.pdf",
            "description": "Sample recipe description",
            "time_minutes": 10,
            "price": Decimal("2.50"),
            "ingredients": [
                {"name": "Ingredient 1"},
                {"name": "Ingredient 2"},
            ],
        }
        response = self.client.post(RECIPES_URL, payload, format="json")
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                name=ingredient["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating recipe with existing ingredient."""

        ingredient_test_name = "Existing ingredient"
        ingredient_test = Ingredient.objects.create(
            user=self.user, name=ingredient_test_name
        )
        payload = {
            "title": "Sample recipe title",
            "link": "https://example.com/recipe.pdf",
            "description": "Sample recipe description",
            "time_minutes": 10,
            "price": Decimal("2.50"),
            "ingredients": [
                {"name": ingredient_test_name},
                {"name": "New ingredient"},
            ],
        }
        response = self.client.post(RECIPES_URL, payload, format="json")
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient_test, recipe.ingredients.all())
        for ingredient in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                name=ingredient["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating ingredient when updating recipe."""

        ingredient_name = "Test create"
        recipe = create_recipe(user=self.user)
        payload = {
            "ingredients": [
                {"name": ingredient_name},
            ]
        }
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format="json")
        new_ingredient = Ingredient.objects.get(user=self.user, name=ingredient_name)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient when updating a recipe."""

        ingredient_test_1 = Ingredient.objects.create(
            user=self.user, name="Test update 1"
        )
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_test_1)

        ingredient_test_2 = Ingredient.objects.create(
            user=self.user, name="Test update 2"
        )
        payload = {
            "ingredients": [
                {"name": "Test update 2"},
            ]
        }
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_test_2, recipe.ingredients.all())
        self.assertNotIn(ingredient_test_1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipes ingredients."""

        ingredient = Ingredient.objects.create(user=self.user, name="Test")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {"ingredients": []}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)
