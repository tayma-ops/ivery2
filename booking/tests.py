import uuid
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone
from .models import Service, Resource, Reservation


class BookingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", password="IndependentTest77!")
        self.other = User.objects.create_user("other", password="IndependentTest77!")
        self.service = Service.objects.create(
            code="sample", name="خدمة", price=85, duration=60
        )
        self.resource = Resource.objects.create(
            name="مقدم تجريبي", service=self.service
        )
        self.client.force_login(self.user)
        self.data = {
            "token": str(uuid.uuid4()),
            "resource": self.resource.pk,
            "service": "sample",
            "date": (timezone.localdate() + timedelta(days=1)).isoformat(),
            "time": "10:00",
            "customer": "عميل",
            "phone": "0500000000",
            "price": 0,
        }

    def post(self, data=None):
        return self.client.post(
            "/api/bookings/create/", data or self.data, content_type="application/json"
        )

    def test_shared_conflicts_adjacent_slots_and_idempotency(self):
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(Reservation.objects.count(), 1)
        self.client.force_login(self.other)
        self.assertEqual(
            self.post({**self.data, "token": str(uuid.uuid4())}).status_code, 409
        )
        self.assertEqual(
            self.post(
                {**self.data, "token": str(uuid.uuid4()), "time": "11:00"}
            ).status_code,
            201,
        )
        self.assertEqual(Reservation.objects.first().total, 85)

    def test_ownership_cancel_and_reopen(self):
        self.post()
        row = Reservation.objects.get()
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.post(f"/api/bookings/{row.pk}/cancel/").status_code, 404
        )
        self.assertEqual(self.client.get("/api/bookings/").json()["bookings"], [])
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.post(f"/api/bookings/{row.pk}/cancel/").status_code, 200
        )
        self.assertEqual(
            self.post({**self.data, "token": str(uuid.uuid4())}).status_code, 201
        )

    def test_validation_server_price_csrf_and_private_files(self):
        for changes in [
            {"phone": "x"},
            {"time": "10:13"},
            {"time": "21:00"},
            {"date": "2000-01-01"},
            {"resource": 999},
        ]:
            self.assertIn(self.post({**self.data, **changes}).status_code, [400, 409])
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.user)
        self.assertEqual(
            c.post(
                "/api/bookings/create/", self.data, content_type="application/json"
            ).status_code,
            403,
        )
        for path in ["/db.sqlite3", "/.git/config", "/.env", "/config/settings.py"]:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.post().json()["booking"]["price"], "85.00")

    def test_busy_slots_do_not_disclose_customer_data(self):
        self.post()
        self.client.logout()
        response = self.client.get(
            "/api/availability/",
            {
                "resource": self.resource.pk,
                "service": "sample",
                "date": self.data["date"],
            },
        )
        self.assertEqual(response.status_code, 200)
        slots = response.json()["slots"]
        self.assertFalse(next(s["available"] for s in slots if s["time"] == "10:00"))
        self.assertNotContains(response, "0500000000")
        self.assertEqual(self.post().status_code, 401)
