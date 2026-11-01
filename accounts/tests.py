from django.contrib.auth.models import User
from django.test import Client, TestCase
from .models import Profile


class AccountTests(TestCase):
    def test_signup_validates_password_and_creates_hashed_account(self):
        data = {
            "username": "newbuyer",
            "first_name": "عميل",
            "email": "buyer@example.test",
            "password1": "123",
            "password2": "123",
        }
        self.assertEqual(self.client.post("/accounts/signup/", data).status_code, 200)
        self.assertFalse(User.objects.exists())
        data.update(
            password1="IndependentPassword77!", password2="IndependentPassword77!"
        )
        self.assertEqual(self.client.post("/accounts/signup/", data).status_code, 302)
        user = User.objects.get()
        self.assertTrue(user.check_password(data["password1"]))
        self.assertNotEqual(user.password, data["password1"])
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_profile_belongs_to_current_user_and_logout_is_post_only(self):
        first = User.objects.create_user("first", password="IndependentPassword77!")
        other = User.objects.create_user("other", password="IndependentPassword77!")
        profile = Profile.objects.create(user=other, city="الرياض")
        self.client.force_login(first)
        self.client.post(
            "/accounts/",
            {
                "phone": "0500000000",
                "city": "جدة",
                "address": "عنوان",
                "user": other.pk,
            },
        )
        profile.refresh_from_db()
        self.assertEqual(profile.city, "الرياض")
        self.assertEqual(Profile.objects.get(user=first).city, "جدة")
        self.assertEqual(self.client.get("/accounts/logout/").status_code, 405)
        self.assertEqual(self.client.post("/accounts/logout/").status_code, 302)
        self.assertEqual(self.client.get("/accounts/").status_code, 302)

    def test_password_change_preserves_valid_session(self):
        user = User.objects.create_user("owner", password="IndependentPassword77!")
        self.client.force_login(user)
        self.assertEqual(
            self.client.post(
                "/accounts/password/",
                {
                    "old_password": "IndependentPassword77!",
                    "new_password1": "DifferentPassword88!",
                    "new_password2": "DifferentPassword88!",
                },
            ).status_code,
            302,
        )
        user.refresh_from_db()
        self.assertTrue(user.check_password("DifferentPassword88!"))
        self.assertEqual(self.client.get("/accounts/").status_code, 200)

    def test_csrf_rejects_account_mutations(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/accounts/signup/", {}).status_code, 403)
