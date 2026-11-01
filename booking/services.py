from datetime import date, datetime, time, timedelta
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import Reservation, Resource, Service, ScheduleLock


def window(day, clock, service, vehicle="", wax=False, scent=False):
    try:
        day = date.fromisoformat(day)
        clock = time.fromisoformat(clock)
    except (ValueError, TypeError):
        raise ValidationError("التاريخ أو الوقت غير صالح.")
    if not timezone.localdate() <= day <= timezone.localdate() + timedelta(days=30):
        raise ValidationError("اختر تاريخًا من اليوم وحتى 30 يومًا قادمة.")
    if (
        clock.second
        or clock.microsecond
        or clock.minute not in [0, 30]
        or clock.hour < 9
    ):
        raise ValidationError("اختر موعدًا من الأوقات المعروضة.")
    if vehicle not in ["", "sedan", "suv"]:
        raise ValidationError("نوع السيارة غير صحيح.")
    duration = service.duration + (15 if wax else 0)
    if not 15 <= duration <= 180:
        raise ValidationError("مدة الخدمة غير صالحة؛ راجع الإدارة.")
    start = timezone.make_aware(datetime.combine(day, clock))
    end = start + timedelta(minutes=duration)
    closing = timezone.make_aware(datetime.combine(day, time(21)))
    if start <= timezone.now() or end > closing:
        raise ValidationError("هذا الوقت غير متاح.")
    total = (
        service.price
        + (Decimal("20") if vehicle == "suv" else 0)
        + (Decimal("30") if wax else 0)
        + (Decimal("10") if scent else 0)
    )
    return start, end, total


def resolve(resource_id, code):
    try:
        resource = Resource.objects.get(pk=resource_id, active=True)
        service = Service.objects.get(code=code, active=True)
    except (Resource.DoesNotExist, Service.DoesNotExist, ValueError, TypeError):
        raise ValidationError("الخدمة أو مقدم الخدمة غير موجود.")
    if resource.service_id and resource.service_id != service.pk:
        raise ValidationError("الخدمة لا تخص مقدم الخدمة المحدد.")
    return resource, service


@transaction.atomic
def reserve(user, form):
    # One short write lock serializes overlap checks on SQLite and other DBs.
    if not ScheduleLock.objects.filter(pk=1).update(version=F("version") + 1):
        ScheduleLock.objects.create(pk=1, version=1)
    lock = ScheduleLock.objects.select_for_update().get(pk=1)
    previous = Reservation.objects.filter(token=form["token"]).first()
    if previous:
        if previous.user_id != user.pk:
            raise ValidationError("مرجع الحجز غير صالح.")
        return previous
    resource, service = resolve(form["resource"], form["service"])
    if settings.BOOKING_KIND == "medical" and (
        form.get("vehicle") or form.get("wax") or form.get("scent")
    ):
        raise ValidationError("خيارات الخدمة غير صالحة.")
    start, end, total = window(
        form["date"],
        form["time"],
        service,
        form.get("vehicle", ""),
        form.get("wax", False),
        form.get("scent", False),
    )
    if Reservation.objects.filter(
        resource=resource,
        status__in=["pending", "confirmed"],
        start__lt=end,
        end__gt=start,
    ).exists():
        raise ValidationError("حُجز هذا الموعد بالفعل. اختر وقتًا آخر.")
    return Reservation.objects.create(
        token=form["token"],
        user=user,
        resource=resource,
        service=service,
        start=start,
        end=end,
        total=total,
        customer=form["customer"],
        phone=form["phone"],
        vehicle=form.get("vehicle", ""),
        wax=form.get("wax", False),
        scent=form.get("scent", False),
        notes=form.get("notes", ""),
    )


def cancel(reservation_id, user, staff=False):
    rows = Reservation.objects.filter(pk=reservation_id)
    if not staff:
        rows = rows.filter(user=user)
    if not rows.filter(
        status__in=["pending", "confirmed"], start__gt=timezone.now()
    ).update(status="cancelled"):
        raise ValidationError("يمكن إلغاء حجز نشط لم يبدأ بعد فقط.")
