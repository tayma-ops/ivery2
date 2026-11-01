import json
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from .forms import ReservationForm
from .models import Resource, Service, Reservation
from .services import window, resolve, reserve, cancel


def packed(r):
    start = timezone.localtime(r.start)
    end = timezone.localtime(r.end)
    return {
        "id": r.pk,
        "token": str(r.token),
        "date": start.date().isoformat(),
        "time": start.strftime("%H:%M"),
        "duration": int((end - start).total_seconds() / 60),
        "price": str(r.total),
        "name": r.customer,
        "phone": r.phone,
        "serviceId": r.service.code,
        "serviceName": r.service.name,
        "resource": r.resource.name,
        "status": r.status,
        "notes": r.notes,
    }


@ensure_csrf_cookie
@require_GET
def session(request):
    return JsonResponse(
        {
            "authenticated": request.user.is_authenticated,
            "username": (
                request.user.get_username() if request.user.is_authenticated else ""
            ),
            "kind": settings.BOOKING_KIND,
        }
    )


@require_GET
def resources(request):
    rows = Resource.objects.filter(active=True).select_related("service").order_by("pk")
    for key in ["specialty", "city"]:
        value = request.GET.get(key, "").strip()[:100]
        if value:
            rows = rows.filter(**{key: value})
    return JsonResponse(
        {
            "resources": [
                {
                    "id": r.pk,
                    "name": r.name,
                    "city": r.city,
                    "specialty": r.specialty,
                    "service": r.service.code if r.service else None,
                }
                for r in rows
            ],
            "services": [
                {
                    "id": s.code,
                    "name": s.name,
                    "description": s.description,
                    "price": str(s.price),
                    "duration": s.duration,
                }
                for s in Service.objects.filter(active=True).order_by("pk")
            ],
        }
    )


@require_GET
def availability(request):
    try:
        resource, service = resolve(
            request.GET.get("resource"), request.GET.get("service")
        )
        vehicle = request.GET.get("vehicle", "")
        wax = request.GET.get("wax") == "1"
        scent = request.GET.get("scent") == "1"
        if settings.BOOKING_KIND == "medical":
            vehicle = ""
            wax = scent = False
        # Validate the selected date once even if every time is unavailable.
        from datetime import date, timedelta

        day = date.fromisoformat(request.GET.get("date", ""))
        if not timezone.localdate() <= day <= timezone.localdate() + timedelta(days=30):
            raise ValueError
        slots = []
        for minutes in range(9 * 60, 21 * 60, 30):
            clock = f"{minutes//60:02}:{minutes%60:02}"
            try:
                start, end, total = window(
                    day.isoformat(), clock, service, vehicle, wax, scent
                )
                allowed = not Reservation.objects.filter(
                    resource=resource,
                    status__in=["pending", "confirmed"],
                    start__lt=end,
                    end__gt=start,
                ).exists()
            except ValidationError:
                allowed = False
            slots.append({"time": clock, "available": allowed})
        return JsonResponse({"slots": slots})
    except (ValidationError, ValueError):
        return JsonResponse({"error": "اختر خدمة وتاريخًا صحيحين."}, status=400)


@require_GET
def bookings(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "سجل الدخول لعرض حجوزاتك."}, status=401)
    return JsonResponse(
        {
            "bookings": [
                packed(r)
                for r in Reservation.objects.filter(user=request.user).select_related(
                    "resource", "service"
                )
            ]
        }
    )


@require_POST
def create(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "سجل الدخول لحفظ الحجز."}, status=401)
    if request.content_type != "application/json" or len(request.body) > 12000:
        return JsonResponse({"error": "صيغة الطلب غير صالحة."}, status=400)
    try:
        body = json.loads(request.body)
        if not isinstance(body, dict):
            raise ValueError
    except (ValueError, UnicodeError):
        return JsonResponse({"error": "تعذر قراءة الطلب."}, status=400)
    form = ReservationForm(body)
    if not form.is_valid():
        return JsonResponse(
            {
                "error": "تحقق من البيانات ورقم الجوال.",
                "fields": form.errors.get_json_data(),
            },
            status=400,
        )
    try:
        reservation = reserve(request.user, form.cleaned_data)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    return JsonResponse({"booking": packed(reservation)}, status=201)


@require_POST
def cancel_api(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "سجل الدخول أولًا."}, status=401)
    get_object_or_404(Reservation, pk=pk, user=request.user)
    try:
        cancel(pk, request.user)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    return JsonResponse({"ok": True})


@login_required
@require_GET
def history(request):
    return render(
        request,
        "booking/history.html",
        {
            "bookings": Reservation.objects.filter(user=request.user).select_related(
                "service", "resource"
            )
        },
    )


@login_required
@require_POST
def cancel_page(request, pk):
    get_object_or_404(Reservation, pk=pk, user=request.user)
    try:
        cancel(pk, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("/bookings/")
