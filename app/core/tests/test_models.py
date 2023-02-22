"""
Test for models.
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from core import models


class ModelTests(TestCase):
    """Model tests."""

    def test_create_user_with_email_successful(self):
        """Test successful creation of a user with an email."""

        email = "test@example.com"
        password = "Test1234"
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test that email is normalized for new users."""

        sample_emails = [
            ["test1@EXAMPLE.com", "test1@example.com"],
            ["Test2@Example.com", "Test2@example.com"],
            ["TEST3@EXAMPLE.COM", "TEST3@example.com"],
            ["test4@example.COM", "test4@example.com"],
        ]

        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, "Test1234")
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Test that creating a new user without email raises a ValueError"""

        with self.assertRaises(ValueError):
            get_user_model().objects.create_user("", "Test1234")

    def test_create_superuser(self):
        """Test creating a superuser"""

        user = get_user_model().objects.create_superuser("test@example.com", "Test1234")

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        """Test creating a recipe is successful"""

        user = get_user_model().objects.create_user(
            "test@example.com",
            "Test1234",
        )
        recipe = models.Recipe.objects.create(
            user=user,
            title="Sample recipe name",
            time_minutes=5,
            price=Decimal("5.50"),
            description="Sample recipe description",
        )

        self.assertEqual(str(recipe), recipe.title)
