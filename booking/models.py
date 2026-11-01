import uuid
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class Service(models.Model):
    description = models.TextField(max_length=500, blank=True)
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    duration = models.PositiveIntegerField(validators=[MinValueValidator(15)])
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Resource(models.Model):
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, default="الرياض")
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, null=True, blank=True
    )
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ScheduleLock(models.Model):
    version = models.PositiveIntegerField(default=0)


class Reservation(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    customer = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    start = models.DateTimeField()
    end = models.DateTimeField()
    total = models.DecimalField(max_digits=8, decimal_places=2)
    vehicle = models.CharField(max_length=10, blank=True)
    wax = models.BooleanField(default=False)
    scent = models.BooleanField(default=False)
    notes = models.TextField(blank=True, max_length=500)
    status = models.CharField(
        max_length=12,
        default="pending",
        choices=[
            ("pending", "قيد الانتظار"),
            ("confirmed", "مؤكد"),
            ("cancelled", "ملغي"),
            ("completed", "مكتمل"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start"]
        indexes = [models.Index(fields=["resource", "start", "end", "status"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end__gt=models.F("start")),
                name="reservation_positive_duration",
            )
        ]

    def __str__(self):
        return f"{self.resource} — {self.start}"
